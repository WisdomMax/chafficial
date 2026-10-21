"""전국 중고차 매물 데이터 인입, 시계열 무결성 적재 및 기회 매물 자동 선별 파이프라인.

DIRECTIVE 007-B 규격:
- 007-B 확장 필드(sub_model, powertrain_line, product_type, monthly_payment 등) 지원
- 금융상품 시세 비교군 원천 격리
- 점수 산출 중간 계산값 상세 CSV(export_score_breakdown_csv) 출력 지원
"""

import csv
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from chaficial.models.listing import Listing
from chaficial.models.snapshot import ListingSnapshot
from chaficial.platforms.base import PlatformUrlParser, StandardListingRecord
from chaficial.regions.manager import RegionManager
from chaficial.scorer.opportunity import (
    OpportunityScoreResult,
    OpportunityScorer,
    ScorerParameters,
)


def _to_utc(dt: datetime) -> datetime:
    """naive 또는 aware datetime을 일관된 UTC datetime으로 변환."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class OpportunityPipeline:
    """전국 매물 데이터 인입, 스냅샷 보존 및 기회 스코어링 총괄 파이프라인."""

    @staticmethod
    def load_records_from_csv(csv_path: str | Path) -> list[StandardListingRecord]:
        """CSV 파일에서 표준 매물 레코드 목록 로드 및 엄격 파싱."""
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"매물 CSV 파일을 찾을 수 없습니다: {csv_path}")

        records: list[StandardListingRecord] = []
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=2):
                mfg = row.get("manufacturer", "").strip()
                model = row.get("model_name", "").strip()
                if not mfg or not model:
                    raise ValueError(
                        f"[Line {row_idx}] 제조사 또는 모델명 누락."
                    )

                year_raw = row.get("model_year", "").strip()
                mileage_raw = row.get("mileage_km", "").strip()
                if not mileage_raw:
                    raise ValueError(
                        f"[Line {row_idx}] 필수 숫자 제원(주행거리) 누락."
                    )

                model_year = int(year_raw) if year_raw and year_raw.isdigit() else None
                mileage_km = int(mileage_raw)

                # 금융상품 및 가격 파싱
                product_type = row.get("product_type", "CASH_OR_INSTALLMENT").strip() or "CASH_OR_INSTALLMENT"
                price_raw = row.get("price_krw", "").strip()
                price_krw = int(price_raw) if price_raw else None

                monthly_raw = row.get("monthly_payment_krw", "").strip()
                monthly_payment = int(monthly_raw) if monthly_raw else None

                url = row.get("source_url", "").strip() or None
                platform = row.get("source_platform", "").strip()
                source_id = row.get("source_listing_id", "").strip()

                if url:
                    extracted_platform, extracted_id = (
                        PlatformUrlParser.extract_source_id(url)
                    )
                    if not platform:
                        platform = extracted_platform
                    if not source_id and extracted_id:
                        source_id = extracted_id

                if not platform or platform == "UNKNOWN_PLATFORM":
                    platform = "OTHER"
                if not source_id:
                    raise ValueError(f"[Line {row_idx}] 매물 고유 ID 누락.")

                observed_str = row.get("observed_at", "").strip()
                if not observed_str:
                    raise ValueError(f"[Line {row_idx}] 관측 시각 누락.")
                observed_at = datetime.fromisoformat(observed_str)

                accident_state = row.get("accident_state", "UNKNOWN").strip() or "UNKNOWN"
                accident_verification = row.get("accident_verification", "UNVERIFIED").strip() or "UNVERIFIED"
                has_inspection = row.get("has_inspection_record", "N").strip().upper() in ("Y", "TRUE", "1")

                sub_model = row.get("sub_model", "PRE_FACELIFT").strip() or "PRE_FACELIFT"
                powertrain_line = row.get("powertrain_line", "STANDARD").strip() or "STANDARD"
                reg_ym = row.get("registration_year_month", "").strip() or None
                fuel_type = row.get("fuel_type", "UNKNOWN").strip() or "UNKNOWN"
                transmission = row.get("transmission", "UNKNOWN").strip() or "UNKNOWN"
                raw_loc = row.get("raw_location", "UNKNOWN").strip() or "UNKNOWN"
                data_origin = row.get("data_origin", "MANUALLY_OBSERVED").strip() or "MANUALLY_OBSERVED"
                raw_text = row.get("raw_card_text", "").strip() or None
                trim = row.get("trim_name", "").strip() or None
                gen = row.get("model_generation", "CN7").strip() or "CN7"
                fp = row.get("vehicle_fingerprint", "").strip()
                if not fp:
                    # DIRECTIVE 008-B: 가격을 지문에서 제외한 순수 물리 제원 실차 지문
                    fp = f"{mfg}_{model}_{gen}_{sub_model}_{powertrain_line}_{reg_ym}_{model_year or 'NOYEAR'}_{mileage_km}_{fuel_type}_{trim or 'NOTRIM'}"

                record = StandardListingRecord(
                    source_platform=platform,
                    source_listing_id=source_id,
                    source_url=url,
                    seller_reference=row.get("seller_reference", "").strip() or None,
                    manufacturer=mfg,
                    model_name=model,
                    model_generation=row.get("model_generation", "CN7").strip() or "CN7",
                    sub_model=sub_model,
                    powertrain_line=powertrain_line,
                    trim_name=trim,
                    model_year=model_year,
                    registration_year_month=reg_ym,
                    mileage_km=mileage_km,
                    fuel_type=fuel_type,
                    transmission=transmission,
                    product_type=product_type,
                    price_krw=price_krw,
                    monthly_payment_krw=monthly_payment,
                    raw_location=raw_loc,
                    accident_state=accident_state,
                    accident_verification=accident_verification,
                    has_inspection_record=has_inspection,
                    observed_at=observed_at,
                    listing_status=row.get("listing_status", "ACTIVE").strip() or "ACTIVE",
                    data_origin=data_origin,
                    vehicle_fingerprint=fp,
                    raw_card_text=raw_text,
                )
                records.append(record)

        return records

    @staticmethod
    def ingest_records_to_db(
        session: Session, records: list[StandardListingRecord]
    ) -> dict[str, Any]:
        """매물 레코드를 DB에 적재하고 시계열 가격 변경 스냅샷을 생성."""
        stats = {
            "total_input": len(records),
            "new_listings": 0,
            "existing_listings": 0,
            "new_snapshots": 0,
            "price_changed_count": 0,
            "price_drop_flags": {},
        }

        region_mgr = RegionManager()
        for rec in records:
            resolved_region_id = (
                region_mgr.resolve_region_from_text(rec.raw_location)
                if rec.raw_location != "UNKNOWN"
                else None
            )

            existing_listing = session.execute(
                select(Listing).where(
                    Listing.source_platform == rec.source_platform,
                    Listing.source_listing_id == rec.source_listing_id,
                )
            ).scalar_one_or_none()

            has_price_drop = False
            rec_key = f"{rec.source_platform}:{rec.source_listing_id}"

            # 금융상품은 가격이 None일 수 있으므로 0원으로 안전 저장하거나 스냅샷 보존
            record_price = rec.price_krw if rec.price_krw is not None else 0

            if existing_listing is None:
                new_listing = Listing(
                    source_platform=rec.source_platform,
                    source_listing_id=rec.source_listing_id,
                    seller_reference=rec.seller_reference,
                    first_observed_at=rec.observed_at,
                    raw_location=rec.raw_location,
                    normalized_region_id=resolved_region_id,
                    current_status=rec.listing_status,
                )
                session.add(new_listing)
                session.flush()

                snapshot = ListingSnapshot(
                    listing_id=new_listing.listing_id,
                    observed_at=rec.observed_at,
                    price_krw=record_price,
                    mileage_km=rec.mileage_km,
                    listing_status=rec.listing_status,
                    normalized_region_id=resolved_region_id,
                    raw_specs={"model": rec.model_name, "trim": rec.trim_name, "product_type": rec.product_type},
                )
                session.add(snapshot)
                stats["new_listings"] += 1
                stats["new_snapshots"] += 1

            else:
                stats["existing_listings"] += 1
                latest_snapshot = session.execute(
                    select(ListingSnapshot)
                    .where(ListingSnapshot.listing_id == existing_listing.listing_id)
                    .order_by(ListingSnapshot.observed_at.desc())
                ).scalars().first()

                if latest_snapshot:
                    rec_obs_utc = _to_utc(rec.observed_at)
                    latest_obs_utc = _to_utc(latest_snapshot.observed_at)

                    is_newer = rec_obs_utc >= latest_obs_utc
                    is_duplicate_snapshot = (
                        rec_obs_utc == latest_obs_utc
                        and record_price == latest_snapshot.price_krw
                        and rec.mileage_km == latest_snapshot.mileage_km
                        and rec.listing_status == latest_snapshot.listing_status
                    )

                    if is_newer and not is_duplicate_snapshot:
                        if record_price > 0 and record_price < latest_snapshot.price_krw:
                            has_price_drop = True
                            existing_listing.current_status = "PRICE_CHANGED"
                            stats["price_changed_count"] += 1

                        if (
                            record_price != latest_snapshot.price_krw
                            or rec.mileage_km != latest_snapshot.mileage_km
                            or rec.listing_status != latest_snapshot.listing_status
                        ):
                            new_snapshot = ListingSnapshot(
                                listing_id=existing_listing.listing_id,
                                observed_at=rec.observed_at,
                                price_krw=record_price,
                                mileage_km=rec.mileage_km,
                                listing_status=rec.listing_status,
                                normalized_region_id=resolved_region_id or existing_listing.normalized_region_id,
                                raw_specs={"model": rec.model_name, "trim": rec.trim_name, "product_type": rec.product_type},
                            )
                            session.add(new_snapshot)
                            stats["new_snapshots"] += 1

            stats["price_drop_flags"][rec_key] = has_price_drop

        session.commit()
        return stats

    @staticmethod
    def evaluate_all(
        records: list[StandardListingRecord],
        price_drop_flags: dict[str, bool] | None = None,
        params: ScorerParameters | None = None,
    ) -> list[OpportunityScoreResult]:
        """전체 매물 레코드에 대해 Leave-One-Out 독립 코호트 기회 평가 수행."""
        drop_flags = price_drop_flags or {}
        cohort_map: dict[str, list[StandardListingRecord]] = defaultdict(list)
        for rec in records:
            key = OpportunityScorer.make_cohort_key(rec)
            cohort_map[key].append(rec)

        results: list[OpportunityScoreResult] = []
        for rec in records:
            cohort_key = OpportunityScorer.make_cohort_key(rec)
            cohort = cohort_map[cohort_key]
            rec_key = f"{rec.source_platform}:{rec.source_listing_id}"
            has_drop = drop_flags.get(rec_key, False)

            res = OpportunityScorer.evaluate_listing(
                target=rec, cohort_records=cohort, params=params, recent_price_drop=has_drop
            )
            results.append(res)

        # EVALUATED 상태 우선, 기회 점수 내림차순 정렬
        results.sort(
            key=lambda x: (
                x.evaluation_status == "EVALUATED",
                x.opportunity_score is not None,
                x.opportunity_score or -1.0,
            ),
            reverse=True,
        )
        return results

    @staticmethod
    def export_top_opportunities_to_csv(
        results: list[OpportunityScoreResult],
        output_path: str | Path,
        top_n: int = 10,
        deduplicate_by_fingerprint: bool = True,
    ) -> list[OpportunityScoreResult]:
        """유효하게 평가된 상위 N개 기회 매물만 선별하여 CSV 파일로 저장.

        DIRECTIVE 008-B:
        deduplicate_by_fingerprint=True 시 동일 실차(vehicle_fingerprint) 중복 매물은
        점수 순으로 1건(Canonical Record)만 선별하여 Top N 목록에 쌍둥이 매물 중복 노출을 원천 차단.
        """
        evaluated_candidates = [
            r for r in results if r.evaluation_status == "EVALUATED"
        ]

        if deduplicate_by_fingerprint:
            seen_fingerprints: set[str] = set()
            unique_candidates: list[OpportunityScoreResult] = []
            for item in evaluated_candidates:
                fp = item.vehicle_fingerprint
                if fp:
                    if fp in seen_fingerprints:
                        continue
                    seen_fingerprints.add(fp)
                unique_candidates.append(item)
            top_candidates = unique_candidates[:top_n]
        else:
            top_candidates = evaluated_candidates[:top_n]

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "rank",
            "opportunity_score",
            "recommendation_category",
            "overall_confidence",
            "data_completeness_score",
            "valuation_uncertainty_score",
            "evaluation_status",
            "data_confidence",
            "data_origin",
            "vehicle_summary",
            "vehicle_fingerprint",
            "price_krw",
            "adjusted_fair_value_krw",
            "adjusted_advantage_pct",
            "benchmark_median_price_krw",
            "normalized_baseline_median_krw",
            "sample_count",
            "missing_attributes",
            "source_platform",
            "source_listing_id",
            "source_url",
            "selection_reason",
        ]

        with open(path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for idx, item in enumerate(top_candidates, start=1):
                writer.writerow(
                    {
                        "rank": idx,
                        "opportunity_score": item.opportunity_score
                        if item.opportunity_score is not None
                        else "N/A",
                        "recommendation_category": item.recommendation_category,
                        "overall_confidence": item.overall_confidence,
                        "data_completeness_score": f"{item.data_completeness_score * 100:.0f}%",
                        "valuation_uncertainty_score": f"±{item.valuation_uncertainty_score}%"
                        if item.valuation_uncertainty_score is not None
                        else "N/A",
                        "evaluation_status": item.evaluation_status,
                        "data_confidence": item.data_confidence,
                        "data_origin": item.data_origin,
                        "vehicle_summary": item.vehicle_summary,
                        "vehicle_fingerprint": item.vehicle_fingerprint or "N/A",
                        "price_krw": f"{item.price_krw:,}원" if item.price_krw else "N/A",
                        "adjusted_fair_value_krw": f"{item.adjusted_fair_value_krw:,}원"
                        if item.adjusted_fair_value_krw
                        else "N/A",
                        "adjusted_advantage_pct": f"{item.adjusted_advantage_pct:+0.2f}%"
                        if item.adjusted_advantage_pct is not None
                        else "N/A",
                        "benchmark_median_price_krw": f"{item.benchmark_median_price_krw:,}원"
                        if item.benchmark_median_price_krw
                        else "N/A",
                        "normalized_baseline_median_krw": f"{item.normalized_baseline_median_krw:,}원"
                        if item.normalized_baseline_median_krw
                        else "N/A",
                        "sample_count": item.sample_count,
                        "missing_attributes": "; ".join(item.missing_attributes) if item.missing_attributes else "NONE",
                        "source_platform": item.source_platform,
                        "source_listing_id": item.source_listing_id,
                        "source_url": item.source_url or "",
                        "selection_reason": item.selection_reason,
                    }
                )

        return top_candidates

    @staticmethod
    def export_actionable_recommendations_csv(
        results: list[OpportunityScoreResult],
        output_path: str | Path,
        max_n: int = 20,
    ) -> list[OpportunityScoreResult]:
        """DIRECTIVE 008-C: 실질 검토 및 추천 가능한 고신뢰도 기회 매물만 선별.

        선별 기준:
        1. evaluation_status == 'EVALUATED'
        2. recommendation_category == 'RECOMMENDED' (MANUAL_REVIEW_NEEDED 배제)
        3. overall_confidence in ('HIGH', 'MEDIUM') (LOW, UNRELIABLE 배제)
        4. price_krw is not None and price_krw > 0 (가격 결측/금융상품 원천 배제)
        5. 실차 지문 기준 중복 제거 (고유 실차당 최고점 1건만 선별)
        6. 조건을 만족하는 실제 수량만 출력 (부족분을 채우기 위해 기준을 완화하지 않음)
        """
        valid_actionable = [
            r for r in results
            if r.evaluation_status == "EVALUATED"
            and r.recommendation_category == "RECOMMENDED"
            and r.overall_confidence in ("HIGH", "MEDIUM")
            and r.price_krw is not None
            and r.price_krw > 0
        ]

        seen_fingerprints: set[str] = set()
        unique_actionable: list[OpportunityScoreResult] = []
        for item in valid_actionable:
            fp = item.vehicle_fingerprint
            if fp:
                if fp in seen_fingerprints:
                    continue
                seen_fingerprints.add(fp)
            unique_actionable.append(item)

        final_candidates = unique_actionable[:max_n]

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "rank",
            "opportunity_score",
            "overall_confidence",
            "data_completeness_score",
            "valuation_uncertainty_score",
            "vehicle_summary",
            "vehicle_fingerprint",
            "price_krw",
            "adjusted_fair_value_krw",
            "adjusted_advantage_pct",
            "sample_count",
            "source_platform",
            "source_listing_id",
            "source_url",
            "selection_reason",
        ]

        with open(path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for idx, item in enumerate(final_candidates, start=1):
                writer.writerow(
                    {
                        "rank": idx,
                        "opportunity_score": item.opportunity_score,
                        "overall_confidence": item.overall_confidence,
                        "data_completeness_score": f"{item.data_completeness_score * 100:.0f}%",
                        "valuation_uncertainty_score": f"±{item.valuation_uncertainty_score}%",
                        "vehicle_summary": item.vehicle_summary,
                        "vehicle_fingerprint": item.vehicle_fingerprint or "N/A",
                        "price_krw": f"{item.price_krw:,}원",
                        "adjusted_fair_value_krw": f"{item.adjusted_fair_value_krw:,}원" if item.adjusted_fair_value_krw else "N/A",
                        "adjusted_advantage_pct": f"{item.adjusted_advantage_pct:+0.2f}%" if item.adjusted_advantage_pct is not None else "N/A",
                        "sample_count": item.sample_count,
                        "source_platform": item.source_platform,
                        "source_listing_id": item.source_listing_id,
                        "source_url": item.source_url or "",
                        "selection_reason": item.selection_reason,
                    }
                )

        return final_candidates

    @staticmethod
    def export_manual_review_candidates_to_csv(
        results: list[OpportunityScoreResult],
        output_path: str | Path,
    ) -> list[OpportunityScoreResult]:
        """DIRECTIVE 008: 신뢰도가 낮거나 불확실성이 커서 상세 확인이 필요한 매물 목록 저장."""
        review_candidates = [
            r for r in results if r.recommendation_category == "MANUAL_REVIEW_NEEDED"
        ]

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "listing_id",
            "opportunity_score",
            "overall_confidence",
            "data_completeness_score",
            "missing_attributes",
            "valuation_uncertainty_score",
            "price_krw",
            "sample_count",
            "vehicle_summary",
            "review_reason",
            "source_url",
        ]

        with open(path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in review_candidates:
                reasons = []
                if item.overall_confidence in ("LOW", "UNRELIABLE"):
                    reasons.append(f"신뢰도부족({item.overall_confidence})")
                if item.data_completeness_score < 0.65:
                    reasons.append(f"데이터불완전({item.data_completeness_score*100:.0f}%)")
                if item.missing_attributes:
                    reasons.append(f"누락속성({','.join(item.missing_attributes)})")
                if not reasons:
                    reasons.append("상세검증필요")

                writer.writerow(
                    {
                        "listing_id": item.listing_id,
                        "opportunity_score": item.opportunity_score if item.opportunity_score is not None else "N/A",
                        "overall_confidence": item.overall_confidence,
                        "data_completeness_score": f"{item.data_completeness_score * 100:.0f}%",
                        "missing_attributes": "; ".join(item.missing_attributes) if item.missing_attributes else "NONE",
                        "valuation_uncertainty_score": f"±{item.valuation_uncertainty_score}%" if item.valuation_uncertainty_score is not None else "N/A",
                        "price_krw": f"{item.price_krw:,}원" if item.price_krw else "N/A",
                        "sample_count": item.sample_count,
                        "vehicle_summary": item.vehicle_summary,
                        "review_reason": " | ".join(reasons),
                        "source_url": item.source_url or "",
                    }
                )

        return review_candidates

    @staticmethod
    def export_score_breakdown_csv(
        results: list[OpportunityScoreResult],
        output_path: str | Path,
    ) -> None:
        """DIRECTIVE 007-B: 모든 평가 매물의 세부 중간 계산값을 투명하게 CSV로 출력."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "listing_id",
            "evaluation_status",
            "opportunity_score",
            "recommendation_category",
            "overall_confidence",
            "data_completeness_score",
            "valuation_uncertainty_score",
            "base_score",
            "price_component",
            "mileage_component",
            "condition_component",
            "momentum_component",
            "raw_score",
            "confidence_multiplier",
            "data_confidence",
            "sample_count",
            "price_krw",
            "normalized_baseline_median_krw",
            "adjusted_fair_value_krw",
            "adjusted_advantage_pct",
            "source_url",
        ]

        with open(path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(
                    {
                        "listing_id": r.listing_id,
                        "evaluation_status": r.evaluation_status,
                        "opportunity_score": r.opportunity_score if r.opportunity_score is not None else "N/A",
                        "recommendation_category": r.recommendation_category,
                        "overall_confidence": r.overall_confidence,
                        "data_completeness_score": f"{r.data_completeness_score * 100:.0f}%",
                        "valuation_uncertainty_score": f"±{r.valuation_uncertainty_score}%" if r.valuation_uncertainty_score is not None else "N/A",
                        "base_score": r.base_score,
                        "price_component": f"{r.price_component:+.2f}",
                        "mileage_component": f"{r.mileage_component:+.2f}",
                        "condition_component": f"{r.condition_component:+.2f}",
                        "momentum_component": f"{r.momentum_component:+.2f}",
                        "raw_score": f"{r.raw_score:.2f}",
                        "confidence_multiplier": r.confidence_multiplier,
                        "data_confidence": r.data_confidence,
                        "sample_count": r.sample_count,
                        "price_krw": r.price_krw if r.price_krw is not None else "N/A",
                        "normalized_baseline_median_krw": r.normalized_baseline_median_krw if r.normalized_baseline_median_krw else "N/A",
                        "adjusted_fair_value_krw": r.adjusted_fair_value_krw if r.adjusted_fair_value_krw else "N/A",
                        "adjusted_advantage_pct": f"{r.adjusted_advantage_pct:+.2f}%" if r.adjusted_advantage_pct is not None else "N/A",
                        "source_url": r.source_url or "",
                    }
                )
