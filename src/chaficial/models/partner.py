"""영업 파트너(딜러) 모델."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class SalesPartner(Base):
    """실제 판매 및 고객 상담을 담당하는 전문 딜러 파트너.
    
    장안평 25년 경력 등 실무 전문가를 주요 실사용자로 하여 설계되었습니다.
    """
    __tablename__ = "sales_partners"

    partner_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    partner_name: Mapped[str] = mapped_column(String(100), nullable=False)
    operating_region_id: Mapped[str] = mapped_column(
        ForeignKey("regions.region_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    partner_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ACTIVE"
    )  # ACTIVE, INACTIVE
    experience_years: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    contact_masked: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "partner_status IN ('ACTIVE', 'INACTIVE')",
            name="chk_partner_status",
        ),
        CheckConstraint("experience_years >= 0", name="chk_partner_exp_non_negative"),
    )

    operating_region = relationship("Region", lazy="joined")
