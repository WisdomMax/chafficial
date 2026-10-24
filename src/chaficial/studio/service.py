"""CHA-FICIAL AI Content Studio 통합 서비스 파사드.

DIRECTIVE 004-A 명세 준수:
- 다차원 검색 실행 및 쿼터 추적
- 토픽 클러스터링 및 TOP 5~10 추천 산출
- 주제 채택/보류/제외 상태 관리
- 제작 기획서 생성 및 차마트 사장님 피드백 반영
- 롱폼 영상 심층 분석
- 기존 chaficial.content ContentProductionPipeline (EXPERT_STORY) 프로젝트 생성 연계
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from chaficial.content.pipeline import ContentProductionPipeline
from chaficial.content.repository import ContentRepository
from chaficial.studio.brief_generator import ProductionBriefGenerator
from chaficial.studio.connectors.base import ConnectorStatus
from chaficial.studio.connectors.external import InstagramConnector, TikTokConnector
from chaficial.studio.connectors.youtube import YouTubeConnector
from chaficial.studio.longform_engine import LongFormAnalysisEngine
from chaficial.studio.models import (
    ContentFormat,
    ContentPlatform,
    LongFormAnalysis,
    ProductionBrief,
    TopicRecommendation,
    TopicStatus,
    VideoRecord,
)
from chaficial.studio.storage import StudioStorage
from chaficial.studio.topic_engine import TopicDiscoveryEngine

# 기본 추천 중고차 검색 키워드 모음 (지시서 명시)
DEFAULT_SEARCH_KEYWORDS = [
    "중고차",
    "중고차 추천",
    "감가상각",
    "중고차 수리비",
    "중고 BMW",
    "벤츠 중고",
    "가성비 중고차",
    "자동차 구매 후회",
    "허위매물",
    "사고차",
    "엔진 고장",
    "자동차 유지비",
]


class StudioService:
    """스튜디오 전체 유스케이스를 관리하는 중앙 서비스 클래스."""

    def __init__(
        self,
        storage: StudioStorage | None = None,
        youtube_connector: YouTubeConnector | None = None,
        content_pipeline: ContentProductionPipeline | None = None,
    ) -> None:
        self.storage = storage or StudioStorage()
        self.youtube = youtube_connector or YouTubeConnector()
        self.instagram = InstagramConnector()
        self.tiktok = TikTokConnector()
        self.topic_engine = TopicDiscoveryEngine()
        self.longform_engine = LongFormAnalysisEngine()
        self.brief_generator = ProductionBriefGenerator()
        self.content_pipeline = content_pipeline or ContentProductionPipeline(ContentRepository())

        # 기본 설정 초기화
        self._ensure_initial_settings()

    def _ensure_initial_settings(self) -> None:
        raw_keywords = self.storage.get_setting("search_keywords")
        if not raw_keywords:
            self.storage.set_setting("search_keywords", json.dumps(DEFAULT_SEARCH_KEYWORDS, ensure_ascii=False))
        if not self.storage.get_setting("operation_mode"):
            self.storage.set_setting("operation_mode", "INTENSIVE_DISCOVERY")  # INTENSIVE_DISCOVERY / STABLE_OPERATION

    # =========================================================================
    # 1. 검색 및 데이터 수집
    # =========================================================================

    def run_discovery_search(self, custom_keywords: list[str] | None = None) -> dict[str, Any]:
        """등록된 키워드들을 기반으로 플랫폼 검색을 실행하고 신규 비디오를 영속화."""
        keywords = custom_keywords or json.loads(self.storage.get_setting("search_keywords", "[]"))
        if not keywords:
            keywords = DEFAULT_SEARCH_KEYWORDS

        all_discovered: list[VideoRecord] = []
        for kw in keywords:
            videos = self.youtube.search_videos(query=kw, max_results=10)
            for v in videos:
                if kw not in v.matched_keywords:
                    v.matched_keywords.append(kw)
            all_discovered.extend(videos)

        # 중복 제거 (video_id 기준)
        unique_videos: dict[str, VideoRecord] = {}
        for v in all_discovered:
            if v.video_id not in unique_videos:
                unique_videos[v.video_id] = v
            else:
                for kw in v.matched_keywords:
                    if kw not in unique_videos[v.video_id].matched_keywords:
                        unique_videos[v.video_id].matched_keywords.append(kw)

        video_list = list(unique_videos.values())
        self.storage.save_videos(video_list)

        # 토픽 재클러스터링 및 추천 갱신
        top_topics = self.refresh_topic_recommendations()

        return {
            "searched_keywords": keywords,
            "total_videos_found": len(video_list),
            "top_topics_count": len(top_topics),
            "executed_at": datetime.now(UTC).isoformat(),
        }

    def list_videos(
        self,
        platform: ContentPlatform | None = None,
        content_format: ContentFormat | None = None,
        limit: int = 100,
    ) -> list[VideoRecord]:
        videos = self.storage.list_videos(platform=platform, content_format=content_format, limit=limit)
        if not videos:
            # 최초 실행 시 저장된 영상이 없으면 기본 데모 수집 자동 1회 실행
            self.run_discovery_search()
            videos = self.storage.list_videos(platform=platform, content_format=content_format, limit=limit)
        return videos

    # =========================================================================
    # 2. 토픽 클러스터링 및 추천 랭킹
    # =========================================================================

    def refresh_topic_recommendations(self) -> list[TopicRecommendation]:
        """저장된 모든 비디오를 기반으로 TOP 5~10 추천 주제를 계산하고 영속화."""
        all_videos = self.storage.list_videos(limit=500)
        if not all_videos:
            self.run_discovery_search()
            all_videos = self.storage.list_videos(limit=500)

        top_recs = self.topic_engine.rank_top_topics(all_videos, top_n=10)

        # 기존 상태(채택/보류/제외) 보존 매핑
        existing_recs = {r.topic_name: r for r in self.storage.list_topic_recommendations()}
        for rec in top_recs:
            if rec.topic_name in existing_recs:
                old = existing_recs[rec.topic_name]
                rec.recommendation_id = old.recommendation_id
                rec.status = old.status
                rec.is_newly_discovered = False

            # 기획서가 아직 없으면 초기 기획서 자동 생성 및 보존
            if not self.storage.get_brief_by_recommendation(rec.recommendation_id):
                brief = self.brief_generator.generate_initial_brief(rec)
                self.storage.save_brief(brief)

        self.storage.save_topic_recommendations(top_recs)
        return top_recs

    def get_topic_recommendations(self, status: TopicStatus | None = None) -> list[TopicRecommendation]:
        recs = self.storage.list_topic_recommendations(status=status)
        if not recs:
            recs = self.refresh_topic_recommendations()
            if status:
                recs = [r for r in recs if r.status == status]
        return recs

    def update_topic_status(self, recommendation_id: str, new_status: TopicStatus) -> bool:
        return self.storage.update_topic_status(recommendation_id, new_status)

    # =========================================================================
    # 3. 제작 기획서 및 사장님 피드백
    # =========================================================================

    def get_or_create_brief(self, recommendation_id: str) -> ProductionBrief | None:
        brief = self.storage.get_brief_by_recommendation(recommendation_id)
        if brief:
            return brief

        recs = {r.recommendation_id: r for r in self.storage.list_topic_recommendations()}
        if recommendation_id not in recs:
            return None

        brief = self.brief_generator.generate_initial_brief(recs[recommendation_id])
        self.storage.save_brief(brief)
        return brief

    def submit_expert_answers(
        self,
        recommendation_id: str,
        answers: dict[str, str],
    ) -> ProductionBrief | None:
        brief = self.get_or_create_brief(recommendation_id)
        if not brief:
            return None

        updated_brief = self.brief_generator.apply_expert_feedback(brief, answers)
        self.storage.save_brief(updated_brief)
        return updated_brief

    def link_to_content_pipeline(self, recommendation_id: str) -> str | None:
        """기획서를 기존 차피셜 ContentProductionPipeline(EXPERT_STORY) 프로젝트와 연계."""
        brief = self.get_or_create_brief(recommendation_id)
        if not brief:
            return None

        # 기존 TrendCandidate로 등록 후 프로젝트 생성
        candidate = self.content_pipeline.trend_engine.register_trend_candidate(
            platform="YOUTUBE_SHORTS",
            source_url="https://studio.chafficial.local/topics/" + recommendation_id,
            title=brief.recommended_titles[0] if brief.recommended_titles else brief.topic_name,
            account_name="장안평 차마트 대표",
            view_count=500000,
            like_count=20000,
            comment_count=1500,
        )
        project = self.content_pipeline.create_trend_project(candidate.candidate_id)
        brief.linked_project_id = project.project_id
        brief.is_approved = True
        self.storage.save_brief(brief)
        self.update_topic_status(recommendation_id, TopicStatus.ADOPTED)
        return project.project_id

    # =========================================================================
    # 4. 롱폼 분석
    # =========================================================================

    def analyze_longform(self, video_id: str, custom_transcript: str | None = None) -> LongFormAnalysis | None:
        all_videos = {v.video_id: v for v in self.storage.list_videos(limit=500)}
        if video_id not in all_videos:
            return None
        return self.longform_engine.analyze_longform_video(all_videos[video_id], custom_transcript)

    # =========================================================================
    # 5. 설정 및 커넥터 상태
    # =========================================================================

    def get_connectors_status(self) -> list[ConnectorStatus]:
        return [
            self.youtube.get_status(),
            self.instagram.get_status(),
            self.tiktok.get_status(),
        ]

    def get_settings(self) -> dict[str, Any]:
        return {
            "search_keywords": json.loads(self.storage.get_setting("search_keywords", "[]")),
            "operation_mode": self.storage.get_setting("operation_mode", "INTENSIVE_DISCOVERY"),
            "connectors": [s.model_dump() for s in self.get_connectors_status()],
        }

    def update_settings(self, keywords: list[str] | None = None, operation_mode: str | None = None) -> None:
        if keywords is not None:
            self.storage.set_setting("search_keywords", json.dumps(keywords, ensure_ascii=False))
        if operation_mode is not None:
            self.storage.set_setting("operation_mode", operation_mode)
