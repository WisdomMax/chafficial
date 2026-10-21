"""차피셜 기회 매물 평가 점수 산정 엔진 (Opportunity Scorer V0.1).

동일 차종·세대·연식·트림 비교 매물 시세를 기반으로 상태 조정 공정 가치를 산출하고,
가격 경쟁력, 주행거리, 사고 이력, 가격 인하 모멘텀, 데이터 신뢰도를 종합하여 0~100점의 기회 점수를 산정합니다.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import median

from chaficial.platforms.base import StandardListingRecord


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

    # 비교 통계
    benchmark_cohort_key: str
    sample_count: int
    benchmark_median_price_krw: int | None
    raw_price_difference_pct: float | None

    # 상태 보정 분석
    adjusted_fair_value_krw: int | None
    adjusted_advantage_krw: int | None
    adjusted_advantage_pct: float | None

    # 점수 및 등급
    opportunity_score: float | None  # 0.0 ~ 100.0 (표본 부족 시 None)
    evaluation_status: str  # EVALUATED, INSUFFICIENT_DATA, ANOMALOUS_DATA
    data_confidence: str  # HIGH, MEDIUM, LOW
    has_recent_price_drop: bool

    # 근거 및 한계
    selection_reason: str
    evaluation_notes: list[str]
    evaluated_at: datetime


class OpportunityScorer:
    """CHA-FICIAL OPPORTUNITY SCORER V0.1 규칙 기반 엔진."""

    MIN_BENCHMARK_SAMPLES = 3  # 최소 비교 표본 수 (동일군 3대 미만 시 INSUFFICIENT_DATA)
    KM_ADJUSTMENT_RATE_PER_10K = 400_000  # 10,000 km당 가치 보정액 (40만원)
    ACCIDENT_PENALTY_SIMPLE = 600_000  # 단순 교환 감가 보정액 (60만원)
    ACCIDENT_PENALTY_MAJOR = 2_500_000  # 주요 골격 유사고 감가 보정액 (250만원)

    @classmethod
    def make_cohort_key(cls, record: StandardListingRecord) -> str:
        """비교 표본 그룹핑 키 생성: 제조사_모델_세대_연식_트림_연료."""
        gen = record.model_generation or "BASE"
        trim = record.trim_name or "STANDARD"
        return f"{record.manufacturer}_{record.model_name}_{gen}_{record.model_year}_{trim}_{record.fuel_type}"

    @classmethod
    def evaluate_listing(
        cls,
        target: StandardListingRecord,
        cohort_records: list[StandardListingRecord],
        recent_price_drop: bool = False,
    ) -> OpportunityScoreResult:
        """단일 매물을 동일군 표본들과 비교 평가하여 기회 점수를 산출."""
        cohort_key = cls.make_cohort_key(target)
        now_dt = datetime.now(UTC)
        vehicle_summary = (
            f"{target.manufacturer} {target.model_name} {target.model_generation or ''} "
            f"{target.trim_name or ''} ({target.model_year}년식 / {target.mileage_km:,}km)"
        ).replace("  ", " ")

        # 1. 표본 수 검증
        sample_count = len(cohort_records)
        if sample_count < cls.MIN_BENCHMARK_SAMPLES:
            return OpportunityScoreResult(
                listing_id=f"{target.source_platform}:{target.source_listing_id}",
                source_platform=target.source_platform,
                source_listing_id=target.source_listing_id,
                source_url=target.source_url,
                vehicle_summary=vehicle_summary,
                model_year=target.model_year,
                mileage_km=target.mileage_km,
                price_krw=target.price_krw,
                benchmark_cohort_key=cohort_key,
                sample_count=sample_count,
                benchmark_median_price_krw=None,
                raw_price_difference_pct=None,
                adjusted_fair_value_krw=None,
                adjusted_advantage_krw=None,
                adjusted_advantage_pct=None,
                opportunity_score=None,
                evaluation_status="INSUFFICIENT_DATA",
                data_confidence=cls._calculate_confidence(target),
                has_recent_price_drop=recent_price_drop,
                selection_reason=f"동일 비교군 표본 부족 (현재 {sample_count}대 / 최소 {cls.MIN_BENCHMARK_SAMPLES}대 필요)",
                evaluation_notes=["비교 가능한 동일 연식·트림의 등록 매물 표본이 부족하여 신뢰할 수 있는 점수 산출 불가."],
                evaluated_at=now_dt,
            )

        # 2. 표본 통계 (중앙 등록가격, 중앙 주행거리)
        prices = [r.price_krw for r in cohort_records if r.price_krw > 0]
        mileages = [r.mileage_km for r in cohort_records if r.mileage_km >= 0]
        median_price = int(median(prices))
        median_mileage = int(median(mileages))

        # 단순 가격 차이
        raw_price_diff = median_price - target.price_krw
        raw_price_diff_pct = round((raw_price_diff / median_price) * 100, 2)

        # 3. 주행거리 상태 보정
        # 표본 중앙값보다 주행거리가 짧으면 가치 상승(+), 길면 가치 하락(-)
        mileage_delta = median_mileage - target.mileage_km
        mileage_adjustment = int((mileage_delta / 10_000.0) * cls.KM_ADJUSTMENT_RATE_PER_10K)

        # 4. 사고/성능점검 상태 보정
        accident_adj = 0
        if target.accident_state == "SIMPLE_REPAIR":
            accident_adj = -cls.ACCIDENT_PENALTY_SIMPLE
        elif target.accident_state in ("MAJOR_ACCIDENT", "STRUCTURAL_DAMAGE"):
            accident_adj = -cls.ACCIDENT_PENALTY_MAJOR
        elif target.accident_state == "UNKNOWN":
            accident_adj = -cls.ACCIDENT_PENALTY_SIMPLE // 2

        # 5. 상태 조정 공정 가치 (Adjusted Fair Value)
        adjusted_fair_value = max(1_000_000, median_price + mileage_adjustment + accident_adj)
        adjusted_advantage_krw = adjusted_fair_value - target.price_krw
        adjusted_advantage_pct = round((adjusted_advantage_krw / adjusted_fair_value) * 100, 2)

        # 6. 기회 점수 계산 (규칙 기반 다차원 스코어링: 0 ~ 100)
        base_score = 50.0

        # A. 가격 경쟁력 (상태 조정 마진율 1%당 2.0점, 최대 ±30점)
        price_score_component = max(-30.0, min(30.0, adjusted_advantage_pct * 2.0))

        # B. 주행거리 절대 매력도 (중앙값 대비 2만km 이하 우위 시 최대 +10점)
        mileage_score_component = max(-10.0, min(10.0, (mileage_delta / 10_000.0) * 5.0))

        # C. 성능점검 및 무사고 신뢰 가점
        condition_component = 0.0
        if target.has_inspection_record:
            condition_component += 5.0
        if target.accident_state == "NO_ACCIDENT":
            condition_component += 5.0
        elif target.accident_state == "SIMPLE_REPAIR":
            condition_component -= 3.0
        elif target.accident_state in ("MAJOR_ACCIDENT", "STRUCTURAL_DAMAGE"):
            condition_component -= 15.0

        # D. 가격 인하 모멘텀 가점 (+5점)
        momentum_component = 5.0 if recent_price_drop else 0.0

        # 종합 계산
        raw_score = (
            base_score
            + price_score_component
            + mileage_score_component
            + condition_component
            + momentum_component
        )

        confidence = cls._calculate_confidence(target)
        if confidence == "MEDIUM":
            raw_score *= 0.95
        elif confidence == "LOW":
            raw_score *= 0.85

        final_score = round(max(0.0, min(100.0, raw_score)), 1)

        # 7. 사유 및 평가 노트 구성
        notes = []
        notes.append(f"동일 비교군 표본 {sample_count}대 중앙 등록가: {median_price:,}원 (대상: {target.price_krw:,}원)")
        if mileage_delta > 0:
            notes.append(f"표본 중앙 주행거리({median_mileage:,}km) 대비 {mileage_delta:,}km 짧아 가치 보정 +{mileage_adjustment:,}원 반영.")
        elif mileage_delta < 0:
            notes.append(f"표본 중앙 주행거리({median_mileage:,}km) 대비 {abs(mileage_delta):,}km 길어 감가 보정 {mileage_adjustment:,}원 반영.")

        if target.accident_state == "NO_ACCIDENT":
            notes.append("완전 무사고 상태 확인됨.")
        elif target.accident_state == "SIMPLE_REPAIR":
            notes.append(f"단순 교환 이력으로 감가 보정 {accident_adj:,}원 반영.")
        elif target.accident_state in ("MAJOR_ACCIDENT", "STRUCTURAL_DAMAGE"):
            notes.append(f"주요 골격 손상/유사고로 큰 폭 감가 보정 {accident_adj:,}원 반영.")

        if recent_price_drop:
            notes.append("최근 가격 인하 이력 관측 (판매 모멘텀 가점 부여).")

        reason = (
            f"조정 시세({adjusted_fair_value:,}원) 대비 {adjusted_advantage_pct}% 가격 경쟁력 확보. "
            f"점수: {final_score}/100"
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
            benchmark_cohort_key=cohort_key,
            sample_count=sample_count,
            benchmark_median_price_krw=median_price,
            raw_price_difference_pct=raw_price_diff_pct,
            adjusted_fair_value_krw=adjusted_fair_value,
            adjusted_advantage_krw=adjusted_advantage_krw,
            adjusted_advantage_pct=adjusted_advantage_pct,
            opportunity_score=final_score,
            evaluation_status="EVALUATED",
            data_confidence=confidence,
            has_recent_price_drop=recent_price_drop,
            selection_reason=reason,
            evaluation_notes=notes,
            evaluated_at=now_dt,
        )

    @classmethod
    def _calculate_confidence(cls, record: StandardListingRecord) -> str:
        """데이터 신뢰도 판정."""
        if not record.has_inspection_record or record.accident_state == "UNKNOWN":
            return "LOW"
        if not record.trim_name or not record.model_generation:
            return "MEDIUM"
        return "HIGH"
