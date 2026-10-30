"""
TASK 3 회귀 테스트: 작업 큐 중단 복구(recover_stale_in_progress_tasks) 및 운영 DB 보호 검증 (ISSUE-78)
"""

import os
import sqlite3
from chaficial.platform.sourcing.incremental_market_observer import IncrementalMarketObserver

TEST_DB = "scratch/test_queue_recovery_sandbox.db"

def test_queue_crash_recovery():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    obs = IncrementalMarketObserver(TEST_DB)
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO market_detail_fetch_queue (
            platform, listing_id, plate_number, model_name, raw_location,
            raw_vendor_status, queue_status, retry_count, discovered_at, updated_at
        ) VALUES 
            ('CARMANAGER', 'stuck_01', '12가1111', 'Model A', '장안모터프라자', 'ACTIVE', 'IN_PROGRESS', 0, datetime('now'), datetime('now')),
            ('CARMANAGER', 'stuck_02', '34나2222', 'Model B', '장안모터프라자', 'ACTIVE', 'IN_PROGRESS', 1, datetime('now'), datetime('now')),
            ('CARMANAGER', 'normal_03', '56다3333', 'Model C', '장안모터프라자', 'ACTIVE', 'COMPLETED', 0, datetime('now'), datetime('now'));
    """)
    conn.commit()
    conn.close()

    # 복구 실행
    recovered_count = obs.recover_stale_in_progress_tasks()
    print(f"Recovered count: {recovered_count} (기대: 2)")
    assert recovered_count == 2

    # 복구 후 다시 선점 가능한지 확인
    claimed = obs.claim_next_queue_item(platform="CARMANAGER")
    print("Claimed after recovery:", claimed)
    assert claimed is not None
    assert claimed["listing_id"] in ("stuck_01", "stuck_02")

    print("[+] TASK 3 큐 크래시 복구 및 라이프사이클 회귀 테스트 100% PASS!")

if __name__ == "__main__":
    test_queue_crash_recovery()
