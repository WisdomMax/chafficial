"""물리적 차량 고유 식별 및 정합성 모델."""

import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class VehicleIdentity(Base):
    """실제 물리적 차량의 동일성 식별 모델.
    
    VIN(차대번호)이나 차량번호는 매물 사이트에서 마스킹되거나 누락될 수 있으므로 기본키로 쓰지 않으며,
    확인되지 않은 경우 'UNCONFIRMED' 상태를 보존합니다.
    """
    __tablename__ = "vehicle_identities"

    vehicle_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("vehicle_catalog.catalog_id", ondelete="SET NULL"), nullable=True, index=True
    )
    plate_number: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    vin: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    identity_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNCONFIRMED"
    )  # CONFIRMED, UNCONFIRMED, AMBIGUOUS
    identity_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5
    )

    __table_args__ = (
        CheckConstraint(
            "identity_status IN ('CONFIRMED', 'UNCONFIRMED', 'AMBIGUOUS')",
            name="chk_vehicle_identity_status",
        ),
        CheckConstraint(
            "identity_confidence >= 0.0 AND identity_confidence <= 1.0",
            name="chk_vehicle_identity_confidence",
        ),
    )

    catalog = relationship("VehicleCatalog", lazy="joined")
