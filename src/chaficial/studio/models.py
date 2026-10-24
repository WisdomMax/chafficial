"""CHA-FICIAL AI Content Studio 도메인 모델.

DIRECTIVE 004-A 명세 준수:
- 플랫폼(YouTube, Instagram, TikTok) 및 포맷(YouTube Long-form, YouTube Shorts, Reels, TikTok) 분리
- Shorts 여부 추정 신뢰도(VERIFIED vs ESTIMATED)
- 원본 영상 메타데이터 및 지표 변화 추적
- 토픽 클러스터링 및 AI 주제 추천 (TOP 5~10, 통계 점수, 딜러 활용도, 신뢰 수준)
- 롱폼 분석 및 쇼츠 소재 추출 (자막 유무에 따른 분석 범위 정직 표기)
- 제작 기획서(제목 3종, 후킹 3종, 딜러 질문 3~5종, 사장님 답변 반영 대본 및 연출 가이드)
- 상태 머신(RECOMMENDED, ADOPTED, SHELVED, DISMISSED)
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ContentPlatform(str, Enum):
    """분석 대상 미디어 플랫폼."""
    YOUTUBE = "YOUTUBE"
    INSTAGRAM = "INSTAGRAM"
    TIKTOK = "TIKTOK"


class ContentFormat(str, Enum):
    """콘텐츠 세부 형식."""
    YOUTUBE_LONG = "YOUTUBE_LONG"      # 유튜브 일반 영상 (롱폼)
    YOUTUBE_SHORTS = "YOUTUBE_SHORTS"  # 유튜브 쇼츠 (<=60초, 쇼츠 URL)
    INSTAGRAM_REELS = "INSTAGRAM_REELS"# 인스타그램 릴스
    TIKTOK_VIDEO = "TIKTOK_VIDEO"      # 틱톡 비디오
    UNKNOWN = "UNKNOWN"


class FormatConfidence(str, Enum):
    """쇼츠/롱폼 분류 신뢰 수준."""
    VERIFIED = "VERIFIED"    # 공식 API 또는 URL 구조(#shorts, /shorts/)로 검증됨
    ESTIMATED = "ESTIMATED"  # 영상 길이(<=60s) 및 세로비 등으로 추정됨


class AnalysisConfidence(str, Enum):
    """AI 분석 및 근거 신뢰 수준."""
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class TopicStatus(str, Enum):
    """추천 주제의 상태."""
    RECOMMENDED = "RECOMMENDED"  # AI가 추천한 신규 주제
    ADOPTED = "ADOPTED"          # 사용자가 채택함 (기획/제작 진행)
    SHELVED = "SHELVED"          # 보류
    DISMISSED = "DISMISSED"      # 제외 (추천 목록에서 숨김)


class VideoRecord(BaseModel):
    """수집된 단일 영상 레코드."""
    video_id: str
    platform: ContentPlatform
    content_format: ContentFormat
    format_confidence: FormatConfidence = FormatConfidence.ESTIMATED
    url: str
    title: str
    channel_name: str
    channel_id: str | None = None
    description: str = ""
    published_at: datetime
    duration_seconds: int = 0
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    has_captions: bool = False
    caption_text: str | None = None
    matched_keywords: list[str] = Field(default_factory=list)
    topic_ids: list[str] = Field(default_factory=list)
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class TopicCluster(BaseModel):
    """공통 주제로 클러스터링된 토픽 그룹."""
    cluster_id: str = Field(default_factory=lambda: str(uuid4()))
    cluster_name: str
    primary_category: str  # 예: 감가상각, 허위매물, 수리비, 특정차종(BMW/벤츠), 첫차추천 등
    keywords: list[str] = Field(default_factory=list)
    video_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TopicRecommendation(BaseModel):
    """AI가 선정한 추천 주제 (TOP 5~10)."""
    recommendation_id: str = Field(default_factory=lambda: str(uuid4()))
    topic_name: str
    category: str
    rank: int = 1
    popularity_score: float = 0.0          # 통계적 인기 점수 (조회수/반응/감쇄)
    velocity_score: float = 0.0            # 최근 성장 속도
    dealer_fit_score: float = 0.0          # 차마트 25년 딜러 경험 활용도 점수
    composite_score: float = 0.0           # 종합 추천 점수
    status: TopicStatus = TopicStatus.RECOMMENDED
    confidence_level: AnalysisConfidence = AnalysisConfidence.HIGH_CONFIDENCE
    supporting_video_ids: list[str] = Field(default_factory=list)
    selection_reason: str                  # 선정 이유 (근거 중심 서술)
    trend_summary: str                     # 시청자 관심사 및 트렌드 패턴 요약
    is_newly_discovered: bool = True       # 신규 발견 여부
    prompt_version: str = "v1.0.0"         # 분석에 사용된 프롬프트/규칙 버전
    model_name: str = "chaficial-rule-stats-hybrid-v1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ShortExtractIdea(BaseModel):
    """유튜브 롱폼에서 추출된 쇼츠 파생 소재."""
    idea_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    core_question: str
    timecode_range: str                    # 예: "02:15 ~ 03:05"
    key_insight: str
    fact_check_needed: list[str] = Field(default_factory=list)


class LongFormAnalysis(BaseModel):
    """유튜브 롱폼 영상의 심층 쇼츠 소재 분석 결과."""
    analysis_id: str = Field(default_factory=lambda: str(uuid4()))
    video_id: str
    analyzed_from_captions: bool           # True면 자막 기반 정밀 분석, False면 제목/설명만 분석
    main_claim: str                        # 영상의 중심 주장
    core_examples: list[str] = Field(default_factory=list)
    audience_questions: list[str] = Field(default_factory=list)
    short_extracts: list[ShortExtractIdea] = Field(default_factory=list) # 쇼츠 독립 주제 1~5개
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VideoStrategy(BaseModel):
    """콘텐츠 영상 전략."""
    audience_hook_reason: str              # 시청자가 관심을 가질 이유
    recommended_format: str                # 전문가 썰 / 정보형 / 비교형 / 실제 사례형
    target_duration_seconds: int = 30      # 권장 길이 (쇼츠 30~50초)
    flow_summary: str                      # 전체 영상 흐름
    thumbnail_concept: str                 # 썸네일 콘셉트
    caption_visual_concept: str            # 자막 및 시각 연출 콘셉트


class ProductionSceneGuide(BaseModel):
    """제작 가이드 내 연출 씬."""
    scene_number: int
    phase: str                             # 오프닝 / 전개 / 반전 or 중요정보 / 결론 / CTA
    narration_guide: str
    visual_broll_guide: str                # 컷별 필요한 자료 화면
    dealer_face_recommended: bool          # 딜러 얼굴 노출이 효과적인 장면인지 여부


class ProductionBrief(BaseModel):
    """제작 기획서 (차마트 사장님 인터뷰 및 대본 연출 가이드 포함)."""
    brief_id: str = Field(default_factory=lambda: str(uuid4()))
    recommendation_id: str
    topic_name: str
    
    # A. 추천 제목 및 후킹
    recommended_titles: list[str] = Field(default_factory=list)  # 제목 후보 3개
    hook_sentences: list[str] = Field(default_factory=list)      # 첫 3초 후킹 후보 3개
    
    # B. 영상 전략
    strategy: VideoStrategy
    
    # C. 차마트 사장님 인터뷰
    interview_questions: list[str] = Field(default_factory=list) # 질문 3~5개
    fact_check_items: list[str] = Field(default_factory=list)    # 사실 확인 필요 항목
    experience_vs_opinion_questions: list[str] = Field(default_factory=list) # 경험/의견 구분 추가 질문
    expert_answers: dict[str, str] = Field(default_factory=dict) # 사장님의 실제 입력 답변
    has_expert_answered: bool = False
    
    # D. 대본과 연출 가이드
    draft_script_text: str = ""                                  # 답변 반영 대본 초안
    scene_guides: list[ProductionSceneGuide] = Field(default_factory=list)
    
    # E. 연결 및 승인 이력
    linked_project_id: str | None = None                         # 기존 ContentProductionPipeline 프로젝트 ID
    is_approved: bool = False
    revision_count: int = 1
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
