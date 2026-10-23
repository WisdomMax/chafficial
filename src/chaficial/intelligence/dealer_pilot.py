"""차피셜 딜러 파일럿 실전 피드백 수집 및 성과 측정 엔진 (DIRECTIVE 016 & 017 & 017-A).

운영 원칙:
- 기존 원본 관측 데이터 및 운영 DB와 100% 분리된 독립 피드백 저장소(`data/dealer_feedback/`) 사용
- 25년 경력 딜러 파트너의 실전 매입 판단 데이터셋 축적 및 AI 추천 정확도 검증
- 엄격한 입력 검증: VERDICT 허용값(BUY_REVIEW, WATCH, EXCLUDE), 금액 필드 음수 금지
- 실제 딜러 회신(is_pilot_actual) 필수 명시화 (기본값 제거로 오분류 원천 차단)
- 과거 피드백 데이터 안전 보존: 손상된 JSON 파일 덮어쓰기 원천 차단 및 원자적 교체(atomic replace) 저장
- 중복 회신 감지: 동일 회신 재업로드 시 중복 방지, 일자별 정당한 재평가는 이력 보존
- 평가 지표 정합성: 고유 차량(unique listing_id) 최신 평가 기준 집계 및 평가완료 기준/전체8대 기준 긍정률 분리
"""

import csv
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import tempfile
from typing import Any

from chaficial.intelligence.opportunity_engine import OpportunityCandidate

ALLOWED_VERDICTS = {"BUY_REVIEW", "WATCH", "EXCLUDE"}
PILOT_TARGET_COUNT = 8  # 딜러 파일럿 대상 우선 검토 매물 수


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

    # 딜러 실전 판단 항목
    dealer_verdict: str  # BUY_REVIEW (매입검토), WATCH (관찰), EXCLUDE (제외)
    dealer_expected_purchase_krw: int | None
    dealer_expected_sale_krw: int | None
    dealer_expected_reconditioning_cost_krw: int | None
    dealer_decision_reason: str
    is_pilot_actual: bool  # 실제 딜러 평가 여부 (필수 인자: 목업과 엄격 분리)
    reviewed_by: str = "장안평_25년경력_수석파트너"
    reviewed_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        """입력 데이터 정합성 검증."""
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

    def get_fingerprint(self) -> str:
        """동일 회신 중복 감지를 위한 레코드 고유 식별자."""
        raw = (
            f"{self.source_listing_id}|{self.dealer_verdict}|"
            f"{self.dealer_expected_purchase_krw}|{self.dealer_expected_sale_krw}|"
            f"{self.dealer_expected_reconditioning_cost_krw}|{self.dealer_decision_reason.strip()}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class PilotPerformanceMetrics:
    """딜러 파일럿 성과 측정 지표 (DIRECTIVE 017-A)."""

    total_candidates_reviewed: int  # 실제 평가 완료된 고유 차량 수
    hit_ratio_pct: float  # 평가 완료 차량 대비 BUY_REVIEW 비율 (%)
    total_target_hit_ratio_pct: float  # 전체 파일럿 8대 대상 대비 BUY_REVIEW 비율 (%)
    watch_ratio_pct: float  # 추가 관찰(WATCH) 비율 (%)
    exclude_ratio_pct: float  # 제외(EXCLUDE) 비율 (%)
    avg_price_difference_krw: float  # 관측가 vs 딜러 예상매입가 차이 (유효 매입가 기준 평균)
    verdict_breakdown: dict[str, int]
    exclude_reason_breakdown: dict[str, int]
    status: str = "PENDING_DEALER_REVIEW"  # PENDING_DEALER_REVIEW, COMPLETED
    actual_feedback_count: int = 0  # 실제 딜러 평가 완료 건수
    mock_feedback_count: int = 0  # 테스트 목업 건수
    total_history_records: int = 0  # 누적된 전체 이력 건수 (재평가 포함)


class DealerPilotManager:
    """딜러 파일럿 피드백 수집 및 성과 분석 매니저."""

    def __init__(self, feedback_dir: Path | None = None):
        self.feedback_dir = feedback_dir or Path("data/dealer_feedback")
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

    def prepare_pilot_evaluation_sheet(
        self, candidates: list[OpportunityCandidate]
    ) -> list[dict[str, Any]]:
        """우선 검토 8대에 대한 딜러 파일럿 평가 자료 구성."""
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
        """딜러 피드백을 안전하게 원자적 교체(atomic replace) 방식으로 저장 및 이력 누적.
        
        안전 보장:
        - 기존 JSON이 손상되었거나 파싱할 수 없는 경우 빈 목록으로 대체하지 않고 예외 발생 (데이터 손실 방지)
        - 임시 파일에 먼저 기록 후 원자적으로 교체(atomic replace)하여 쓰기 도중 크래시 대응
        - 동일 내용 중복 회신 감지하여 불필요한 중복 누적 방지
        """
        save_path = self.feedback_dir / filename

        existing_data: list[dict[str, Any]] = []
        existing_fingerprints: set[str] = set()

        if append_history and save_path.exists():
            content = save_path.read_text(encoding="utf-8")
            if content.strip():
                try:
                    parsed = json.loads(content)
                    if not isinstance(parsed, list):
                        raise ValueError(f"피드백 JSON 형식이 유효한 리스트가 아닙니다: {save_path}")
                    existing_data = parsed
                    # 기존 레코드 핑거프린트 추출
                    for item in existing_data:
                        raw = (
                            f"{item.get('source_listing_id')}|{item.get('dealer_verdict')}|"
                            f"{item.get('dealer_expected_purchase_krw')}|{item.get('dealer_expected_sale_krw')}|"
                            f"{item.get('dealer_expected_reconditioning_cost_krw')}|"
                            f"{(item.get('dealer_decision_reason') or '').strip()}"
                        )
                        existing_fingerprints.add(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16])
                except json.JSONDecodeError as err:
                    # 손상된 기존 파일을 무시하고 덮어쓰는 행위 원천 차단
                    raise RuntimeError(
                        f"기존 피드백 파일({save_path})이 손상되어 읽을 수 없습니다. "
                        f"과거 데이터 보존을 위해 작업을 중단합니다: {err}"
                    ) from err

        # 신규 데이터 중 동일 내용 중복 제외 (날짜가 다른 재평가나 변경된 내용은 정상 누적)
        new_records_to_add: list[dict[str, Any]] = []
        for f in feedback_list:
            fp = f.get_fingerprint()
            if fp not in existing_fingerprints:
                new_records_to_add.append(asdict(f))
                existing_fingerprints.add(fp)

        combined = existing_data + new_records_to_add

        # 원자적 파일 교체 (Atomic write using tempfile)
        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            dir=str(self.feedback_dir),
            delete=False,
            encoding="utf-8",
            suffix=".tmp",
        )
        try:
            json.dump(combined, temp_file, indent=2, ensure_ascii=False)
            temp_file.flush()
            temp_file.close()
            Path(temp_file.name).replace(save_path)
        except Exception:
            Path(temp_file.name).unlink(missing_ok=True)
            raise

        return save_path

    def load_feedback_from_csv(
        self,
        csv_path: Path | str,
        *,
        is_pilot_actual: bool,
    ) -> list[DealerFeedbackRecord]:
        """딜러가 작성하여 회신한 CSV 파일을 읽고 유효성을 검증하여 피드백 레코드로 로드.
        
        주의: is_pilot_actual 기본값은 존재하지 않으며 호출자가 실제 평가 여부를 명시해야 합니다.
        """
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
        """딜러 피드백 기반 추천 엔진 성과 측정 (DIRECTIVE 017-A).
        
        정합성 원칙:
        1. 실제 딜러 평가(is_pilot_actual=True)만 성과 지표 산출에 반영 (테스트 목업 분리)
        2. 동일 차량의 재평가 이력이 존재할 경우 최신 평가(reviewed_at 기준)를 기준으로 고유 차량 집계
        3. 평가 완료 차량 대비 긍정률(hit_ratio_pct)과 전체 파일럿 대상(8대) 대비 긍정률(total_target_hit_ratio_pct) 분리
        4. 가격 편차는 유효한 매입가(> 0)가 존재하는 건에 대해서만 정확히 산출
        """
        if not feedback_list:
            return PilotPerformanceMetrics(
                total_candidates_reviewed=0,
                hit_ratio_pct=0.0,
                total_target_hit_ratio_pct=0.0,
                watch_ratio_pct=0.0,
                exclude_ratio_pct=0.0,
                avg_price_difference_krw=0.0,
                verdict_breakdown={},
                exclude_reason_breakdown={},
                status="PENDING_DEALER_REVIEW",
                actual_feedback_count=0,
                mock_feedback_count=0,
                total_history_records=0,
            )

        total_history = len(feedback_list)
        actual_records: list[DealerFeedbackRecord] = []
        mock_count = 0

        for fb in feedback_list:
            if fb.is_pilot_actual:
                actual_records.append(fb)
            else:
                mock_count += 1

        actual_feedback_count = len(actual_records)

        # 실제 평가가 0건이면 무조건 PENDING_DEALER_REVIEW 유지
        if actual_feedback_count == 0:
            return PilotPerformanceMetrics(
                total_candidates_reviewed=0,
                hit_ratio_pct=0.0,
                total_target_hit_ratio_pct=0.0,
                watch_ratio_pct=0.0,
                exclude_ratio_pct=0.0,
                avg_price_difference_krw=0.0,
                verdict_breakdown={},
                exclude_reason_breakdown={},
                status="PENDING_DEALER_REVIEW",
                actual_feedback_count=0,
                mock_feedback_count=mock_count,
                total_history_records=total_history,
            )

        # 고유 차량별 최신 평가만 집계 (재평가 누적 시 분모 왜곡 차단)
        latest_evaluations: dict[str, DealerFeedbackRecord] = {}
        for fb in actual_records:
            lid = fb.source_listing_id
            if lid not in latest_evaluations or fb.reviewed_at >= latest_evaluations[lid].reviewed_at:
                latest_evaluations[lid] = fb

        unique_reviewed_count = len(latest_evaluations)
        verdicts: dict[str, int] = {}
        exclude_reasons: dict[str, int] = {}
        price_diffs: list[int] = []

        for fb in latest_evaluations.values():
            v = fb.dealer_verdict
            verdicts[v] = verdicts.get(v, 0) + 1
            if v == "EXCLUDE":
                reason_key = (
                    fb.dealer_decision_reason.split(":")[0]
                    if ":" in fb.dealer_decision_reason
                    else fb.dealer_decision_reason
                )
                exclude_reasons[reason_key] = exclude_reasons.get(reason_key, 0) + 1

            if fb.dealer_expected_purchase_krw is not None and fb.dealer_expected_purchase_krw > 0:
                diff = fb.observed_price_krw - fb.dealer_expected_purchase_krw
                price_diffs.append(diff)

        # 평가 완료 고유 차량 기준 비율
        hit_ratio = round((verdicts.get("BUY_REVIEW", 0) / unique_reviewed_count) * 100.0, 1)
        watch_ratio = round((verdicts.get("WATCH", 0) / unique_reviewed_count) * 100.0, 1)
        exclude_ratio = round((verdicts.get("EXCLUDE", 0) / unique_reviewed_count) * 100.0, 1)

        # 전체 대상(8대) 기준 적중률
        total_target_hit_ratio = round((verdicts.get("BUY_REVIEW", 0) / PILOT_TARGET_COUNT) * 100.0, 1)

        avg_diff = round(sum(price_diffs) / len(price_diffs), 1) if price_diffs else 0.0

        return PilotPerformanceMetrics(
            total_candidates_reviewed=unique_reviewed_count,
            hit_ratio_pct=hit_ratio,
            total_target_hit_ratio_pct=total_target_hit_ratio,
            watch_ratio_pct=watch_ratio,
            exclude_ratio_pct=exclude_ratio,
            avg_price_difference_krw=avg_diff,
            verdict_breakdown=verdicts,
            exclude_reason_breakdown=exclude_reasons,
            status="COMPLETED",
            actual_feedback_count=actual_feedback_count,
            mock_feedback_count=mock_count,
            total_history_records=total_history,
        )
