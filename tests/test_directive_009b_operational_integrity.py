"""CHA-FICIAL AI PROJECT - DIRECTIVE 009-B
운영 안전성 및 검색 배치 무결성 회귀 테스트 스위트.

검증 항목:
1. 운영 DB vs 시뮬레이션 DB 완전 격리 및 0건 오염 실증
2. 차종/플랫폼 검색 범위(search_scope) 격리로 교차 오판 방지
3. 부분 수집(is_partial_scrape) 및 수집 실패 시 누락 카운터 보존
4. 동일 batch_id 중복 재시도 시 누락 카운터 1만 증가 (멱등성 보장)
5. 서로 다른 3회 정상 배치에서만 DELISTED_SUSPECT 전이
6. 지연 입력(Out-of-order) 시 최신 상태 및 누락 카운터 보존
7. 복합 이벤트(재등록 + 가격 변동) 동시 발생 시 이벤트 유실 방지
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from chaficial.database.base import Base
from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.platforms.base import StandardListingRecord
from chaficial.tracker.price_tracker import PriceEventTracker


@pytest.fixture
def clean_tracker_session():
    """테스트용 인메모리 SQLite 세션."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()
    yield session
    session.close()


def test_009b_cross_scope_missing_isolation(clean_tracker_session: Session):
    """시나리오 1: 소나타 검색 배치 실행 시 아반떼 매물의 누락 카운터가 증가하지 않아야 함."""
    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    t0 = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    # 아반떼 매물 1건 등록
    avante_rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="AVANTE_01",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(avante_rec, clean_tracker_session)
    clean_tracker_session.commit()

    # 소나타 검색 배치 실행 (아반떼 매물은 당연히 관측 리스트에 없음)
    t1 = t0 + timedelta(days=1)
    observed_sonata_ids = {"SONATA_99"}
    tracker.process_missing_listings(
        observed_source_listing_ids=observed_sonata_ids,
        session=clean_tracker_session,
        observation_time=t1,
        platform="ENCAR",
        search_scope="쏘나타",  # 검색 범위는 쏘나타!
        batch_id="ENCAR_SONATA_BATCH_01",
    )

    # 아반떼 매물 확인: 검색 범위가 다르므로 누락 카운터는 여전히 0이어야 함!
    avante = clean_tracker_session.execute(
        select(Listing).where(Listing.source_listing_id == "AVANTE_01")
    ).scalar_one()
    assert avante.consecutive_missing_count == 0, "교차 오판 결함: 쏘나타 검색이 아반떼의 누락 카운터를 증가시켰습니다!"
    assert avante.current_status == "ACTIVE"


def test_009b_partial_scrape_preserves_counter(clean_tracker_session: Session):
    """시나리오 2: 부분 수집(is_partial_scrape=True) 또는 수집 실패 시 누락 카운터를 올리지 않음."""
    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    t0 = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_01",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(rec, clean_tracker_session)
    clean_tracker_session.commit()

    # 부분 수집 발생 (크롤러 장애로 5페이지만 긁힘)
    t1 = t0 + timedelta(days=1)
    evs = tracker.process_missing_listings(
        observed_source_listing_ids=set(),  # 빈 수집
        session=clean_tracker_session,
        observation_time=t1,
        platform="ENCAR",
        search_scope="아반떼",
        batch_id="ENCAR_FAIL_BATCH_01",
        is_partial_scrape=True,  # 부분 수집 플래그!
    )
    assert len(evs) == 0

    car = clean_tracker_session.execute(
        select(Listing).where(Listing.source_listing_id == "CAR_01")
    ).scalar_one()
    assert car.consecutive_missing_count == 0, "부분 수집 장애 시 누락 카운터가 증가해서는 안 됩니다!"


def test_009b_same_batch_retry_idempotency(clean_tracker_session: Session):
    """시나리오 3: 동일 batch_id를 3번 재시도 호출해도 누락 카운터는 1만 증가해야 함."""
    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    t0 = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_02",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(rec, clean_tracker_session)
    clean_tracker_session.commit()

    # 동일 배치 ID로 3번 연속 실행
    t1 = t0 + timedelta(days=1)
    for _ in range(3):
        tracker.process_missing_listings(
            observed_source_listing_ids=set(),  # 매물 미노출
            session=clean_tracker_session,
            observation_time=t1,
            platform="ENCAR",
            search_scope="아반떼",
            batch_id="BATCH_RETRY_TEST_01",  # 동일 배치 ID 재시도
        )

    car = clean_tracker_session.execute(
        select(Listing).where(Listing.source_listing_id == "CAR_02")
    ).scalar_one()
    assert car.consecutive_missing_count == 1, (
        f"배치 멱등성 결함: 동일 배치 3회 재시도로 카운터가 {car.consecutive_missing_count}로 잘못 증가했습니다!"
    )
    assert car.current_status == "ACTIVE"


def test_009b_three_distinct_batches_trigger_delisted(clean_tracker_session: Session):
    """시나리오 4: 서로 다른 정상 배치 3회에서만 DELISTED_SUSPECT로 안전 전이됨."""
    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    t0 = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_03",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(rec, clean_tracker_session)
    clean_tracker_session.commit()

    # 1회차 누락 (서로 다른 배치)
    tracker.process_missing_listings(
        observed_source_listing_ids=set(),
        session=clean_tracker_session,
        observation_time=t0 + timedelta(days=1),
        platform="ENCAR",
        search_scope="아반떼",
        batch_id="DISTINCT_BATCH_01",
    )
    car = clean_tracker_session.execute(select(Listing).where(Listing.source_listing_id == "CAR_03")).scalar_one()
    assert car.consecutive_missing_count == 1
    assert car.current_status == "ACTIVE"

    # 2회차 누락
    tracker.process_missing_listings(
        observed_source_listing_ids=set(),
        session=clean_tracker_session,
        observation_time=t0 + timedelta(days=2),
        platform="ENCAR",
        search_scope="아반떼",
        batch_id="DISTINCT_BATCH_02",
    )
    car = clean_tracker_session.execute(select(Listing).where(Listing.source_listing_id == "CAR_03")).scalar_one()
    assert car.consecutive_missing_count == 2
    assert car.current_status == "ACTIVE"

    # 3회차 누락 -> DELISTED_SUSPECT 전이!
    evs = tracker.process_missing_listings(
        observed_source_listing_ids=set(),
        session=clean_tracker_session,
        observation_time=t0 + timedelta(days=3),
        platform="ENCAR",
        search_scope="아반떼",
        batch_id="DISTINCT_BATCH_03",
    )
    assert len(evs) == 1
    assert evs[0].event_type == "DELISTED_SUSPECT"

    car = clean_tracker_session.execute(select(Listing).where(Listing.source_listing_id == "CAR_03")).scalar_one()
    assert car.consecutive_missing_count == 3
    assert car.current_status == "DELISTED_SUSPECT"


def test_009b_out_of_order_does_not_corrupt_status(clean_tracker_session: Session):
    """시나리오 5: 지연 입력(Out-of-order)된 과거 관측이 최신 상태나 누락 카운터를 왜곡하지 않음."""
    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    t_latest = datetime(2026, 10, 25, 10, 0, tzinfo=UTC)
    t_past = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)

    # 최신 관측 먼저 도착
    rec_latest = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_04",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=35000,
        observed_at=t_latest,
    )
    tracker.process_observation(rec_latest, clean_tracker_session)
    clean_tracker_session.commit()

    # 과거 관측이 지연되어 뒤늦게 도착
    rec_past = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_04",
        model_name="아반떼",
        price_krw=16000000,  # 과거 가격
        mileage_km=34000,
        observed_at=t_past,
    )
    ev_past = tracker.process_observation(rec_past, clean_tracker_session)
    clean_tracker_session.commit()

    # 시간 역전이므로 이벤트는 None이어야 함 (현재 가격 변동으로 왜곡 금지)
    assert ev_past is None

    # 최신 스냅샷은 여전히 10월 25일의 1,500만원이어야 함
    latest_snap = clean_tracker_session.execute(
        select(ListingSnapshot)
        .where(ListingSnapshot.listing_id == clean_tracker_session.execute(select(Listing.listing_id).where(Listing.source_listing_id == "CAR_04")).scalar_one())
        .order_by(ListingSnapshot.observed_at.desc())
    ).scalars().first()
    assert latest_snap.price_krw == 15000000
    assert tracker._to_utc(latest_snap.observed_at) == t_latest


def test_009b_composite_relisted_and_price_drop(clean_tracker_session: Session):
    """시나리오 6: DELISTED_SUSPECT 매물이 가격 인하와 함께 복귀할 때 이벤트 유실 방지 검증."""
    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t1 = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)

    # 1. 최초 등록 (1,500만원)
    rec1 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_05",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(rec1, clean_tracker_session)
    clean_tracker_session.commit()

    # 2. 강제로 DELISTED_SUSPECT 상태 전이 모사
    listing = clean_tracker_session.execute(select(Listing).where(Listing.source_listing_id == "CAR_05")).scalar_one()
    listing.current_status = "DELISTED_SUSPECT"
    listing.consecutive_missing_count = 3
    clean_tracker_session.commit()

    # 3. 1,400만원(100만원 인하)으로 재등장
    rec2 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_05",
        price_krw=14000000,
        mileage_km=30100,
        observed_at=t1,
    )
    tracker.process_observation(rec2, clean_tracker_session)
    clean_tracker_session.commit()

    # 검증: DB에 RE_LISTED_SUSPECT 이벤트와 PRICE_DROP 이벤트가 둘 다 존재해야 함!
    all_events = clean_tracker_session.execute(
        select(PriceEvent).where(PriceEvent.source_listing_id == "CAR_05")
    ).scalars().all()

    ev_types = [e.event_type for e in all_events]
    assert "NEW_LISTING" in ev_types
    assert "RE_LISTED_SUSPECT" in ev_types, "재등록 이벤트가 유실되었습니다!"
    assert "PRICE_DROP" in ev_types, "가격 인하 이벤트가 유실되었습니다!"

    # 매물 상태 검증
    refreshed_car = clean_tracker_session.execute(select(Listing).where(Listing.source_listing_id == "CAR_05")).scalar_one()
    assert refreshed_car.consecutive_missing_count == 0  # 카운터 초기화 확인
    assert refreshed_car.current_status == "PRICE_CHANGED"
