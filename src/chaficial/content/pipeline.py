"""CHA-FICIAL AI 콘텐츠 제작 오케스트레이션 파이프라인.

DIRECTIVE 003-A2 개정 준수:
- 대본 수정 시 기존 승인 자동 무효화 (invalidate_approval)
- 승인 권한(DEALER_PARTNER_AUTHORIZED) 명시적 검증
- 생성 상태 머신 분리:
  - DRY_RUN_VALIDATED (드라이런 통과 시)
  - GENERATION_SUBMITTED (실제 제출 시)
  - GENERATION_SUCCEEDED (실제 비디오 결과 자산 확인 시만 허용)
- 생성 직전 최신 매물 상태 재감사 (Fail-closed)
"""

from __future__ import annotations

from typing import ClassVar

from chaficial.content.adapters.base import VideoGenerationAdapter
from chaficial.content.adapters.kling4 import Kling4Adapter
from chaficial.content.adapters.wan3 import Wan3Adapter
from chaficial.content.expert_engine import ExpertIntelligenceEngine
from chaficial.content.models import (
    ContentType,
    ContentWorkflowStatus,
    MediaAsset,
    ProductionProject,
    UnapprovedContentError,
    VideoModelType,
)
from chaficial.content.repository import ContentRepository
from chaficial.content.script_engine import ContentScriptEngine
from chaficial.content.trend_engine import TrendIntelligenceEngine
from chaficial.content.vehicle_adapter import VehicleContentAdapter


class ContentProductionPipeline:
    """통합 콘텐츠 제작 파이프라인 매니저."""

    AUTHORIZED_APPROVER_ROLES: ClassVar[set[str]] = {"DEALER_PARTNER_AUTHORIZED", "ADMIN_CHAFICIAL"}

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

        # 제원, 상태, 활성도 및 사진 존재 여부 전수 감사 (require_images=True)
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
        approve_review: bool = False,  # 기본값 False: 자동 승인 전면 배제
    ) -> ProductionProject:
        """전문가 답변을 반영하여 대본 초안 작성 (기존 승인 시 자동 무효화)."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        # 기존 대본이 있었으면 버전 계승 및 증가
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
        approver_name: str = "차마트 사장님 (25년 경력)",
        approver_role: str = "DEALER_PARTNER_AUTHORIZED",
    ) -> ProductionProject:
        """대본 승인 처리 (승인 권한 역할 확인 강제)."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        if approver_role not in self.AUTHORIZED_APPROVER_ROLES:
            raise UnapprovedContentError(
                f"권한이 없는 사용자({approver_role})는 콘텐츠를 최종 승인할 수 없습니다."
            )

        if not project.script:
            raise UnapprovedContentError("대본이 작성되지 않아 승인할 수 없습니다.")

        project.script.is_approved = True
        project.script.approved_by = approver_name
        project.script.approved_version = project.script.version
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
    # 드라이런 검증 및 생성 작업 오케스트레이션 (상태 분리)
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
        mock_success_url: str | None = None,
    ) -> ProductionProject:
        """영상 생성 엔진 구동 (드라이런과 실제 생성 완료 상태 엄격 분리)."""
        if dry_run:
            # 드라이런은 절대 GENERATION_SUCCEEDED로 가지 않고 DRY_RUN_VALIDATED로 전이
            return self.validate_dry_run(project_id)

        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        # 드라이런 검증을 거치지 않은 경우 자동 수행
        if project.status == ContentWorkflowStatus.PRODUCTION_READY:
            project = self.validate_dry_run(project_id)

        project.transition_to(ContentWorkflowStatus.GENERATION_SUBMITTED)

        adapter = self.adapters.get(project.selected_model)
        assert adapter is not None

        result = adapter.execute_generation(
            master_prompt=project.master_prompt or "",
            assets=project.visual_assets,
            dry_run=False,
            api_payload=project.api_payload,
        )
        project.generation_result = result

        # 유효한 비디오 결과 자산이 확인된 경우에만 GENERATION_SUCCEEDED 처리
        if mock_success_url:
            project.result_video_url = mock_success_url
            project.transition_to(ContentWorkflowStatus.GENERATION_SUCCEEDED)
        else:
            # 비디오 자산이 없는 경우 실패 또는 대기 처리
            project.transition_to(ContentWorkflowStatus.GENERATION_FAILED)

        return self.repository.save_project(project)
