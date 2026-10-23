"""CHA-FICIAL 시장 관측 주기적 감시자 CLI 실행 스크립트 (DIRECTIVE 013).

사용 예시:
  # STANDBY 대기 모드 단발 실행 (감독 승인 전 안전 모드)
  uv run python scripts/scheduled_market_watcher.py --once

  # REPLAY 모드로 1회 실행
  uv run python scripts/scheduled_market_watcher.py --mode replay --once

  # LIVE 모드 승인 활성화 단발 실행
  uv run python scripts/scheduled_market_watcher.py --mode live --enable-live-scheduler --once

  # 지정 주기(초) 반복 실행
  uv run python scripts/scheduled_market_watcher.py --interval-seconds 86400
"""

import argparse
import os
import sys
from pathlib import Path

# 프로젝트 루트 임포트 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chaficial.tracker.scheduler import MarketObservationScheduler, SchedulerConfig


def main():
    parser = argparse.ArgumentParser(description="CHA-FICIAL 주기적 시장 관측 자율 운영 스케줄러")
    parser.add_argument("--mode", choices=["live", "replay"], default="live", help="수집 모드 (기본: live)")
    parser.add_argument("--interval-seconds", type=float, default=86400.0, help="관측 주기 초 단위 (기본: 86400.0 / 24시간)")
    parser.add_argument("--max-retries", type=int, default=3, help="장애 시 최대 재시도 횟수 (기본: 3)")
    parser.add_argument("--initial-backoff", type=float, default=5.0, help="초기 백오프 대기 시간 초 (기본: 5.0)")
    parser.add_argument("--enable-live-scheduler", action="store_true", help="LIVE 자동 수집 플래그 (감독 승인 없이는 실행 거부됨)")
    parser.add_argument("--auth-file", type=str, default="data/.live_authorization.json", help="로컬 운영 승인 파일 경로 (Git 비추적, 013-F)")
    parser.add_argument("--once", action="store_true", help="1회만 실행하고 즉시 종료")
    parser.add_argument("--db-path", type=str, default="data/chaficial_market_timeseries.db", help="대상 DB 경로")

    args = parser.parse_args()

    # 환경 변수 기반 플래그 지원
    env_enable = os.getenv("CHAFFICIAL_ENABLE_LIVE_SCHEDULER", "").lower() in ("true", "1", "yes")
    live_enabled = args.enable_live_scheduler or env_enable

    config = SchedulerConfig(
        interval_seconds=args.interval_seconds,
        max_retries=args.max_retries,
        initial_backoff_sec=args.initial_backoff,
        enable_live_execution=live_enabled,
        auth_file_path=Path(args.auth_file),
        db_path=Path(args.db_path),
    )

    scheduler = MarketObservationScheduler(config=config)

    if args.once:
        scheduler.acquire_lock()
        try:
            res = scheduler.execute_single_observation(mode=args.mode)
            print(f"[+] 실행 결과: {res}")
        finally:
            scheduler.release_lock()
    else:
        scheduler.run_loop(mode=args.mode)


if __name__ == "__main__":
    main()
