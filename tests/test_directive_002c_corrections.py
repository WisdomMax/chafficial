"""DIRECTIVE 002-C 결함 수정 및 안전성 검증 테스트.

1. 과거 가격 기록 연쇄 삭제 차단 및 보존 검증
2. 구버전 DB 스키마 무손실 업그레이드(마이그레이션) 검증
3. 과거 파트너 승인 상태 미래 정보 누출 차단 검증
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from chaficial.database.base import Base
from chaficial.database.migration import migrate_database
from chaficial.models.candidate import CandidateStatusHistory, SalesCandidate
from chaficial.models.listing import Listing, ListingDeletionRestrictedError
from chaficial.models.region import Region
from chaficial.models.snapshot import ImmutableSnapshotError, ListingSnapshot
from chaficial.models.vehicle import VehicleIdentity
from chaficial.time_travel.query_engine import TimeTravelQueryEngine


@pytest.fixture
def db_session():
    """테스트용 메모리 DB 세션 fixture."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # 기본 지역 생성
        region = Region(
            region_id="janganpyeong",
            region_name="서울 장안평",
            region_type="MARKET_COMPLEX",
            is_active=True,
        )
        session.add(region)
        session.commit()
        yield session


def test_listing_history_preservation_and_deletion_prevention(db_session: Session):
    """[결함 1 반례] 10월 1일 등록, 10월 5일 가격 인하, 10월 10일 판매 종료(DELISTED).
    
    판매 종료 이후에도 10월 1일과 10월 5일의 가격 기록이 보존되어 조회되어야 하며,
    스냅샷을 보유한 매물의 무단 물리 삭제 시도는 차단되어야 한다.
    """
    vehicle = VehicleIdentity(
        vehicle_id="veh-hist-01",
        plate_number="12가3456",
        vin="KMHXX001",
    )
    db_session.add(vehicle)

    # 10월 1일 매물 등록
    t1 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    listing = Listing(
        listing_id="list-hist-01",
        source_platform="encar",
        source_listing_id="enc-01",
        vehicle_id="veh-hist-01",
        raw_location="서울 동대문구 장안동",
        normalized_region_id="janganpyeong",
        first_observed_at=t1,
        current_status="ACTIVE",
    )
    db_session.add(listing)

    snap1 = ListingSnapshot(
        listing_id="list-hist-01",
        observed_at=t1,
        ingested_at=t1,
        price_krw=20_000_000,
        mileage_km=50_000,
        listing_status="ACTIVE",
        normalized_region_id="janganpyeong",
    )
    db_session.add(snap1)
    db_session.commit()

    # 10월 5일 가격 인하
    t2 = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)
    snap2 = ListingSnapshot(
        listing_id="list-hist-01",
        observed_at=t2,
        ingested_at=t2,
        price_krw=19_000_000,
        mileage_km=50_200,
        listing_status="PRICE_CHANGED",
        normalized_region_id="janganpyeong",
    )
    db_session.add(snap2)
    listing.current_status = "PRICE_CHANGED"
    db_session.commit()

    # 10월 10일 판매 종료 (DELISTED) 처리
    t3 = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)
    snap3 = ListingSnapshot(
        listing_id="list-hist-01",
        observed_at=t3,
        ingested_at=t3,
        price_krw=19_000_000,
        mileage_km=50_500,
        listing_status="DELISTED",
        normalized_region_id="janganpyeong",
    )
    db_session.add(snap3)
    listing.current_status = "DELISTED"
    db_session.commit()

    # 1. 판매 종료 이후에도 10월 1일과 10월 5일의 가격 기록이 과거 시점 조회로 정상 확인되어야 함
    snap_oct1 = TimeTravelQueryEngine.get_listing_snapshot_at(db_session, "list-hist-01", datetime(2026, 10, 2, tzinfo=UTC))
    assert snap_oct1 is not None
    assert snap_oct1.price_krw == 20_000_000
    assert snap_oct1.listing_status == "ACTIVE"

    snap_oct6 = TimeTravelQueryEngine.get_listing_snapshot_at(db_session, "list-hist-01", datetime(2026, 10, 6, tzinfo=UTC))
    assert snap_oct6 is not None
    assert snap_oct6.price_krw == 19_000_000
    assert snap_oct6.listing_status == "PRICE_CHANGED"

    # 2. 일반 매물 물리 삭제 시도 시 에러 발생 및 차단 확인
    with pytest.raises(ListingDeletionRestrictedError):
        db_session.delete(listing)
        db_session.flush()
    db_session.rollback()

    # 3. 롤백 후 모든 스냅샷이 온전히 보존되어 있는지 확인
    snapshots = db_session.scalars(
        select(ListingSnapshot).where(ListingSnapshot.listing_id == "list-hist-01")
    ).all()
    assert len(snapshots) == 3


def test_legacy_database_migration():
    """[결함 2 반례] 구버전 DB 스키마 생성 후 데이터 무손실 마이그레이션 검증.
    
    구버전 테이블 구조(normalized_region_id, created_at 컬럼 부재)를 재현하고,
    마이그레이션 실행 후 기존 레코드 보존, 신규 컬럼 조회, 멱등성을 검증한다.
    """
    engine = create_engine("sqlite:///:memory:")

    # 1. 전체 테이블 기본 생성
    Base.metadata.create_all(engine)

    # 2. 구버전 상태로 되돌리기: 인덱스 제거 -> 컬럼 드롭 -> 구버전 테이블 상태 확립
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE candidate_status_histories;"))
        conn.execute(text("DROP INDEX IF EXISTS ix_listing_snapshots_normalized_region_id;"))
        conn.execute(text("DROP INDEX IF EXISTS ix_sales_candidates_created_at;"))
        conn.execute(text("ALTER TABLE listing_snapshots DROP COLUMN normalized_region_id;"))
        conn.execute(text("ALTER TABLE sales_candidates DROP COLUMN created_at;"))

        # 구버전 트리거 삭제 (이전 조건부 트리거 또는 트리거 없음 상태)
        conn.execute(text("DROP TRIGGER IF EXISTS trg_prevent_snapshot_update;"))
        conn.execute(text("DROP TRIGGER IF EXISTS trg_prevent_snapshot_delete;"))

        # 구버전 샘플 데이터 삽입
        conn.execute(text("""
            INSERT INTO regions (region_id, region_name, region_type, is_active)
            VALUES ('janganpyeong', '서울 장안평', 'MARKET_COMPLEX', 1);
        """))
        conn.execute(text("""
            INSERT INTO listings (listing_id, source_platform, source_listing_id, raw_location, normalized_region_id, first_observed_at, current_status)
            VALUES ('legacy-l1', 'encar', 'e1', '서울 동대문구 장안동', 'janganpyeong', '2026-10-01 10:00:00', 'ACTIVE');
        """))
        conn.execute(text("""
            INSERT INTO listing_snapshots (snapshot_id, listing_id, observed_at, ingested_at, price_krw, mileage_km, listing_status)
            VALUES ('snap-legacy-1', 'legacy-l1', '2026-10-01 10:00:00', '2026-10-01 10:00:00', 15000000, 60000, 'ACTIVE');
        """))
        conn.execute(text("""
            INSERT INTO sales_candidates (candidate_id, listing_id, target_region_id, selected_at, selected_by, selection_reason, selection_score, availability_status, partner_review_status)
            VALUES ('cand-legacy-1', 'legacy-l1', 'janganpyeong', '2026-10-01 12:00:00', 'AI_AGENT', '가격 경쟁력 우수', 85.0, 'UNCONFIRMED', 'PENDING');
        """))

    # 3. 마이그레이션 실행
    report = migrate_database(engine)
    assert report["success"] is True

    with Session(engine) as session:
        # 1. 기존 데이터 레코드 수 및 가격 유지 확인
        snap = session.scalar(select(ListingSnapshot).where(ListingSnapshot.snapshot_id == "snap-legacy-1"))
        assert snap is not None
        assert snap.price_krw == 15_000_000
        # 2. 신규 컬럼 정상 추가 및 과거 스냅샷 지역은 임의 날조 없이 None(미확정)으로 보존됨을 확인
        assert snap.normalized_region_id is None

        # 3. sales_candidates 신규 컬럼(created_at) 정상 확인
        cand = session.scalar(select(SalesCandidate).where(SalesCandidate.candidate_id == "cand-legacy-1"))
        assert cand is not None
        assert cand.created_at is not None

        # 4. 스냅샷 불변성 트리거 동작 확인 (수정 시도 시 차단)
        with pytest.raises(ImmutableSnapshotError):
            snap.price_krw = 999
            session.commit()
        session.rollback()

    # 5. 마이그레이션 2회차 반복 실행 시에도 안전(멱등성) 확인
    report2 = migrate_database(engine)
    assert report2["success"] is True


def test_past_partner_review_status_leakage_prevention(db_session: Session):
    """[결함 3 반례] 과거 시점 파트너 승인 상태 미래 정보 누출 방지 검증.
    
    10월 5일 선정: PENDING
    10월 10일 파트너 승인: APPROVED
    10월 6일 시점 조회: PENDING (APPROVED 누출 차단)
    10월 11일 시점 조회: APPROVED
    """
    t_select = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)
    t_approve = datetime(2026, 10, 10, 15, 0, tzinfo=UTC)

    # 매물 등록
    listing = Listing(
        listing_id="list-cand-01",
        source_platform="encar",
        source_listing_id="enc-c01",
        raw_location="서울 동대문구 장안동",
        normalized_region_id="janganpyeong",
        first_observed_at=t_select,
        current_status="ACTIVE",
    )
    db_session.add(listing)

    snap = ListingSnapshot(
        listing_id="list-cand-01",
        observed_at=t_select,
        ingested_at=t_select,
        price_krw=25_000_000,
        mileage_km=40_000,
        listing_status="ACTIVE",
        normalized_region_id="janganpyeong",
    )
    db_session.add(snap)

    # 10월 5일: 후보 선정 (초기 상태 PENDING)
    candidate = SalesCandidate(
        candidate_id="cand-001",
        listing_id="list-cand-01",
        target_region_id="janganpyeong",
        selected_at=t_select,
        created_at=t_select,
        selected_by="AI_AGENT",
        selection_reason="장안평 시장 회전율 우수 예상",
        selection_score=92.5,
        availability_status="AVAILABLE",
        partner_review_status="PENDING",
    )
    db_session.add(candidate)
    
    # 후보 초기 상태 이력 기록
    hist1 = CandidateStatusHistory(
        candidate_id="cand-001",
        partner_review_status="PENDING",
        availability_status="AVAILABLE",
        changed_at=t_select,
        ingested_at=t_select,
        review_note="초기 AI 후보 선정",
    )
    db_session.add(hist1)
    db_session.commit()

    # 10월 10일: 파트너가 매물 검토 후 승인 (APPROVED)
    candidate.partner_review_status = "APPROVED"
    hist2 = CandidateStatusHistory(
        candidate_id="cand-001",
        partner_review_status="APPROVED",
        availability_status="AVAILABLE",
        changed_at=t_approve,
        ingested_at=t_approve,
        review_note="장안평 딜러 협의 완료, 광고 승인",
    )
    db_session.add(hist2)
    db_session.commit()

    # 10월 6일 시점 조회 (승인 전): partner_review_status가 PENDING이어야 함 (미래의 APPROVED 누출 차단)
    t_query_before = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
    results_before = TimeTravelQueryEngine.get_selected_candidates_as_of(
        db_session, "janganpyeong", t_query_before
    )
    assert len(results_before) == 1
    assert results_before[0]["candidate_id"] == "cand-001"
    assert results_before[0]["partner_review_status"] == "PENDING"

    # 10월 11일 시점 조회 (승인 후): partner_review_status가 APPROVED이어야 함
    t_query_after = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)
    results_after = TimeTravelQueryEngine.get_selected_candidates_as_of(
        db_session, "janganpyeong", t_query_after
    )
    assert len(results_after) == 1
    assert results_after[0]["candidate_id"] == "cand-001"
    assert results_after[0]["partner_review_status"] == "APPROVED"
