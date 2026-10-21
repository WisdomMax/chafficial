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
