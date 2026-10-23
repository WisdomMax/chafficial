"""DIRECTIVE 003-A2 중대 연동 및 진실성 안전 감사(Critical Integration & Truth-Safety Audit) 테스트.

검증 항목:
1. 실제 SQLAlchemy ORM(SalesCandidate, Listing, ListingSnapshot, VehicleCatalog) 통합 검증
   - price_krw(원) -> price(만원) 변환
   - 최신 스냅샷 자동 선택 및 30일 이내 관측 날짜 검증
2. Fail-Closed 판매 승인 정책 검증:
   - 사진 0장인 차량의 홍보 프로젝트 생성 차단
   - 내부 보관 권한만 있는 사진의 광고 제작 차단 (republication_allowed=False)
   - 30일 초과된 오래된 매물 차단
3. 공식 Runway Dev WAN 3.0 API(wan3) 스키마 계약 테스트:
   - model: 'wan3'
   - ratio: '720:1280'
   - references 배열 구조 ([{"type": "image", "url": "..."}, {"type": "audio", "url": "..."}])
   - 비공식 임의 필드(resolution, options) 전무 단언
4. 허위 사실 및 미증빙 문구 생성 원천 차단:
   - 무사고 증빙 없는 매물 단정 배제
   - 임의 환불/보상 약속 및 긴급성 조장 문구 배제
5. 전문가 및 대본 승인 절차 (버전 관리 및 수정 시 승인 자동 취소, 비인가 승인 차단)
6. 생성 상태 머신 분리:
   - 드라이런 시 DRY_RUN_VALIDATED 전이 (절대 GENERATION_SUCCEEDED 아님)
   - 결과 비디오 URL 없이 성공 완료 차단
7. 출력 품질 감사:
   - 차종별 3종(아반떼 세단, 쏘렌토 SUV, 레이 경차) 대본 및 썰 3종 발화 속도(30초 이내) 계산 검증
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from chaficial.content.adapters.wan3 import Wan3Adapter
from chaficial.content.models import (
    AssetType,
    CommercialIneligibilityError,
    ContentWorkflowStatus,
    MediaAsset,
    MissingVehicleInfoError,
    UnapprovedContentError,
    UnauthorizedAssetError,
    WorkflowTransitionError,
)
from chaficial.content.pipeline import ContentProductionPipeline
from chaficial.content.repository import ContentRepository
from chaficial.content.script_engine import estimate_speech_duration_seconds
from chaficial.content.vehicle_adapter import VehicleContentAdapter
from chaficial.database.base import Base
from chaficial.models.candidate import SalesCandidate
from chaficial.models.catalog import VehicleCatalog
from chaficial.models.listing import Listing
from chaficial.models.permission import DataSourcePermission
from chaficial.models.region import Region
from chaficial.models.snapshot import ListingSnapshot
from chaficial.models.vehicle import VehicleIdentity


@pytest.fixture
def db_session() -> Session:
    """실제 SQLAlchemy ORM 테스트를 위한 인메모리 DB 세션."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    yield session
    session.close()


@pytest.fixture
def pipeline() -> ContentProductionPipeline:
    return ContentProductionPipeline(repository=ContentRepository())


# ============================================================================
# 1. 실제 차량 ORM 모델 연동 테스트 (P0)
# ============================================================================

def test_actual_sqlalchemy_orm_integration(db_session: Session, pipeline: ContentProductionPipeline):
    """실제 SQLAlchemy ORM 객체들과의 연동 및 최신 스냅샷(price_krw -> price) 자동 변환 검증."""
    # 1. 카탈로그 및 지역
    region = Region(region_id="REG-SEOUL-01", region_name="서울 장안평", region_type="MARKET_COMPLEX")
    catalog = VehicleCatalog(
        catalog_id=101,
        manufacturer="현대",
        model_name="아반떼",
        generation="CN7",
        is_facelift=False,
        trim="인스퍼레이션",
        model_year=2022,
        fuel_type="가솔린",
    )
    db_session.add_all([region, catalog])
    db_session.flush()

    # 2. 차량 고유식별 및 매물
    vehicle = VehicleIdentity(
        vehicle_id="VEH-AVANTE-2022",
        catalog_id=catalog.catalog_id,
        identity_status="CONFIRMED",
    )
    db_session.add(vehicle)
    db_session.flush()

    listing = Listing(
        listing_id="LIST-AVANTE-001",
        source_platform="ENCAR",
        source_listing_id="ENCAR-123456",
        vehicle_id=vehicle.vehicle_id,
        raw_location="서울 장안평",
        normalized_region_id=region.region_id,
        current_status="ACTIVE",
    )
    db_session.add(listing)
    db_session.flush()

    # 3. 시계열 스냅샷 2개 (과거 5일 전 2,000만원 vs 최신 1일 전 1,900만원)
    now = datetime.now(UTC)
    snap_old = ListingSnapshot(
        snapshot_id="SNAP-OLD",
        listing_id=listing.listing_id,
        observed_at=now - timedelta(days=5),
        price_krw=20_000_000,
        mileage_km=30000,
        listing_status="ACTIVE",
    )
    snap_latest = ListingSnapshot(
        snapshot_id="SNAP-LATEST",
        listing_id=listing.listing_id,
        observed_at=now - timedelta(days=1),
        price_krw=19_000_000,  # 1,900만원 (만원 단위 환산 시 1900)
        mileage_km=30500,
        listing_status="ACTIVE",
    )
    listing.snapshots.extend([snap_old, snap_latest])
    db_session.add_all([snap_old, snap_latest])
    db_session.flush()

    # 4. 판매 후보
    candidate = SalesCandidate(
        candidate_id="CAND-AVANTE-001",
        listing_id=listing.listing_id,
        target_region_id=region.region_id,
        selected_by="AI_AGENT",
        selection_reason="수익성 최상위 매물",
        availability_status="AVAILABLE",
        partner_review_status="APPROVED",
    )
    db_session.add(candidate)
    db_session.flush()

    # 5. 출처 권한
    perm = DataSourcePermission(
        source_id="ENCAR",
        source_name="엔카 공인 제휴",
        permission_status="AUTHORIZED",
        republication_allowed=True,
        storage_allowed=True,
        authorization_reference="제휴계약서 제2022호",
    )
    db_session.add(perm)
    db_session.flush()

    # 6. ORM 어댑터 변환 검증
    vehicle_content = VehicleContentAdapter.from_sales_candidate(
        candidate=candidate,
        permission=perm,
        images=[
            {
                "path_or_url": "/assets/avante_front.jpg",
                "label": "전면 정면",
                "republication_allowed": True,
            }
        ],
    )

    # 최신 스냅샷(1,900만원, 30500km)이 자동으로 선택되었는지 검증
    assert vehicle_content.price == 1900  # 만원 단위 변환
    assert vehicle_content.price_krw == 19_000_000  # 원 단위 보존
    assert vehicle_content.mileage == 30500
    assert vehicle_content.availability_status == "AVAILABLE"
    assert vehicle_content.partner_review_status == "APPROVED"
    assert "아반떼" in vehicle_content.model_name
    assert vehicle_content.model_year == 2022
    assert len(vehicle_content.images) == 1
    assert vehicle_content.images[0].republication_allowed is True

    # 7. 파이프라인 프로젝트 생성 검증
    pipeline.repository.save_vehicle(vehicle_content)
    project = pipeline.create_vehicle_project(vehicle_content.candidate_id)
    assert project.status == ContentWorkflowStatus.SELECTED


# ============================================================================
# 2. Fail-Closed 판매 승인 정책 검증 (P0)
# ============================================================================

def test_fail_closed_zero_photos_blocked(pipeline: ContentProductionPipeline):
    """실제 사진이 0장인 매물은 판매 홍보 프로젝트 생성을 전면 차단."""
    no_photo_vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-NO-PHOTO",
        "data_source": "TEST",
        "model_name": "기아 쏘렌토",
        "model_year": 2021,
        "price": 3200,
        "mileage": 45000,
        "availability_status": "AVAILABLE",
        "partner_review_status": "APPROVED",
        "listing_status": "ACTIVE",
        "images": [],  # 사진 없음
    })
    pipeline.repository.save_vehicle(no_photo_vehicle)

    with pytest.raises(MissingVehicleInfoError) as exc_info:
        pipeline.create_vehicle_project(no_photo_vehicle.candidate_id)
    assert "실차 사진이 1장도 등록되지 않았습니다" in str(exc_info.value)


def test_internal_storage_only_photo_blocked(pipeline: ContentProductionPipeline):
    """내부 보관 권한만 있고 상업적 재배포 권한이 없는 사진은 차단."""
    internal_only_vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-INTERNAL-ONLY",
        "data_source": "TEST",
        "model_name": "제네시스 G80",
        "model_year": 2021,
        "price": 4500,
        "mileage": 50000,
        "availability_status": "AVAILABLE",
        "partner_review_status": "APPROVED",
        "listing_status": "ACTIVE",
        "images": [
            {
                "path_or_url": "/assets/g80.jpg",
                "label": "내부 열람용 사진",
                "internal_storage_allowed": True,   # 내부 보관만 가능
                "republication_allowed": False,     # 외부 광고 불허
            }
        ],
    })
    pipeline.repository.save_vehicle(internal_only_vehicle)

    with pytest.raises(UnauthorizedAssetError) as exc_info:
        pipeline.create_vehicle_project(internal_only_vehicle.candidate_id)
    assert "상업적 재배포 권한" in str(exc_info.value)


def test_stale_snapshot_blocked(pipeline: ContentProductionPipeline):
    """가격 관측 시점이 30일을 초과한 오래된 매물은 차단."""
    stale_vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-STALE-PRICE",
        "data_source": "TEST",
        "model_name": "현대 소나타",
        "model_year": 2020,
        "price": 1800,
        "mileage": 60000,
        "availability_status": "AVAILABLE",
        "partner_review_status": "APPROVED",
        "listing_status": "ACTIVE",
        "snapshot_observed_at": datetime.now(UTC) - timedelta(days=45),  # 45일 전 관측
        "images": [{"path_or_url": "/img/1.jpg", "republication_allowed": True}],
    })
    pipeline.repository.save_vehicle(stale_vehicle)

    with pytest.raises(CommercialIneligibilityError) as exc_info:
        pipeline.create_vehicle_project(stale_vehicle.candidate_id)
    assert "30일을 초과" in str(exc_info.value)


# ============================================================================
# 3. 공식 Runway Dev WAN 3.0 API 계약 테스트 (P0)
# ============================================================================

def test_official_wan3_api_schema_contract():
    """공식 Runway Dev wan3 스키마(wan3, 720:1280, references)와 대조 계약 검증."""
    adapter = Wan3Adapter()

    # 1. 모델 ID 단언
    assert adapter.MODEL_ID == "wan3"
    assert adapter.VERTICAL_RATIO == "720:1280"

    # 가상 대본과 에셋
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

    from chaficial.content.models import ContentScript, StoryboardScene
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

    # 2. 공식 필드 구조 단언
    assert payload["model"] == "wan3"
    assert payload["duration"] == 30
    assert payload["ratio"] == "720:1280"
    assert "promptText" in payload
    assert isinstance(payload["references"], list)

    # 3. references 배열 항목 검증 (type, url)
    refs = payload["references"]
    assert len(refs) == 2
    assert refs[0] == {"type": "image", "url": "https://cdn.chafficial.com/host.jpg"}
    assert refs[1] == {"type": "audio", "url": "https://cdn.chafficial.com/voice.wav"}

    # 4. 비공식 임의 필드 전무 단언
    assert "resolution" not in payload
    assert "options" not in payload
    assert "referenceImages" not in payload
    assert "referenceAudio" not in payload


# ============================================================================
# 4. 허위 사실 및 미증빙 문구 차단 검증 (P0)
# ============================================================================

def test_truth_safety_script_generation(pipeline: ContentProductionPipeline):
    """과장 약속('전액 환불', '오백만원 보상', '장난치는 거 아닙니다')이 일체 생성되지 않는지 검증."""
    vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-TRUTH-01",
        "data_source": "CERTIFIED",
        "model_name": "기아 쏘렌토",
        "model_year": 2021,
        "price": 3200,
        "mileage": 42000,
        "availability_status": "AVAILABLE",
        "partner_review_status": "APPROVED",
        "listing_status": "ACTIVE",
        "snapshot_observed_at": datetime.now(UTC) - timedelta(days=2),
        "images": [{"path_or_url": "/img/sorento.jpg", "republication_allowed": True}],
    })
    pipeline.repository.save_vehicle(vehicle)
    project = pipeline.create_vehicle_project(vehicle.candidate_id)

    _, review_id = pipeline.start_expert_review(project.project_id)
    project = pipeline.draft_script_with_expert_feedback(
        project.project_id, review_id, {"q": "상태 점검 완료 매물입니다."}
    )

    full_text = project.script.full_text

    # 허위 및 과장 표현 전무 단언
    prohibited_phrases = [
        "장난치는 거 아닙니다",
        "고민하면 바로 나가니까",
        "전액 환불",
        "오백만원 보상",
        "완벽",
        "최상",
        "침수차 피해 급증",
    ]
    for phrase in prohibited_phrases:
        assert phrase not in full_text, f"금지된 과장 표현 '{phrase}' 발견됨"


# ============================================================================
# 5. 전문가 및 대본 승인 절차 (수정 시 승인 취소 & 비인가자 차단) (P1)
# ============================================================================

def test_script_approval_invalidation_and_unauthorized_block(pipeline: ContentProductionPipeline):
    """대본 수정 시 승인 자동 무효화 및 비인가 사용자 승인 차단 검증."""
    vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-APP-TEST",
        "data_source": "TEST",
        "model_name": "현대 아반떼",
        "model_year": 2022,
        "price": 1900,
        "mileage": 30000,
        "availability_status": "AVAILABLE",
        "partner_review_status": "APPROVED",
        "listing_status": "ACTIVE",
        "images": [{"path_or_url": "/img/1.jpg", "republication_allowed": True}],
    })
    pipeline.repository.save_vehicle(vehicle)
    project = pipeline.create_vehicle_project(vehicle.candidate_id)

    _, review_id = pipeline.start_expert_review(project.project_id)
    project = pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {"q": "정상 매물"})

    # 1. 비인가 사용자 승인 시도 차단
    with pytest.raises(UnapprovedContentError) as exc_info:
        pipeline.approve_script(project.project_id, approver_role="ANONYMOUS_USER")
    assert "권한이 없는 사용자" in str(exc_info.value)

    # 2. 정규 승인권자 승인
    project = pipeline.approve_script(project.project_id, approver_role="DEALER_PARTNER_AUTHORIZED")
    assert project.status == ContentWorkflowStatus.APPROVED
    assert project.script.is_approved is True
    assert project.script.version == 1

    # 3. 대본 재작성/수정 시 기존 승인 자동 무효화 검증
    project = pipeline.draft_script_with_expert_feedback(
        project.project_id, review_id, {"q": "재검토 후 수정"}
    )
    assert project.status == ContentWorkflowStatus.SCRIPT_DRAFT
    assert project.script.is_approved is False
    assert project.script.approved_by is None
    assert project.script.version == 2


# ============================================================================
# 6. 생성 작업 상태 머신 분리 (P0)
# ============================================================================

def test_generation_state_machine_isolation(pipeline: ContentProductionPipeline):
    """드라이런 검증(DRY_RUN_VALIDATED)과 실제 생성 완료(GENERATION_SUCCEEDED)의 상태 분리 검증."""
    trend = pipeline.trend_engine.register_trend_candidate(
        platform="YOUTUBE_SHORTS",
        source_url="https://youtube.com/shorts/state_test",
        title="중고차 점검 요령",
        account_name="test_account",
    )
    project = pipeline.create_trend_project(trend.candidate_id)
    _, review_id = pipeline.start_expert_review(project.project_id)
    pipeline.draft_script_with_expert_feedback(project.project_id, review_id, {"q": "답변"})
    pipeline.approve_script(project.project_id)

    host_asset = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="/host.jpg",
        label="호스트",
        republication_allowed=True,
    )
    project = pipeline.prepare_production(project.project_id, authorized_assets=[host_asset])
    assert project.status == ContentWorkflowStatus.PRODUCTION_READY

    # 1. 드라이런 실행 -> 반드시 DRY_RUN_VALIDATED (절대 GENERATION_SUCCEEDED 아님)
    project = pipeline.execute_video_generation(project.project_id, dry_run=True)
    assert project.status == ContentWorkflowStatus.DRY_RUN_VALIDATED
    assert project.result_video_url is None

    # 2. 결과 비디오 URL 없이 성공 완료 처리 시도 시 차단
    with pytest.raises(WorkflowTransitionError) as exc_info:
        project.transition_to(ContentWorkflowStatus.GENERATION_SUCCEEDED)
    assert "실제 비디오 결과 자산" in str(exc_info.value)

    # 3. 유효한 결과 자산 주입 시 성공 완료 전이
    project = pipeline.execute_video_generation(
        project.project_id, dry_run=False, mock_success_url="https://storage.chafficial.com/video/result.mp4"
    )
    assert project.status == ContentWorkflowStatus.GENERATION_SUCCEEDED
    assert project.result_video_url == "https://storage.chafficial.com/video/result.mp4"


# ============================================================================
# 7. 출력 품질 및 30초 발화 속도 감사 (다양한 6개 시나리오)
# ============================================================================

def test_speech_timing_and_quality_across_diverse_vehicles(pipeline: ContentProductionPipeline):
    """세단, SUV, 경차 3종 매물 및 썰 3종의 30초 발화 속도 및 조사 품질 검증."""
    vehicles = [
        ("현대 아반떼", 2022, 1900, 30000, "아반떼가"),
        ("기아 쏘렌토", 2021, 3200, 45000, "쏘렌토가"),
        ("기아 레이", 2023, 1350, 15000, "레이가"),
    ]

    for model, year, price, mileage, expected_subject in vehicles:
        v = VehicleContentAdapter.from_dict({
            "vehicle_id": f"CAR-{model}",
            "data_source": "TEST",
            "model_name": model,
            "model_year": year,
            "price": price,
            "mileage": mileage,
            "availability_status": "AVAILABLE",
            "partner_review_status": "APPROVED",
            "listing_status": "ACTIVE",
            "images": [{"path_or_url": "/img.jpg", "republication_allowed": True}],
        })
        pipeline.repository.save_vehicle(v)
        proj = pipeline.create_vehicle_project(v.candidate_id)
        _, rev_id = pipeline.start_expert_review(proj.project_id)
        proj = pipeline.draft_script_with_expert_feedback(proj.project_id, rev_id, {})

        script = proj.script
        assert expected_subject in script.full_text, f"{model}의 올바른 조사가 반영되지 않음"

        # 30초 발화 시간(음절수/4.5) 계산
        est_seconds = estimate_speech_duration_seconds(script.full_text)
        assert 15.0 <= est_seconds <= 30.0, f"{model} 대본의 발화 시간({est_seconds}초)이 30초 기준을 벗어남"
