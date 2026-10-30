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
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
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
    print("[*] Test 1: Production DB Protection Guard against Historical Replay...")
    # Chamart real production path emulation
    temp_dir = tempfile.mkdtemp()
    fake_prod_db = os.path.join(temp_dir, "chamart_platform_demo.db")
    setup_isolated_db(fake_prod_db)

    # Calling run_sync_pipeline without live collector against a DB named 'chamart_platform_demo.db'
    # MUST automatically force dry_run=True to prevent operational pollution!
    res = run_sync_pipeline(use_live_collector=False, dry_run=False, db_path=fake_prod_db)
    assert res["dry_run"] is True, "FAIL: Historical replay against production DB must force dry_run=True!"
    print("  -> PASS: Historical replay write to production DB was blocked and forced to DRY_RUN!")
    shutil.rmtree(temp_dir)

def test_raw_sha256_duplicate_event_guard():
    print("[*] Test 2: Raw SHA256 Replay Event Duplication Guard...")
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_replay_sandbox.db")
    setup_isolated_db(test_db)

    ts_engine = MarketTimeSeriesEngine(db_path=test_db, dry_run=False)

    # Mock snapshot
    cars_data = [
        {"encarno": f"TEST_{i:04d}", "car_no": f"12가{i:04d}", "price": 1500, "shop": "상사A", "model": "아반떼"}
        for i in range(1, 20)
    ]

    # Run 1: First snapshot ingestion
    res1 = ts_engine.record_snapshot(cars_data, source="CARMANAGER")
    assert res1["status"] == "SUCCESS", f"FAIL: Run 1 expected SUCCESS, got {res1['status']}"
    assert res1["appeared_count"] == 19, f"FAIL: Run 1 expected 19 appeared, got {res1['appeared_count']}"

    # Run 2: Exact same raw snapshot re-submitted
    res2 = ts_engine.record_snapshot(cars_data, source="CARMANAGER")
    assert res2["status"] == "ALREADY_RECORDED_HASH", f"FAIL: Run 2 expected ALREADY_RECORDED_HASH, got {res2['status']}"
    assert res2["events_count"] == 0, f"FAIL: Run 2 must generate 0 events, got {res2['events_count']}"
    assert res2["appeared_count"] == 0, f"FAIL: Run 2 must generate 0 appeared events, got {res2['appeared_count']}"
    print("  -> PASS: Duplicate raw_sha256 snapshot safely recognized and generated 0 duplicate events!")
    shutil.rmtree(temp_dir)

def test_independent_db_invariance():
    print("[*] Test 3: Independent DB Historical Invariance Verification...")
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_invariance_sandbox.db")
    setup_isolated_db(test_db)

    # First run: run full pipeline on local historical dataset
    res1 = run_sync_pipeline(use_live_collector=False, dry_run=False, db_path=test_db)
    assert res1["status"] == "SUCCESS"
    assert res1["dry_run"] is False

    # Inspect record counts
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM vehicle_listings WHERE platform = 'CARMANAGER'")
    initial_listing_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM market_listing_events")
    initial_event_count = c.fetchone()[0]
    conn.close()

    assert initial_listing_count > 0, "Initial listings must be inserted"

    # Second run: run again with same historical dataset
    res2 = run_sync_pipeline(use_live_collector=False, dry_run=False, db_path=test_db)
    assert res2["status"] == "SUCCESS"

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM vehicle_listings WHERE platform = 'CARMANAGER'")
    second_listing_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM market_listing_events")
    second_event_count = c.fetchone()[0]
    conn.close()

    assert initial_listing_count == second_listing_count, f"Listing count must be identical: {initial_listing_count} vs {second_listing_count}"
    assert initial_event_count == second_event_count, f"Event count must be identical (no fake price/appeared events on repeat run): {initial_event_count} vs {second_event_count}"
    print(f"  -> PASS: Database invariant verified across duplicate runs (Listings={initial_listing_count}, Events={initial_event_count})!")
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_production_file_guard()
    test_raw_sha256_duplicate_event_guard()
    test_independent_db_invariance()
    print("\n[+] ALL DIRECTIVE 126 TASK 1 REPRESSION TESTS PASSED 100%!")
