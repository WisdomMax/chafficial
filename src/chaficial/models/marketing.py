"""마케팅 및 SNS 광고 성과 모델."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class MarketingResult(Base):
    """광고 성과 기록 모델.
    
    조회수나 노출수뿐 아니라 실제 유효 문의(verified_leads) 및 집행 비용을 기록합니다.
    """
    __tablename__ = "marketing_results"

    marketing_result_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    decision_id: Mapped[str] = mapped_column(
        ForeignKey("promotion_decisions.decision_id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # YOUTUBE_SHORTS, INSTAGRAM_REELS, TIKTOK, CAROUSEL
    creative_type: Mapped[str] = mapped_column(String(50), nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inquiries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    verified_leads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    production_cost_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    advertising_cost_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        CheckConstraint("impressions >= 0", name="chk_mr_impressions_non_negative"),
        CheckConstraint("views >= 0", name="chk_mr_views_non_negative"),
        CheckConstraint("clicks >= 0", name="chk_mr_clicks_non_negative"),
        CheckConstraint("inquiries >= 0", name="chk_mr_inquiries_non_negative"),
        CheckConstraint("verified_leads >= 0", name="chk_mr_leads_non_negative"),
        CheckConstraint("production_cost_krw >= 0", name="chk_mr_prod_cost_non_negative"),
        CheckConstraint("advertising_cost_krw >= 0", name="chk_mr_ad_cost_non_negative"),
    )

    decision = relationship("PromotionDecision", lazy="joined")
