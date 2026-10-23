"""CHA-FICIAL 주기적 LIVE 시장 관측 스케줄러 모듈 (DIRECTIVE 013-B 커밋 경계 안전성 완비).

[013-B 핵심 강화 내역]
1. 커밋 경계 안전성 (Commit Boundary Safety):
   - 러너 호출 전 DB의 최신 batch_id 목록 및 배치 수를 기록.
   - 러너 실행 도중 또는 직후 예외가 발생하더라도, DB에 이미 신규 배치가 커밋되었는지 즉시 검사.
   - 이미 커밋이 완료된 상태에서 사후 예외(리포트 생성, 로깅 등)가 발생한 경우,
     절대 파이프라인을 재실행하지 않고 'ALREADY_COMMITTED_POST_ERROR'로 안전 격리.
2. 재시도 예외 범위 정밀화 (Strict Network-Only Transient Errors):
   - OSError 전체 재시도 차단!
   - ConnectionError, TimeoutError, 또는 네트워크 소켓 관련 errno (ECONNRESET, ETIMEDOUT, ENETUNREACH, EHOSTUNREACH)만 선별 재시도.
   - PermissionError, FileNotFoundError, 디스크 오류, DB 파일 락 및 스키마/무결성 에러는 즉시 중단 (Fail-Fast).
3. 치명적 장애 시 스케줄러 루프 안전 종료 (Fail-Safe Break).
4. 일별 보고서 원자적 생성 및 장애 보고서 배타적 생성 (동일 시점 덮어쓰기 원천 차단).
"""

import dataclasses
from datetime import UTC, datetime
import errno
import fcntl
import http.client
import json
import logging
import os
from pathlib import Path
import sqlite3
import time
import traceback
from typing import Any, Callable
import urllib.error
import uuid

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from chaficial.models import Listing, ListingSnapshot, PriceEvent, BatchAuditLog
from chaficial.tracker.daily_reporter import DailyMarketReporter

logger = logging.getLogger("chaficial.scheduler")

# DIRECTIVE 010-H: 공식 운영 DB 경로 (REPLAY 격리 보호용)
OFFICIAL_OPERATIONAL_DB_PATH = Path("data/chaficial_market_timeseries.db").resolve()

# 네트워크 관련 명시적 errno 집합
NETWORK_ERRNOS = {
    errno.ECONNRESET,
    errno.ECONNREFUSED,
    errno.ETIMEDOUT,
    errno.ENETUNREACH,
    errno.EHOSTUNREACH,
    errno.ENETDOWN,
}


def is_transient_network_error(exc: Exception) -> bool:
    """오직 네트워크 일시적 장애인 경우에만 True를 반환합니다 (013-B 엄격 검증).

    디스크 용량 부족, 파일 권한, DB 에러, 스키마 에러는 절대 재시도하지 않습니다.
    """
    # 1. 파일/디스크/권한 관련 예외는 절대 재시도 금지
    if isinstance(exc, (PermissionError, FileNotFoundError, IsADirectoryError)):
        return False

    # 2. SQLite / 데이터베이스 관련 예외는 절대 재시도 금지
    if isinstance(exc, (sqlite3.Error,)):
        return False

    # 3. 명시적 네트워크/타임아웃 예외 확인
    if isinstance(exc, (ConnectionError, TimeoutError, http.client.RemoteDisconnected)):
        return True

    if isinstance(exc, urllib.error.URLError) and not isinstance(exc, urllib.error.HTTPError):
        return True

    # 4. OSError인 경우 네트워크 소켓 errno만 허용
    if isinstance(exc, OSError):
        if getattr(exc, "errno", None) in NETWORK_ERRNOS:
            return True

    return False


class SchedulerLockError(Exception):
    """스케줄러 중복 실행 방지 잠금 획득 실패 예외."""


class SchedulerConfigError(Exception):
    """스케줄러 설정값 유효성 검증 실패 예외."""


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

    def validate(self, mode: str = "live"):
        """설정값 유효성 검증 (DIRECTIVE 013-A)."""
        if self.interval_seconds <= 0:
            raise SchedulerConfigError(f"interval_seconds는 0보다 커야 합니다: {self.interval_seconds}")
        if self.max_retries < 1:
            raise SchedulerConfigError(f"max_retries는 1 이상이어야 합니다: {self.max_retries}")
        if self.initial_backoff_sec < 0:
            raise SchedulerConfigError(f"initial_backoff_sec는 0 이상이어야 합니다: {self.initial_backoff_sec}")
        if self.backoff_factor < 1.0:
            raise SchedulerConfigError(f"backoff_factor는 1.0 이상이어야 합니다: {self.backoff_factor}")

        # DIRECTIVE 010-H: REPLAY 모드 시 운영 DB 대상 차단
        if mode == "replay" and self.db_path.resolve() == OFFICIAL_OPERATIONAL_DB_PATH:
            raise SchedulerConfigError(
                f"[REPLAY 격리 위반] 운영 DB({OFFICIAL_OPERATIONAL_DB_PATH})는 REPLAY 모드의 대상이 될 수 없습니다."
            )


class MarketObservationScheduler:
    """주기적 시장 관측 자율 운영 스케줄러 (DIRECTIVE 013-B)."""

    def __init__(
        self,
        config: SchedulerConfig | None = None,
        pipeline_runner: Callable[..., Any] | None = None,
    ):
        self.config = config or SchedulerConfig()
        self.config.validate()
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

    def _get_committed_batch_ids(self) -> set[str]:
        """대상 DB에 이미 커밋 완료된 batch_id 목록을 조회합니다."""
        if not self.config.db_path.exists():
            return set()
        try:
            engine = create_engine(f"sqlite:///{self.config.db_path}")
            with Session(engine) as session:
                return set(session.execute(select(BatchAuditLog.batch_id)).scalars().all())
        except Exception:
            return set()

    def execute_single_observation(self, mode: str = "live") -> dict[str, Any]:
        """단일 관측 배치 실행 (013-B: 커밋 경계 안전성 및 네트워크 전용 재시도)."""
        self.config.validate(mode=mode)

        # 1. 안전 가드 검증: 감독 승인 전 무단 LIVE 실행 차단
        if mode == "live" and not self.config.enable_live_execution:
            print("[*] [안전 모드 (STANDBY)] LIVE 자동 수집 비활성화 상태입니다 (총괄 감독 별도 승인 대기).")
            return {
                "collection_status": "STANDBY_SKIPPED",
                "report_status": "SKIPPED",
                "status": "STANDBY_SKIPPED",
                "message": "enable_live_execution=False로 인해 실제 LIVE 수집이 안전하게 건너뛰어졌습니다.",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        runner = self.pipeline_runner
        if runner is None:
            from scripts.run_directive_010_market_stream import run_pipeline
            runner = run_pipeline

        # 2. 실행 전 DB의 기 커밋된 배치 목록 확인 (커밋 경계 안전성)
        pre_committed_batches = self._get_committed_batch_ids()

        attempt = 0
        current_backoff = self.config.initial_backoff_sec
        last_error = None
        collection_result = None

        # ----------------------------------------------------------------------
        # [단계 A] 실시간 수집 및 DB 적재 단계 (엄격한 커밋 경계 안전성)
        # ----------------------------------------------------------------------
        while attempt < self.config.max_retries:
            attempt += 1
            try:
                print(f"[*] [스케줄러] 관측 시도 {attempt}/{self.config.max_retries} 개시 (모드: {mode})...")
                collection_result = runner(mode=mode, db_path_override=self.config.db_path)
                print(f"[+] [스케줄러] 관측 및 DB 커밋 성공! (시도 {attempt}회)")
                break

            except Exception as e:
                last_error = e

                # 013-B 핵심: 예외 발생 시 DB에 이미 신규 배치가 커밋되었는지 전수 확인!
                post_committed_batches = self._get_committed_batch_ids()
                new_batches = post_committed_batches - pre_committed_batches

                if new_batches:
                    # DB 커밋은 이미 성공했는데 사후 로깅/리턴 과정에서 예외가 난 경우
                    print(f"[!] [커밋 경계 감지] DB 커밋은 이미 성공했으나 사후 예외 발생 (신규 배치: {new_batches}).")
                    print("[!] [중복 수집 방지] 동일 배치의 중복 적재를 막기 위해 파이프라인 재실행을 차단합니다.")
                    collection_result = {"status": "COMMITTED_WITH_POST_ERROR", "batches": list(new_batches)}
                    break

                # 013-B: 엄격한 네트워크 일시적 예외 검증 (디스크/권한/DB 에러는 즉시 Fail-Fast)
                is_transient = is_transient_network_error(e)
                print(f"[!] [스케줄러] 시도 {attempt} 실패: {type(e).__name__}: {e} (네트워크재시도가능: {is_transient})")

                if not is_transient:
                    print(f"[!] [영구적 장애] {type(e).__name__}은 네트워크 오류가 아니므로 즉시 중단(Fail-Fast)합니다.")
                    break

                if attempt < self.config.max_retries:
                    print(f"[*] [지수 백오프] {current_backoff:.1f}초 대기 후 재시도합니다...")
                    time.sleep(current_backoff)
                    current_backoff *= self.config.backoff_factor

        # 수집 자체가 실패한 경우 -> 장애 보고서 발행 및 FAILED 반환
        if collection_result is None:
            fail_report_path = self._write_failure_report(mode=mode, attempts=attempt, error=last_error)
            return {
                "collection_status": "FAILED",
                "report_status": "SKIPPED",
                "status": "FAILED",
                "attempts": attempt,
                "failure_report": str(fail_report_path),
                "error_type": type(last_error).__name__ if last_error else "Unknown",
                "error": f"{type(last_error).__name__}: {last_error}" if last_error else "Unknown",
            }

        # ----------------------------------------------------------------------
        # [단계 B] 일별 요약 보고서 생성 단계 (수집 성공 후 독립 실행)
        # ----------------------------------------------------------------------
        report_status = "SUCCESS"
        daily_report_path = None
        report_error_msg = None

        try:
            reporter = DailyMarketReporter(db_path=self.config.db_path, output_dir=self.config.report_dir)
            daily_report_path = str(reporter.generate_daily_summary())
            print(f"[+] [스케줄러] 일별 보고서 자동 발행 완료: {daily_report_path}")
        except Exception as report_err:
            report_status = "REPORT_FAILED"
            report_error_msg = f"{type(report_err).__name__}: {report_err}"
            print(f"[!] [경고] 수집은 성공했으나 일별 보고서 생성 실패 (수집 재실행 안함): {report_error_msg}")

        return {
            "collection_status": "SUCCESS",
            "report_status": report_status,
            "status": "SUCCESS" if report_status == "SUCCESS" else "PARTIAL_SUCCESS",
            "attempts": attempt,
            "daily_report": daily_report_path,
            "report_error": report_error_msg,
            "completed_at": datetime.now(UTC).isoformat(),
        }

    def _write_failure_report(self, mode: str, attempts: int, error: Exception | None) -> Path:
        """장애 보고서를 마이크로초와 UUID로 배타적 생성합니다 (덮어쓰기 방지)."""
        now_dt = datetime.now(UTC)
        timestamp_str = now_dt.strftime("%Y%m%d_%H%M%S_%f")
        unique_suffix = uuid.uuid4().hex[:6]
        report_file = self.config.failure_dir / f"failure_batch_{timestamp_str}_{unique_suffix}.md"

        content = [
            f"# CHA-FICIAL 시장 관측 실패 보고서 ({timestamp_str})",
            "",
            f"- **발생 시각 (UTC)**: {now_dt.isoformat()}",
            f"- **실행 모드**: `{mode}`",
            f"- **시도 횟수**: {attempts}회 / 최대 {self.config.max_retries}회",
            f"- **예외 유형**: `{type(error).__name__ if error else 'Unknown'}`",
            f"- **예외 메시지**: `{str(error)}`",
            "",
            "## 실패 스택트레이스",
            "```text",
            traceback.format_exc(),
            "```",
            "",
            "## 시스템 조치",
            "- **수집 안전 종료 (Fail-Safe Break)**: 동일 배치 무작정 재실행 차단",
            "- **커밋 경계 보호**: 미커밋 상태 확인 완료",
            "- **운영자 감사**: 수동 확인 후 재기동 필요",
        ]

        with open(report_file, "x", encoding="utf-8") as f:
            f.write("\n".join(content))

        print(f"[x] 장애 보고서 배타적 생성 완료: {report_file}")
        return report_file

    def run_loop(self, max_cycles: int | None = None, mode: str = "live"):
        """주기적 관측 루프 (013-A: 치명적 장애 시 루프 안전 종료)."""
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
                res = self.execute_single_observation(mode=mode)

                if res.get("collection_status") == "FAILED":
                    print("[!] [치명적 장애] 수집 실패로 인해 스케줄러 루프를 안전 종료합니다 (Fail-Safe Break).")
                    break

                if max_cycles and cycle_count >= max_cycles:
                    print(f"[*] 지정된 사이클 횟수({max_cycles}회)에 도달하여 스케줄러를 정상 종료합니다.")
                    break

                print(f"[*] 다음 관측까지 {self.config.interval_seconds:.1f}초 대기 중 (CPU 저부하 유지)...")
                remaining = self.config.interval_seconds
                while remaining > 0 and self._is_running:
                    sleep_chunk = min(remaining, 5.0)
                    time.sleep(sleep_chunk)
                    remaining -= sleep_chunk

        finally:
            self._is_running = False
            self.release_lock()
            print("[+] 스케줄러 잠금 해제 및 종료 완료.")
