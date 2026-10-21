"""DIRECTIVE 006: 전국 중고차 매물 분석 및 기회 점수 산정(Opportunity Scorer) 검증 테스트."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from chaficial.database.base import Base
from chaficial.models.listing import Listing
from chaficial.models.snapshot import ListingSnapshot
from chaficial.pipeline.ingest_and_score import OpportunityPipeline
from chaficial.platforms.base import PlatformUrlParser, StandardListingRecord
from chaficial.scorer.opportunity import OpportunityScorer


@pytest.fixture
def test_db_session():
    """인메모리 격리 SQLite 테스트 세션."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_platform_url_parser():
    """엔카, KB차차차, KCar URL 파서 식별 및 매물 ID 추출 검증."""
    # 1. 엔카 쿼리 파라미터형
    p1, id1 = PlatformUrlParser.extract_source_id("https://car.encar.com/detail?carid=38291021")
    assert p1 == "ENCAR"
    assert id1 == "38291021"

    # 2. KB차차차 carSeq형
    p2, id2 = PlatformUrlParser.extract_source_id(
        "https://www.kbchachacha.com/public/car/detail.kbc?carSeq=24901823"
    )
    assert p2 == "KB_CHACHACHA"
    assert id2 == "24901823"

    # 3. KCar i_sCarCd형
    p3, id3 = PlatformUrlParser.extract_source_id(
        "https://www.kcar.com/bc/detail/carSearchDetail?i_sCarCd=EC60812929"
    )
    assert p3 == "KCAR"
    assert id3 == "EC60812929"


def test_opportunity_scorer_insufficient_samples():
    """표본 수가 최소 기준(3대) 미만일 때 억지 점수를 계산하지 않고 INSUFFICIENT_DATA를 반환하는지 검증."""
    now = datetime.now(UTC)
    target = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="SINGLE_01",
        source_url=None,
        seller_reference="D1",
        manufacturer="제네시스",
        model_name="GV70",
        model_generation="JK1",
        trim_name="가솔린2.5터보",
        model_year=2022,
        mileage_km=29000,
        fuel_type="가솔린",
        transmission="자동",
        price_krw=41500000,
        raw_location="서울 서초구",
        accident_state="NO_ACCIDENT",
        has_inspection_record=True,
        observed_at=now,
    )

    # 표본 2대만 제공
    cohort = [
        target,
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="SINGLE_02",
            source_url=None,
            seller_reference="D2",
            manufacturer="제네시스",
            model_name="GV70",
            model_generation="JK1",
            trim_name="가솔린2.5터보",
            model_year=2022,
            mileage_km=35000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=43000000,
            raw_location="경기 수원시",
            accident_state="NO_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        ),
    ]

    res = OpportunityScorer.evaluate_listing(target, cohort)
    assert res.evaluation_status == "INSUFFICIENT_DATA"
    assert res.opportunity_score is None
    assert "표본 부족" in res.selection_reason
    assert res.sample_count == 1  # Leave-One-Out: 대상 제외 후 1대


def test_opportunity_scorer_comprehensive_evaluation():
    """충분한 표본(4대)에서 상태 보정 및 기회 점수가 합리적으로 산출되는지 검증."""
    now = datetime.now(UTC)
    # 동일군: 아반떼 CN7 모던 2021년식 가솔린 (중앙가격: 15,150,000원 / 중앙주행: 48,000km)
    records = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="AV_01",
            source_url=None,
            seller_reference=None,
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            trim_name="모던",
            model_year=2021,
            mileage_km=20000,  # 매우 짧음
            fuel_type="가솔린",
            transmission="자동",
            price_krw=14000000,  # 저렴함
            raw_location="서울 장안평",
            accident_state="NO_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="AV_02",
            source_url=None,
            seller_reference=None,
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            trim_name="모던",
            model_year=2021,
            mileage_km=45000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=15000000,
            raw_location="경기 수원",
            accident_state="NO_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        ),
        StandardListingRecord(
            source_platform="KB",
            source_listing_id="AV_03",
            source_url=None,
            seller_reference=None,
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            trim_name="모던",
            model_year=2021,
            mileage_km=52000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=15300000,
            raw_location="인천 서구",
            accident_state="SIMPLE_REPAIR",
            has_inspection_record=True,
            observed_at=now,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="AV_04",
            source_url=None,
            seller_reference=None,
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            trim_name="모던",
            model_year=2021,
            mileage_km=85000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=16000000,
            raw_location="서울 강남",
            accident_state="MAJOR_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        ),
    ]

    target = records[0]  # AV_01 (최고 매력 매물)
    res = OpportunityScorer.evaluate_listing(target, records, recent_price_drop=True)

    assert res.evaluation_status == "EVALUATED"
    assert res.opportunity_score is not None
    assert res.opportunity_score >= 70.0  # 고득점 기회 매물
    assert res.sample_count == 3  # Leave-One-Out: 대상 제외 후 3대
    assert res.adjusted_advantage_pct > 0  # 실질 이익 우위
    assert res.has_recent_price_drop is True


def test_pipeline_ingest_db_and_deduplication(test_db_session):
    """파이프라인의 DB 적재 및 동일 매물 가격 인하 시 스냅샷 추가(Append-only) 검증."""
    now1 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    now2 = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)

    rec1 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="DUP_TEST_01",
        source_url=None,
        seller_reference="D1",
        manufacturer="현대",
        model_name="아반떼",
        model_generation="CN7",
        trim_name="모던",
        model_year=2021,
        mileage_km=30000,
        fuel_type="가솔린",
        transmission="자동",
        price_krw=15000000,
        raw_location="서울 동대문구 장안동",
        accident_state="NO_ACCIDENT",
        has_inspection_record=True,
        observed_at=now1,
    )

    # 1차 인입
    stats1 = OpportunityPipeline.ingest_records_to_db(test_db_session, [rec1])
    assert stats1["new_listings"] == 1
    assert stats1["new_snapshots"] == 1

    # 2차 인입: 동일 매물 가격 인하 (1500만원 -> 1420만원)
    rec2 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="DUP_TEST_01",
        source_url=None,
        seller_reference="D1",
        manufacturer="현대",
        model_name="아반떼",
        model_generation="CN7",
        trim_name="모던",
        model_year=2021,
        mileage_km=30500,
        fuel_type="가솔린",
        transmission="자동",
        price_krw=14200000,  # 80만원 인하
        raw_location="서울 동대문구 장안동",
        accident_state="NO_ACCIDENT",
        has_inspection_record=True,
        observed_at=now2,
    )

    stats2 = OpportunityPipeline.ingest_records_to_db(test_db_session, [rec2])
    assert stats2["new_listings"] == 0  # 신규 생성 방지 (중복 매물 무결성)
    assert stats2["existing_listings"] == 1
    assert stats2["new_snapshots"] == 1  # 새 스냅샷 추가 (이력 보존)
    assert stats2["price_changed_count"] == 1

    # DB 확인
    listing = test_db_session.execute(
        select(Listing).where(Listing.source_listing_id == "DUP_TEST_01")
    ).scalar_one()
    assert listing.current_status == "PRICE_CHANGED"

    snapshots = test_db_session.execute(
        select(ListingSnapshot)
        .where(ListingSnapshot.listing_id == listing.listing_id)
        .order_by(ListingSnapshot.observed_at.asc())
    ).scalars().all()
    assert len(snapshots) == 2
    assert snapshots[0].price_krw == 15000000
    assert snapshots[1].price_krw == 14200000


def test_pipeline_csv_roundtrip_and_export(tmp_path):
    """샘플 CSV 로드부터 평가, Top 10 CSV 파일 내보내기 전 과정 통합 검증."""
    sample_csv = Path("templates/DIRECTIVE_006_MARKET_OBSERVATIONS_SAMPLE.csv")
    assert sample_csv.exists()

    records = OpportunityPipeline.load_records_from_csv(sample_csv)
    assert len(records) == 20

    # 일괄 평가
    results = OpportunityPipeline.evaluate_all(records)
    assert len(results) == 20

    # 상위 10건 CSV 내보내기
    out_csv = tmp_path / "top_10_opportunities.csv"
    top_items = OpportunityPipeline.export_top_opportunities_to_csv(results, out_csv, top_n=10)

    assert len(top_items) == 10
    assert out_csv.exists()
    assert out_csv.stat().st_size > 0

    # 1위 매물은 점수가 정상 산출되어 있어야 함
    assert top_items[0].opportunity_score is not None
    assert top_items[0].evaluation_status == "EVALUATED"
