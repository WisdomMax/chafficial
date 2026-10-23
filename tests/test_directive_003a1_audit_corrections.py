"""DIRECTIVE 003-A1 독립 감사 및 결함 수정 회귀 테스트.

검증 항목:
1. 한국어 조사 오류 수정 검증 ("카이엔 쿠페가" vs "카니발이")
2. 연식 및 금액 자연스러운 한글 독음 변환 검증 ("이천이십년식", "육천구백만원")
3. 확인되지 않은 무사고/침수/성능 단정 배제 검증
4. 전문가 미답변 시 허위 경험 귀속 원천 방지 검증
5. 대본 씬별 출처(FACT / EXPERT_VERIFIED / AI_CREATIVE) 분리 검증
6. 실제 판매 홍보 불가 매물(비활성 매물, 파트너 미승인, 재고 없음, 권한 없는 사진) 엄격 차단 검증
7. Runway Dev WAN 3.0 REST API JSON Payload 명세 규격 검증
"""

import pytest

from chaficial.content.models import (
    AssetType,
    MediaAsset,
    ProvenanceType,
    UnauthorizedAssetError,
    VideoModelType,
)
from chaficial.content.pipeline import ContentProductionPipeline
from chaficial.content.repository import ContentRepository
from chaficial.content.script_engine import (
    attach_particle,
    convert_year_to_korean,
    koreanize_numbers,
)
from chaficial.content.vehicle_adapter import CommercialIneligibilityError, VehicleContentAdapter


@pytest.fixture
def pipeline() -> ContentProductionPipeline:
    repo = ContentRepository()
    return ContentProductionPipeline(repository=repo)


# ============================================================================
# 1. 한국어 조사 및 발음 품질 회귀 테스트
# ============================================================================

def test_korean_particle_and_pronunciation():
    """받침 유무에 따른 조사 결합 및 숫자 독음 검증."""
    # 1. 받침 없는 단어: '가', '는', '를'
    assert attach_particle("카이엔 쿠페", "이/가") == "카이엔 쿠페가"
    assert attach_particle("아반떼", "이/가") == "아반떼가"
    assert attach_particle("쏘렌토", "은/는") == "쏘렌토는"
    assert attach_particle("그랜저", "을/를") == "그랜저를"

    # 2. 받침 있는 단어: '이', '은', '을'
    assert attach_particle("카니발", "이/가") == "카니발이"
    assert attach_particle("포르쉐 카이엔", "이/가") == "포르쉐 카이엔이"
    assert attach_particle("모닝", "은/는") == "모닝은"
    assert attach_particle("트랙스", "을/를") == "트랙스를"

    # 3. 연도 변환
    assert convert_year_to_korean(2020) == "이천이십"
    assert convert_year_to_korean(2024) == "이천이십사"
    assert convert_year_to_korean(2019) == "이천십구"

    # 4. 종합 대사 치환
    raw_text = "2020년식 포르쉐 카이엔 쿠페 6900만원, 21인치 휠에 102,039km 주행 4존 에어컨 30초 안내"
    koreanized = koreanize_numbers(raw_text)
    assert "이천이십년식" in koreanized
    assert "육천구백만원" in koreanized
    assert "이십일인치" in koreanized
    assert "십만 이천 킬로" in koreanized
    assert "포존" in koreanized
    assert "삼십초" in koreanized


# ============================================================================
# 2. 사실관계 왜곡 및 허위 경험 귀속 방지 검증
# ============================================================================

def test_unverified_accident_claim_prevention(pipeline: ContentProductionPipeline):
    """사고 이력이 검증되지 않은 매물에 대해 '완전 무사고'로 임의 단정하지 않는지 검증."""
    unverified_vehicle = VehicleContentAdapter.from_dict({
        "vehicle_id": "CAR-UNVERIFIED-ACCIDENT",
        "data_source": "TEST",
        "model_name": "BMW 520d",
        "model_year": 2021,
        "price": 3800,
        "mileage": 60000,
        "verified_pros": [],       # 무사고 인증 없음
        "precautions": [],         # 단순 교환 언급 없음
        "images": [
            {"path_or_url": "/img/520d.jpg", "label": "정면", "is_authorized": True}
        ],
    })
    pipeline.repository.save_vehicle(unverified_vehicle)
    project = pipeline.create_vehicle_project(unverified_vehicle.candidate_id)

    # 전문가 답변 없이 대본 생성
    _, review_id = pipeline.start_expert_review(project.project_id)
    project = pipeline.draft_script_with_expert_feedback(
        project_id=project.project_id,
        review_id=review_id,
        expert_answers={},  # 사장님 답변 미입력
    )

    full_script = project.script.full_text
    # '완전 무사고'라는 단정적 허위 표현이 없어야 함
    assert "완전 무사고" not in full_script
    assert "성능점검기록부 원본을 투명하게 공개" in full_script


def test_false_expert_attribution_prevention(pipeline: ContentProductionPipeline):
    """사장님이 직접 답변하지 않은 경우, 허위 경험(25년 매일 차를 보면서 느낀 건데 등)을 귀속하지 않는지 검증."""
    trend = pipeline.trend_engine.register_trend_candidate(
        platform="YOUTUBE_SHORTS",
        source_url="https://youtube.com/shorts/no_answer_test",
        title="허위매물 피하는 법",
        account_name="test_acc",
    )
    project = pipeline.create_trend_project(trend.candidate_id)
    _, review_id = pipeline.start_expert_review(project.project_id)

    # 사장님 답변 없이 대본 초안 생성
    project = pipeline.draft_script_with_expert_feedback(
        project_id=project.project_id,
        review_id=review_id,
        expert_answers={},  # 답변 없음
    )

    full_text = project.script.full_text
    # 허위 구술 문구가 들어가지 않아야 함
    assert "25년 동안 매일 차를 보면서 느낀 건데" not in full_text
    assert "최근 시장에서" in full_text

    # 출처 구분 검증 (FACT / AI_CREATIVE 분리)
    scenes = project.script.scenes
    assert any(s.provenance_type == ProvenanceType.FACT for s in scenes)
    assert any(s.provenance_type == ProvenanceType.AI_CREATIVE for s in scenes)


# ============================================================================
# 3. 판매 홍보 불가 매물 엄격 차단 검증
# ============================================================================

def test_delisted_vehicle_commercial_ineligibility():
    """매물 상태가 DELISTED(판매종료)인 경우 제작 진입 원천 차단."""
    delisted_data = {
        "vehicle_id": "CAR-DELISTED-001",
        "data_source": "ENCAR",
        "model_name": "현대 그랜저 IG",
        "model_year": 2019,
        "price": 2100,
        "mileage": 70000,
        "listing_status": "DELISTED",  # 판매 완료/삭제 매물
        "images": [{"path_or_url": "/img/1.jpg", "is_authorized": True}],
    }
    candidate = VehicleContentAdapter.from_dict(delisted_data)
    assert candidate.availability_status == "DELISTED"

    repo = ContentRepository()
    repo.save_vehicle(candidate)
    pipe = ContentProductionPipeline(repository=repo)

    with pytest.raises(CommercialIneligibilityError) as exc_info:
        pipe.create_vehicle_project(candidate.candidate_id)
    assert "DELISTED" in str(exc_info.value)


def test_partner_unapproved_vehicle_blocked():
    """파트너 검토가 완료되지 않은(PENDING/REJECTED) 매물 제작 진입 차단."""
    unapproved_data = {
        "vehicle_id": "CAR-PENDING-001",
        "data_source": "DEALER_PILOT",
        "model_name": "기아 K5",
        "model_year": 2021,
        "price": 1900,
        "mileage": 40000,
        "partner_review_status": "PENDING",  # 파트너 미승인
        "images": [{"path_or_url": "/img/k5.jpg", "is_authorized": True}],
    }
    candidate = VehicleContentAdapter.from_dict(unapproved_data)
    assert candidate.availability_status == "PARTNER_UNAPPROVED"

    repo = ContentRepository()
    repo.save_vehicle(candidate)
    pipe = ContentProductionPipeline(repository=repo)

    with pytest.raises(CommercialIneligibilityError):
        pipe.create_vehicle_project(candidate.candidate_id)


def test_unauthorized_image_vehicle_blocked():
    """상업적 재배포 권한이 없는(republication_allowed=False) 이미지만 가진 매물 차단."""
    no_auth_data = {
        "vehicle_id": "CAR-NO-AUTH-001",
        "data_source": "SCRAPED_PORTAL",
        "model_name": "제네시스 GV80",
        "model_year": 2022,
        "price": 5500,
        "mileage": 35000,
        "images": [
            {
                "path_or_url": "/unauthorized/gv80.jpg",
                "label": "포털 불펌 사진",
                "republication_allowed": False,  # 비인가
            }
        ],
    }
    candidate = VehicleContentAdapter.from_dict(no_auth_data)
    repo = ContentRepository()
    repo.save_vehicle(candidate)
    pipe = ContentProductionPipeline(repository=repo)

    with pytest.raises(UnauthorizedAssetError):
        pipe.create_vehicle_project(candidate.candidate_id)


# ============================================================================
# 4. Runway Dev WAN 3.0 API 공식 JSON Payload 명세 규격 검증
# ============================================================================

def test_wan3_runway_dev_api_payload_specification(pipeline: ContentProductionPipeline):
    """2026-10-22 공식 Runway Dev WAN 3.0 API 규격 준수 검증."""
    valid_data = {
        "vehicle_id": "CAR-WAN3-SPEC-TEST",
        "data_source": "PARTNER_CERTIFIED",
        "model_name": "포르쉐 카이엔 쿠페",
        "model_year": 2020,
        "price": 6900,
        "mileage": 102039,
        "verified_pros": ["크레용 컬러", "보르도 레드 시트", "완전 무사고"],
        "precautions": ["트렁크 단순교환 1건"],
        "images": [
            {
                "path_or_url": "https://storage.chafficial.com/cars/cayenne_front.jpg",
                "label": "카이엔 전면 정면",
                "is_authorized": True,
                "republication_allowed": True,
            }
        ],
    }
    vehicle = VehicleContentAdapter.from_dict(valid_data)
    pipeline.repository.save_vehicle(vehicle)
    project = pipeline.create_vehicle_project(vehicle.candidate_id)

    _, review_id = pipeline.start_expert_review(project.project_id)
    pipeline.draft_script_with_expert_feedback(
        project.project_id,
        review_id,
        {"q": "트렁크 단순교환 하나 있지만 뼈대는 멀쩡한 완전 무사고 차량입니다."},
    )
    pipeline.approve_script(project.project_id)

    # 에셋 주입 (대표님 시트 + 음성 + 실차)
    host_img = MediaAsset(
        asset_type=AssetType.IMAGE,
        path_or_url="https://storage.chafficial.com/hosts/dealer_sheet.jpg",
        label="차마트 사장님 3열 시트",
        is_authorized=True,
    )
    voice_audio = MediaAsset(
        asset_type=AssetType.AUDIO,
        path_or_url="https://storage.chafficial.com/audio/dealer_voice.wav",
        label="차마트 사장님 목소리 락",
        is_authorized=True,
    )

    project = pipeline.prepare_production(
        project_id=project.project_id,
        authorized_assets=[host_img, voice_audio] + vehicle.images,
        model_type=VideoModelType.WAN_3_0,
    )

    # 1. 웹 UI 텍스트 프롬프트 검증
    assert "Part-1 [Duration: 30s] [Aspect Ratio: 9:16]" in project.master_prompt
    assert "이 포르쉐 카이엔 쿠페가 육천구백만원?" in project.master_prompt  # '쿠페이' 조사 오류 완치 확인!

    # 2. Runway Dev API 요청 드라이런 실행 및 JSON Payload 검증
    project = pipeline.execute_video_generation(project.project_id, dry_run=True)
    gen_result = project.generation_result
    assert gen_result["status"] == "READY_FOR_API_SUBMISSION"
    assert gen_result["model"] == "wan-3.0"

    api_payload = gen_result["api_payload"]
    assert api_payload["model"] == "wan-3.0"
    assert api_payload["duration"] == 30
    assert api_payload["ratio"] == "9:16"
    assert api_payload["resolution"] == "720p"
    assert api_payload["options"]["native_audio"] is True
    assert api_payload["options"]["lip_sync"] is True

    # 참조 이미지 리스트 검증
    ref_images = api_payload["referenceImages"]
    assert len(ref_images) >= 2
    assert ref_images[0]["tag"] == "@Image 1"
    assert ref_images[0]["role"] == "subject_host"

    # 참조 오디오 바인딩 검증
    ref_audio = api_payload["referenceAudio"]
    assert ref_audio is not None
    assert ref_audio["tag"] == "@Audio 1"
    assert ref_audio["role"] == "voice_timbre"
    assert "dealer_voice.wav" in ref_audio["uri"]
