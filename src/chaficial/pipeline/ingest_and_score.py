"""전국 중고차 매물 데이터 인입, 시계열 무결성 적재 및 기회 매물 자동 선별 파이프라인.

DIRECTIVE 007 무결성 수정:
- 누락 데이터 위조 금지 (기본값 남발 방지)
- 늦게 도착한 과거 관측 자료의 최신 상태 오염 방지
- 동일 시각/동일 가격 재입력 중복 스냅샷 방지
- 장안평 기본 지역 강제 연결 배제
- 평가 불가 차량 Top 추천 목록 분리
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
from chaficial.scorer.opportunity import OpportunityScorer, OpportunityScoreResult


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
                # 1. 필수 제원 검증 (누락 시 위조 금지, 즉시 에러)
                mfg = row.get("manufacturer", "").strip()
                model = row.get("model_name", "").strip()
                if not mfg or not model:
                    raise ValueError(
                        f"[Line {row_idx}] 제조사(manufacturer) 또는 모델명(model_name) 누락: 데이터를 임의 생성할 수 없습니다."
                    )

                price_raw = row.get("price_krw", "").strip()
                mileage_raw = row.get("mileage_km", "").strip()
                year_raw = row.get("model_year", "").strip()
                if not price_raw or not mileage_raw or not year_raw:
                    raise ValueError(
                        f"[Line {row_idx}] 필수 숫자 제원(가격/주행거리/연식) 누락: 검증 오류."
                    )

                price_krw = int(price_raw)
                mileage_km = int(mileage_raw)
                model_year = int(year_raw)

                # 2. 플랫폼 및 매물 ID 식별
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
                    raise ValueError(
                        f"[Line {row_idx}] 매물 고유 ID(source_listing_id) 누락: 식별 불가 매물입니다."
                    )

                # 3. 관측 시각 파싱
                observed_str = row.get("observed_at", "").strip()
                if not observed_str:
                    raise ValueError(
                        f"[Line {row_idx}] 관측 시각(observed_at) 누락: 시계열 무결성을 위해 관측 시각은 필수입니다."
                    )
                try:
                    observed_at = datetime.fromisoformat(observed_str)
                except ValueError as err:
                    raise ValueError(
                        f"[Line {row_idx}] 관측 시각 형식 오류 ({observed_str}): {err}"
                    ) from err

                # 4. 사고 및 성능점검 상태 (누락 시 정상으로 위조 금지 -> UNKNOWN / False)
                raw_accident = row.get("accident_state", "").strip()
                accident_state = raw_accident if raw_accident else "UNKNOWN"

                raw_inspection = row.get("has_inspection_record", "").strip().upper()
                has_inspection = raw_inspection in ("Y", "TRUE", "1", "YES")

                # 데이터 출처 메타데이터
                data_origin = (
                    row.get("data_origin", "").strip() or "MANUALLY_OBSERVED"
                )

                record = StandardListingRecord(
                    source_platform=platform,
                    source_listing_id=source_id,
                    source_url=url,
                    seller_reference=row.get("seller_reference", "").strip() or None,
                    manufacturer=mfg,
                    model_name=model,
                    model_generation=row.get("model_generation", "").strip() or None,
                    trim_name=row.get("trim_name", "").strip() or None,
                    model_year=model_year,
                    mileage_km=mileage_km,
                    fuel_type=row.get("fuel_type", "가솔린").strip() or "UNKNOWN",
                    transmission=row.get("transmission", "자동").strip() or "UNKNOWN",
                    price_krw=price_krw,
                    raw_location=row.get("raw_location", "").strip() or "UNKNOWN",
                    accident_state=accident_state,
                    has_inspection_record=has_inspection,
                    observed_at=observed_at,
                    listing_status=row.get("listing_status", "ACTIVE").strip()
                    or "ACTIVE",
                    data_origin=data_origin,
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
            # 주소 기반 매매단지 정밀 판정 (하드코딩된 기본값 배제)
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
                    price_krw=rec.price_krw,
                    mileage_km=rec.mileage_km,
                    listing_status=rec.listing_status,
                    normalized_region_id=resolved_region_id,
                    raw_specs={"model": rec.model_name, "trim": rec.trim_name},
                )
                session.add(snapshot)
                stats["new_listings"] += 1
                stats["new_snapshots"] += 1

            else:
                stats["existing_listings"] += 1
                # 최신 스냅샷 확인
                latest_snapshot = session.execute(
                    select(ListingSnapshot)
                    .where(ListingSnapshot.listing_id == existing_listing.listing_id)
                    .order_by(ListingSnapshot.observed_at.desc())
                ).scalars().first()

                if latest_snapshot:
                    rec_obs_utc = _to_utc(rec.observed_at)
                    latest_obs_utc = _to_utc(latest_snapshot.observed_at)

                    # 1. 늦게 도착한 과거 관측 자료인지 확인 (과거 자료는 상태 덮어쓰기 금지)
                    is_newer = rec_obs_utc >= latest_obs_utc

                    # 2. 동일 시각, 동일 가격, 동일 상태 중복 입력 차단
                    is_duplicate_snapshot = (
                        rec_obs_utc == latest_obs_utc
                        and rec.price_krw == latest_snapshot.price_krw
                        and rec.mileage_km == latest_snapshot.mileage_km
                        and rec.listing_status == latest_snapshot.listing_status
                    )

                    if is_newer and not is_duplicate_snapshot:
                        if rec.price_krw < latest_snapshot.price_krw:
                            has_price_drop = True
                            existing_listing.current_status = "PRICE_CHANGED"
                            stats["price_changed_count"] += 1

                        if (
                            rec.price_krw != latest_snapshot.price_krw
                            or rec.mileage_km != latest_snapshot.mileage_km
                            or rec.listing_status != latest_snapshot.listing_status
                        ):
                            new_snapshot = ListingSnapshot(
                                listing_id=existing_listing.listing_id,
                                observed_at=rec.observed_at,
                                price_krw=rec.price_krw,
                                mileage_km=rec.mileage_km,
                                listing_status=rec.listing_status,
                                normalized_region_id=resolved_region_id
                                or existing_listing.normalized_region_id,
                                raw_specs={
                                    "model": rec.model_name,
                                    "trim": rec.trim_name,
                                },
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

            # OpportunityScorer 내부에서 Leave-One-Out 자동 적용
            res = OpportunityScorer.evaluate_listing(
                target=rec, cohort_records=cohort, recent_price_drop=has_drop
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
    ) -> list[OpportunityScoreResult]:
        """유효하게 평가된 상위 N개 기회 매물만 선별하여 CSV 파일로 저장."""
        # 표본 부족(INSUFFICIENT_DATA) 차량은 상위 추천 목록에서 제외!
        evaluated_candidates = [
            r for r in results if r.evaluation_status == "EVALUATED"
        ]
        top_candidates = evaluated_candidates[:top_n]

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "rank",
            "opportunity_score",
            "evaluation_status",
            "data_confidence",
            "data_origin",
            "vehicle_summary",
            "price_krw",
            "adjusted_fair_value_krw",
            "adjusted_advantage_pct",
            "benchmark_median_price_krw",
            "normalized_baseline_median_krw",
            "sample_count",
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
                        "evaluation_status": item.evaluation_status,
                        "data_confidence": item.data_confidence,
                        "data_origin": item.data_origin,
                        "vehicle_summary": item.vehicle_summary,
                        "price_krw": f"{item.price_krw:,}원",
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
                        "source_platform": item.source_platform,
                        "source_listing_id": item.source_listing_id,
                        "source_url": item.source_url or "",
                        "selection_reason": item.selection_reason,
                    }
                )

        return top_candidates
