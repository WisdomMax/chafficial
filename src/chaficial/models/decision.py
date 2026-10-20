"""광고 및 홍보 의사결정 이력 모델 (강화학습 핵심 로깅)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class PromotionDecision(Base):
    """홍보 의사결정 로그.
    
    향후 강화학습(Contextual Bandit / Offline RL)을 위해 의사결정 시점의
    선택 가능한 행동(eligible_actions), 실제 선택한 행동(chosen_action),
    행동 선택 확률(action_probability)을 엄격히 기록합니다.
    """
    __tablename__ = "promotion_decisions"

    decision_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("sales_candidates.candidate_id", ondelete="CASCADE"), nullable=False, index=True
    )
    partner_id: Mapped[str | None] = mapped_column(
        ForeignKey("sales_partners.partner_id", ondelete="SET NULL"), nullable=True, index=True
    )
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False, index=True
    )
    decision_source: Mapped[str] = mapped_column(
        String(30), nullable=False, default="AI_AGENT"
    )  # AI_AGENT, PARTNER_MANUAL, HEURISTIC_RULE
    eligible_actions: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    chosen_action: Mapped[str] = mapped_column(String(50), nullable=False)
    action_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    planned_budget_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING, EXECUTED, CANCELLED

    __table_args__ = (
        CheckConstraint(
            "decision_source IN ('AI_AGENT', 'PARTNER_MANUAL', 'HEURISTIC_RULE')",
            name="chk_decision_source",
        ),
        CheckConstraint(
            "execution_status IN ('PENDING', 'EXECUTED', 'CANCELLED')",
            name="chk_decision_exec_status",
        ),
        CheckConstraint("planned_budget_krw >= 0", name="chk_decision_budget_non_negative"),
        CheckConstraint(
            "action_probability IS NULL OR (action_probability >= 0.0 AND action_probability <= 1.0)",
            name="chk_decision_prob_range",
        ),
    )

    candidate = relationship("SalesCandidate", lazy="joined")
    partner = relationship("SalesPartner", lazy="joined")
