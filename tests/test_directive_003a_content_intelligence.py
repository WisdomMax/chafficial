"""DIRECTIVE 003-A 필수 검증 시나리오 및 오류 처리 테스트.

검증 항목:
1. 시나리오 A (인기 중고차 소재):
   - 인기 영상 후보 입력 -> AI 질문 생성 -> 사장님 답변 입력 -> 수정 대본 -> WAN 3.0 컷별 프롬프트 출력
2. 시나리오 B (추천 중고차 매물):
   - 기존 차량 데이터 샘플 입력 -> 정보 검증 -> 사진 자산 선택 -> 소개 대본 -> WAN 3.0 컷별 프롬프트 출력
3. 필수 오류 테스트:
   - 동일 영상 중복 등록 (DuplicateTrendCandidateError)
   - 필수 차량 정보 누락 (MissingVehicleInfoError / 상태 MISSING)
   - 권한 없는 이미지의 제작 자산 사용 차단 (UnauthorizedAssetError)
   - 승인되지 않은 콘텐츠의 제작 완료 처리 차단 (UnapprovedContentError)
   - 기존 차량 엔진과의 인터페이스 불일치 (InvalidVehicleInterfaceError)
   - 외부 모델 API 부재 시 비정상 종료 방지 (Graceful Dry-run fallback)
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


# ============================================================================
# 시나리오 A: 인기 중고차 소재 파이프라인 검증
# ============================================================================

def test_scenario_a_trend_content_lifecycle(pipeline: ContentProductionPipeline):
    """시나리오 A: 인기 영상 후보 등록 -> 질문 생성 -> 답변 기록 -> 대본 작성 -> 승인 -> WAN 3.0 프롬프트 출력."""
    # 1. 인기 영상 후보 등록
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
    assert "침수" in trend.topic

    # 2. 프로젝트 생성 및 워크플로 시작 (SELECTED)
    project = pipeline.create_trend_project(trend.candidate_id)
    assert project.status == ContentWorkflowStatus.SELECTED
    assert project.content_type == ContentType.EXPERT_STORY

    # 3. 차마트 사장님(25년 경력) 인터뷰 세션 개시 (EXPERT_REVIEW)
    project, review_id = pipeline.start_expert_review(project.project_id)
    assert project.status == ContentWorkflowStatus.EXPERT_REVIEW
    review = pipeline.repository.get_review(review_id)
    assert len(review.generated_questions) == 3

    # 4. 사장님 구술 답변 입력 및 대본 초안 생성 (SCRIPT_DRAFT)
    dealer_answers = {
        review.generated_questions[0]: "25년 동안 장마 끝나면 안전벨트만 갈아 끼운 얌체 침수차 진짜 많이 봤습니다.",
        review.generated_questions[1]: "안전벨트만 보지 말고 퓨즈박스 안쪽 모래나 시트 밑 프레임 녹을 반드시 만져봐야 합니다.",
        review.generated_questions[2]: "차마트는 침수차 판정 시 100% 전액 환불에 500만원 보상 계약서에 특약 박아드립니다.",
    }
    project = pipeline.draft_script_with_expert_feedback(
        project_id=project.project_id,
        review_id=review_id,
        expert_answers=dealer_answers,
        approve_review=True,
    )
    assert project.status == ContentWorkflowStatus.SCRIPT_DRAFT
    assert project.script is not None
    assert len(project.script.scenes) == 5
    assert "퓨즈박스" in project.script.full_text or "안전벨트" in project.script.full_text

    # 5. 전문가/관리자 최종 승인 (APPROVED)
    project = pipeline.approve_script(project.project_id, approver_name="차마트 사장님")
    assert project.status == ContentWorkflowStatus.APPROVED
    assert project.script.is_approved is True

    # 6. 제작 자산 연결 및 WAN 3.0 프롬프트 생성 (PRODUCTION_READY)
    host_asset = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="/assets/dealer_character_sheet.jpg",
        label="차마트 사장님 3열 마스터 시트",
        is_authorized=True,
        authorization_reference="초상권 및 홍보영상 활용 사전동의서",
        slot_tag="@Image 1",
    )
    audio_asset = MediaAsset(
        asset_type=AssetType.AUDIO,
        path_or_url="/assets/dealer_voice.wav",
        label="차마트 사장님 실제 음성 참조",
        is_authorized=True,
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
    assert "Part-1 [Duration: 30s] [Aspect Ratio: 9:16]" in project.master_prompt
    assert "@Audio 1" in project.master_prompt

    # 7. 영상 생성 시뮬레이션 (GENERATED)
    project = pipeline.execute_video_generation(project.project_id, dry_run=True)
    assert project.status == ContentWorkflowStatus.GENERATED
    assert project.generation_result["is_dry_run"] is True


# ============================================================================
# 시나리오 B: 추천 중고차 매물 파이프라인 검증
# ============================================================================

def test_scenario_b_vehicle_content_lifecycle(pipeline: ContentProductionPipeline):
    """시나리오 B: 추천 매물 데이터 입력 -> 검증 -> 사진 선택 -> 대본 -> WAN 3.0 프롬프트 출력."""
    # 1. 기존 차량 선별 엔진 형식의 샘플 입력
    raw_vehicle_data = {
        "vehicle_id": "CAR-2020-CAYENNE-001",
        "data_source": "OPPORTUNITY_ENGINE_PROD",
        "model_name": "포르쉐 카이엔 쿠페",
        "model_year": 2020,
        "price": 6900,
        "mileage": 102039,
        "options": ["21인치 RS스파이더 휠", "보르도 레드 시트", "스포츠 크로노", "서라운드 뷰"],
        "verified_pros": ["인기 1위 크레용 외장", "보르도 레드 인테리어", "완전 무사고"],
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

    # 2. 어댑터를 통한 변환 및 정합성 검증
    vehicle_candidate = VehicleContentAdapter.from_dict(raw_vehicle_data)
    assert vehicle_candidate.availability_status == "AVAILABLE"
    assert len(vehicle_candidate.images) == 2
    assert vehicle_candidate.images[0].is_authorized is True

    # 저장소에 등록
    pipeline.repository.save_vehicle(vehicle_candidate)

    # 3. 프로젝트 생성 (SELECTED)
    project = pipeline.create_vehicle_project(vehicle_candidate.candidate_id)
    assert project.status == ContentWorkflowStatus.SELECTED
    assert project.content_type == ContentType.VEHICLE_PROMOTION

    # 4. 차마트 사장님 확인 인터뷰 (EXPERT_REVIEW)
    project, review_id = pipeline.start_expert_review(project.project_id)
    review = pipeline.repository.get_review(review_id)
    assert len(review.generated_questions) == 3

    # 사장님 답변 주입 및 매물 대본 생성 (SCRIPT_DRAFT)
    answers = {
        review.generated_questions[0]: "크레용에 보르도 레드 시트 조합이라 들어오자마자 나갈 매물입니다.",
        review.generated_questions[1]: "엔진 미션 짱짱하고 하체 잡소리 일절 없습니다.",
        review.generated_questions[2]: "트렁크 단순교환 하나 있지만 뼈대는 멀쩡한 완전 무사고 차량입니다.",
    }
    project = pipeline.draft_script_with_expert_feedback(
        project_id=project.project_id,
        review_id=review_id,
        expert_answers=answers,
        approve_review=True,
    )
    assert project.status == ContentWorkflowStatus.SCRIPT_DRAFT
    assert "육천구백만원" in project.script.full_text or "6,900만원" in project.script.full_text

    # 5. 승인 처리 (APPROVED)
    project = pipeline.approve_script(project.project_id)
    assert project.status == ContentWorkflowStatus.APPROVED

    # 6. 제작 준비 및 WAN 3.0 프롬프트 생성 (PRODUCTION_READY)
    host_asset = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="/assets/dealer_character_sheet.jpg",
        label="차마트 사장님 3열 마스터 시트",
        is_authorized=True,
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
    assert "@Image 1" in project.master_prompt
    assert "@Image 2" in project.master_prompt

    # 7. 영상 생성 시뮬레이션
    project = pipeline.execute_video_generation(project.project_id, dry_run=True)
    assert project.status == ContentWorkflowStatus.GENERATED


# ============================================================================
# 오류 처리 필수 테스트 6종
# ============================================================================

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
    metrics = pipeline.trend_engine.get_discovery_metrics()
    assert metrics["duplicate_count"] == 1


def test_error_2_missing_essential_vehicle_info(pipeline: ContentProductionPipeline):
    """오류 2: 필수 차량 정보(가격, 연식 등) 누락 시 MISSING 상태 전이 및 제작 차단."""
    bad_data = {
        "vehicle_id": "CAR-MISSING-001",
        "data_source": "MANUAL_TEST",
        "model_name": "기아 쏘렌토",
        # model_year, price, mileage 누락
    }
    candidate = VehicleContentAdapter.from_dict(bad_data)
    assert candidate.availability_status == "MISSING"
    assert any("미확인 항목" in p for p in candidate.precautions)

    pipeline.repository.save_vehicle(candidate)

    # 제작 프로젝트 생성 시도 시 MissingVehicleInfoError 발생
    with pytest.raises(MissingVehicleInfoError):
        pipeline.create_vehicle_project(candidate.candidate_id)


def test_error_3_unauthorized_asset_blocked(pipeline: ContentProductionPipeline):
    """오류 3: 권한 없는 이미지(is_authorized=False)의 제작 자산 사용 시 차단."""
    # 유효한 차량 데이터
    vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-AUTH-TEST",
        "data_source": "TEST",
        "model_name": "현대 아반떼",
        "model_year": 2022,
        "price": 1800,
        "mileage": 30000,
    })
    pipeline.repository.save_vehicle(vehicle)
    project = pipeline.create_vehicle_project(vehicle.candidate_id)

    # 검토 및 대본 승인까지 진행
    _, review_id = pipeline.start_expert_review(project.project_id)
    pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {"q1": "a1"})
    pipeline.approve_script(project.project_id)

    # 권한 없는 불법 스크랩 사진 주입 시도
    illegal_asset = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="/scraped/unauthorized_photo.jpg",
        label="인터넷 불펌 차량 사진",
        is_authorized=False,
        authorization_reference="",
    )

    with pytest.raises(UnauthorizedAssetError) as exc_info:
        pipeline.prepare_production(
            project_id=project.project_id,
            authorized_assets=[illegal_asset],
        )
    assert "사용 권한이 없습니다" in str(exc_info.value)


def test_error_4_unapproved_content_blocked(pipeline: ContentProductionPipeline):
    """오류 4: 전문가/관리자 최종 승인 없이 제작 완료(PRODUCTION_READY / GENERATED) 처리 차단."""
    vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-UNAPPROVED-TEST",
        "data_source": "TEST",
        "model_name": "제네시스 G80",
        "model_year": 2021,
        "price": 4500,
        "mileage": 50000,
    })
    pipeline.repository.save_vehicle(vehicle)
    project = pipeline.create_vehicle_project(vehicle.candidate_id)

    # 대본 초안만 작성하고 승인(approve_script)은 거치지 않음
    _, review_id = pipeline.start_expert_review(project.project_id)
    pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {"q": "a"})

    assert project.status == ContentWorkflowStatus.SCRIPT_DRAFT

    # 승인 없이 PRODUCTION_READY 진입 시도 -> UnapprovedContentError
    with pytest.raises(UnapprovedContentError) as exc_info:
        pipeline.prepare_production(project.project_id)
    assert "승인되지 않은 대본" in str(exc_info.value)


def test_error_5_invalid_vehicle_interface_mismatch():
    """오류 5: 기존 차량 엔진과의 인터페이스 불일치 시 InvalidVehicleInterfaceError 발생."""
    # 딕셔너리가 아닌 잘못된 타입
    with pytest.raises(InvalidVehicleInterfaceError):
        VehicleContentAdapter.from_dict(["잘못된", "리스트", "입력"])

    # 필수 키 vehicle_id 누락
    with pytest.raises(InvalidVehicleInterfaceError) as exc_info:
        VehicleContentAdapter.from_dict({"data_source": "TEST"})
    assert "vehicle_id" in str(exc_info.value)


def test_error_6_external_api_absence_graceful_handling(pipeline: ContentProductionPipeline):
    """오류 6: 외부 비디오 생성 API 미제공 환경에서도 충돌 없이 오프라인 프롬프트 명세 생성 및 안전 처리."""
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

    # Kling 4.0 어댑터로 전환
    project = pipeline.prepare_production(project.project_id, model_type=VideoModelType.KLING_4_0)
    assert project.selected_model == VideoModelType.KLING_4_0
    assert "KLING 4.0 CINEMATIC" in project.master_prompt

    # 외부 API가 없는 상태에서 execute_video_generation 호출 시 예외 없이 MOCK_SUCCESS 또는 READY_FOR_SUBMISSION 반환
    project = pipeline.execute_video_generation(project.project_id, dry_run=False)
    assert project.status == ContentWorkflowStatus.GENERATED
    assert project.generation_result["status"] == "MOCK_SUCCESS"
    assert project.generation_result["model"] == "KLING_4_0"
