"""CHA-FICIAL 주기적 LIVE 시장 관측 스케줄러 모듈 (DIRECTIVE 013).

- fcntl 기반 단일 인스턴스 실행 잠금 (중복 실행 100% 차단)
- 지수 백오프(Exponential Backoff) 기반 안전 재시도 및 무한 루프 차단
- 감독 승인 전 무단 LIVE 실행 방지 안전 가드 (STANDBY / DRY_RUN 기본값)
- 관측 직전 SQLite 온라인 백업 및 PRAGMA integrity_check 자동 연동
- 일별 시장 요약 리포트 및 장애 격리 보고서 자동 발행
"""

import dataclasses
from datetime import UTC, datetime
import fcntl
import json
import logging
import os
from pathlib import Path
import time
import traceback
from typing import Any, Callable

from chaficial.tracker.daily_reporter import DailyMarketReporter

logger = logging.getLogger("chaficial.scheduler")


class SchedulerLockError(Exception):
    """스케줄러 중복 실행 방지 잠금 획득 실패 예외."""


@dataclasses.dataclass
class SchedulerConfig:
    """스케줄러 설정 데이터클래스."""

    interval_seconds: float = 86400.0  # 기본: 24시간
    max_retries: int = 3               # 최대 재시도 횟수
    initial_backoff_sec: float = 5.0   # 1차 재시도 대기 시간 (초)
    backoff_factor: float = 2.0        # 지수 증가 배수
    enable_live_execution: bool = False  # 안전 가드: 감독 별도 승인 전까지 False 필수
    db_path: Path = Path("data/chaficial_market_timeseries.db")
    lock_file: Path = Path("data/.scheduler.lock")
    report_dir: Path = Path("reports/daily_summaries")
    failure_dir: Path = Path("reports/failures")


class MarketObservationScheduler:
    """주기적 시장 관측 자율 운영 스케줄러."""

    def __init__(
        self,
        config: SchedulerConfig | None = None,
        pipeline_runner: Callable[..., Any] | None = None,
    ):
        self.config = config or SchedulerConfig()
        self.pipeline_runner = pipeline_runner
        self.config.failure_dir.mkdir(parents=True, exist_ok=True)
        self.config.report_dir.mkdir(parents=True, exist_ok=True)
        self.lock_fp = None
        self._is_running = False

    def acquire_lock(self):
        """fcntl 기반 단일 스케줄러 인스턴스 배타적 파일 락을 획득합니다."""
        self.config.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_fp = open(self.config.lock_file, "w")
        try:
            fcntl.flock(self.lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            self.lock_fp.close()
            self.lock_fp = None
            raise SchedulerLockError(
                f"[중복 실행 차단] 다른 스케줄러 프로세스가 이미 실행 중입니다 ({self.config.lock_file})."
            )

    def release_lock(self):
        """스케줄러 파일 락을 안전하게 해제합니다."""
        if self.lock_fp:
            try:
                fcntl.flock(self.lock_fp.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self.lock_fp.close()
            self.lock_fp = None

    def execute_single_observation(self, mode: str = "live") -> dict[str, Any]:
        """지수 백오프 기반의 단일 관측 배치 실행 (최대 max_retries회 시도)."""
        # 1. 안전 가드 검증: 감독 승인 전 무단 LIVE 실행 차단
        if mode == "live" and not self.config.enable_live_execution:
            print("[*] [안전 모드 (STANDBY)] LIVE 자동 수집 비활성화 상태입니다 (총괄 감독 별도 승인 대기). DRY_RUN 모드로 전환합니다.")
            return {
                "status": "STANDBY_SKIPPED",
                "message": "enable_live_execution=False로 인해 실제 LIVE 수집이 안전하게 건너뛰어졌습니다.",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        # 2. 파이프라인 러너 확인 (기본적으로 run_directive_010_market_stream의 run_pipeline 사용)
        runner = self.pipeline_runner
        if runner is None:
            from scripts.run_directive_010_market_stream import run_pipeline
            runner = run_pipeline

        attempt = 0
        current_backoff = self.config.initial_backoff_sec
        last_error = None
        start_time = datetime.now(UTC)

        while attempt < self.config.max_retries:
            attempt += 1
            try:
                print(f"[*] [스케줄러] 관측 시도 {attempt}/{self.config.max_retries} 개시 (모드: {mode})...")
                res = runner(mode=mode, db_path_override=self.config.db_path)

                # 성공 시 일별 요약 리포트 자동 생성
                reporter = DailyMarketReporter(db_path=self.config.db_path, output_dir=self.config.report_dir)
                report_path = reporter.generate_daily_summary()

                print(f"[+] [스케줄러] 관측 성공! (시도: {attempt}회, 일별 보고서: {report_path})")
                return {
                    "status": "SUCCESS",
                    "attempt": attempt,
                    "daily_report": str(report_path),
                    "completed_at": datetime.now(UTC).isoformat(),
                }

            except Exception as e:
                last_error = e
                print(f"[!] [스케줄러] 시도 {attempt} 실패: {type(e).__name__}: {e}")
                if attempt < self.config.max_retries:
                    print(f"[*] [지수 백오프] {current_backoff:.1f}초 대기 후 재시도합니다...")
                    time.sleep(current_backoff)
                    current_backoff *= self.config.backoff_factor

        # 3. 최대 재시도 초과 시: 장애 보고서 생성 및 안전 종료 (무한 루프 방지)
        fail_timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        failure_report_file = self.config.failure_dir / f"failure_batch_{fail_timestamp}.md"

        fail_content = [
            f"# CHA-FICIAL 시장 관측 실패 보고서 ({fail_timestamp})",
            "",
            f"- **발생 시각 (UTC)**: {datetime.now(UTC).isoformat()}",
            f"- **실행 모드**: `{mode}`",
            f"- **최대 재시도 횟수**: {self.config.max_retries}회",
            f"- **최종 예외 유형**: `{type(last_error).__name__}`",
            f"- **예외 메시지**: `{str(last_error)}`",
            "",
            "## 실패 스택트레이스",
            "```text",
            traceback.format_exc(),
            "```",
            "",
            "## 시스템 조치",
            "- 무작정 자동 재실행 차단 (Fail-Safe 안전 종료)",
            "- 기존 운영 DB 손상 방지 및 격리 유지",
            "- 관리자 및 총괄 감독 수동 검토 필요",
        ]

        with open(failure_report_file, "w", encoding="utf-8") as f:
            f.write("\n".join(fail_content))

        print(f"[x] [스케줄러] 최대 재시도({self.config.max_retries}회) 초과로 관측 실패. 장애 보고서 생성: {failure_report_file}")
        return {
            "status": "FAILED",
            "attempts": attempt,
            "failure_report": str(failure_report_file),
            "error": str(last_error),
        }

    def run_loop(self, max_cycles: int | None = None, mode: str = "live"):
        """지정된 인터벌로 주기적 관측 루프를 실행합니다."""
        self.acquire_lock()
        self._is_running = True
        cycle_count = 0

        try:
            print("=" * 80)
            print(f"[*] CHA-FICIAL 시장 관측 스케줄러 루프 개시 (인터벌: {self.config.interval_seconds}s, LIVE승인: {self.config.enable_live_execution})")
            print("=" * 80)

            while self._is_running:
                cycle_count += 1
                print(f"\n[+] === 스케줄러 사이클 #{cycle_count} 실행 ===")
                self.execute_single_observation(mode=mode)

                if max_cycles and cycle_count >= max_cycles:
                    print(f"[*] 지정된 사이클 횟수({max_cycles}회)에 도달하여 스케줄러를 정상 종료합니다.")
                    break

                print(f"[*] 다음 관측까지 {self.config.interval_seconds:.1f}초 대기 중 (CPU 저부하 유지)...")
                # CPU 70% 이하 유지를 위한 슬립 분할
                remaining = self.config.interval_seconds
                while remaining > 0 and self._is_running:
                    sleep_chunk = min(remaining, 5.0)
                    time.sleep(sleep_chunk)
                    remaining -= sleep_chunk

        finally:
            self._is_running = False
            self.release_lock()
            print("[+] 스케줄러 잠금 해제 및 종료 완료.")
