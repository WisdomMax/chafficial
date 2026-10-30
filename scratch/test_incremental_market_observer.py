"""
TASK 6 테스트: IncrementalMarketObserver (50대 목록 저부하 증분 관측 검증)
"""

import os
import sqlite3
import time
from chaficial.platform.sourcing.incremental_market_observer import (
    IncrementalMarketObserver, MarketListingSummary, ObservationAction
)

TEST_DB = "scratch/test_incremental_observer_sandbox.db"

def setup_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE vehicles (
            id TEXT PRIMARY KEY,
            plate_number TEXT,
            model_name TEXT
        );

        CREATE TABLE vehicle_listings (
            id TEXT PRIMARY KEY,
            vehicle_id TEXT,
            platform TEXT,
            listing_id TEXT,
            advertised_price INTEGER,
            listing_status TEXT,
            last_observed_at TEXT
        );
    """)

    # 40대 기존 매물 삽입 (1~40번)
    for i in range(1, 41):
        v_id = f"veh_{i:03d}"
        c.execute("INSERT INTO vehicles (id, plate_number, model_name) VALUES (?, ?, ?)",
                  (v_id, f"12가{i:04d}", f"테스트차량 {i}"))
        c.execute("""
            INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, advertised_price, listing_status, last_observed_at)
            VALUES (?, ?, 'CARMANAGER', ?, ?, 'ACTIVE', '2026-10-30T12:00:00+09:00')
        """, (f"list_{i:03d}", v_id, f"CM_{i:04d}", 2000))
    
    conn.commit()
    conn.close()

def test_observer_batch():
    setup_test_db()
    observer = IncrementalMarketObserver(TEST_DB)

    # 50대 관측 배치 준비:
    # 1~35번: 기존 매물, 가격 동일(2000만) -> NO_CHANGE
    # 36~40번: 기존 매물, 가격 변경(2000만 -> 1950만) -> UPDATE_PRICE_STATUS
    # 41~50번: 신규 매물 -> SCHEDULE_DEEP_FETCH
    batch = []
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")

    for i in range(1, 51):
        price = 1950 if (36 <= i <= 40) else 2000
        batch.append(MarketListingSummary(
            listing_id=f"CM_{i:04d}",
            platform="CARMANAGER",
            plate_number=f"12가{i:04d}",
            model_name=f"테스트차량 {i}",
            advertised_price=price,
            status="ACTIVE",
            raw_location="장안모터프라자",
            observed_at=now_iso
        ))

    diffs = observer.inspect_batch(batch, platform="CARMANAGER")

    no_change = [d for d in diffs if d.action == ObservationAction.NO_CHANGE]
    update_price = [d for d in diffs if d.action == ObservationAction.UPDATE_PRICE_STATUS]
    deep_fetch = [d for d in diffs if d.action == ObservationAction.SCHEDULE_DEEP_FETCH]

    print(f"Total diffs: {len(diffs)}")
    print(f"NO_CHANGE: {len(no_change)} (기대: 35)")
    print(f"UPDATE_PRICE_STATUS: {len(update_price)} (기대: 5)")
    print(f"SCHEDULE_DEEP_FETCH: {len(deep_fetch)} (기대: 10)")

    assert len(no_change) == 35
    assert len(update_price) == 5
    assert len(deep_fetch) == 10

    # 경량 업데이트 실행
    applied = observer.apply_lightweight_updates(diffs, platform="CARMANAGER")
    print(f"Applied lightweight updates: {applied}건")
    assert applied == 5

    # DB 검증: 36번 매물 가격 확인
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("SELECT advertised_price, last_observed_at FROM vehicle_listings WHERE listing_id = 'CM_0036'")
    row = c.fetchone()
    conn.close()

    print(f"CM_0036 DB state: price={row[0]}, observed_at={row[1]}")
    assert row[0] == 1950
    assert row[1] == now_iso

    print("[+] TASK 6 저부하 50대 목록 증분 관측 검증 100% PASS!")

if __name__ == "__main__":
    test_observer_batch()
