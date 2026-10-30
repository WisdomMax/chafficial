import json
import sqlite3
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, "src")
from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine

def run_real_market_observation():
    print("================================================================================")
    print(" TASK 7: 카매니저 최신 실매물 시장 시계열 최초 관측 적재 및 재실행 멱등성 검증")
    print("================================================================================")

    # 1. 원본 수집 데이터 로드
    raw_path = Path("data/carmanager_raw/janghanpyeong_full_collection.json")
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cars = data.get("cars", [])
    summary = data.get("summary", {})
    total_found = 1764
    pages_collected = summary.get("total_pages_queried", 89)

    print(f"[*] Raw Data Loaded: {len(cars)} cars | Pages: {pages_collected} | Total Found: {total_found}")

    db_path = "data/chamart/chamart_platform_demo.db"
    engine = MarketTimeSeriesEngine(db_path=db_path, dry_run=False)

    # 2. 최초 관측 실행
    started_at = datetime.now().isoformat()
    first_run_id = str(uuid.uuid4())
    print(f"[*] Executing Run 1 (Initial Market Observation) -> Run ID: {first_run_id}")
    
    res1 = engine.record_snapshot(
        snapshot_cars=cars,
        started_at=started_at,
        source="CARMANAGER",
        search_condition="장안평/성동구(1104,1105,1230)",
        total_found=total_found,
        pages_collected=pages_collected,
        run_id=first_run_id,
        dry_run=False
    )
    finished_at = datetime.now().isoformat()

    print(f"[+] Run 1 Result: Status={res1['status']}")
    print(f"    - Observations Stored: {res1['observations_count']}")
    print(f"    - Events Count: {res1['events_count']} (Appeared={res1['appeared_count']}, PriceDec={res1['price_decreased_count']}, Delisted={res1['disappeared_count']})")
    print(f"    - Unique Cars: {res1['unique_cars_count']}")
    print(f"    - Raw SHA256: {res1['raw_sha256']}")

    # 3. 두 번째 동일 run_id 재처리 실행 (멱등성 검증)
    print(f"\n[*] Executing Run 2 (Same Run ID Re-execution) -> Run ID: {first_run_id}")
    res2 = engine.record_snapshot(
        snapshot_cars=cars,
        started_at=started_at,
        source="CARMANAGER",
        search_condition="장안평/성동구(1104,1105,1230)",
        total_found=total_found,
        pages_collected=pages_collected,
        run_id=first_run_id,
        dry_run=False
    )
    print(f"[+] Run 2 Result: Status={res2['status']}")
    print(f"    - Observations Stored: {res2['observations_count']} (Expected: 0)")
    print(f"    - Events Count: {res2['events_count']} (Expected: 0)")

    # 4. 실제 SQLite DB SQL 조회 검증
    print("\n[*] Querying Production Database for SQL Evidence:")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("SELECT run_id, started_at, total_found, pages_collected, unique_cars_count, raw_sha256, status FROM market_collection_runs WHERE run_id = ?", (first_run_id,))
    run_row = c.fetchone()
    print(f"  [market_collection_runs]: {run_row}")

    c.execute("SELECT COUNT(*) FROM market_listing_observations WHERE run_id = ?", (first_run_id,))
    obs_cnt = c.fetchone()[0]
    print(f"  [market_listing_observations count for run]: {obs_cnt}")

    c.execute("SELECT COUNT(*) FROM market_listing_events WHERE run_id = ?", (first_run_id,))
    evt_cnt = c.fetchone()[0]
    print(f"  [market_listing_events count for run]: {evt_cnt}")

    # 샘플 관측 3건 조회 (photo_count, raw_hash 확인)
    c.execute("""
        SELECT encarno, model_name, price_manwon, mileage_km, photo_count, substr(raw_hash, 1, 12) 
        FROM market_listing_observations 
        WHERE run_id = ? 
        LIMIT 3
    """, (first_run_id,))
    sample_obs = c.fetchall()
    print("  [Sample Observations]:")
    for s in sample_obs:
        print(f"    * ID={s[0][:15]}.. | Model={s[1]} | Price={s[2]}만원 | KM={s[3]}km | Photos={s[4]} | RawHash={s[5]}..")

    conn.close()

    # JSON 증거 파일 저장
    evidence = {
        "execution_time": started_at,
        "run_id": first_run_id,
        "total_found": total_found,
        "pages_collected": pages_collected,
        "unique_cars_count": res1['unique_cars_count'],
        "observations_stored": res1['observations_count'],
        "appeared_count": res1['appeared_count'],
        "price_decreased_count": res1['price_decreased_count'],
        "disappeared_count": res1['disappeared_count'],
        "raw_sha256": res1['raw_sha256'],
        "run2_status": res2['status'],
        "run2_observations_added": res2['observations_count'],
        "sample_observations": [
            {"id": s[0], "model": s[1], "price": s[2], "km": s[3], "photo_count": s[4], "raw_hash_prefix": s[5]}
            for s in sample_obs
        ]
    }
    with open("scratch/task7_market_observation_evidence.json", "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)

    print("\n[+] TASK 7 Observation & Idempotency Evidence written to scratch/task7_market_observation_evidence.json")

if __name__ == "__main__":
    run_real_market_observation()
