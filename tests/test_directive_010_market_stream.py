"""CHA-FICIAL AI PROJECT - DIRECTIVE 010
실제 시장 반복 관측 스트림 파이프라인 단위 테스트 스위트.

검증 항목:
1. 3개 시점 독립 관측 배치 순차 누적 및 FIRST_SEEN / 재관측 집계
2. 1회 미노출 매물의 ACTIVE 상태 유지 및 섣부른 DELISTED_SUSPECT 차단
3. 동일 가격 재수집 시 PRICE_DROP/PRICE_INCREASE 이벤트 0건 멱등성
4. UTC 저장 및 KST(UTC+9) 문자열 변환 정확도
5. 실제 시장 가격 변동 0건의 과학적·운영적 정직성 검증
6. StreamPipeline의 batch_id 멱등성(중복 실행 방지)
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from chaficial.database.base import Base
from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.platforms.base import StandardListingRecord
from chaficial.tracker.price_tracker import PriceEventTracker, SearchScopeSpec
from chaficial.tracker.stream_pipeline import MarketObservationStreamPipeline


@pytest.fixture
def session_010():
    """테스트용 인메모리 SQLite 세션."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()
    yield session
    session.close()


def test_010_three_batches_cumulative_execution(session_010: Session):
    """시나리오 1: 3개 시점 독립 배치 실행 및 FIRST_SEEN / 재관측 카운트 집계 검증."""
    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")
    t1 = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)

    # 1차 배치: 매물 2건 최초 등록
    b1_records = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="CN7_01",
            model_name="아반떼",
            price_krw=15000000,
            mileage_km=30000,
            observed_at=t1,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="CN7_02",
            model_name="아반떼",
            price_krw=16000000,
            mileage_km=25000,
            observed_at=t1,
        ),
    ]
    res1 = pipeline.execute_batch(b1_records, session_010, "BATCH_01", scope, observation_time=t1)
    session_010.commit()
    assert res1.total_records_ingested == 2
    assert res1.first_seen_count == 2
    assert res1.re_observed_count == 0

    # 2차 배치: 동일 매물 2건 재관측
    t2 = t1 + timedelta(hours=5)
    res2 = pipeline.execute_batch(b1_records, session_010, "BATCH_02", scope, observation_time=t2)
    session_010.commit()
    assert res2.total_records_ingested == 2
    assert res2.first_seen_count == 0
    assert res2.re_observed_count == 2

    # 3차 배치: CN7_01만 재관측 + 신규 CN7_03 진입
    t3 = t1 + timedelta(days=1)
    b3_records = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="CN7_01",
            model_name="아반떼",
            price_krw=15000000,
            mileage_km=30050,
            observed_at=t3,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="CN7_03",
            model_name="아반떼",
            price_krw=17000000,
            mileage_km=15000,
            observed_at=t3,
        ),
    ]
    res3 = pipeline.execute_batch(b3_records, session_010, "BATCH_03", scope, observation_time=t3)
    session_010.commit()
    assert res3.first_seen_count == 1
    assert res3.re_observed_count == 1


def test_010_single_missing_keeps_active(session_010: Session):
    """시나리오 2: 1회 검색 미노출 매물은 consecutive_missing_count: 1을 기록하고 ACTIVE 상태를 유지해야 함."""
    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")
    t1 = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="MISSING_CAR_1X",
        manufacturer="현대",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t1,
    )
    pipeline.execute_batch([rec], session_010, "BATCH_B1", scope, observation_time=t1)
    session_010.commit()

    # 2차 배치에서 MISSING_CAR_1X 누락 (빈 수집)
    t2 = t1 + timedelta(days=1)
    res = pipeline.execute_batch([], session_010, "BATCH_B2", scope, observation_time=t2)
    session_010.commit()

    assert res.delisted_suspect_count == 0  # 1회 누락만으로는 DELISTED_SUSPECT가 아님!
    car = session_010.execute(select(Listing).where(Listing.source_listing_id == "MISSING_CAR_1X")).scalar_one()
    assert car.consecutive_missing_count == 1
    assert car.current_status == "ACTIVE", "1회 누락 매물이 DELISTED_SUSPECT로 오판되었습니다!"


def test_010_identical_price_no_price_event(session_010: Session):
    """시나리오 3: 동일 가격 재관측 시 가격 변동 이벤트(PRICE_DROP, PRICE_INCREASE) 0건 검증."""
    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")
    t1 = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="SAME_PRICE_CAR",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t1,
    )
    pipeline.execute_batch([rec], session_010, "BATCH_S1", scope, observation_time=t1)
    session_010.commit()

    # 동일 가격 재관측
    t2 = t1 + timedelta(hours=3)
    res = pipeline.execute_batch([rec], session_010, "BATCH_S2", scope, observation_time=t2)
    session_010.commit()

    assert res.price_drop_count == 0
    assert res.price_increase_count == 0

    events = session_010.execute(select(PriceEvent).where(PriceEvent.source_listing_id == "SAME_PRICE_CAR")).scalars().all()
    ev_types = [e.event_type for e in events]
    assert ev_types == ["NEW_LISTING"]  # 최초 등록 외에 추가 가격 변동 이벤트 없음!


def test_010_kst_string_formatting():
    """시나리오 4: UTC datetime의 한국표준시(KST, UTC+9) 문자열 정확 변환 검증."""
    pipeline = MarketObservationStreamPipeline()
    utc_time = datetime(2026, 10, 21, 9, 0, 0, tzinfo=UTC)
    kst_str = pipeline.to_kst_string(utc_time)
    assert kst_str == "2026-10-21 18:00:00 KST"


def test_010_real_price_delta_zero_reporting(session_010: Session):
    """시나리오 5: 실제 시장 가격 변동이 0건일 때 인위적 조작 없이 0건으로 정직하게 보고됨을 검증."""
    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")
    t1 = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)

    recs = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id=f"REAL_CAR_{i}",
            model_name="아반떼",
            price_krw=14000000 + i * 500000,
            mileage_km=30000,
            observed_at=t1,
        )
        for i in range(5)
    ]
    res = pipeline.execute_batch(recs, session_010, "BATCH_R1", scope, observation_time=t1)
    session_010.commit()

    assert res.price_drop_count == 0
    assert res.price_increase_count == 0
    assert res.total_price_drop_krw == 0


def test_010_stream_pipeline_batch_id_idempotency(session_010: Session):
    """시나리오 6: 동일 batch_id를 가진 배치의 중복 호출 시 원자적 스킵 및 멱등성 검증."""
    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")
    t1 = datetime(2026, 10, 21, 9, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="IDEMPOTENT_CAR",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t1,
    )
    # 1차 실행
    res1 = pipeline.execute_batch([rec], session_010, "IDEMPOTENT_BATCH_KEY", scope, observation_time=t1)
    session_010.commit()
    assert res1.total_records_ingested == 1
    assert res1.first_seen_count == 1

    # 2차 중복 실행 (동일 batch_id)
    res2 = pipeline.execute_batch([rec], session_010, "IDEMPOTENT_BATCH_KEY", scope, observation_time=t1)
    assert res2.total_records_ingested == 0
    assert res2.notes == "ALREADY_PROCESSED_IDEMPOTENT_SKIP"
