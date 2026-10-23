"""배치 수집 및 미노출 판정 감사 로그 모델.

각 검색 수집 배치의 고유 batch_id를 영속 보존하여,
동일 배치의 중복 호출이나 재시도 시 매물 누락 카운터가 중복 증가하는 결함을 원천 차단합니다.
"""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text
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
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def get_audit_metadata(self) -> dict[str, Any] | None:
        """notes 필드에 직렬화된 JSON 메타데이터를 파싱하여 반환합니다.

        일반 텍스트이거나 비어있는 경우(레거시 배치) None을 반환합니다.
        """
        if not self.notes or not self.notes.strip():
            return None
        trimmed = self.notes.strip()
        if trimmed.startswith("{") and trimmed.endswith("}"):
            try:
                data = json.loads(trimmed)
                if isinstance(data, dict):
                    return data
            except Exception:
                return None
        return None

    def set_audit_metadata(self, metadata: dict[str, Any]) -> None:
        """구조화된 감사 메타데이터를 JSON 형태로 notes 필드에 안전하게 직렬화합니다."""
        self.notes = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
