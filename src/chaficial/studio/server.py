"""CHA-FICIAL AI Content Studio localhost 웹 대시보드 서버.

DIRECTIVE 004-A 명세 준수:
- 최소한의 의존성 (Python 표준 라이브러리 기반 HTTP 서버)
- 5개 화면 지원 REST API 라우팅
- 포트 8501 (또는 사용자 지정 포트) 서빙
- CLI 구동 진입점: python -m chaficial.studio.server [--port 8501] [--host 127.0.0.1]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from chaficial.studio.models import ContentFormat, ContentPlatform, TopicStatus
from chaficial.studio.service import StudioService

UI_DIR = Path(__file__).parent / "ui"
HTML_INDEX_FILE = UI_DIR / "index.html"


class StudioHTTPRequestHandler(BaseHTTPRequestHandler):
    """Studio 대시보드 REST API 및 정적 자산 서빙 핸들러."""

    service: StudioService

    def log_message(self, format: str, *args: Any) -> None:
        # 콘솔 로그 간소화
        sys.stderr.write(f"[Studio HTTP] {self.address_string()} - {format % args}\n")

    def _send_json(self, data: Any, status_code: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, content: str, status_code: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw) if raw.strip() else {}

    def do_GET(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query_params = urllib.parse.parse_qs(parsed_url.query)

        # 1. 정적 UI 서빙
        if path in ("/", "/index.html"):
            if HTML_INDEX_FILE.exists():
                content = HTML_INDEX_FILE.read_text(encoding="utf-8")
                self._send_html(content)
            else:
                self._send_html("<h1>UI file not found</h1>", status_code=404)
            return

        # 2. REST API: 토픽 추천 목록
        if path == "/api/topics":
            status_param = query_params.get("status", [None])[0]
            status_enum = TopicStatus(status_param) if status_param else None
            topics = self.service.get_topic_recommendations(status=status_enum)
            self._send_json([t.model_dump() for t in topics])
            return

        # 3. REST API: 비디오 목록
        if path == "/api/videos":
            plat_param = query_params.get("platform", [None])[0]
            fmt_param = query_params.get("format", [None])[0]
            plat = ContentPlatform(plat_param) if plat_param else None
            fmt = ContentFormat(fmt_param) if fmt_param else None
            videos = self.service.list_videos(platform=plat, content_format=fmt)
            self._send_json([v.model_dump() for v in videos])
            return

        # 4. REST API: 기획서 상세 조회
        if path == "/api/briefs":
            rec_id = query_params.get("recommendation_id", [None])[0]
            if not rec_id:
                self._send_json({"error": "recommendation_id parameter is required"}, status_code=400)
                return
            brief = self.service.get_or_create_brief(rec_id)
            if not brief:
                self._send_json({"error": "Brief not found for topic"}, status_code=404)
                return
            self._send_json(brief.model_dump())
            return

        # 5. REST API: 롱폼 심층 분석
        if path == "/api/longform/analyze":
            vid = query_params.get("video_id", [None])[0]
            if not vid:
                self._send_json({"error": "video_id parameter is required"}, status_code=400)
                return
            analysis = self.service.analyze_longform(vid)
            if not analysis:
                self._send_json({"error": "Longform analysis failed"}, status_code=404)
                return
            self._send_json(analysis.model_dump())
            return

        # 6. REST API: 설정 및 커넥터 상태
        if path == "/api/settings":
            settings = self.service.get_settings()
            self._send_json(settings)
            return

        self._send_json({"error": "Not Found"}, status_code=404)

    def do_POST(self) -> None:
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        # 1. REST API: 토픽 상태 변경
        if path == "/api/topics/status":
            body = self._read_json_body()
            rec_id = body.get("recommendation_id")
            new_status_str = body.get("status")
            if not rec_id or not new_status_str:
                self._send_json({"error": "Missing recommendation_id or status"}, status_code=400)
                return
            success = self.service.update_topic_status(rec_id, TopicStatus(new_status_str))
            self._send_json({"success": success})
            return

        # 2. REST API: 사장님 답변 제출 및 대본 갱신
        if path == "/api/briefs/answers":
            body = self._read_json_body()
            rec_id = body.get("recommendation_id")
            answers = body.get("answers", {})
            if not rec_id:
                self._send_json({"error": "Missing recommendation_id"}, status_code=400)
                return
            updated_brief = self.service.submit_expert_answers(rec_id, answers)
            if not updated_brief:
                self._send_json({"error": "Failed to update brief"}, status_code=404)
                return
            self._send_json(updated_brief.model_dump())
            return

        # 3. REST API: 차피셜 기존 파이프라인 프로젝트 연계
        if path == "/api/briefs/link-project":
            body = self._read_json_body()
            rec_id = body.get("recommendation_id")
            if not rec_id:
                self._send_json({"error": "Missing recommendation_id"}, status_code=400)
                return
            project_id = self.service.link_to_content_pipeline(rec_id)
            if not project_id:
                self._send_json({"error": "Failed to link project"}, status_code=404)
                return
            self._send_json({"success": True, "project_id": project_id})
            return

        # 4. REST API: 집중 검색 즉시 실행
        if path == "/api/discovery/run":
            body = self._read_json_body()
            custom_kw = body.get("keywords")
            result = self.service.run_discovery_search(custom_keywords=custom_kw)
            self._send_json(result)
            return

        # 5. REST API: 설정 갱신
        if path == "/api/settings":
            body = self._read_json_body()
            keywords = body.get("search_keywords")
            mode = body.get("operation_mode")
            self.service.update_settings(keywords=keywords, operation_mode=mode)
            self._send_json({"success": True})
            return

        self._send_json({"error": "Not Found"}, status_code=404)


def run_server(host: str = "127.0.0.1", port: int = 8501, service: StudioService | None = None) -> None:
    """대시보드 HTTP 서버 실행."""
    active_service = service or StudioService()
    # 첫 기동 시 기본 데이터가 없다면 검색 1회 실행하여 오늘의 추천 TOP 10 준비
    active_service.get_topic_recommendations()

    # 핸들러에 서비스 바인딩
    StudioHTTPRequestHandler.service = active_service

    server = ThreadingHTTPServer((host, port), StudioHTTPRequestHandler)
    print("\n========================================================")
    print("🚀 CHA-FICIAL AI Content Studio 대시보드 서버 가동 완료!")
    print(f"👉 접속 URL: http://{host}:{port}")
    print("👉 종료 방법: Ctrl + C")
    print("========================================================\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료 신호 수신. 정상 종료합니다.")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CHA-FICIAL AI Content Studio Server")
    parser.add_argument("--host", default="127.0.0.1", help="서버 호스트 (기본: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8501, help="서버 포트 (기본: 8501)")
    args = parser.parse_args()

    run_server(host=args.host, port=args.port)
