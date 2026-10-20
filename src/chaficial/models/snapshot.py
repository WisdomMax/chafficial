"""매물 상태 및 가격의 시계열 스냅샷 모델."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class ListingSnapshot(Base):
    """매물 관측 시점별 불변(Immutable) 스냅샷.
    
    가격 변경이나 상태 변경 시 이전 기록을 절대 덮어쓰지 않고 새로 추가합니다.
    - observed_at: 실제 시장에서 관측된 시점
    - ingested_at: 차피셜 시스템 데이터베이스에 적재된 시점
    과거 특정 시점 조회 시 observed_at <= T and ingested_at <= T 조건으로 미래 정보 누출을 방지합니다.
    """
    __tablename__ = "listing_snapshots"

    snapshot_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    listing_id: Mapped[str] = mapped_column(
        ForeignKey("listings.listing_id", ondelete="CASCADE"), nullable=False, index=True
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    price_krw: Mapped[int] = mapped_column(Integer, nullable=False)
    mileage_km: Mapped[int] = mapped_column(Integer, nullable=False)
    listing_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVE"
    )  # ACTIVE, PRICE_CHANGED, DELISTED, UNKNOWN
    raw_specs: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint("price_krw >= 0", name="chk_snapshot_price_non_negative"),
        CheckConstraint("mileage_km >= 0", name="chk_snapshot_mileage_non_negative"),
        CheckConstraint(
            "listing_status IN ('ACTIVE', 'PRICE_CHANGED', 'DELISTED', 'UNKNOWN')",
            name="chk_snapshot_status",
        ),
    )

    listing = relationship("Listing", back_populates="snapshots")
