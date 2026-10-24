"""CHA-FICIAL DIRECTIVE 004-A 테스트 스위트.

검증 항목:
1. YouTube 롱폼 vs 쇼츠 판별 및 신뢰수준(VERIFIED vs ESTIMATED)
2. YouTube Data API 쿼터 추적 및 DEMO/LIVE 모드 분리
3. 다차원 토픽 클러스터링 및 TOP 5~10 랭킹 (인기도/속도/딜러적합도)
4. 롱폼 자막 정밀 분석 vs 메타데이터 분석의 정직한 구분
5. 기획서 생성 및 차마트 사장님 답변 실시간 대본 반영
6. SQLite 로컬 영속화 (재접속 시 데이터 및 상태 보존)
7. 기존 chaficial.content 파이프라인 (EXPERT_STORY) 프로젝트 연계
8. localhost 대시보드 REST API 엔드포인트 계약
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from chaficial.studio.connectors.youtube import (
    YouTubeConnector,
    parse_iso8601_duration,
)
from chaficial.studio.models import (
    AnalysisConfidence,
    ContentFormat,
    ContentPlatform,
    FormatConfidence,
    TopicStatus,
    VideoRecord,
)
from chaficial.studio.service import StudioService
from chaficial.studio.storage import StudioStorage


@pytest.fixture
def temp_db(tmp_path: Path) -> StudioStorage:
    db_file = tmp_path / "test_studio.db"
    return StudioStorage(str(db_file))


@pytest.fixture
def studio_service(temp_db: StudioStorage) -> StudioService:
    connector = YouTubeConnector(api_key=None)  # 데모 모드로 안전 테스트
    return StudioService(storage=temp_db, youtube_connector=connector)


# ============================================================================
# 1. YouTube 커넥터 및 쇼츠/롱폼 판별 테스트
# ============================================================================

def test_iso8601_duration_parsing():
    """ISO 8601 문자열의 초 단위 변환 검증."""
    assert parse_iso8601_duration("PT45S") == 45
    assert parse_iso8601_duration("PT1M15S") == 75
    assert parse_iso8601_duration("PT1H2M30S") == 3750
    assert parse_iso8601_duration("") == 0


def test_youtube_connector_shorts_vs_longform_classification(studio_service: StudioService):
    """비디오 지속 시간 및 태그에 따른 쇼츠 vs 롱폼 및 신뢰 수준 분류 검증."""
    videos = studio_service.list_videos()
    assert len(videos) > 0

    shorts_count = sum(1 for v in videos if v.content_format == ContentFormat.YOUTUBE_SHORTS)
    long_count = sum(1 for v in videos if v.content_format == ContentFormat.YOUTUBE_LONG)
    assert shorts_count > 0, "쇼츠 영상이 최소 1개 이상 존재해야 함"
    assert long_count > 0, "롱폼 영상이 최소 1개 이상 존재해야 함"

    # 쇼츠 영상은 재생시간이 60초 이하이거나 #shorts 구조 검증
    for v in videos:
        if v.content_format == ContentFormat.YOUTUBE_SHORTS:
            assert v.duration_seconds <= 60 or "#shorts" in v.title.lower() or "/shorts/" in v.url
        elif v.content_format == ContentFormat.YOUTUBE_LONG:
            assert v.duration_seconds > 60 or v.format_confidence == FormatConfidence.ESTIMATED


def test_youtube_connector_demo_mode_status(studio_service: StudioService):
    """API 키 미제공 시 DEMO 모드 안전 동작 및 상태 표기 검증."""
    status = studio_service.youtube.get_status()
    assert status.platform == ContentPlatform.YOUTUBE
    assert status.is_connected is True
    assert status.connection_mode == "DEMO"
    assert "데모 데이터셋 모드" in status.notes
    assert status.daily_quota_used == 0


# ============================================================================
# 2. 토픽 클러스터링 및 다차원 스코어러 테스트
# ============================================================================

def test_topic_clustering_and_top_ranking(studio_service: StudioService):
    """단순 조회수 정렬 배제, 공통 관심사 클러스터링 및 딜러 적합도 기반 TOP 5~10 랭킹 검증."""
    topics = studio_service.get_topic_recommendations()
    assert len(topics) >= 5, "최소 5개 이상의 추천 주제가 산출되어야 함"
    assert len(topics) <= 10, "최대 10개 이하의 추천 주제가 산출되어야 함"

    # 순위 순서 검증 (1위부터 오름차순 정렬)
    ranks = [t.rank for t in topics]
    assert ranks == list(range(1, len(topics) + 1))

    for t in topics:
        assert t.composite_score > 0
        assert t.popularity_score > 0
        assert t.dealer_fit_score > 0
        assert len(t.supporting_video_ids) > 0
        assert len(t.selection_reason.strip()) > 10
        assert len(t.trend_summary.strip()) > 10
        assert t.status == TopicStatus.RECOMMENDED
        assert t.confidence_level in (AnalysisConfidence.HIGH_CONFIDENCE, AnalysisConfidence.LOW_CONFIDENCE)


def test_topic_status_transition(studio_service: StudioService):
    """추천 주제의 상태 전이 (ADOPTED, SHELVED, DISMISSED) 및 영속화 검증."""
    topics = studio_service.get_topic_recommendations()
    target_id = topics[0].recommendation_id

    # 채택
    ok = studio_service.update_topic_status(target_id, TopicStatus.ADOPTED)
    assert ok is True
    updated = [t for t in studio_service.get_topic_recommendations(status=TopicStatus.ADOPTED) if t.recommendation_id == target_id]
    assert len(updated) == 1
    assert updated[0].status == TopicStatus.ADOPTED

    # 보류
    studio_service.update_topic_status(target_id, TopicStatus.SHELVED)
    updated = [t for t in studio_service.get_topic_recommendations(status=TopicStatus.SHELVED) if t.recommendation_id == target_id]
    assert len(updated) == 1
    assert updated[0].status == TopicStatus.SHELVED


# ============================================================================
# 3. 롱폼 자막 정밀 분석 vs 메타데이터 분석 테스트
# ============================================================================

def test_longform_analysis_with_captions(studio_service: StudioService):
    """자막이 있는 롱폼 영상에 대해 쇼츠 독립 소재 1~5개 및 타임코드 추출 검증."""
    videos = studio_service.list_videos(content_format=ContentFormat.YOUTUBE_LONG)
    caption_video = next((v for v in videos if v.has_captions), None)
    assert caption_video is not None

    analysis = studio_service.analyze_longform(caption_video.video_id)
    assert analysis is not None
    assert analysis.analyzed_from_captions is True
    assert len(analysis.main_claim.strip()) > 0
    assert len(analysis.short_extracts) >= 1
    assert len(analysis.short_extracts) <= 5

    for ext in analysis.short_extracts:
        assert len(ext.title) > 0
        assert len(ext.core_question) > 0
        assert "~" in ext.timecode_range
        assert len(ext.fact_check_needed) >= 1


def test_longform_analysis_without_captions(studio_service: StudioService):
    """자막이 없는 영상의 경우 전체 영상 분석으로 과장하지 않고 메타데이터 분석임을 정직하게 표기."""
    no_caption_video = VideoRecord(
        video_id="yt_test_no_cap",
        platform=ContentPlatform.YOUTUBE,
        content_format=ContentFormat.YOUTUBE_LONG,
        format_confidence=FormatConfidence.VERIFIED,
        url="https://youtube.com/watch?v=no_cap",
        title="자막 없는 중고차 엔진 점검 팁",
        channel_name="테스트채널",
        description="설명문입니다.",
        published_at=datetime.now(UTC),
        duration_seconds=300,
        has_captions=False,
    )
    studio_service.storage.save_videos([no_caption_video])

    analysis = studio_service.analyze_longform("yt_test_no_cap")
    assert analysis is not None
    assert analysis.analyzed_from_captions is False
    assert "[제목/설명 기반 추정]" in analysis.main_claim


# ============================================================================
# 4. 콘텐츠 제작 기획서 및 차마트 사장님 답변 반영 테스트
# ============================================================================

def test_production_brief_initial_creation_and_expert_answers(studio_service: StudioService):
    """제작 기획서 생성, 제목 3종/후킹 3종, 사장님 답변 반영 및 대본 갱신 검증."""
    topics = studio_service.get_topic_recommendations()
    target_rec = topics[0]

    brief = studio_service.get_or_create_brief(target_rec.recommendation_id)
    assert brief is not None
    assert len(brief.recommended_titles) == 3
    assert len(brief.hook_sentences) == 3
    assert len(brief.interview_questions) >= 3
    assert len(brief.scene_guides) >= 3
    assert brief.has_expert_answered is False
    assert "차마트 사장님의 현장 실제 답변 대기 중" in brief.draft_script_text

    # 사장님 답변 제출
    q1 = brief.interview_questions[0]
    expert_answers = {
        q1: "수입차 살 때 10만km 넘어가면 오일팬 누유랑 하체 부싱은 무조건 교체하고 타야 합니다.",
    }
    updated_brief = studio_service.submit_expert_answers(target_rec.recommendation_id, expert_answers)
    assert updated_brief is not None
    assert updated_brief.has_expert_answered is True
    assert updated_brief.revision_count == 2
    assert "오일팬 누유랑 하체 부싱은 무조건 교체" in updated_brief.draft_script_text


# ============================================================================
# 5. 기존 chaficial.content 파이프라인 (EXPERT_STORY) 연계 테스트
# ============================================================================

def test_link_to_chaficial_content_pipeline(studio_service: StudioService):
    """기획서를 기존 차피셜 EXPERT_STORY 프로젝트로 연계 생성 검증."""
    topics = studio_service.get_topic_recommendations()
    target_rec = topics[0]

    project_id = studio_service.link_to_content_pipeline(target_rec.recommendation_id)
    assert project_id is not None

    brief = studio_service.get_or_create_brief(target_rec.recommendation_id)
    assert brief.linked_project_id == project_id
    assert brief.is_approved is True

    # 주제 상태가 자동으로 ADOPTED로 전이되었는지 확인
    recs = [t for t in studio_service.get_topic_recommendations() if t.recommendation_id == target_rec.recommendation_id]
    assert recs[0].status == TopicStatus.ADOPTED


# ============================================================================
# 6. SQLite 로컬 영속화 및 재접속 보존 테스트
# ============================================================================

def test_sqlite_persistence_across_service_instances(temp_db: StudioStorage):
    """서비스 인스턴스를 재기동해도 저장된 영상, 토픽, 기획서, 사장님 답변이 보존되는지 검증."""
    # 인스턴스 1: 검색 및 답변 입력
    svc1 = StudioService(storage=temp_db)
    topics = svc1.get_topic_recommendations()
    target_id = topics[0].recommendation_id
    svc1.submit_expert_answers(target_id, {"테스트질문": "테스트답변입니다."})
    svc1.update_topic_status(target_id, TopicStatus.ADOPTED)

    # 인스턴스 2: 새로운 서비스 인스턴스 생성 (동일 DB 파일 참조)
    svc2 = StudioService(storage=temp_db)
    recs2 = svc2.get_topic_recommendations()
    assert len(recs2) == len(topics)

    target_rec2 = next(t for t in recs2 if t.recommendation_id == target_id)
    assert target_rec2.status == TopicStatus.ADOPTED

    brief2 = svc2.get_or_create_brief(target_id)
    assert brief2 is not None
    assert brief2.has_expert_answered is True
    assert brief2.expert_answers.get("테스트질문") == "테스트답변입니다."


# ============================================================================
# 7. localhost 대시보드 HTTP 서버 REST API 통합 테스트
# ============================================================================

def test_http_server_rest_api_lifecycle(studio_service: StudioService):
    """표준 라이브러리 HTTP 서버 핸들러를 통한 실제 REST API 요청/응답 검증."""
    import threading
    import urllib.request
    from http.server import ThreadingHTTPServer

    from chaficial.studio.server import StudioHTTPRequestHandler

    StudioHTTPRequestHandler.service = studio_service
    # 무작위 여유 포트(포트 0)로 서버 바인딩
    server = ThreadingHTTPServer(("127.0.0.1", 0), StudioHTTPRequestHandler)
    host, port = server.server_address

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    base_url = f"http://{host}:{port}"
    try:
        # 1. GET / (UI HTML 서빙)
        with urllib.request.urlopen(f"{base_url}/") as resp:
            assert resp.status == 200
            assert "text/html" in resp.headers.get("Content-Type", "")
            html = resp.read().decode("utf-8")
            assert "CHA-FICIAL" in html
            assert "오늘 제작할 가치가 가장 높은 주제" in html

        # 2. GET /api/topics
        with urllib.request.urlopen(f"{base_url}/api/topics") as resp:
            assert resp.status == 200
            topics_data = json.loads(resp.read().decode("utf-8"))
            assert len(topics_data) >= 5
            first_topic = topics_data[0]
            rec_id = first_topic["recommendation_id"]

        # 3. GET /api/videos
        with urllib.request.urlopen(f"{base_url}/api/videos") as resp:
            assert resp.status == 200
            videos_data = json.loads(resp.read().decode("utf-8"))
            assert len(videos_data) > 0

        # 4. GET /api/briefs?recommendation_id=...
        with urllib.request.urlopen(f"{base_url}/api/briefs?recommendation_id={rec_id}") as resp:
            assert resp.status == 200
            brief_data = json.loads(resp.read().decode("utf-8"))
            assert len(brief_data["recommended_titles"]) == 3

        # 5. POST /api/topics/status (주제 상태 변경)
        post_data = json.dumps({"recommendation_id": rec_id, "status": "ADOPTED"}).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/topics/status", data=post_data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            res = json.loads(resp.read().decode("utf-8"))
            assert res["success"] is True

        # 6. POST /api/briefs/answers (사장님 답변 제출)
        q_text = brief_data["interview_questions"][0]
        answer_payload = json.dumps({
            "recommendation_id": rec_id,
            "answers": {q_text: "HTTP 테스트 답변입니다."}
        }).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/api/briefs/answers", data=answer_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 200
            updated_brief = json.loads(resp.read().decode("utf-8"))
            assert updated_brief["has_expert_answered"] is True
            assert "HTTP 테스트 답변입니다." in updated_brief["draft_script_text"]

    finally:
        server.shutdown()
        server.server_close()

