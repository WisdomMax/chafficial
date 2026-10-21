"""차피셜 기회 매물 평가 점수 산정 엔진 (Opportunity Scorer V0.2.1 - DIRECTIVE 007-B).

개선 사항:
1. 금융상품(렌트/리스) 시세 비교군 원천 배제 (Filter-Out)
2. 정밀 코호트 키: 제조사_모델_세대_서브모델(전기/PE)_라인(일반/N라인/N)_연식_트림_연료
3. 중간 계산값 투명성 강화 (가격경쟁력, 주행거리, 사고인증, 신뢰도가중치 등 중간 세부 수치 DTO 보존)
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from statistics import median
from typing import Any

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
    model_year: int | None
    mileage_km: int
    price_krw: int | None
    product_type: str
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

    # 점수 구성요소 중간 계산값 (수학적 검산 투명성)
    base_score: float = 50.0
    price_component: float = 0.0
    mileage_component: float = 0.0
    condition_component: float = 0.0
    momentum_component: float = 0.0
    raw_score: float = 0.0
    confidence_multiplier: float = 1.0
    opportunity_score: float | None = None  # 최종 산출 점수

    # DIRECTIVE 008: 점수와 신뢰도 분리 및 다차원 평가 지표
    data_completeness_score: float = 1.0  # 데이터 완전성 점수 (0.0 ~ 1.0)
    missing_attributes: list[str] = field(default_factory=list)  # 누락된 속성 목록
    valuation_uncertainty_score: float | None = None  # 시세 예측 불확실성 (%)
    overall_confidence: str = "LOW"  # HIGH, MEDIUM, LOW, UNRELIABLE
    recommendation_category: str = "RECOMMENDED"  # RECOMMENDED, MANUAL_REVIEW_NEEDED, INSUFFICIENT_DATA, FINANCIAL_PRODUCT

    evaluation_status: str = "EVALUATED"  # EVALUATED, INSUFFICIENT_DATA, FINANCIAL_PRODUCT, ANOMALOUS_DATA
    data_confidence: str = "LOW"  # HIGH, MEDIUM, LOW
    has_recent_price_drop: bool = False
    estimation_nature: str = "EXPERIMENTAL_ESTIMATE"

    # 근거 및 한계
    selection_reason: str = ""
    evaluation_notes: list[str] = field(default_factory=list)
    evaluated_at: datetime | None = None


class OpportunityScorer:
    """CHA-FICIAL OPPORTUNITY SCORER V0.2.2 정밀 코호트 및 신뢰도 분리 엔진."""

    DEFAULT_PARAMS = ScorerParameters()

    @classmethod
    def make_cohort_key(cls, record: StandardListingRecord) -> str:
        """비교 표본 그룹핑 키: 제조사_모델_세대_서브모델_파워트레인라인_연식_트림_연료."""
        gen = record.model_generation or "UNKNOWN_GEN"
        sub = record.sub_model or "UNKNOWN_SUB"
        line = record.powertrain_line or "UNKNOWN_LINE"
        year_str = str(record.model_year) if record.model_year is not None else "UNKNOWN_YEAR"
        trim = record.trim_name or "UNKNOWN_TRIM"
        fuel = record.fuel_type or "UNKNOWN_FUEL"
        return f"{record.manufacturer}_{record.model_name}_{gen}_{sub}_{line}_{year_str}_{trim}_{fuel}"

    @classmethod
    def calculate_data_completeness(cls, record: StandardListingRecord) -> tuple[float, list[str]]:
        """데이터 완전성 점수(0.0~1.0)와 누락된 속성 목록 계산."""
        missing = []
        score = 0.0

        if record.model_generation:
            score += 0.15
        else:
            missing.append("model_generation")

        if record.sub_model and record.sub_model != "UNKNOWN":
            score += 0.10
        else:
            missing.append("sub_model")

        if record.powertrain_line and record.powertrain_line != "UNKNOWN":
            score += 0.10
        else:
            missing.append("powertrain_line")

        if record.trim_name and record.trim_name != "UNKNOWN":
            score += 0.20
        else:
            missing.append("trim_name")

        if record.model_year is not None:
            score += 0.15
        else:
            missing.append("model_year")

        if record.registration_year_month:
            score += 0.10
        else:
            missing.append("registration_year_month")

        if record.accident_state != "UNKNOWN":
            score += 0.10
        else:
            missing.append("accident_state")

        if record.has_inspection_record or record.accident_verification != "UNVERIFIED":
            score += 0.10
        else:
            missing.append("accident_verification")

        return round(score, 2), missing

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
            f"[{target.sub_model}/{target.powertrain_line}] {target.trim_name or ''} "
            f"({target.model_year}년식 / {target.mileage_km:,}km)"
        ).replace("  ", " ")

        completeness_score, missing_attrs = cls.calculate_data_completeness(target)

        # 1. 금융 상품(렌트/리스) 사전 격리 (시세 비교군 편입 원천 제외)
        if target.product_type != "CASH_OR_INSTALLMENT" or target.price_krw is None:
            return OpportunityScoreResult(
                listing_id=f"{target.source_platform}:{target.source_listing_id}",
                source_platform=target.source_platform,
                source_listing_id=target.source_listing_id,
                source_url=target.source_url,
                vehicle_summary=vehicle_summary,
                model_year=target.model_year,
                mileage_km=target.mileage_km,
                price_krw=target.price_krw,
                product_type=target.product_type,
                data_origin=target.data_origin,
                benchmark_cohort_key=cohort_key,
                sample_count=0,
                benchmark_median_price_krw=None,
                normalized_baseline_median_krw=None,
                adjusted_fair_value_krw=None,
                adjusted_advantage_krw=None,
                adjusted_advantage_pct=None,
                opportunity_score=None,
                data_completeness_score=completeness_score,
                missing_attributes=missing_attrs,
                valuation_uncertainty_score=None,
                overall_confidence="UNRELIABLE",
                recommendation_category="FINANCIAL_PRODUCT",
                evaluation_status="FINANCIAL_PRODUCT",
                data_confidence="LOW",
                has_recent_price_drop=recent_price_drop,
                selection_reason=f"금융상품({target.product_type}): 월 납입액(월 {target.monthly_payment_krw:,}원) 매물이므로 일반 시세 비교군에서 원천 제외.",
                evaluation_notes=["금융상품은 총판매가격이 아니므로 일반 현금/할부 시세 비교 대상이 아님."],
                evaluated_at=now_dt,
            )

        # 2. Leave-One-Out: 대상 차량, 동일 실차 중복 매물(지문 일치), 타 코호트 매물, 및 금융상품을 비교 표본에서 완전히 배제
        target_fp = target.vehicle_fingerprint
        independent_cohort: list[StandardListingRecord] = []
        for r in cohort_records:
            # 다른 코호트 매물 원천 배제 (동일 연식/트림/서브모델/파워트레인라인 등 일치 필수)
            if cls.make_cohort_key(r) != cohort_key:
                continue

            # 자기 자신 배제
            is_same = (
                r.source_platform == target.source_platform
                and r.source_listing_id == target.source_listing_id
            )
            # 동일 실차 중복 등록 매물 배제 (Leave-One-Out 데이터 누출 원천 차단!)
            is_dup_vehicle = (
                target_fp is not None
                and r.vehicle_fingerprint is not None
                and r.vehicle_fingerprint == target_fp
            )
            if is_same or is_dup_vehicle:
                continue

            # 금융상품 제외 및 유효 가격 매물만 비교군 편입
            is_valid_cash_car = (
                r.product_type == "CASH_OR_INSTALLMENT"
                and r.price_krw is not None
                and r.price_krw > 0
            )
            if is_valid_cash_car:
                independent_cohort.append(r)

        sample_count = len(independent_cohort)

        # 3. 표본 수 검증: 대상 제외 후 최소 표본 수 미달 시 점수 산정 불가
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
                product_type=target.product_type,
                data_origin=target.data_origin,
                benchmark_cohort_key=cohort_key,
                sample_count=sample_count,
                benchmark_median_price_krw=None,
                normalized_baseline_median_krw=None,
                adjusted_fair_value_krw=None,
                adjusted_advantage_krw=None,
                adjusted_advantage_pct=None,
                opportunity_score=None,
                data_completeness_score=completeness_score,
                missing_attributes=missing_attrs,
                valuation_uncertainty_score=None,
                overall_confidence="UNRELIABLE",
                recommendation_category="INSUFFICIENT_DATA",
                evaluation_status="INSUFFICIENT_DATA",
                data_confidence="LOW",
                has_recent_price_drop=recent_price_drop,
                selection_reason=f"동일 정밀 코호트 표본 부족 (대상 제외 후 {sample_count}대 / 최소 {cfg.min_benchmark_samples}대 필요)",
                evaluation_notes=[
                    "동일 서브모델/파워트레인/연식/트림의 독립 비교 매물 표본이 부족하여 왜곡 방지를 위해 점수 산출을 보류함."
                ],
                evaluated_at=now_dt,
            )

        # 4. 비교 표본 각각의 기준 조건화 (무사고, 기준 주행거리 역보정)
        all_mileages = [r.mileage_km for r in independent_cohort]
        baseline_mileage = int(median(all_mileages))

        normalized_prices: list[int] = []
        raw_prices: list[int] = []

        for r in independent_cohort:
            raw_prices.append(r.price_krw)
            m_delta = baseline_mileage - r.mileage_km
            m_adj = int((m_delta / 10_000.0) * cfg.km_rate_per_10k)

            acc_penalty = 0
            if r.accident_state == "SIMPLE_REPAIR":
                acc_penalty = -cfg.simple_repair_penalty
            elif r.accident_state in ("MAJOR_ACCIDENT", "STRUCTURAL_DAMAGE"):
                acc_penalty = -cfg.major_accident_penalty
            elif r.accident_state == "UNKNOWN":
                acc_penalty = -cfg.unknown_accident_penalty

            norm_price = r.price_krw - m_adj - acc_penalty
            normalized_prices.append(norm_price)

        raw_median_price = int(median(raw_prices))
        norm_median_price = int(median(normalized_prices))

        # 5. 대상 차량(Target)의 상태 반영 공정 시세 (Adjusted Fair Value) 산출
        target_mileage_delta = baseline_mileage - target.mileage_km
        target_mileage_adj = int((target_mileage_delta / 10_000.0) * cfg.km_rate_per_10k)

        target_acc_penalty = 0
        if target.accident_state == "SIMPLE_REPAIR":
            target_acc_penalty = -cfg.simple_repair_penalty
        elif target.accident_state in ("MAJOR_ACCIDENT", "STRUCTURAL_DAMAGE"):
            target_acc_penalty = -cfg.major_accident_penalty
        elif target.accident_state == "UNKNOWN":
            target_acc_penalty = -cfg.unknown_accident_penalty

        adjusted_fair_value = max(
            1_000_000, norm_median_price + target_mileage_adj + target_acc_penalty
        )

        # 이상치 및 미끼/리스승계 잔여금 의심 매물 탐지
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
                product_type=target.product_type,
                data_origin=target.data_origin,
                benchmark_cohort_key=cohort_key,
                sample_count=sample_count,
                benchmark_median_price_krw=raw_median_price,
                normalized_baseline_median_krw=norm_median_price,
                adjusted_fair_value_krw=adjusted_fair_value,
                adjusted_advantage_krw=adjusted_fair_value - target.price_krw,
                adjusted_advantage_pct=round(((adjusted_fair_value - target.price_krw) / adjusted_fair_value) * 100, 2),
                opportunity_score=None,
                data_completeness_score=completeness_score,
                missing_attributes=missing_attrs,
                valuation_uncertainty_score=None,
                overall_confidence="UNRELIABLE",
                recommendation_category="ANOMALOUS_DATA",
                evaluation_status="ANOMALOUS_DATA",
                data_confidence="LOW",
                has_recent_price_drop=recent_price_drop,
                estimation_nature="EXPERIMENTAL_ESTIMATE",
                selection_reason=f"비정상적 극단 저가 매물 (시세 {norm_median_price:,}원 대비 {target.price_krw:,}원: 리스승계/선납금/미끼매물 의심)",
                evaluation_notes=["호가가 정상 시세의 35% 미만으로 확인되어 이상치(ANOMALOUS_DATA)로 자동 격리함."],
                evaluated_at=now_dt,
            )

        adjusted_advantage_krw = adjusted_fair_value - target.price_krw
        adjusted_advantage_pct = round(
            (adjusted_advantage_krw / adjusted_fair_value) * 100, 2
        )

        # 시세 예측 불확실성 산출 (정규화 시세 분포의 산포도 %)
        if len(normalized_prices) > 1 and norm_median_price > 0:
            price_devs = [abs(p - norm_median_price) for p in normalized_prices]
            val_uncertainty = round((median(price_devs) / norm_median_price) * 100, 1)
        else:
            val_uncertainty = 10.0

        # 6. 다차원 점수 산정 (모든 중간 계산값 보존)
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
            if target.accident_verification == "OFFICIAL_VERIFIED":
                cond_component += 5.0  # 공인 진단 무사고 (+5점)
            else:
                cond_component += 2.0  # 단순 판매자 주장 무사고 (+2점)
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
        confidence_multiplier = 1.0
        if confidence == "MEDIUM":
            confidence_multiplier = 0.95
        elif confidence == "LOW":
            confidence_multiplier = 0.85

        final_score = round(max(0.0, min(100.0, raw_score * confidence_multiplier)), 1)

        # DIRECTIVE 008-A: 종합 신뢰도(overall_confidence) 및 추천 범주(recommendation_category)
        if sample_count >= 8 and completeness_score >= 0.85 and target.accident_state != "UNKNOWN" and target.model_year is not None:
            overall_conf = "HIGH"
        elif sample_count >= 5 and completeness_score >= 0.65 and target.model_year is not None:
            overall_conf = "MEDIUM"
        elif sample_count >= 3:
            overall_conf = "LOW"
        else:
            overall_conf = "UNRELIABLE"

        # 모델연도 누락 차량은 연식 미확인이므로 신뢰도 최대 LOW로 강제 제한
        if target.model_year is None and overall_conf in ("HIGH", "MEDIUM"):
            overall_conf = "LOW"

        # 신뢰도가 낮거나(사고미확인/주요정보누락/표본부족) 불확실성이 크면 상세 확인 대상(MANUAL_REVIEW_NEEDED)
        if (
            overall_conf in ("LOW", "UNRELIABLE")
            or completeness_score < 0.65
            or target.accident_state == "UNKNOWN"
            or target.accident_verification == "UNVERIFIED"
            or target.model_year is None
        ):
            rec_cat = "MANUAL_REVIEW_NEEDED"
        else:
            rec_cat = "RECOMMENDED"

        notes = [
            f"[Leave-One-Out] 대상 제외 독립 표본 {sample_count}대 대상 분석",
            f"표본 단순 중앙가: {raw_median_price:,}원 -> 무사고·기준주행 정규화 시세: {norm_median_price:,}원",
            f"주행거리({target.mileage_km:,}km vs 기준 {baseline_mileage:,}km) 보정: {target_mileage_adj:+,}원",
            f"사고 상태({target.accident_state}/{target.accident_verification}) 보정: {target_acc_penalty:+,}원",
            f"점수 계산식: ({base_score} + 가격경쟁력 {price_component:+.1f} + 주행거리 {mileage_component:+.1f} + 상태 {cond_component:+.1f} + 모멘텀 {momentum_component:+.1f}) x {confidence_multiplier} = {final_score}점",
            f"완전성 점수: {completeness_score*100:.0f}% (누락: {', '.join(missing_attrs) if missing_attrs else '없음'}) | 시세산포율(CV): {val_uncertainty}%",
            f"추천 분류: {rec_cat} (종합 신뢰도: {overall_conf})",
            "주의: Adjusted Advantage는 단순 시세 호가 경쟁력 지표이며 확정 순익이나 판매 수수료가 아닙니다.",
        ]

        reason = (
            f"정규화 상태조정 시세({adjusted_fair_value:,}원) 대비 {adjusted_advantage_pct:+.1f}% 가격 우위. "
            f"기회점수: {final_score}/100 [EXPERIMENTAL_ESTIMATE] (신뢰도: {overall_conf}, 분류: {rec_cat})"
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
            product_type=target.product_type,
            data_origin=target.data_origin,
            benchmark_cohort_key=cohort_key,
            sample_count=sample_count,
            benchmark_median_price_krw=raw_median_price,
            normalized_baseline_median_krw=norm_median_price,
            adjusted_fair_value_krw=adjusted_fair_value,
            adjusted_advantage_krw=adjusted_advantage_krw,
            adjusted_advantage_pct=adjusted_advantage_pct,
            base_score=base_score,
            price_component=price_component,
            mileage_component=mileage_component,
            condition_component=cond_component,
            momentum_component=momentum_component,
            raw_score=raw_score,
            confidence_multiplier=confidence_multiplier,
            opportunity_score=final_score,
            data_completeness_score=completeness_score,
            missing_attributes=missing_attrs,
            valuation_uncertainty_score=val_uncertainty,
            overall_confidence=overall_conf,
            recommendation_category=rec_cat,
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
