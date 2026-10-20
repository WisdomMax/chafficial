"""과거 시점 재현 및 미래 정보 누출(Data Leakage) 방지 쿼리 엔진."""

from datetime import datetime
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from chaficial.models.condition import VehicleCondition
from chaficial.models.listing import Listing
from chaficial.models.snapshot import ListingSnapshot


class TimeTravelQueryEngine:
    """의사결정 시점(Decision Time) 기준 과거에 실제로 관측·적재된 정보만 재현하는 엔진."""

    @staticmethod
    def get_listing_snapshot_at(
        session: Session, listing_id: str, as_of_time: datetime
    ) -> ListingSnapshot | None:
        """지정된 과거 시점(as_of_time) 이전에 실제 관측되고 DB에 적재된 최신 매물 스냅샷을 반환합니다.
        
        미래 시점에 발생한 가격 인하나 상태 변경은 일절 반환되지 않습니다.
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
    def get_catalog_market_stats_at(
        session: Session, catalog_id: int, as_of_time: datetime
    ) -> dict[str, Any]:
        """특정 시점 기준 해당 차종 카탈로그의 시장 통계(매물 수, 최저/최고/평균 등록가격)를 산출합니다.
        
        당시 시점까지 살아있던 활성 매물의 최신 스냅샷만 집계합니다.
        """
        # 해당 카탈로그에 속한 매물 목록 조회
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
