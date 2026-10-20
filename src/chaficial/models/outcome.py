"""실제 영업 및 계약 결과 모델."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class SalesOutcome(Base):
    """실제 차량 판매 및 계약 결과.
    
    - 매물 삭제(DELISTED_UNKNOWN)를 판매 완료(SOLD_CONFIRMED)로 단정하지 않습니다.
    - 실제 확인된 계약 거래가격(confirmed_sale_price_krw)은 등록가격과 엄격히 분리됩니다.
    """
    __tablename__ = "sales_outcomes"

    outcome_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("sales_candidates.candidate_id", ondelete="CASCADE"), nullable=False, index=True
    )
    partner_id: Mapped[str | None] = mapped_column(
        ForeignKey("sales_partners.partner_id", ondelete="SET NULL"), nullable=True, index=True
    )
    outcome_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="NOT_YET_SOLD"
    )  # NOT_YET_SOLD, SOLD_CONFIRMED, DELISTED_UNKNOWN, UNKNOWN
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNVERIFIED"
    )  # CONFIRMED_BY_CONTRACT, PARTNER_REPORTED, UNVERIFIED
    contracted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_sale_price_krw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    evidence_reference: Mapped[str | None] = mapped_column(String(200), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "outcome_status IN ('NOT_YET_SOLD', 'SOLD_CONFIRMED', 'DELISTED_UNKNOWN', 'UNKNOWN')",
            name="chk_outcome_status",
        ),
        CheckConstraint(
            "verification_status IN ('CONFIRMED_BY_CONTRACT', 'PARTNER_REPORTED', 'UNVERIFIED')",
            name="chk_outcome_verification",
        ),
        CheckConstraint(
            "confirmed_sale_price_krw IS NULL OR confirmed_sale_price_krw >= 0",
            name="chk_confirmed_sale_price_non_negative",
        ),
    )

    candidate = relationship("SalesCandidate", lazy="joined")
    partner = relationship("SalesPartner", lazy="joined")
    settlement = relationship("Settlement", uselist=False, back_populates="outcome")
