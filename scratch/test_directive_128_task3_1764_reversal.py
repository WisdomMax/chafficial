import os
import sys
import uuid
import json
import sqlite3
import shutil
from datetime import datetime

sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
from src.chaficial.platform.sourcing.normalizer import normalize_carmanager_record

TEST_DB = "data/chamart/sandbox_directive_128_task3.db"
PROD_DB = "data/chamart/chamart_platform_demo.db"
SNAPSHOT_PATH = "data/carmanager_raw/janghanpyeong_full_collection.json"

def setup_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    # 실제 운영 DB 스키마 복제 (구조만)
    conn_src = sqlite3.connect(PROD_DB)
    conn_dst = sqlite3.connect(TEST_DB)
    for line in conn_src.iterdump():
        if "sqlite_sequence" in line or line.startswith("INSERT INTO"):
            continue
        try:
            conn_dst.execute(line)
        except Exception:
            pass
    conn_dst.commit()
    conn_src.close()
    conn_dst.close()

def run_tests():
    print("=" * 70)
    print("[DIRECTIVE 128 TASK 3] 1,764대 실데이터 역행 방지 전수 1:1 대조 실측 검증")
    print("=" * 70)

    setup_test_db()

    with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
        full_data = json.load(f)
    raw_cars = full_data.get("cars", [])
    total_cars = len(raw_cars)
    print(f"[*] Loaded original historical snapshot: {total_cars} cars.")

    # 1. 초기 1,764대를 LIVE_OBSERVED 모드로 테스트 DB에 적재 (기준 베이스라인 구축)
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    base_time = "2026-10-25T10:00:00"

    print("[*] Seeding 1,764 baseline listings into isolated test DB...")
    for idx, raw in enumerate(raw_cars):
        norm = normalize_carmanager_record(raw)
        encarno = norm["encarno"]
        p_val = norm["price_manwon"]
        v_id = str(uuid.uuid4())
        c.execute("""
            INSERT INTO vehicles (
                id, branch_id, plate_number, model_name, year, mileage,
                fuel_type, transmission, color, purchase_price, target_price, status,
                is_demo, timeline_json, created_at, updated_at, publishing_status, is_public,
                listing_ownership_type
            ) VALUES (?, 'B01', ?, ?, ?, ?, ?, ?, ?, 0, ?, 'DRAFT', 0, '[]', ?, ?, 'PUBLISHED', 1, 'MARKET_JANGHANPYEONG')
        """, (
            v_id, f"서울{idx}가{1000+idx}", norm["model_name"], norm["model_year"],
            norm["mileage_km"] or 50000, norm.get("fuel") or "UNKNOWN", norm.get("mission") or "오토",
            norm.get("color") or "은색", p_val, base_time, base_time
        ))
        c.execute("""
            INSERT INTO vehicle_listings (
                id, vehicle_id, platform, listing_id, advertised_price,
                listing_status, first_observed_at, last_observed_at,
                is_demo, source_confidence, unverified_consecutive_count
            ) VALUES (?, ?, 'CARMANAGER', ?, ?, 'ACTIVE', ?, ?, 0, 0.95, 0)
        """, (
            str(uuid.uuid4()), v_id, encarno, p_val, base_time, base_time
        ))
    conn.commit()
    print(f"[+] Successfully seeded {total_cars} baseline records.")

    # 2. 6대 변경 그룹 구성 (각 100대씩, 총 600대 변형 적용)
    # 그룹 A (0~99): 가격 인상 (+200만원)
    # 그룹 B (100~199): 가격 인하 (-150만원)
    # 그룹 C (200~299): 판매 완료 (status = 'SOLD', listing_status = 'SOLD')
    # 그룹 D (300~399): 비공개 전환 (is_public = 0, publishing_status = 'DRAFT')
    # 그룹 E (400~499): 관측 시각 갱신 ('2026-10-31T02:00:00')
    # 그룹 F (500~599): 상담 가격 전환 (target_price = NULL, advertised_price = NULL)
    mutated_at = "2026-10-30T15:00:00"
    fresh_obs_time = "2026-10-31T02:00:00"

    print("\n[*] Applying operational modifications across 6 mutation groups (600 cars total)...")

    # Group A: 가격 인상
    c.execute("""
        UPDATE vehicles SET target_price = target_price + 200, updated_at = ?
        WHERE id IN (SELECT vehicle_id FROM vehicle_listings WHERE listing_id IN (
            SELECT listing_id FROM vehicle_listings LIMIT 100 OFFSET 0
        ))
    """, (mutated_at,))
    c.execute("""
        UPDATE vehicle_listings SET advertised_price = advertised_price + 200, last_observed_at = ?
        WHERE listing_id IN (SELECT listing_id FROM vehicle_listings LIMIT 100 OFFSET 0)
    """, (mutated_at,))

    # Group B: 가격 인하
    c.execute("""
        UPDATE vehicles SET target_price = MAX(100, target_price - 150), updated_at = ?
        WHERE id IN (SELECT vehicle_id FROM vehicle_listings WHERE listing_id IN (
            SELECT listing_id FROM vehicle_listings LIMIT 100 OFFSET 100
        ))
    """, (mutated_at,))
    c.execute("""
        UPDATE vehicle_listings SET advertised_price = MAX(100, advertised_price - 150), last_observed_at = ?
        WHERE listing_id IN (SELECT listing_id FROM vehicle_listings LIMIT 100 OFFSET 100)
    """, (mutated_at,))

    # Group C: 판매 완료
    c.execute("""
        UPDATE vehicles SET status = 'SOLD', updated_at = ?
        WHERE id IN (SELECT vehicle_id FROM vehicle_listings WHERE listing_id IN (
            SELECT listing_id FROM vehicle_listings LIMIT 100 OFFSET 200
        ))
    """, (mutated_at,))
    c.execute("""
        UPDATE vehicle_listings SET listing_status = 'SOLD', last_observed_at = ?
        WHERE listing_id IN (SELECT listing_id FROM vehicle_listings LIMIT 100 OFFSET 200)
    """, (mutated_at,))

    # Group D: 비공개 전환
    c.execute("""
        UPDATE vehicles SET is_public = 0, publishing_status = 'DRAFT', updated_at = ?
        WHERE id IN (SELECT vehicle_id FROM vehicle_listings WHERE listing_id IN (
            SELECT listing_id FROM vehicle_listings LIMIT 100 OFFSET 300
        ))
    """, (mutated_at,))

    # Group E: 관측 시각 갱신
    c.execute("""
        UPDATE vehicle_listings SET last_observed_at = ?
        WHERE listing_id IN (SELECT listing_id FROM vehicle_listings LIMIT 100 OFFSET 400)
    """, (fresh_obs_time,))

    # Group F: 상담 가격 전환 (NULL)
    c.execute("""
        UPDATE vehicles SET target_price = NULL, updated_at = ?
        WHERE id IN (SELECT vehicle_id FROM vehicle_listings WHERE listing_id IN (
            SELECT listing_id FROM vehicle_listings LIMIT 100 OFFSET 500
        ))
    """, (mutated_at,))
    c.execute("""
        UPDATE vehicle_listings SET advertised_price = NULL, last_observed_at = ?
        WHERE listing_id IN (SELECT listing_id FROM vehicle_listings LIMIT 100 OFFSET 500)
    """, (mutated_at,))

    conn.commit()
    print("[+] All 6 operational mutation groups successfully applied.")

    # 3. 변형 적용 후의 상태를 스냅샷으로 캡처 (기준점)
    c.execute("""
        SELECT vl.listing_id, v.target_price, vl.advertised_price, v.status, vl.listing_status,
               vl.last_observed_at, v.is_public, v.publishing_status
        FROM vehicle_listings vl
        JOIN vehicles v ON vl.vehicle_id = v.id
    """)
    baseline_states = {}
    for r in c.fetchall():
        baseline_states[r[0]] = {
            "target_price": r[1],
            "advertised_price": r[2],
            "v_status": r[3],
            "l_status": r[4],
            "last_observed_at": r[5],
            "is_public": r[6],
            "pub_status": r[7]
        }
    conn.close()

    # 4. 과거 원본(오래된 1,764대 원본 스냅샷)을 HISTORICAL_REPLAY 모드로 재투입!
    print("\n[*] Replaying original historical snapshot (1,764 cars) in HISTORICAL_REPLAY mode...")
    service = CarManagerSyncService(db_path=TEST_DB, dry_run=False)
    sync_res = service.run_sync(
        current_snapshot=raw_cars,
        scope="MARKET_OBSERVED",
        observation_mode="HISTORICAL_REPLAY",
        observed_at="2026-10-25T10:00:00"
    )
    print(f"[+] Sync finished: Inspected={sync_res['total_inspected']}, PriceChanged={sync_res['price_changed']}, Status={sync_res['status']}")

    # 5. 전수 1:1 대조 실측 검증
    print("\n[*] Performing 1:1 exhaustive verification across all 1,764 vehicles...")
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("""
        SELECT vl.listing_id, v.target_price, vl.advertised_price, v.status, vl.listing_status,
               vl.last_observed_at, v.is_public, v.publishing_status
        FROM vehicle_listings vl
        JOIN vehicles v ON vl.vehicle_id = v.id
    """)
    post_replay_rows = c.fetchall()
    conn.close()

    mismatches = {
        "price_mismatches": 0,
        "status_mismatches": 0,
        "last_observed_mismatches": 0,
        "public_mismatches": 0
    }

    for r in post_replay_rows:
        lid = r[0]
        base = baseline_states[lid]
        
        # 1) 가격 검증 (target_price, advertised_price)
        if r[1] != base["target_price"] or r[2] != base["advertised_price"]:
            mismatches["price_mismatches"] += 1
            print(f"[PRICE ERROR] {lid}: Expected target={base['target_price']}, adv={base['advertised_price']} | Got target={r[1]}, adv={r[2]}")

        # 2) 상태 검증 (vehicles.status, vehicle_listings.listing_status)
        if r[3] != base["v_status"] or r[4] != base["l_status"]:
            mismatches["status_mismatches"] += 1
            print(f"[STATUS ERROR] {lid}: Expected v_stat={base['v_status']}, l_stat={base['l_status']} | Got v_stat={r[3]}, l_stat={r[4]}")

        # 3) 관측 시각 검증 (last_observed_at)
        if r[5] != base["last_observed_at"]:
            mismatches["last_observed_mismatches"] += 1
            print(f"[OBS_TIME ERROR] {lid}: Expected obs_time={base['last_observed_at']} | Got obs_time={r[5]}")

        # 4) 공개 여부 검증 (is_public, publishing_status)
        if r[6] != base["is_public"] or r[7] != base["pub_status"]:
            mismatches["public_mismatches"] += 1
            print(f"[PUBLIC ERROR] {lid}: Expected is_public={base['is_public']}, pub_status={base['pub_status']} | Got is_public={r[6]}, pub_status={r[7]}")

    print("\n" + "=" * 70)
    print(">>> 1,764대 실데이터 역행 방지 전수 대조 실측 결과 <<<")
    print(f"1. 가격 불일치(역행) 건수:          {mismatches['price_mismatches']}건 / 1,764건")
    print(f"2. 판매/리스팅 상태 불일치 건수:      {mismatches['status_mismatches']}건 / 1,764건")
    print(f"3. 관측 시각(last_observed_at) 불일치: {mismatches['last_observed_mismatches']}건 / 1,764건")
    print(f"4. 공개 여부(is_public/status) 불일치: {mismatches['public_mismatches']}건 / 1,764건")
    print("=" * 70)

    assert mismatches["price_mismatches"] == 0, f"Price reversals detected: {mismatches['price_mismatches']}"
    assert mismatches["status_mismatches"] == 0, f"Status reversals detected: {mismatches['status_mismatches']}"
    assert mismatches["last_observed_mismatches"] == 0, f"Observation time mutations detected: {mismatches['last_observed_mismatches']}"
    assert mismatches["public_mismatches"] == 0, f"Public flag mutations detected: {mismatches['public_mismatches']}"

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    print("\n>>> [DIRECTIVE 128 TASK 3] 1,764대 전수 불변성(0 mismatches) 실측 검증 완결! <<<")

if __name__ == "__main__":
    run_tests()
