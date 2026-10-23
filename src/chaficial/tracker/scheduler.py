"""CHA-FICIAL 주기적 LIVE 시장 관측 스케줄러 모듈 (DIRECTIVE 013-C 최종 안전 감사 규격).

[013-C 핵심 원칙]
1. 커밋 조회 실패 시 Fail-Closed:
   - DB 조회 에러/잠금으로 커밋 여부 확인이 불가능하면 절대 재수집하지 않고 'COMMIT_STATUS_UNKNOWN'으로 즉시 안전 종료.
2. 실행별 고유 배치 ID(batch_id) 사전 발급 및 1:1 귀속성 검증:
   - 스케줄러가 실행 전 고유 batch_id를 발급하고 러너에 전달.
   - 사후 예외 발생 시 오직 자신이 발급한 batch_id가 커밋되었는지만 1:1 단독 검사. 타 프로세스의 배치는 무시.
3. 5대 상태 판정 체계:
   - RETRYABLE_FAILURE: 커밋 전 일시적 네트워크 장애 (제한적 재시도 허용)
   - COMMITTED_WITH_POST_ERROR: 현재 batch_id 커밋 확인 후 사후 오류 (재수집 절대 금지)
   - COMMIT_STATUS_UNKNOWN: 커밋 여부 불명확 (재수집 절대 금지, Fail-Closed)
   - FAILED: 영구적 오류 / 최대 재시도 초과 (재수집 절대 금지)
   - PARTIAL_SUCCESS: 수집 성공, 보고서 실패 (재수집 절대 금지)
4. 네트워크 전용 재시도:
   - 디스크/권한/SQLite/스키마 에러는 즉시 중단 (Fail-Fast).
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

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from chaficial.models import BatchAuditLog
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
    """오직 네트워크 일시적 장애인 경우에만 True를 반환합니다 (013-B/C 엄격 검증).

    디스크 용량 부족, 파일 권한, DB 에러, 스키마 에러는 절대 재시도하지 않습니다.
    """
    if isinstance(exc, (PermissionError, FileNotFoundError, IsADirectoryError)):
        return False

    if isinstance(exc, (sqlite3.Error,)):
        return False

    if isinstance(exc, (ConnectionError, TimeoutError, http.client.RemoteDisconnected)):
        return True

    if isinstance(exc, urllib.error.URLError) and not isinstance(exc, urllib.error.HTTPError):
        return True

    if isinstance(exc, OSError):
        if getattr(exc, "errno", None) in NETWORK_ERRNOS:
            return True

    return False


class SchedulerLockError(Exception):
    """스케줄러 중복 실행 방지 잠금 획득 실패 예외."""


class SchedulerConfigError(Exception):
    """스케줄러 설정값 유효성 검증 실패 예외."""


class CommitStatusUnknownError(Exception):
    """커밋 상태 조회 실패로 커밋 여부를 확정할 수 없을 때 발생하는 예외."""


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
        """설정값 유효성 검증."""
        if self.interval_seconds <= 0:
            raise SchedulerConfigError(f"interval_seconds는 0보다 커야 합니다: {self.interval_seconds}")
        if self.max_retries < 1:
            raise SchedulerConfigError(f"max_retries는 1 이상이어야 합니다: {self.max_retries}")
        if self.initial_backoff_sec < 0:
            raise SchedulerConfigError(f"initial_backoff_sec는 0 이상이어야 합니다: {self.initial_backoff_sec}")
        if self.backoff_factor < 1.0:
            raise SchedulerConfigError(f"backoff_factor는 1.0 이상이어야 합니다: {self.backoff_factor}")

        if mode == "replay" and self.db_path.resolve() == OFFICIAL_OPERATIONAL_DB_PATH:
            raise SchedulerConfigError(
                f"[REPLAY 격리 위반] 운영 DB({OFFICIAL_OPERATIONAL_DB_PATH})는 REPLAY 모드의 대상이 될 수 없습니다."
            )


class MarketObservationScheduler:
    """주기적 시장 관측 자율 운영 스케줄러 (DIRECTIVE 013-C)."""

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

    def check_batch_committed(self, batch_id: str) -> str:
        """지정된 batch_id가 대상 DB에 확실하게 커밋되었는지 검사합니다 (013-D Fail-Closed).

        반환값:
          - 'COMMITTED': 대상 배치가 DB에 확실하게 존재함.
          - 'NOT_COMMITTED': DB 조회가 정상 수행되었고 해당 배치가 없음.
        예외:
          - CommitStatusUnknownError: DB 파일 부재 또는 조회 실패로 확인 불가 시 발생.
        """
        if not self.config.db_path.exists():
            # 013-D: 대상 DB 파일이 없으면 미커밋으로 단정하지 않고 Fail-Closed
            raise CommitStatusUnknownError(
                f"대상 DB 파일이 존재하지 않아 커밋 여부 확인 불가: {self.config.db_path}"
            )

        try:
            engine = create_engine(f"sqlite:///{self.config.db_path}")
            with Session(engine) as session:
                log = session.execute(
                    select(BatchAuditLog).where(BatchAuditLog.batch_id == batch_id)
                ).scalars().first()
                return "COMMITTED" if log is not None else "NOT_COMMITTED"
        except Exception as query_err:
            # 013-D: 빈 결과를 반환하지 않고 반드시 예외 발생 (Fail-Closed)
            raise CommitStatusUnknownError(
                f"배치 {batch_id} 커밋 여부 확인 실패 (DB 조회 에러: {query_err})"
            ) from query_err

    def generate_batch_id(self, mode: str = "live") -> str:
        """실행별 고유 배치 ID를 사전 발급합니다 (013-C 배치 귀속성 보장)."""
        now_dt = datetime.now(UTC)
        timestamp_str = now_dt.strftime("%Y%m%d_%H%M%S")
        unique_hex = uuid.uuid4().hex[:12]
        prefix = "ENCAR_CN7_LIVE" if mode == "live" else "ENCAR_CN7_REPLAY"
        return f"{prefix}_{timestamp_str}_{unique_hex}"

    def execute_single_observation(self, mode: str = "live") -> dict[str, Any]:
        """단일 관측 배치 실행 (013-C: 커밋 불확실성 원천 차단 및 고유 배치 귀속성 검증)."""
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

        # 2. 실행별 고유 batch_id 사전 발급 (배치 귀속성 보장)
        current_batch_id = self.generate_batch_id(mode=mode)
        print(f"[*] [스케줄러] 013-D 고유 배치 ID 사전 발급 완료: {current_batch_id}")

        # 3. 러너의 batch_id 인자 지원 여부 사전 정적 검사 (inspect.signature)
        import inspect
        sig = inspect.signature(runner)
        has_batch_id_param = "batch_id" in sig.parameters or any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )

        if mode == "live" and not has_batch_id_param:
            raise SchedulerConfigError(
                f"[배치 귀속성 계약 위반] LIVE 러너({runner})는 batch_id 인자를 필수로 지원해야 합니다."
            )

        attempt = 0
        current_backoff = self.config.initial_backoff_sec
        last_error = None
        collection_result = None
        execution_outcome = "PENDING"

        # ----------------------------------------------------------------------
        # [단계 A] 실시간 수집 및 DB 적재 단계 (Fail-Closed 커밋 경계 검증)
        # ----------------------------------------------------------------------
        while attempt < self.config.max_retries:
            attempt += 1
            try:
                print(f"[*] [스케줄러] 관측 시도 {attempt}/{self.config.max_retries} 개시 (배치: {current_batch_id})...")
                # 013-D: 사전 정적 판별에 따라 단 1회만 정확히 호출 (TypeError 재호출 금지)
                if has_batch_id_param:
                    collection_result = runner(mode=mode, db_path_override=self.config.db_path, batch_id=current_batch_id)
                else:
                    collection_result = runner(mode=mode, db_path_override=self.config.db_path)

                execution_outcome = "SUCCESS"
                print(f"[+] [스케줄러] 관측 및 DB 커밋 성공! (시도 {attempt}회)")
                break

            except Exception as e:
                last_error = e

                # 013-C 핵심 1: 커밋 확인 조회 시도 (Fail-Closed)
                try:
                    commit_status = self.check_batch_committed(current_batch_id)
                except CommitStatusUnknownError as unknown_err:
                    # DB 조회 실패로 커밋 여부를 확정할 수 없음 -> 재수집 절대 금지!
                    print(f"[!] [치명적 불확실성] {unknown_err}")
                    print("[!] [Fail-Closed 차단] 커밋 여부가 불확실하므로 동일 배치의 중복 적재를 방지하기 위해 재수집을 영구 차단합니다.")
                    execution_outcome = "COMMIT_STATUS_UNKNOWN"
                    break

                # 013-C 핵심 2: 오직 자신이 발급한 current_batch_id가 커밋되었는지 검사
                if commit_status == "COMMITTED":
                    print(f"[!] [커밋 경계 감지] 현재 배치({current_batch_id})는 이미 DB 커밋 완료 후 사후 예외 발생.")
                    print("[!] [중복 수집 방지] 동일 배치의 중복 수집을 원천 차단하기 위해 파이프라인 재실행을 금지합니다.")
                    execution_outcome = "COMMITTED_WITH_POST_ERROR"
                    collection_result = {"status": "COMMITTED_WITH_POST_ERROR", "batch_id": current_batch_id}
                    break

                # 013-C 핵심 3: 커밋되지 않은 것이 확실할 때만 일시적 네트워크 예외 검증
                is_transient = is_transient_network_error(e)
                print(f"[!] [스케줄러] 시도 {attempt} 실패: {type(e).__name__}: {e} (네트워크재시도가능: {is_transient})")

                if not is_transient:
                    print(f"[!] [영구적 장애] {type(e).__name__}은 네트워크 오류가 아니므로 즉시 중단(Fail-Fast)합니다.")
                    execution_outcome = "FAILED"
                    break

                if attempt < self.config.max_retries:
                    print(f"[*] [지수 백오프] {current_backoff:.1f}초 대기 후 재시도합니다...")
                    time.sleep(current_backoff)
                    current_backoff *= self.config.backoff_factor
                else:
                    execution_outcome = "FAILED"

        # 3. 비정상 상황 처리 (수집 실패 / 커밋 불확실 / 사후 에러)
        if execution_outcome == "COMMIT_STATUS_UNKNOWN":
            fail_report_path = self._write_failure_report(
                mode=mode, attempts=attempt, error=last_error, batch_id=current_batch_id, notes="COMMIT_STATUS_UNKNOWN: 커밋 확인 실패로 인한 안전 중단"
            )
            return {
                "collection_status": "COMMIT_STATUS_UNKNOWN",
                "report_status": "SKIPPED",
                "status": "COMMIT_STATUS_UNKNOWN",
                "batch_id": current_batch_id,
                "attempts": attempt,
                "failure_report": str(fail_report_path),
                "error_type": "CommitStatusUnknownError",
                "error": f"커밋 상태 불확실: {last_error}",
            }

        if execution_outcome == "COMMITTED_WITH_POST_ERROR":
            fail_report_path = self._write_failure_report(
                mode=mode, attempts=attempt, error=last_error, batch_id=current_batch_id, notes="COMMITTED_WITH_POST_ERROR: 커밋 완료 후 사후 예외"
            )
            return {
                "collection_status": "COMMITTED_WITH_POST_ERROR",
                "report_status": "REPORT_FAILED",
                "status": "COMMITTED_WITH_POST_ERROR",
                "batch_id": current_batch_id,
                "attempts": attempt,
                "failure_report": str(fail_report_path),
                "error_type": type(last_error).__name__ if last_error else "Unknown",
                "error": str(last_error),
            }

        if collection_result is None or execution_outcome == "FAILED":
            fail_report_path = self._write_failure_report(
                mode=mode, attempts=attempt, error=last_error, batch_id=current_batch_id, notes="FAILED: 최대 재시도 초과 또는 영구적 예외"
            )
            return {
                "collection_status": "FAILED",
                "report_status": "SKIPPED",
                "status": "FAILED",
                "batch_id": current_batch_id,
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
            "batch_id": current_batch_id,
            "attempts": attempt,
            "daily_report": daily_report_path,
            "report_error": report_error_msg,
            "completed_at": datetime.now(UTC).isoformat(),
        }

    def _write_failure_report(
        self, mode: str, attempts: int, error: Exception | None, batch_id: str | None = None, notes: str | None = None
    ) -> Path:
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
            f"- **배치 식별자**: `{batch_id or 'N/A'}`",
            f"- **시도 횟수**: {attempts}회 / 최대 {self.config.max_retries}회",
            f"- **예외 유형**: `{type(error).__name__ if error else 'Unknown'}`",
            f"- **예외 메시지**: `{str(error)}`",
            f"- **감사 비고**: `{notes or 'None'}`",
            "",
            "## 실패 스택트레이스",
            "```text",
            traceback.format_exc(),
            "```",
            "",
            "## 시스템 조치",
            "- **수집 안전 종료 (Fail-Safe Break)**: 동일 배치 무작정 재실행 차단",
            "- **커밋 경계 보호**: 커밋 불확실 시 재수집 원천 금지 (Fail-Closed)",
            "- **운영자 감사**: 수동 확인 후 재기동 필요",
        ]

        with open(report_file, "x", encoding="utf-8") as f:
            f.write("\n".join(content))

        print(f"[x] 장애 보고서 배타적 생성 완료: {report_file}")
        return report_file

    def run_loop(self, max_cycles: int | None = None, mode: str = "live"):
        """주기적 관측 루프 (013-C: 치명적 장애 또는 커밋 불확실 시 루프 즉시 안전 종료)."""
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

                # 013-D: FAILED, COMMIT_STATUS_UNKNOWN, COMMITTED_WITH_POST_ERROR 발생 시 즉시 루프 안전 중단
                col_status = res.get("collection_status")
                if col_status in ("FAILED", "COMMIT_STATUS_UNKNOWN", "COMMITTED_WITH_POST_ERROR"):
                    print(f"[!] [치명적 장애 ({col_status})] 안전을 위해 스케줄러 루프를 즉시 종료합니다 (Fail-Safe Break).")
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
