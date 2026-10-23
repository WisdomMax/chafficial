"""CHA-FICIAL DIRECTIVE 013-A 스케줄러 및 운영체계 강화 독립 테스트 스위트.

1. 안전 가드 (STANDBY): 감독 승인 전 무단 LIVE 실행 차단 검증
2. 프로세스 실행 잠금: 중복 스케줄러 기동 100% 차단 검증
3. 일시적 네트워크 장애 지수 백오프: 2회 실패 후 3회차 성공 복구 검증
4. 영구적 장애 즉시 중단 (Fail-Fast): 비네트워크 예외는 재시도 없이 즉시 중단 검증
5. 수집 성공과 보고서 실패의 엄격한 분리: 보고서 실패 시 LIVE를 재실행하지 않고 1회 실행 보장 검증
6. 치명적 수집 실패 시 스케줄러 루프 안전 종료 (Fail-Safe Break) 검증
7. 스케줄러 설정값 검증 (0 이하 인터벌, REPLAY 모드 운영 DB 차단)
8. 장애 보고서 배타적 생성 (동일 시점 덮어쓰기 원천 방지)
9. KST 자정 전후(UTC+9) 날짜 변환 경계치 검증
10. 일별 마크다운 요약 리포터 원자적 생성 및 메트릭 검증
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import time
import pytest
from sqlalchemy import create_engine

import json
from chaficial.database.base import Base
from chaficial.tracker.daily_reporter import DailyMarketReporter, to_kst_date_str
from chaficial.tracker.scheduler import (
    DEFAULT_AUTH_FILE_PATH,
    LEGACY_BATCH_IDS,
    LiveExecutionNotAuthorizedError,
    MarketObservationScheduler,
    SchedulerConfig,
    SchedulerConfigError,
    SchedulerLockError,
    verify_live_authorization,
)


def create_test_auth_file(
    target_path: Path,
    is_approved: bool = True,
    expired: bool = False,
    days_valid: float = 1.0,
    approved_by: str = "LOCAL_OPERATOR_TEST",
) -> Path:
    """테스트 더블 전용 로컬 승인 파일 생성 헬퍼 (013-G)."""
    expires = datetime.now(UTC) + (timedelta(days=-1) if expired else timedelta(days=days_valid))
    payload = {
        "is_approved": is_approved,
        "approved_by": approved_by,
        "expires_at": expires.isoformat(),
    }
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(payload), encoding="utf-8")
    return target_path


def make_live_config(**kwargs):
    """테스트 더블 전용 LIVE 승인 설정 헬퍼 (013-I 로컬 분리 운영 승인 및 원천 경로 격리)."""
    if "db_path" in kwargs and kwargs["db_path"]:
        base_dir = kwargs["db_path"].parent
        if "auth_file_path" not in kwargs:
            auth_file = base_dir / ".test_live_auth.json"
            create_test_auth_file(auth_file, is_approved=True, expired=False)
            kwargs["auth_file_path"] = auth_file
        if "raw_observations_dir" not in kwargs:
            raw_obs_dir = base_dir / "raw_observations"
            raw_obs_dir.mkdir(parents=True, exist_ok=True)
            kwargs["raw_observations_dir"] = raw_obs_dir
    else:
        if "auth_file_path" not in kwargs:
            auth_file = Path("/tmp/.test_live_auth.json")
            create_test_auth_file(auth_file, is_approved=True, expired=False)
            kwargs["auth_file_path"] = auth_file

    defaults = {
        "enable_live_execution": True,
    }
    defaults.update(kwargs)
    return SchedulerConfig(**defaults)


def test_scheduler_safety_guard_standby_mode(tmp_path):
    """지침 1: enable_live_execution=False 상태에서 LIVE 수집 시도 시 STANDBY로 안전 건너뜀 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_lock = tmp_path / ".test_scheduler.lock"

    config = SchedulerConfig(
        enable_live_execution=False,  # 안전 모드
        db_path=dummy_db,
        lock_file=dummy_lock,
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    runner_called = False
    def mock_runner(*args, **kwargs):
        nonlocal runner_called
        runner_called = True
        return {}

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_runner)
    result = scheduler.execute_single_observation(mode="live")

    assert result["collection_status"] == "STANDBY_SKIPPED"
    assert result["status"] == "STANDBY_SKIPPED"
    assert "enable_live_execution=False" in result["message"]
    assert runner_called is False, "안전 모드에서는 실제 파이프라인 러너가 호출되면 안 됩니다!"


def test_scheduler_lock_contention_blocks_duplicate_instance(tmp_path):
    """지침 2: 동일 락 파일에 대해 2개 인스턴스 중복 기동 시 즉시 SchedulerLockError 발생 검증."""
    dummy_lock = tmp_path / ".dup_scheduler.lock"

    config1 = SchedulerConfig(lock_file=dummy_lock)
    config2 = SchedulerConfig(lock_file=dummy_lock)

    sched1 = MarketObservationScheduler(config=config1)
    sched2 = MarketObservationScheduler(config=config2)

    sched1.acquire_lock()
    try:
        with pytest.raises(SchedulerLockError, match="다른 스케줄러 프로세스가 이미 실행 중입니다"):
            sched2.acquire_lock()
    finally:
        sched1.release_lock()

    sched2.acquire_lock()
    sched2.release_lock()


def test_transient_network_error_recovers_via_backoff(tmp_path):
    """지침 3: 일시적 네트워크 타임아웃(ConnectionError)은 지수 백오프로 3회차에 성공 복구 검증."""
    dummy_db = tmp_path / "dummy.db"
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    config = make_live_config(
        max_retries=3,
        initial_backoff_sec=0.04,
        backoff_factor=1.5,
        db_path=dummy_db,
        lock_file=tmp_path / ".retry.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    attempts_log = []
    def mock_flaky_runner(*args, **kwargs):
        attempts_log.append(time.time())
        if len(attempts_log) < 3:
            raise ConnectionError("엔카 모바일 웹 일시적 타임아웃 주입")
        return {"batch_id": "MOCK_SUCCESS"}

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_flaky_runner)
    result = scheduler.execute_single_observation(mode="live")

    assert result["collection_status"] == "SUCCESS"
    assert result["attempts"] == 3
    assert len(attempts_log) == 3


def test_permanent_error_fails_fast_without_retries(tmp_path):
    """지침 4 (013-A): 스키마 오류/ValueError 등 영구적 예외는 재시도 없이 1회 만에 즉시 중단(Fail-Fast) 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    config = make_live_config(
        max_retries=3,
        initial_backoff_sec=0.05,
        db_path=dummy_db,
        lock_file=tmp_path / ".fail_fast.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    attempt_count = 0
    def mock_permanent_failing_runner(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        raise ValueError("치명적 파싱 스키마 변경 (영구적 오류 주입)")

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_permanent_failing_runner)
    result = scheduler.execute_single_observation(mode="live")

    assert result["collection_status"] == "FAILED"
    # 재시도하지 않고 정확히 1회 만에 중단되어야 함
    assert attempt_count == 1
    assert result["attempts"] == 1
    assert "ValueError" in result["error"]


def test_collection_success_with_report_failure_does_not_retry_live(tmp_path, monkeypatch):
    """지침 5 (013-A 핵심): LIVE 수집 성공 후 보고서 생성이 실패하더라도 LIVE를 절대 재실행하지 않음 검증."""
    dummy_db = tmp_path / "dummy.db"
    config = make_live_config(
        max_retries=3,
        db_path=dummy_db,
        lock_file=tmp_path / ".report_fail.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    live_call_count = 0
    def mock_runner(*args, **kwargs):
        nonlocal live_call_count
        live_call_count += 1
        return {"batch_id": "BATCH_OK"}

    # DailyMarketReporter에서 예외 발생 주입
    def mock_generate_failure(*args, **kwargs):
        raise RuntimeError("보고서 템플릿 렌더링 디스크 풀 에러 주입")

    monkeypatch.setattr(DailyMarketReporter, "generate_daily_summary", mock_generate_failure)

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_runner)
    result = scheduler.execute_single_observation(mode="live")

    # 수집은 성공으로 인정되고, 보고서만 실패로 격리 기록
    assert result["collection_status"] == "SUCCESS"
    assert result["report_status"] == "REPORT_FAILED"
    assert result["status"] == "PARTIAL_SUCCESS"
    assert "RuntimeError" in result["report_error"]
    # 가장 중요한 검증: 라이브 러너가 절대 2회 이상 재실행되지 않고 정확히 1회만 호출됨!
    assert live_call_count == 1


def test_loop_breaks_on_fatal_failure(tmp_path):
    """지침 6 (013-A): run_loop 실행 중 수집 실패(FAILED) 발생 시 무한 루프 돌지 않고 즉시 중단 검증."""
    dummy_db = tmp_path / "dummy.db"
    config = make_live_config(
        interval_seconds=0.01,
        max_retries=1,
        db_path=dummy_db,
        lock_file=tmp_path / ".loop_break.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    cycle_count = 0
    def mock_fatal_runner(*args, **kwargs):
        nonlocal cycle_count
        cycle_count += 1
        raise ConnectionError("네트워크 전면 단절")

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_fatal_runner)
    # max_cycles=10으로 주어도 1회차 실패 시 즉시 루프 종료
    scheduler.run_loop(max_cycles=10, mode="live")

    assert cycle_count == 1, f"치명적 실패 시 루프를 즉시 종료해야 하는데 {cycle_count}회 실행됨"


def test_config_validation_rules(tmp_path):
    """지침 7 (013-A): 설정값 유효성 검증 규칙 (인터벌 > 0, REPLAY 시 운영 DB 차단)."""
    # 1. interval <= 0
    with pytest.raises(SchedulerConfigError, match="interval_seconds는 0보다 커야 합니다"):
        c = SchedulerConfig(interval_seconds=0)
        c.validate()

    # 2. max_retries < 1
    with pytest.raises(SchedulerConfigError, match="max_retries는 1 이상이어야 합니다"):
        c = SchedulerConfig(max_retries=0)
        c.validate()

    # 3. REPLAY 모드에서 운영 DB 지정 시 차단
    op_db = Path("data/chaficial_market_timeseries.db")
    c = SchedulerConfig(db_path=op_db)
    with pytest.raises(SchedulerConfigError, match="운영 DB.*는 REPLAY 모드의 대상이 될 수 없습니다"):
        c.validate(mode="replay")


def test_failure_report_unique_naming_no_overwrite(tmp_path):
    """지침 8 (013-A): 동일 초에 장애가 반복 발생해도 기존 보고서를 덮어쓰지 않고 배타적 생성 검증."""
    config = make_live_config(
        failure_dir=tmp_path / "failures",
    )
    scheduler = MarketObservationScheduler(config=config)

    path1 = scheduler._write_failure_report(mode="live", attempts=1, error=RuntimeError("에러1"))
    path2 = scheduler._write_failure_report(mode="live", attempts=1, error=RuntimeError("에러2"))

    assert path1.exists()
    assert path2.exists()
    assert path1 != path2, "동일 초 생성 시 고유 파일명으로 분리되어야 합니다!"


def test_kst_date_conversion_boundary():
    """지침 9 (013-A): UTC -> KST(UTC+9) 변환 시 자정 전후 경계값 정확성 검증."""
    # UTC 2026-10-23 14:59:59 -> KST 2026-10-23 23:59:59 (KST 날짜: 2026-10-23)
    dt1 = datetime(2026, 10, 23, 14, 59, 59, tzinfo=UTC)
    assert to_kst_date_str(dt1) == "2026-10-23"

    # UTC 2026-10-23 15:00:00 -> KST 2026-10-24 00:00:00 (KST 자정, 날짜: 2026-10-24)
    dt2 = datetime(2026, 10, 23, 15, 0, 0, tzinfo=UTC)
    assert to_kst_date_str(dt2) == "2026-10-24"

    # None 입력 시
    assert to_kst_date_str(None) is None


def test_is_transient_network_error_classification():
    """지침 11 (013-B): 일시적 네트워크 예외와 영구적 파일/DB 예외의 엄격한 분류 검증."""
    from chaficial.tracker.scheduler import is_transient_network_error
    import sqlite3

    # 네트워크 일시적 예외 -> True
    assert is_transient_network_error(ConnectionError("네트워크 단절")) is True
    assert is_transient_network_error(TimeoutError("소켓 타임아웃")) is True

    # 파일 / 권한 / DB 영구적 예외 -> 절대 False
    assert is_transient_network_error(PermissionError("디스크 쓰기 권한 없음")) is False
    assert is_transient_network_error(FileNotFoundError("파일 없음")) is False
    assert is_transient_network_error(sqlite3.OperationalError("데이터베이스 락")) is False
    assert is_transient_network_error(ValueError("데이터 형식 오류")) is False


def test_commit_boundary_post_error_does_not_re_collect(tmp_path):
    """지침 12 (013-B/C 핵심): 현재 발급된 batch_id가 DB에 커밋된 후 사후 예외 발생 시 재수집 차단 검증."""
    dummy_db = tmp_path / "dummy.db"
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session

    config = make_live_config(
        max_retries=3,
        db_path=dummy_db,
        lock_file=tmp_path / ".commit_boundary.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    import hashlib
    raw_f = config.raw_observations_dir / "mock_live_raw.json"
    raw_f.write_text("{}", encoding="utf-8")
    raw_sha = hashlib.sha256(b"{}").hexdigest()
    valid_notes = json.dumps({
        "raw_file_path": str(raw_f),
        "raw_file_sha256": raw_sha,
        "first_seen_count": 100,
        "re_observed_count": 0,
    })

    runner_call_count = 0
    def mock_runner_commits_then_crashes(*args, **kwargs):
        nonlocal runner_call_count
        runner_call_count += 1
        b_id = kwargs.get("batch_id") or "UNKNOWN_BATCH"
        # 러너가 현재 발급된 batch_id로 DB 커밋 완료
        with Session(engine) as session:
            b = BatchAuditLog(
                batch_id=b_id,
                source_platform="ENCAR",
                search_scope="아반떼 CN7",
                record_count=100,
                notes=valid_notes,
            )
            session.add(b)
            session.commit()

        # 커밋 성공 후 네트워크 단절 또는 사후 예외 발생 주입
        raise ConnectionError("커밋 후 소켓 닫힘 예외 주입")

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_runner_commits_then_crashes)
    result = scheduler.execute_single_observation(mode="live")

    # DB에 현재 배치가 이미 커밋되었음을 스케줄러가 감지하여 재실행을 차단하고 1회만 호출되어야 함!
    assert runner_call_count == 1, "DB 커밋 후 사후 예외가 발생해도 재수집하면 안 됩니다!"
    assert result["collection_status"] == "COMMITTED_WITH_POST_ERROR"


def test_disk_and_permission_errors_fail_fast_without_retry(tmp_path):
    """지침 13 (013-B): PermissionError 등 디스크/권한 에러 발생 시 즉시 중단(Fail-Fast) 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    config = make_live_config(
        max_retries=3,
        db_path=dummy_db,
        lock_file=tmp_path / ".perm_err.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    call_count = 0
    def mock_perm_error_runner(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise PermissionError("디스크 권한 거부")

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_perm_error_runner)
    result = scheduler.execute_single_observation(mode="live")

    assert call_count == 1, "PermissionError는 재시도 없이 1회 만에 Fail-Fast 되어야 합니다!"
    assert result["collection_status"] == "FAILED"
    assert result["error_type"] == "PermissionError"


def test_check_batch_committed_fail_closed_on_db_query_error(tmp_path, monkeypatch):
    """지침 14 (013-C 핵심): DB 커밋 상태 조회 실패 시 Fail-Closed로 재시도 0회 즉시 차단 검증."""
    dummy_db = tmp_path / "dummy.db"
    config = make_live_config(
        max_retries=3,
        db_path=dummy_db,
        lock_file=tmp_path / ".fail_closed.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    runner_called_count = 0
    def mock_runner(*args, **kwargs):
        nonlocal runner_called_count
        runner_called_count += 1
        raise ConnectionError("네트워크 오류 발생")

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_runner)

    # check_batch_committed에서 DB 조회 실패 예외 주입
    from chaficial.tracker.scheduler import CommitStatusUnknownError
    def mock_check_fail(batch_id):
        raise CommitStatusUnknownError("DB 잠금 경합으로 인한 커밋 조회 불가 주입")

    monkeypatch.setattr(scheduler, "check_batch_committed", mock_check_fail)

    result = scheduler.execute_single_observation(mode="live")

    # 커밋 여부가 불확실하므로 재시도하지 않고 1회 시도 후 즉시 COMMIT_STATUS_UNKNOWN으로 안전 종료
    assert runner_called_count == 1
    assert result["collection_status"] == "COMMIT_STATUS_UNKNOWN"
    assert result["error_type"] == "CommitStatusUnknownError"


def test_batch_ownership_ignores_other_process_batches(tmp_path):
    """지침 15 (013-C 핵심): 타 프로세스의 신규 배치가 DB에 있어도 현재 배치가 아니면 오인하지 않음 검증."""
    dummy_db = tmp_path / "dummy.db"
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session

    config = make_live_config(
        max_retries=1,
        db_path=dummy_db,
        lock_file=tmp_path / ".ownership.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    def mock_runner_crashes_while_another_process_commits(*args, **kwargs):
        # 다른 독립 프로세스가 자신의 batch_id를 커밋했다고 가정
        with Session(engine) as session:
            b = BatchAuditLog(
                batch_id="OTHER_PROCESS_BATCH_999",
                source_platform="ENCAR",
                search_scope="아반떼 CN7",
                record_count=50,
            )
            session.add(b)
            session.commit()

        # 현재 프로세스는 자신의 배치를 커밋하지 못하고 크래시
        raise ConnectionError("내 배치는 미커밋 상태에서 크래시")

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_runner_crashes_while_another_process_commits)
    result = scheduler.execute_single_observation(mode="live")

    # 타 프로세스의 배치를 내 배치의 성공으로 오인하지 않고 FAILED 처리되어야 함!
    assert result["collection_status"] == "FAILED"
    assert result["batch_id"] != "OTHER_PROCESS_BATCH_999"


def test_loop_breaks_on_commit_status_unknown(tmp_path, monkeypatch):
    """지침 16 (013-C): COMMIT_STATUS_UNKNOWN 발생 시 run_loop가 즉시 안전 중단(Break)됨을 검증."""
    dummy_db = tmp_path / "dummy.db"
    config = make_live_config(
        interval_seconds=0.01,
        max_retries=1,
        db_path=dummy_db,
        lock_file=tmp_path / ".loop_unknown.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    cycle_count = 0
    def mock_runner(*args, **kwargs):
        nonlocal cycle_count
        cycle_count += 1
        raise ConnectionError("네트워크 에러")

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_runner)

    from chaficial.tracker.scheduler import CommitStatusUnknownError
    def mock_check_fail(batch_id):
        raise CommitStatusUnknownError("DB 잠금")

    monkeypatch.setattr(scheduler, "check_batch_committed", mock_check_fail)

    scheduler.run_loop(max_cycles=5, mode="live")
    assert cycle_count == 1, "COMMIT_STATUS_UNKNOWN 발생 시 즉시 루프가 중단되어야 함"



def test_daily_market_reporter_atomic_creation(tmp_path):
    """지침 10 (013-A): DailyMarketReporter가 원자적으로 일별 보고서를 발행하고 메트릭을 포함하는지 검증."""
    op_db = Path("data/chaficial_market_timeseries.db")
    reporter = DailyMarketReporter(db_path=op_db, output_dir=tmp_path / "reports")
    report_file = reporter.generate_daily_summary(target_date_str="2026-10-24")

    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "# CHA-FICIAL 일별 시장 관측 요약 보고서 (2026-10-24)" in content
    assert "정밀 파싱 수집 매물 수" in content
    assert "당일 재관측 매물 (`RE_OBSERVED`)" in content
    assert "3,100,000원" in content


def test_runner_internal_type_error_called_exactly_once(tmp_path):
    """지침 17 (013-D 최우선): 러너 내부 TypeError 발생 시 호환성 오인 재호출 없이 정확히 1회만 호출 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()  # DB 파일 생성
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    config = make_live_config(
        max_retries=3,
        db_path=dummy_db,
        lock_file=tmp_path / ".type_err.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    call_count = 0
    def mock_runner_with_internal_type_error(mode: str, db_path_override=None, batch_id=None):
        nonlocal call_count
        call_count += 1
        # 러너 내부 로직에서 발생한 TypeError
        return int(None)  # TypeError: int() argument must be a string, a bytes-like object or a real number, not 'NoneType'

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_runner_with_internal_type_error)
    result = scheduler.execute_single_observation(mode="live")

    # 영구적 예외이므로 재시도나 호환성 재호출 없이 정확히 1회만 호출되고 즉시 FAILED
    assert call_count == 1, f"러너 내부 TypeError 발생 시 재호출되면 안 되는데 {call_count}회 호출됨!"
    assert result["collection_status"] == "FAILED"
    assert result["error_type"] == "TypeError"


def test_live_runner_without_batch_id_rejected(tmp_path):
    """지침 18 (013-D): LIVE 러너가 batch_id 인자를 지원하지 않으면 즉시 실행 거부 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()

    config = make_live_config(
        db_path=dummy_db,
        lock_file=tmp_path / ".no_batch_id.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    def mock_legacy_runner(mode: str, db_path_override=None):
        # batch_id 파라미터가 없는 구식 러너
        return {}

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_legacy_runner)
    with pytest.raises(SchedulerConfigError, match="LIVE 러너.*batch_id 인자를 필수로 지원해야 합니다"):
        scheduler.execute_single_observation(mode="live")


def test_db_file_missing_treated_as_commit_status_unknown(tmp_path):
    """지침 19 (013-D): DB 파일 부재 시 미커밋으로 단정하지 않고 CommitStatusUnknownError 발생 검증."""
    non_existent_db = tmp_path / "not_found.db"
    config = SchedulerConfig(db_path=non_existent_db)
    scheduler = MarketObservationScheduler(config=config)

    from chaficial.tracker.scheduler import CommitStatusUnknownError
    with pytest.raises(CommitStatusUnknownError, match="대상 DB 파일이 존재하지 않아 커밋 여부 확인 불가"):
        scheduler.check_batch_committed("SOME_BATCH_ID")


def test_loop_breaks_on_committed_with_post_error(tmp_path):
    """지침 20 (013-D): COMMITTED_WITH_POST_ERROR 발생 시 run_loop가 다음 주기로 가지 않고 즉시 중단 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session

    config = make_live_config(
        interval_seconds=0.01,
        max_retries=1,
        db_path=dummy_db,
        lock_file=tmp_path / ".post_err_loop.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    cycle_count = 0
    def mock_runner_commits_then_crashes(mode: str, db_path_override=None, batch_id=None):
        nonlocal cycle_count
        cycle_count += 1
        with Session(engine) as session:
            b = BatchAuditLog(
                batch_id=batch_id,
                source_platform="ENCAR",
                search_scope="아반떼 CN7",
                record_count=10,
            )
            session.add(b)
            session.commit()
        raise ConnectionError("커밋 후 소켓 에러")

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_runner_commits_then_crashes)
    scheduler.run_loop(max_cycles=5, mode="live")

    # COMMITTED_WITH_POST_ERROR 발생 시 수동 확인 필요하므로 1회차에 즉시 루프 중단!
    assert cycle_count == 1, "COMMITTED_WITH_POST_ERROR 발생 시 루프가 즉시 중단되어야 함"


# ==============================================================================
# DIRECTIVE 013-F: FINAL LIVE AUTHORIZATION & STRICT COMMIT AUDIT
# ==============================================================================


def test_live_execution_rejected_when_auth_file_missing(tmp_path):
    """지침 1 (013-F): enable_live_execution=True여도 승인 파일이 없으면 LiveExecutionNotAuthorizedError 거부."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()

    # 승인 파일이 존재하지 않는 경로로 설정
    missing_auth = tmp_path / "non_existent_auth.json"
    config = SchedulerConfig(
        enable_live_execution=True,
        auth_file_path=missing_auth,
        db_path=dummy_db,
    )

    with pytest.raises(LiveExecutionNotAuthorizedError, match="총괄 감독의 유효한 로컬 운영 승인이 확인되지 않았습니다"):
        MarketObservationScheduler(config=config)


def test_live_execution_rejected_when_auth_expired(tmp_path):
    """지침 1 (013-F): 승인 파일이 존재하더라도 만료일자가 지났으면 LiveExecutionNotAuthorizedError 거부."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()

    expired_auth = tmp_path / "expired_auth.json"
    create_test_auth_file(expired_auth, is_approved=True, expired=True)

    config = SchedulerConfig(
        enable_live_execution=True,
        auth_file_path=expired_auth,
        db_path=dummy_db,
    )

    with pytest.raises(LiveExecutionNotAuthorizedError, match="운영 승인 유효기간 만료됨"):
        MarketObservationScheduler(config=config)


def test_live_execution_rejected_when_not_approved(tmp_path):
    """지침 1 (013-F): 승인 파일 내 is_approved=False이면 LiveExecutionNotAuthorizedError 거부."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()

    unapproved_auth = tmp_path / "unapproved_auth.json"
    create_test_auth_file(unapproved_auth, is_approved=False, expired=False)

    config = SchedulerConfig(
        enable_live_execution=True,
        auth_file_path=unapproved_auth,
        db_path=dummy_db,
    )

    with pytest.raises(LiveExecutionNotAuthorizedError, match="is_approved.*boolean true가 아닙니다"):
        MarketObservationScheduler(config=config)


def test_default_config_has_no_live_auth():
    """지침 1 (013-F): 기본 설정 상태에서는 운영 승인 파일이 존재하지 않아 LIVE 실행이 불가함을 입증."""
    config = SchedulerConfig()
    # 기본값은 LIVE 비활성
    assert config.enable_live_execution is False

    # 만약 임의로 enable_live_execution만 켜더라도 승인 파일 부재로 즉시 거부됨
    config.enable_live_execution = True
    with pytest.raises(LiveExecutionNotAuthorizedError, match="운영 승인 파일 부재"):
        config.validate(mode="live")


def test_partial_success_breaks_run_loop(tmp_path):
    """지침 2 (013-E): PARTIAL_SUCCESS(보고서 실패) 발생 시 다음 주기로 가지 않고 루프 즉시 종료 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    # 읽기 전용으로 보고서 디렉토리를 엉뚱한 경로로 지정하여 보고서 생성 강제 실패 유도
    failing_report_dir = tmp_path / "read_only_reports"
    failing_report_dir.mkdir(parents=True, exist_ok=True)
    # 읽기 전용 디렉토리 권한 설정
    failing_report_dir.chmod(0o444)

    config = make_live_config(
        interval_seconds=0.01,
        max_retries=1,
        db_path=dummy_db,
        lock_file=tmp_path / ".partial_success_loop.lock",
        report_dir=failing_report_dir,
        failure_dir=tmp_path / "failures",
    )

    cycle_count = 0
    def mock_runner_success(mode: str, db_path_override=None, batch_id=None):
        nonlocal cycle_count
        cycle_count += 1
        return {"batch_id": batch_id, "record_count": 10}

    try:
        scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_runner_success)
        scheduler.run_loop(max_cycles=5, mode="live")
        # 보고서 실패로 PARTIAL_SUCCESS가 발생하므로 1회 만에 루프 종료되어야 함
        assert cycle_count == 1, f"PARTIAL_SUCCESS 시 루프가 즉시 중단되어야 하는데 {cycle_count}회 반복됨"
    finally:
        failing_report_dir.chmod(0o755)


def test_recover_daily_report_standalone(tmp_path):
    """지침 2 (013-E): 수집 재실행 없이 일별 요약 보고서만 단독으로 안전 복구 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    report_dir = tmp_path / "recovered_reports"
    config = make_live_config(
        db_path=dummy_db,
        report_dir=report_dir,
        failure_dir=tmp_path / "failures",
    )

    runner_called = False
    def mock_runner(*args, **kwargs):
        nonlocal runner_called
        runner_called = True
        return {}

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_runner)
    recovered_path = scheduler.recover_daily_report()

    # 수집 러너는 절대 호출되지 않고, 보고서 파일만 생성되어야 함
    assert not runner_called, "보고서 단독 복구 시 파이프라인 러너가 호출되면 안 됩니다!"
    assert recovered_path.exists()
    assert recovered_path.is_file()


def test_check_batch_committed_fails_on_duplicate_batch_id(tmp_path, monkeypatch):
    """지침 3 (013-E): 동일 batch_id가 2건 이상 조회되면 DB 무결성 위반으로 Fail-Closed 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()

    from chaficial.models import BatchAuditLog
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    target_batch_id = "ENCAR_CN7_LIVE_DUP_001"
    b1 = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10)
    b2 = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10)

    class MockScalars:
        def all(self):
            return [b1, b2]

    class MockResult:
        def scalars(self):
            return MockScalars()

    class MockSession:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def execute(self, *args, **kwargs):
            return MockResult()

    monkeypatch.setattr("chaficial.tracker.scheduler.Session", MockSession)

    config = SchedulerConfig(db_path=dummy_db)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="배치 ID 중복 감지"):
        scheduler.check_batch_committed(target_batch_id)


def test_check_batch_committed_fails_on_invalid_record_count(tmp_path):
    """지침 3 (013-E): record_count가 음수이거나 None이면 Fail-Closed 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    target_batch_id = "ENCAR_CN7_LIVE_INVALID_COUNT"
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=-1)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="record_count가 유효하지 않습니다"):
        scheduler.check_batch_committed(target_batch_id)


def test_check_batch_committed_fails_on_platform_mismatch(tmp_path):
    """지침 3 (013-E): source_platform이 ENCAR가 아니면 데이터 기원 불일치로 Fail-Closed 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    target_batch_id = "ENCAR_CN7_LIVE_PLATFORM_MISMATCH"
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="BOBAEDREAM", search_scope="ENCAR:현대:아반떼", record_count=50)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="배치 데이터 기원 불일치"):
        scheduler.check_batch_committed(target_batch_id)


def test_check_batch_committed_fails_on_missing_raw_file(tmp_path):
    """지침 3 (013-E): notes에 기재된 원천 파일 경로가 실제로 존재하지 않으면 Fail-Closed 검증."""
    import json
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    target_batch_id = "ENCAR_CN7_LIVE_MISSING_RAW"
    missing_raw = tmp_path / "does_not_exist_raw.json"

    notes = json.dumps({
        "raw_file_path": str(missing_raw),
        "raw_file_sha256": "a" * 64,
        "first_seen_count": 10,
        "re_observed_count": 0,
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="배치 원천 파일 소실 감지"):
        scheduler.check_batch_committed(target_batch_id)


def test_check_batch_committed_fails_on_raw_file_sha_mismatch(tmp_path):
    """지침 3 (013-E): notes의 원천 파일 SHA-256이 실제 파일 해시와 불일치(변조) 시 Fail-Closed 검증."""
    import json
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    raw_obs_dir = tmp_path / "raw_observations"
    raw_obs_dir.mkdir(parents=True, exist_ok=True)

    target_batch_id = "ENCAR_CN7_LIVE_HASH_TAMPERED"
    real_raw = raw_obs_dir / "tampered_raw.json"
    real_raw.write_text("SOME_ACTUAL_CONTENT", encoding="utf-8")

    # 가짜 조작 해시 주입
    notes = json.dumps({
        "raw_file_path": str(real_raw),
        "raw_file_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "first_seen_count": 10,
        "re_observed_count": 0,
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db, raw_observations_dir=raw_obs_dir)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="배치 원천 파일 SHA-256 변조 감지"):
        scheduler.check_batch_committed(target_batch_id)


def test_check_batch_committed_fails_on_quantity_mismatch(tmp_path):
    """지침 3 (013-E): first_seen + re_observed 수량이 record_count와 불일치 시 Fail-Closed 검증."""
    import json
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    raw_obs_dir = tmp_path / "raw_observations"
    raw_obs_dir.mkdir(parents=True, exist_ok=True)

    target_batch_id = "ENCAR_CN7_LIVE_QTY_MISMATCH"
    dummy_raw = raw_obs_dir / "qty_raw.json"
    dummy_raw.write_text("{}", encoding="utf-8")
    import hashlib
    d_sha = hashlib.sha256(b"{}").hexdigest()

    notes = json.dumps({
        "raw_file_path": str(dummy_raw),
        "raw_file_sha256": d_sha,
        "first_seen_count": 5,
        "re_observed_count": 3,  # 합계 8인데 record_count는 10
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db, raw_observations_dir=raw_obs_dir)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="배치 적재 수량 불일치"):
        scheduler.check_batch_committed(target_batch_id)


def test_check_batch_committed_success_with_valid_audit(tmp_path):
    """지침 3 (013-E): 정상 원천 파일, 해시, 수량이 모두 완벽한 경우 정상 COMMITTED 검증."""
    import hashlib
    import json
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session

    raw_obs_dir = tmp_path / "raw_observations"
    raw_obs_dir.mkdir(parents=True, exist_ok=True)

    target_batch_id = "ENCAR_CN7_LIVE_VALID_AUDIT"
    real_raw = raw_obs_dir / "valid_raw.json"
    real_raw.write_bytes(b'{"valid": true}')
    sha = hashlib.sha256(b'{"valid": true}').hexdigest()

    notes = json.dumps({
        "raw_file_path": str(real_raw),
        "raw_file_sha256": sha,
        "first_seen_count": 8,
        "re_observed_count": 2,
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db, raw_observations_dir=raw_obs_dir)
    scheduler = MarketObservationScheduler(config=config)

    status = scheduler.check_batch_committed(target_batch_id)
    assert status == "COMMITTED", f"정상적인 배치 커밋이어야 하는데 {status} 반환됨"


def test_check_batch_committed_new_batch_fails_without_notes(tmp_path):
    """지침 2 (013-F): 신규 스케줄러 배치는 notes가 없으면 COMMIT_STATUS_UNKNOWN 거부."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    new_batch_id = "ENCAR_CN7_LIVE_20261024_NEW_NO_NOTES"
    with Session(engine) as session:
        # notes=None 으로 저장
        b = BatchAuditLog(batch_id=new_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=None)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="신규 배치.*필수 감사 메타데이터.*누락"):
        scheduler.check_batch_committed(new_batch_id, is_legacy=False)


def test_check_batch_committed_new_batch_fails_when_sha_missing(tmp_path):
    """지침 2 (013-F): 신규 배치는 원천 파일 경로가 있어도 SHA-256이 누락되면 COMMIT_STATUS_UNKNOWN 거부."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    new_batch_id = "ENCAR_CN7_LIVE_20261024_NEW_NO_SHA"
    real_raw = tmp_path / "raw.json"
    real_raw.write_text("{}", encoding="utf-8")

    # raw_file_sha256 필드 누락
    notes = json.dumps({
        "raw_file_path": str(real_raw),
        "first_seen_count": 10,
        "re_observed_count": 0,
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=new_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="필수 감사 메타데이터 누락: 키 'raw_file_sha256'"):
        scheduler.check_batch_committed(new_batch_id, is_legacy=False)


def test_check_batch_committed_legacy_batch_compatible(tmp_path):
    """지침 2 (013-F): 기존 1~3차 레거시 배치는 일반 텍스트 notes여도 하위 호환 통과 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session

    # 1차 레거시 배치 ID 사용
    legacy_batch_id = "ENCAR_CN7_LIVE_20261021_01"
    legacy_notes = "PARTIAL_OR_FAILED_BATCH: 엔카 아반떼 CN7 1페이지 실시간 표본 관측 (카드 250개 중 126대)"

    with Session(engine) as session:
        b = BatchAuditLog(
            batch_id=legacy_batch_id,
            source_platform="ENCAR",
            search_scope="ENCAR:현대:아반떼:ALL:MIN~MAX",
            record_count=126,
            notes=legacy_notes,
        )
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db)
    scheduler = MarketObservationScheduler(config=config)

    # LEGACY_BATCH_IDS에 포함되어 있으므로 레거시 호환 검증 통과
    status = scheduler.check_batch_committed(legacy_batch_id)
    assert status == "COMMITTED", f"레거시 배치는 호환 검증되어야 하는데 {status} 반환됨"


def test_check_batch_committed_new_batch_cannot_bypass_via_is_legacy_flag(tmp_path):
    """지침 2 (013-G): 신규 배치가 is_legacy=True 플래그를 전달하더라도 레거시 검증 우회 원천 차단 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    new_batch_id = "ENCAR_CN7_LIVE_20261024_NEW_BYPASS_ATTEMPT"
    with Session(engine) as session:
        # 신규 배치가 notes 없이 커밋된 상태
        b = BatchAuditLog(batch_id=new_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=None)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db)
    scheduler = MarketObservationScheduler(config=config)

    # is_legacy=True를 명시적으로 주더라도 신규 배치 ID이면 즉시 차단!
    with pytest.raises(CommitStatusUnknownError, match="보안 위반: 신규 배치.*레거시 검증.*우회할 수 없습니다"):
        scheduler.check_batch_committed(new_batch_id, is_legacy=True)


def test_verify_live_authorization_rejects_symlink(tmp_path):
    """지침 1 (013-G): 심볼릭 링크로 연결된 승인 파일은 보안 위반으로 거부 검증."""
    real_auth = tmp_path / "real_auth.json"
    create_test_auth_file(real_auth, is_approved=True)

    symlink_auth = tmp_path / "symlink_auth.json"
    symlink_auth.symlink_to(real_auth)

    is_valid, reason = verify_live_authorization(symlink_auth)
    assert is_valid is False
    assert "심볼릭 링크" in reason


def test_verify_live_authorization_rejects_excessive_duration(tmp_path):
    """지침 1 (013-G): 7일을 초과하는 과도하게 긴 승인 기간은 거부 검증."""
    auth_file = tmp_path / "long_validity_auth.json"
    # 10일 유효기간 주입
    create_test_auth_file(auth_file, is_approved=True, days_valid=10.0)

    is_valid, reason = verify_live_authorization(auth_file)
    assert is_valid is False
    assert "과도하게 긴 승인 기간 거부" in reason


def test_check_batch_committed_fails_on_boolean_counts(tmp_path):
    """지침 3 (013-G): first_seen_count가 True 등 boolean인 경우 정수형 엄격 검증으로 거부."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    raw_obs_dir = tmp_path / "raw_observations"
    raw_obs_dir.mkdir(parents=True, exist_ok=True)

    target_batch_id = "ENCAR_CN7_LIVE_BOOL_COUNT"
    real_raw = raw_obs_dir / "raw.json"
    real_raw.write_text("{}", encoding="utf-8")
    import hashlib
    sha = hashlib.sha256(b"{}").hexdigest()

    # first_seen_count에 boolean True 주입
    notes = json.dumps({
        "raw_file_path": str(real_raw),
        "raw_file_sha256": sha,
        "first_seen_count": True,
        "re_observed_count": 0,
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=1, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db, raw_observations_dir=raw_obs_dir)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="first_seen_count는 0 이상의 정수여야 합니다"):
        scheduler.check_batch_committed(target_batch_id)


# ==============================================================================
# DIRECTIVE 013-H/I: 최종 PR 병합 준비 (원천 파일 경로 보안 & UTC 엄격 검증)
# ==============================================================================


def test_verify_live_authorization_rejects_non_utc_offset(tmp_path):
    """지침 3 (013-H): expires_at에 +09:00 등 비-UTC 오프셋이 지정된 경우 즉시 거부 검증."""
    auth_file = tmp_path / "kst_auth.json"
    payload = {
        "is_approved": True,
        "approved_by": "LOCAL_OPERATOR_TEST",
        "expires_at": "2026-10-25T15:00:00+09:00",  # 비-UTC 시간대 주입
    }
    auth_file.write_text(json.dumps(payload), encoding="utf-8")

    is_valid, reason = verify_live_authorization(auth_file)
    assert is_valid is False
    assert "반드시 UTC 시간대(+00:00 또는 Z)" in reason


def test_check_batch_committed_rejects_raw_file_outside_allowed_dir(tmp_path):
    """지침 1 (013-I): 원천 파일이 허용된 raw_observations 디렉터리 외부 경로이면 거부 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    raw_obs_dir = tmp_path / "raw_observations"
    raw_obs_dir.mkdir(parents=True, exist_ok=True)

    other_dir = tmp_path / "other_folder"
    other_dir.mkdir(parents=True, exist_ok=True)
    outside_raw = other_dir / "outside_raw_test_file.json"
    outside_raw.write_text("{}", encoding="utf-8")
    import hashlib
    sha = hashlib.sha256(b"{}").hexdigest()

    target_batch_id = "ENCAR_CN7_LIVE_OUTSIDE_DIR"
    notes = json.dumps({
        "raw_file_path": str(outside_raw),
        "raw_file_sha256": sha,
        "first_seen_count": 10,
        "re_observed_count": 0,
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db, raw_observations_dir=raw_obs_dir)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="승인된 관측 디렉터리.*외부 경로"):
        scheduler.check_batch_committed(target_batch_id)


def test_check_batch_committed_rejects_data_root_outside_raw_obs(tmp_path):
    """지침 1 (013-I): data/ 루트 내부라도 raw_observations 외부인 파일은 엄격 거부 검증."""
    dummy_db = tmp_path / "data" / "dummy.db"
    dummy_db.parent.mkdir(parents=True, exist_ok=True)
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    raw_obs_dir = tmp_path / "data" / "raw_observations"
    raw_obs_dir.mkdir(parents=True, exist_ok=True)

    # data/ 루트 바로 아래 파일 (raw_observations 외부)
    data_root_raw = tmp_path / "data" / "some_other.json"
    data_root_raw.write_text("{}", encoding="utf-8")
    import hashlib
    sha = hashlib.sha256(b"{}").hexdigest()

    target_batch_id = "ENCAR_CN7_LIVE_DATA_ROOT_REJECT"
    notes = json.dumps({
        "raw_file_path": str(data_root_raw),
        "raw_file_sha256": sha,
        "first_seen_count": 10,
        "re_observed_count": 0,
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db, raw_observations_dir=raw_obs_dir)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="승인된 관측 디렉터리.*외부 경로"):
        scheduler.check_batch_committed(target_batch_id)


def test_check_batch_committed_rejects_raw_file_path_traversal(tmp_path):
    """지침 2 (013-H): 원천 파일 경로에 상위 경로 이탈(..)이 포함된 경우 거부 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    raw_obs_dir = tmp_path / "raw_observations"
    raw_obs_dir.mkdir(parents=True, exist_ok=True)

    target_batch_id = "ENCAR_CN7_LIVE_TRAVERSAL"
    traversal_path = str(raw_obs_dir) + "/../../etc/passwd"

    notes = json.dumps({
        "raw_file_path": traversal_path,
        "raw_file_sha256": "0" * 64,
        "first_seen_count": 10,
        "re_observed_count": 0,
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db, raw_observations_dir=raw_obs_dir)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="상위 디렉터리 이탈"):
        scheduler.check_batch_committed(target_batch_id)


def test_check_batch_committed_rejects_raw_file_symlink(tmp_path):
    """지침 1 (013-I): 원천 파일 자체가 심볼릭 링크인 경우 보안 위반으로 거부 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    raw_obs_dir = tmp_path / "raw_observations"
    raw_obs_dir.mkdir(parents=True, exist_ok=True)

    target_batch_id = "ENCAR_CN7_LIVE_SYMLINK_RAW"
    real_raw = tmp_path / "real_raw.json"
    real_raw.write_text("{}", encoding="utf-8")
    symlink_raw = raw_obs_dir / "symlink_raw.json"
    symlink_raw.symlink_to(real_raw)

    import hashlib
    sha = hashlib.sha256(b"{}").hexdigest()

    notes = json.dumps({
        "raw_file_path": str(symlink_raw),
        "raw_file_sha256": sha,
        "first_seen_count": 10,
        "re_observed_count": 0,
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db, raw_observations_dir=raw_obs_dir)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="원천 파일은 심볼릭 링크일 수 없습니다"):
        scheduler.check_batch_committed(target_batch_id)


def test_check_batch_committed_rejects_parent_dir_symlink(tmp_path):
    """지침 1 (013-I): 원천 파일의 상위 디렉터리가 심볼릭 링크인 경우 보안 위반으로 거부 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_db.touch()
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    from chaficial.models import BatchAuditLog
    from sqlalchemy.orm import Session
    from chaficial.tracker.scheduler import CommitStatusUnknownError

    raw_obs_dir = tmp_path / "raw_observations"
    raw_obs_dir.mkdir(parents=True, exist_ok=True)

    real_sub = tmp_path / "external_sub"
    real_sub.mkdir(parents=True, exist_ok=True)
    real_file = real_sub / "test.json"
    real_file.write_text("{}", encoding="utf-8")

    # raw_obs_dir 내부에 외부 디렉터리를 가리키는 심볼릭 링크 생성
    symlink_dir = raw_obs_dir / "linked_sub"
    symlink_dir.symlink_to(real_sub)

    import hashlib
    sha = hashlib.sha256(b"{}").hexdigest()

    target_batch_id = "ENCAR_CN7_LIVE_PARENT_SYMLINK"
    notes = json.dumps({
        "raw_file_path": str(symlink_dir / "test.json"),
        "raw_file_sha256": sha,
        "first_seen_count": 10,
        "re_observed_count": 0,
    })
    with Session(engine) as session:
        b = BatchAuditLog(batch_id=target_batch_id, source_platform="ENCAR", search_scope="ENCAR:현대:아반떼", record_count=10, notes=notes)
        session.add(b)
        session.commit()

    config = SchedulerConfig(db_path=dummy_db, raw_observations_dir=raw_obs_dir)
    scheduler = MarketObservationScheduler(config=config)

    with pytest.raises(CommitStatusUnknownError, match="원천 파일의 상위 디렉터리가 심볼릭 링크입니다"):
        scheduler.check_batch_committed(target_batch_id)





