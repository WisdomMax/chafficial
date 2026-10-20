"""원천 플랫폼별 매물 정보 모델.

매물 데이터의 영구 보존 및 물리 삭제 차단(Soft delete / DELISTED 상태 전이 강제).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, event, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class ListingDeletionRestrictedError(Exception):
    """스냅샷 또는 이력이 존재하는 매물의 물리적 삭제 시도 시 발생하는 예외."""


class Listing(Base):
    """원천 플랫폼(엔카, KB차차차, 당근 등)에 게시된 개별 매물.
    
    동일 차량이 여러 플랫폼에 올라오더라도 각 매물은 고유하게 유지되며,
    근거 없이 자동 병합되지 않습니다.
    과거 시장 관측 이력 보존을 위해 스냅샷을 보유한 매물의 일반적 물리 삭제는 차단되며,
    판매 종료 시 DELISTED 상태로 관리됩니다.
    """
    __tablename__ = "listings"

    listing_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_listing_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    vehicle_id: Mapped[str | None] = mapped_column(
        ForeignKey("vehicle_identities.vehicle_id", ondelete="SET NULL"), nullable=True, index=True
    )
    seller_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    first_observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    raw_location: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_region_id: Mapped[str | None] = mapped_column(
        ForeignKey("regions.region_id", ondelete="SET NULL"), nullable=True, index=True
    )
    current_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVE", index=True
    )  # ACTIVE, PRICE_CHANGED, DELISTED, UNKNOWN

    __table_args__ = (
        CheckConstraint(
            "current_status IN ('ACTIVE', 'PRICE_CHANGED', 'DELISTED', 'UNKNOWN')",
            name="chk_listing_status",
        ),
    )

    vehicle = relationship("VehicleIdentity", lazy="joined")
    normalized_region = relationship("Region", lazy="joined")
    # 스냅샷 연쇄 삭제(CASCADE delete-orphan) 원천 배제: 이력 보존
    snapshots = relationship(
        "ListingSnapshot",
        back_populates="listing",
        order_by="ListingSnapshot.observed_at",
        cascade="save-update, merge",
        passive_deletes=True,
    )


@event.listens_for(Listing, "before_delete")
def _prevent_listing_physical_delete(mapper, connection, target):
    """스냅샷이 존재하는 매물의 무단 물리 삭제를 차단하고 이력을 영구 보존합니다."""
    count = connection.execute(
        text("SELECT COUNT(1) FROM listing_snapshots WHERE listing_id = :lid"),
        {"lid": target.listing_id},
    ).scalar() or 0
    if count > 0:
        raise ListingDeletionRestrictedError(
            f"Listing '{target.listing_id}' has {count} historic snapshot(s) and cannot be deleted physically. "
            "Update status to 'DELISTED' to preserve training market intelligence."
        )
