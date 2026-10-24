"""Instagram 및 TikTok 외부 플랫폼 커넥터.

DIRECTIVE 004-A 명세 준수:
- 공식 API 미연결 시 정직하게 UNCONNECTED / MANUAL_ONLY 상태 표기
- 수동 URL 등록 및 CSV 임포트 지원
- 합법적 메타데이터 제공업체 및 CSV 가져오기 연동 규격 지원
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from chaficial.studio.connectors.base import ConnectorStatus, PlatformConnector
from chaficial.studio.models import (
    ContentFormat,
    ContentPlatform,
    FormatConfidence,
    VideoRecord,
)


class InstagramConnector(PlatformConnector):
    """Instagram Reels 커넥터 (수동 등록 및 CSV 임포트 지원, 공식 API 미연결 상태 정직 표기)."""

    def __init__(self) -> None:
        self.manual_videos: list[VideoRecord] = []
        self.last_sync_at: datetime | None = None

    def get_status(self) -> ConnectorStatus:
        return ConnectorStatus(
            platform=ContentPlatform.INSTAGRAM,
            is_connected=False,
            connection_mode="MANUAL_OR_CSV_ONLY",
            daily_quota_limit=0,
            daily_quota_used=0,
            notes="Instagram 공식 Graph API 미연동 (현재 CSV 임포트 및 수동 URL 등록만 활성화됨)",
        )

    def search_videos(
        self,
        query: str,
        max_results: int = 20,
        published_after: datetime | None = None,
    ) -> list[VideoRecord]:
        q = query.lower()
        matched = [v for v in self.manual_videos if q in v.title.lower() or q in v.description.lower()]
        return matched[:max_results]

    def fetch_video_details(self, video_ids: list[str]) -> list[VideoRecord]:
        return [v for v in self.manual_videos if v.video_id in video_ids]

    def add_manual_video(
        self,
        url: str,
        title: str,
        account_name: str,
        view_count: int = 0,
        like_count: int = 0,
        comment_count: int = 0,
        description: str = "",
    ) -> VideoRecord:
        """인스타그램 릴스 수동 URL 등록."""
        import uuid
        record = VideoRecord(
            video_id=f"ig_{uuid.uuid4().hex[:8]}",
            platform=ContentPlatform.INSTAGRAM,
            content_format=ContentFormat.INSTAGRAM_REELS,
            format_confidence=FormatConfidence.VERIFIED,
            url=url,
            title=title,
            channel_name=account_name,
            description=description,
            published_at=datetime.now(UTC),
            duration_seconds=30,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            matched_keywords=["수동등록", "릴스"],
        )
        self.manual_videos.append(record)
        return record

    def import_csv(self, csv_content: str) -> int:
        """CSV 텍스트로부터 비디오 레코드 일괄 인입."""
        reader = csv.DictReader(io.StringIO(csv_content))
        count = 0
        for row in reader:
            url = row.get("url", "")
            title = row.get("title", "")
            account = row.get("account", row.get("channel", "알수없음"))
            views = int(row.get("view_count", row.get("views", 0)) or 0)
            likes = int(row.get("like_count", row.get("likes", 0)) or 0)
            if url and title:
                self.add_manual_video(url, title, account, views, likes)
                count += 1
        return count


class TikTokConnector(PlatformConnector):
    """TikTok 커넥터 (수동 등록 및 CSV 임포트 지원, 공식 API 미연결 상태 정직 표기)."""

    def __init__(self) -> None:
        self.manual_videos: list[VideoRecord] = []

    def get_status(self) -> ConnectorStatus:
        return ConnectorStatus(
            platform=ContentPlatform.TIKTOK,
            is_connected=False,
            connection_mode="MANUAL_OR_CSV_ONLY",
            daily_quota_limit=0,
            daily_quota_used=0,
            notes="TikTok 공식 Research API 미연동 (현재 CSV 임포트 및 수동 URL 등록만 활성화됨)",
        )

    def search_videos(
        self,
        query: str,
        max_results: int = 20,
        published_after: datetime | None = None,
    ) -> list[VideoRecord]:
        q = query.lower()
        matched = [v for v in self.manual_videos if q in v.title.lower() or q in v.description.lower()]
        return matched[:max_results]

    def fetch_video_details(self, video_ids: list[str]) -> list[VideoRecord]:
        return [v for v in self.manual_videos if v.video_id in video_ids]

    def add_manual_video(
        self,
        url: str,
        title: str,
        account_name: str,
        view_count: int = 0,
        like_count: int = 0,
        comment_count: int = 0,
        description: str = "",
    ) -> VideoRecord:
        """틱톡 비디오 수동 등록."""
        import uuid
        record = VideoRecord(
            video_id=f"tk_{uuid.uuid4().hex[:8]}",
            platform=ContentPlatform.TIKTOK,
            content_format=ContentFormat.TIKTOK_VIDEO,
            format_confidence=FormatConfidence.VERIFIED,
            url=url,
            title=title,
            channel_name=account_name,
            description=description,
            published_at=datetime.now(UTC),
            duration_seconds=30,
            view_count=view_count,
            like_count=like_count,
            comment_count=comment_count,
            matched_keywords=["수동등록", "틱톡"],
        )
        self.manual_videos.append(record)
        return record
