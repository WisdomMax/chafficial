"""DIRECTIVE 008-C 무결성 및 신뢰도 등급화 테스트."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from chaficial.analytics.valuation_validator import ValuationValidator
from chaficial.pipeline.ingest_and_score import OpportunityPipeline
from chaficial.platforms.base import StandardListingRecord
from chaficial.platforms.encar import EncarCardParser
from chaficial.scorer.opportunity import OpportunityScorer, ScorerParameters


def test_directive_008c_missing_price_handling():
    """DIRECTIVE 008-C: 가격 미확인/금융상품 매물이 0원으로 오염되지 않고 None/NULL로 격리되는지 검증."""
    now_iso = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    card_rent = {
        "carid": "42956168",
        "raw_text": "엔카 실촬영 아반떼 (CN7) 1.6 스마트 22/07식(23년형)40,334km가솔린경기 렌트월28만원/24개월 검정색 계열",
    }
    parsed = EncarCardParser.parse_card(card_rent, now_iso)
    assert parsed is not None
    assert parsed["product_type"] == "RENT"
    # 총 매매가격은 0원이 아닌 공란(None)이어야 함!
    assert parsed["price_krw"] == ""
    assert parsed["monthly_payment_krw"] == "280000"


def test_directive_008c_actionable_recommendations_purity(tmp_path):
    """DIRECTIVE 008-C: Actionable 추천 목록에는 LOW 신뢰도나 MANUAL_REVIEW_NEEDED, 가격결측 매물이 0건인지 검증."""
    now = datetime.now(UTC)
    cfg = ScorerParameters(min_benchmark_samples=3)

    records = [
        # 1. 고신뢰도 추천 대상
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="GOOD_01",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            registration_year_month="2021-05",
            mileage_km=40000,
            price_krw=13500000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint="FP_GOOD_01",
            observed_at=now,
        ),
        # 2. 저신뢰도 매물 (사고 미확인) -> MANUAL_REVIEW_NEEDED
        StandardListingRecord(
            source_platform="ENCAR",
            source_listing_id="LOW_01",
            manufacturer="현대",
            model_name="아반떼",
            model_generation="CN7",
            sub_model="PRE_FACELIFT",
            powertrain_line="STANDARD",
            trim_name="모던",
            model_year=2021,
            registration_year_month="2021-05",
            mileage_km=40000,
            price_krw=11000000,
            accident_state="UNKNOWN",
            accident_verification="UNVERIFIED",
            has_inspection_record=False,
            vehicle_fingerprint="FP_LOW_01",
            observed_at=now,
        ),
        # 3. 금융 상품 (가격 결측)
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
            registration_year_month="2021-05",
            mileage_km=40000,
            product_type="RENT",
            price_krw=None,
            monthly_payment_krw=280000,
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint="FP_RENT_01",
            observed_at=now,
        ),
    ] + [
        # 비교 코호트 매물 8대 (충분한 표본 확보용)
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
            mileage_km=40000 + (i * 2000),
            price_krw=14000000 + (i * 200000),
            accident_state="NO_ACCIDENT",
            accident_verification="OFFICIAL_VERIFIED",
            has_inspection_record=True,
            vehicle_fingerprint=f"FP_COHORT_{i}",
            observed_at=now,
        )
        for i in range(8)
    ]

    all_evaluated = OpportunityPipeline.evaluate_all(records, params=cfg)
    out_csv = tmp_path / "actionable.csv"
    actionable = OpportunityPipeline.export_actionable_recommendations_csv(
        all_evaluated, out_csv, max_n=10
    )

    # Actionable 추천에는 LOW 신뢰도(LOW_01)와 금융상품(RENT_01)이 절대 포함되지 않아야 함!
    actionable_ids = [a.source_listing_id for a in actionable]
    assert "GOOD_01" in actionable_ids
    assert "LOW_01" not in actionable_ids
    assert "RENT_01" not in actionable_ids

    for item in actionable:
        assert item.overall_confidence in ("HIGH", "MEDIUM")
        assert item.recommendation_category == "RECOMMENDED"
        assert item.price_krw is not None and item.price_krw > 0


def test_directive_008c_excluded_vehicles_audit_and_sum():
    """DIRECTIVE 008-C: 유효 평가 완료(224) + 제외 표본(58) = 전체 고유 실차(282) 수량 보존성 검증."""
    csv_file = Path("templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv")
    assert csv_file.exists()

    records = OpportunityPipeline.load_records_from_csv(csv_file)
    # 지문 부여
    fp_groups = {}
    for r in records:
        fp = f"{r.manufacturer}_{r.model_name}_{r.model_generation or 'CN7'}_{r.sub_model}_{r.powertrain_line}_{r.registration_year_month}_{r.model_year or 'NOYEAR'}_{r.mileage_km}_{r.fuel_type}_{r.trim_name or 'NOTRIM'}"
        r.vehicle_fingerprint = fp
        if fp not in fp_groups:
            fp_groups[fp] = r

    canonical_records = list(fp_groups.values())
    assert len(canonical_records) == 282  # 추정 고유 실차 282대

    summary = ValuationValidator.evaluate_valuation_accuracy(canonical_records)
    eval_count = summary.total_evaluated_count
    excl_count = len(summary.excluded_records)

    assert eval_count == 224
    assert excl_count == 58
    assert eval_count + excl_count == 282
