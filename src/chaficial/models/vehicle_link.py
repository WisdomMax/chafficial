"""서로 다른 광고 간 동일 실차 추정 링크 모델 (DIRECTIVE 009).

플랫폼별 광고 매물이 동일 실차(PROBABLE_SAME)로 연결되는 근거와 신뢰도 등급을 기록합니다.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from chaficial.database.base import Base


class VehicleIdentityLink(Base):
    """서로 다른 광고 간 동일 실차 추정 관계(Identity Link)."""

    __tablename__ = "vehicle_identity_links"

    link_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_listing_id: Mapped[str] = mapped_column(
        ForeignKey("listings.listing_id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_listing_id: Mapped[str] = mapped_column(
        ForeignKey("listings.listing_id", ondelete="CASCADE"), nullable=False, index=True
    )
    vehicle_fingerprint: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    # 신뢰도 등급: CONFIRMED_SAME, PROBABLE_SAME, UNCERTAIN, DISTINCT
    confidence_grade: Mapped[str] = mapped_column(String(30), nullable=False, default="PROBABLE_SAME")
    link_basis: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "confidence_grade IN ('CONFIRMED_SAME', 'PROBABLE_SAME', 'UNCERTAIN', 'DISTINCT')",
            name="chk_link_confidence_grade",
        ),
    )
