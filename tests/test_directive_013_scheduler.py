"""CHA-FICIAL DIRECTIVE 013 스케줄러 및 운영체계 독립 테스트 스위트.

1. 안전 가드 (STANDBY): 감독 승인 전 무단 LIVE 실행 차단 검증
2. 프로세스 실행 잠금: 중복 스케줄러 기동 100% 차단 검증
3. 실패 주입 및 지수 백오프: 2회 실패 후 3회차 성공 복구 검증
4. 최대 재시도 초과 및 장애 격리: 3회 실패 시 FAILED 종결 및 장애 보고서 발행 검증
5. 일별 시장 요약 리포터: 데이터베이스 동적 집계 및 마크다운 생성 검증
"""

import multiprocessing
from pathlib import Path
import time
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from chaficial.database.base import Base
from chaficial.tracker.daily_reporter import DailyMarketReporter
from chaficial.tracker.scheduler import (
    MarketObservationScheduler,
    SchedulerConfig,
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

    # 잠금 해제 후 sched2가 락을 정상 획득할 수 있는지 확인
    sched2.acquire_lock()
    sched2.release_lock()


def test_failure_injection_and_exponential_backoff_recovery(tmp_path):
    """지침 3: 2회 일시적 장애(예: 네트워크 타임아웃) 발생 후 3회차 성공 시 복구 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_lock = tmp_path / ".retry_test.lock"

    config = SchedulerConfig(
        enable_live_execution=True,
        max_retries=3,
        initial_backoff_sec=0.05,  # 테스트용 짧은 대기
        backoff_factor=1.5,
        db_path=dummy_db,
        lock_file=dummy_lock,
        report_dir=tmp_path / "reports",
        failure_dir=tmp_path / "failures",
    )

    attempts_log = []
    def mock_flaky_runner(*args, **kwargs):
        attempts_log.append(time.time())
        if len(attempts_log) < 3:
            raise ConnectionError("엔카 모바일 웹 일시적 응답 지연 (네트워크 타임아웃 주입)")
        return {"batch_id": "MOCK_SUCCESS"}

    # 더미 DB 테이블 생성
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_flaky_runner)
    result = scheduler.execute_single_observation(mode="live")

    assert result["status"] == "SUCCESS"
    assert result["attempt"] == 3
    assert len(attempts_log) == 3
    # 백오프 대기가 발생했는지 확인
    assert (attempts_log[1] - attempts_log[0]) >= 0.04
    assert (attempts_log[2] - attempts_log[1]) >= 0.06


def test_max_retries_exceeded_creates_failure_report(tmp_path):
    """지침 4: 최대 재시도(3회) 초과 시 무한 루프 돌지 않고 FAILED 종결 및 장애 보고서 배타적 생성 검증."""
    dummy_db = tmp_path / "dummy.db"
    dummy_lock = tmp_path / ".fail_test.lock"
    failure_dir = tmp_path / "failures"

    config = SchedulerConfig(
        enable_live_execution=True,
        max_retries=3,
        initial_backoff_sec=0.02,
        backoff_factor=1.0,
        db_path=dummy_db,
        lock_file=dummy_lock,
        report_dir=tmp_path / "reports",
        failure_dir=failure_dir,
    )

    def mock_failing_runner(*args, **kwargs):
        raise ValueError("지속적인 웹 스키마 변경 에러")

    scheduler = MarketObservationScheduler(config=config, pipeline_runner=mock_failing_runner)
    result = scheduler.execute_single_observation(mode="live")

    assert result["status"] == "FAILED"
    assert result["attempts"] == 3
    assert "failure_report" in result

    report_path = Path(result["failure_report"])
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "시장 관측 실패 보고서" in content
    assert "지속적인 웹 스키마 변경 에러" in content
    assert "무작정 자동 재실행 차단" in content


def test_daily_market_reporter_generates_markdown(tmp_path):
    """지침 5: DailyMarketReporter가 실제 운영 DB를 읽어 일별 마크다운 요약 리포트를 정상 생성하는지 검증."""
    op_db = Path("data/chaficial_market_timeseries.db")
    if not op_db.exists():
        pytest.skip("운영 DB가 존재하지 않아 일별 요약 리포트 테스트를 건너뜁니다.")

    reporter = DailyMarketReporter(db_path=op_db, output_dir=tmp_path / "reports")
    # 3차 관측이 일어난 2026-10-24 기준 요약 리포트 생성
    report_file = reporter.generate_daily_summary(target_date_str="2026-10-24")

    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "# CHA-FICIAL 일별 시장 관측 요약 보고서 (2026-10-24)" in content
    assert "listings" in content
    assert "348" in content
    assert "PRICE_DROP" in content
    assert "3,100,000원" in content  # 5건 가격 인하 총액
