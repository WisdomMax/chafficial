"""CHA-FICIAL AI 콘텐츠 제작 오케스트레이션 파이프라인.

DIRECTIVE 003-A 명세 준수:
- 워크플로 상태 머신 관리 (DISCOVERED -> ... -> MEASURED)
- 미승인 대본 제작 진입 차단 (UnapprovedContentError)
- 비인가 에셋 제작 진입 차단 (UnauthorizedAssetError)
- WAN 3.0 / Kling 4.0 어댑터 통합
- 외부 API 부재 시 정상 처리(Graceful degradation)
"""

from __future__ import annotations

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

    def __init__(self, repository: ContentRepository | None = None) -> None:
        self.repository = repository or ContentRepository()
        self.trend_engine = TrendIntelligenceEngine(self.repository)
        self.expert_engine = ExpertIntelligenceEngine(self.repository)

        # 모델 어댑터 등록
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

        # 제원, 상태, 매물 활성도 및 사진 권한 엄격 검증
        VehicleContentAdapter.validate_commercial_eligibility(vehicle)

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
        approve_review: bool = True,
    ) -> ProductionProject:
        """전문가 답변을 반영하여 대본 초안 작성."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        # 사장님 답변 기록
        review = self.expert_engine.record_expert_answers(
            review_id=review_id,
            answers=expert_answers,
            revision_notes=revision_notes,
            approve=approve_review,
        )

        # 대본 생성
        if project.content_type == ContentType.EXPERT_STORY:
            trend = self.repository.get_trend(project.target_id)
            assert trend is not None
            script = ContentScriptEngine.generate_trend_script(trend, review)
        else:
            vehicle = self.repository.get_vehicle(project.target_id)
            assert vehicle is not None
            script = ContentScriptEngine.generate_vehicle_script(vehicle, review)

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
    ) -> ProductionProject:
        """대본 승인 처리."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        if not project.script:
            raise UnapprovedContentError("대본이 작성되지 않아 승인할 수 없습니다.")

        project.script.is_approved = True
        project.script.approved_by = approver_name
        project.transition_to(ContentWorkflowStatus.APPROVED)
        return self.repository.save_project(project)

    # -------------------------------------------------------------------------
    # 제작 준비 및 프롬프트 생성 (APPROVED -> PRODUCTION_READY)
    # -------------------------------------------------------------------------

    def prepare_production(
        self,
        project_id: str,
        authorized_assets: list[MediaAsset] | None = None,
        model_type: VideoModelType | None = None,
    ) -> ProductionProject:
        """제작 자산 확정, 모델 어댑터 선택 및 컷별 프롬프트 생성."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

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

        project.shot_prompts = shot_prompts
        project.master_prompt = master_prompt
        return self.repository.save_project(project)

    # -------------------------------------------------------------------------
    # 영상 생성 실행 (PRODUCTION_READY -> GENERATED)
    # -------------------------------------------------------------------------

    def execute_video_generation(
        self, project_id: str, dry_run: bool = True
    ) -> ProductionProject:
        """영상 생성 엔진 구동 (외부 API 부재 시에도 dry_run으로 안전 처리)."""
        project = self.repository.get_project(project_id)
        if not project:
            raise ValueError(f"프로젝트 '{project_id}'를 찾을 수 없습니다.")

        adapter = self.adapters.get(project.selected_model)
        if not adapter:
            raise ValueError(f"지원되지 않는 모델 타입: {project.selected_model}")

        result = adapter.execute_generation(
            master_prompt=project.master_prompt or "",
            assets=project.visual_assets,
            dry_run=dry_run,
            api_payload=(
                adapter.format_api_payload(project.script, project.visual_assets, project.shot_prompts)
                if isinstance(adapter, Wan3Adapter) and project.script
                else None
            ),
        )

        project.generation_result = result
        project.transition_to(ContentWorkflowStatus.GENERATED)
        return self.repository.save_project(project)
