"""원천 플랫폼별 매물 정보 모델."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class Listing(Base):
    """원천 플랫폼(엔카, KB차차차, 당근 등)에 게시된 개별 매물.
    
    동일 차량이 여러 플랫폼에 올라오더라도 각 매물은 고유하게 유지되며,
    근거 없이 자동 병합되지 않습니다.
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
    snapshots = relationship(
        "ListingSnapshot",
        back_populates="listing",
        order_by="ListingSnapshot.observed_at",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
