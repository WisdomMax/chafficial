"""차량 상태, 성능점검, 사고·보험 이력 모델."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class VehicleCondition(Base):
    """차량 상태 및 성능점검기록부 정보.
    
    외판 교환과 주요 골격 손상을 엄격히 분리하며, 확인되지 않은 상태는 정상으로 단정하지 않습니다.
    """
    __tablename__ = "vehicle_conditions"

    condition_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    listing_id: Mapped[str | None] = mapped_column(
        ForeignKey("listings.listing_id", ondelete="CASCADE"), nullable=True, index=True
    )
    vehicle_id: Mapped[str | None] = mapped_column(
        ForeignKey("vehicle_identities.vehicle_id", ondelete="CASCADE"), nullable=True, index=True
    )
    inspection_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNCONFIRMED"
    )  # CONFIRMED, UNCONFIRMED
    accident_classification: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNCONFIRMED"
    )  # NO_ACCIDENT, SIMPLE_REPAIR, MAJOR_ACCIDENT, UNCONFIRMED

    # 외판 교환 vs 주요 골격 손상 분리
    outer_panel_repairs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # 휀더, 도어, 후드 등
    structural_damages: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)   # 프레임, 필러, 휠하우스 등

    # 보험 사고 이력
    insurance_record_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    my_damage_amount_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    other_damage_amount_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_total_loss: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 전손
    is_flood: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)       # 침수
    is_theft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)       # 도난

    # 사용 이력
    owner_change_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_change: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # 렌트/영업용

    # 주요 기계 상태 (확인 안된 경우 UNCONFIRMED)
    engine_condition: Mapped[str] = mapped_column(String(30), default="UNCONFIRMED", nullable=False)
    transmission_condition: Mapped[str] = mapped_column(String(30), default="UNCONFIRMED", nullable=False)
    oil_leak_status: Mapped[str] = mapped_column(String(30), default="UNCONFIRMED", nullable=False)

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    source_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "inspection_status IN ('CONFIRMED', 'UNCONFIRMED')",
            name="chk_condition_inspection_status",
        ),
        CheckConstraint(
            "accident_classification IN ('NO_ACCIDENT', 'SIMPLE_REPAIR', 'MAJOR_ACCIDENT', 'UNCONFIRMED')",
            name="chk_condition_accident_class",
        ),
        CheckConstraint("my_damage_amount_krw >= 0", name="chk_my_damage_non_negative"),
        CheckConstraint("other_damage_amount_krw >= 0", name="chk_other_damage_non_negative"),
        CheckConstraint("owner_change_count IS NULL OR owner_change_count >= 0", name="chk_owner_change_non_negative"),
    )

    listing = relationship("Listing", lazy="select")
    vehicle = relationship("VehicleIdentity", lazy="select")
