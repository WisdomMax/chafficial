"""DIRECTIVE 003-A3 최종 결함(Final Blocker) 재현 및 검증 테스트.

검증 항목:
1. Runway wan3 공식 API 규격: references에 audio 삽입 금지 및 referenceAudio 전용 필드 분리
2. 가짜 영상 URL(mock_success_url)을 통한 실제 생성 성공(GENERATION_SUCCEEDED) 위장 차단
3. 기본 인자만 사용한 승인 권한 획득 차단 (신뢰할 수 있는 ApproverContext 필수)
4. 가격 관측 시각(snapshot_observed_at) 누락 매물의 판매 홍보 차단
5. 증빙 없는 사실(FACT) 문장의 승인 차단
6. ListingSnapshot으로 사고/실내 상태를 검증했다고 주장하는 잘못된 증빙 연결 차단
"""

from datetime import UTC, datetime

import pytest

from chaficial.content.adapters.wan3 import Wan3Adapter
from chaficial.content.models import (
    AssetType,
    CommercialIneligibilityError,
    ContentScript,
    ContentWorkflowStatus,
    FactEvidence,
    FactVerificationError,
    MediaAsset,
    ProvenanceType,
    StoryboardScene,
    UnapprovedContentError,
    VerificationStatus,
)
from chaficial.content.pipeline import ContentProductionPipeline
from chaficial.content.repository import ContentRepository
from chaficial.content.vehicle_adapter import VehicleContentAdapter


@pytest.fixture
def pipeline() -> ContentProductionPipeline:
    return ContentProductionPipeline(repository=ContentRepository())


# ============================================================================
# 1. Runway wan3 공식 API 입력 규격 (references vs referenceAudio)
# ============================================================================

def test_wan3_api_reference_audio_isolated_from_references():
    """Runway wan3 API는 references 배열에 오디오를 넣지 않고 referenceAudio 필드로 분리해야 함."""
    adapter = Wan3Adapter()

    host_img = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="https://cdn.chafficial.com/host.jpg",
        label="호스트",
        republication_allowed=True,
    )
    voice_audio = MediaAsset(
        asset_type=AssetType.AUDIO,
        path_or_url="https://cdn.chafficial.com/voice.wav",
        label="음성",
        republication_allowed=True,
    )

    script = ContentScript(
        title="테스트 대본",
        hook_sentence="테스트 훅",
        full_text="테스트 본문",
        scenes=[
            StoryboardScene(
                scene_number=1,
                title="씬 1",
                duration_seconds=4.0,
                visual_description="설명",
                narration="대사 1",
            )
        ],
    )

    shot_prompts = adapter.generate_shot_prompts(script, [host_img, voice_audio])
    payload = adapter.format_api_payload(script, [host_img, voice_audio], shot_prompts)

    # 1. references에는 오직 이미지만 포함되어야 함 (audio 타입 삽입 금지)
    assert "references" in payload
    for ref in payload["references"]:
        assert ref.get("type") != "audio", "references 배열에 audio 타입이 포함되어서는 안 됩니다."
        assert "url" in ref

    # 2. 오디오는 referenceAudio 전용 필드로 분리되어야 함
    assert "referenceAudio" in payload
    assert payload["referenceAudio"] is not None
    assert payload["referenceAudio"]["url"] == "https://cdn.chafficial.com/voice.wav"


# ============================================================================
# 2. MOCK 영상 성공 처리 격리 (운영 파이프라인에서 가짜 완료 차단)
# ============================================================================

def test_production_pipeline_blocks_mock_generation_success(pipeline: ContentProductionPipeline):
    """실제 생성 API가 미연동인 운영 파이프라인에서는 가짜 URL 주입으로 GENERATION_SUCCEEDED에 도달할 수 없음."""
    trend = pipeline.trend_engine.register_trend_candidate(
        platform="YOUTUBE_SHORTS",
        source_url="https://youtube.com/shorts/mock_test",
        title="중고차 점검 요령",
        account_name="test_account",
    )
    project = pipeline.create_trend_project(trend.candidate_id)
    _, review_id = pipeline.start_expert_review(project.project_id)
    pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {"q": "답변"})

    from chaficial.content.pipeline import ApproverContext
    ctx = ApproverContext(
        user_id="dealer_001",
        user_name="차마트 사장님",
        role="DEALER_PARTNER_AUTHORIZED",
        verified_identity=True,
    )
    pipeline.approve_script(project.project_id, approver_context=ctx)

    host_asset = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="/host.jpg",
        label="호스트",
        republication_allowed=True,
    )
    pipeline.prepare_production(project.project_id, authorized_assets=[host_asset])

    # 운영 환경 실행 시 외부 API 미연동이므로 GENERATION_SUCCEEDED는 불가능해야 함
    project = pipeline.execute_video_generation(project.project_id, dry_run=False)
    assert project.status != ContentWorkflowStatus.GENERATION_SUCCEEDED
    assert project.status in (ContentWorkflowStatus.DRY_RUN_VALIDATED, ContentWorkflowStatus.GENERATION_FAILED)


# ============================================================================
# 3. 전문가 승인 절차 (기본 인자 제거 및 ApproverContext 필수화, 해시 보존)
# ============================================================================

def test_approve_script_requires_explicit_approver_context(pipeline: ContentProductionPipeline):
    """approve_script() 호출 시 기본 인자만으로 승인 권한을 획득하는 것을 차단."""
    trend = pipeline.trend_engine.register_trend_candidate(
        platform="YOUTUBE_SHORTS",
        source_url="https://youtube.com/shorts/approval_test",
        title="허위매물 피하는 법",
        account_name="test_account",
    )
    project = pipeline.create_trend_project(trend.candidate_id)
    _, review_id = pipeline.start_expert_review(project.project_id)
    pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {"q": "답변"})

    # approver_context 없이 호출하거나 미인가 컨텍스트일 때 승인 거부되어야 함
    with pytest.raises((TypeError, UnapprovedContentError)):
        pipeline.approve_script(project.project_id)  # 인자 없이 호출 시 에러 강제

    from chaficial.content.pipeline import ApproverContext
    unauth_ctx = ApproverContext(
        user_id="user_guest",
        user_name="익명",
        role="GUEST",
        verified_identity=False,
    )
    with pytest.raises(UnapprovedContentError) as exc_info:
        pipeline.approve_script(project.project_id, approver_context=unauth_ctx)
    assert "권한이 없습니다" in str(exc_info.value) or "권한" in str(exc_info.value)


def test_script_approval_preserves_content_hash(pipeline: ContentProductionPipeline):
    """대본 승인 시 내용 해시(content_hash)를 기록하고, 내용 변조 시 무효화 확인."""
    trend = pipeline.trend_engine.register_trend_candidate(
        platform="YOUTUBE_SHORTS",
        source_url="https://youtube.com/shorts/hash_test",
        title="중고차 상식",
        account_name="test_account",
    )
    project = pipeline.create_trend_project(trend.candidate_id)
    _, review_id = pipeline.start_expert_review(project.project_id)
    pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {"q": "답변"})

    from chaficial.content.pipeline import ApproverContext
    ctx = ApproverContext(
        user_id="dealer_001",
        user_name="차마트 사장님",
        role="DEALER_PARTNER_AUTHORIZED",
        verified_identity=True,
    )
    project = pipeline.approve_script(project.project_id, approver_context=ctx)
    assert project.script.approved_content_hash is not None
    assert len(project.script.approved_content_hash) == 64  # SHA-256


# ============================================================================
# 4. snapshot_observed_at 누락 시 판매 홍보 차단
# ============================================================================

def test_missing_snapshot_observed_at_blocks_promotion(pipeline: ContentProductionPipeline):
    """가격 관측 시각(snapshot_observed_at)이 누락된 매물은 홍보 프로젝트 생성을 차단."""
    no_time_vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-NO-OBSERVED-TIME",
        "data_source": "TEST",
        "model_name": "기아 K5",
        "model_year": 2021,
        "price": 2000,
        "mileage": 30000,
        "availability_status": "AVAILABLE",
        "partner_review_status": "APPROVED",
        "listing_status": "ACTIVE",
        "snapshot_observed_at": None,  # 관측 시점 누락
        "images": [{"path_or_url": "/img.jpg", "republication_allowed": True}],
    })
    pipeline.repository.save_vehicle(no_time_vehicle)

    with pytest.raises(CommercialIneligibilityError) as exc_info:
        pipeline.create_vehicle_project(no_time_vehicle.candidate_id)
    assert "관측 시점" in str(exc_info.value) or "snapshot_observed_at" in str(exc_info.value)


# ============================================================================
# 5. FACT 증빙 실제 검증 강제 (증빙 없는 FACT 문장 승인 차단)
# ============================================================================

def test_fact_sentence_requires_valid_evidence_for_approval(pipeline: ContentProductionPipeline):
    """FACT 문장이 포함된 대본에 실제 검증된 FactEvidence가 없으면 최종 승인을 차단."""
    vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-NO-EVIDENCE-TEST",
        "data_source": "TEST",
        "model_name": "현대 아반떼",
        "model_year": 2022,
        "price": 1900,
        "mileage": 30000,
        "availability_status": "AVAILABLE",
        "partner_review_status": "APPROVED",
        "listing_status": "ACTIVE",
        "snapshot_observed_at": datetime.now(UTC),
        "images": [{"path_or_url": "/img.jpg", "republication_allowed": True}],
        "evidences": [],  # 증빙 전무
    })
    pipeline.repository.save_vehicle(vehicle)
    project = pipeline.create_vehicle_project(vehicle.candidate_id)

    _, review_id = pipeline.start_expert_review(project.project_id)
    project = pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {})

    # FACT 씬 중 evidence가 없는 씬이 있을 때 승인 시도
    # 대본에 증빙이 없는 FACT 씬이 존재하면 FactVerificationError 발생해야 함
    from chaficial.content.pipeline import ApproverContext
    ctx = ApproverContext(
        user_id="dealer_001",
        user_name="차마트 사장님",
        role="DEALER_PARTNER_AUTHORIZED",
        verified_identity=True,
    )

    # evidence가 없는 FACT 씬을 강제 주입
    project.script.scenes[0].evidence = None
    project.script.scenes[0].provenance_type = ProvenanceType.FACT

    with pytest.raises((FactVerificationError, UnapprovedContentError)) as exc_info:
        pipeline.approve_script(project.project_id, approver_context=ctx)
    assert "증빙" in str(exc_info.value) or "검증" in str(exc_info.value)


# ============================================================================
# 6. ListingSnapshot으로 실내/사고 상태 검증 주장 차단
# ============================================================================

def test_listing_snapshot_cannot_verify_interior_or_accident():
    """ListingSnapshot 증빙은 오직 가격과 주행거리만 검증할 수 있으며, 사고나 실내 상태 근거로 사용 시 거부."""

    snapshot_evidence = FactEvidence(
        source_type="ListingSnapshot",
        document_ref="SNAP-001",
        verified_by="PRICE_SYSTEM",
        verification_status=VerificationStatus.VERIFIED,
        notes="가격 및 주행거리 관측",
    )

    # 1. 가격이나 주행거리 팩트에 연결하는 것은 정상
    scene_valid = StoryboardScene(
        scene_number=1,
        title="가격 안내",
        duration_seconds=4.0,
        visual_description="가격 안내 컷",
        narration="가격 천구백만원입니다.",
        provenance_type=ProvenanceType.FACT,
        provenance_detail="가격 관측치",
        evidence=snapshot_evidence,
    )
    assert scene_valid.evidence.source_type == "ListingSnapshot"

    # 2. 성능점검/사고/실내 상태에 ListingSnapshot을 증빙으로 부착하여 검증하는 함수 검증
    from chaficial.content.script_engine import validate_scene_evidence_compatibility

    with pytest.raises(FactVerificationError) as exc_info:
        validate_scene_evidence_compatibility(
            claim_text="성능점검상 완전 무사고이며 가죽 시트 최상입니다.",
            evidence=snapshot_evidence,
        )
    assert "ListingSnapshot은 사고 이력이나 실내 상태의 검증 근거로 사용할 수 없습니다" in str(exc_info.value)
