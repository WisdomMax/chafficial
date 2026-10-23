"""CHA-FICIAL AI 콘텐츠 인텔리전스 & 영상 제작 시스템 데이터 모델 및 예외 정의.

DIRECTIVE 003-A 명세 준수:
- TrendCandidate
- VehicleContentCandidate
- ExpertReview
- ProductionProject
- 워크플로 상태 머신 및 안전성 검증
"""

from __future__ import annotations

import enum
import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# 도메인 예외 정의
# ============================================================================

class ContentEngineError(Exception):
    """콘텐츠 엔진 기본 예외."""


class DuplicateTrendCandidateError(ContentEngineError):
    """동일한 영상 또는 URL이 이미 등록된 경우 발생하는 예외."""


class MissingVehicleInfoError(ContentEngineError):
    """차량 필수 정보(연식, 가격, 주행거리, 모델명 등)가 누락되거나 미검증일 때 발생하는 예외."""


class UnauthorizedAssetError(ContentEngineError):
    """사용 권한(republication_allowed 등)이 확보되지 않은 이미지/에셋 사용 시 발생하는 예외."""


class UnapprovedContentError(ContentEngineError):
    """전문가/관리자 최종 승인 없이 제작 완료(PRODUCTION_READY, GENERATED) 단계로 진입할 때 발생하는 예외."""


class InvalidVehicleInterfaceError(ContentEngineError):
    """기존 차량 선별 엔진의 데이터 인터페이스 규격과 불일치할 때 발생하는 예외."""


class WorkflowTransitionError(ContentEngineError):
    """올바르지 않은 워크플로 상태 전이 시도 시 발생하는 예외."""


# ============================================================================
# 열거형 정의
# ============================================================================

class ContentType(str, enum.Enum):
    """콘텐츠 유형."""
    EXPERT_STORY = "EXPERT_STORY"            # 트렌드 기반 전문가 썰 영상
    VEHICLE_PROMOTION = "VEHICLE_PROMOTION"  # 실제 추천 매물 홍보 영상


class ContentWorkflowStatus(str, enum.Enum):
    """제작 워크플로 9단계 상태 흐름."""
    DISCOVERED = "DISCOVERED"              # 후보 발견/등록
    SELECTED = "SELECTED"                  # 제작 대상 선정
    EXPERT_REVIEW = "EXPERT_REVIEW"        # 25년 차마트 사장님 질의응답 및 팩트 검토
    SCRIPT_DRAFT = "SCRIPT_DRAFT"          # 대본 초안 작성
    APPROVED = "APPROVED"                  # 전문가 및 관리자 최종 승인
    PRODUCTION_READY = "PRODUCTION_READY"  # 프롬프트/에셋 준비 완료 (제작 대기)
    GENERATED = "GENERATED"                # 영상 생성 완료
    PUBLISHED = "PUBLISHED"                # SNS/쇼츠 게시 완료
    MEASURED = "MEASURED"                  # 성과 측정 및 피드백 수집


class AssetType(str, enum.Enum):
    """에셋 종류."""
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"


class VideoModelType(str, enum.Enum):
    """영상 생성 AI 엔진."""
    WAN_3_0 = "WAN_3_0"      # 기본: 한국어 대사, 얼굴 일관성, 매물 소개
    KLING_4_0 = "KLING_4_0"  # 보조: 시네마틱 드라마, 극적 연출


# ============================================================================
# 자산 및 세부 모델
# ============================================================================

class MediaAsset(BaseModel):
    """제작에 활용되는 미디어 자산 모델."""
    asset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_type: AssetType = AssetType.IMAGE
    path_or_url: str
    label: str = Field(description="에셋 설명 (예: 1열 보르도 레드 시트, 대표님 3열 시트 등)")
    is_authorized: bool = Field(
        default=False,
        description="상업적 영상 제작 및 재배포 권한 확보 여부 (republication_allowed)"
    )
    authorization_reference: str = Field(
        default="",
        description="이용 권한 근거 (예: 파트너 동의서, 직접 촬영, 초상권 활용 승낙)"
    )
    is_verified: bool = Field(default=False, description="실제 차량/인물과 일치 여부 검증")
    slot_tag: str | None = Field(
        default=None,
        description="Runway/Wan 모델 바인딩 태그 (예: @Image 1, @Audio 1)"
    )


class ShotPrompt(BaseModel):
    """영상 생성 모델에 주입되는 컷별(씬별) 프롬프트 명세."""
    scene_number: int
    duration_seconds: float = 4.0
    scene_title: str
    camera_movement: str
    visual_prompt: str
    dialogue: str
    audio_instruction: str
    reference_asset_tags: list[str] = Field(default_factory=list)


class StoryboardScene(BaseModel):
    """스토리보드 장면 구성."""
    scene_number: int
    title: str
    duration_seconds: float
    visual_description: str
    narration: str
    matched_asset_ids: list[str] = Field(default_factory=list)


class ContentScript(BaseModel):
    """콘텐츠 대본 모델."""
    title: str
    version: int = 1
    hook_sentence: str
    full_text: str
    scenes: list[StoryboardScene] = Field(default_factory=list)
    is_approved: bool = False
    approved_by: str | None = None
    approved_at: datetime | None = None


# ============================================================================
# 핵심 필수 데이터 모델 (DIRECTIVE 003-A 섹션 4 준수)
# ============================================================================

class TrendCandidate(BaseModel):
    """A. 트렌드 기반 인기 콘텐츠 후보 모델."""
    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: str = Field(description="YOUTUBE_SHORTS, INSTAGRAM_REELS, TIKTOK 등")
    source_url: str
    title: str
    account_name: str
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    uploaded_at: datetime | None = None
    search_keyword: str
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    content_hash: str = Field(default="", description="중복 방지용 고유 해시 식별자")
    popularity_score: float = Field(default=0.0, description="인기도 분석 점수")
    topic: str = Field(default="", description="분석된 콘텐츠 주제")
    structure_analysis: dict[str, Any] = Field(
        default_factory=dict,
        description="후킹, 본론, 반전, 편집 패턴 등 분석 결과"
    )

    @field_validator("content_hash", mode="before")
    @classmethod
    def compute_content_hash(cls, v: str, values: Any) -> str:
        if v:
            return v
        # platform과 source_url 기반 해시 자동 산출
        raw = f"{getattr(values, 'platform', '')}:{getattr(values, 'source_url', '')}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def model_post_init(self, context: Any, /) -> None:
        if not self.content_hash and self.source_url:
            raw = f"{self.platform}:{self.source_url.strip()}"
            self.content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()


class VehicleContentCandidate(BaseModel):
    """B. 실제 추천 매물 콘텐츠 후보 모델 (기존 차량 선별 엔진 연동)."""
    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_id: str
    data_source: str
    model_name: str | None = None
    model_year: int | None = None
    price: int | None = Field(default=None, description="판매 가격 (만원 단위)")
    mileage: int | None = Field(default=None, description="주행거리 (km)")
    options: list[str] = Field(default_factory=list)
    verified_pros: list[str] = Field(default_factory=list)
    precautions: list[str] = Field(default_factory=list)
    verified_at: datetime | None = None
    availability_status: str = Field(
        default="VERIFY_REQUIRED",
        description="AVAILABLE, MISSING, VERIFY_REQUIRED, SOLD_OUT"
    )
    images: list[MediaAsset] = Field(default_factory=list)
    recommendation_reason: str = ""
    recommendation_source: str = "OPPORTUNITY_ENGINE"

    def validate_essential_info(self) -> tuple[bool, list[str]]:
        """필수 정보 누락 여부 검증."""
        missing: list[str] = []
        if not self.model_name:
            missing.append("model_name")
        if self.model_year is None or self.model_year <= 1990:
            missing.append("model_year")
        if self.price is None or self.price <= 0:
            missing.append("price")
        if self.mileage is None or self.mileage < 0:
            missing.append("mileage")
        return (len(missing) == 0, missing)


class ExpertReview(BaseModel):
    """전문가(25년 경력 차마트 사장님) 인터뷰 및 팩트 검토 모델."""
    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_id: str = Field(description="연결된 영상 소재(TrendCandidate) 또는 차량 ID")
    target_type: ContentType
    generated_questions: list[str] = Field(default_factory=list)
    expert_answers: dict[str, str] = Field(
        default_factory=dict,
        description="사용자가 직접 입력한 차마트 사장님 답변"
    )
    fact_check_items: list[str] = Field(default_factory=list)
    approval_status: str = Field(default="PENDING", description="PENDING, APPROVED, REJECTED")
    reviewer_name: str = "차마트 사장님 (25년 경력)"
    reviewed_at: datetime | None = None
    revision_notes: str | None = None


class ProductionProject(BaseModel):
    """통합 콘텐츠 제작 프로젝트 모델."""
    project_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_type: ContentType
    status: ContentWorkflowStatus = ContentWorkflowStatus.DISCOVERED
    target_id: str = Field(description="연결된 TrendCandidate ID 또는 VehicleContentCandidate ID")
    script: ContentScript | None = None
    visual_assets: list[MediaAsset] = Field(default_factory=list)
    selected_model: VideoModelType = VideoModelType.WAN_3_0
    shot_prompts: list[ShotPrompt] = Field(default_factory=list)
    master_prompt: str | None = None
    generation_result: dict[str, Any] | None = None
    revision_history: list[dict[str, Any]] = Field(default_factory=list)
    performance_metrics: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def transition_to(self, target_status: ContentWorkflowStatus) -> None:
        """상태 전이 유효성 검사 및 전이 실행."""
        # 1. 미승인 상태에서 제작 완료 단계(PRODUCTION_READY / GENERATED) 전이 차단
        if (
            target_status in (ContentWorkflowStatus.PRODUCTION_READY, ContentWorkflowStatus.GENERATED)
            and (not self.script or not self.script.is_approved)
        ):
            raise UnapprovedContentError(
                f"승인되지 않은 대본으로는 {target_status.value} 단계로 전이할 수 없습니다. "
                "전문가/관리자 최종 승인이 필요합니다."
            )

        # 2. 제작 준비 단계에서 권한 없는 에셋 검사
        if target_status == ContentWorkflowStatus.PRODUCTION_READY:
            for asset in self.visual_assets:
                if not asset.is_authorized:
                    raise UnauthorizedAssetError(
                        f"에셋 '{asset.label}'({asset.path_or_url})의 사용 권한이 없습니다. "
                        "권한 없는 자료는 제작에 사용할 수 없습니다."
                    )

        # 상태 업데이트 및 이력 기록
        old_status = self.status
        self.status = target_status
        self.updated_at = datetime.now(UTC)
        self.revision_history.append({
            "timestamp": self.updated_at.isoformat(),
            "from_status": old_status.value,
            "to_status": target_status.value,
        })
