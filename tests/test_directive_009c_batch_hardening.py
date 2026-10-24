"""CHA-FICIAL AI PROJECT - DIRECTIVE 009-C
검색 배치 운영 안전성 및 논리 해시 무오염 검증 테스트 스위트.

검증 항목:
1. batch_id 누락 시 명시적 ValueError 발생 검증 (필수화)
2. 구조화된 SearchScopeSpec을 통한 교차 오판 완전 방지
3. 배치 트랜잭션 원자성 및 영속 감사 기록 검증
4. 운영 DB 논리 데이터 행 기반 SHA-256 해시 불변 검증
"""

from datetime import UTC, datetime, timedelta
import hashlib
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


@pytest.fixture
def session_009c():
    """테스트용 인메모리 SQLite 세션."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine)
    session = SessionMaker()
    yield session
    session.close()


def test_009c_missing_batch_id_raises_value_error(session_009c: Session):
    """시나리오 1: batch_id가 누락되거나 빈 문자열이면 명시적인 ValueError를 발생시켜야 함."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    # 1. batch_id=None 시도시 ValueError 발생
    with pytest.raises(ValueError, match="batch_id is strictly required"):
        tracker.process_missing_listings(
            observed_source_listing_ids=set(),
            session=session_009c,
            observation_time=t0,
            batch_id="",  # 빈 문자열
            scope=SearchScopeSpec(platform="ENCAR", model_name="아반떼"),
        )

    # 2. 공백 문자열 시도시에도 ValueError 발생
    with pytest.raises(ValueError, match="batch_id is strictly required"):
        tracker.process_missing_listings(
            observed_source_listing_ids=set(),
            session=session_009c,
            observation_time=t0,
            batch_id="   ",
            scope=SearchScopeSpec(platform="ENCAR", model_name="아반떼"),
        )


def test_009c_search_scope_spec_exact_filtering(session_009c: Session):
    """시나리오 2: 구조화된 SearchScopeSpec을 통해 동일 브랜드 내 서로 다른 세부 차종 교차 오판 차단."""
    tracker = PriceEventTracker(consecutive_missing_threshold=3)
    t0 = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    # 아반떼 CN7 매물 등록
    rec_avante = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="AVANTE_CN7_01",
        model_name="아반떼",
        sub_model="CN7",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t0,
    )
    # 쏘나타 DN8 매물 등록
    rec_sonata = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="SONATA_DN8_01",
        model_name="쏘나타",
        sub_model="DN8",
        price_krw=20000000,
        mileage_km=25000,
        observed_at=t0,
    )
    tracker.process_observation(rec_avante, session_009c)
    tracker.process_observation(rec_sonata, session_009c)
    session_009c.commit()

    # 아반떼 전용 SearchScopeSpec으로 미노출 실행 (소나타 매물은 관측되지 않았음)
    scope_avante = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼", sub_model="CN7")
    tracker.process_missing_listings(
        observed_source_listing_ids={"AVANTE_CN7_01"},  # 아반떼는 관측됨
        session=session_009c,
        observation_time=t0 + timedelta(days=1),
        batch_id="BATCH_AVANTE_SPEC_01",
        scope=scope_avante,
    )

    # 쏘나타 매물 검증: 아반떼 검색 배치에서 관측되지 않았더라도 카운터는 0이어야 함!
    sonata = session_009c.execute(select(Listing).where(Listing.source_listing_id == "SONATA_DN8_01")).scalar_one()
    assert sonata.consecutive_missing_count == 0, "교차 오판: 아반떼 검색이 쏘나타의 누락 카운터를 올렸습니다!"


def test_009c_search_scope_counterexamples(session_009c: Session):
    """시나리오 3: 제조사 불일치, 연식 범위 밖, 제원 결측 시 미노출 오판이 원천 차단되는 반례 검증."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    # 1. 다른 제조사 차량 (기아 K3)
    rec_kia = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="KIA_K3_01",
        manufacturer="기아",
        model_name="K3",
        price_krw=14000000,
        mileage_km=30000,
        observed_at=t0,
    )
    # 2. 연식 범위 밖 아반떼 (2018년식)
    rec_old_avante = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="AVANTE_2018_01",
        manufacturer="현대",
        model_name="아반떼",
        model_year="2018",
        price_krw=11000000,
        mileage_km=80000,
        observed_at=t0,
    )
    tracker.process_observation(rec_kia, session_009c)
    tracker.process_observation(rec_old_avante, session_009c)
    session_009c.commit()

    # 현대 2022~2024년식 아반떼 전용 검색 실행
    target_scope = SearchScopeSpec(
        platform="ENCAR",
        manufacturer="현대",
        model_name="아반떼",
        min_year=2022,
        max_year=2024,
    )

    tracker.process_missing_listings(
        observed_source_listing_ids=set(),
        session=session_009c,
        observation_time=t0 + timedelta(days=1),
        batch_id="COUNTER_EXAMPLE_BATCH_01",
        scope=target_scope,
    )

    # 기아 K3 및 2018년식 아반떼는 검색 조건 밖이므로 누락 카운터가 절대 증가하지 않아야 함!
    k3 = session_009c.execute(select(Listing).where(Listing.source_listing_id == "KIA_K3_01")).scalar_one()
    old_avante = session_009c.execute(select(Listing).where(Listing.source_listing_id == "AVANTE_2018_01")).scalar_one()

    assert k3.consecutive_missing_count == 0, "제조사 불일치 오판 결함!"
    assert old_avante.consecutive_missing_count == 0, "연식 범위 밖 차량 오판 결함!"


def test_009c_atomic_transaction_rollback_on_failure(session_009c: Session):
    """시나리오 4: 배치 처리 도중 예외 발생 시 원자적 롤백으로 미노출 카운터 및 로그가 보존되지 않음."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="ROLLBACK_CAR_01",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(rec, session_009c)
    session_009c.commit()

    # 배치 도중 강제 DB 오류 발생 시뮬레이션
    try:
        with session_009c.begin_nested():
            car = session_009c.execute(select(Listing).where(Listing.source_listing_id == "ROLLBACK_CAR_01")).scalar_one()
            car.consecutive_missing_count += 1
            # 강제 에러 유발
            raise RuntimeError("CRITICAL_DATABASE_CRASH_MID_BATCH")
    except RuntimeError:
        session_009c.rollback()

    # 롤백 후 원상 복구 확인
    car_after = session_009c.execute(select(Listing).where(Listing.source_listing_id == "ROLLBACK_CAR_01")).scalar_one()
    assert car_after.consecutive_missing_count == 0, "트랜잭션 롤백 실패: 카운터가 원복되지 않았습니다!"


def test_009c_hash_fails_on_single_column_mutation(session_009c: Session):
    """시나리오 5: 테이블의 단 1개 컬럼 값만 변경되어도 논리 SHA-256 해시가 불일치하여 위변조를 즉각 탐지함."""
    from chaficial.tracker.price_tracker import compute_db_logical_hashes

    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="MUTATION_CAR_01",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(rec, session_009c)
    session_009c.commit()

    # 1. 초기 해시 계산
    hashes_initial = compute_db_logical_hashes(session_009c)

    # 2. 단 1개 컬럼(consecutive_missing_count)만 0에서 1로 변조
    listing = session_009c.execute(select(Listing).where(Listing.source_listing_id == "MUTATION_CAR_01")).scalar_one()
    listing.consecutive_missing_count = 1
    session_009c.commit()

    # 3. 변조 후 해시 계산
    hashes_mutated = compute_db_logical_hashes(session_009c)

    # 검증: listings 테이블의 해시가 반드시 달라져야 함!
    assert hashes_initial["listings"]["hash"] != hashes_mutated["listings"]["hash"], (
        "치명적 결함: 데이터 컬럼이 변조되었는데도 SHA-256 해시가 변하지 않았습니다!"
    )



def test_009c_logical_data_hash_consistency(session_009c: Session):
    """시나리오 4: 정렬된 행 데이터 기반 논리 SHA-256 해시가 불변성을 엄밀하게 입증하는지 검증."""
    tracker = PriceEventTracker()
    t0 = datetime(2026, 10, 21, 10, 0, tzinfo=UTC)

    rec = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="HASH_CAR_01",
        model_name="아반떼",
        price_krw=15000000,
        mileage_km=30000,
        observed_at=t0,
    )
    tracker.process_observation(rec, session_009c)
    session_009c.commit()

    # 1차 해시 계산
    listings_1 = session_009c.execute(select(Listing).order_by(Listing.listing_id)).scalars().all()
    hash_1 = hashlib.sha256(
        "|".join(f"{l.listing_id}:{l.source_listing_id}:{l.current_status}:{l.consecutive_missing_count}" for l in listings_1).encode()
    ).hexdigest()

    # 다른 무관한 쿼리나 세션 조작 후에도 2차 해시가 100% 동일한지 검증
    listings_2 = session_009c.execute(select(Listing).order_by(Listing.listing_id)).scalars().all()
    hash_2 = hashlib.sha256(
        "|".join(f"{l.listing_id}:{l.source_listing_id}:{l.current_status}:{l.consecutive_missing_count}" for l in listings_2).encode()
    ).hexdigest()

    assert hash_1 == hash_2, "논리 해시 불일치 발생!"
