"""차피셜 딜러 파일럿 실전 피드백 수집 및 성과 측정 엔진 (DIRECTIVE 016).

운영 원칙:
- 기존 원본 관측 데이터 및 운영 DB와 100% 분리된 독립 피드백 저장소(`data/dealer_feedback/`) 사용
- 25년 경력 딜러 파트너의 실전 매입 판단 데이터셋 축적 및 AI 추천 정확도 검증
"""

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from chaficial.intelligence.opportunity_engine import OpportunityCandidate


@dataclass
class DealerFeedbackRecord:
    """딜러의 개별 매물 실전 평가 기록 DTO."""

    listing_id: str
    source_listing_id: str
    source_url: str
    vehicle_summary: str
    observed_price_krw: int
    ai_opportunity_score: float
    ai_hypothetical_net_profit_krw: int

    # 딜러 실전 판단 항목 (지침 3)
    dealer_verdict: str  # BUY_REVIEW (매입검토), WATCH (관찰), EXCLUDE (제외)
    dealer_expected_purchase_krw: int | None
    dealer_expected_sale_krw: int | None
    dealer_expected_reconditioning_cost_krw: int | None
    dealer_decision_reason: str
    reviewed_by: str = "장안평_25년경력_수석파트너"
    reviewed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class PilotPerformanceMetrics:
    """딜러 파일럿 성과 측정 지표 (지침 4)."""

    total_candidates_reviewed: int
    hit_ratio_pct: float                # 딜러가 매입 가치(BUY_REVIEW)를 인정한 비율 (%)
    watch_ratio_pct: float              # 추가 관찰(WATCH) 비율 (%)
    exclude_ratio_pct: float            # 제외(EXCLUDE) 비율 (%)
    avg_price_difference_krw: float     # AI 호가 매입가 vs 딜러 예상 매입가 차이 (평균)
    verdict_breakdown: dict[str, int]
    exclude_reason_breakdown: dict[str, int]


class DealerPilotManager:
    """딜러 파일럿 피드백 수집 및 성과 분석 매니저."""

    def __init__(self, feedback_dir: Path | None = None):
        self.feedback_dir = feedback_dir or Path("data/dealer_feedback")
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

    def prepare_pilot_evaluation_sheet(
        self, candidates: list[OpportunityCandidate]
    ) -> list[dict[str, Any]]:
        """우선 검토 8대에 대한 딜러 파일럿 평가 자료 구성 (지침 2)."""
        sheet = []
        for c in candidates:
            if c.market_opportunity_grade != "PRIORITY_REVIEW":
                continue
            b = c.base_scenario
            url = f"https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid={c.source_listing_id}"
            sheet.append({
                "listing_id": c.listing_id,
                "source_listing_id": c.source_listing_id,
                "source_url": url,
                "vehicle_summary": c.vehicle_summary,
                "observed_price_krw": c.current_price_krw,
                "cohort_median_price_krw": c.cohort_median_price_krw,
                "sample_count": c.sample_count,
                "relative_price_gap_pct": c.relative_price_gap_pct,
                "hypothetical_net_profit_krw": b.hypothetical_net_profit_krw if b else 0,
                "region": c.raw_location,
                "partner_suitability": c.partner_operational_suitability,
                "duplicate_status": c.duplicate_status,
                "duplicate_ids": c.duplicate_listing_ids,
                "history_check_required": "보험사고/침수/용도이력 실사필요",
            })
        return sheet

    def record_feedback(
        self, feedback_list: list[DealerFeedbackRecord], filename: str = "dealer_pilot_feedback_20261024.json"
    ) -> Path:
        """딜러 피드백을 기존 원본 데이터와 완전 분리된 독립 JSON으로 저장."""
        save_path = self.feedback_dir / filename
        data = [asdict(f) for f in feedback_list]
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return save_path

    def calculate_performance(
        self, feedback_list: list[DealerFeedbackRecord]
    ) -> PilotPerformanceMetrics:
        """딜러 피드백 기반 추천 엔진 성과 측정 (지침 4)."""
        if not feedback_list:
            return PilotPerformanceMetrics(0, 0.0, 0.0, 0.0, 0.0, {}, {})

        total = len(feedback_list)
        verdicts = {}
        exclude_reasons = {}
        price_diffs = []

        for fb in feedback_list:
            v = fb.dealer_verdict
            verdicts[v] = verdicts.get(v, 0) + 1
            if v == "EXCLUDE":
                reason_key = fb.dealer_decision_reason.split(":")[0] if ":" in fb.dealer_decision_reason else fb.dealer_decision_reason
                exclude_reasons[reason_key] = exclude_reasons.get(reason_key, 0) + 1

            if fb.dealer_expected_purchase_krw is not None:
                diff = fb.observed_price_krw - fb.dealer_expected_purchase_krw
                price_diffs.append(diff)

        hit_ratio = round((verdicts.get("BUY_REVIEW", 0) / total) * 100.0, 1)
        watch_ratio = round((verdicts.get("WATCH", 0) / total) * 100.0, 1)
        exclude_ratio = round((verdicts.get("EXCLUDE", 0) / total) * 100.0, 1)
        avg_diff = round(sum(price_diffs) / len(price_diffs), 1) if price_diffs else 0.0

        return PilotPerformanceMetrics(
            total_candidates_reviewed=total,
            hit_ratio_pct=hit_ratio,
            watch_ratio_pct=watch_ratio,
            exclude_ratio_pct=exclude_ratio,
            avg_price_difference_krw=avg_diff,
            verdict_breakdown=verdicts,
            exclude_reason_breakdown=exclude_reasons,
        )
