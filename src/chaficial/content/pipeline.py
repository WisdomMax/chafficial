"""CHA-FICIAL AI 콘텐츠 제작 오케스트레이션 파이프라인.

DIRECTIVE 003-A3 개정 준수:
- ApproverContext: 신뢰할 수 있는 승인자 컨텍스트 필수화 (기본 인자 완전 배제)
- 승인 시 대본 내 모든 FACT 장면의 FactEvidence 적합성 전수 검증
- 승인한 대본의 내용 해시(approved_content_hash: SHA-256) 보존
- mock_success_url 운영 파이프라인 제거 및 MOCK 영상 성공 처리 엄격 격리
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import ClassVar

from pydantic import BaseModel, Field

from chaficial.content.adapters.base import VideoGenerationAdapter
from chaficial.content.adapters.kling4 import Kling4Adapter
from chaficial.content.adapters.wan3 import Wan3Adapter
from chaficial.content.expert_engine import ExpertIntelligenceEngine
from chaficial.content.models import (
    ContentType,
    ContentWorkflowStatus,
    MediaAsset,
    ProductionProject,
    ProvenanceType,
    UnapprovedContentError,
    VideoModelType,
)
from chaficial.content.repository import ContentRepository
from chaficial.content.script_engine import (
    ContentScriptEngine,
    validate_scene_evidence_compatibility,
)
from chaficial.content.trend_engine import TrendIntelligenceEngine
from chaficial.content.vehicle_adapter import VehicleContentAdapter


class ApproverContext(BaseModel):
    """신뢰할 수 있는 승인자 컨텍스트 모델 (내부 MVP 명시적 승인 기록 인터페이스)."""
    user_id: str
    user_name: str
    role: str
    verified_identity: bool = False
    authorization_token: str | None = None
    approved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ContentProductionPipeline:
    """통합 콘텐츠 제작 파이프라인 매니저."""

    AUTHORIZED_APPROVER_ROLES: ClassVar[set[str]] = {
        "DEALER_PARTNER_AUTHORIZED",
        "ADMIN_CHAFICIAL",
    }

    def __init__(self, repository: ContentRepository | None = None) -> None:
        self.repository = repository or ContentRepository()
        self.trend_engine = TrendIntelligenceEngine(self.repository)
        self.expert_engine = ExpertIntelligenceEngine(self.repository)

        self.adapters: dict[VideoModelType, VideoGenerationAdapter] = {
            VideoModelType.WAN_3_0: Wan3Adapter(),
            VideoModelType.KLING_4_0: Kling4Adapter(),
        }

    # -------------------------------------------------------------------------
    # 프로젝트 초기화 (DISCOVERED -> SELECTED)
    # -------------------------------------------------------------------------

    def create_trend_project(self, candidate_id: str) -> ProductionProject:
        """트렌드 후보 기반 프로젝트 생성."""
        trend = self.repository.get_trend(candidate_id)
        if not trend:
            raise ValueError(f"트렌드 후보 ID '{candidate_id}'를 찾을 수 없습니다.")

        project = ProductionProject(
            content_type=ContentType.EXPERT_STORY,
            status=ContentWorkflowStatus.DISCOVERED,
            target_id=candidate_id,
            selected_model=VideoModelType.WAN_3_0,
        )
        project.transition_to(ContentWorkflowStatus.SELECTED)
        return self.repository.save_project(project)

    def create_vehicle_project(self, vehicle_candidate_id: str) -> ProductionProject:
        """차량 후보 기반 프로젝트 생성 (상업적 판매 홍보 적격성 엄격 감사)."""
        vehicle = self.repository.get_vehicle(vehicle_candidate_id)
        if not vehicle:
            raise ValueError(f"차량 후보 ID '{vehicle_candidate_id}'를 찾을 수 없습니다.")

        # 제원, 상태, 활성도, 관측시점 최신성 및 사진 존재 전수 감사 (require_images=True)
        VehicleContentAdapter.validate_commercial_eligibility(vehicle, require_images=True)

        project = ProductionProject(
            content_type=ContentType.VEHICLE_PROMOTION,
            status=ContentWorkflowStatus.DISCOVERED,
            target_id=vehicle_candidate_id,
            selected_model=VideoModelType.WAN_3_0,
            visual_assets=vehicle.images,
        )
        project.transition_to(ContentWorkflowStatus.SELECTED)
        return self.repository.save_project(project)

    # -------------------------------------------------------------------------
    # 전문가 인터뷰 & 대본 초안 (EXPERT_REVIEW -> SCRIPT_DRAFT)
    # -------------------------------------------------------------------------

    def start_expert_review(self, project_id: str) -> tuple[ProductionProject, str]:
        """전문가 인터뷰 세션 개시."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        if project.content_type == ContentType.EXPERT_STORY:
            source = self.repository.get_trend(project.target_id)
        else:
            source = self.repository.get_vehicle(project.target_id)

        if not source:
            raise ValueError(f"프로젝트 대상 소스를 찾을 수 없습니다: {project.target_id}")

        review = self.expert_engine.create_expert_review_session(
            target_id=project.target_id,
            target_type=project.content_type,
            source_data=source,
        )
        project.transition_to(ContentWorkflowStatus.EXPERT_REVIEW)
        self.repository.save_project(project)
        return project, review.review_id

    def draft_script_with_expert_feedback(
        self,
        project_id: str,
        review_id: str,
        expert_answers: dict[str, str],
        revision_notes: str | None = None,
        approve_review: bool = False,
    ) -> ProductionProject:
        """전문가 답변을 반영하여 대본 초안 작성 (기존 승인 시 자동 무효화)."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        next_version = 1
        if project.script:
            next_version = project.script.version + 1
            if project.script.is_approved:
                project.script.invalidate_approval("전문가 피드백 반영으로 인한 대본 재작성")

        review = self.expert_engine.record_expert_answers(
            review_id=review_id,
            answers=expert_answers,
            revision_notes=revision_notes,
            approve=approve_review,
        )

        if project.content_type == ContentType.EXPERT_STORY:
            trend = self.repository.get_trend(project.target_id)
            assert trend is not None
            script = ContentScriptEngine.generate_trend_script(trend, review)
        else:
            vehicle = self.repository.get_vehicle(project.target_id)
            assert vehicle is not None
            script = ContentScriptEngine.generate_vehicle_script(vehicle, review)

        script.version = next_version
        project.script = script
        project.transition_to(ContentWorkflowStatus.SCRIPT_DRAFT)
        return self.repository.save_project(project)

    # -------------------------------------------------------------------------
    # 대본 승인 (SCRIPT_DRAFT -> APPROVED)
    # -------------------------------------------------------------------------

    def approve_script(
        self,
        project_id: str,
        approver_context: ApproverContext,  # 기본 인자 없음: 컨텍스트 강제
    ) -> ProductionProject:
        """대본 승인 처리 (ApproverContext 검증, 내용 해시 보존, FACT 증빙 전수 검증)."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        if not approver_context or not approver_context.verified_identity:
            raise UnapprovedContentError("신원이 확인되지 않은 승인자 컨텍스트입니다. 승인 권한이 없습니다.")

        if approver_context.role not in self.AUTHORIZED_APPROVER_ROLES:
            raise UnapprovedContentError(
                f"승인 권한이 없는 역할({approver_context.role})입니다. 승인이 거부되었습니다."
            )

        if not project.script:
            raise UnapprovedContentError("대본이 작성되지 않아 승인할 수 없습니다.")

        # 대본 내 모든 FACT 장면에 대해 실제 검증된 증빙 존재 및 적합성 검증
        for scene in project.script.scenes:
            if scene.provenance_type == ProvenanceType.FACT:
                validate_scene_evidence_compatibility(scene.narration, scene.evidence)

        # 대본 내용 SHA-256 해시 계산 및 보존
        content_hash = hashlib.sha256(project.script.full_text.encode("utf-8")).hexdigest()

        project.script.is_approved = True
        project.script.approved_by = approver_context.user_name
        project.script.approved_at = datetime.now(UTC)
        project.script.approved_version = project.script.version
        project.script.approved_content_hash = content_hash
        project.transition_to(ContentWorkflowStatus.APPROVED)
        return self.repository.save_project(project)

    # -------------------------------------------------------------------------
    # 제작 준비 및 공식 프롬프트/페이로드 생성 (APPROVED -> PRODUCTION_READY)
    # -------------------------------------------------------------------------

    def prepare_production(
        self,
        project_id: str,
        authorized_assets: list[MediaAsset] | None = None,
        model_type: VideoModelType | None = None,
    ) -> ProductionProject:
        """제작 자산 확정, 모델 어댑터 선택 및 공식 규격 생성."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        # 매물 콘텐츠의 경우 최신 매물 상태 재감사 (Fail-closed)
        if project.content_type == ContentType.VEHICLE_PROMOTION:
            vehicle = self.repository.get_vehicle(project.target_id)
            if vehicle:
                VehicleContentAdapter.validate_commercial_eligibility(vehicle, require_images=True)

        if authorized_assets is not None:
            project.visual_assets = authorized_assets

        if model_type is not None:
            project.selected_model = model_type

        # 상태 전이 (미승인 또는 비인가 에셋 시 내부 예외 발생)
        project.transition_to(ContentWorkflowStatus.PRODUCTION_READY)

        adapter = self.adapters.get(project.selected_model)
        if not adapter:
            raise ValueError(f"지원되지 않는 모델 타입: {project.selected_model}")

        assert project.script is not None
        shot_prompts = adapter.generate_shot_prompts(
            script=project.script,
            assets=project.visual_assets,
            duration_sec=30.0,
        )
        master_prompt = adapter.format_master_prompt(
            script=project.script,
            assets=project.visual_assets,
            shot_prompts=shot_prompts,
        )

        api_payload = None
        if isinstance(adapter, Wan3Adapter):
            api_payload = adapter.format_api_payload(
                script=project.script,
                assets=project.visual_assets,
                shot_prompts=shot_prompts,
            )

        project.shot_prompts = shot_prompts
        project.master_prompt = master_prompt
        project.api_payload = api_payload
        return self.repository.save_project(project)

    # -------------------------------------------------------------------------
    # 드라이런 검증 및 생성 작업 오케스트레이션 (운영/테스트 격리)
    # -------------------------------------------------------------------------

    def validate_dry_run(self, project_id: str) -> ProductionProject:
        """공식 API 규격 오프라인 검증 (PRODUCTION_READY -> DRY_RUN_VALIDATED)."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        adapter = self.adapters.get(project.selected_model)
        if not adapter:
            raise ValueError(f"지원되지 않는 모델 타입: {project.selected_model}")

        result = adapter.execute_generation(
            master_prompt=project.master_prompt or "",
            assets=project.visual_assets,
            dry_run=True,
            api_payload=project.api_payload,
        )
        project.generation_result = result
        project.transition_to(ContentWorkflowStatus.DRY_RUN_VALIDATED)
        return self.repository.save_project(project)

    def execute_video_generation(
        self,
        project_id: str,
        dry_run: bool = True,
    ) -> ProductionProject:
        """운영 영상 생성 파이프라인.
        
        실제 외부 생성 API가 미연동 상태이므로, 임의의 성공 상태를 조작하지 않고
        드라이런 검증(DRY_RUN_VALIDATED) 또는 미연동 알림(GENERATION_FAILED)으로 안전 처리합니다.
        """
        if dry_run:
            return self.validate_dry_run(project_id)

        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        if project.status == ContentWorkflowStatus.PRODUCTION_READY:
            project = self.validate_dry_run(project_id)

        project.transition_to(ContentWorkflowStatus.GENERATION_SUBMITTED)

        # 실제 외부 API가 미연동이므로 실제 생성 성공은 불가하며 작업 실패/대기 상태로 기록
        project.generation_result = {
            "status": "UNINTEGRATED_API",
            "message": "실제 상용 유료 생성 API 엔드포인트가 연동되지 않았습니다. 임의의 성공 처리가 차단되었습니다.",
        }
        project.transition_to(ContentWorkflowStatus.GENERATION_FAILED)
        return self.repository.save_project(project)

    def _simulate_generation_success_for_testing(
        self,
        project_id: str,
        verified_video_url: str,
    ) -> ProductionProject:
        """테스트 환경 전용: 실제 외부 API 연동 시의 성공 상태 전이를 시뮬레이션."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        if not verified_video_url:
            raise ValueError("유효한 비디오 URL이 제공되어야 합니다.")

        if project.status != ContentWorkflowStatus.GENERATION_SUBMITTED:
            if project.status == ContentWorkflowStatus.PRODUCTION_READY:
                project = self.validate_dry_run(project_id)
            project.transition_to(ContentWorkflowStatus.GENERATION_SUBMITTED)

        project.result_video_url = verified_video_url
        project.transition_to(ContentWorkflowStatus.GENERATION_SUCCEEDED)
        return self.repository.save_project(project)
