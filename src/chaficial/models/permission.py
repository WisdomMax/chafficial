"""데이터 출처별 이용 및 재배포 권한 모델."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from chaficial.database.base import Base


class DataSourcePermission(Base):
    """데이터 원천별 법적 이용 권한 관리.
    
    공개 웹페이지라고 해서 자동 수집 및 상업적 재사용 권한이 있는 것은 아니므로,
    수집/저장/학습/재배포(광고 영상 제작 등) 권한을 명시적으로 구분 관리합니다.
    """
    __tablename__ = "data_source_permissions"

    source_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    permission_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # AUTHORIZED, RESTRICTED, FORBIDDEN, PENDING
    collection_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    storage_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    model_training_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    republication_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    authorization_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "permission_status IN ('AUTHORIZED', 'RESTRICTED', 'FORBIDDEN', 'PENDING')",
            name="chk_permission_status",
        ),
    )
