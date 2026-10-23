"""차피셜 DIRECTIVE 017-A & 017-B & 019 피드백 안전성 및 데이터 일관성 검증 테스트.

검증 항목:
1. 동일 제출(동일 submission_id) 두 번 입력 시 이력 1건 (중복 방지)
2. 같은 판단이라도 새로운 세션(재평가) 시 이력 2건 누적 보존
3. 빈 JSON 파일(0 bytes) 입력 시 저장 실패(RuntimeError) 및 원본 보존
4. 손상된 JSON 구조(파싱오류, non-list, non-dict) 입력 시 저장 실패 및 원본 보존
5. 고유 차량(unique listing) 최신 평가 기준 지표 산출 및 평가완료/전체8대 긍정률 분리 검증
6. is_pilot_actual 필수 인자 강제(기본값 제거) 검증
7. reports/pilot/dealer_pilot_review_8.csv와 MarketOpportunityEngine 출력 100% 일치 검증
8. DIRECTIVE 019: 상위 3대 우선 간편 검토 및 미회신 5대 정상 제외/응답 표본 집계 검증
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


def test_empty_zero_byte_json_fails_and_preserves_file(tmp_path: Path):
    """지침 3: 빈 JSON 파일(0 bytes) 입력 시 저장 실패 및 원본 보존 검증."""
    empty_file = tmp_path / "dealer_feedback.json"
    empty_file.write_bytes(b"")

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

    with pytest.raises(RuntimeError, match="빈 파일.*0 bytes"):
        manager.record_feedback([record], filename="dealer_feedback.json", append_history=True)

    assert empty_file.read_bytes() == b""


def test_invalid_json_structure_fails_and_preserves_file(tmp_path: Path):
    """지침 4: 손상된 JSON 구조(파싱 에러 및 non-list/non-dict) 입력 시 저장 실패 및 원본 보존 검증."""
    corrupted_file = tmp_path / "corrupted.json"
    corrupted_bytes = b'{"broken": [1, 2, 3'
    corrupted_file.write_bytes(corrupted_bytes)

    manager = DealerPilotManager(feedback_dir=tmp_path)
    record = DealerFeedbackRecord(
        listing_id="l1", source_listing_id="100", source_url="", vehicle_summary="",
        observed_price_krw=17000000, ai_opportunity_score=80.0, ai_hypothetical_net_profit_krw=3000000,
        dealer_verdict="BUY_REVIEW", dealer_expected_purchase_krw=16500000, dealer_expected_sale_krw=20000000,
        dealer_expected_reconditioning_cost_krw=800000, dealer_decision_reason="우수",
        is_pilot_actual=True,
    )

    with pytest.raises(RuntimeError, match="JSON 파싱에 실패"):
        manager.record_feedback([record], filename="corrupted.json", append_history=True)
    assert corrupted_file.read_bytes() == corrupted_bytes

    dict_file = tmp_path / "dict_file.json"
    dict_bytes = b'{"type": "wrong_root_structure"}'
    dict_file.write_bytes(dict_bytes)

    with pytest.raises(RuntimeError, match="리스트가 아닙니다"):
        manager.record_feedback([record], filename="dict_file.json", append_history=True)
    assert dict_file.read_bytes() == dict_bytes

    invalid_item_file = tmp_path / "invalid_item.json"
    invalid_bytes = b'["string_item_not_dict"]'
    invalid_item_file.write_bytes(invalid_bytes)

    with pytest.raises(RuntimeError, match="레코드 구조가 유효하지 않습니다"):
        manager.record_feedback([record], filename="invalid_item.json", append_history=True)
    assert invalid_item_file.read_bytes() == invalid_bytes


def test_same_submission_twice_keeps_single_record(tmp_path: Path):
    """지침 1: 동일 제출(동일 submission_id) 두 번 입력 시 이력 1건 유지 검증."""
    manager = DealerPilotManager(feedback_dir=tmp_path)

    record = DealerFeedbackRecord(
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
        dealer_decision_reason="1차 관망",
        is_pilot_actual=True,
        submission_id="sub-session-001",
    )

    save_path = manager.record_feedback([record], filename="feedback.json", append_history=True)
    data = json.loads(save_path.read_text(encoding="utf-8"))
    assert len(data) == 1

    save_path = manager.record_feedback([record], filename="feedback.json", append_history=True)
    data = json.loads(save_path.read_text(encoding="utf-8"))
    assert len(data) == 1


def test_same_verdict_new_session_keeps_two_history_records(tmp_path: Path):
    """지침 2: 같은 판단(WATCH)이라도 새로운 세션(재평가) 시 이력 2건 누적 보존 검증."""
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
        submission_id="sub-20261024-session1",
    )
    manager.record_feedback([record1], filename="feedback.json", append_history=True)

    record2 = DealerFeedbackRecord(
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
        submission_id="sub-20261124-session2",
    )
    save_path = manager.record_feedback([record2], filename="feedback.json", append_history=True)

    data = json.loads(save_path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["submission_id"] == "sub-20261024-session1"
    assert data[1]["submission_id"] == "sub-20261124-session2"


def test_csv_loader_automatic_hash_submission_id(tmp_path: Path):
    """CSV 로더 호출 시 파일 해시 기반으로 동일 파일 반복 로드 중복 방지 검증."""
    csv_file = tmp_path / "feedback.csv"
    csv_file.write_text(
        "priority_rank,source_listing_id,vehicle_summary,observed_price_krw,source_url,dealer_verdict,dealer_expected_purchase_krw,dealer_expected_sale_krw,dealer_expected_reconditioning_cost_krw,dealer_decision_reason\n"
        "1,42969608,아반떼,16900000,http://...,BUY_REVIEW,16500000,20500000,800000,우수매물\n",
        encoding="utf-8-sig",
    )

    manager = DealerPilotManager(feedback_dir=tmp_path)
    records1 = manager.load_feedback_from_csv(csv_file, is_pilot_actual=True)
    manager.record_feedback(records1, filename="fb.json", append_history=True)

    records2 = manager.load_feedback_from_csv(csv_file, is_pilot_actual=True)
    save_path = manager.record_feedback(records2, filename="fb.json", append_history=True)

    data = json.loads(save_path.read_text(encoding="utf-8"))
    assert len(data) == 1


def test_partial_review_top_3_cars_and_unreviewed_handling(tmp_path: Path):
    """DIRECTIVE 019: 상위 3대만 부분 평가 회신 시 정상 로드 및 미회신 분리 검증."""
    csv_file = tmp_path / "partial_feedback.csv"
    # 1, 2, 3번만 작성되고 4~8번은 비어있는 실전 회신 시나리오
    csv_content = """priority_rank,source_listing_id,vehicle_summary,observed_price_krw,source_url,dealer_verdict,dealer_expected_purchase_krw,dealer_expected_sale_krw,dealer_expected_reconditioning_cost_krw,dealer_decision_reason
1,42969608,"현대 아반떼 CN7",16900000,http://...,BUY_REVIEW,16500000,20500000,800000,1순위 강력 추천 매입 승인
2,41366410,"현대 아반떼 CN7",14990000,http://...,WATCH,14000000,18000000,1000000,대구 탁송 감안 추가 관망
3,42706751,"현대 아반떼 CN7",18740000,http://...,EXCLUDE,,,,"사고이력의심 골격수리 추정 제외"
4,42814110,"현대 아반떼 CN7",21200000,http://...,,,,,
5,42811604,"현대 아반떼 CN7",15900000,http://...,,,,,
6,42671808,"현대 아반떼 CN7",15900000,http://...,,,,,
7,42911910,"현대 아반떼 CN7",21490000,http://...,,,,,
8,42863742,"현대 아반떼 CN7",21900000,http://...,,,,,
"""
    csv_file.write_text(csv_content, encoding="utf-8-sig")

    manager = DealerPilotManager(feedback_dir=tmp_path)
    records = manager.load_feedback_from_csv(csv_file, is_pilot_actual=True)

    # 8개 행 중 verdict가 작성된 3대만 정상 로드되어야 함 (4~8번 5대는 미회신 제외)
    assert len(records) == 3
    assert [r.source_listing_id for r in records] == ["42969608", "41366410", "42706751"]

    metrics = manager.calculate_performance(records)
    # 평가 완료된 응답 표본 수는 3대
    assert metrics.total_candidates_reviewed == 3
    assert metrics.actual_feedback_count == 3
    # 평가 완료 3대 중 BUY_REVIEW 1건 -> 평가완료 대비 33.3%
    assert metrics.hit_ratio_pct == 33.3
    # 전체 8대 대상 대비 적중률 -> 1건 / 8대 = 12.5%
    assert metrics.total_target_hit_ratio_pct == 12.5
    # WATCH 1건 (33.3%), EXCLUDE 1건 (33.3%)
    assert metrics.watch_ratio_pct == 33.3
    assert metrics.exclude_ratio_pct == 33.3


def test_unique_vehicle_metrics_and_dual_hit_ratios():
    """고유 차량 최신 평가 기준 집계 및 평가완료 기준/전체 8대 기준 긍정률 분리 검증."""
    manager = DealerPilotManager()

    fb1_v1 = DealerFeedbackRecord(
        listing_id="l1", source_listing_id="42969608", source_url="", vehicle_summary="",
        observed_price_krw=16900000, ai_opportunity_score=80.0, ai_hypothetical_net_profit_krw=4000000,
        dealer_verdict="WATCH", dealer_expected_purchase_krw=15000000, dealer_expected_sale_krw=19000000,
        dealer_expected_reconditioning_cost_krw=800000, dealer_decision_reason="관찰",
        is_pilot_actual=True, reviewed_at="2026-10-24T05:00:00Z", submission_id="s1",
    )
    fb1_v2 = DealerFeedbackRecord(
        listing_id="l1", source_listing_id="42969608", source_url="", vehicle_summary="",
        observed_price_krw=16900000, ai_opportunity_score=80.0, ai_hypothetical_net_profit_krw=4000000,
        dealer_verdict="BUY_REVIEW", dealer_expected_purchase_krw=16500000, dealer_expected_sale_krw=20500000,
        dealer_expected_reconditioning_cost_krw=800000, dealer_decision_reason="매입 승인",
        is_pilot_actual=True, reviewed_at="2026-10-24T05:30:00Z", submission_id="s2",
    )

    fb2 = DealerFeedbackRecord(
        listing_id="l2", source_listing_id="41366410", source_url="", vehicle_summary="",
        observed_price_krw=14990000, ai_opportunity_score=75.0, ai_hypothetical_net_profit_krw=2000000,
        dealer_verdict="EXCLUDE", dealer_expected_purchase_krw=None, dealer_expected_sale_krw=None,
        dealer_expected_reconditioning_cost_krw=None, dealer_decision_reason="사고의심",
        is_pilot_actual=True, reviewed_at="2026-10-24T05:10:00Z", submission_id="s1",
    )

    metrics = manager.calculate_performance([fb1_v1, fb1_v2, fb2])

    assert metrics.total_candidates_reviewed == 2
    assert metrics.total_history_records == 3
    assert metrics.actual_feedback_count == 3
    assert metrics.hit_ratio_pct == 50.0
    assert metrics.total_target_hit_ratio_pct == 12.5
    assert metrics.avg_price_difference_krw == 400000.0


def test_is_pilot_actual_mandatory_argument():
    """load_feedback_from_csv 호출 시 is_pilot_actual 누락 시 TypeError 발생 검증."""
    manager = DealerPilotManager()
    with pytest.raises(TypeError):
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
