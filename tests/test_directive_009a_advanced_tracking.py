"""DIRECTIVE 009-A 가격 변동 추적 엔진 고급 무결성 및 멱등성 검증 테스트."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from chaficial.database.base import Base
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.platforms.base import StandardListingRecord
from chaficial.tracker.price_tracker import PriceEventTracker


@pytest.fixture
def db_session():
    """인메모리 SQLite 격리 테스트 DB 세션."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def test_009a_price_null_snapshot_preservation(db_session: Session):
    """시나리오 1: 가격 미확인/금융상품 매물의 가격이 0원이 아닌 NULL로 DB에 안전 저장·조회되는지 검증."""
    tracker = PriceEventTracker()
    now = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    rec_null_price = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="NULL_PRICE_CAR",
        product_type="RENT",
        price_krw=None,
        monthly_payment_krw=280000,
        mileage_km=40334,
        observed_at=now,
    )
    tracker.process_observation(rec_null_price, db_session)
    db_session.commit()

    snap = db_session.execute(
        select(ListingSnapshot).where(ListingSnapshot.mileage_km == 40334)
    ).scalar_one()

    # 0원이 아닌 반드시 None (NULL)이어야 함!
    assert snap.price_krw is None
    assert snap.price_krw != 0


def test_009a_financial_product_price_event_blocking(db_session: Session):
    """시나리오 2: 금융상품(렌트/리스) 매물이 월납입액 변동 시 차량 가격 인하 이벤트로 오인되지 않는지 검증."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)

    rec1 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="RENT_CAR_01",
        product_type="RENT",
        price_krw=None,
        monthly_payment_krw=280000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(rec1, db_session)

    # 렌트료가 25만원으로 인하되었더라도 차량 총매매가 이벤트(PRICE_DROP)가 발생하면 안 됨!
    rec2 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="RENT_CAR_01",
        product_type="RENT",
        price_krw=None,
        monthly_payment_krw=250000,
        mileage_km=30100,
        observed_at=t1,
    )
    ev = tracker.process_observation(rec2, db_session)
    assert ev is None


def test_009a_idempotency_duplicate_batch_reexecution(db_session: Session):
    """시나리오 3: 동일 배치 재실행 시 스냅샷 및 가격 이벤트 중복 0건 (멱등성 Idempotency) 검증."""
    tracker = PriceEventTracker()
    now = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="IDEMPOTENT_CAR",
        price_krw=15000000,
        mileage_km=50000,
        observed_at=now,
    )

    # 1회차 실행
    ev1 = tracker.process_observation(rec, db_session)
    assert ev1 is not None

    # 2회차 재실행 (동일 레코드 재입력)
    ev2 = tracker.process_observation(rec, db_session)
    # 중복 이벤트 생성 차단 (None 반환)
    assert ev2 is None

    # DB 스냅샷 개수가 1개로 유지되는지 검증
    snaps = db_session.execute(
        select(ListingSnapshot).join(Listing).where(Listing.source_listing_id == "IDEMPOTENT_CAR")
    ).scalars().all()
    assert len(snaps) == 1


def test_009a_out_of_order_historical_observation(db_session: Session):
    """시나리오 5: 과거 시점 데이터 지연 입력(Out-of-order) 시 현재 최신 가격 상태를 덮어쓰지 않는지 검증."""
    tracker = PriceEventTracker()
    t_latest = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
    t_past = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)

    # 1. 10월 20일 관측 (현재 가격 1,400만원)
    rec_latest = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="TIME_TRAVEL_CAR",
        price_krw=14000000,
        mileage_km=50000,
        observed_at=t_latest,
    )
    tracker.process_observation(rec_latest, db_session)

    # 2. 뒤늦게 10월 10일 과거 관측 데이터(1,500만원)가 지연 유입됨
    rec_past = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="TIME_TRAVEL_CAR",
        price_krw=15000000,
        mileage_km=49000,
        observed_at=t_past,
    )
    ev_past = tracker.process_observation(rec_past, db_session)
    # 과거 데이터 지연 유입으로 현재 가격이 인상된 것으로 오판단하지 않아야 함!
    assert ev_past is None

    # 최신 스냅샷(10월 20일)의 가격(1,400만원)이 안전하게 유지되는지 검증
    latest_snap = db_session.execute(
        select(ListingSnapshot).join(Listing)
        .where(Listing.source_listing_id == "TIME_TRAVEL_CAR")
        .order_by(ListingSnapshot.observed_at.desc())
    ).scalars().first()
    assert latest_snap.price_krw == 14000000


def test_009a_consecutive_missing_threshold_and_delisted_suspect(db_session: Session):
    """시나리오 6: 1회·2회 누락 시 ACTIVE 유지, 3회 연속 누락 시 DELISTED_SUSPECT 전이 검증."""
    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="MISSING_TRACK_CAR",
        price_krw=16000000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(rec, db_session)

    listing = db_session.execute(
        select(Listing).where(Listing.source_listing_id == "MISSING_TRACK_CAR")
    ).scalar_one()

    # 1회 누락 관측 배치 (MISSING_TRACK_CAR 미포함)
    events_m1 = tracker.process_missing_listings(
        observed_source_listing_ids=set(),
        session=db_session,
        observation_time=datetime(2026, 10, 2, 10, 0, tzinfo=UTC),
        batch_id="TEST_009A_BATCH_01",
        search_scope_success=True,
    )
    assert len(events_m1) == 0
    assert listing.consecutive_missing_count == 1
    assert listing.current_status == "ACTIVE"

    # 2회 누락 관측 배치
    events_m2 = tracker.process_missing_listings(
        observed_source_listing_ids=set(),
        session=db_session,
        observation_time=datetime(2026, 10, 3, 10, 0, tzinfo=UTC),
        batch_id="TEST_009A_BATCH_02",
        search_scope_success=True,
    )
    assert len(events_m2) == 0
    assert listing.consecutive_missing_count == 2
    assert listing.current_status == "ACTIVE"

    # 3회 연속 누락 관측 배치 -> DELISTED_SUSPECT 전이 및 이벤트 발생!
    events_m3 = tracker.process_missing_listings(
        observed_source_listing_ids=set(),
        session=db_session,
        observation_time=datetime(2026, 10, 4, 10, 0, tzinfo=UTC),
        batch_id="TEST_009A_BATCH_03",
        search_scope_success=True,
    )
    assert len(events_m3) == 1
    assert events_m3[0].event_type == "DELISTED_SUSPECT"
    assert listing.consecutive_missing_count == 3
    assert listing.current_status == "DELISTED_SUSPECT"


def test_009a_search_failure_preserves_missing_counter(db_session: Session):
    """시나리오 7, 8: 수집 실패/일부 페이지 누락(search_scope_success=False) 시 누락 카운터 증가 방지 검증."""
    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    now = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="SCRAPE_FAIL_TEST_CAR",
        price_krw=15000000,
        mileage_km=40000,
        observed_at=now,
    )
    tracker.process_observation(rec, db_session)
    listing = db_session.execute(select(Listing).where(Listing.source_listing_id == "SCRAPE_FAIL_TEST_CAR")).scalar_one()
    assert listing.consecutive_missing_count == 0

    # 크롤러 실패 또는 검색 차단 발생 (search_scope_success=False)
    tracker.process_missing_listings(
        observed_source_listing_ids=set(),
        session=db_session,
        observation_time=now + timedelta(days=1),
        batch_id="TEST_009A_FAIL_BATCH_01",
        search_scope_success=False,
    )
    # 수집 실패 시에는 무고한 매물이 누락 처리되지 않도록 카운터가 0으로 보존되어야 함!
    assert listing.consecutive_missing_count == 0
    assert listing.current_status == "ACTIVE"


def test_009a_reappearance_resets_counter_and_creates_relisted_suspect(db_session: Session):
    """시나리오 9: 비노출(DELISTED_SUSPECT) 후 재등장 시 누락 카운터 초기화 및 RE_LISTED_SUSPECT 생성 검증."""
    tracker = PriceEventTracker(consecutive_missing_threshold=1)
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 10, 2, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="REAPPEAR_CAR",
        price_krw=17000000,
        mileage_km=20000,
        observed_at=t0,
    )
    tracker.process_observation(rec, db_session)

    # 1회 누락으로 비노출 전이
    tracker.process_missing_listings(
        observed_source_listing_ids=set(),
        session=db_session,
        observation_time=t1,
        batch_id="TEST_009A_REAPPEAR_BATCH_01",
        search_scope_success=True,
    )
    listing = db_session.execute(select(Listing).where(Listing.source_listing_id == "REAPPEAR_CAR")).scalar_one()
    assert listing.current_status == "DELISTED_SUSPECT"

    # 다시 시장에 재등장 관측!
    rec_reappear = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="REAPPEAR_CAR",
        price_krw=17000000,
        mileage_km=20050,
        observed_at=t2,
    )
    ev_reappear = tracker.process_observation(rec_reappear, db_session)
    assert ev_reappear is not None
    assert ev_reappear.event_type == "RE_LISTED_SUSPECT"
    assert listing.current_status == "ACTIVE"
    assert listing.consecutive_missing_count == 0


def test_009a_real_observed_vs_simulated_separation(db_session: Session):
    """시나리오 11: 실제 관측(REAL_OBSERVED)과 시뮬레이션(SIMULATED)의 통계적 격리 검증."""
    tracker = PriceEventTracker()
    now = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    # 1. 실제 관측 매물
    rec_real = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="REAL_CAR_01",
        price_krw=15000000,
        mileage_km=40000,
        data_origin="REAL_OBSERVED",
        observed_at=now,
    )
    tracker.process_observation(rec_real, db_session, data_origin="REAL_OBSERVED")

    # 2. 시뮬레이션 가격 인하 매물
    rec_sim1 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="SIM_CAR_01",
        price_krw=15000000,
        mileage_km=40000,
        data_origin="SIMULATED",
        observed_at=now,
    )
    tracker.process_observation(rec_sim1, db_session, data_origin="SIMULATED")

    rec_sim2 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="SIM_CAR_01",
        price_krw=14000000,
        mileage_km=40000,
        data_origin="SIMULATED",
        observed_at=now + timedelta(days=2),
    )
    tracker.process_observation(rec_sim2, db_session, data_origin="SIMULATED")
    db_session.commit()

    # 실제 관측 기반 가격 인하는 0건이어야 함!
    real_drops = PriceEventTracker.get_price_drops_summary(db_session, window_days=7, data_origin="REAL_OBSERVED")
    assert len(real_drops) == 0

    # 시뮬레이션 기반 가격 인하는 1건으로 정확히 분리 조회되어야 함!
    sim_drops = PriceEventTracker.get_price_drops_summary(db_session, window_days=7, data_origin="SIMULATED")
    assert len(sim_drops) == 1
    assert sim_drops[0]["price_drop_krw"] == 1000000


def test_009a_cumulative_price_delta_drop_then_increase(db_session: Session):
    """시나리오 12: 1,500만원 -> 1,450만원 인하 후 -> 1,480만원 인상 시 누적 변동액(-20만원) 정밀 계산 검증."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 10, 3, 10, 0, tzinfo=UTC)
    t2 = datetime(2026, 10, 6, 10, 0, tzinfo=UTC)

    # 1차: 1,500만원
    r0 = StandardListingRecord(source_platform="ENCAR", source_listing_id="CUMULATIVE_CAR", price_krw=15000000, mileage_km=30000, observed_at=t0)
    tracker.process_observation(r0, db_session)

    # 2차: 1,450만원 (50만원 인하)
    r1 = StandardListingRecord(source_platform="ENCAR", source_listing_id="CUMULATIVE_CAR", price_krw=14500000, mileage_km=30050, observed_at=t1)
    ev_drop = tracker.process_observation(r1, db_session)
    assert ev_drop.price_delta_krw == -500000
    assert ev_drop.cumulative_delta_krw == -500000

    # 3차: 1,480만원 (30만원 인상)
    r2 = StandardListingRecord(source_platform="ENCAR", source_listing_id="CUMULATIVE_CAR", price_krw=14800000, mileage_km=30100, observed_at=t2)
    ev_increase = tracker.process_observation(r2, db_session)
    assert ev_increase.price_delta_krw == 300000  # 직전(1,450만) 대비 +30만원
    assert ev_increase.cumulative_delta_krw == -200000  # 최초(1,500만) 대비 -20만원 누적 인하!
    assert ev_increase.cumulative_delta_pct == -1.33
