"""차피셜 시세 정확도 및 오차(Valuation Accuracy) 통계 검증 엔진 (DIRECTIVE 008-A).

개선 사항:
1. Leave-One-Out 평가 시 동일 실차 지문 매물 완전 배제 (데이터 누출 원천 차단)
2. 분위수(P50, P75, P90, P95) 정밀 산출
3. 모델연도 확정 코호트 vs 미확인(UNKNOWN_YEAR) 코호트 분리 집계
4. 원시 평가 레코드 CSV (독립 표본 ID 목록 포함) 저장 지원
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
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
    mape_pct: float  # Mean Absolute Percentage Error (평균 백분율 오차 % - 분모: actual_price)
    smape_pct: float  # Symmetric Mean Absolute Percentage Error (대칭 백분율 오차 %)

    # 분위수 (Quantiles)
    p50_krw: float = 0.0
    p75_krw: float = 0.0
    p90_krw: float = 0.0
    p95_krw: float = 0.0
    p50_mape: float = 0.0
    p75_mape: float = 0.0
    p90_mape: float = 0.0
    p95_mape: float = 0.0

    # DIRECTIVE 008-B: 베이스라인(단순 코호트 중앙가) 대비 상태보정 모델 성능 비교
    baseline_mae_krw: float = 0.0
    baseline_mdae_krw: float = 0.0
    baseline_mape_pct: float = 0.0
    mae_improvement_pct: float = 0.0  # MAE 오차 감소율 (%)
    mape_improvement_pct: float = 0.0  # MAPE 오차 감소율 (%)

    # 연식 확정 vs 미확인 코호트 분리 통계
    confirmed_year_stats: dict[str, Any] = field(default_factory=dict)
    unknown_year_stats: dict[str, Any] = field(default_factory=dict)

    cohort_breakdown: dict[str, dict[str, Any]] = field(default_factory=dict)
    individual_errors: list[dict[str, Any]] = field(default_factory=list)
    # DIRECTIVE 008-C: 평가 제외 표본 및 상세 제외 사유 전수 추적
    excluded_records: list[dict[str, Any]] = field(default_factory=list)


def _calc_percentile(sorted_list: list[float], percentile: float) -> float:
    """정렬된 리스트에서 분위수(0.0~1.0) 계산."""
    if not sorted_list:
        return 0.0
    k = (len(sorted_list) - 1) * percentile
    f = int(k)
    c = min(f + 1, len(sorted_list) - 1)
    d = k - f
    return sorted_list[f] + d * (sorted_list[c] - sorted_list[f])


class ValuationValidator:
    """시세 평가 모델 정확도 검증 및 민감도 분석기 (DIRECTIVE 008-A)."""

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

        errors_abs: list[float] = []
        errors_pct: list[float] = []
        errors_smape: list[float] = []
        baseline_errors_abs: list[float] = []
        baseline_errors_pct: list[float] = []
        individual_records: list[dict[str, Any]] = []
        excluded_records: list[dict[str, Any]] = []
        cohort_groups: dict[str, list[dict[str, Any]]] = {}

        # 1. 가격 결측 또는 금융 상품 매물은 즉시 제외 목록으로 분류
        for rec in records:
            if rec.product_type != "CASH_OR_INSTALLMENT":
                excluded_records.append({
                    "listing_id": rec.source_listing_id,
                    "vehicle_fingerprint": rec.vehicle_fingerprint or "N/A",
                    "model_name": rec.model_name,
                    "sub_model": rec.sub_model,
                    "model_year": rec.model_year or "UNKNOWN",
                    "trim_name": rec.trim_name or "UNKNOWN",
                    "product_type": rec.product_type,
                    "price_krw": "NULL",
                    "exclusion_category": "FINANCIAL_PRODUCT",
                    "exclusion_reason": f"금융상품({rec.product_type}): 월 납입액 매물로 일반 시세 평가 대상 제외",
                    "sample_count": 0,
                })
            elif rec.price_krw is None or rec.price_krw <= 0:
                excluded_records.append({
                    "listing_id": rec.source_listing_id,
                    "vehicle_fingerprint": rec.vehicle_fingerprint or "N/A",
                    "model_name": rec.model_name,
                    "sub_model": rec.sub_model,
                    "model_year": rec.model_year or "UNKNOWN",
                    "trim_name": rec.trim_name or "UNKNOWN",
                    "product_type": rec.product_type,
                    "price_krw": "NULL",
                    "exclusion_category": "MISSING_PRICE",
                    "exclusion_reason": "가격 미확인 또는 0원 결측 매물",
                    "sample_count": 0,
                })

        for rec in valid_records:
            # Leave-One-Out 단일 매물 평가 (지문 일치 중복 매물도 비교군에서 제외됨)
            res = OpportunityScorer.evaluate_listing(
                target=rec, cohort_records=valid_records, params=cfg
            )

            # 유효하게 상태조정시세가 산출된 매물만 대상
            if res.evaluation_status == "EVALUATED" and res.adjusted_fair_value_krw:
                actual_price = float(rec.price_krw)
                predicted_price = float(res.adjusted_fair_value_krw)

                abs_err = abs(actual_price - predicted_price)
                # DIRECTIVE 008-B: 정통 MAPE 공식 적용 (분모: actual_price)
                pct_err = (abs_err / actual_price) * 100.0
                smape_val = (2.0 * abs_err / (actual_price + predicted_price)) * 100.0

                errors_abs.append(abs_err)
                errors_pct.append(pct_err)
                errors_smape.append(smape_val)

                # 베이스라인(단순 코호트 중앙가) 오차 계산
                baseline_price = float(res.benchmark_median_price_krw) if res.benchmark_median_price_krw else actual_price
                base_abs_err = abs(actual_price - baseline_price)
                base_pct_err = (base_abs_err / actual_price) * 100.0
                baseline_errors_abs.append(base_abs_err)
                baseline_errors_pct.append(base_pct_err)

                # 비교군에 실제로 사용된 독립 표본 ID 추출
                independent_ids = []
                for other in valid_records:
                    if OpportunityScorer.make_cohort_key(other) != res.benchmark_cohort_key:
                        continue
                    if other.source_listing_id == rec.source_listing_id:
                        continue
                    if rec.vehicle_fingerprint and other.vehicle_fingerprint == rec.vehicle_fingerprint:
                        continue
                    independent_ids.append(other.source_listing_id)

                year_cat = "CONFIRMED_YEAR" if rec.model_year is not None else "UNKNOWN_YEAR"
                accident_cat = "VERIFIED_OR_CLAIMED" if rec.accident_state != "UNKNOWN" else "UNKNOWN"

                item_info = {
                    "listing_id": rec.source_listing_id,
                    "vehicle_fingerprint": rec.vehicle_fingerprint or "N/A",
                    "cohort_key": res.benchmark_cohort_key,
                    "model_year_category": year_cat,
                    "accident_category": accident_cat,
                    "sample_count": res.sample_count,
                    "actual_price_krw": int(actual_price),
                    "predicted_price_krw": int(predicted_price),
                    "abs_error_krw": int(abs_err),
                    "pct_error": round(pct_err, 2),
                    "smape_error": round(smape_val, 2),
                    "baseline_price_krw": int(baseline_price),
                    "baseline_abs_error_krw": int(base_abs_err),
                    "baseline_pct_error": round(base_pct_err, 2),
                    "data_completeness": res.data_completeness_score,
                    "accident_state": rec.accident_state,
                    "independent_sample_ids": "; ".join(independent_ids),
                }
                individual_records.append(item_info)

                ckey = res.benchmark_cohort_key
                if ckey not in cohort_groups:
                    cohort_groups[ckey] = []
                cohort_groups[ckey].append(item_info)
            else:
                # 독립 표본 부족 등으로 평가 보류된 매물 추적
                excluded_records.append({
                    "listing_id": rec.source_listing_id,
                    "vehicle_fingerprint": rec.vehicle_fingerprint or "N/A",
                    "model_name": rec.model_name,
                    "sub_model": rec.sub_model,
                    "model_year": rec.model_year or "UNKNOWN",
                    "trim_name": rec.trim_name or "UNKNOWN",
                    "product_type": rec.product_type,
                    "price_krw": rec.price_krw,
                    "exclusion_category": res.evaluation_status,
                    "exclusion_reason": res.selection_reason,
                    "sample_count": res.sample_count,
                })

        if not errors_abs:
            return ValuationErrorSummary(
                total_evaluated_count=0,
                mae_krw=0.0,
                mdae_krw=0.0,
                mape_pct=0.0,
                smape_pct=0.0,
            )

        sorted_abs = sorted(errors_abs)
        sorted_pct = sorted(errors_pct)

        mae_val = round(mean(errors_abs), 0)
        mdae_val = round(median(errors_abs), 0)
        mape_val = round(mean(errors_pct), 2)
        smape_val_mean = round(mean(errors_smape), 2)

        base_mae = round(mean(baseline_errors_abs), 0) if baseline_errors_abs else 0.0
        base_mdae = round(median(baseline_errors_abs), 0) if baseline_errors_abs else 0.0
        base_mape = round(mean(baseline_errors_pct), 2) if baseline_errors_pct else 0.0

        mae_improvement = round(((base_mae - mae_val) / base_mae) * 100.0, 2) if base_mae > 0 else 0.0
        mape_improvement = round(((base_mape - mape_val) / base_mape) * 100.0, 2) if base_mape > 0 else 0.0

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

        # 연식 확정 vs 미확인 집단 통계 분리
        conf_items = [x for x in individual_records if x["model_year_category"] == "CONFIRMED_YEAR"]
        unkn_items = [x for x in individual_records if x["model_year_category"] == "UNKNOWN_YEAR"]

        def _sub_stats(items: list[dict[str, Any]]) -> dict[str, Any]:
            if not items:
                return {"count": 0, "mae_krw": 0, "mdae_krw": 0, "mape_pct": 0.0}
            c_abs = [x["abs_error_krw"] for x in items]
            c_pct = [x["pct_error"] for x in items]
            return {
                "count": len(items),
                "mae_krw": round(mean(c_abs), 0),
                "mdae_krw": round(median(c_abs), 0),
                "mape_pct": round(mean(c_pct), 2),
            }

        return ValuationErrorSummary(
            total_evaluated_count=len(errors_abs),
            mae_krw=mae_val,
            mdae_krw=mdae_val,
            mape_pct=mape_val,
            smape_pct=smape_val_mean,
            p50_krw=round(_calc_percentile(sorted_abs, 0.50), 0),
            p75_krw=round(_calc_percentile(sorted_abs, 0.75), 0),
            p90_krw=round(_calc_percentile(sorted_abs, 0.90), 0),
            p95_krw=round(_calc_percentile(sorted_abs, 0.95), 0),
            p50_mape=round(_calc_percentile(sorted_pct, 0.50), 2),
            p75_mape=round(_calc_percentile(sorted_pct, 0.75), 2),
            p90_mape=round(_calc_percentile(sorted_pct, 0.90), 2),
            p95_mape=round(_calc_percentile(sorted_pct, 0.95), 2),
            baseline_mae_krw=base_mae,
            baseline_mdae_krw=base_mdae,
            baseline_mape_pct=base_mape,
            mae_improvement_pct=mae_improvement,
            mape_improvement_pct=mape_improvement,
            confirmed_year_stats=_sub_stats(conf_items),
            unknown_year_stats=_sub_stats(unkn_items),
            cohort_breakdown=cohort_stats,
            individual_errors=individual_records,
            excluded_records=excluded_records,
        )

    @classmethod
    def evaluate_unique_vehicles(
        cls,
        records: list[StandardListingRecord],
        params: ScorerParameters | None = None,
    ) -> ValuationErrorSummary:
        """DIRECTIVE 008-B: 고유 실차(Canonical Record) 기준 시세 예측 오차 집계.

        동일 물리 지문(vehicle_fingerprint)을 가진 중복 매물 중 대표 1건(Canonical Record)만 선별하여
        독립 실차 집합 기준으로 Leave-One-Out 교차 검증을 수행합니다.
        """
        seen_fingerprints: set[str] = set()
        canonical_records: list[StandardListingRecord] = []

        # 대표 레코드 선별 (완전성 및 최신성 우선)
        for rec in records:
            fp = rec.vehicle_fingerprint
            if not fp:
                canonical_records.append(rec)
                continue
            if fp not in seen_fingerprints:
                seen_fingerprints.add(fp)
                canonical_records.append(rec)

        return cls.evaluate_valuation_accuracy(canonical_records, params=params)

    @classmethod
    def export_raw_valuation_records_csv(
        cls,
        summary: ValuationErrorSummary,
        output_path: str | Path,
    ) -> None:
        """DIRECTIVE 008-B: 모든 평가 매물의 실제 호가, 상태보정예측가, 베이스라인예측가, 오차, 사용된 비교 표본 ID 목록 CSV 저장."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "listing_id",
            "vehicle_fingerprint",
            "cohort_key",
            "model_year_category",
            "accident_category",
            "sample_count",
            "actual_price_krw",
            "predicted_price_krw",
            "abs_error_krw",
            "pct_error",
            "smape_error",
            "baseline_price_krw",
            "baseline_abs_error_krw",
            "baseline_pct_error",
            "data_completeness",
            "accident_state",
            "independent_sample_ids",
        ]

        with open(path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary.individual_errors)

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
                return {"count": 0, "mae_krw": 0, "mdae_krw": 0, "mape_pct": 0.0}
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

        def _get_top_ids(params: ScorerParameters) -> list[str]:
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

    @classmethod
    def export_excluded_records_csv(
        cls,
        summary: ValuationErrorSummary,
        output_path: str | Path,
    ) -> None:
        """DIRECTIVE 008-C: 시세 평가에서 제외된 표본(표본부족, 금융상품, 가격결측 등) 전수 명세 CSV 저장."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "listing_id",
            "vehicle_fingerprint",
            "model_name",
            "sub_model",
            "model_year",
            "trim_name",
            "product_type",
            "price_krw",
            "exclusion_category",
            "exclusion_reason",
            "sample_count",
        ]

        with open(path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(summary.excluded_records)
