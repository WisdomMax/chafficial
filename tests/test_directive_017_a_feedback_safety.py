"""차피셜 DIRECTIVE 017-A 피드백 안전성 및 데이터 일관성 검증 테스트.

검증 항목:
1. 손상된 JSON 파일 원본 보존 및 예외 발생 (덮어쓰기 원천 차단)
2. 원자적 교체(atomic replace) 안전 저장 검증
3. 동일 회신 재업로드 시 중복 감지 및 정당한 재평가 이력 누적 검증
4. 고유 차량(unique listing) 최신 평가 기준 지표 산출 및 평가완료/전체8대 긍정률 분리 검증
5. is_pilot_actual 필수 인자 강제(기본값 제거) 검증
6. reports/pilot/dealer_pilot_review_8.csv와 MarketOpportunityEngine 출력 100% 일치 검증
"""

import csv
import json
from pathlib import Path
import pytest

from chaficial.intelligence.dealer_pilot import (
    DealerFeedbackRecord,
    DealerPilotManager,
    PilotPerformanceMetrics,
)
from chaficial.intelligence.opportunity_engine import MarketOpportunityEngine


def test_corrupted_json_preservation_and_exception(tmp_path: Path):
    """손상된 JSON 파일이 있을 때 덮어쓰지 않고 RuntimeError를 발생시키며 원본 보존."""
    corrupted_file = tmp_path / "dealer_feedback.json"
    corrupted_content = '{"invalid_json": [1, 2, 3'  # 닫히지 않은 손상된 JSON
    corrupted_file.write_text(corrupted_content, encoding="utf-8")

    manager = DealerPilotManager(feedback_dir=tmp_path)
    record = DealerFeedbackRecord(
        listing_id="l1",
        source_listing_id="100",
        source_url="http://test",
        vehicle_summary="아반떼 CN7",
        observed_price_krw=17000000,
        ai_opportunity_score=80.0,
        ai_hypothetical_net_profit_krw=3000000,
        dealer_verdict="BUY_REVIEW",
        dealer_expected_purchase_krw=16500000,
        dealer_expected_sale_krw=20000000,
        dealer_expected_reconditioning_cost_krw=800000,
        dealer_decision_reason="우수",
        is_pilot_actual=True,
    )

    with pytest.raises(RuntimeError, match="손상되어 읽을 수 없습니다"):
        manager.record_feedback([record], filename="dealer_feedback.json", append_history=True)

    # 원본 손상 파일 내용이 덮어쓰이지 않고 그대로 보존되었는지 검증
    assert corrupted_file.read_text(encoding="utf-8") == corrupted_content


def test_duplicate_submission_detection_and_valid_reassessment(tmp_path: Path):
    """동일 회신 재업로드 시 중복 방지 및 정당한 2차 재평가 누적 검증."""
    manager = DealerPilotManager(feedback_dir=tmp_path)

    record1 = DealerFeedbackRecord(
        listing_id="l1",
        source_listing_id="42969608",
        source_url="http://test",
        vehicle_summary="아반떼 CN7",
        observed_price_krw=16900000,
        ai_opportunity_score=80.0,
        ai_hypothetical_net_profit_krw=3000000,
        dealer_verdict="WATCH",
        dealer_expected_purchase_krw=15000000,
        dealer_expected_sale_krw=19000000,
        dealer_expected_reconditioning_cost_krw=800000,
        dealer_decision_reason="1차 평가: 관망",
        is_pilot_actual=True,
    )

    # 1회 저장
    save_path = manager.record_feedback([record1], filename="feedback.json", append_history=True)
    data = json.loads(save_path.read_text(encoding="utf-8"))
    assert len(data) == 1

    # 동일한 레코드 다시 저장 시도 (중복 회신 시뮬레이션)
    save_path = manager.record_feedback([record1], filename="feedback.json", append_history=True)
    data = json.loads(save_path.read_text(encoding="utf-8"))
    assert len(data) == 1  # 중복이므로 추가되지 않아야 함!

    # 내용이 변경된 2차 재평가 저장
    record2 = DealerFeedbackRecord(
        listing_id="l1",
        source_listing_id="42969608",
        source_url="http://test",
        vehicle_summary="아반떼 CN7",
        observed_price_krw=16900000,
        ai_opportunity_score=80.0,
        ai_hypothetical_net_profit_krw=3000000,
        dealer_verdict="BUY_REVIEW",
        dealer_expected_purchase_krw=16000000,
        dealer_expected_sale_krw=20000000,
        dealer_expected_reconditioning_cost_krw=700000,
        dealer_decision_reason="2차 평가: 실차 확인 후 매입 결정",
        is_pilot_actual=True,
    )
    save_path = manager.record_feedback([record2], filename="feedback.json", append_history=True)
    data = json.loads(save_path.read_text(encoding="utf-8"))
    assert len(data) == 2  # 정당한 재평가는 누적 보존!


def test_unique_vehicle_metrics_and_dual_hit_ratios():
    """고유 차량 최신 평가 기준 집계 및 평가완료 기준/전체 8대 기준 긍정률 분리 검증."""
    manager = DealerPilotManager()

    # 차량 1 (42969608): 1차 WATCH -> 2차 BUY_REVIEW
    fb1_v1 = DealerFeedbackRecord(
        listing_id="l1", source_listing_id="42969608", source_url="", vehicle_summary="",
        observed_price_krw=16900000, ai_opportunity_score=80.0, ai_hypothetical_net_profit_krw=4000000,
        dealer_verdict="WATCH", dealer_expected_purchase_krw=15000000, dealer_expected_sale_krw=19000000,
        dealer_expected_reconditioning_cost_krw=800000, dealer_decision_reason="관찰",
        is_pilot_actual=True, reviewed_at="2026-10-24T05:00:00Z",
    )
    fb1_v2 = DealerFeedbackRecord(
        listing_id="l1", source_listing_id="42969608", source_url="", vehicle_summary="",
        observed_price_krw=16900000, ai_opportunity_score=80.0, ai_hypothetical_net_profit_krw=4000000,
        dealer_verdict="BUY_REVIEW", dealer_expected_purchase_krw=16500000, dealer_expected_sale_krw=20500000,
        dealer_expected_reconditioning_cost_krw=800000, dealer_decision_reason="매입 승인",
        is_pilot_actual=True, reviewed_at="2026-10-24T05:30:00Z",
    )

    # 차량 2 (41366410): 1차 EXCLUDE
    fb2 = DealerFeedbackRecord(
        listing_id="l2", source_listing_id="41366410", source_url="", vehicle_summary="",
        observed_price_krw=14990000, ai_opportunity_score=75.0, ai_hypothetical_net_profit_krw=2000000,
        dealer_verdict="EXCLUDE", dealer_expected_purchase_krw=None, dealer_expected_sale_krw=None,
        dealer_expected_reconditioning_cost_krw=None, dealer_decision_reason="사고의심",
        is_pilot_actual=True, reviewed_at="2026-10-24T05:10:00Z",
    )

    metrics = manager.calculate_performance([fb1_v1, fb1_v2, fb2])

    # 고유 차량 수는 총 2대 (42969608, 41366410)
    assert metrics.total_candidates_reviewed == 2
    assert metrics.total_history_records == 3
    assert metrics.actual_feedback_count == 3

    # 최신 평가: 42969608은 BUY_REVIEW, 41366410은 EXCLUDE -> 2대 중 BUY_REVIEW 1건 (50.0%)
    assert metrics.hit_ratio_pct == 50.0
    # 전체 8대 대상 기준 긍정률: 1대 / 8대 = 12.5%
    assert metrics.total_target_hit_ratio_pct == 12.5

    # 가격 편차: 42969608 유효 매입가(1650만) 1건만 존재 (1690만 - 1650만 = 40만)
    assert metrics.avg_price_difference_krw == 400000.0


def test_is_pilot_actual_mandatory_argument():
    """load_feedback_from_csv 호출 시 is_pilot_actual 누락 시 TypeError 발생 검증."""
    manager = DealerPilotManager()
    with pytest.raises(TypeError):
        # is_pilot_actual 인자 없이 호출 시 실패해야 함
        manager.load_feedback_from_csv("dummy.csv")  # type: ignore


def test_dealer_review_8_csv_matches_opportunity_engine_output():
    """reports/pilot/dealer_pilot_review_8.csv 파일과 MarketOpportunityEngine 실제 출력 100% 일치 검증."""
    csv_path = Path("reports/pilot/dealer_pilot_review_8.csv")
    assert csv_path.exists(), "dealer_pilot_review_8.csv 파일이 존재해야 합니다."

    db_path = Path("data/chaficial_market_timeseries.db")
    engine = MarketOpportunityEngine()
    candidates = engine.evaluate_market_opportunities(db_path=db_path)
    priority_candidates = [c for c in candidates if c.market_opportunity_grade == "PRIORITY_REVIEW"]
    assert len(priority_candidates) == 8, "우선 검토 후보는 정확히 8대여야 합니다."

    # CSV 로드
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)

    assert len(csv_rows) == 8, "CSV 행 수는 정확히 8개여야 합니다."

    for i in range(8):
        c = priority_candidates[i]
        b = c.base_scenario
        row = csv_rows[i]

        assert row["source_listing_id"] == c.source_listing_id
        assert int(row["observed_price_krw"]) == c.current_price_krw
        assert int(row["cohort_median_price_krw"]) == c.cohort_median_price_krw
        assert float(row["relative_price_gap_pct"]) == round(c.relative_price_gap_pct, 2)
        assert int(row["hypothetical_net_profit_krw"]) == (b.hypothetical_net_profit_krw if b else 0)
        assert row["location"] == c.raw_location
        assert c.duplicate_status in row["duplicate_status"]
