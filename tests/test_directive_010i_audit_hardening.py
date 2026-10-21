"""CHA-FICIAL AI PROJECT - DIRECTIVE 010-I
PR #10 최종 승인을 위한 3대 핵심 감사 보완 테스트 세트:
1. 실제 DB 부분 쓰기(flush) 후 롤백 및 논리 해시 보존 검증
2. 과거 데이터 보존 및 실제 DB Mutation(변조/복구) 테스트
3. 백업 경로 배타적 예약 및 실제 멀티프로세스 잠금 경합 검증
"""

import json
import multiprocessing
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import sessionmaker

from chaficial.database.base import Base
from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.tracker.price_tracker import compute_db_logical_hashes
from scripts.run_directive_010_market_stream import (
    FileLockContext,
    OperationalLockError,
    backup_operational_db_safe,
    run_pipeline,
)

RAW_OBS_FILE_1 = Path("data/raw_observations/encar_cn7_live_20261021_01.json")
RAW_OBS_FILE_2 = Path("data/raw_observations/encar_cn7_live_20261021_120825.json")


# ==============================================================================
# 1. 실제 DB 부분 쓰기 후 롤백 검증
# ==============================================================================
def test_db_partial_write_rollback_preserves_hashes(tmp_path):
    """지침 1: 신규 배치 중 50개 행 부분 쓰기(flush) 후 예외 발생 시 트랜잭션 롤백 및 기존 데이터 불변 검증."""
    test_db = tmp_path / "rollback_test.db"

    # 1. 테스트 DB에 1차 배치 정상 적재
    run_pipeline(mode="replay", input_file=str(RAW_OBS_FILE_1), db_path_override=test_db)

    # 1차 적재 직후 DB 기준 상태 및 논리 해시 저장
    engine = create_engine(f"sqlite:///{test_db}")
    with sessionmaker(bind=engine)() as s:
        baseline_hashes = compute_db_logical_hashes(s)
        baseline_listings = set(s.execute(select(Listing.listing_id)).scalars().all())
        baseline_snapshots = set(s.execute(select(ListingSnapshot.snapshot_id)).scalars().all())
        baseline_batches = s.execute(select(func.count(BatchAuditLog.batch_id))).scalar()
        assert len(baseline_listings) == 126
        assert len(baseline_snapshots) == 126
        assert baseline_batches == 1

    # 2. 2차 배치 실행 중 50개 행 부분 쓰기(flush) 후 의도적 예외 주입
    with pytest.raises(RuntimeError, match="Simulated DB Ingest Failure After 50 Records Written"):
        run_pipeline(
            mode="replay",
            input_file=str(RAW_OBS_FILE_2),
            db_path_override=test_db,
            test_hook_fail_after_records=50,
        )

    # 3. 예외 발생 후 완전히 새로운 독립 DB 세션을 열어 무결성 검증
    with sessionmaker(bind=engine)() as s:
        post_hashes = compute_db_logical_hashes(s)
        post_listings = set(s.execute(select(Listing.listing_id)).scalars().all())
        post_snapshots = set(s.execute(select(ListingSnapshot.snapshot_id)).scalars().all())
        post_batches = s.execute(select(func.count(BatchAuditLog.batch_id))).scalar()

        # 기존 1차 적재 데이터가 단 1비트도 변하지 않고 100% 동일한지 검증
        assert post_listings == baseline_listings, "롤백 실패: 신규 매물이 잔존하거나 기존 매물이 훼손되었습니다."
        assert post_snapshots == baseline_snapshots, "롤백 실패: 신규 스냅샷이 잔존합니다."
        assert post_batches == 1, "롤백 실패: 미완료 배치의 감사 로그가 잔존합니다."

        for tbl, info in baseline_hashes.items():
            assert post_hashes[tbl]["hash"] == info["hash"], f"테이블 {tbl}의 논리 해시가 변경되었습니다!"
            assert post_hashes[tbl]["count"] == info["count"]


# ==============================================================================
# 2. 과거 데이터 보존 및 실제 Mutation(변조/복구) 테스트
# ==============================================================================
def test_past_data_preservation_and_real_mutation_test(tmp_path):
    """지침 2: 1차 배치 스냅샷 전체 속성 동결 비교 및 실제 DB 레코드 변조(Mutation) 감지·복구 실증."""
    test_db = tmp_path / "mutation_test.db"

    # 1. 1차 배치 적재
    run_pipeline(mode="replay", input_file=str(RAW_OBS_FILE_1), db_path_override=test_db)

    engine = create_engine(f"sqlite:///{test_db}")
    Session = sessionmaker(bind=engine)

    # 1차 배치의 126건 스냅샷 전체 영속 필드를 고정 기준 데이터(Baseline)로 추출
    snapshot_baseline: dict[str, dict] = {}
    with Session() as s:
        for snap in s.execute(select(ListingSnapshot)).scalars().all():
            snapshot_baseline[snap.snapshot_id] = {
                "listing_id": snap.listing_id,
                "price_krw": snap.price_krw,
                "mileage_km": snap.mileage_km,
                "listing_status": snap.listing_status,
                "observed_at": snap.observed_at,
            }
    assert len(snapshot_baseline) == 126

    # 1차 배치의 126대 매물 불변 필드를 고정 기준 데이터(Baseline)로 추출
    listing_baseline: dict[str, dict] = {}
    with Session() as s:
        for l in s.execute(select(Listing)).scalars().all():
            listing_baseline[l.listing_id] = {
                "source_platform": l.source_platform,
                "source_listing_id": l.source_listing_id,
                "first_observed_at": l.first_observed_at,
                "raw_location": l.raw_location,
            }
    assert len(listing_baseline) == 126

    # 2. 2차 배치 정상 적재 (시계열 누적)
    run_pipeline(mode="replay", input_file=str(RAW_OBS_FILE_2), db_path_override=test_db)

    # 3. 2차 적재 후에도 1차 스냅샷 126건 및 매물 불변 필드가 100% 보존되었는지 검증
    def verify_all_past_records(session):
        current_snaps = {
            snap.snapshot_id: snap for snap in session.execute(select(ListingSnapshot)).scalars().all()
        }
        for snap_id, expected in snapshot_baseline.items():
            if snap_id not in current_snaps:
                return False, f"스냅샷 유실: {snap_id}"
            actual = current_snaps[snap_id]
            if actual.price_krw != expected["price_krw"]:
                return False, f"가격 변조 감지: {actual.price_krw} != {expected['price_krw']}"
            if actual.mileage_km != expected["mileage_km"]:
                return False, f"주행거리 변조 감지: {actual.mileage_km} != {expected['mileage_km']}"
            if actual.observed_at != expected["observed_at"]:
                return False, f"관측시각 변조 감지: {actual.observed_at} != {expected['observed_at']}"

        current_listings = {
            l.listing_id: l for l in session.execute(select(Listing)).scalars().all()
        }
        for l_id, exp_l in listing_baseline.items():
            if l_id not in current_listings:
                return False, f"매물 유실: {l_id}"
            act_l = current_listings[l_id]
            if act_l.source_listing_id != exp_l["source_listing_id"]:
                return False, f"매물 소스 ID 변조 감지: {act_l.source_listing_id}"
            if act_l.raw_location != exp_l["raw_location"]:
                return False, f"매물 위치 변조 감지: {act_l.raw_location} != {exp_l['raw_location']}"

        return True, "ALL_PAST_RECORDS_PRESERVED"

    with Session() as s:
        ok, msg = verify_all_past_records(s)
        assert ok is True, f"과거 데이터 보존 검증 실패: {msg}"

    # 4. 실제 Mutation Test (DB 실제 UPDATE 주입 및 감지 증명)
    target_listing_id = list(listing_baseline.keys())[0]
    original_loc = listing_baseline[target_listing_id]["raw_location"]
    tampered_loc = "TAMPERED_INJECTED_LOCATION_MUTATION"

    with Session() as s:
        # 실제 SQLite DB 테이블 레코드 값 변조 수행
        s.execute(
            update(Listing)
            .where(Listing.listing_id == target_listing_id)
            .values(raw_location=tampered_loc)
        )
        s.commit()

        # 변조 상태에서 검증 수행 -> 반드시 실패해야 함!
        ok_tampered, msg_tampered = verify_all_past_records(s)
        assert ok_tampered is False, "Mutation 감지 실패: 변조된 위치가 감지되지 않았습니다."
        assert "매물 위치 변조 감지" in msg_tampered

        # 5. 원래 값으로 DB 레코드 복원
        s.execute(
            update(Listing)
            .where(Listing.listing_id == target_listing_id)
            .values(raw_location=original_loc)
        )
        s.commit()

        # 복구 상태에서 검증 재수행 -> 반드시 성공해야 함!
        ok_restored, msg_restored = verify_all_past_records(s)
        assert ok_restored is True, f"원상 복구 후 검증 실패: {msg_restored}"


# ==============================================================================
# 3. 백업 경로 배타적 예약 및 실제 멀티프로세스 잠금 경합 검증
# ==============================================================================
def _child_process_hold_lock(lock_file_path: str, hold_seconds: float):
    """독립 OS 자식 프로세스에서 락을 획득하고 일정 시간 유지하는 함수."""
    with FileLockContext(Path(lock_file_path)):
        time.sleep(hold_seconds)


def test_backup_exclusive_reservation_and_multiprocess_lock_contention(tmp_path):
    """지침 3: 백업 경로 배타적 생성 및 실제 2개 독립 OS 프로세스 간 실행 락 경합 검증."""
    dummy_db = tmp_path / "dummy.db"
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    # 1. 백업 배타적 생성 검증
    backup_path = backup_operational_db_safe(dummy_db)
    assert backup_path is not None and backup_path.exists()

    # 2. 독립 프로세스 간 실제 잠금 경합 검증
    lock_file = tmp_path / "proc_contention.lock"

    # 자식 프로세스 시작 (0.8초간 락 유지)
    p = multiprocessing.Process(target=_child_process_hold_lock, args=(str(lock_file), 0.8))
    p.start()
    time.sleep(0.2)  # 자식 프로세스가 락을 잡을 때까지 잠시 대기

    try:
        # 부모 프로세스가 동일 락으로 LIVE 진입 시도 -> 즉시 OperationalLockError 발생
        with pytest.raises(OperationalLockError, match="다른 관측 프로세스가 이미 실행 중입니다"):
            run_pipeline(mode="live", db_path_override=dummy_db, lock_file_path=lock_file)
    finally:
        p.join()

    # 자식 프로세스 종료 후 -> 부모 프로세스가 락을 정상 획득할 수 있는지 확인
    with FileLockContext(lock_file):
        pass  # 락 정상 획득 완료
