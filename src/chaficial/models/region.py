"""지역 분류 및 분석·판매 지역 설정 모델."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class Region(Base):
    """행정구역 및 중고차 전문 매매단지(시장권역) 분류 모델.
    
    예: 서울 장안평 중고차 시장, 경기 수원 도이치오토월드/SK V1, 인천 엠파크 등
    """
    __tablename__ = "regions"

    region_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    region_name: Mapped[str] = mapped_column(String(100), nullable=False)
    region_type: Mapped[str] = mapped_column(String(30), nullable=False)  # COUNTRY, METROPOLIS, DISTRICT, MARKET_COMPLEX
    parent_region_id: Mapped[str | None] = mapped_column(
        ForeignKey("regions.region_id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "region_type IN ('COUNTRY', 'METROPOLIS', 'DISTRICT', 'MARKET_COMPLEX')",
            name="chk_region_type",
        ),
    )

    parent = relationship("Region", remote_side=[region_id], lazy="select")


class RegionConfiguration(Base):
    """시장 분석 범위, 실제 판매 대상 매물 지역, 고객 타겟 지역의 독립 설정 모델.
    
    - analysis_region_scope: 전국(NATIONWIDE) 등
    - sales_region_ids: 장안평(REGION_JANGANPYEONG) 등 실제 파트너 판매 가능 지역 목록
    - customer_target_regions: 광고 노출 및 고객 유치 대상 지역 목록
    """
    __tablename__ = "region_configurations"

    config_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    analysis_region_scope: Mapped[str] = mapped_column(String(50), nullable=False, default="NATIONWIDE")
    sales_region_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    customer_target_regions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
