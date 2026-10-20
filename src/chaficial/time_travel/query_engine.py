"""과거 시점 재현 및 미래 정보 누출(Data Leakage) 방지 쿼리 엔진."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from chaficial.models.candidate import SalesCandidate
from chaficial.models.condition import VehicleCondition
from chaficial.models.listing import Listing
from chaficial.models.snapshot import ListingSnapshot


class TimeTravelQueryEngine:
    """의사결정 시점(as_of_time) 기준 과거에 실제로 관측·적재된 정보만 재현하는 엔진."""

    @staticmethod
    def get_listing_snapshot_at(
        session: Session, listing_id: str, as_of_time: datetime
    ) -> ListingSnapshot | None:
        """지정된 과거 시점(as_of_time) 이전에 실제 관측되고 DB에 적재된 최신 매물 스냅샷을 반환합니다.
        
        - observed_at <= as_of_time: 미래에 일어난 가격 변동 제외
        - ingested_at <= as_of_time: 미래 시점에 뒤늦게 입력된 과거 관측치 제외
        """
        stmt = (
            select(ListingSnapshot)
            .where(
                and_(
                    ListingSnapshot.listing_id == listing_id,
                    ListingSnapshot.observed_at <= as_of_time,
                    ListingSnapshot.ingested_at <= as_of_time,
                )
            )
            .order_by(ListingSnapshot.observed_at.desc(), ListingSnapshot.ingested_at.desc())
            .limit(1)
        )
        return session.scalar(stmt)

    @staticmethod
    def get_eligible_listings_as_of(
        session: Session, target_region_id: str, as_of_time: datetime
    ) -> list[dict[str, Any]]:
        """특정 과거 시점(as_of_time) 당시 시장에서 추천 대상이 될 수 있었던 매물 풀(Listing)을 반환합니다.
        
        - [지역 누출 차단]: 현재 Listing.normalized_region_id가 아닌 당시 스냅샷에 기록된 normalized_region_id를 검사합니다.
        - [상태 누출 차단]: 당시 스냅샷 상태가 ACTIVE 또는 PRICE_CHANGED인 경우만 포함합니다.
        """
        stmt = (
            select(Listing)
            .where(Listing.first_observed_at <= as_of_time)
        )
        eligible_pool: list[dict[str, Any]] = []
        for listing in session.scalars(stmt).all():
            snap = TimeTravelQueryEngine.get_listing_snapshot_at(session, listing.listing_id, as_of_time)
            # 당시 스냅샷이 활성 상태이고, 당시 스냅샷의 normalized_region_id가 target_region_id와 일치하는 경우만 포함
            if (
                snap
                and snap.listing_status in ("ACTIVE", "PRICE_CHANGED")
                and snap.normalized_region_id == target_region_id
            ):
                eligible_pool.append({
                    "listing_id": listing.listing_id,
                    "source_platform": listing.source_platform,
                    "source_listing_id": listing.source_listing_id,
                    "target_region_id": target_region_id,
                    "price_krw": snap.price_krw,
                    "mileage_km": snap.mileage_km,
                    "listing_status": snap.listing_status,
                    "observed_at": snap.observed_at,
                    "ingested_at": snap.ingested_at,
                })
        return eligible_pool

    @staticmethod
    def get_sales_candidates_as_of(
        session: Session, target_region_id: str, as_of_time: datetime
    ) -> list[dict[str, Any]]:
        """기존 호환용 별칭: get_eligible_listings_as_of를 호출합니다."""
        return TimeTravelQueryEngine.get_eligible_listings_as_of(
            session=session, target_region_id=target_region_id, as_of_time=as_of_time
        )

    @staticmethod
    def get_selected_candidates_as_of(
        session: Session, target_region_id: str, as_of_time: datetime
    ) -> list[dict[str, Any]]:
        """특정 과거 시점(as_of_time) 이전에 실제로 선정되어 SalesCandidate에 기록된 후보 목록을 반환합니다.
        
        - selected_at <= as_of_time
        - created_at <= as_of_time
        """
        stmt = (
            select(SalesCandidate)
            .where(
                and_(
                    SalesCandidate.target_region_id == target_region_id,
                    SalesCandidate.selected_at <= as_of_time,
                    SalesCandidate.created_at <= as_of_time,
                )
            )
            .order_by(SalesCandidate.selected_at.asc())
        )
        selected_candidates: list[dict[str, Any]] = []
        for cand in session.scalars(stmt).all():
            snap = TimeTravelQueryEngine.get_listing_snapshot_at(session, cand.listing_id, as_of_time)
            selected_candidates.append({
                "candidate_id": cand.candidate_id,
                "listing_id": cand.listing_id,
                "target_region_id": cand.target_region_id,
                "selected_at": cand.selected_at,
                "created_at": cand.created_at,
                "selected_by": cand.selected_by,
                "selection_reason": cand.selection_reason,
                "selection_score": cand.selection_score,
                "availability_status": cand.availability_status,
                "partner_review_status": cand.partner_review_status,
                "current_price_krw": snap.price_krw if snap else None,
            })
        return selected_candidates

    @staticmethod
    def get_current_sales_candidates(
        session: Session, target_region_id: str
    ) -> list[dict[str, Any]]:
        """현재 시점 기준 추천 가능 매물 풀을 반환합니다."""
        return TimeTravelQueryEngine.get_eligible_listings_as_of(
            session=session,
            target_region_id=target_region_id,
            as_of_time=datetime.now(UTC),
        )

    @staticmethod
    def get_vehicle_condition_at(
        session: Session, listing_id: str, as_of_time: datetime
    ) -> VehicleCondition | None:
        """지정된 과거 시점 이전에 확인된 차량 상태 및 성능점검 정보를 반환합니다."""
        stmt = (
            select(VehicleCondition)
            .where(
                and_(
                    VehicleCondition.listing_id == listing_id,
                    VehicleCondition.observed_at <= as_of_time,
                    VehicleCondition.ingested_at <= as_of_time,
                )
            )
            .order_by(VehicleCondition.observed_at.desc(), VehicleCondition.ingested_at.desc())
            .limit(1)
        )
        return session.scalar(stmt)

    @staticmethod
    def get_market_stats_as_of(
        session: Session, catalog_id: int, as_of_time: datetime
    ) -> dict[str, Any]:
        """특정 시점 기준 해당 차종 카탈로그의 시장 통계를 산출합니다."""
        return TimeTravelQueryEngine.get_catalog_market_stats_at(session, catalog_id, as_of_time)

    @staticmethod
    def get_catalog_market_stats_at(
        session: Session, catalog_id: int, as_of_time: datetime
    ) -> dict[str, Any]:
        """기존 인터페이스 호환용 카탈로그 시장 통계 산출 함수."""
        listings = session.scalars(
            select(Listing)
            .join(Listing.vehicle)
            .where(Listing.vehicle.has(catalog_id=catalog_id))
            .where(Listing.first_observed_at <= as_of_time)
        ).all()

        active_prices: list[int] = []
        for l in listings:
            snap = TimeTravelQueryEngine.get_listing_snapshot_at(session, l.listing_id, as_of_time)
            if snap and snap.listing_status in ("ACTIVE", "PRICE_CHANGED"):
                active_prices.append(snap.price_krw)

        if not active_prices:
            return {
                "active_listing_count": 0,
                "min_price_krw": None,
                "max_price_krw": None,
                "avg_price_krw": None,
            }

        return {
            "active_listing_count": len(active_prices),
            "min_price_krw": min(active_prices),
            "max_price_krw": max(active_prices),
            "avg_price_krw": sum(active_prices) // len(active_prices),
        }
