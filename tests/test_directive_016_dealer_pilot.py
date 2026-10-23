"""차피셜 딜러 파일럿 피드백 수집 및 성과 분석 테스트 (DIRECTIVE 016)."""

from pathlib import Path
import json
import pytest

from chaficial.intelligence.dealer_pilot import DealerFeedbackRecord, DealerPilotManager


def test_dealer_feedback_recording_isolated_storage(tmp_path):
    """지침 3: 딜러 피드백이 기존 원본 DB와 분리된 독립 파일로 안전하게 저장되는지 검증."""
    pilot_dir = tmp_path / "dealer_feedback"
    manager = DealerPilotManager(feedback_dir=pilot_dir)

    record = DealerFeedbackRecord(
        listing_id="list-001",
        source_listing_id="42969608",
        source_url="https://fem.encar.com/cars/detail/42969608",
        vehicle_summary="현대 아반떼 CN7 (2024년식, 42,076km)",
        observed_price_krw=16900000,
        ai_opportunity_score=75.0,
        ai_hypothetical_net_profit_krw=4150000,
        dealer_verdict="BUY_REVIEW",
        dealer_expected_purchase_krw=16500000,
        dealer_expected_sale_krw=21500000,
        dealer_expected_reconditioning_cost_krw=900000,
        dealer_decision_reason="시세 대비 뚜렷한 저평가 상태로 매입 가치 충분",
        is_pilot_actual=True,
    )

    save_path = manager.record_feedback([record], "test_feedback.json")
    assert save_path.exists()

    data = json.loads(save_path.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["source_listing_id"] == "42969608"
    assert data[0]["dealer_verdict"] == "BUY_REVIEW"
    assert data[0]["dealer_expected_purchase_krw"] == 16500000


def test_pilot_performance_calculation():
    """지침 4: 딜러 피드백 기반 추천 적중률 및 가격 편차 집계 검증."""
    manager = DealerPilotManager()

    records = [
        DealerFeedbackRecord(
            listing_id="l1", source_listing_id="1", source_url="", vehicle_summary="",
            observed_price_krw=17000000, ai_opportunity_score=75.0, ai_hypothetical_net_profit_krw=3000000,
            dealer_verdict="BUY_REVIEW", dealer_expected_purchase_krw=16500000, dealer_expected_sale_krw=21000000,
            dealer_expected_reconditioning_cost_krw=800000, dealer_decision_reason="우수 매물",
            is_pilot_actual=True,
        ),
        DealerFeedbackRecord(
            listing_id="l2", source_listing_id="2", source_url="", vehicle_summary="",
            observed_price_krw=15000000, ai_opportunity_score=70.0, ai_hypothetical_net_profit_krw=2000000,
            dealer_verdict="WATCH", dealer_expected_purchase_krw=14000000, dealer_expected_sale_krw=18000000,
            dealer_expected_reconditioning_cost_krw=1000000, dealer_decision_reason="가격 추가 조정 필요",
            is_pilot_actual=True,
        ),
        DealerFeedbackRecord(
            listing_id="l3", source_listing_id="3", source_url="", vehicle_summary="",
            observed_price_krw=18000000, ai_opportunity_score=60.0, ai_hypothetical_net_profit_krw=1000000,
            dealer_verdict="EXCLUDE", dealer_expected_purchase_krw=None, dealer_expected_sale_krw=None,
            dealer_expected_reconditioning_cost_krw=None, dealer_decision_reason="사고의심:골격수리이력추정",
            is_pilot_actual=True,
        ),
        DealerFeedbackRecord(
            listing_id="l4", source_listing_id="4", source_url="", vehicle_summary="",
            observed_price_krw=21000000, ai_opportunity_score=73.0, ai_hypothetical_net_profit_krw=1500000,
            dealer_verdict="BUY_REVIEW", dealer_expected_purchase_krw=20500000, dealer_expected_sale_krw=23500000,
            dealer_expected_reconditioning_cost_krw=700000, dealer_decision_reason="신차급 인기 트림",
            is_pilot_actual=True,
        ),
    ]

    metrics = manager.calculate_performance(records)
    # 4건 중 BUY_REVIEW 2건 (50.0%), WATCH 1건 (25.0%), EXCLUDE 1건 (25.0%)
    assert metrics.total_candidates_reviewed == 4
    assert metrics.hit_ratio_pct == 50.0
    assert metrics.watch_ratio_pct == 25.0
    assert metrics.exclude_ratio_pct == 25.0
    # 가격 차이: (1700만 - 1650만 = 50만) + (1500만 - 1400만 = 100만) + (2100만 - 2050만 = 50만) -> 평균 666,666.7원
    assert metrics.avg_price_difference_krw == pytest.approx(666666.7, rel=1e-3)
