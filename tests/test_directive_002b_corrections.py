"""DIRECTIVE 002-B 감사 결함 수정 및 데이터 정합성 검증 테스트 스위트."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from chaficial.database.base import Base, get_engine, get_session_factory
from chaficial.models import (
    Listing,
    ListingSnapshot,
    Region,
    SalesCandidate,
)
from chaficial.models.listing import ListingDeletionRestrictedError
from chaficial.models.snapshot import (
    ensure_snapshot_immutability_triggers,
)
from chaficial.regions.manager import (
    InactiveRegionError,
    InvalidRegionError,
    RegionManager,
)
from chaficial.time_travel.query_engine import TimeTravelQueryEngine

# ==============================================================================
# 결함 1: 과거 시점의 지역 정보 누출 방지 반례 테스트
# ==============================================================================

def test_time_travel_region_leakage_protection(db_session):
    """10/1 지역 미확정 매물이 10/10 장안평으로 확인된 경우, 10/5 시점 조회에 장안평 매물로 나타나면 안 됨."""
    reg_mgr = RegionManager()
    reg_mgr.seed_default_regions(db_session)

    t_oct01 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t_oct10 = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)

    # 1. 10/1 최초 수집 시: 주소가 모호하여 지역 미확정 매물
    listing = Listing(
        source_platform="ENCAR",
        source_listing_id="REGION-LEAK-01",
        raw_location="주소 미기재 또는 모호한 서울 주소",
        normalized_region_id="REGION_JANGANPYEONG",  # 현재 상태 필드는 장안평으로 나중에 덮어써졌다고 가정!
        first_observed_at=t_oct01,
        current_status="ACTIVE",
    )
    db_session.add(listing)
    db_session.flush()

    # 10/1 당시 스냅샷: 지역 미확정(None)
    snap_oct01 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=t_oct01,
        ingested_at=t_oct01 + timedelta(minutes=5),
        price_krw=15_000_000,
        mileage_km=40_000,
        listing_status="ACTIVE",
        normalized_region_id=None,  # 10/1 당시에는 지역 미확정이었음!
    )
    # 10/10 정정 스냅샷: 장안평 매매단지로 소재지 확인
    snap_oct10 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=t_oct10,
        ingested_at=t_oct10 + timedelta(minutes=5),
        price_krw=15_000_000,
        mileage_km=40_050,
        listing_status="ACTIVE",
        normalized_region_id="REGION_JANGANPYEONG",  # 10/10에 확인됨!
    )
    db_session.add_all([snap_oct01, snap_oct10])
    db_session.commit()

    # 10/5 시점 조회: Listing.normalized_region_id가 장안평이더라도, 당시 스냅샷은 None이므로 장안평 풀에 나타나면 안 됨!
    t_oct05 = datetime(2026, 10, 5, 0, 0, tzinfo=UTC)
    candidates_oct05 = TimeTravelQueryEngine.get_eligible_listings_as_of(
        db_session, target_region_id="REGION_JANGANPYEONG", as_of_time=t_oct05
    )
    assert not any(c["listing_id"] == listing.listing_id for c in candidates_oct05), (
        "미래(10/10)에 확인된 장안평 지역 정보가 과거(10/5) 조회에 누출되었습니다!"
    )

    # 10/11 시점 조회: 정상적으로 장안평 매물 풀에 포함되어야 함
    t_oct11 = datetime(2026, 10, 11, 0, 0, tzinfo=UTC)
    candidates_oct11 = TimeTravelQueryEngine.get_eligible_listings_as_of(
        db_session, target_region_id="REGION_JANGANPYEONG", as_of_time=t_oct11
    )
    assert any(c["listing_id"] == listing.listing_id for c in candidates_oct11)


# ==============================================================================
# 결함 2: 일반 매물 풀과 실제 선정 후보(SalesCandidate) 구분 테스트
# ==============================================================================

def test_distinction_between_eligible_listings_and_selected_candidates(db_session):
    """추천 대상 매물 풀(Listing)과 실제 선정 후보(SalesCandidate)가 엄격히 구분되어야 함."""
    reg_mgr = RegionManager()
    reg_mgr.seed_default_regions(db_session)

    t_oct01 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t_oct05 = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)

    # 매물 등록
    listing = Listing(
        source_platform="DEALER_DIRECT",
        source_listing_id="POOL-VS-CANDIDATE",
        raw_location="서울 동대문구 장안동 장안평 자동차 매매단지",
        normalized_region_id="REGION_JANGANPYEONG",
        first_observed_at=t_oct01,
        current_status="ACTIVE",
    )
    db_session.add(listing)
    db_session.flush()

    snap = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=t_oct01,
        ingested_at=t_oct01 + timedelta(minutes=5),
        price_krw=12_000_000,
        mileage_km=50_000,
        listing_status="ACTIVE",
        normalized_region_id="REGION_JANGANPYEONG",
    )
    db_session.add(snap)
    db_session.commit()

    # 10/3 조회: 시장 매물 풀(eligible_listings)에는 존재하지만, 아직 SalesCandidate로 선정되지 않음
    t_oct03 = datetime(2026, 10, 3, 0, 0, tzinfo=UTC)
    eligible = TimeTravelQueryEngine.get_eligible_listings_as_of(
        db_session, target_region_id="REGION_JANGANPYEONG", as_of_time=t_oct03
    )
    selected = TimeTravelQueryEngine.get_selected_candidates_as_of(
        db_session, target_region_id="REGION_JANGANPYEONG", as_of_time=t_oct03
    )
    assert len(eligible) >= 1
    assert any(e["listing_id"] == listing.listing_id for e in eligible)
    assert len(selected) == 0  # 아직 선정된 적 없음!

    # 10/5에 실제로 후보로 선정하여 SalesCandidate 테이블에 기록
    candidate = SalesCandidate(
        listing_id=listing.listing_id,
        target_region_id="REGION_JANGANPYEONG",
        selected_at=t_oct05,
        created_at=t_oct05 + timedelta(minutes=1),
        selected_by="AI_AGENT",
        selection_reason="10/5 정기 배치 선정",
    )
    db_session.add(candidate)
    db_session.commit()

    # 10/3 시점 조회 재확인: 미래(10/5)에 선정된 후보가 10/3 조회에 나타나면 안 됨!
    selected_at_oct03 = TimeTravelQueryEngine.get_selected_candidates_as_of(
        db_session, target_region_id="REGION_JANGANPYEONG", as_of_time=t_oct03
    )
    assert len(selected_at_oct03) == 0

    # 10/6 시점 조회: 10/5에 선정된 후보가 정상 조회되어야 함
    t_oct06 = datetime(2026, 10, 6, 0, 0, tzinfo=UTC)
    selected_at_oct06 = TimeTravelQueryEngine.get_selected_candidates_as_of(
        db_session, target_region_id="REGION_JANGANPYEONG", as_of_time=t_oct06
    )
    assert len(selected_at_oct06) == 1
    assert selected_at_oct06[0]["candidate_id"] == candidate.candidate_id


# ==============================================================================
# 결함 3: 지역 설정 버그 수정 테스트 (빈 배열, 중복, 비활성, 존재하지 않는 지역)
# ==============================================================================

def test_region_configuration_edge_cases(db_session):
    """지역 설정 관련 5가지 필수 조건 검증."""
    reg_mgr = RegionManager()
    reg_mgr.seed_default_regions(db_session)

    # 1. 초기 기본값: 장안평
    default_ids = reg_mgr.get_active_sales_region_ids(db_session)
    assert default_ids == ["REGION_JANGANPYEONG"]

    # 매물 1건 준비
    l = Listing(source_platform="ENCAR", source_listing_id="R-TEST-1", raw_location="장안평 자동차 매매단지", normalized_region_id="REGION_JANGANPYEONG", current_status="ACTIVE")
    db_session.add(l)
    db_session.commit()

    # 2. 빈 목록 설정 후 결과 0건 (장안평으로 되돌아가지 않아야 함!)
    reg_mgr.update_sales_regions(db_session, [])
    assert reg_mgr.get_active_sales_region_ids(db_session) == []
    empty_listings = reg_mgr.get_configured_sales_listings(db_session)
    assert len(empty_listings) == 0

    # 3. 수원·인천 추가
    reg_mgr.update_sales_regions(db_session, ["REGION_SUWON", "REGION_INCHEON"])
    active_ids = reg_mgr.get_active_sales_region_ids(db_session)
    assert "REGION_SUWON" in active_ids
    assert "REGION_INCHEON" in active_ids

    # 4. 존재하지 않는 지역 ID 차단 (명확한 예외 발생)
    with pytest.raises(InvalidRegionError):
        reg_mgr.update_sales_regions(db_session, ["REGION_NON_EXISTENT"])

    # 5. 중복 지역 ID 처리 (중복 제거 및 유일화)
    reg_mgr.update_sales_regions(db_session, ["REGION_SUWON", "REGION_SUWON", "REGION_JANGANPYEONG"])
    deduped_ids = reg_mgr.get_active_sales_region_ids(db_session)
    assert deduped_ids == ["REGION_SUWON", "REGION_JANGANPYEONG"]

    # 6. 비활성화된 지역 설정 시 차단
    inactive_reg = Region(region_id="REGION_INACTIVE", region_name="폐쇄된 단지", region_type="MARKET_COMPLEX", is_active=False)
    db_session.add(inactive_reg)
    db_session.commit()
    with pytest.raises(InactiveRegionError):
        reg_mgr.update_sales_regions(db_session, ["REGION_INACTIVE"])


# ==============================================================================
# 결함 4: 기존 DB에 대한 불변성 트리거 보장 및 CASCADE 안전성 테스트
# ==============================================================================

def test_existing_database_immutability_enforcement_and_cascade(tmp_path):
    """이미 데이터가 존재하는 기존 SQLite DB 파일에 트리거를 무손실로 주입하고 UPDATE/DELETE 차단 검증."""
    db_file = tmp_path / "legacy_test.db"
    db_url = f"sqlite:///{db_file}"

    # 1. 초기 DB 생성 및 매물/스냅샷 데이터 적재
    engine = get_engine(db_url, echo=False)
    Base.metadata.create_all(bind=engine)

    # 강제로 기존 트리거를 삭제하여 '트리거가 누락된 레거시 DB' 환경을 모사
    with engine.connect() as conn:
        conn.execute(text("DROP TRIGGER IF EXISTS trg_prevent_snapshot_update"))
        conn.execute(text("DROP TRIGGER IF EXISTS trg_prevent_snapshot_delete"))
        conn.commit()

    SessionLocal = get_session_factory(engine)
    reg_mgr = RegionManager()
    with SessionLocal() as session:
        reg_mgr.seed_default_regions(session)

    with SessionLocal() as session:
        listing = Listing(source_platform="ENCAR", source_listing_id="LEGACY-01", raw_location="장안평", normalized_region_id="REGION_JANGANPYEONG")
        session.add(listing)
        session.flush()

        snap = ListingSnapshot(
            listing_id=listing.listing_id,
            observed_at=datetime.now(UTC),
            price_krw=10_000_000,
            mileage_km=30_000,
            listing_status="ACTIVE",
        )
        session.add(snap)
        session.commit()
        snap_id = snap.snapshot_id
        listing_id = listing.listing_id

    # 2. ensure_snapshot_immutability_triggers 실행 (누락된 트리거를 기존 데이터 손실 없이 설치)
    ensure_snapshot_immutability_triggers(engine)

    # 멱등성 검증: 여러 번 실행해도 에러 없이 안전해야 함
    ensure_snapshot_immutability_triggers(engine)

    # 3. 기존 스냅샷 UPDATE 차단 검증 (Raw SQL)
    with SessionLocal() as session:
        with pytest.raises((OperationalError, IntegrityError)):
            session.execute(
                text("UPDATE listing_snapshots SET price_krw = 5000000 WHERE snapshot_id = :sid"),
                {"sid": snap_id},
            )
            session.commit()
        session.rollback()

    # 4. 기존 스냅샷 직접 DELETE 차단 검증 (Raw SQL)
    with SessionLocal() as session:
        with pytest.raises((OperationalError, IntegrityError)):
            session.execute(
                text("DELETE FROM listing_snapshots WHERE snapshot_id = :sid"),
                {"sid": snap_id},
            )
            session.commit()
        session.rollback()

    # 5. [DIRECTIVE 002-C] 부모 매물 물리 삭제 시도 시 차단 및 스냅샷 보존 검증:
    # 매물 정리 시 과거 시계열 스냅샷이 연쇄 삭제되지 않도록 물리 삭제를 차단하고 이력을 보존함
    with SessionLocal() as session:
        l = session.get(Listing, listing_id)
        with pytest.raises(ListingDeletionRestrictedError):
            session.delete(l)
            session.commit()
        session.rollback()

    with SessionLocal() as session:
        # 부모 매물 삭제 시도가 차단되었으므로 스냅샷은 안전하게 영구 보존됨
        assert session.get(ListingSnapshot, snap_id) is not None
