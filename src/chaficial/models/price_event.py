"""가격 변동 이벤트 및 시계열 이력 추적 모델 (DIRECTIVE 009).

매물의 가격 인하, 인상, 신규 등록, 비노출/삭제 상태 전이를 구조화하여 영구 보존합니다.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chaficial.database.base import Base


class PriceEvent(Base):
    """개별 매물의 시계열 가격 변동 이벤트 기록."""

    __tablename__ = "price_events"

    event_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    listing_id: Mapped[str] = mapped_column(
        ForeignKey("listings.listing_id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_listing_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # 이벤트 유형: NEW_LISTING, PRICE_DROP, PRICE_INCREASE, DELISTED, RE_LISTED_SUSPECT
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # 가격 변동 수치
    previous_price_krw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_price_krw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_delta_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    price_delta_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # 최초 관측 대비 누적 변동
    initial_price_krw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cumulative_delta_krw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cumulative_delta_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # 관측 시점 주행거리 및 경과일수
    mileage_at_event: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    days_since_first_observed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 금융상품 구분 및 비정상 격리 플래그
    product_type: Mapped[str] = mapped_column(
        String(30), default="CASH_OR_INSTALLMENT", nullable=False
    )
    is_anomaly: Mapped[bool] = mapped_column(default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('NEW_LISTING', 'PRICE_DROP', 'PRICE_INCREASE', 'DELISTED', 'RE_LISTED_SUSPECT')",
            name="chk_price_event_type",
        ),
    )

    listing = relationship("Listing", lazy="joined")
