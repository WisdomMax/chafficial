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
from datetime import UTC, date, datetime, timedelta
import errno
import fcntl
import hashlib
import http.client
import json
import logging
import os
from pathlib import Path
import re
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
    """커밋 상태 조회 실패 또는 배치 감사 계약 불일치로 커밋 여부를 확정할 수 없을 때 발생하는 예외."""


class LiveExecutionNotAuthorizedError(Exception):
    """LIVE 관측 실행이 총괄 감독/운영자에 의해 명시적으로 승인되지 않았을 때 발생하는 예외 (Fail-Closed)."""


# 013-F: 기존 1~3차 레거시 배치 식별자 (과거 커밋 보존용 호환성 허용 목록)
LEGACY_BATCH_IDS = {
    "ENCAR_CN7_LIVE_20261021_01",
    "ENCAR_CN7_LIVE_20261021_120825",
    "ENCAR_CN7_LIVE_20261024_030446_518b4987e3b2",
}

DEFAULT_AUTH_FILE_PATH = Path("data/.live_authorization.json")
MAX_AUTH_VALIDITY_DAYS = 7.0  # 과도하게 긴 승인 방지용 최대 유효기간 (7일)


def verify_live_authorization(auth_file: Path | None) -> tuple[bool, str]:
    """운영자 로컬 활성화 승인 파일의 무결성과 유효기간을 엄격히 검증합니다 (013-G).

    [원칙]
    - 이 검증은 단일 운영자 환경에서 실수에 의한 LIVE 실행을 방지하기 위한 로컬 안전 가드입니다.
    - 소스 코드에 공개된 고정 토큰이나 기본 정답은 일체 존재하지 않습니다.
    - 파일 부재, 심볼릭 링크, 만료, 필드 누락, 과도한 기간(7일 초과) 시 무조건 거부 (Fail-Closed).
    - 본 파일의 존재는 최종 승인 행위를 대신하지 않으며 운영자의 직접 생성이 요구됩니다.
    """
    if not auth_file:
        return False, "운영 승인 파일 경로가 지정되지 않았습니다"

    # 심볼릭 링크 및 비정상 파일 차단
    if auth_file.is_symlink():
        return False, f"보안 위반: 심볼릭 링크 파일은 승인 파일로 사용할 수 없습니다 ({auth_file})"

    if not auth_file.exists():
        return False, f"운영 승인 파일 부재: {auth_file}"

    if not auth_file.is_file():
        return False, f"운영 승인 파일이 일반 파일이 아닙니다: {auth_file}"

    try:
        with open(auth_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return False, "운영 승인 파일 형식 오류 (JSON 객체여야 함)"

        # is_approved는 정확히 JSON boolean True여야 함
        is_app = data.get("is_approved")
        if is_app is not True or not isinstance(is_app, bool):
            return False, "운영 승인 플래그(is_approved)가 boolean true가 아닙니다"

        # 승인 주체(operator) 검증
        approved_by = data.get("approved_by")
        if not isinstance(approved_by, str) or not approved_by.strip():
            return False, "운영 승인 주체(approved_by) 누락 또는 유효하지 않은 문자열"

        # 만료일자(UTC 시간대 필수) 검증
        expires_at_str = data.get("expires_at")
        if not isinstance(expires_at_str, str) or not expires_at_str.strip():
            return False, "운영 승인 만료일자(expires_at) 누락"

        expires_at = datetime.fromisoformat(expires_at_str)
        if expires_at.tzinfo is None:
            return False, "운영 승인 만료일자에 시간대(Timezone/UTC) 정보가 누락되었습니다"

        now_utc = datetime.now(UTC)
        if now_utc > expires_at:
            return False, f"운영 승인 유효기간 만료됨 (만료일자: {expires_at.isoformat()})"

        # 과도하게 긴 승인 기간(7일 초과) 거부
        if (expires_at - now_utc) > timedelta(days=MAX_AUTH_VALIDITY_DAYS):
            return False, f"과도하게 긴 승인 기간 거부 (최대 {MAX_AUTH_VALIDITY_DAYS}일 허용, 요청: {(expires_at - now_utc).days}일)"

        return True, f"유효한 로컬 운영 승인 확인 (운영자: {approved_by}, 만료: {expires_at.isoformat()})"
    except Exception as read_err:
        return False, f"운영 승인 파일 읽기/검증 실패: {read_err}"


@dataclasses.dataclass
class SchedulerConfig:
    """스케줄러 설정 데이터클래스 (013-F: 로컬 분리 운영 승인 체계)."""

    interval_seconds: float = 86400.0  # 기본: 24시간
    max_retries: int = 3               # 최대 재시도 횟수
    initial_backoff_sec: float = 5.0   # 1차 재시도 대기 시간 (초)
    backoff_factor: float = 2.0        # 지수 증가 배수
    enable_live_execution: bool = False  # 개발/실행 플래그: LIVE 시도 의도 여부
    auth_file_path: Path = DEFAULT_AUTH_FILE_PATH  # 로컬 운영 승인 파일 경로 (Git 비추적)
    db_path: Path = Path("data/chaficial_market_timeseries.db")
    lock_file: Path = Path("data/.scheduler.lock")
    report_dir: Path = Path("reports/daily_summaries")
    failure_dir: Path = Path("reports/failures")

    def validate(self, mode: str = "live"):
        """설정값 유효성 검증 (013-F: LIVE 운영 승인 파일 강제)."""
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

        # 013-F [지침 1]: LIVE 실행 플래그가 켜진 경우, 소스코드 외부에 분리된 로컬 승인 파일 검증 필수
        if mode == "live" and self.enable_live_execution:
            is_valid, reason = verify_live_authorization(self.auth_file_path)
            if not is_valid:
                raise LiveExecutionNotAuthorizedError(
                    f"LIVE 관측 실행 거부: 총괄 감독의 유효한 로컬 운영 승인이 확인되지 않았습니다 ({reason}). (Fail-Closed)"
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

    def check_batch_committed(
        self,
        batch_id: str,
        expected_platform: str = "ENCAR",
        expected_scope_prefix: str = "ENCAR:",
        is_legacy: bool | None = None,
    ) -> str:
        """지정된 batch_id의 DB 커밋 여부 및 엄격한 감사 계약을 종합 검증합니다 (013-F).

        [신규 LIVE 배치 계약 (is_legacy=False)]
          - notes(JSON) 필수: raw_file_path, raw_file_sha256, first_seen_count, re_observed_count 전수 필수.
          - 원천 파일 실존 및 SHA-256 1:1 대조 필수 (하나라도 누락/불일치 시 즉시 CommitStatusUnknownError).
          - first_seen_count + re_observed_count == record_count 완벽 일치 필수.
        [레거시 배치 호환 (is_legacy=True 또는 LEGACY_BATCH_IDS 포함)]
          - 기존 1~3차 관측 데이터의 보존 및 호환성 유지.
        """
        if not self.config.db_path.exists():
            raise CommitStatusUnknownError(
                f"대상 DB 파일이 존재하지 않아 커밋 여부 확인 불가: {self.config.db_path}"
            )

        # 013-G: 레거시 판정 우회 원천 차단
        # 오직 LEGACY_BATCH_IDS(1~3차 배치 3개)에 등록된 배치만 레거시 검증이 허용됨.
        # 신규 배치가 is_legacy=True를 전달하여 우회를 시도할 경우 즉시 거부!
        if is_legacy is True and batch_id not in LEGACY_BATCH_IDS:
            raise CommitStatusUnknownError(
                f"보안 위반: 신규 배치({batch_id})는 레거시 검증(is_legacy=True)으로 우회할 수 없습니다 (013-G)."
            )

        is_legacy_batch = (batch_id in LEGACY_BATCH_IDS)

        try:
            engine = create_engine(f"sqlite:///{self.config.db_path}")
            with Session(engine) as session:
                logs = session.execute(
                    select(BatchAuditLog).where(BatchAuditLog.batch_id == batch_id)
                ).scalars().all()

                if not logs:
                    return "NOT_COMMITTED"

                if len(logs) > 1:
                    raise CommitStatusUnknownError(
                        f"배치 ID 중복 감지: 배치 식별자 {batch_id} 레코드가 {len(logs)}건 발견되었습니다."
                    )

                log = logs[0]

                # 기본 필드 무결성 검증 (정수형 엄격 검증, bool 제외)
                if log.record_count is None or isinstance(log.record_count, bool) or log.record_count < 0:
                    raise CommitStatusUnknownError(
                        f"배치 감사 로그 무결성 위반: record_count가 유효하지 않습니다 ({log.record_count})"
                    )

                if log.source_platform != expected_platform:
                    raise CommitStatusUnknownError(
                        f"배치 데이터 기원 불일치: 기대 플랫폼={expected_platform}, 실제 플랫폼={log.source_platform}"
                    )

                if not log.search_scope or not (
                    log.search_scope.startswith(expected_scope_prefix)
                    or "아반떼" in log.search_scope
                ):
                    raise CommitStatusUnknownError(
                        f"배치 검색 범위 불일치: scope={log.search_scope}"
                    )

                # ------------------------------------------------------------------
                # 신규 스케줄러 LIVE 배치: 엄격한 필수 감사 메타데이터 계약 강제 (013-G)
                # ------------------------------------------------------------------
                if not is_legacy_batch:
                    if not log.notes:
                        raise CommitStatusUnknownError(
                            f"신규 배치 감사 계약 위반: 배치 {batch_id}의 필수 감사 메타데이터(notes)가 누락되었습니다."
                        )

                    try:
                        notes_data = json.loads(log.notes)
                    except Exception as json_err:
                        raise CommitStatusUnknownError(
                            f"신규 배치 감사 계약 위반: notes가 유효한 JSON 형식이 아닙니다 ({json_err})"
                        )

                    if not isinstance(notes_data, dict):
                        raise CommitStatusUnknownError("신규 배치 감사 계약 위반: notes는 JSON 객체여야 합니다.")

                    # 필수 4대 메타데이터 키 존재 검증
                    required_keys = ["raw_file_path", "raw_file_sha256", "first_seen_count", "re_observed_count"]
                    for k in required_keys:
                        if k not in notes_data or notes_data[k] is None:
                            raise CommitStatusUnknownError(
                                f"신규 배치 필수 감사 메타데이터 누락: 키 '{k}'가 존재하지 않습니다."
                            )

                    # 013-G: 메타데이터 타입 엄격 검증 (first_seen, re_observed 정수형, bool 제외)
                    first_seen = notes_data["first_seen_count"]
                    re_observed = notes_data["re_observed_count"]
                    raw_path_val = notes_data["raw_file_path"]
                    raw_sha_val = notes_data["raw_file_sha256"]

                    if not isinstance(first_seen, int) or isinstance(first_seen, bool) or first_seen < 0:
                        raise CommitStatusUnknownError(
                            f"first_seen_count는 0 이상의 정수여야 합니다 (실제: {type(first_seen).__name__}={first_seen})"
                        )
                    if not isinstance(re_observed, int) or isinstance(re_observed, bool) or re_observed < 0:
                        raise CommitStatusUnknownError(
                            f"re_observed_count는 0 이상의 정수여야 합니다 (실제: {type(re_observed).__name__}={re_observed})"
                        )

                    # 문자열 및 SHA-256 64자리 16진수 검증
                    if not isinstance(raw_path_val, str) or not raw_path_val.strip():
                        raise CommitStatusUnknownError("raw_file_path는 비어있지 않은 문자열이어야 합니다")
                    if not isinstance(raw_sha_val, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", raw_sha_val):
                        raise CommitStatusUnknownError(
                            f"raw_file_sha256은 64자리 16진수 해시 문자열이어야 합니다 (실제: {raw_sha_val})"
                        )

                    # 원천 파일 실존 검증
                    raw_path = Path(raw_path_val)
                    if not raw_path.exists():
                        raise CommitStatusUnknownError(
                            f"배치 원천 파일 소실 감지: {raw_path} 파일이 디스크에 존재하지 않습니다."
                        )

                    # 원천 파일 SHA-256 1:1 대조 검증
                    hasher = hashlib.sha256()
                    with open(raw_path, "rb") as rf:
                        while chunk := rf.read(65536):
                            hasher.update(chunk)
                    actual_sha = hasher.hexdigest()
                    if actual_sha != raw_sha_val.lower():
                        raise CommitStatusUnknownError(
                            f"배치 원천 파일 SHA-256 변조 감지: 기대={raw_sha_val}, 실제={actual_sha}"
                        )

                    # 수집 수량 일치 검증: record_count == first_seen + re_observed
                    expected_count = first_seen + re_observed
                    if expected_count != log.record_count:
                        raise CommitStatusUnknownError(
                            f"배치 적재 수량 불일치: record_count={log.record_count}, "
                            f"first_seen({first_seen}) + re_observed({re_observed}) = {expected_count}"
                        )

                return "COMMITTED"
        except CommitStatusUnknownError:
            raise
        except Exception as query_err:
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

    def recover_daily_report(self, target_date_str: str | None = None) -> Path:
        """수집 결과는 그대로 보존하고 실패한 일별 보고서만 단독으로 안전하게 재생성/복구합니다 (013-E)."""
        print(f"[*] [스케줄러 복구] {target_date_str or '당일'} 일별 요약 보고서 단독 복구 시작 (수집 재실행 없음)...")
        reporter = DailyMarketReporter(db_path=self.config.db_path, output_dir=self.config.report_dir)
        return reporter.generate_daily_summary(target_date_str=target_date_str)

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

                # 013-D/E: FAILED, COMMIT_STATUS_UNKNOWN, COMMITTED_WITH_POST_ERROR 및 PARTIAL_SUCCESS 발생 시 즉시 루프 안전 중단
                col_status = res.get("collection_status")
                overall_status = res.get("status")
                if (
                    col_status in ("FAILED", "COMMIT_STATUS_UNKNOWN", "COMMITTED_WITH_POST_ERROR")
                    or overall_status == "PARTIAL_SUCCESS"
                ):
                    print(
                        f"[!] [안전 차단 (수집:{col_status}, 전체:{overall_status})] "
                        "치명적 오류 또는 운영 보고 실패로 스케줄러 루프를 즉시 안전 종료합니다 (Fail-Safe Break)."
                    )
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
