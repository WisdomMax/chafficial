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

from chaficial.database.base import Base
from chaficial.tracker.daily_reporter import DailyMarketReporter, to_kst_date_str
from chaficial.tracker.scheduler import (
    MarketObservationScheduler,
    SchedulerConfig,
    SchedulerConfigError,
    SchedulerLockError,
)


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

    config = SchedulerConfig(
        enable_live_execution=True,
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
    config = SchedulerConfig(
        enable_live_execution=True,
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
    config = SchedulerConfig(
        enable_live_execution=True,
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
    config = SchedulerConfig(
        enable_live_execution=True,
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
    config = SchedulerConfig(
        enable_live_execution=True,
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

    config = SchedulerConfig(
        enable_live_execution=True,
        max_retries=3,
        db_path=dummy_db,
        lock_file=tmp_path / ".commit_boundary.lock",
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

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
    config = SchedulerConfig(
        enable_live_execution=True,
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
    config = SchedulerConfig(
        enable_live_execution=True,
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

    config = SchedulerConfig(
        enable_live_execution=True,
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
    config = SchedulerConfig(
        enable_live_execution=True,
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
