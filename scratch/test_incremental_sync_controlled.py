import sqlite3
import shutil
import json
import os
import sys

sys.path.insert(0, "src")
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService

# 1. 독립 테스트 DB 복제 (운영 DB 완벽 보호)
SRC_DB = "data/chamart/chamart_platform_demo.db"
TEST_DB = "data/chamart/chamart_platform_test_sync.db"
shutil.copy2(SRC_DB, TEST_DB)
print(f"[*] Cloned test DB to {TEST_DB}")

service = CarManagerSyncService(db_path=TEST_DB)
conn = sqlite3.connect(TEST_DB)
cursor = conn.cursor()

print("\n=======================================================")
print("[*] DIRECTIVE 105 TASK 5: CONTROLLED SYNC EXPERIMENTS")
print("=======================================================")

# 기존 1대 매물 선정 (실험 대상)
cursor.execute("""
    SELECT l.listing_id, v.id, v.target_price, v.status, v.plate_number
    FROM vehicle_listings l
    JOIN vehicles v ON l.vehicle_id = v.id
    WHERE l.platform = 'CARMANAGER' AND v.listing_ownership_type = 'MARKET_JANGHANPYEONG'
    LIMIT 1
""")
target_row = cursor.fetchone()
test_listing_id, test_vid, orig_price, orig_status, test_plate = target_row
print(f"[+] Target Vehicle: listing_id={test_listing_id}, plate={test_plate}, price={orig_price}, status={orig_status}")

# -------------------------------------------------------------
# 실험 1: 가격 변경 감지 (PRICE_CHANGED)
# -------------------------------------------------------------
print("\n--- EXPERIMENT 1: Price Change Detection ---")
# 초기 유효 가격 설정
cursor.execute("UPDATE vehicles SET target_price = 15000000 WHERE id = ?", (test_vid,))
cursor.execute("UPDATE vehicle_listings SET advertised_price = 15000000 WHERE listing_id = ?", (test_listing_id,))
conn.commit()

new_price_manwon = 1400 # 1,400만원으로 100만원 인하
snapshot_exp1 = [{
    "encarno": test_listing_id,
    "full_plate": test_plate,
    "price_manwon": new_price_manwon,
    "model": "실험 대상 차량",
    "year": 2021,
    "mileage": 50000
}]

res1 = service.run_sync(current_snapshot=snapshot_exp1, scope="MARKET_OBSERVED")
cursor.execute("SELECT target_price, updated_at, timeline_json FROM vehicles WHERE id = ?", (test_vid,))
after_price, updated_at, tl = cursor.fetchone()
cursor.execute("SELECT advertised_price FROM vehicle_listings WHERE listing_id = ?", (test_listing_id,))
after_l_price = cursor.fetchone()[0]

print(f"  Result Stats: price_changed={res1['price_changed']}, unchanged={res1['unchanged_count']}")
print(f"  SQL Before: target_price={orig_price}")
print(f"  SQL After : target_price={after_price}, listing_advertised_price={after_l_price}")
assert after_price == new_price_manwon * 10000
assert res1["price_changed"] == 1
print("  [PASS] Experiment 1 Succeeded!")

# -------------------------------------------------------------
# 실험 2: 관리자 가격 잠금 보호 (ADMIN_PRICE_LOCK)
# -------------------------------------------------------------
print("\n--- EXPERIMENT 2: Admin Price Lock Preservation ---")
# 관리자가 가격 잠금(is_price_locked = True)을 건 상태로 설정
cond_locked = {"is_price_locked": True, "lock_reason": "딜러 협의 완료"}
cursor.execute("UPDATE vehicles SET condition_detail_json = ? WHERE id = ?", (json.dumps(cond_locked), test_vid))
conn.commit()

# 카매니저에서 또 가격을 바꾼 스냅샷 전송
snapshot_exp2 = [{
    "encarno": test_listing_id,
    "full_plate": test_plate,
    "price_manwon": new_price_manwon - 50, # 또 50만원 인하
    "model": "실험 대상 차량",
    "year": 2021,
    "mileage": 50000
}]

res2 = service.run_sync(current_snapshot=snapshot_exp2, scope="MARKET_OBSERVED")
cursor.execute("SELECT target_price, timeline_json FROM vehicles WHERE id = ?", (test_vid,))
locked_price, tl_locked = cursor.fetchone()

print(f"  Result Stats: price_changed={res2['price_changed']}, unchanged={res2['unchanged_count']}")
print(f"  SQL Kept Target Price: {locked_price} (Unchanged despite external sync change)")
assert locked_price == after_price # 기존 가격 유지
assert "SYNC_PRICE_SKIPPED_ADMIN_PRICE_LOCK" in tl_locked
print("  [PASS] Experiment 2 Succeeded (Admin lock successfully protected)!")

# -------------------------------------------------------------
# 실험 3: 신규 차량 감지 (NEW_INSERTED)
# -------------------------------------------------------------
print("\n--- EXPERIMENT 3: New Vehicle Discovery ---")
new_encarno = "TEST_NEW_ENCARNO_9999"
new_plate = "99호9999"
snapshot_exp3 = [
    snapshot_exp2[0],
    {
        "encarno": new_encarno,
        "full_plate": new_plate,
        "price_manwon": 2500,
        "model": "신규 감지 현대 아반떼",
        "maker": "현대",
        "year": 2023,
        "mileage": 12000,
        "shop": "동대문상사",
        "vin": "KMHD1234567890TEST"
    }
]

res3 = service.run_sync(current_snapshot=snapshot_exp3, scope="MARKET_OBSERVED")
cursor.execute("SELECT id, plate_number, target_price, vin, status, listing_ownership_type FROM vehicles WHERE plate_number = ?", (new_plate,))
new_car_row = cursor.fetchone()

print(f"  Result Stats: new_inserted={res3['new_inserted']}")
print(f"  SQL Inserted: {new_car_row}")
assert res3["new_inserted"] == 1
assert new_car_row[1] == new_plate
assert new_car_row[2] == 25000000
assert new_car_row[3] == "KMHD1234567890TEST"
assert new_car_row[5] == "MARKET_JANGHANPYEONG"
print("  [PASS] Experiment 3 Succeeded!")

# -------------------------------------------------------------
# 실험 4: 안전 판매완료/광고중지 감지 (SAFE DELISTING)
# -------------------------------------------------------------
print("\n--- EXPERIMENT 4: Safe Delisting Threshold (3 consecutive unverified) ---")
# 신규 차량이 목록에서 빠진 빈 스냅샷 전송 (1회차 누락)
snapshot_empty = [snapshot_exp2[0]] # 신규 차량 제외
res4_1 = service.run_sync(current_snapshot=snapshot_empty, scope="MARKET_OBSERVED")
cursor.execute("SELECT listing_status, unverified_consecutive_count FROM vehicle_listings WHERE listing_id = ?", (new_encarno,))
status_1, unverified_1 = cursor.fetchone()
print(f"  Miss 1: status={status_1}, count={unverified_1} (Unverified, NOT delisted yet)")
assert unverified_1 == 1
assert status_1 != "DELISTED"

# 2회차 누락
res4_2 = service.run_sync(current_snapshot=snapshot_empty, scope="MARKET_OBSERVED")
cursor.execute("SELECT listing_status, unverified_consecutive_count FROM vehicle_listings WHERE listing_id = ?", (new_encarno,))
status_2, unverified_2 = cursor.fetchone()
print(f"  Miss 2: status={status_2}, count={unverified_2} (Unverified, NOT delisted yet)")
assert unverified_2 == 2
assert status_2 != "DELISTED"

# 3회차 누락 -> 안전 임계치 도달 -> DELISTED 및 SOLD 전환
res4_3 = service.run_sync(current_snapshot=snapshot_empty, scope="MARKET_OBSERVED")
cursor.execute("SELECT listing_status, unverified_consecutive_count FROM vehicle_listings WHERE listing_id = ?", (new_encarno,))
status_3, unverified_3 = cursor.fetchone()
cursor.execute("SELECT status, is_public FROM vehicles WHERE plate_number = ?", (new_plate,))
v_status_3, v_public_3 = cursor.fetchone()

print(f"  Miss 3: listing_status={status_3}, count={unverified_3}, vehicle_status={v_status_3}, is_public={v_public_3}")
assert status_3 == "DELISTED"
assert v_status_3 == "SOLD"
assert v_public_3 == 0
print("  [PASS] Experiment 4 Succeeded (Safe 3-threshold Delisting verified)!")

# -------------------------------------------------------------
# 실험 5: 동일 스냅샷 재실행 멱등성 검증 (IDEMPOTENCY)
# -------------------------------------------------------------
print("\n--- EXPERIMENT 5: Idempotency with Zero Redundant Changes ---")
res5 = service.run_sync(current_snapshot=snapshot_empty, scope="MARKET_OBSERVED")
print(f"  Result Stats: new={res5['new_inserted']}, price_changed={res5['price_changed']}, sold={res5['sold_count']}, unchanged={res5['unchanged_count']}")
assert res5["new_inserted"] == 0
assert res5["price_changed"] == 0
print("  [PASS] Experiment 5 Succeeded (Perfect Idempotency)!")

conn.close()
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
print("\n[+] ALL 5 CONTROLLED EXPERIMENTS PASSED WITH COMPLETE SQL INTEGRITY EVIDENCE!")
