"""차량별 옵션 장착 및 확인 상태 모델."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class VehicleOption(Base):
    """차량 개별 옵션 모델.
    
    미확인 옵션을 미장착으로 단정하지 않으며, PRESENT, ABSENT, UNKNOWN 3가지 상태로 명시 관리합니다.
    """
    __tablename__ = "vehicle_options"

    option_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    listing_id: Mapped[str | None] = mapped_column(
        ForeignKey("listings.listing_id", ondelete="CASCADE"), nullable=True, index=True
    )
    vehicle_id: Mapped[str | None] = mapped_column(
        ForeignKey("vehicle_identities.vehicle_id", ondelete="CASCADE"), nullable=True, index=True
    )
    option_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    option_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNKNOWN"
    )  # PRESENT, ABSENT, UNKNOWN
    verification_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "option_status IN ('PRESENT', 'ABSENT', 'UNKNOWN')",
            name="chk_option_status",
        ),
    )

    listing = relationship("Listing", lazy="select")
    vehicle = relationship("VehicleIdentity", lazy="select")
