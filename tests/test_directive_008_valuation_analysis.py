"""DIRECTIVE 008 신규 무결성 검증 및 시세 평가 엔진 테스트."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from chaficial.analytics.valuation_validator import ValuationValidator
from chaficial.pipeline.ingest_and_score import OpportunityPipeline
from chaficial.platforms.base import StandardListingRecord
from chaficial.platforms.encar import EncarCardParser
from chaficial.scorer.opportunity import OpportunityScorer, ScorerParameters


def test_directive_008_n_line_vs_n_priority():
    """N Line과 고성능 N의 우선순위 판별 및 오분류 방지 검증."""
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    card_nline = {
        "carid": "1001",
        "raw_text": "현대 아반떼 CN7 1.6 터보 N Line 인스퍼레이션 21/05식 45,000km 1,850만원 엔카진단",
    }
    parsed_nline = EncarCardParser.parse_card(card_nline, now_iso)
    assert parsed_nline is not None
    assert parsed_nline["powertrain_line"] == "N_LINE"
    assert parsed_nline["powertrain_line"] != "N"

    card_n = {
        "carid": "1002",
        "raw_text": "현대 아반떼 CN7 2.0 N 22/03식(22년형) 30,000km 2,750만원 엔카진단 무사고",
    }
    parsed_n = EncarCardParser.parse_card(card_n, now_iso)
    assert parsed_n is not None
    assert parsed_n["powertrain_line"] == "N"


def test_directive_008_rental_explanation_vs_financial_product():
    """단순 '렌트이력 없음' 설명 문구와 실제 렌트/리스 금융상품의 분리 검증."""
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 1. 단순 설명 문구 (정상 매매 매물)
    card_normal = {
        "carid": "2001",
        "raw_text": "현대 아반떼 CN7 1.6 가솔린 모던 21/08식 52,000km 1,350만원 1인신조 렌트이력무 완전무사고",
    }
    parsed_normal = EncarCardParser.parse_card(card_normal, now_iso)
    assert parsed_normal is not None
    assert parsed_normal["product_type"] == "CASH_OR_INSTALLMENT"
    assert parsed_normal["price_krw"] == "13500000"
    assert parsed_normal["monthly_payment_krw"] == ""

    # 2. 실제 렌트 월납입형 금융상품
    card_rent = {
        "carid": "2002",
        "raw_text": "현대 아반떼 CN7 1.6 모던 21/09식 40,000km 렌트월28만원 장기렌트 승계",
    }
    parsed_rent = EncarCardParser.parse_card(card_rent, now_iso)
    assert parsed_rent is not None
    assert parsed_rent["product_type"] == "RENT"
    assert parsed_rent["price_krw"] == ""
    assert parsed_rent["monthly_payment_krw"] == "280000"


def test_directive_008_no_model_year_fallback_to_registration():
    """모델연도(형식연도) 미표기 시 등록연도로 대체하지 않고 미확인(None) 처리 검증."""
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # 형식연도 표기 있는 경우
    card_with_year = {
        "carid": "3001",
        "raw_text": "현대 아반떼 CN7 1.6 모던 21/09식(22년형) 38,000km 1,450만원",
    }
    p1 = EncarCardParser.parse_card(card_with_year, now_iso)
    assert p1["model_year"] == "2022"
    assert p1["registration_year_month"] == "2021-09"

    # 형식연도 표기 없는 경우 (임의 추정 금지)
    card_no_year = {
        "carid": "3002",
        "raw_text": "현대 아반떼 CN7 1.6 모던 21/09식 38,000km 1,450만원",
    }
    p2 = EncarCardParser.parse_card(card_no_year, now_iso)
    assert p2["model_year"] == ""  # 2021년으로 임의 대체되지 않고 공란 보존
    assert p2["registration_year_month"] == "2021-09"


def test_directive_008_multidimensional_score_and_confidence_separation():
    """점수와 신뢰도 분리, 데이터 완전성 및 상세 확인(Manual Review) 분류 검증."""
    now = datetime.now(UTC)
    cfg = ScorerParameters(min_benchmark_samples=3)

    # 1. 완전한 데이터 & 충분한 표본 (8대 이상) -> HIGH 신뢰도 & RECOMMENDED
    good_records = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id=f"GOOD_{i}",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            registration_year_month="2021-05",
            mileage_km=40000 + (i * 3000),
            price_krw=14000000 + (i * 200000),
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            observed_at=now,
        )
        for i in range(10)
    ]
    target_good = good_records[0]
    res_good = OpportunityScorer.evaluate_listing(target_good, good_records, params=cfg)
    assert res_good.evaluation_status == "EVALUATED"
    assert res_good.overall_confidence == "HIGH"
    assert res_good.recommendation_category == "RECOMMENDED"
    assert res_good.data_completeness_score >= 0.85

    # 2. 불완전한 데이터 (사고 상태 UNKNOWN) -> MANUAL_REVIEW_NEEDED
    target_incomplete = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="INCOMP_01",
        manufacturer="현대",
        model_name="아반떼",
        model_generation="CN7",
        sub_model="PRE_FACELIFT",
        powertrain_line="STANDARD",
        trim_name="모던",
        model_year=2021,
        registration_year_month="2021-05",
        mileage_km=40000,
        price_krw=11000000,  # 매우 저렴하여 점수는 높을 수 있음
        accident_state="UNKNOWN",  # 사고 미확인
        accident_verification="UNVERIFIED",
        has_inspection_record=False,
        observed_at=now,
    )
    res_incomp = OpportunityScorer.evaluate_listing(target_incomplete, good_records, params=cfg)
    assert res_incomp.evaluation_status == "EVALUATED"
    # 높은 기회 점수라도 사고 미확인이면 상세 확인 대상이어야 함!
    assert res_incomp.recommendation_category == "MANUAL_REVIEW_NEEDED"
    assert "accident_state" in res_incomp.missing_attributes


def test_directive_008_valuation_accuracy_validator():
    """ValuationValidator의 Leave-One-Out 오차 계산 정확성 검증."""
    now = datetime.now(UTC)
    cfg = ScorerParameters(min_benchmark_samples=3)

    records = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id=f"VAL_{i}",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            registration_year_month="2021-05",
            mileage_km=50000,
            price_krw=15000000 + (i * 200000),
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            observed_at=now,
        )
        for i in range(5)
    ]

    summary = ValuationValidator.evaluate_valuation_accuracy(records, params=cfg)
    assert summary.total_evaluated_count == 5
    assert summary.mae_krw >= 0
    assert summary.mdae_krw >= 0
    assert summary.mape_pct >= 0


def test_directive_008_expanded_dataset_file_integrity():
    """실제 수집된 아반떼 CN7 확장 데이터셋 파일 무결성 검증."""
    csv_file = Path("templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv")
    assert csv_file.exists()

    records = OpportunityPipeline.load_records_from_csv(csv_file)
    assert len(records) >= 300  # 최소 목표치 300건 달성 검증
    assert all(r.data_origin == "MANUALLY_OBSERVED" for r in records)
    assert all(r.manufacturer == "현대" and r.model_name == "아반떼" for r in records)


def test_directive_008a_option_price_parsing_exclusion():
    """옵션 추가설명(예: 115만원, 120만원)이 차량 본체 가격으로 오탐되지 않는지 검증 (매물 42938839 반례)."""
    raw_text = (
        "스마트센스 1(115만원), 컴포트 1(120만원) 추가옵션 엔카진단 무사고진단 "
        "아반떼 (CN7) 1.6 모던 22/05식(23년형)54,449km가솔린경기 1,780만원 검정색 계열"
    )
    parsed = EncarCardParser.parse_card({"carid": "42938839", "raw_text": raw_text})
    assert parsed is not None
    # 115만원이나 120만원이 아닌 1,780만원(17800000)으로 정확히 파싱되어야 함!
    assert parsed["price_krw"] == "17800000"
    assert parsed["price_status"] == "VERIFIED"


def test_directive_008a_duplicate_vehicle_loo_leakage_prevention():
    """동일 실차 지문을 가진 복제 광고 매물이 Leave-One-Out 비교군에서 완전히 제외되는지 검증."""
    now = datetime.now(UTC)
    cfg = ScorerParameters(min_benchmark_samples=3)

    fp_twin = "현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2022-09_2023_33660_14000000_모던"

    records = [
        # 실차 쌍둥이 A (엔카믿고 광고 매물)
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="42925136",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2023,
            registration_year_month="2022-09",
            mileage_km=33660,
            price_krw=14000000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint=fp_twin,
            observed_at=now,
        ),
        # 실차 쌍둥이 B (일반 리스팅 매물 - A와 동일 실차)
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="42924382",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2023,
            registration_year_month="2022-09",
            mileage_km=33660,
            price_krw=14000000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint=fp_twin,
            observed_at=now,
        ),
        # 다른 독립 실차 C, D, E (3대)
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="INDEP_01",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2023,
            registration_year_month="2022-09",
            mileage_km=40000,
            price_krw=16500000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint="FP_INDEP_01",
            observed_at=now,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="INDEP_02",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2023,
            registration_year_month="2022-09",
            mileage_km=42000,
            price_krw=16700000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint="FP_INDEP_02",
            observed_at=now,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="INDEP_03",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2023,
            registration_year_month="2022-09",
            mileage_km=38000,
            price_krw=16900000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint="FP_INDEP_03",
            observed_at=now,
        ),
    ]

    # 쌍둥이 A를 평가할 때, 비교군에 쌍둥이 B가 포함되면 안 됨!
    # 유효 독립 표본은 오직 INDEP_01, INDEP_02, INDEP_03의 3대뿐이어야 함.
    res_a = OpportunityScorer.evaluate_listing(records[0], records, params=cfg)
    assert res_a.evaluation_status == "EVALUATED"
    assert res_a.sample_count == 3  # 쌍둥이 B가 완벽히 배제되었음을 입증!
    # 중앙값은 1,650만, 1,670만, 1,690만의 중앙값인 1,670만원이어야 함 (1,400만원이 오염되지 않음!)
    assert res_a.benchmark_median_price_krw == 16700000


def test_directive_008b_mape_denominator_is_actual_price():
    """DIRECTIVE 008-B: MAPE 산출 공식의 분모가 예측가가 아닌 실제 등록 호가(actual_price)인지 검증."""
    now = datetime.now(UTC)
    cfg = ScorerParameters(min_benchmark_samples=3)

    # 4대의 매물: 3대는 1,500만원, 1대는 1,000만원
    # 1,000만원 매물의 경우 Leave-One-Out 비교군(3대)의 중앙가는 1,500만원
    # 상태 보정 후 예측가가 1,500만원이라면:
    # abs_error = |1000 - 1500| = 500만원
    # 정통 MAPE (분모 actual_price = 1000만원) = 500 / 1000 * 100 = 50.0%
    # (구 방식: 분모 predicted = 1500만원인 경우 500 / 1500 * 100 = 33.33%)
    records = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="TARGET_01",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            registration_year_month="2021-05",
            mileage_km=50000,
            price_krw=10000000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint="FP_TARGET",
            observed_at=now,
        )
    ] + [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id=f"COHORT_{i}",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            registration_year_month="2021-05",
            mileage_km=50000,
            price_krw=15000000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint=f"FP_COHORT_{i}",
            observed_at=now,
        )
        for i in range(3)
    ]

    summary = ValuationValidator.evaluate_valuation_accuracy(records, params=cfg)
    target_rec = next(r for r in summary.individual_errors if r["listing_id"] == "TARGET_01")
    assert target_rec["actual_price_krw"] == 10000000
    assert target_rec["predicted_price_krw"] == 15000000
    assert target_rec["abs_error_krw"] == 5000000
    # 분모가 actual_price(10,000,000)이므로 pct_error는 50.0%여야 함! (33.33%가 아님)
    assert target_rec["pct_error"] == 50.0


def test_directive_008b_top_20_unique_vehicles_no_duplicate_fingerprint(tmp_path):
    """DIRECTIVE 008-B: Top 기회 매물 선별 시 실차 지문 기준 디듀플리케이션으로 중복 실차 0건 검증."""
    now = datetime.now(UTC)
    cfg = ScorerParameters(min_benchmark_samples=3)

    fp_dup = "현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2022-09_2023_30000_가솔린_모던"

    # 동일 실차 2건(DUP_A, DUP_B)과 다른 실차 3건(IND_1, IND_2, IND_3)
    records = [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="DUP_A",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2023,
            registration_year_month="2022-09",
            mileage_km=30000,
            price_krw=13000000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint=fp_dup,
            observed_at=now,
        ),
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="DUP_B",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2023,
            registration_year_month="2022-09",
            mileage_km=30000,
            price_krw=13200000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint=fp_dup,
            observed_at=now,
        ),
    ] + [
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id=f"IND_{i}",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2023,
            registration_year_month="2022-09",
            mileage_km=30000,
            price_krw=16000000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint=f"FP_IND_{i}",
            observed_at=now,
        )
        for i in range(3)
    ]

    all_evaluated = OpportunityPipeline.evaluate_all(records, params=cfg)
    out_csv = tmp_path / "top_unique.csv"
    top_candidates = OpportunityPipeline.export_top_opportunities_to_csv(
        all_evaluated, out_csv, top_n=5, deduplicate_by_fingerprint=True
    )

    fps = [c.vehicle_fingerprint for c in top_candidates if c.vehicle_fingerprint]
    # DUP_A와 DUP_B 중 1건만 선별되어 고유해야 함!
    assert len(fps) == len(set(fps))
    assert sum(1 for fp in fps if fp == fp_dup) == 1


def test_directive_008b_fingerprint_excludes_price_invariant_to_price_change():
    """DIRECTIVE 008-B: 차량 지문이 가격을 제외한 물리 불변 제원으로 구성되어 가격 인하 시에도 동일 지문 유지 검증."""
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    card_before = {
        "carid": "5001",
        "raw_text": "현대 아반떼 CN7 1.6 모던 21/09식(22년형) 38,000km 1,550만원",
    }
    card_after = {
        "carid": "5001",
        "raw_text": "현대 아반떼 CN7 1.6 모던 21/09식(22년형) 38,000km 1,450만원",  # 100만원 인하
    }

    p_before = EncarCardParser.parse_card(card_before, now_iso)
    p_after = EncarCardParser.parse_card(card_after, now_iso)

    # 가격이 1,550만원에서 1,450만원으로 변했더라도 물리 지문은 100% 동일해야 함!
    assert p_before["vehicle_fingerprint"] == p_after["vehicle_fingerprint"]
    assert "15500000" not in p_before["vehicle_fingerprint"]
    assert "14500000" not in p_after["vehicle_fingerprint"]
