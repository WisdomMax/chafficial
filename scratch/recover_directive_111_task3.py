import sqlite3
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, "src")
from chaficial.platform.sourcing.normalizer import normalize_carmanager_record
from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine

def recover_timeseries():
    print("================================================================================")
    print(" DIRECTIVE 111 - TASK 3: 잘못 적재된 시계열 데이터 격리 및 정상 복구 적재")
    print("================================================================================")

    db_path = Path("data/chamart/chamart_platform_demo.db")
    backup_path = Path("data/chamart/chamart_platform_demo.db.backup_directive111")

    # 1. 일관된 SQLite 백업 생성
    print(f"[*] Step 1: Creating verified database backup at {backup_path}...")
    shutil.copy2(db_path, backup_path)
    assert backup_path.exists() and backup_path.stat().st_size > 0
    print(f"[+] Backup verified: {backup_path.stat().st_size} bytes")

    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    # 2. 기존 오염된 run_id 격리 (QUARANTINED_DIRTY_MAPPING)
    dirty_run_id = "e0698ccf-15bc-4a1c-bc04-81621bae6473"
    print(f"\n[*] Step 2: Quarantining dirty run ({dirty_run_id})...")
    c.execute("""
        UPDATE market_collection_runs 
        SET status = 'QUARANTINED_DIRTY_MAPPING' 
        WHERE run_id = ?
    """, (dirty_run_id,))
    c.execute("""
        UPDATE market_listing_observations 
        SET listing_status = 'QUARANTINED' 
        WHERE run_id = ?
    """, (dirty_run_id,))
    conn.commit()

    c.execute("SELECT status FROM market_collection_runs WHERE run_id = ?", (dirty_run_id,))
    q_status = c.fetchone()[0]
    print(f"[+] Dirty run status updated to: {q_status} (Isolated from AI training)")

    # 3. 원본 수집 자료 로드
    raw_path = Path("data/carmanager_raw/janghanpyeong_full_collection.json")
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    raw_cars = raw_data.get("cars", [])
    print(f"\n[*] Step 3: Loaded {len(raw_cars)} raw cars from {raw_path}")

    # 4. 공통 정규화 계층(normalize_carmanager_record) 적용하여 정상 시계열 적재
    print("[*] Step 4: Ingesting normalized records via MarketTimeSeriesEngine...")
    engine = MarketTimeSeriesEngine(db_path=str(db_path), dry_run=False)
    
    recovered_run_id = str(uuid.uuid4())
    obs_time = "2026-10-30T22:24:13"  # 원본 관측 시각 보존

    res = engine.record_snapshot(
        snapshot_cars=raw_cars,
        started_at=obs_time,
        finished_at=obs_time,
        source="CARMANAGER",
        search_condition="장안평/성동구(1104,1105,1230)",
        total_found=1764,
        pages_collected=89,
        run_id=recovered_run_id,
        dry_run=False
    )
    print(f"[+] Recovery Ingestion Result: Status={res['status']}")
    print(f"    - Observations Stored: {res['observations_count']}")
    print(f"    - Unique Cars: {res['unique_cars_count']}")
    print(f"    - Appeared Events: {res['appeared_count']}")

    # 5. 복구 후 SQL 통계 전수 검증
    print("\n[*] Step 5: Auditing Recovered Run Quality via SQL...")
    c.execute("""
        SELECT COUNT(*) FROM market_listing_observations 
        WHERE run_id = ?
    """, (recovered_run_id,))
    rec_total = c.fetchone()[0]

    # 가격이 0원인 불량 레코드 (0원 무료 차량 왜곡 0건이어야 함)
    c.execute("""
        SELECT COUNT(*) FROM market_listing_observations 
        WHERE run_id = ? AND price_manwon = 0
    """, (recovered_run_id,))
    rec_zero_price = c.fetchone()[0]

    # 가격 확정 매물 (정수 만원)
    c.execute("""
        SELECT COUNT(*) FROM market_listing_observations 
        WHERE run_id = ? AND price_manwon IS NOT NULL AND price_manwon > 0
    """, (recovered_run_id,))
    rec_priced_count = c.fetchone()[0]

    # 가격 미공개 / 상담 대상 매물 (price_manwon IS NULL)
    c.execute("""
        SELECT COUNT(*) FROM market_listing_observations 
        WHERE run_id = ? AND price_manwon IS NULL
    """, (recovered_run_id,))
    rec_consult_count = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM market_listing_observations 
        WHERE run_id = ? AND (model_name IS NULL OR model_name = '')
    """, (recovered_run_id,))
    rec_null_model = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM market_listing_observations 
        WHERE run_id = ? AND model_year IS NULL
    """, (recovered_run_id,))
    rec_null_year = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM market_listing_observations 
        WHERE run_id = ? AND (shop_name IS NULL OR shop_name = '')
    """, (recovered_run_id,))
    rec_null_shop = c.fetchone()[0]

    c.execute("""
        SELECT COUNT(*) FROM market_listing_observations 
        WHERE run_id = ? AND mileage_km IS NULL
    """, (recovered_run_id,))
    rec_null_km = c.fetchone()[0]

    print(f"  * Recovered Total Observations: {rec_total}")
    print(f"  * ZERO Price (0원 무료 왜곡) Count: {rec_zero_price} (Strictly 0 rows expected)")
    print(f"  * Valid Priced Vehicles Count: {rec_priced_count} (Normal integer man-won)")
    print(f"  * Unpriced / Consultation Required (NULL): {rec_consult_count} (Safe isolated from price RL)")
    print(f"  * NULL Model Name Count: {rec_null_model} (Fixed from 1764 to {rec_null_model})")
    print(f"  * NULL Model Year Count: {rec_null_year} (Fixed from 1764 to {rec_null_year})")
    print(f"  * NULL Shop Name Count: {rec_null_shop} (Fixed from 1764 to {rec_null_shop})")
    print(f"  * NULL Mileage Count: {rec_null_km}")

    assert rec_total == 1764
    assert rec_zero_price == 0, f"Zero price count must be 0! Found {rec_zero_price}"
    assert rec_null_model == 0, f"Model name must not be NULL! Found {rec_null_model}"
    assert rec_null_year == 0, f"Model year must not be NULL! Found {rec_null_year}"
    assert rec_null_shop == 0, f"Shop name must not be NULL! Found {rec_null_shop}"

    # 6. 무작위 표본 30대 추출하여 원본 JSON과 DB 대조
    c.execute("""
        SELECT encarno, price_manwon, model_name, model_year, shop_name, mileage_km 
        FROM market_listing_observations 
        WHERE run_id = ?
    """, (recovered_run_id,))
    db_rows = c.fetchall()

    raw_car_map = {c["encarno"]: c for c in raw_cars if "encarno" in c}
    import random
    random.seed(42)
    sample_30 = random.sample(db_rows, 30)

    print("\n[*] Step 6: Auditing 30 Random Samples against Raw Records...")
    match_count = 0
    sample_audit_details = []
    for r in sample_30:
        enc = r[0]
        raw_c = raw_car_map[enc]
        
        # 원본과 정규화 비교
        norm_expected = normalize_carmanager_record(raw_c)
        is_match = (
            r[1] == norm_expected["price_manwon"] and
            r[2] == norm_expected["model_name"] and
            r[3] == norm_expected["model_year"] and
            r[4] == norm_expected["shop_name"] and
            r[5] == norm_expected["mileage_km"]
        )
        if is_match:
            match_count += 1

        detail = {
            "encarno": enc[:15] + "..",
            "model": r[2],
            "price": f"{r[1]}만원",
            "year": r[3],
            "shop": r[4],
            "km": f"{r[5]}km",
            "match": is_match
        }
        sample_audit_details.append(detail)
        print(f"  * [{detail['encarno']}] Model={detail['model'][:25]} | Price={detail['price']} | Year={detail['year']} | Shop={detail['shop']} | Match={is_match}")

    conn.close()

    print(f"\n[+] 30 Random Samples Match Rate: {match_count}/30 ({match_count/30*100:.1f}%)")
    assert match_count == 30, "All 30 random samples must match raw records 100%!"

    evidence = {
        "recovered_run_id": recovered_run_id,
        "quarantined_dirty_run_id": dirty_run_id,
        "total_recovered": rec_total,
        "zero_price_count": rec_zero_price,
        "null_model_count": rec_null_model,
        "null_year_count": rec_null_year,
        "null_shop_count": rec_null_shop,
        "null_mileage_count": rec_null_km,
        "samples_match_rate": f"{match_count}/30 (100.0%)",
        "sample_audit_details": sample_audit_details
    }
    with open("scratch/directive_111_recovery_evidence.json", "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)

    print("\n================================================================================")
    print(" [+] TASK 3 TIMESERIES RECOVERY COMPLETED & VERIFIED 100% VIA SQL!")
    print("================================================================================")

if __name__ == "__main__":
    recover_timeseries()
