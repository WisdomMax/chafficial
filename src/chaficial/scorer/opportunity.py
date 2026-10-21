"""차피셜 기회 매물 평가 점수 산정 엔진 (Opportunity Scorer V0.2).

DIRECTIVE 007 핵심 감사 결함 수정 반영:
1. Leave-One-Out (자기 자신 비교 표본 완전 배제)
2. 비교 표본 각각의 기준 조건화(Normalized Baseline Fair Price) 역보정 후 공정 시세 도출
3. 조작·추정 파라미터 분리 및 EXPERIMENTAL_ESTIMATE 명시
4. 누락값 위조 금지 및 표본 부족 시 INSUFFICIENT_DATA 강제
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import median

from chaficial.platforms.base import StandardListingRecord


@dataclass
class ScorerParameters:
    """조정 가능한 스코어러 기준 파라미터 (EXPERIMENTAL_ESTIMATE)."""

    min_benchmark_samples: int = 3  # 최소 독립 비교 표본 수 (자기 자신 제외 후)
    km_rate_per_10k: int = 400_000  # 10,000 km당 가치 보정액 (40만원)
    simple_repair_penalty: int = 600_000  # 단순 외판 교환 감가액 (60만원)
    major_accident_penalty: int = 2_500_000  # 주요 골격 유사고 감가액 (250만원)
    unknown_accident_penalty: int = 400_000  # 사고 미상 패널티 (40만원)
    recent_price_drop_bonus: float = 5.0  # 가격 인하 모멘텀 보너스


@dataclass
class OpportunityScoreResult:
    """기회 매물 평가 결과 DTO."""

    listing_id: str
    source_platform: str
    source_listing_id: str
    source_url: str | None

    # 차량 정보 요약
    vehicle_summary: str
    model_year: int
    mileage_km: int
    price_krw: int
    data_origin: str

    # 비교 통계 (Leave-One-Out 적용)
    benchmark_cohort_key: str
    sample_count: int  # 독립 비교 표본 수 (대상 차량 제외)
    benchmark_median_price_krw: int | None
    normalized_baseline_median_krw: int | None  # 무사고·기준주행 정규화 시세 중앙값

    # 상태 보정 분석
    adjusted_fair_value_krw: int | None  # 대상 차량 상태 반영 적정 가치
    adjusted_advantage_krw: int | None  # 적정 가치 대비 가격 차액 (수익·마진 아님)
    adjusted_advantage_pct: float | None  # 적정 가치 대비 우위율 (%)

    # 점수 및 등급
    opportunity_score: float | None  # 0.0 ~ 100.0 (표본 부족 시 None)
    evaluation_status: str  # EVALUATED, INSUFFICIENT_DATA, ANOMALOUS_DATA
    data_confidence: str  # HIGH, MEDIUM, LOW
    has_recent_price_drop: bool
    estimation_nature: str = "EXPERIMENTAL_ESTIMATE"

    # 근거 및 한계
    selection_reason: str = ""
    evaluation_notes: list[str] = None
    evaluated_at: datetime = None


class OpportunityScorer:
    """CHA-FICIAL OPPORTUNITY SCORER V0.2 정규화 기준 엔진."""

    DEFAULT_PARAMS = ScorerParameters()

    @classmethod
    def make_cohort_key(cls, record: StandardListingRecord) -> str:
        """비교 표본 그룹핑 키: 제조사_모델_세대_연식_트림_연료."""
        gen = record.model_generation or "BASE"
        trim = record.trim_name or "STANDARD"
        return f"{record.manufacturer}_{record.model_name}_{gen}_{record.model_year}_{trim}_{record.fuel_type}"

    @classmethod
    def evaluate_listing(
        cls,
        target: StandardListingRecord,
        cohort_records: list[StandardListingRecord],
        recent_price_drop: bool = False,
        params: ScorerParameters | None = None,
    ) -> OpportunityScoreResult:
        """단일 매물을 자기 자신을 제외한 독립 표본들과 비교 평가."""
        cfg = params or cls.DEFAULT_PARAMS
        cohort_key = cls.make_cohort_key(target)
        now_dt = datetime.now(UTC)
        vehicle_summary = (
            f"{target.manufacturer} {target.model_name} {target.model_generation or ''} "
            f"{target.trim_name or ''} ({target.model_year}년식 / {target.mileage_km:,}km)"
        ).replace("  ", " ")

        # 1. Leave-One-Out: 대상 차량 자기 자신을 비교 표본에서 완전히 배제
        independent_cohort: list[StandardListingRecord] = []
        for r in cohort_records:
            is_same = (
                r.source_platform == target.source_platform
                and r.source_listing_id == target.source_listing_id
            )
            if not is_same and r.price_krw > 0:
                independent_cohort.append(r)

        sample_count = len(independent_cohort)

        # 2. 표본 수 검증: 대상 제외 후 최소 표본 수 미달 시 점수 산정 불가
        if sample_count < cfg.min_benchmark_samples:
            return OpportunityScoreResult(
                listing_id=f"{target.source_platform}:{target.source_listing_id}",
                source_platform=target.source_platform,
                source_listing_id=target.source_listing_id,
                source_url=target.source_url,
                vehicle_summary=vehicle_summary,
                model_year=target.model_year,
                mileage_km=target.mileage_km,
                price_krw=target.price_krw,
                data_origin=target.data_origin,
                benchmark_cohort_key=cohort_key,
                sample_count=sample_count,
                benchmark_median_price_krw=None,
                normalized_baseline_median_krw=None,
                adjusted_fair_value_krw=None,
                adjusted_advantage_krw=None,
                adjusted_advantage_pct=None,
                opportunity_score=None,
                evaluation_status="INSUFFICIENT_DATA",
                data_confidence="LOW",
                has_recent_price_drop=recent_price_drop,
                selection_reason=f"독립 비교 표본 부족 (대상 제외 후 {sample_count}대 / 최소 {cfg.min_benchmark_samples}대 필요)",
                evaluation_notes=[
                    "자기 자신을 제외한 유효 비교 매물 표본이 부족하여 왜곡 방지를 위해 점수 산출을 차단함."
                ],
                evaluated_at=now_dt,
            )

        # 3. 비교 표본 각각의 기준 조건화 (무사고, 기준 주행거리 역보정)
        # 기준 주행거리는 비교군 전체의 중앙 주행거리로 설정
        all_mileages = [r.mileage_km for r in independent_cohort]
        baseline_mileage = int(median(all_mileages))

        normalized_prices: list[int] = []
        raw_prices: list[int] = []

        for r in independent_cohort:
            raw_prices.append(r.price_krw)
            # r의 주행거리 보정액: 기준보다 길면 감가(-)되어 있었으므로 역으로 빼서(+) 환원
            m_delta = baseline_mileage - r.mileage_km
            m_adj = int((m_delta / 10_000.0) * cfg.km_rate_per_10k)

            # r의 사고 감가액 환원
            acc_penalty = 0
            if r.accident_state == "SIMPLE_REPAIR":
                acc_penalty = -cfg.simple_repair_penalty
            elif r.accident_state in ("MAJOR_ACCIDENT", "STRUCTURAL_DAMAGE"):
                acc_penalty = -cfg.major_accident_penalty
            elif r.accident_state == "UNKNOWN":
                acc_penalty = -cfg.unknown_accident_penalty

            # 정규화 기준가격: "r이 기준 주행거리 및 완전 무사고였다면 얼마였을까?"
            norm_price = r.price_krw - m_adj - acc_penalty
            normalized_prices.append(norm_price)

        raw_median_price = int(median(raw_prices))
        norm_median_price = int(median(normalized_prices))

        # 4. 대상 차량(Target)의 상태 반영 공정 시세 (Adjusted Fair Value) 산출
        target_mileage_delta = baseline_mileage - target.mileage_km
        target_mileage_adj = int((target_mileage_delta / 10_000.0) * cfg.km_rate_per_10k)

        target_acc_penalty = 0
        if target.accident_state == "SIMPLE_REPAIR":
            target_acc_penalty = -cfg.simple_repair_penalty
        elif target.accident_state in ("MAJOR_ACCIDENT", "STRUCTURAL_DAMAGE"):
            target_acc_penalty = -cfg.major_accident_penalty
        elif target.accident_state == "UNKNOWN":
            target_acc_penalty = -cfg.unknown_accident_penalty

        # 대상 차량의 상태를 정규화 기준 시세에 적용
        adjusted_fair_value = max(
            1_000_000, norm_median_price + target_mileage_adj + target_acc_penalty
        )

        # 이상치 및 미끼/리스승계 의심 매물 탐지 (정규화 시세의 35% 미만인 경우)
        if target.price_krw < (norm_median_price * 0.35):
            return OpportunityScoreResult(
                listing_id=f"{target.source_platform}:{target.source_listing_id}",
                source_platform=target.source_platform,
                source_listing_id=target.source_listing_id,
                source_url=target.source_url,
                vehicle_summary=vehicle_summary,
                model_year=target.model_year,
                mileage_km=target.mileage_km,
                price_krw=target.price_krw,
                data_origin=target.data_origin,
                benchmark_cohort_key=cohort_key,
                sample_count=sample_count,
                benchmark_median_price_krw=raw_median_price,
                normalized_baseline_median_krw=norm_median_price,
                adjusted_fair_value_krw=adjusted_fair_value,
                adjusted_advantage_krw=adjusted_fair_value - target.price_krw,
                adjusted_advantage_pct=round(((adjusted_fair_value - target.price_krw) / adjusted_fair_value) * 100, 2),
                opportunity_score=None,
                evaluation_status="ANOMALOUS_DATA",
                data_confidence="LOW",
                has_recent_price_drop=recent_price_drop,
                estimation_nature="EXPERIMENTAL_ESTIMATE",
                selection_reason=f"비정상적 극단 저가 매물 (시세 {norm_median_price:,}원 대비 {target.price_krw:,}원: 리스승계/선납금/미끼매물 의심)",
                evaluation_notes=[
                    "호가가 정상 시세의 35% 미만으로 확인되어 이상치(ANOMALOUS_DATA)로 분류하고 기회 추천에서 자동 배제함."
                ],
                evaluated_at=now_dt,
            )

        adjusted_advantage_krw = adjusted_fair_value - target.price_krw
        adjusted_advantage_pct = round(
            (adjusted_advantage_krw / adjusted_fair_value) * 100, 2
        )

        # 5. 다차원 점수 산정 (0 ~ 100)
        base_score = 50.0

        # A. 가격 경쟁력 (상태 조정 할인율 1%당 2.0점, 최대 ±30점)
        price_component = max(-30.0, min(30.0, adjusted_advantage_pct * 2.0))

        # B. 주행거리 절대 우위 점수 (최대 ±10점)
        mileage_component = max(
            -10.0, min(10.0, (target_mileage_delta / 10_000.0) * 5.0)
        )

        # C. 성능점검 및 무사고 가점
        cond_component = 0.0
        if target.has_inspection_record:
            cond_component += 5.0
        if target.accident_state == "NO_ACCIDENT":
            cond_component += 5.0
        elif target.accident_state == "SIMPLE_REPAIR":
            cond_component -= 3.0
        elif target.accident_state in ("MAJOR_ACCIDENT", "STRUCTURAL_DAMAGE"):
            cond_component -= 15.0
        elif target.accident_state == "UNKNOWN":
            cond_component -= 5.0

        # D. 가격 인하 모멘텀
        momentum_component = cfg.recent_price_drop_bonus if recent_price_drop else 0.0

        raw_score = (
            base_score
            + price_component
            + mileage_component
            + cond_component
            + momentum_component
        )

        confidence = cls._calculate_confidence(target, sample_count)
        if confidence == "MEDIUM":
            raw_score *= 0.95
        elif confidence == "LOW":
            raw_score *= 0.85

        final_score = round(max(0.0, min(100.0, raw_score)), 1)

        # 6. 평가 노트 작성
        notes = [
            f"[Leave-One-Out] 대상 제외 독립 표본 {sample_count}대 대상 분석",
            f"표본 단순 중앙가: {raw_median_price:,}원 -> 무사고·기준주행 정규화 시세: {norm_median_price:,}원",
            f"대상 차량 주행거리({target.mileage_km:,}km vs 기준 {baseline_mileage:,}km) 보정: {target_mileage_adj:+,}원",
            f"대상 차량 사고 상태({target.accident_state}) 보정: {target_acc_penalty:+,}원",
            "주의: Adjusted Advantage는 단순 호가 시세 경쟁력 지표이며 확정 순익이나 판매 수수료가 아닙니다.",
        ]
        if recent_price_drop:
            notes.append("최근 가격 인하 관측으로 모멘텀 가점 반영됨.")

        reason = (
            f"정규화 상태조정 시세({adjusted_fair_value:,}원) 대비 {adjusted_advantage_pct:+.1f}% 가격 우위. "
            f"기회점수: {final_score}/100 [EXPERIMENTAL_ESTIMATE]"
        )

        return OpportunityScoreResult(
            listing_id=f"{target.source_platform}:{target.source_listing_id}",
            source_platform=target.source_platform,
            source_listing_id=target.source_listing_id,
            source_url=target.source_url,
            vehicle_summary=vehicle_summary,
            model_year=target.model_year,
            mileage_km=target.mileage_km,
            price_krw=target.price_krw,
            data_origin=target.data_origin,
            benchmark_cohort_key=cohort_key,
            sample_count=sample_count,
            benchmark_median_price_krw=raw_median_price,
            normalized_baseline_median_krw=norm_median_price,
            adjusted_fair_value_krw=adjusted_fair_value,
            adjusted_advantage_krw=adjusted_advantage_krw,
            adjusted_advantage_pct=adjusted_advantage_pct,
            opportunity_score=final_score,
            evaluation_status="EVALUATED",
            data_confidence=confidence,
            has_recent_price_drop=recent_price_drop,
            estimation_nature="EXPERIMENTAL_ESTIMATE",
            selection_reason=reason,
            evaluation_notes=notes,
            evaluated_at=now_dt,
        )

    @classmethod
    def _calculate_confidence(
        cls, record: StandardListingRecord, sample_count: int
    ) -> str:
        """데이터 품질 및 표본 크기 기반 신뢰도 판정."""
        if sample_count < 4:
            return "LOW"
        if not record.has_inspection_record or record.accident_state == "UNKNOWN":
            return "LOW"
        if not record.trim_name or not record.model_generation:
            return "MEDIUM"
        return "HIGH"
