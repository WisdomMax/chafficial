"""DIRECTIVE 003-A 초기 시나리오 검증 테스트 (003-A2 규격 반영 업데이트).

- Fail-Closed 정책 반영 (partner_review_status, listing_status, republication_allowed)
- WAN 3.0 공식 규격(wan3, DRY_RUN_VALIDATED) 반영
"""

from datetime import UTC, datetime

import pytest

from chaficial.content.models import (
    AssetType,
    ContentType,
    ContentWorkflowStatus,
    DuplicateTrendCandidateError,
    InvalidVehicleInterfaceError,
    MediaAsset,
    MissingVehicleInfoError,
    UnapprovedContentError,
    UnauthorizedAssetError,
    VideoModelType,
)
from chaficial.content.pipeline import ContentProductionPipeline
from chaficial.content.repository import ContentRepository
from chaficial.content.vehicle_adapter import VehicleContentAdapter


@pytest.fixture
def pipeline() -> ContentProductionPipeline:
    repo = ContentRepository()
    return ContentProductionPipeline(repository=repo)


def test_scenario_a_trend_content_lifecycle(pipeline: ContentProductionPipeline):
    """시나리오 A: 인기 영상 후보 등록 -> 질문 생성 -> 답변 기록 -> 대본 작성 -> 승인 -> WAN 3.0 프롬프트 출력."""
    trend = pipeline.trend_engine.register_trend_candidate(
        platform="YOUTUBE_SHORTS",
        source_url="https://youtube.com/shorts/test_flood_car_123",
        title="장마철 침수차 1분 만에 구별하는 딜러 꿀팁",
        account_name="중고차탐구생활",
        view_count=150_000,
        like_count=5_400,
        comment_count=420,
        uploaded_at=datetime.now(UTC),
        search_keyword="침수차 구별법",
        raw_description="침수차 절대 속지 마세요. 안전벨트 끝까지 당겨보는 비밀",
    )
    assert trend.candidate_id is not None
    assert trend.popularity_score > 0

    project = pipeline.create_trend_project(trend.candidate_id)
    assert project.status == ContentWorkflowStatus.SELECTED
    assert project.content_type == ContentType.EXPERT_STORY

    project, review_id = pipeline.start_expert_review(project.project_id)
    assert project.status == ContentWorkflowStatus.EXPERT_REVIEW
    review = pipeline.repository.get_review(review_id)
    assert len(review.generated_questions) == 3

    dealer_answers = {
        review.generated_questions[0]: "안전벨트만 보지 말고 퓨즈박스 안쪽 모래나 시트 밑 프레임 녹을 반드시 만져봐야 합니다.",
    }
    project = pipeline.draft_script_with_expert_feedback(
        project_id=project.project_id,
        review_id=review_id,
        expert_answers=dealer_answers,
        approve_review=True,
    )
    assert project.status == ContentWorkflowStatus.SCRIPT_DRAFT
    assert project.script is not None

    project = pipeline.approve_script(project.project_id, approver_name="차마트 사장님")
    assert project.status == ContentWorkflowStatus.APPROVED
    assert project.script.is_approved is True

    host_asset = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="/assets/dealer_character_sheet.jpg",
        label="차마트 사장님 3열 마스터 시트",
        republication_allowed=True,
        authorization_reference="초상권 및 홍보영상 활용 사전동의서",
        slot_tag="@Image 1",
    )
    audio_asset = MediaAsset(
        asset_type=AssetType.AUDIO,
        path_or_url="/assets/dealer_voice.wav",
        label="차마트 사장님 실제 음성 참조",
        republication_allowed=True,
        authorization_reference="음성 복제 및 합성 동의서",
        slot_tag="@Audio 1",
    )

    project = pipeline.prepare_production(
        project_id=project.project_id,
        authorized_assets=[host_asset, audio_asset],
        model_type=VideoModelType.WAN_3_0,
    )
    assert project.status == ContentWorkflowStatus.PRODUCTION_READY
    assert len(project.shot_prompts) == 5
    assert project.master_prompt is not None

    # 드라이런 검증 시 DRY_RUN_VALIDATED 상태 확인
    project = pipeline.execute_video_generation(project.project_id, dry_run=True)
    assert project.status == ContentWorkflowStatus.DRY_RUN_VALIDATED
    assert project.generation_result["is_dry_run"] is True


def test_scenario_b_vehicle_content_lifecycle(pipeline: ContentProductionPipeline):
    """시나리오 B: 추천 매물 데이터 입력 -> 검증 -> 사진 선택 -> 대본 -> WAN 3.0 프롬프트 출력."""
    raw_vehicle_data = {
        "vehicle_id": "CAR-2020-CAYENNE-001",
        "data_source": "OPPORTUNITY_ENGINE_PROD",
        "model_name": "포르쉐 카이엔 쿠페",
        "model_year": 2020,
        "price": 6900,
        "mileage": 102039,
        "availability_status": "AVAILABLE",
        "partner_review_status": "APPROVED",
        "listing_status": "ACTIVE",
        "options": ["21인치 RS스파이더 휠", "보르도 레드 시트", "스포츠 크로노", "서라운드 뷰"],
        "verified_pros": ["인기 1위 크레용 외장", "보르도 레드 인테리어"],
        "precautions": ["트렁크 리드 단순교환 1건 있음 (골격 무사고)"],
        "images": [
            {
                "path_or_url": "/assets/cayenne_front.jpg",
                "label": "카이엔 쿠페 전면 정면 번호판",
                "republication_allowed": True,
                "authorization_reference": "차마트 소유 매물 직접 촬영",
            },
            {
                "path_or_url": "/assets/cayenne_interior.jpg",
                "label": "1열 보르도 레드 인테리어",
                "republication_allowed": True,
                "authorization_reference": "차마트 소유 매물 직접 촬영",
            },
        ],
    }

    vehicle_candidate = VehicleContentAdapter.from_dict(raw_vehicle_data)
    assert vehicle_candidate.availability_status == "AVAILABLE"
    assert len(vehicle_candidate.images) == 2
    assert vehicle_candidate.images[0].republication_allowed is True

    pipeline.repository.save_vehicle(vehicle_candidate)
    project = pipeline.create_vehicle_project(vehicle_candidate.candidate_id)
    assert project.status == ContentWorkflowStatus.SELECTED

    project, review_id = pipeline.start_expert_review(project.project_id)
    review = pipeline.repository.get_review(review_id)

    answers = {
        review.generated_questions[0]: "크레용에 보르도 레드 시트 조합이라 들어오자마자 나갈 매물입니다.",
    }
    project = pipeline.draft_script_with_expert_feedback(
        project_id=project.project_id,
        review_id=review_id,
        expert_answers=answers,
        approve_review=True,
    )
    assert project.status == ContentWorkflowStatus.SCRIPT_DRAFT

    project = pipeline.approve_script(project.project_id)
    assert project.status == ContentWorkflowStatus.APPROVED

    host_asset = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="/assets/dealer_character_sheet.jpg",
        label="차마트 사장님 3열 마스터 시트",
        republication_allowed=True,
        authorization_reference="초상권 활용 승낙서",
        slot_tag="@Image 1",
    )
    combined_assets = [host_asset] + vehicle_candidate.images

    project = pipeline.prepare_production(
        project_id=project.project_id,
        authorized_assets=combined_assets,
        model_type=VideoModelType.WAN_3_0,
    )
    assert project.status == ContentWorkflowStatus.PRODUCTION_READY
    assert len(project.shot_prompts) == 5

    project = pipeline.execute_video_generation(project.project_id, dry_run=True)
    assert project.status == ContentWorkflowStatus.DRY_RUN_VALIDATED


def test_error_1_duplicate_trend_candidate(pipeline: ContentProductionPipeline):
    """오류 1: 동일 영상 중복 등록 시 DuplicateTrendCandidateError 발생."""
    url = "https://youtube.com/shorts/dup_test_video"
    pipeline.trend_engine.register_trend_candidate(
        platform="YOUTUBE_SHORTS",
        source_url=url,
        title="중복 테스트 영상",
        account_name="test_acc",
    )

    with pytest.raises(DuplicateTrendCandidateError) as exc_info:
        pipeline.trend_engine.register_trend_candidate(
            platform="YOUTUBE_SHORTS",
            source_url=url,
            title="중복 테스트 영상 재등록",
            account_name="test_acc",
        )
    assert "이미 등록된 영상 콘텐츠" in str(exc_info.value)


def test_error_2_missing_essential_vehicle_info(pipeline: ContentProductionPipeline):
    """오류 2: 필수 차량 정보 누락 시 MISSING 상태 전이 및 제작 차단."""
    bad_data = {
        "vehicle_id": "CAR-MISSING-001",
        "data_source": "MANUAL_TEST",
        "model_name": "기아 쏘렌토",
    }
    candidate = VehicleContentAdapter.from_dict(bad_data)
    assert candidate.availability_status == "MISSING"

    pipeline.repository.save_vehicle(candidate)

    with pytest.raises(MissingVehicleInfoError):
        pipeline.create_vehicle_project(candidate.candidate_id)


def test_error_3_unauthorized_asset_blocked(pipeline: ContentProductionPipeline):
    """오류 3: 권한 없는 이미지(republication_allowed=False)의 제작 자산 사용 시 차단."""
    vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-AUTH-TEST",
        "data_source": "TEST",
        "model_name": "현대 아반떼",
        "model_year": 2022,
        "price": 1800,
        "mileage": 30000,
        "availability_status": "AVAILABLE",
        "partner_review_status": "APPROVED",
        "listing_status": "ACTIVE",
        "images": [{"path_or_url": "/valid.jpg", "republication_allowed": True}],
    })
    pipeline.repository.save_vehicle(vehicle)
    project = pipeline.create_vehicle_project(vehicle.candidate_id)

    _, review_id = pipeline.start_expert_review(project.project_id)
    pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {"q1": "a1"})
    pipeline.approve_script(project.project_id)

    illegal_asset = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="/scraped/unauthorized_photo.jpg",
        label="인터넷 불펌 차량 사진",
        republication_allowed=False,  # 비인가
    )

    with pytest.raises(UnauthorizedAssetError) as exc_info:
        pipeline.prepare_production(
            project_id=project.project_id,
            authorized_assets=[illegal_asset],
        )
    assert "재배포 권한" in str(exc_info.value)


def test_error_4_unapproved_content_blocked(pipeline: ContentProductionPipeline):
    """오류 4: 전문가/관리자 최종 승인 없이 제작 완료 처리 차단."""
    vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-UNAPPROVED-TEST",
        "data_source": "TEST",
        "model_name": "제네시스 G80",
        "model_year": 2021,
        "price": 4500,
        "mileage": 50000,
        "availability_status": "AVAILABLE",
        "partner_review_status": "APPROVED",
        "listing_status": "ACTIVE",
        "images": [{"path_or_url": "/valid.jpg", "republication_allowed": True}],
    })
    pipeline.repository.save_vehicle(vehicle)
    project = pipeline.create_vehicle_project(vehicle.candidate_id)

    _, review_id = pipeline.start_expert_review(project.project_id)
    pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {"q": "a"})

    assert project.status == ContentWorkflowStatus.SCRIPT_DRAFT

    with pytest.raises(UnapprovedContentError) as exc_info:
        pipeline.prepare_production(project.project_id)
    assert "승인되지 않은 대본" in str(exc_info.value)


def test_error_5_invalid_vehicle_interface_mismatch():
    """오류 5: 기존 차량 엔진과의 인터페이스 불일치 시 InvalidVehicleInterfaceError 발생."""
    with pytest.raises(InvalidVehicleInterfaceError):
        VehicleContentAdapter.from_dict(["잘못된", "리스트", "입력"])

    with pytest.raises(InvalidVehicleInterfaceError) as exc_info:
        VehicleContentAdapter.from_dict({"data_source": "TEST"})
    assert "vehicle_id" in str(exc_info.value)


def test_error_6_external_api_absence_graceful_handling(pipeline: ContentProductionPipeline):
    """오류 6: 외부 API 부재 시 드라이런 검증(DRY_RUN_VALIDATED)으로 안전 처리."""
    trend = pipeline.trend_engine.register_trend_candidate(
        platform="TIKTOK",
        source_url="https://tiktok.com/@car/video/99999",
        title="중고차 꿀팁 쇼츠",
        account_name="tiktok_dealer",
    )
    project = pipeline.create_trend_project(trend.candidate_id)
    _, review_id = pipeline.start_expert_review(project.project_id)
    pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {"q": "a"})
    pipeline.approve_script(project.project_id)

    host_asset = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="/host.jpg",
        label="호스트",
        republication_allowed=True,
    )
    project = pipeline.prepare_production(
        project.project_id,
        authorized_assets=[host_asset],
        model_type=VideoModelType.KLING_4_0,
    )
    assert project.selected_model == VideoModelType.KLING_4_0

    # 드라이런 실행 시 안전하게 DRY_RUN_VALIDATED 반환
    project = pipeline.execute_video_generation(project.project_id, dry_run=True)
    assert project.status == ContentWorkflowStatus.DRY_RUN_VALIDATED
