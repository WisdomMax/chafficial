"""차피셜(CHA-FICIAL) 통합 운영 관리 시스템 웹 서버 실행기.

포트 8501 (또는 사용자 지정 포트)로 FastAPI 앱을 구동합니다.
- 관리자 OS: http://127.0.0.1:8501/
- 차마트 고객 쇼룸: http://127.0.0.1:8501/chamart
"""

import argparse
import sys
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="차피셜(CHA-FICIAL) 통합 운영 관리 시스템 서버")
    parser.add_argument("--host", default="127.0.0.1", help="바인딩 호스트 (기본: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8501, help="바인딩 포트 (기본: 8501)")
    parser.add_argument("--reload", action="store_true", help="자동 리로드 활성화")
    args = parser.parse_args()

    print(f"[*] 차피셜(CHA-FICIAL) 통합 운영 관리 시스템 가동 중... http://{args.host}:{args.port}")
    uvicorn.run(
        "chaficial.platform.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
