"""판매 후보 매물 모델."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class SalesCandidate(Base):
    """AI 알고리즘 또는 전문가가 선정한 실제 판매 후보 차량.
    
    저렴하다는 이유만으로 자동 추천되지 않으며, 파트너의 실제 재고·판매 가능 여부 검토를 거칩니다.
    - selected_at: 의사결정상 선정 시각
    - created_at: 시스템 데이터베이스에 적재된 시각
    """
    __tablename__ = "sales_candidates"

    candidate_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    listing_id: Mapped[str] = mapped_column(
        ForeignKey("listings.listing_id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_region_id: Mapped[str] = mapped_column(
        ForeignKey("regions.region_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    selected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    selected_by: Mapped[str] = mapped_column(
        String(30), nullable=False, default="AI_AGENT"
    )  # AI_AGENT, PARTNER_MANUAL, RULE_BASED
    selection_reason: Mapped[str] = mapped_column(String(200), nullable=False)
    selection_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    availability_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNCONFIRMED"
    )  # AVAILABLE, RESERVED, SOLD_OUT, UNCONFIRMED
    partner_review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )  # APPROVED, REJECTED, PENDING
    review_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "selected_by IN ('AI_AGENT', 'PARTNER_MANUAL', 'RULE_BASED')",
            name="chk_candidate_selected_by",
        ),
        CheckConstraint(
            "availability_status IN ('AVAILABLE', 'RESERVED', 'SOLD_OUT', 'UNCONFIRMED')",
            name="chk_candidate_availability",
        ),
        CheckConstraint(
            "partner_review_status IN ('APPROVED', 'REJECTED', 'PENDING')",
            name="chk_candidate_partner_review",
        ),
    )

    listing = relationship("Listing", lazy="joined")
    target_region = relationship("Region", lazy="joined")
