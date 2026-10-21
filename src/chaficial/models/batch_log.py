"""배치 수집 및 미노출 판정 감사 로그 모델.

각 검색 수집 배치의 고유 batch_id를 영속 보존하여,
동일 배치의 중복 호출이나 재시도 시 매물 누락 카운터가 중복 증가하는 결함을 원천 차단합니다.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from chaficial.database.base import Base


class BatchAuditLog(Base):
    """검색 및 수집 배치 실행 이력 테이블."""

    __tablename__ = "batch_audit_logs"

    batch_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source_platform: Mapped[str] = mapped_column(String(50), nullable=False)
    search_scope: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_partial_scrape: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
