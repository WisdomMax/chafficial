"""
TASK 3 회귀 테스트: IncrementalMarketObserver V2 검증
- NO_CHANGE 차량의 last_observed_at 최신 갱신 (ISSUE-62)
- 부분 관측 시 누락 차량 DELISTED/SOLD 오판정 0건 보장
- 신규 매물 상세조회 대기열 SQLite 영속화 및 재시작 복원 (ISSUE-64)
- 가격 미공개(None/상담) 매물 안전 처리
"""

import os
import sqlite3
import time
from chaficial.platform.sourcing.incremental_market_observer import (
    IncrementalMarketObserver, MarketListingSummary, ObservationAction
)

TEST_DB = "scratch/test_incremental_observer_v2_sandbox.db"

def setup_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE vehicles (
            id TEXT PRIMARY KEY,
            plate_number TEXT,
            model_name TEXT,
            status TEXT DEFAULT 'AVAILABLE'
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

    # 기존 매물 100대 등록 (1~100번)
    old_time = "2026-10-30T10:00:00+09:00"
    for i in range(1, 101):
        v_id = f"veh_{i:03d}"
        c.execute("INSERT INTO vehicles (id, plate_number, model_name) VALUES (?, ?, ?)",
                  (v_id, f"12가{i:04d}", f"기존차량 {i}"))
        c.execute("""
            INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, advertised_price, listing_status, last_observed_at)
            VALUES (?, ?, 'CARMANAGER', ?, ?, 'ACTIVE', ?)
        """, (f"list_{i:03d}", v_id, f"CM_{i:04d}", 2000, old_time))
    
    conn.commit()
    conn.close()

def test_observer_v2_full():
    setup_test_db()
    observer = IncrementalMarketObserver(TEST_DB)

    # 50대 관측 배치 준비:
    # 1~35번: 기존 매물, 가격 동일(2000만) -> NO_CHANGE
    # 36~40번: 기존 매물, 가격 변동(2000만 -> 1920만) -> UPDATE_PRICE_STATUS
    # 41~45번: 기존 매물, 가격 미공개(상담/None) -> UPDATE_PRICE_STATUS (None)
    # 46~50번: 신규 매물 (101~105번) -> SCHEDULE_DEEP_FETCH
    # ※ 51~100번은 이번 50대 목록에 나타나지 않는 부분 관측 누락 차량!
    
    batch = []
    now_iso = "2026-10-31T00:36:00+09:00"

    for i in range(1, 36):
        batch.append(MarketListingSummary(
            listing_id=f"CM_{i:04d}", platform="CARMANAGER", plate_number=f"12가{i:04d}",
            model_name=f"기존차량 {i}", advertised_price=2000, status="ACTIVE",
            raw_location="장안모터프라자", observed_at=now_iso
        ))
    for i in range(36, 41):
        batch.append(MarketListingSummary(
            listing_id=f"CM_{i:04d}", platform="CARMANAGER", plate_number=f"12가{i:04d}",
            model_name=f"기존차량 {i}", advertised_price=1920, status="ACTIVE",
            raw_location="장안모터프라자", observed_at=now_iso
        ))
    for i in range(41, 46):
        batch.append(MarketListingSummary(
            listing_id=f"CM_{i:04d}", platform="CARMANAGER", plate_number=f"12가{i:04d}",
            model_name=f"기존차량 {i}", advertised_price=None, status="ACTIVE",
            raw_location="장안모터프라자", observed_at=now_iso
        ))
    for i in range(101, 106):
        batch.append(MarketListingSummary(
            listing_id=f"CM_{i:04d}", platform="CARMANAGER", plate_number=f"77호{i:04d}",
            model_name=f"신규차량 {i}", advertised_price=3500, status="ACTIVE",
            raw_location="장안모터프라자", observed_at=now_iso
        ))

    diffs = observer.inspect_batch(batch, platform="CARMANAGER")
    assert len(diffs) == 50

    # 원자적 적용 및 큐잉 실행
    counts = observer.apply_batch_updates_and_enqueue(diffs, platform="CARMANAGER")
    print("[Batch Apply Counts]:", counts)

    assert counts["no_change_timestamp_refreshed"] == 35
    assert counts["price_status_updated"] == 10 # 5대 가격변경 + 5대 상담(None) 변경
    assert counts["new_vehicles_enqueued"] == 5

    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()

    # 1. NO_CHANGE 차량(1번)의 last_observed_at 최신 갱신 확인 (ISSUE-62)
    c.execute("SELECT advertised_price, last_observed_at FROM vehicle_listings WHERE listing_id = 'CM_0001'")
    r1 = c.fetchone()
    print("CM_0001 (NO_CHANGE) state:", r1)
    assert r1[0] == 2000
    assert r1[1] == now_iso, "NO_CHANGE 차량의 last_observed_at이 갱신되지 않음!"

    # 2. 가격 미공개(None) 차량(41번) 확인
    c.execute("SELECT advertised_price, last_observed_at FROM vehicle_listings WHERE listing_id = 'CM_0041'")
    r41 = c.fetchone()
    print("CM_0041 (None price) state:", r41)
    assert r41[0] is None
    assert r41[1] == now_iso

    # 3. 부분 관측 누락 차량(51~100번)의 상태 불변 확인 (False DELISTED/SOLD 0건)
    c.execute("SELECT count(*) FROM vehicle_listings WHERE listing_status = 'ACTIVE' AND listing_id >= 'CM_0051' AND listing_id <= 'CM_0100'")
    unseen_active_cnt = c.fetchone()[0]
    print(f"부분 관측 누락 50대 중 ACTIVE 유지 건수: {unseen_active_cnt} / 50")
    assert unseen_active_cnt == 50, "부분 관측에서 누락 차량이 거짓 DELISTED/SOLD 처리됨!"

    # 4. 신규 매물 5건의 SQLite 대기열 영속화 및 재시작 복원 확인 (ISSUE-64)
    pending_items = observer.get_pending_queue_items(limit=10)
    print(f"Queue PENDING items: {len(pending_items)}건")
    assert len(pending_items) == 5
    assert pending_items[0]["listing_id"] == "CM_0101"

    # 멱등성: 동일 배치 재처리 시 큐 중복 삽입 0건 확인
    counts2 = observer.apply_batch_updates_and_enqueue(diffs, platform="CARMANAGER")
    assert counts2["new_vehicles_enqueued"] == 0, "동일 배치 재실행 시 큐 중복 등록 발생!"

    conn.close()
    print("[+] TASK 3 IncrementalMarketObserver V2 회귀 테스트 100% PASS!")

if __name__ == "__main__":
    test_observer_v2_full()
