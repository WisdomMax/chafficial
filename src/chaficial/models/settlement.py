"""실제 영업 정산 및 순수익 모델."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class Settlement(Base):
    """실제 사업 수익 및 정산 내역.
    
    - outcome_id는 Unique 제약으로 동일 판매 건의 중복 정산을 방지합니다.
    - settlement_status가 'SETTLED'로 확정되기 전에는 미확정 상태로 유지되며 확정 수익으로 간주하지 않습니다.
    """
    __tablename__ = "settlements"

    settlement_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    outcome_id: Mapped[str] = mapped_column(
        ForeignKey("sales_outcomes.outcome_id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    revenue_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="COMMISSION"
    )  # COMMISSION, AD_FEE, TRADING_MARGIN, OTHER
    confirmed_revenue_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    advertising_cost_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    production_cost_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    other_costs_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    net_profit_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    settlement_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING, SETTLED, DISPUTED, CANCELLED
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "settlement_status IN ('PENDING', 'SETTLED', 'DISPUTED', 'CANCELLED')",
            name="chk_settlement_status",
        ),
        CheckConstraint(
            "revenue_type IN ('COMMISSION', 'AD_FEE', 'TRADING_MARGIN', 'OTHER')",
            name="chk_revenue_type",
        ),
        CheckConstraint("confirmed_revenue_krw >= 0", name="chk_confirmed_rev_non_negative"),
        CheckConstraint("advertising_cost_krw >= 0", name="chk_settle_ad_cost_non_negative"),
        CheckConstraint("production_cost_krw >= 0", name="chk_settle_prod_cost_non_negative"),
        CheckConstraint("other_costs_krw >= 0", name="chk_settle_other_cost_non_negative"),
    )

    outcome = relationship("SalesOutcome", back_populates="settlement")

    def calculate_net_profit(self) -> int:
        """비용을 차감한 실제 순수익 계산."""
        return (
            self.confirmed_revenue_krw
            - self.advertising_cost_krw
            - self.production_cost_krw
            - self.other_costs_krw
        )
