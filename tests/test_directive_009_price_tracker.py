"""DIRECTIVE 009 가격 변동 추적 엔진 통제 시계열 검증 테스트."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
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


def test_case_1_price_drop_event(db_session: Session):
    """검증 1: 1,500만원 -> 1,450만원 변경 시 50만원 인하(PRICE_DROP) 이벤트 1건 생성 검증."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 10, 3, 14, 0, tzinfo=UTC)

    rec_initial = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_001",
        price_krw=15000000,
        mileage_km=40000,
        product_type="CASH_OR_INSTALLMENT",
        observed_at=t0,
    )
    ev0 = tracker.process_observation(rec_initial, db_session)
    assert ev0 is not None
    assert ev0.event_type == "NEW_LISTING"
    assert ev0.new_price_krw == 15000000

    # 1,450만원으로 인하된 2차 관측
    rec_dropped = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_001",
        price_krw=14500000,
        mileage_km=40050,
        product_type="CASH_OR_INSTALLMENT",
        observed_at=t1,
    )
    ev1 = tracker.process_observation(rec_dropped, db_session)
    assert ev1 is not None
    assert ev1.event_type == "PRICE_DROP"
    assert ev1.previous_price_krw == 15000000
    assert ev1.new_price_krw == 14500000
    assert ev1.price_delta_krw == -500000
    assert ev1.price_delta_pct == -3.33
    assert ev1.cumulative_delta_krw == -500000
    assert ev1.days_since_first_observed == 2


def test_case_2_duplicate_price_no_event(db_session: Session):
    """검증 2: 1,450만원 재관측 시 가격 변동 이벤트 0건 검증 (중복 이벤트 생성 차단)."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 10, 2, 10, 0, tzinfo=UTC)

    rec1 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_002",
        price_krw=14500000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(rec1, db_session)

    # 동일한 1,450만원 재관측
    rec2 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_002",
        price_krw=14500000,
        mileage_km=30000,
        observed_at=t1,
    )
    ev_duplicate = tracker.process_observation(rec2, db_session)
    # 동일 가격 재수집 시 가격 이벤트는 None이어야 함!
    assert ev_duplicate is None


def test_case_3_price_increase_event(db_session: Session):
    """검증 3: 1,450만원 -> 1,480만원 변경 시 30만원 인상(PRICE_INCREASE) 이벤트 1건 생성 검증."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)

    rec_base = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_003",
        price_krw=14500000,
        mileage_km=50000,
        observed_at=t0,
    )
    tracker.process_observation(rec_base, db_session)

    # 1,480만원으로 인상된 관측
    rec_increased = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_003",
        price_krw=14800000,
        mileage_km=50100,
        observed_at=t1,
    )
    ev_increase = tracker.process_observation(rec_increased, db_session)
    assert ev_increase is not None
    assert ev_increase.event_type == "PRICE_INCREASE"
    assert ev_increase.previous_price_krw == 14500000
    assert ev_increase.new_price_krw == 14800000
    assert ev_increase.price_delta_krw == 300000
    assert ev_increase.price_delta_pct == 2.07


def test_case_4_single_missing_observation_no_premature_delisting(db_session: Session):
    """검증 4: 1회 검색 누락만으로 섣부른 판매 완료(DELISTED) 판정 금지 검증."""
    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_004",
        price_krw=16000000,
        mileage_km=25000,
        observed_at=t0,
    )
    tracker.process_observation(rec, db_session)

    # 1회 누락 시에도 매물 상태는 ACTIVE를 유지해야 함
    listing = db_session.query(Listing).filter_by(source_listing_id="CAR_004").one()
    assert listing.current_status == "ACTIVE"
    assert listing.current_status != "DELISTED"


def test_case_5_monthly_payment_never_treated_as_total_price(db_session: Session):
    """검증 5: 월납입 19만원 렌트 매물을 차량 총가격 19만원으로 처리하지 않는지 검증."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)

    rec_financial = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_RENT_005",
        product_type="RENT",
        price_krw=None,
        monthly_payment_krw=190000,
        mileage_km=35000,
        observed_at=t0,
    )
    ev = tracker.process_observation(rec_financial, db_session)
    assert ev is not None
    assert ev.product_type == "RENT"
    # 총 매매가격은 190,000원이 아닌 None이어야 함!
    assert ev.new_price_krw is None
    assert ev.price_delta_krw == 0


def test_case_6_mileage_change_preserves_listing_timeseries(db_session: Session):
    """검증 6: 주행거리 변경(40,000km -> 41,000km) 시 동일 listing_id의 시계열 유지 검증."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)

    rec_t0 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_006",
        price_krw=17000000,
        mileage_km=40000,
        observed_at=t0,
    )
    tracker.process_observation(rec_t0, db_session)

    # 주행거리만 41,000km로 증가하고 가격은 1,700만원 그대로인 관측
    rec_t1 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_006",
        price_krw=17000000,
        mileage_km=41000,
        observed_at=t1,
    )
    ev = tracker.process_observation(rec_t1, db_session)
    # 가격 변동이 없으므로 가격 이벤트는 None
    assert ev is None

    # 하지만 동일 listing_id 아래에 2개의 시계열 스냅샷이 누적 보존되어야 함!
    listing = db_session.query(Listing).filter_by(source_listing_id="CAR_006").one()
    snapshots = (
        db_session.query(ListingSnapshot)
        .filter_by(listing_id=listing.listing_id)
        .order_by(ListingSnapshot.observed_at.asc())
        .all()
    )
    assert len(snapshots) == 2
    assert snapshots[0].mileage_km == 40000
    assert snapshots[1].mileage_km == 41000
    assert snapshots[0].price_krw == 17000000
    assert snapshots[1].price_krw == 17000000
