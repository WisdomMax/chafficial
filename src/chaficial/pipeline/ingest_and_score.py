"""전국 중고차 매물 데이터 인입, 시계열 무결성 적재 및 기회 매물 자동 선별 파이프라인."""

import csv
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from chaficial.models.listing import Listing
from chaficial.models.region import Region
from chaficial.models.snapshot import ListingSnapshot
from chaficial.platforms.base import PlatformUrlParser, StandardListingRecord
from chaficial.scorer.opportunity import OpportunityScorer, OpportunityScoreResult


class OpportunityPipeline:
    """전국 매물 데이터 인입, 스냅샷 보존 및 기회 스코어링 총괄 파이프라인."""

    @staticmethod
    def load_records_from_csv(csv_path: str | Path) -> list[StandardListingRecord]:
        """CSV 파일에서 표준 매물 레코드 목록 로드 및 파싱."""
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"매물 CSV 파일을 찾을 수 없습니다: {csv_path}")

        records: list[StandardListingRecord] = []
        with open(path, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 필수 필드 기본값 및 안전 파싱
                url = row.get("source_url", "").strip() or None
                platform = row.get("source_platform", "").strip()
                source_id = row.get("source_listing_id", "").strip()

                if not platform and url:
                    platform, extracted_id = PlatformUrlParser.extract_source_id(url)
                    if not source_id and extracted_id:
                        source_id = extracted_id

                if not platform:
                    platform = "OTHER"
                if not source_id:
                    source_id = f"ROW_{len(records) + 1}"

                observed_str = row.get("observed_at", "").strip()
                if observed_str:
                    try:
                        observed_at = datetime.fromisoformat(observed_str)
                    except ValueError:
                        observed_at = datetime.now(UTC)
                else:
                    observed_at = datetime.now(UTC)

                has_inspection = row.get("has_inspection_record", "Y").strip().upper() in (
                    "Y",
                    "TRUE",
                    "1",
                    "YES",
                )

                record = StandardListingRecord(
                    source_platform=platform,
                    source_listing_id=source_id,
                    source_url=url,
                    seller_reference=row.get("seller_reference", "").strip() or None,
                    manufacturer=row.get("manufacturer", "현대").strip(),
                    model_name=row.get("model_name", "아반떼").strip(),
                    model_generation=row.get("model_generation", "").strip() or None,
                    trim_name=row.get("trim_name", "").strip() or None,
                    model_year=int(row.get("model_year", 2021)),
                    mileage_km=int(row.get("mileage_km", 50000)),
                    fuel_type=row.get("fuel_type", "가솔린").strip(),
                    transmission=row.get("transmission", "자동").strip(),
                    price_krw=int(row.get("price_krw", 15000000)),
                    raw_location=row.get("raw_location", "서울 동대문구 장안동").strip(),
                    accident_state=row.get("accident_state", "NO_ACCIDENT").strip(),
                    has_inspection_record=has_inspection,
                    observed_at=observed_at,
                    listing_status=row.get("listing_status", "ACTIVE").strip() or "ACTIVE",
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
            "price_drop_flags": {},  # (platform, source_id) -> bool
        }

        # 기본 지역 확보 (미등록 시 기본 서울 지역 연결)
        default_region = session.execute(
            select(Region).where(Region.region_id == "REGION_JANGANPYEONG")
        ).scalar_one_or_none()
        default_region_id = default_region.region_id if default_region else None

        for rec in records:
            # 1. 기존 매물 확인
            existing_listing = session.execute(
                select(Listing).where(
                    Listing.source_platform == rec.source_platform,
                    Listing.source_listing_id == rec.source_listing_id,
                )
            ).scalar_one_or_none()

            has_price_drop = False
            rec_key = f"{rec.source_platform}:{rec.source_listing_id}"

            if existing_listing is None:
                # 신규 매물 등록
                new_listing = Listing(
                    source_platform=rec.source_platform,
                    source_listing_id=rec.source_listing_id,
                    seller_reference=rec.seller_reference,
                    first_observed_at=rec.observed_at,
                    raw_location=rec.raw_location,
                    normalized_region_id=default_region_id,
                    current_status=rec.listing_status,
                )
                session.add(new_listing)
                session.flush()

                # 최초 스냅샷 생성 (Append-only)
                snapshot = ListingSnapshot(
                    listing_id=new_listing.listing_id,
                    observed_at=rec.observed_at,
                    price_krw=rec.price_krw,
                    mileage_km=rec.mileage_km,
                    listing_status=rec.listing_status,
                    normalized_region_id=default_region_id,
                    raw_specs={"model": rec.model_name, "trim": rec.trim_name},
                )
                session.add(snapshot)
                stats["new_listings"] += 1
                stats["new_snapshots"] += 1

            else:
                stats["existing_listings"] += 1
                # 기존 최신 스냅샷 확인
                latest_snapshot = session.execute(
                    select(ListingSnapshot)
                    .where(ListingSnapshot.listing_id == existing_listing.listing_id)
                    .order_by(ListingSnapshot.observed_at.desc())
                ).scalars().first()

                if latest_snapshot:
                    if rec.price_krw < latest_snapshot.price_krw:
                        has_price_drop = True
                        existing_listing.current_status = "PRICE_CHANGED"

                    # 가격이나 주행거리, 상태에 변동이 있을 때만 신규 스냅샷 추가
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
                            normalized_region_id=existing_listing.normalized_region_id,
                            raw_specs={"model": rec.model_name, "trim": rec.trim_name},
                        )
                        session.add(new_snapshot)
                        stats["new_snapshots"] += 1
                        if has_price_drop:
                            stats["price_changed_count"] += 1

            stats["price_drop_flags"][rec_key] = has_price_drop

        session.commit()
        return stats

    @staticmethod
    def evaluate_all(
        records: list[StandardListingRecord],
        price_drop_flags: dict[str, bool] | None = None,
    ) -> list[OpportunityScoreResult]:
        """전체 매물 레코드에 대해 동일군 코호트를 형성하고 일괄 기회 평가 수행."""
        drop_flags = price_drop_flags or {}
        # 1. 코호트별 매물 분류
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
                target=rec, cohort_records=cohort, recent_price_drop=has_drop
            )
            results.append(res)

        # 기회 점수 내림차순 정렬 (점수가 None인 경우 맨 뒤로)
        results.sort(
            key=lambda x: (x.opportunity_score is not None, x.opportunity_score or -1.0),
            reverse=True,
        )
        return results

    @staticmethod
    def export_top_opportunities_to_csv(
        results: list[OpportunityScoreResult],
        output_path: str | Path,
        top_n: int = 10,
    ) -> list[OpportunityScoreResult]:
        """상위 N개 기회 매물을 CSV 파일로 저장."""
        top_candidates = results[:top_n]
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "rank",
            "opportunity_score",
            "evaluation_status",
            "data_confidence",
            "vehicle_summary",
            "price_krw",
            "adjusted_fair_value_krw",
            "adjusted_advantage_pct",
            "benchmark_median_price_krw",
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
                        "vehicle_summary": item.vehicle_summary,
                        "price_krw": f"{item.price_krw:,}원",
                        "adjusted_fair_value_krw": f"{item.adjusted_fair_value_krw:,}원"
                        if item.adjusted_fair_value_krw
                        else "N/A",
                        "adjusted_advantage_pct": f"{item.adjusted_advantage_pct}%"
                        if item.adjusted_advantage_pct is not None
                        else "N/A",
                        "benchmark_median_price_krw": f"{item.benchmark_median_price_krw:,}원"
                        if item.benchmark_median_price_krw
                        else "N/A",
                        "sample_count": item.sample_count,
                        "source_platform": item.source_platform,
                        "source_listing_id": item.source_listing_id,
                        "source_url": item.source_url or "",
                        "selection_reason": item.selection_reason,
                    }
                )

        return top_candidates
