"""DIRECTIVE 007: 실제 중고차 데이터 수집 PoC 및 Opportunity Scorer 핵심 결함 수정 검증 테스트."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from chaficial.database.base import Base
from chaficial.models.listing import Listing
from chaficial.pipeline.ingest_and_score import OpportunityPipeline
from chaficial.platforms.base import PlatformUrlParser, StandardListingRecord
from chaficial.scorer.opportunity import OpportunityScorer, ScorerParameters


@pytest.fixture
def test_db_session():
    """인메모리 격리 SQLite 테스트 세션."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_platform_url_parser_hostname_strict():
    """URL의 hostname 기반 엄격한 플랫폼 식별 및 고유 매물 ID 추출 검증."""
    # 정상 엔카 URL
    p1, id1 = PlatformUrlParser.extract_source_id(
        "https://car.encar.com/detail?carid=42617437"
    )
    assert p1 == "ENCAR"
    assert id1 == "42617437"

    # 모바일 엔카 URL
    p1_m, id1_m = PlatformUrlParser.extract_source_id(
        "https://fem.encar.com/cars/detail/42617437"
    )
    assert p1_m == "ENCAR"
    assert id1_m == "42617437"

    # 위장 도메인 차단 (단순 문자열 포함 공격 방어)
    fake_url = "https://fake-phishing-encar.com.malicious.site/detail?carid=123456"
    p_fake, _ = PlatformUrlParser.extract_source_id(fake_url)
    assert p_fake == "UNKNOWN_PLATFORM"


def test_opportunity_scorer_leave_one_out():
    """Leave-One-Out 적용 검증: 대상 차량 자기 자신이 비교 표본에 포함되지 않아야 함."""
    now = datetime.now(UTC)
    # 동일군 3대 매물 준비
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
            mileage_km=30000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=15000000,
            raw_location="서울 강서구",
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
            mileage_km=35000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=15500000,
            raw_location="경기 수원시",
            accident_state="NO_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="AV_03",
            source_url=None,
            seller_reference=None,
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            trim_name="모던",
            model_year=2021,
            mileage_km=40000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=16000000,
            raw_location="인천 서구",
            accident_state="NO_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        ),
    ]

    target = records[0]  # AV_01
    # 3대 중 AV_01을 평가하면, 남은 독립 표본은 AV_02, AV_03 (2대)뿐이므로 3대 미달로 INSUFFICIENT_DATA가 되어야 함!
    res = OpportunityScorer.evaluate_listing(target, records)
    assert res.evaluation_status == "INSUFFICIENT_DATA"
    assert res.opportunity_score is None
    assert res.sample_count == 2  # 자기 자신(AV_01)이 제외되었음을 명확히 입증!


def test_normalized_baseline_price_restoration():
    """사고차와 무사고차가 섞여 있을 때 각각을 무사고 기준으로 역정규화하여 중앙값을 복원하는지 검증."""
    now = datetime.now(UTC)
    cfg = ScorerParameters(
        min_benchmark_samples=3,
        km_rate_per_10k=400_000,
        major_accident_penalty=2_500_000,
    )

    # 4대 매물 준비: 기준 주행거리 50,000km, 정상 무사고 시세 약 1,500만원
    records = [
        # 대상 차량: 50,000km, 완전 무사고, 1,400만원 등록 (100만원 저렴)
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="T_TARGET",
            source_url=None,
            seller_reference=None,
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            trim_name="모던",
            model_year=2021,
            mileage_km=50000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=14000000,
            raw_location="서울 강서구",
            accident_state="NO_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        ),
        # 비교 1: 50,000km, 무사고, 1,500만원
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="COMP_01",
            source_url=None,
            seller_reference=None,
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            trim_name="모던",
            model_year=2021,
            mileage_km=50000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=15000000,
            raw_location="경기 수원시",
            accident_state="NO_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        ),
        # 비교 2: 50,000km, 무사고, 1,520만원
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="COMP_02",
            source_url=None,
            seller_reference=None,
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            trim_name="모던",
            model_year=2021,
            mileage_km=50000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=15200000,
            raw_location="경기 수원시",
            accident_state="NO_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        ),
        # 비교 3: 50,000km, 주요사고차여서 1,250만원에 등록됨 (250만원 감가 반영된 상태)
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="COMP_03",
            source_url=None,
            seller_reference=None,
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            trim_name="모던",
            model_year=2021,
            mileage_km=50000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=12500000,
            raw_location="인천 서구",
            accident_state="MAJOR_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        ),
    ]

    res = OpportunityScorer.evaluate_listing(records[0], records, params=cfg)
    assert res.evaluation_status == "EVALUATED"
    # COMP_03은 사고차(-250만)이므로 무사고 기준가는 1,250 + 250 = 1,500만원으로 복원됨!
    # 따라서 세 비교 매물의 정규화 기준가는 1500만, 1520만, 1500만 -> 중앙값 1,500만원!
    assert res.normalized_baseline_median_krw == 15000000
    assert res.adjusted_fair_value_krw == 15000000
    assert res.adjusted_advantage_krw == 1000000  # 1,500만 - 1,400만 = 100만원 우위


def test_anomalous_data_rejection():
    """비정상적 저가 등록 매물(리스승계, 선납금, 미끼매물) 탐지 및 자동 배제 검증."""
    now = datetime.now(UTC)
    records = [
        # 정상 매물 4대 (1,500만원 대)
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id=f"NORM_{i}",
            source_url=None,
            seller_reference=None,
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            trim_name="모던",
            model_year=2021,
            mileage_km=40000,
            fuel_type="가솔린",
            transmission="자동",
            price_krw=15000000 + (i * 200000),
            raw_location="서울",
            accident_state="NO_ACCIDENT",
            has_inspection_record=True,
            observed_at=now,
        )
        for i in range(4)
    ]

    # 미끼 의심 매물: 120만원 등록 (시세의 10% 미만)
    bait_record = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="BAIT_01",
        source_url=None,
        seller_reference=None,
        manufacturer="현대",
        model_name="아반떼",
        model_generation="CN7",
        trim_name="모던",
        model_year=2021,
        mileage_km=40000,
        fuel_type="가솔린",
        transmission="자동",
        price_krw=1200000,
        raw_location="서울",
        accident_state="NO_ACCIDENT",
        has_inspection_record=True,
        observed_at=now,
    )
    records.append(bait_record)

    res = OpportunityScorer.evaluate_listing(bait_record, records)
    assert res.evaluation_status == "ANOMALOUS_DATA"
    assert res.opportunity_score is None
    assert "비정상적 극단 저가" in res.selection_reason


def test_late_arriving_past_data_integrity(test_db_session):
    """늦게 도착한 과거 관측 자료가 최신 매물 상태나 가격을 오염시키지 않는지 검증."""
    datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t_latest = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)
    t_late_arriving_past = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)

    # 1. 10월 15일 최신 매물 인입 (가격: 1,400만원, 상태: ACTIVE)
    rec_latest = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="TIME_TEST_01",
        source_url=None,
        seller_reference=None,
        manufacturer="현대",
        model_name="아반떼",
        model_generation="CN7",
        trim_name="모던",
        model_year=2021,
        mileage_km=40000,
        fuel_type="가솔린",
        transmission="자동",
        price_krw=14000000,
        raw_location="서울 강서구",
        accident_state="NO_ACCIDENT",
        has_inspection_record=True,
        observed_at=t_latest,
    )
    OpportunityPipeline.ingest_records_to_db(test_db_session, [rec_latest])

    # 2. 10월 5일자 과거 매물 자료가 나중에 지연 인입됨 (가격: 1,500만원)
    rec_past_delayed = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="TIME_TEST_01",
        source_url=None,
        seller_reference=None,
        manufacturer="현대",
        model_name="아반떼",
        model_generation="CN7",
        trim_name="모던",
        model_year=2021,
        mileage_km=39000,
        fuel_type="가솔린",
        transmission="자동",
        price_krw=15000000,
        raw_location="서울 강서구",
        accident_state="NO_ACCIDENT",
        has_inspection_record=True,
        observed_at=t_late_arriving_past,
    )
    stats = OpportunityPipeline.ingest_records_to_db(test_db_session, [rec_past_delayed])

    # 과거 자료는 최신 상태를 덮어쓰지 않고 새로운 스냅샷 생성도 차단되어야 함
    assert stats["new_snapshots"] == 0

    listing = test_db_session.execute(
        select(Listing).where(Listing.source_listing_id == "TIME_TEST_01")
    ).scalar_one()
    assert listing.current_status == "ACTIVE"


def test_real_encar_30_dataset_pipeline_roundtrip(tmp_path):
    """실측 엔카 아반떼 CN7 30건 데이터셋 로드, 파이프라인 무결성 평가 및 Top 10 CSV 검증."""
    real_csv = Path("templates/DIRECTIVE_007_REAL_ENCAR_OBSERVATIONS_30.csv")
    assert real_csv.exists()

    records = OpportunityPipeline.load_records_from_csv(real_csv)
    assert len(records) == 30
    assert all(r.data_origin == "MANUALLY_OBSERVED" for r in records)

    results = OpportunityPipeline.evaluate_all(records)
    assert len(results) == 30

    # 상태별 분류 검증 (표본 부족 코호트와 정상 평가 코호트 공존 확인)
    evaluated = [r for r in results if r.evaluation_status == "EVALUATED"]
    insufficient = [r for r in results if r.evaluation_status == "INSUFFICIENT_DATA"]
    assert len(evaluated) >= 5  # 충분한 표본의 코호트(모던 2021 등)는 정상 평가
    assert len(insufficient) >= 1  # 단독/소수 트림은 무리한 점수 산출 금지

    out_csv = tmp_path / "top_10_real_encar_opportunities.csv"
    top_candidates = OpportunityPipeline.export_top_opportunities_to_csv(
        results, out_csv, top_n=10
    )

    # Top 추천 목록에는 표본 부족이 아닌 정상 평가 매물만 포함되어야 함
    assert all(c.evaluation_status == "EVALUATED" for c in top_candidates)
    assert len(top_candidates) <= 10
    assert out_csv.exists()


def test_directive_007b_financial_product_exclusion_from_benchmark():
    """금융상품(렌트/리스 월납입형)이 일반 매매 시세 중앙값 산정에서 완벽히 배제되는지 검증."""
    now = datetime.now(UTC)
    cfg = ScorerParameters(min_benchmark_samples=3)

    records = [
        # 일반 정상 매매 매물 4대 (1,400만 ~ 1,600만원)
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="CASH_01",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            mileage_km=50000,
            product_type="CASH_OR_INSTALLMENT",
            price_krw=15000000,
            accident_state="NO_ACCIDENT",
            observed_at=now,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="CASH_02",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            mileage_km=50000,
            product_type="CASH_OR_INSTALLMENT",
            price_krw=14800000,
            accident_state="NO_ACCIDENT",
            observed_at=now,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="CASH_03",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            mileage_km=50000,
            product_type="CASH_OR_INSTALLMENT",
            price_krw=15200000,
            accident_state="NO_ACCIDENT",
            observed_at=now,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="CASH_04",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            mileage_km=50000,
            product_type="CASH_OR_INSTALLMENT",
            price_krw=15000000,
            accident_state="NO_ACCIDENT",
            observed_at=now,
        ),
        # 렌트 상품 매물 (월 납입금 28만원, price_krw=None)
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="RENT_01",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            mileage_km=50000,
            product_type="RENT",
            price_krw=None,
            monthly_payment_krw=280000,
            accident_state="NO_ACCIDENT",
            observed_at=now,
        ),
    ]

    target = records[0]  # CASH_01
    res = OpportunityScorer.evaluate_listing(target, records, params=cfg)

    # CASH_01 평가 시 유효 비교군은 CASH_02, CASH_03, CASH_04 (3대). RENT_01은 배제됨
    assert res.sample_count == 3
    assert res.evaluation_status == "EVALUATED"
    # 중앙값은 1480만, 1500만, 1520만의 중앙값인 1500만원이어야 함
    assert res.normalized_baseline_median_krw == 15000000

    # 렌트 매물 자체 평가 시 매매가가 없으므로 안전하게 FINANCIAL_PRODUCT 처리
    rent_target = records[4]
    rent_res = OpportunityScorer.evaluate_listing(rent_target, records, params=cfg)
    assert rent_res.evaluation_status == "FINANCIAL_PRODUCT"
    assert rent_res.opportunity_score is None


def test_directive_007b_facelift_and_powertrain_line_cohort_separation():
    """더 뉴 아반떼(FACELIFT) 및 N_LINE이 동일 연식/트림 일반형과 분리되는지 검증."""
    now = datetime.now(UTC)
    cfg = ScorerParameters(min_benchmark_samples=3)

    records = [
        # CN7 전기형(PRE_FACELIFT) STANDARD 모던 3대
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id=f"PRE_STD_{i}",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2023,
            mileage_km=30000,
            product_type="CASH_OR_INSTALLMENT",
            price_krw=17000000 + (i * 100000),
            accident_state="NO_ACCIDENT",
            observed_at=now,
        )
        for i in range(3)
    ] + [
        # 더 뉴 아반떼(FACELIFT) STANDARD 모던 1대 (신형이라 2,100만원)
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="PE_STD_01",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2023,
            mileage_km=30000,
            product_type="CASH_OR_INSTALLMENT",
            price_krw=21000000,
            accident_state="NO_ACCIDENT",
            observed_at=now,
        ),
        # CN7 전기형(PRE_FACELIFT) N_LINE 모던 1대
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="PRE_NLINE_01",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="N_LINE",
            trim_name="모던",
            model_year=2023,
            mileage_km=30000,
            product_type="CASH_OR_INSTALLMENT",
            price_krw=20000000,
            accident_state="NO_ACCIDENT",
            observed_at=now,
        ),
    ]

    # 더 뉴 아반떼 대상 평가: 비교군에 FACELIFT 표본이 1대뿐이므로(자기 자신 제외 0대) INSUFFICIENT_DATA
    pe_target = records[3]
    pe_res = OpportunityScorer.evaluate_listing(pe_target, records, params=cfg)
    assert pe_res.evaluation_status == "INSUFFICIENT_DATA"
    assert pe_res.sample_count == 0

    # N_LINE 대상 평가: N_LINE 표본이 1대뿐이므로 INSUFFICIENT_DATA
    nline_target = records[4]
    nline_res = OpportunityScorer.evaluate_listing(nline_target, records, params=cfg)
    assert nline_res.evaluation_status == "INSUFFICIENT_DATA"
    assert nline_res.sample_count == 0


def test_directive_007b_mathematical_intermediate_calculation_consistency(tmp_path):
    """스코어 중간 계산값의 수학적 일치성 및 CSV Breakdown 내역 검증."""
    now = datetime.now(UTC)
    cfg = ScorerParameters(min_benchmark_samples=3)

    records = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id=f"CALC_{i}",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            mileage_km=40000 + (i * 5000),
            product_type="CASH_OR_INSTALLMENT",
            price_krw=13000000 + (i * 500000),
            accident_state="NO_ACCIDENT",
            observed_at=now,
        )
        for i in range(4)
    ]

    target = records[0]
    res = OpportunityScorer.evaluate_listing(target, records, params=cfg)
    assert res.evaluation_status == "EVALUATED"

    # 중간 계산값 산술 일치 검증:
    # raw_score = base_score + price_component + mileage_component + condition_component + momentum_component
    expected_raw = (
        res.base_score
        + res.price_component
        + res.mileage_component
        + res.condition_component
        + res.momentum_component
    )
    assert abs(res.raw_score - expected_raw) < 1e-4

    # opportunity_score = round(raw_score * confidence_multiplier, 1)
    expected_final = round(res.raw_score * res.confidence_multiplier, 1)
    assert abs(res.opportunity_score - expected_final) < 1e-4

    # Breakdown CSV 내보내기 검증
    out_breakdown = tmp_path / "directive_007b_score_breakdown.csv"
    OpportunityPipeline.export_score_breakdown_csv([res], out_breakdown)
    assert out_breakdown.exists()
