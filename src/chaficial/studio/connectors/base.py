"""플랫폼 커넥터 추상 기본 클래스 및 쿼터 메트릭."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from pydantic import BaseModel

from chaficial.studio.models import ContentPlatform, VideoRecord


class ConnectorStatus(BaseModel):
    """플랫폼 커넥터의 현재 연결 상태 및 쿼터 정보."""
    platform: ContentPlatform
    is_connected: bool
    connection_mode: str  # "LIVE", "DEMO", "MANUAL_ONLY", "UNCONNECTED"
    daily_quota_limit: int = 10000
    daily_quota_used: int = 0
    quota_reset_at: datetime | None = None
    last_sync_at: datetime | None = None
    last_error: str | None = None
    rate_limit_per_minute: int = 60
    notes: str = ""


class PlatformConnector(ABC):
    """모든 플랫폼 커넥터가 구현해야 하는 추상 인터페이스."""

    @abstractmethod
    def get_status(self) -> ConnectorStatus:
        """현재 커넥터 상태 반환."""

    @abstractmethod
    def search_videos(
        self,
        query: str,
        max_results: int = 20,
        published_after: datetime | None = None,
    ) -> list[VideoRecord]:
        """키워드 기반 비디오 검색."""

    @abstractmethod
    def fetch_video_details(self, video_ids: list[str]) -> list[VideoRecord]:
        """특정 비디오 ID 목록의 상세 지표 갱신."""
