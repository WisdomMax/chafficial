"""CHA-FICIAL AI PROJECT - DIRECTIVE 010-D
운영 DB 영구 보존, 멱등성, 부분 수집 보호 회귀 검증 테스트 세트.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from chaficial.database.base import Base
from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.platforms.base import StandardListingRecord
from chaficial.tracker.price_tracker import (
    PriceEventTracker,
    SearchScopeSpec,
    compute_db_logical_hashes,
)
from chaficial.tracker.stream_pipeline import MarketObservationStreamPipeline


@pytest.fixture
def test_engine():
    """인메모리 테스트 DB 엔진."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def test_operational_db_not_deleted_and_preserves_records(test_engine):
    """지침 1: 기존 DB에 126대가 존재하는 상태에서 신규 배치가 유입될 때 기존 매물과 스냅샷이 100% 보존되는지 검증."""
    Session = sessionmaker(bind=test_engine)
    session = Session()

    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    pipeline = MarketObservationStreamPipeline(tracker=tracker)
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼", sub_model="ALL")

    t1 = datetime(2026, 10, 21, 11, 0, tzinfo=UTC)
    records_batch1 = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id=f"CAR_{i:04d}",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year="2022",
            registration_year_month="2022-03",
            mileage_km=30000 + i * 100,
            price_krw=17000000 + i * 100000,
            monthly_payment_krw=None,
            product_type="CASH_OR_INSTALLMENT",
            raw_location="경기 수원",
            vehicle_fingerprint=f"현대_아반떼_CN7_CAR_{i:04d}",
            observed_at=t1,
            data_origin="REAL_OBSERVED",
        )
        for i in range(126)
    ]

    res1 = pipeline.execute_batch(
        records=records_batch1,
        session=session,
        batch_id="TEST_BATCH_01",
        scope=scope,
        observation_time=t1,
        is_partial_scrape=True,
        data_origin="REAL_OBSERVED",
    )
    session.commit()

    assert res1.total_records_ingested == 126
    assert res1.first_seen_count == 126
    assert session.execute(select(func.count(Listing.listing_id))).scalar() == 126
    assert session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar() == 126

    # 2차 관측 배치: 기존 126대 중 100대 재관측 + 신규 10대 유입
    t2 = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)
    records_batch2 = records_batch1[:100] + [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id=f"NEW_CAR_{j:04d}",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="인스퍼레이션",
            model_year="2023",
            registration_year_month="2023-01",
            mileage_km=15000,
            price_krw=21000000,
            monthly_payment_krw=None,
            product_type="CASH_OR_INSTALLMENT",
            raw_location="서울 장안평",
            vehicle_fingerprint=f"현대_아반떼_CN7_NEW_CAR_{j:04d}",
            observed_at=t2,
            data_origin="REAL_OBSERVED",
        )
        for j in range(10)
    ]

    res2 = pipeline.execute_batch(
        records=records_batch2,
        session=session,
        batch_id="TEST_BATCH_02",
        scope=scope,
        observation_time=t2,
        is_partial_scrape=True,
        data_origin="REAL_OBSERVED",
    )
    session.commit()

    # 기존 126대는 삭제되지 않고 10대가 더해져 총 136대 유지
    assert session.execute(select(func.count(Listing.listing_id))).scalar() == 136
    # 스냅샷: 기존 126개 + 신규 매물 10개의 최초 스냅샷 = 136개 완벽 보존 (변동 없는 재관측 시 중복 스냅샷 방지)
    assert session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar() == 136
    # 배치 로그도 2개 영구 보존
    assert session.execute(select(func.count(BatchAuditLog.batch_id))).scalar() == 2


def test_idempotent_reexecution_preserves_exact_state(test_engine):
    """지침 2: 동일 배치 재실행 시 DB 내용 및 행 수가 100% 불변 보존되는지 멱등성 검증."""
    Session = sessionmaker(bind=test_engine)
    session = Session()

    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    pipeline = MarketObservationStreamPipeline(tracker=tracker)
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼", sub_model="ALL")

    t1 = datetime(2026, 10, 21, 11, 0, tzinfo=UTC)
    records = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="IDEMPOTENT_CAR_01",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="스마트",
            model_year="2021",
            registration_year_month="2021-05",
            mileage_km=40000,
            price_krw=14500000,
            monthly_payment_krw=None,
            product_type="CASH_OR_INSTALLMENT",
            raw_location="인천 서구",
            vehicle_fingerprint="현대_아반떼_CN7_IDEMPOTENT_01",
            observed_at=t1,
            data_origin="REAL_OBSERVED",
        )
    ]

    # 1회차 실행
    res1 = pipeline.execute_batch(
        records=records,
        session=session,
        batch_id="IDEMPOTENT_BATCH",
        scope=scope,
        observation_time=t1,
        is_partial_scrape=True,
    )
    session.commit()

    hash_after_1 = compute_db_logical_hashes(session)
    count_listings_1 = session.execute(select(func.count(Listing.listing_id))).scalar()
    count_snapshots_1 = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
    count_events_1 = session.execute(select(func.count(PriceEvent.event_id))).scalar()

    # 동일 배치 2회차 재실행
    res2 = pipeline.execute_batch(
        records=records,
        session=session,
        batch_id="IDEMPOTENT_BATCH",
        scope=scope,
        observation_time=t1,
        is_partial_scrape=True,
    )
    session.commit()

    hash_after_2 = compute_db_logical_hashes(session)
    count_listings_2 = session.execute(select(func.count(Listing.listing_id))).scalar()
    count_snapshots_2 = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
    count_events_2 = session.execute(select(func.count(PriceEvent.event_id))).scalar()

    # 멱등성 검증: 행 수 및 SHA-256 해시가 1비트도 변하지 않아야 함
    assert count_listings_1 == count_listings_2 == 1
    assert count_snapshots_1 == count_snapshots_2 == 1
    assert count_events_1 == count_events_2 == 1
    assert hash_after_1["listings"]["hash"] == hash_after_2["listings"]["hash"]
    assert hash_after_1["listing_snapshots"]["hash"] == hash_after_2["listing_snapshots"]["hash"]
    assert hash_after_1["price_events"]["hash"] == hash_after_2["price_events"]["hash"]
    assert res2.notes == "ALREADY_PROCESSED_IDEMPOTENT_SKIP"


def test_partial_scrape_freezes_missing_counters(test_engine):
    """지침 3: is_partial_scrape=True인 경우 미노출 매물의 누락 카운터가 증가하지 않고 동결 보존되는지 검증."""
    Session = sessionmaker(bind=test_engine)
    session = Session()

    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    pipeline = MarketObservationStreamPipeline(tracker=tracker)
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼", sub_model="ALL")

    t1 = datetime(2026, 10, 21, 11, 0, tzinfo=UTC)
    r1 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="WATCHED_CAR_01",
        manufacturer="현대",
        model_name="아반떼",
        model_generation="CN7",
        sub_model="PRE_FACELIFT",
        powertrain_line="STANDARD",
        trim_name="모던",
        model_year="2022",
        registration_year_month="2022-03",
        mileage_km=30000,
        price_krw=17000000,
        monthly_payment_krw=None,
        product_type="CASH_OR_INSTALLMENT",
        raw_location="경기 수원",
        vehicle_fingerprint="WATCHED_01",
        observed_at=t1,
        data_origin="REAL_OBSERVED",
    )
    pipeline.execute_batch(records=[r1], session=session, batch_id="B1", scope=scope, observation_time=t1, is_partial_scrape=True)
    session.commit()

    listing = session.execute(select(Listing).where(Listing.source_listing_id == "WATCHED_CAR_01")).scalar_one()
    assert listing.consecutive_missing_count == 0
    assert listing.current_status == "ACTIVE"

    # 2차 수집 시 이 매물이 누락되었으나 is_partial_scrape=True 인 경우
    t2 = datetime(2026, 10, 21, 15, 0, tzinfo=UTC)
    other_r = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="OTHER_CAR_02",
        manufacturer="현대",
        model_name="아반떼",
        model_generation="CN7",
        sub_model="PRE_FACELIFT",
        powertrain_line="STANDARD",
        trim_name="스마트",
        model_year="2021",
        registration_year_month="2021-01",
        mileage_km=50000,
        price_krw=13000000,
        monthly_payment_krw=None,
        product_type="CASH_OR_INSTALLMENT",
        raw_location="경기 수원",
        vehicle_fingerprint="OTHER_02",
        observed_at=t2,
        data_origin="REAL_OBSERVED",
    )
    res_part = pipeline.execute_batch(records=[other_r], session=session, batch_id="B2_PARTIAL", scope=scope, observation_time=t2, is_partial_scrape=True)
    session.commit()

    assert res_part.delisted_suspect_count == 0
    # 누락 카운터가 0으로 안전하게 동결 보존되어야 함 (섣부른 판매종료 오판 방지)
    session.refresh(listing)
    assert listing.consecutive_missing_count == 0
    assert listing.current_status == "ACTIVE"


def test_source_code_has_no_db_unlink_in_operational_scripts():
    """지침 4: 운영 수집 스크립트에 db_path.unlink() 또는 DB 삭제 로직이 완전히 0건인지 코드 정적 검증."""
    script_path = Path("scripts/run_directive_010_market_stream.py")
    assert script_path.exists()
    content = script_path.read_text(encoding="utf-8")

    # 운영 DB(db_path)에 대한 unlink 호출 금지 검증
    assert "db_path.unlink()" not in content, "운영 DB 삭제 로직(db_path.unlink())이 코드에 존재합니다!"
    assert "os.remove(db_path)" not in content, "운영 DB 삭제 로직(os.remove)이 코드에 존재합니다!"
