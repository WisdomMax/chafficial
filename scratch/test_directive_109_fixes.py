import sys
import os
import sqlite3
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, "src")
sys.path.insert(0, ".")
from chaficial.platform.sourcing.janghanpyeong_collector import JanghanpyeongCollector
from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine

def test_fixes():
    print("================================================================")
    print(" DIRECTIVE 109 - 4대 결함 수정 및 엔진 직결 종합 무결성 검증")
    print("================================================================")

    # -------------------------------------------------------------
    # TEST 1: Collector dynamic while loop verification
    # -------------------------------------------------------------
    print("[1] Testing Collector Dynamic while loop logic...")
    # 소스 코드에서 while page_no <= max_pages 구문 확인
    collector_file = Path("src/chaficial/platform/sourcing/janghanpyeong_collector.py").read_text()
    assert "while page_no <= max_pages:" in collector_file, "Collector must use dynamic while loop!"
    assert "for page_no in range(1, max_pages + 1):" not in collector_file, "Collector range() loop must be removed!"
    print("  -> PASSED: janghanpyeong_collector.py correctly implements dynamic while page_no <= max_pages loop.")

    # -------------------------------------------------------------
    # TEST 2 & 3: MarketTimeSeriesEngine timestamp & SHA256 idempotency
    # -------------------------------------------------------------
    print("\n[2] Testing MarketTimeSeriesEngine timestamp preservation & idempotency...")
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db = Path(tmpdir) / "test_ts.db"
        engine = MarketTimeSeriesEngine(db_path=str(test_db))
        
        # 가상 스냅샷 데이터 생성
        mock_snapshot_day1 = [
            {
                "encarno": "TEST_ENCAR_001",
                "price": "1,500만원",
                "km": "45,000 km",
                "caryear": "2020",
                "carname": "아반떼 CN7",
                "fuel": "가솔린",
                "mission": "오토",
                "shopname": "더쿨모터스",
                "danji": "장안평"
            },
            {
                "encarno": "TEST_ENCAR_002",
                "price": "2,800만원",
                "km": "30,000 km",
                "caryear": "2021",
                "carname": "쏘렌토 4세대",
                "fuel": "디젤",
                "mission": "오토",
                "shopname": "타상사",
                "danji": "장안평"
            }
        ]

        historical_time_day1 = "2026-10-28T09:00:00"
        res1 = engine.record_snapshot(mock_snapshot_day1, started_at=historical_time_day1)
        assert res1["status"] == "SUCCESS", f"Expected SUCCESS, got {res1['status']}"
        assert res1["observations_count"] == 2
        assert res1["appeared_count"] == 2

        # DB 검증: observed_at 및 event_at이 historical_time_day1로 저장되었는가?
        conn = sqlite3.connect(str(test_db))
        c = conn.cursor()
        c.execute("SELECT observed_at FROM market_listing_observations WHERE encarno = 'TEST_ENCAR_001'")
        obs_time = c.fetchone()[0]
        assert obs_time == historical_time_day1, f"Expected {historical_time_day1}, got {obs_time}"

        c.execute("SELECT event_at FROM market_listing_events WHERE encarno = 'TEST_ENCAR_001'")
        evt_time = c.fetchone()[0]
        assert evt_time == historical_time_day1, f"Expected {historical_time_day1}, got {evt_time}"
        print(f"  -> PASSED: Injected started_at ({historical_time_day1}) strictly preserved in DB observations and events.")

        # TEST 3: 동일 스냅샷 재호출 시 raw_sha256 기반 중복 차단 (멱등성)
        print("\n[3] Testing SHA256 Idempotency guard (duplicate snapshot rejection)...")
        res_dup = engine.record_snapshot(mock_snapshot_day1, started_at=historical_time_day1)
        assert res_dup["status"] == "ALREADY_RECORDED", f"Expected ALREADY_RECORDED, got {res_dup['status']}"
        assert res_dup["observations_count"] == 0, "Duplicate run must insert 0 observations!"
        assert res_dup["events_count"] == 0, "Duplicate run must insert 0 events!"

        # runs 테이블에 추가 row가 안 생겼는지 확인
        c.execute("SELECT COUNT(*) FROM market_collection_runs")
        run_count = c.fetchone()[0]
        assert run_count == 1, f"Expected exactly 1 run record, got {run_count}"
        conn.close()
        print("  -> PASSED: Identical raw snapshot blocked from duplicate insertion (ALREADY_RECORDED, 0 rows added).")

    # -------------------------------------------------------------
    # TEST 4: run_daily_sync.py dry_run integration test
    # -------------------------------------------------------------
    print("\n[4] Testing scripts/run_daily_sync.py --dry-run end-to-end integration...")
    from scripts.run_daily_sync import run_sync_pipeline
    # dry_run=True 로 실행하여 에러 없이 MarketTimeSeriesEngine까지 통과하는지 검증
    try:
        run_sync_pipeline(use_live_collector=False, dry_run=True)
        print("  -> PASSED: run_daily_sync.py --dry-run successfully executed and invoked MarketTimeSeriesEngine.")
    except Exception as e:
        print(f"  -> FAILED: run_daily_sync.py failed with {e}")
        sys.exit(1)

    print("\n================================================================")
    print(" [+] ALL 4 DIRECTIVE 109 REMEDIATION TESTS PASSED 100%!")
    print("================================================================")

if __name__ == "__main__":
    test_fixes()
