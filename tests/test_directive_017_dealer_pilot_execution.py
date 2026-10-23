"""차피셜 딜러 파일럿 실전 패키지 및 피드백 검증 테스트 (DIRECTIVE 017).

검증 항목:
1. VERDICT 허용값(BUY_REVIEW, WATCH, EXCLUDE) 엄격 검증
2. 금액 필드 음수 입력 차단 검증
3. 딜러 판단 사유 필수 입력 검증
4. CSV 피드백 파일 로드(UTF-8/UTF-8-BOM) 및 유효성 검증
5. 재평가 시 덮어쓰지 않고 이력 누적 보존 검증
6. 실제 딜러 입력(is_pilot_actual)과 테스트 목업 분리 및 성과 지표 상태 검증
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


def test_verdict_validation_strict():
    """VERDICT 허용값 검증: 허용된 값은 통과하고, 잘못된 값은 ValueError 발생."""
    valid_record = DealerFeedbackRecord(
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
        dealer_decision_reason="시세 대비 우수",
    )
    assert valid_record.dealer_verdict == "BUY_REVIEW"

    # 비허용값 테스트
    for invalid_verdict in ["BUY", "PASS", "HOLD", "APPROVE", ""]:
        with pytest.raises(ValueError, match="유효하지 않은 dealer_verdict"):
            DealerFeedbackRecord(
                listing_id="l1",
                source_listing_id="100",
                source_url="http://test",
                vehicle_summary="아반떼 CN7",
                observed_price_krw=17000000,
                ai_opportunity_score=80.0,
                ai_hypothetical_net_profit_krw=3000000,
                dealer_verdict=invalid_verdict,
                dealer_expected_purchase_krw=16500000,
                dealer_expected_sale_krw=20000000,
                dealer_expected_reconditioning_cost_krw=800000,
                dealer_decision_reason="테스트",
            )


def test_negative_financial_values_rejected():
    """금액 필드에 음수가 입력될 경우 ValueError 발생."""
    base_kwargs = {
        "listing_id": "l1",
        "source_listing_id": "100",
        "source_url": "http://test",
        "vehicle_summary": "아반떼 CN7",
        "observed_price_krw": 17000000,
        "ai_opportunity_score": 80.0,
        "ai_hypothetical_net_profit_krw": 3000000,
        "dealer_verdict": "BUY_REVIEW",
        "dealer_decision_reason": "테스트",
    }

    with pytest.raises(ValueError, match="예상 매입가.*0 이상"):
        DealerFeedbackRecord(
            **base_kwargs,
            dealer_expected_purchase_krw=-500000,
            dealer_expected_sale_krw=20000000,
            dealer_expected_reconditioning_cost_krw=800000,
        )

    with pytest.raises(ValueError, match="예상 판매가.*0 이상"):
        DealerFeedbackRecord(
            **base_kwargs,
            dealer_expected_purchase_krw=16500000,
            dealer_expected_sale_krw=-1000000,
            dealer_expected_reconditioning_cost_krw=800000,
        )

    with pytest.raises(ValueError, match="상품화 비용.*0 이상"):
        DealerFeedbackRecord(
            **base_kwargs,
            dealer_expected_purchase_krw=16500000,
            dealer_expected_sale_krw=20000000,
            dealer_expected_reconditioning_cost_krw=-100000,
        )


def test_empty_decision_reason_rejected():
    """딜러 판단 사유가 누락되거나 공백일 경우 ValueError 발생."""
    with pytest.raises(ValueError, match="딜러 판단 사유.*필수"):
        DealerFeedbackRecord(
            listing_id="l1",
            source_listing_id="100",
            source_url="http://test",
            vehicle_summary="아반떼 CN7",
            observed_price_krw=17000000,
            ai_opportunity_score=80.0,
            ai_hypothetical_net_profit_krw=3000000,
            dealer_verdict="WATCH",
            dealer_expected_purchase_krw=16000000,
            dealer_expected_sale_krw=20000000,
            dealer_expected_reconditioning_cost_krw=800000,
            dealer_decision_reason="   ",
        )


def test_load_feedback_from_csv(tmp_path: Path):
    """CSV 피드백 파일 로드 및 유효성 검증 (BOM 포함)."""
    csv_file = tmp_path / "feedback.csv"
    csv_content = """priority_rank,source_listing_id,vehicle_summary,observed_price_krw,source_url,dealer_verdict,dealer_expected_purchase_krw,dealer_expected_sale_krw,dealer_expected_reconditioning_cost_krw,dealer_decision_reason
1,42969608,"현대 아반떼 CN7",16900000,https://encar.com/...,BUY_REVIEW,"16,500,000","20,500,000","800,000","시세 대비 15% 저평가 우수 매물"
2,41366410,"현대 아반떼 CN7",14990000,https://encar.com/...,WATCH,"14,000,000","18,000,000","1,000,000","타이어 마모 감안 추가 관찰"
3,42706751,"현대 아반떼 CN7",18740000,https://encar.com/...,,,,,
4,42814110,"현대 아반떼 CN7",21200000,https://encar.com/...,EXCLUDE,,,,"사고이력의심:좌측프론트휀더 교환"
"""
    # UTF-8 BOM 인코딩으로 저장
    csv_file.write_text(csv_content, encoding="utf-8-sig")

    manager = DealerPilotManager(feedback_dir=tmp_path)
    records = manager.load_feedback_from_csv(csv_file, is_pilot_actual=True)

    # 3번 행은 verdict가 없으므로 건너뛰고 총 3건 로드
    assert len(records) == 3
    assert records[0].source_listing_id == "42969608"
    assert records[0].dealer_verdict == "BUY_REVIEW"
    assert records[0].dealer_expected_purchase_krw == 16500000
    assert records[0].is_pilot_actual is True

    assert records[1].dealer_verdict == "WATCH"
    assert records[2].dealer_verdict == "EXCLUDE"
    assert "사고이력의심" in records[2].dealer_decision_reason


def test_feedback_history_accumulation(tmp_path: Path):
    """기존 피드백이 존재할 때 재평가 수행 시 덮어쓰지 않고 이력이 누적되는지 검증."""
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
    manager.record_feedback([record1], filename="feedback.json", append_history=True)

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
        dealer_decision_reason="2차 재평가: 실차 확인 후 매입 승인",
        is_pilot_actual=True,
    )
    save_path = manager.record_feedback([record2], filename="feedback.json", append_history=True)

    # 누적되어 2건이 모두 보존되어야 함
    data = json.loads(save_path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[0]["dealer_verdict"] == "WATCH"
    assert data[1]["dealer_verdict"] == "BUY_REVIEW"


def test_performance_metrics_and_status():
    """피드백 상태(PENDING vs COMPLETED) 및 실제/목업 건수 분리 검증."""
    manager = DealerPilotManager()

    # 빈 피드백 상태
    empty_metrics = manager.calculate_performance([])
    assert empty_metrics.status == "PENDING_DEALER_REVIEW"
    assert empty_metrics.total_candidates_reviewed == 0
    assert empty_metrics.actual_feedback_count == 0

    # 목업 데이터만 있는 상태
    mock_record = DealerFeedbackRecord(
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
        dealer_decision_reason="목업 테스트 데이터",
        is_pilot_actual=False,
    )
    mock_metrics = manager.calculate_performance([mock_record])
    assert mock_metrics.status == "PENDING_DEALER_REVIEW"
    assert mock_metrics.actual_feedback_count == 0
    assert mock_metrics.mock_feedback_count == 1

    # 실제 딜러 입력 데이터 포함 상태
    actual_record = DealerFeedbackRecord(
        listing_id="l2",
        source_listing_id="200",
        source_url="http://test",
        vehicle_summary="아반떼 CN7",
        observed_price_krw=16000000,
        ai_opportunity_score=85.0,
        ai_hypothetical_net_profit_krw=3500000,
        dealer_verdict="BUY_REVIEW",
        dealer_expected_purchase_krw=15500000,
        dealer_expected_sale_krw=19500000,
        dealer_expected_reconditioning_cost_krw=600000,
        dealer_decision_reason="25년 경력 수석 파트너 실제 회신",
        is_pilot_actual=True,
    )
    actual_metrics = manager.calculate_performance([actual_record])
    assert actual_metrics.status == "COMPLETED"
    assert actual_metrics.actual_feedback_count == 1
    assert actual_metrics.mock_feedback_count == 0
