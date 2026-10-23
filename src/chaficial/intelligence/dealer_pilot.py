"""차피셜 딜러 파일럿 실전 피드백 수집 및 성과 측정 엔진 (DIRECTIVE 016 & DIRECTIVE 017).

운영 원칙:
- 기존 원본 관측 데이터 및 운영 DB와 100% 분리된 독립 피드백 저장소(`data/dealer_feedback/`) 사용
- 25년 경력 딜러 파트너의 실전 매입 판단 데이터셋 축적 및 AI 추천 정확도 검증
- 엄격한 입력 검증: VERDICT 허용값(BUY_REVIEW, WATCH, EXCLUDE), 금액 필드 음수 금지
- 실제 딜러 회신(is_pilot_actual=True)과 테스트/목업 데이터 분리
- 피드백 재평가 시 덮어쓰지 않고 이력(History) 누적 보존
"""

import csv
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from chaficial.intelligence.opportunity_engine import OpportunityCandidate

ALLOWED_VERDICTS = {"BUY_REVIEW", "WATCH", "EXCLUDE"}


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

    # 딜러 실전 판단 항목 (지침 3 & DIRECTIVE 017)
    dealer_verdict: str  # BUY_REVIEW (매입검토), WATCH (관찰), EXCLUDE (제외)
    dealer_expected_purchase_krw: int | None
    dealer_expected_sale_krw: int | None
    dealer_expected_reconditioning_cost_krw: int | None
    dealer_decision_reason: str
    reviewed_by: str = "장안평_25년경력_수석파트너"
    reviewed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    is_pilot_actual: bool = False  # 실제 딜러 입력 여부 (단위테스트/목업과 분리)

    def __post_init__(self) -> None:
        """입력 데이터 정합성 검증 (DIRECTIVE 017 지침)."""
        if self.dealer_verdict not in ALLOWED_VERDICTS:
            raise ValueError(
                f"유효하지 않은 dealer_verdict '{self.dealer_verdict}'. "
                f"허용값: {', '.join(sorted(ALLOWED_VERDICTS))}"
            )

        if self.dealer_expected_purchase_krw is not None and self.dealer_expected_purchase_krw < 0:
            raise ValueError(
                f"예상 매입가({self.dealer_expected_purchase_krw})는 0 이상이어야 합니다."
            )

        if self.dealer_expected_sale_krw is not None and self.dealer_expected_sale_krw < 0:
            raise ValueError(
                f"예상 판매가({self.dealer_expected_sale_krw})는 0 이상이어야 합니다."
            )

        if (
            self.dealer_expected_reconditioning_cost_krw is not None
            and self.dealer_expected_reconditioning_cost_krw < 0
        ):
            raise ValueError(
                f"상품화 비용({self.dealer_expected_reconditioning_cost_krw})은 0 이상이어야 합니다."
            )

        if not self.dealer_decision_reason or not self.dealer_decision_reason.strip():
            raise ValueError("딜러 판단 사유(dealer_decision_reason)는 필수 입력 사항입니다.")


@dataclass
class PilotPerformanceMetrics:
    """딜러 파일럿 성과 측정 지표 (지침 4 & DIRECTIVE 017)."""

    total_candidates_reviewed: int
    hit_ratio_pct: float  # 딜러가 매입 가치(BUY_REVIEW)를 인정한 비율 (%)
    watch_ratio_pct: float  # 추가 관찰(WATCH) 비율 (%)
    exclude_ratio_pct: float  # 제외(EXCLUDE) 비율 (%)
    avg_price_difference_krw: float  # AI 호가 매입가 vs 딜러 예상 매입가 차이 (평균)
    verdict_breakdown: dict[str, int]
    exclude_reason_breakdown: dict[str, int]
    status: str = "PENDING_DEALER_REVIEW"  # PENDING_DEALER_REVIEW, COMPLETED
    actual_feedback_count: int = 0
    mock_feedback_count: int = 0


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
        self,
        feedback_list: list[DealerFeedbackRecord],
        filename: str = "dealer_pilot_feedback_20261024.json",
        append_history: bool = True,
    ) -> Path:
        """딜러 피드백을 기존 원본 데이터와 완전 분리된 독립 JSON으로 저장 (이력 누적 보존)."""
        save_path = self.feedback_dir / filename

        existing_data: list[dict[str, Any]] = []
        if append_history and save_path.exists():
            try:
                content = save_path.read_text(encoding="utf-8")
                if content.strip():
                    existing_data = json.loads(content)
            except Exception:
                existing_data = []

        new_data = [asdict(f) for f in feedback_list]
        combined = existing_data + new_data

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)
        return save_path

    def load_feedback_from_csv(
        self,
        csv_path: Path | str,
        is_pilot_actual: bool = True,
    ) -> list[DealerFeedbackRecord]:
        """딜러가 작성하여 회신한 CSV 파일을 읽고 유효성을 검증하여 피드백 레코드로 로드."""
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"피드백 CSV 파일을 찾을 수 없습니다: {path}")

        records: list[DealerFeedbackRecord] = []

        # UTF-8 BOM(utf-8-sig) 및 UTF-8 자동 처리
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 공백 제거
                clean_row = {
                    k.strip() if k else "": v.strip() if v else ""
                    for k, v in row.items()
                }

                verdict = clean_row.get("dealer_verdict", "")
                if not verdict:
                    # 미평가 행은 건너뜀
                    continue

                def _parse_int(val: str) -> int | None:
                    if not val:
                        return None
                    # 쉼표나 원화 표시 제거
                    cleaned = val.replace(",", "").replace("원", "").replace("KRW", "").strip()
                    return int(cleaned) if cleaned else None

                record = DealerFeedbackRecord(
                    listing_id=clean_row.get("listing_id", f"list-{clean_row.get('source_listing_id', 'unknown')}"),
                    source_listing_id=clean_row.get("source_listing_id", ""),
                    source_url=clean_row.get("source_url", ""),
                    vehicle_summary=clean_row.get("vehicle_summary", ""),
                    observed_price_krw=_parse_int(clean_row.get("observed_price_krw", "0")) or 0,
                    ai_opportunity_score=float(clean_row.get("ai_opportunity_score", 0.0) or 0.0),
                    ai_hypothetical_net_profit_krw=_parse_int(clean_row.get("hypothetical_net_profit_krw", "0")) or 0,
                    dealer_verdict=verdict,
                    dealer_expected_purchase_krw=_parse_int(clean_row.get("dealer_expected_purchase_krw", "")),
                    dealer_expected_sale_krw=_parse_int(clean_row.get("dealer_expected_sale_krw", "")),
                    dealer_expected_reconditioning_cost_krw=_parse_int(clean_row.get("dealer_expected_reconditioning_cost_krw", "")),
                    dealer_decision_reason=clean_row.get("dealer_decision_reason", ""),
                    is_pilot_actual=is_pilot_actual,
                )
                records.append(record)

        return records

    def calculate_performance(
        self, feedback_list: list[DealerFeedbackRecord]
    ) -> PilotPerformanceMetrics:
        """딜러 피드백 기반 추천 엔진 성과 측정 (지침 4 & DIRECTIVE 017)."""
        if not feedback_list:
            return PilotPerformanceMetrics(
                total_candidates_reviewed=0,
                hit_ratio_pct=0.0,
                watch_ratio_pct=0.0,
                exclude_ratio_pct=0.0,
                avg_price_difference_krw=0.0,
                verdict_breakdown={},
                exclude_reason_breakdown={},
                status="PENDING_DEALER_REVIEW",
                actual_feedback_count=0,
                mock_feedback_count=0,
            )

        total = len(feedback_list)
        verdicts: dict[str, int] = {}
        exclude_reasons: dict[str, int] = {}
        price_diffs: list[int] = []
        actual_count = 0
        mock_count = 0

        for fb in feedback_list:
            if fb.is_pilot_actual:
                actual_count += 1
            else:
                mock_count += 1

            v = fb.dealer_verdict
            verdicts[v] = verdicts.get(v, 0) + 1
            if v == "EXCLUDE":
                reason_key = (
                    fb.dealer_decision_reason.split(":")[0]
                    if ":" in fb.dealer_decision_reason
                    else fb.dealer_decision_reason
                )
                exclude_reasons[reason_key] = exclude_reasons.get(reason_key, 0) + 1

            if fb.dealer_expected_purchase_krw is not None:
                diff = fb.observed_price_krw - fb.dealer_expected_purchase_krw
                price_diffs.append(diff)

        hit_ratio = round((verdicts.get("BUY_REVIEW", 0) / total) * 100.0, 1)
        watch_ratio = round((verdicts.get("WATCH", 0) / total) * 100.0, 1)
        exclude_ratio = round((verdicts.get("EXCLUDE", 0) / total) * 100.0, 1)
        avg_diff = round(sum(price_diffs) / len(price_diffs), 1) if price_diffs else 0.0

        status = "COMPLETED" if actual_count > 0 else "PENDING_DEALER_REVIEW"

        return PilotPerformanceMetrics(
            total_candidates_reviewed=total,
            hit_ratio_pct=hit_ratio,
            watch_ratio_pct=watch_ratio,
            exclude_ratio_pct=exclude_ratio,
            avg_price_difference_krw=avg_diff,
            verdict_breakdown=verdicts,
            exclude_reason_breakdown=exclude_reasons,
            status=status,
            actual_feedback_count=actual_count,
            mock_feedback_count=mock_count,
        )
