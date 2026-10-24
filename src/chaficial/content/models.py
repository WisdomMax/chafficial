"""CHA-FICIAL AI 콘텐츠 인텔리전스 & 영상 제작 시스템 데이터 모델 및 도메인 규칙.

DIRECTIVE 003-A2 개정 준수:
- 12단계 정밀 워크플로 상태 머신 (DRY_RUN_VALIDATED, GENERATION_SUCCEEDED 등)
- 팩트 증빙 추적 (FactEvidence: 근거 문서, 검증 시각, 검증자, 상태)
- 내부 사용 권한(internal_storage_allowed)과 외부 광고 재배포 권한(republication_allowed) 엄격 분리
- 대본 버전 관리 및 수정 시 기존 승인 자동 무효화 (invalidate_approval)
- 임의 단정 문구 및 허위 사실 자동 생성 방지
"""

from __future__ import annotations

import enum
import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

# ============================================================================
# 도메인 예외 정의
# ============================================================================

class ContentEngineError(Exception):
    """콘텐츠 엔진 기본 예외."""


class DuplicateTrendCandidateError(ContentEngineError):
    """동일한 영상 또는 URL이 이미 등록된 경우 발생하는 예외."""


class MissingVehicleInfoError(ContentEngineError):
    """차량 필수 정보가 누락되거나 미검증일 때 발생하는 예외."""


class UnauthorizedAssetError(ContentEngineError):
    """상업적 재배포 권한(republication_allowed)이 확보되지 않은 에셋 사용 시 발생하는 예외."""


class UnapprovedContentError(ContentEngineError):
    """전문가/관리자 최종 승인 없이 제작 준비/완료 단계로 진입할 때 발생하는 예외."""


class InvalidVehicleInterfaceError(ContentEngineError):
    """기존 차량 선별 엔진의 데이터 인터페이스 규격과 불일치할 때 발생하는 예외."""


class WorkflowTransitionError(ContentEngineError):
    """올바르지 않은 워크플로 상태 전이 시도 시 발생하는 예외."""


class CommercialIneligibilityError(MissingVehicleInfoError):
    """실제 판매 홍보가 불가능한 매물이 영상 제작 승인으로 넘어갈 때 발생하는 예외."""


class FactVerificationError(ContentEngineError):
    """객관적 증빙이 없는 문장을 사실(FACT)로 단정하려 할 때 발생하는 예외."""


# ============================================================================
# 열거형 정의
# ============================================================================

class ContentType(str, enum.Enum):
    """콘텐츠 유형."""
    EXPERT_STORY = "EXPERT_STORY"            # 트렌드 기반 전문가 썰 영상
    VEHICLE_PROMOTION = "VEHICLE_PROMOTION"  # 실제 추천 매물 홍보 영상


class ContentWorkflowStatus(str, enum.Enum):
    """제작 워크플로 정밀 상태 흐름 (Fail-closed & State Isolation)."""
    DISCOVERED = "DISCOVERED"                          # 후보 발견/등록
    SELECTED = "SELECTED"                              # 제작 대상 선정
    EXPERT_REVIEW = "EXPERT_REVIEW"                    # 25년 차마트 사장님 질의응답 및 팩트 검토
    SCRIPT_DRAFT = "SCRIPT_DRAFT"                      # 대본 초안 작성
    APPROVED = "APPROVED"                              # 최종 승인권자 서명 승인
    PRODUCTION_READY = "PRODUCTION_READY"              # 프롬프트/인가 에셋 준비 완료
    DRY_RUN_VALIDATED = "DRY_RUN_VALIDATED"            # 공식 API 규격 오프라인 검증 성공
    GENERATION_SUBMITTED = "GENERATION_SUBMITTED"      # 실제 API 호출 요청 전송
    GENERATION_SUCCEEDED = "GENERATION_SUCCEEDED"      # 실제 비디오 결과물 생성 완료 확인
    GENERATION_FAILED = "GENERATION_FAILED"            # 비디오 생성 실패
    PUBLISHED = "PUBLISHED"                            # SNS/쇼츠 게시 완료
    MEASURED = "MEASURED"                              # 성과 측정 및 피드백 수집


class VerificationStatus(str, enum.Enum):
    """팩트 증빙 검증 상태."""
    UNVERIFIED = "UNVERIFIED"              # 미검증
    VERIFY_REQUIRED = "VERIFY_REQUIRED"    # 증빙 추가 확인 필요
    VERIFIED = "VERIFIED"                  # 공식 문서로 검증 완료
    REJECTED = "REJECTED"                  # 허위 또는 불일치 판정


class ProvenanceType(str, enum.Enum):
    """대본 문장 및 팩트의 출처 유형."""
    FACT = "FACT"                        # 등록원부, 성능점검기록부 등 객관적 증빙 기반 팩트
    EXPERT_VERIFIED = "EXPERT_VERIFIED"  # 사장님이 구술하고 사실 검증을 거친 진술
    AI_CREATIVE = "AI_CREATIVE"          # AI가 제안한 창작 표현 (후킹, 묘사)


class AssetType(str, enum.Enum):
    """에셋 종류."""
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"


class VideoModelType(str, enum.Enum):
    """영상 생성 AI 엔진."""
    WAN_3_0 = "WAN_3_0"      # Runway Dev wan3 공식 모델
    KLING_4_0 = "KLING_4_0"  # 시네마틱 드라마 모델


# ============================================================================
# 자산 및 증빙 모델
# ============================================================================

class FactEvidence(BaseModel):
    """객관적 사실(FACT)에 대한 검증 증빙 모델."""
    evidence_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = Field(description="성능상태점검기록부, 자동차등록원부, 파트너계약서 등")
    document_ref: str = Field(description="문서 관리번호 또는 열람 고유키")
    verified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    verification_status: VerificationStatus = VerificationStatus.VERIFY_REQUIRED
    verified_by: str = Field(description="검증 담당자 또는 공인 시스템명")
    notes: str = ""


class MediaAsset(BaseModel):
    """제작에 활용되는 미디어 자산 모델."""
    asset_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_type: AssetType = AssetType.IMAGE
    path_or_url: str
    label: str = Field(description="에셋 설명 (예: 1열 보르도 레드 시트 등)")
    republication_allowed: bool = Field(
        default=False,
        description="상업적 외부 광고 영상 제작 및 재배포 권한 확보 여부"
    )
    internal_storage_allowed: bool = Field(
        default=False,
        description="단순 내부 분석 및 보관 권한 (외부 광고 허가와 엄격 분리)"
    )
    authorization_reference: str = Field(
        default="",
        description="재배포 권한 근거 문서 (예: 파트너 상업적 광고 동의서, 직접 촬영 원본)"
    )
    is_verified: bool = Field(default=False, description="실제 차량/인물과의 일치 여부 검증")
    verification_evidence_id: str | None = None
    slot_tag: str | None = Field(default=None, description="@Image 1, @Audio 1 등")

    @property
    def is_authorized(self) -> bool:
        """외부 제작에 사용 가능한지 여부: 오직 republication_allowed가 True일 때만 허용."""
        return self.republication_allowed


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
    provenance_type: ProvenanceType = ProvenanceType.FACT
    provenance_detail: str = Field(default="", description="출처 상세 근거")
    evidence: FactEvidence | None = None
    matched_asset_ids: list[str] = Field(default_factory=list)


class ContentScript(BaseModel):
    """콘텐츠 대본 모델 (버전 관리, 승인 무효화 및 내용 해시 무결성 보존)."""
    title: str
    version: int = 1
    hook_sentence: str
    full_text: str
    scenes: list[StoryboardScene] = Field(default_factory=list)
    is_approved: bool = False
    approved_by: str | None = None
    approved_at: datetime | None = None
    approved_version: int | None = None
    approved_content_hash: str | None = None

    def invalidate_approval(self, reason: str = "대본 내용 수정") -> None:
        """대본 수정 시 기존 승인을 즉시 무효화하고 버전을 증가."""
        self.is_approved = False
        self.approved_by = None
        self.approved_at = None
        self.approved_version = None
        self.approved_content_hash = None
        self.version += 1


# ============================================================================
# 핵심 필수 데이터 모델 (DIRECTIVE 003-A2 준수)
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

    def model_post_init(self, context: Any, /) -> None:
        if not self.content_hash and self.source_url:
            raw = f"{self.platform}:{self.source_url.strip()}"
            self.content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()


class VehicleContentCandidate(BaseModel):
    """B. 실제 추천 매물 콘텐츠 후보 모델 (Fail-closed 기본값 준수)."""
    candidate_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_id: str
    data_source: str
    model_name: str | None = None
    model_year: int | None = None
    price: int | None = Field(default=None, description="판매 가격 (만원 단위)")
    price_krw: int | None = Field(default=None, description="원천 원 단위 가격 (원)")
    mileage: int | None = Field(default=None, description="주행거리 (km)")
    options: list[str] = Field(default_factory=list)
    verified_pros: list[str] = Field(default_factory=list)
    precautions: list[str] = Field(default_factory=list)
    verified_at: datetime | None = None
    # Fail-closed 기본값: 미확인 시 VERIFY_REQUIRED
    availability_status: str = Field(
        default="VERIFY_REQUIRED",
        description="AVAILABLE, MISSING, VERIFY_REQUIRED, PARTNER_UNAPPROVED, DELISTED, SOLD_OUT"
    )
    partner_review_status: str = Field(
        default="PENDING",
        description="APPROVED, REJECTED, PENDING"
    )
    listing_status: str = Field(
        default="UNKNOWN",
        description="ACTIVE, PRICE_CHANGED, DELISTED, DELISTED_SUSPECT, UNKNOWN"
    )
    snapshot_observed_at: datetime | None = None
    images: list[MediaAsset] = Field(default_factory=list)
    evidences: list[FactEvidence] = Field(default_factory=list)
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
    """전문가 인터뷰 및 팩트 검토 모델 (진술 기록과 객관적 검증 분리)."""
    review_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_id: str
    target_type: ContentType
    generated_questions: list[str] = Field(default_factory=list)
    expert_answers: dict[str, str] = Field(
        default_factory=dict,
        description="사용자가 직접 입력한 대표님 진술 기록 자체"
    )
    verified_answers: dict[str, str] = Field(
        default_factory=dict,
        description="성능기록부/원부와 대조하여 객관적 사실로 검증된 진술"
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
    target_id: str = Field(description="TrendCandidate ID 또는 VehicleContentCandidate ID")
    script: ContentScript | None = None
    visual_assets: list[MediaAsset] = Field(default_factory=list)
    selected_model: VideoModelType = VideoModelType.WAN_3_0
    shot_prompts: list[ShotPrompt] = Field(default_factory=list)
    master_prompt: str | None = None
    api_payload: dict[str, Any] | None = None
    generation_result: dict[str, Any] | None = None
    result_video_url: str | None = None
    revision_history: list[dict[str, Any]] = Field(default_factory=list)
    performance_metrics: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def transition_to(self, target_status: ContentWorkflowStatus) -> None:
        """상태 전이 유효성 검사 및 엄격한 전이 실행 (Fail-closed)."""
        # 1. 미승인 상태에서 제작 준비(PRODUCTION_READY) 진입 차단
        if target_status == ContentWorkflowStatus.PRODUCTION_READY:
            if not self.script or not self.script.is_approved:
                raise UnapprovedContentError(
                    f"승인되지 않은 대본으로는 {target_status.value} 단계로 전이할 수 없습니다."
                )
            if not self.visual_assets:
                raise UnauthorizedAssetError("제작에 사용할 인가된 에셋이 1장도 없습니다.")
            for asset in self.visual_assets:
                if not asset.republication_allowed:
                    raise UnauthorizedAssetError(
                        f"에셋 '{asset.label}'({asset.path_or_url})의 상업적 재배포 권한이 없습니다."
                    )

        # 2. 드라이런 검증 없이 생성 제출/완료 단계 진입 차단
        if (
            target_status == ContentWorkflowStatus.GENERATION_SUBMITTED
            and self.status != ContentWorkflowStatus.DRY_RUN_VALIDATED
        ):
            raise WorkflowTransitionError(
                "공식 API 드라이런 검증(DRY_RUN_VALIDATED)을 통과하지 않고 생성을 제출할 수 없습니다."
            )

        # 3. 실제 결과 자산(result_video_url) 없이 성공 완료(GENERATION_SUCCEEDED) 처리 차단
        if target_status == ContentWorkflowStatus.GENERATION_SUCCEEDED and not self.result_video_url:
            raise WorkflowTransitionError(
                "실제 비디오 결과 자산(result_video_url)이 확인되지 않은 작업을 완료 처리할 수 없습니다."
            )

        old_status = self.status
        self.status = target_status
        self.updated_at = datetime.now(UTC)
        self.revision_history.append({
            "timestamp": self.updated_at.isoformat(),
            "from_status": old_status.value,
            "to_status": target_status.value,
        })
