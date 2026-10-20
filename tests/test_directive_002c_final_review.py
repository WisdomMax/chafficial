"""DIRECTIVE 002-C FINAL REVIEW 결함 검증 및 보완 테스트.

1. 결함 A: 마이그레이션 시 허위 과거 승인 정보 생성 방지 (역사적 정확성 보존)
2. 결함 B: 파트너 상태 이력 불변성(Append-only) 및 UPDATE/DELETE 차단 검증
3. 원자적 상태 변경 도우미 함수(update_candidate_status) 검증
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from chaficial.database.base import Base
from chaficial.database.migration import migrate_database
from chaficial.models.candidate import (
    CandidateStatusHistory,
    ImmutableCandidateHistoryError,
    SalesCandidate,
    update_candidate_status,
)
from chaficial.models.listing import Listing
from chaficial.models.region import Region
from chaficial.time_travel.query_engine import TimeTravelQueryEngine


@pytest.fixture
def db_session():
    """테스트용 메모리 DB 세션 fixture."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        region = Region(
            region_id="janganpyeong",
            region_name="서울 장안평",
            region_type="MARKET_COMPLEX",
            is_active=True,
        )
        session.add(region)
        session.commit()
        yield session


def test_migration_does_not_create_false_past_approval():
    """[결함 A 반례] 마이그레이션 시 기존 레거시 후보가 과거 시점에 이미 적재된 것으로 날조되지 않는지 검증.
    
    10월 5일 선정되었으나 실제 DB 적재(마이그레이션) 시점이 10월 21일인 레거시 후보는,
    시스템에 존재하지 않았던 과거 시점(10월 6일) 조회에 나타나지 않아야 한다 (created_at 소급 누출 차단).
    마이그레이션 이후 시점(10월 22일)에서는 정상 조회되어야 한다.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # 구버전 상태 모사: candidate_status_histories 제거, 컬럼 제거
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE candidate_status_histories;"))
        conn.execute(text("DROP INDEX IF EXISTS ix_listing_snapshots_normalized_region_id;"))
        conn.execute(text("DROP INDEX IF EXISTS ix_sales_candidates_created_at;"))
        conn.execute(text("ALTER TABLE listing_snapshots DROP COLUMN normalized_region_id;"))
        conn.execute(text("ALTER TABLE sales_candidates DROP COLUMN created_at;"))

        # 구버전 데이터 삽입 (10월 5일 선정되었고 현재 상태는 APPROVED인 후보)
        conn.execute(text("""
            INSERT INTO regions (region_id, region_name, region_type, is_active)
            VALUES ('janganpyeong', '서울 장안평', 'MARKET_COMPLEX', 1);
        """))
        conn.execute(text("""
            INSERT INTO listings (listing_id, source_platform, source_listing_id, raw_location, normalized_region_id, first_observed_at, current_status)
            VALUES ('legacy-l1', 'encar', 'e1', '서울 동대문구 장안동', 'janganpyeong', '2026-10-05 10:00:00', 'ACTIVE');
        """))
        conn.execute(text("""
            INSERT INTO listing_snapshots (snapshot_id, listing_id, observed_at, ingested_at, price_krw, mileage_km, listing_status)
            VALUES ('snap-legacy-1', 'legacy-l1', '2026-10-05 10:00:00', '2026-10-05 10:00:00', 15000000, 60000, 'ACTIVE');
        """))
        conn.execute(text("""
            INSERT INTO sales_candidates (candidate_id, listing_id, target_region_id, selected_at, selected_by, selection_reason, selection_score, availability_status, partner_review_status)
            VALUES ('cand-legacy-approved', 'legacy-l1', 'janganpyeong', '2026-10-05 12:00:00', 'AI_AGENT', '가상 검증', 90.0, 'AVAILABLE', 'APPROVED');
        """))

    # 마이그레이션 실행 (시점: 10월 21일 기준)
    migration_time = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    report = migrate_database(engine, migration_time=migration_time)
    assert report["success"] is True

    with Session(engine) as session:
        # 1. 10월 6일 시점 조회 시: 시스템에 아직 적재(created_at)되지 않은 과거이므로 조회 결과가 0건이어야 함! (적재 시점 누출 차단)
        t_oct6 = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)
        results = TimeTravelQueryEngine.get_selected_candidates_as_of(session, "janganpyeong", t_oct6)
        assert len(results) == 0

        # 2. 마이그레이션 이후 시점(10월 22일) 조회 시: 정상 적재되어 조회 가능 확인
        t_oct22 = datetime(2026, 10, 22, 12, 0, tzinfo=UTC)
        results_after = TimeTravelQueryEngine.get_selected_candidates_as_of(session, "janganpyeong", t_oct22)
        assert len(results_after) == 1
        assert results_after[0]["partner_review_status"] == "APPROVED"


def test_candidate_status_history_immutability(db_session: Session):
    """[결함 B 반례] CandidateStatusHistory의 불변성(Append-only) 및 수정/삭제 차단 검증."""
    t1 = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 10, 10, 15, 0, tzinfo=UTC)

    listing = Listing(
        listing_id="list-b-01",
        source_platform="encar",
        source_listing_id="e-b01",
        raw_location="서울 장안평",
        normalized_region_id="janganpyeong",
        first_observed_at=t1,
        current_status="ACTIVE",
    )
    db_session.add(listing)

    candidate = SalesCandidate(
        candidate_id="cand-b-01",
        listing_id="list-b-01",
        target_region_id="janganpyeong",
        selected_at=t1,
        created_at=t1,
        selected_by="AI_AGENT",
        selection_reason="검증",
        partner_review_status="PENDING",
    )
    db_session.add(candidate)

    # 1. 초기 PENDING 이력 생성
    hist1 = CandidateStatusHistory(
        candidate_id="cand-b-01",
        partner_review_status="PENDING",
        availability_status="UNCONFIRMED",
        changed_at=t1,
        ingested_at=t1,
        review_note="초기 선정",
    )
    db_session.add(hist1)
    db_session.commit()

    # 2. update_candidate_status API를 통한 원자적 상태 갱신 및 이력 추가
    update_candidate_status(
        session=db_session,
        candidate_id="cand-b-01",
        new_partner_status="APPROVED",
        new_availability_status="AVAILABLE",
        changed_at=t2,
        ingested_at=t2,
        note="파트너 승인 완료",
    )
    db_session.commit()

    # 3. 과거 PENDING 이력 ORM UPDATE 시도 차단 검증
    with pytest.raises(ImmutableCandidateHistoryError):
        hist1.partner_review_status = "REJECTED"
        db_session.commit()
    db_session.rollback()

    # 4. 과거 PENDING 이력 ORM DELETE 시도 차단 검증
    with pytest.raises(ImmutableCandidateHistoryError):
        db_session.delete(hist1)
        db_session.commit()
    db_session.rollback()

    # 5. Raw SQL UPDATE/DELETE 차단 검증 (DB 트리거)
    with pytest.raises((OperationalError, IntegrityError)):
        db_session.execute(
            text("UPDATE candidate_status_histories SET partner_review_status='REJECTED' WHERE history_id=:hid"),
            {"hid": hist1.history_id},
        )
        db_session.commit()
    db_session.rollback()

    with pytest.raises((OperationalError, IntegrityError)):
        db_session.execute(
            text("DELETE FROM candidate_status_histories WHERE history_id=:hid"),
            {"hid": hist1.history_id},
        )
        db_session.commit()
    db_session.rollback()

    # 6. 과거 시점 조회 정합성 재확인 (10월 6일: PENDING, 10월 11일: APPROVED)
    res_oct6 = TimeTravelQueryEngine.get_selected_candidates_as_of(
        db_session, "janganpyeong", datetime(2026, 10, 6, tzinfo=UTC)
    )
    assert res_oct6[0]["partner_review_status"] == "PENDING"

    res_oct11 = TimeTravelQueryEngine.get_selected_candidates_as_of(
        db_session, "janganpyeong", datetime(2026, 10, 11, tzinfo=UTC)
    )
    assert res_oct11[0]["partner_review_status"] == "APPROVED"
