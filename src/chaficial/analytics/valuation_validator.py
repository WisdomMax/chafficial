"""차피셜 시세 정확도 및 오차(Valuation Accuracy) 통계 검증 엔진 (DIRECTIVE 008).

핵심 지표:
1. Leave-One-Out 기반 각 매물의 공정 시세(Fair Value) 예측 오차 산출
2. MAE, MdAE, MAPE, sMAPE 통계 측정
3. 코호트별 표본 수와 오차 상관관계 분석
4. 주행거리 감가 계수(km_rate) 민감도 분석 (30만/40만/50만원)
5. 사고/옵션 정보 누락(완전성)에 따른 오차 영향도 분석
6. 상위 추천 순위의 파라미터 변화 안정성(Rank Stability) 분석
"""

from dataclasses import dataclass, field
from statistics import mean, median
from typing import Any

from chaficial.platforms.base import StandardListingRecord
from chaficial.scorer.opportunity import OpportunityScorer, ScorerParameters


@dataclass
class ValuationErrorSummary:
    """시세 예측 오차 집계 통계 DTO."""

    total_evaluated_count: int
    mae_krw: float  # Mean Absolute Error (평균 절대 오차)
    mdae_krw: float  # Median Absolute Error (중앙값 절대 오차)
    mape_pct: float  # Mean Absolute Percentage Error (평균 백분율 오차 %)
    smape_pct: float  # Symmetric Mean Absolute Percentage Error (대칭 백분율 오차 %)
    cohort_breakdown: dict[str, dict[str, Any]] = field(default_factory=dict)
    individual_errors: list[dict[str, Any]] = field(default_factory=list)


class ValuationValidator:
    """시세 평가 모델 정확도 검증 및 민감도 분석기."""

    @classmethod
    def evaluate_valuation_accuracy(
        cls,
        records: list[StandardListingRecord],
        params: ScorerParameters | None = None,
    ) -> ValuationErrorSummary:
        """전체 매물 대상 Leave-One-Out 교차 검증으로 시세 예측 오차 산출."""
        cfg = params or ScorerParameters()

        # 유효 현금/할부 매매 매물만 평가 대상
        valid_records = [
            r for r in records
            if r.product_type == "CASH_OR_INSTALLMENT"
            and r.price_krw is not None
            and r.price_krw > 0
        ]

        errors_abs = []
        errors_pct = []
        errors_smape = []
        individual_records = []
        cohort_groups: dict[str, list[dict[str, Any]]] = {}

        for rec in valid_records:
            # Leave-One-Out 단일 매물 평가
            res = OpportunityScorer.evaluate_listing(
                target=rec, cohort_records=valid_records, params=cfg
            )

            # 독립 비교 표본이 충분하여 유효하게 상태조정시세가 산출된 매물만 대상
            if res.evaluation_status == "EVALUATED" and res.adjusted_fair_value_krw:
                actual_price = rec.price_krw
                predicted_price = res.adjusted_fair_value_krw

                abs_err = abs(actual_price - predicted_price)
                pct_err = (abs_err / predicted_price) * 100.0
                smape_val = (2.0 * abs_err / (actual_price + predicted_price)) * 100.0

                errors_abs.append(abs_err)
                errors_pct.append(pct_err)
                errors_smape.append(smape_val)

                item_info = {
                    "listing_id": rec.source_listing_id,
                    "cohort_key": res.benchmark_cohort_key,
                    "sample_count": res.sample_count,
                    "actual_price_krw": actual_price,
                    "predicted_price_krw": predicted_price,
                    "abs_error_krw": abs_err,
                    "pct_error": round(pct_err, 2),
                    "smape_error": round(smape_val, 2),
                    "data_completeness": res.data_completeness_score,
                    "accident_state": rec.accident_state,
                }
                individual_records.append(item_info)

                ckey = res.benchmark_cohort_key
                if ckey not in cohort_groups:
                    cohort_groups[ckey] = []
                cohort_groups[ckey].append(item_info)

        if not errors_abs:
            return ValuationErrorSummary(
                total_evaluated_count=0,
                mae_krw=0.0,
                mdae_krw=0.0,
                mape_pct=0.0,
                smape_pct=0.0,
            )

        # 코호트별 세부 오차 집계
        cohort_stats = {}
        for ckey, items in cohort_groups.items():
            c_abs = [x["abs_error_krw"] for x in items]
            c_pct = [x["pct_error"] for x in items]
            cohort_stats[ckey] = {
                "evaluated_count": len(items),
                "mae_krw": round(mean(c_abs), 0),
                "mdae_krw": round(median(c_abs), 0),
                "mape_pct": round(mean(c_pct), 2),
            }

        return ValuationErrorSummary(
            total_evaluated_count=len(errors_abs),
            mae_krw=round(mean(errors_abs), 0),
            mdae_krw=round(median(errors_abs), 0),
            mape_pct=round(mean(errors_pct), 2),
            smape_pct=round(mean(errors_smape), 2),
            cohort_breakdown=cohort_stats,
            individual_errors=individual_records,
        )

    @classmethod
    def sensitivity_analysis_km_rate(
        cls,
        records: list[StandardListingRecord],
        km_rates: list[int] = None,
    ) -> dict[int, dict[str, Any]]:
        """1만km당 감가 보정액(km_rate_per_10k) 변화에 따른 시세 오차 민감도 분석."""
        rates = km_rates or [300_000, 400_000, 500_000]
        results = {}

        for rate in rates:
            params = ScorerParameters(km_rate_per_10k=rate)
            summary = cls.evaluate_valuation_accuracy(records, params=params)
            results[rate] = {
                "km_rate_per_10k": rate,
                "evaluated_count": summary.total_evaluated_count,
                "mae_krw": summary.mae_krw,
                "mdae_krw": summary.mdae_krw,
                "mape_pct": summary.mape_pct,
                "smape_pct": summary.smape_pct,
            }

        return results

    @classmethod
    def completeness_impact_analysis(
        cls,
        records: list[StandardListingRecord],
    ) -> dict[str, dict[str, Any]]:
        """데이터 완전성(사고여부 확인 여부 등)에 따른 시세 예측 오차 비교 분석."""
        summary = cls.evaluate_valuation_accuracy(records)
        complete_items = [x for x in summary.individual_errors if x["accident_state"] != "UNKNOWN"]
        incomplete_items = [x for x in summary.individual_errors if x["accident_state"] == "UNKNOWN"]

        def _calc_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
            if not items:
                return {"count": 0, "mae_krw": 0, "mape_pct": 0.0}
            c_abs = [x["abs_error_krw"] for x in items]
            c_pct = [x["pct_error"] for x in items]
            return {
                "count": len(items),
                "mae_krw": round(mean(c_abs), 0),
                "mdae_krw": round(median(c_abs), 0),
                "mape_pct": round(mean(c_pct), 2),
            }

        return {
            "ALL_EVALUATED": {
                "count": summary.total_evaluated_count,
                "mae_krw": summary.mae_krw,
                "mape_pct": summary.mape_pct,
            },
            "VERIFIED_OR_CLAIMED_ACCIDENT_STATE": _calc_stats(complete_items),
            "UNKNOWN_ACCIDENT_STATE": _calc_stats(incomplete_items),
        }

    @classmethod
    def rank_stability_analysis(
        cls,
        records: list[StandardListingRecord],
        top_n: int = 20,
    ) -> dict[str, Any]:
        """파라미터 변동(km_rate: 30만 vs 40만 vs 50만) 시 상위 N개 추천 순위 안정성 분석."""
        p_base = ScorerParameters(km_rate_per_10k=400_000)
        p_low = ScorerParameters(km_rate_per_10k=300_000)
        p_high = ScorerParameters(km_rate_per_10k=500_000)

        # 각 파라미터별 전체 평가 및 Top-N ID 추출
        from chaficial.pipeline.ingest_and_score import OpportunityPipeline

        def _get_top_ids(params: ScorerParameters) -> list[str]:
            # evaluate_all에 params를 전달하여 평가
            cohort_map = {}
            for r in records:
                k = OpportunityScorer.make_cohort_key(r)
                if k not in cohort_map:
                    cohort_map[k] = []
                cohort_map[k].append(r)

            results = []
            for r in records:
                k = OpportunityScorer.make_cohort_key(r)
                res = OpportunityScorer.evaluate_listing(
                    target=r, cohort_records=cohort_map[k], params=params
                )
                results.append(res)

            evaluated = [x for x in results if x.evaluation_status == "EVALUATED"]
            evaluated.sort(key=lambda x: (x.opportunity_score or -1.0), reverse=True)
            return [x.listing_id for x in evaluated[:top_n]]

        top_base = _get_top_ids(p_base)
        top_low = _get_top_ids(p_low)
        top_high = _get_top_ids(p_high)

        # Jaccard 유사도 계산 (상위 집합의 보존율)
        set_base = set(top_base)
        set_low = set(top_low)
        set_high = set(top_high)

        jaccard_low = len(set_base & set_low) / max(1, len(set_base | set_low))
        jaccard_high = len(set_base & set_high) / max(1, len(set_base | set_high))

        return {
            "top_n": top_n,
            "base_count": len(top_base),
            "jaccard_base_vs_low_km_rate": round(jaccard_low * 100, 1),
            "jaccard_base_vs_high_km_rate": round(jaccard_high * 100, 1),
            "top_10_overlap_count_low": len(set(top_base[:10]) & set(top_low[:10])),
            "top_10_overlap_count_high": len(set(top_base[:10]) & set(top_high[:10])),
        }
