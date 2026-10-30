"""
TASK 5 회귀 테스트: 상세조회 큐 원자적 선점 및 동시성 검증 (ISSUE-72)
"""

import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from chaficial.platform.sourcing.incremental_market_observer import IncrementalMarketObserver

TEST_DB = "scratch/test_queue_concurrency_sandbox.db"

def setup_queue_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    obs = IncrementalMarketObserver(TEST_DB)
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    # 5개의 PENDING 작업 삽입
    for i in range(1, 6):
        c.execute("""
            INSERT INTO market_detail_fetch_queue (
                platform, listing_id, plate_number, model_name, raw_location,
                raw_vendor_status, queue_status, retry_count, discovered_at, updated_at
            ) VALUES ('CARMANAGER', ?, ?, 'Test Model', '장안모터프라자', 'ACTIVE', 'PENDING', 0, datetime('now'), datetime('now'))
        """, (f"car_q_{i:02d}", f"12가{i:04d}"))
    conn.commit()
    conn.close()

def test_queue_concurrency():
    setup_queue_db()
    obs = IncrementalMarketObserver(TEST_DB)

    claimed_items = []

    def worker_claim(worker_id):
        # 각 워커가 선점 시도
        item = obs.claim_next_queue_item(platform="CARMANAGER")
        if item:
            return item["listing_id"]
        return None

    # 10개 스레드로 5개 작업 동시 선점 경쟁
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(worker_claim, range(10)))

    successful_claims = [r for r in results if r is not None]
    print(f"Total claims: {len(successful_claims)}, Unique claims: {len(set(successful_claims))}")
    print("Claimed IDs:", successful_claims)

    assert len(successful_claims) == 5, "5개 작업이 모두 선점되어야 함"
    assert len(successful_claims) == len(set(successful_claims)), "동일 작업이 둘 이상의 워커에 중복 선점됨!"

    # 3회 실패 시 관리자 검토 전이 확인
    obs.mark_queue_item_failed("CARMANAGER", "car_q_01", "Network Timeout 1", max_retries=3)
    obs.mark_queue_item_failed("CARMANAGER", "car_q_01", "Network Timeout 2", max_retries=3)
    obs.mark_queue_item_failed("CARMANAGER", "car_q_01", "Network Timeout 3", max_retries=3)

    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("SELECT queue_status, retry_count FROM market_detail_fetch_queue WHERE listing_id = 'car_q_01'")
    r = c.fetchone()
    conn.close()

    print("car_q_01 status after 3 failures:", r)
    assert r[0] == "REQUIRES_ADMIN_REVIEW"
    assert r[1] == 3

    print("[+] TASK 5 상세조회 큐 원자적 선점 및 동시성 검증 100% PASS!")

if __name__ == "__main__":
    test_queue_concurrency()
