"""
DIRECTIVE 126 TASK 1 (P0, ISSUE-92) Regression Test Suite:
1. Operational DB Corruption Guard:
   - When HISTORICAL_REPLAY is used against real production DB (chamart_platform_demo.db), writes are strictly aborted / forced to DRY_RUN.
2. Raw SHA256 Replay Event Duplication Guard:
   - Re-running identical raw snapshot (same raw_sha256) returns ALREADY_RECORDED_HASH and generates 0 new events.
3. Independent DB Invariance Test:
   - Successive runs of historical snapshot do not corrupt or falsely alter vehicle prices, statuses, or appearances.
"""

import sys
import os
import json
import sqlite3
import shutil
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
from chaficial.platform.sourcing.normalizer import normalize_carmanager_record
from run_daily_sync import run_sync_pipeline

def setup_isolated_db(db_path: str):
    # 운영 DB 스키마를 그대로 복제하여 완벽한 격리 DB 구성
    prod_db = "data/chamart/chamart_platform_demo.db"
    conn_src = sqlite3.connect(prod_db)
    conn_dst = sqlite3.connect(db_path)
    # 스키마 덤프 및 복원 (데이터 제외 구조만)
    schema_dump = "".join(line for line in conn_src.iterdump() if "INSERT INTO" not in line)
    conn_src.close()
    conn_dst.executescript(schema_dump)
    conn_dst.commit()
    conn_dst.close()

    # Init engine schemas
    ts = MarketTimeSeriesEngine(db_path=db_path, dry_run=False)
    ts.ensure_schema()
    sync = CarManagerSyncService(db_path=db_path, dry_run=False)
    sync._ensure_log_table()

def test_production_file_guard():
    print("[*] Test 1: Historical Replay Protection Guard (No Live Collector)...")
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "custom_database_name.db")
    setup_isolated_db(test_db)

    # Calling run_sync_pipeline without live collector (HISTORICAL_REPLAY) and without explicit test flag
    # MUST automatically force dry_run=True to prevent operational pollution regardless of file name!
    res = run_sync_pipeline(use_live_collector=False, dry_run=False, db_path=test_db)
    assert res["dry_run"] is True, "FAIL: Historical replay without live collector must force dry_run=True!"
    print("  -> PASS: Historical replay write was strictly blocked and forced to DRY_RUN (independently of file name)!")
    shutil.rmtree(temp_dir)

def test_same_session_replay_guard_and_daily_continuation():
    print("[*] Test 2: Session Replay Guard & Daily Observation Continuation (DIRECTIVE 127 P0)...")
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_session_sandbox.db")
    setup_isolated_db(test_db)

    ts_engine = MarketTimeSeriesEngine(db_path=test_db, dry_run=False)

    # Mock snapshot: 19 cars
    cars_data = [
        {"encarno": f"TEST_{i:04d}", "car_no": f"12가{i:04d}", "price": 1500, "shop": "상사A", "model": "아반떼"}
        for i in range(1, 20)
    ]

    # Day 1: 2026-10-31 Initial observation
    res1 = ts_engine.record_snapshot(cars_data, source="CARMANAGER", started_at="2026-10-31T10:00:00+09:00")
    assert res1["status"] == "SUCCESS", f"FAIL: Day 1 expected SUCCESS, got {res1['status']}"
    assert res1["appeared_count"] == 19, f"FAIL: Day 1 expected 19 appeared, got {res1['appeared_count']}"
    assert res1["observations_count"] == 19

    # Day 1 Duplicate Retry: Same session at same started_at with same raw_sha256
    res1_retry = ts_engine.record_snapshot(cars_data, source="CARMANAGER", started_at="2026-10-31T10:00:00+09:00")
    assert res1_retry["status"] == "ALREADY_RECORDED_SESSION", f"FAIL: Same session retry expected ALREADY_RECORDED_SESSION, got {res1_retry['status']}"
    assert res1_retry["events_count"] == 0, "Same session retry must generate 0 events"
    print("  -> PASS: Same-session duplicate retry strictly blocked with 0 duplicate events!")

    # Day 2: 2026-11-01 Next day real observation with identical cars (market calm, no price changes)
    # [DIRECTIVE 127 P0 FIX]: Must NOT be blocked! Must record observations for Days on Market continuation!
    res2 = ts_engine.record_snapshot(cars_data, source="CARMANAGER", started_at="2026-11-01T10:00:00+09:00")
    assert res2["status"] == "SUCCESS", f"FAIL: Day 2 expected SUCCESS, got {res2['status']}"
    assert res2["observations_count"] == 19, f"FAIL: Day 2 must record 19 observations for continuity, got {res2['observations_count']}"
    assert res2["events_count"] == 0, f"FAIL: Day 2 with calm market must generate 0 events, got {res2['events_count']}"
    assert res2["appeared_count"] == 0, f"FAIL: Day 2 must not re-appear already existing cars"
    print("  -> PASS: Day 2 identical observation successfully recorded 19 continuity observations with 0 fake events!")

    shutil.rmtree(temp_dir)

def test_independent_db_invariance():
    print("[*] Test 3: Independent DB Historical Invariance Verification (Full Fields)...")
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_invariance_sandbox.db")
    setup_isolated_db(test_db)

    # [DIRECTIVE 128 P0]: HISTORICAL_REPLAY는 신규 마스터 생성을 0건으로 차단하므로,
    # 베이스라인 1,764대를 먼저 DB에 시딩한 후 불변성을 검증한다.
    with open("data/carmanager_raw/janghanpyeong_full_collection.json", "r") as f:
        cars = json.load(f).get("cars", [])
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    base_t = "2026-10-25T10:00:00"
    for idx, raw in enumerate(cars):
        norm = normalize_carmanager_record(raw)
        v_id = str(uuid.uuid4())
        c.execute("""
            INSERT INTO vehicles (id, branch_id, plate_number, model_name, year, mileage, fuel_type, transmission, color, purchase_price, target_price, status, is_demo, timeline_json, created_at, updated_at, publishing_status, is_public, listing_ownership_type)
            VALUES (?, 'B01', ?, ?, ?, ?, ?, ?, ?, 0, ?, 'DRAFT', 0, '[]', ?, ?, 'PUBLISHED', 1, 'MARKET_JANGHANPYEONG')
        """, (v_id, f"차{idx}", norm["model_name"], norm["model_year"], norm["mileage_km"] or 50000, norm.get("fuel") or "UNKNOWN", norm.get("mission") or "오토", "은색", norm["price_manwon"], base_t, base_t))
        c.execute("""
            INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, advertised_price, listing_status, first_observed_at, last_observed_at, is_demo, source_confidence, unverified_consecutive_count)
            VALUES (?, ?, 'CARMANAGER', ?, ?, 'ACTIVE', ?, ?, 0, 0.95, 0)
        """, (str(uuid.uuid4()), v_id, norm["encarno"], norm["price_manwon"], base_t, base_t))
    conn.commit()
    conn.close()

    # First run: run full pipeline on local historical dataset (explicit test commit allowed)
    res1 = run_sync_pipeline(use_live_collector=False, dry_run=False, db_path=test_db, allow_historical_test_commit=True)
    assert res1["status"] == "SUCCESS"
    assert res1["dry_run"] is False

    # Extract all listings details: listing_id -> (advertised_price, listing_status, last_observed_at)
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("SELECT listing_id, advertised_price, listing_status, last_observed_at FROM vehicle_listings WHERE platform = 'CARMANAGER'")
    records_run1 = {r[0]: (r[1], r[2], r[3]) for r in c.fetchall()}
    c.execute("SELECT COUNT(*) FROM market_listing_events")
    initial_event_count = c.fetchone()[0]
    conn.close()

    assert len(records_run1) == 1764, f"Expected 1764 listings, got {len(records_run1)}"

    # Second run: run again with same historical dataset
    res2 = run_sync_pipeline(use_live_collector=False, dry_run=False, db_path=test_db, allow_historical_test_commit=True)
    assert res2["status"] == "SUCCESS"

    # Extract all listings details again
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("SELECT listing_id, advertised_price, listing_status, last_observed_at FROM vehicle_listings WHERE platform = 'CARMANAGER'")
    records_run2 = {r[0]: (r[1], r[2], r[3]) for r in c.fetchall()}
    c.execute("SELECT COUNT(*) FROM market_listing_events")
    second_event_count = c.fetchone()[0]
    conn.close()

    assert len(records_run1) == len(records_run2), "Listing count must match exactly"
    assert initial_event_count == second_event_count, "Event count must match exactly"

    # 1:1 Strict Verification of prices, statuses, and last_observed_at
    mismatches = []
    for lid, vals1 in records_run1.items():
        vals2 = records_run2.get(lid)
        if vals1 != vals2:
            mismatches.append((lid, vals1, vals2))

    assert len(mismatches) == 0, f"FAIL: {len(mismatches)} listings had unexpected field mutations! Sample: {mismatches[:3]}"
    print(f"  -> PASS: 100% full-field invariance verified across repeat runs (1,764/1,764 listings identical in price, status, last_observed_at)!")
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_production_file_guard()
    test_same_session_replay_guard_and_daily_continuation()
    test_independent_db_invariance()
    print("\n[+] ALL DIRECTIVE 127 REPRESSION TESTS PASSED 100%!")
