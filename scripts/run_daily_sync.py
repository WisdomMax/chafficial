import sys
import os
import json
import time
from pathlib import Path

sys.path.insert(0, "src")
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService

def main():
    print("========================================================")
    print(f"[*] Chaficial Daily Sync Service Run: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("========================================================")

    # 1. 최신 카매니저 장한평 및 내차 스냅샷 로드
    snapshot_path = "data/carmanager_raw/janghanpyeong_full_collection.json"
    if not os.path.exists(snapshot_path):
        print(f"[!] Error: Snapshot not found at {snapshot_path}")
        return

    with open(snapshot_path, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    all_cars = full_data.get("cars", [])
    print(f"[+] Loaded {len(all_cars)} cars from latest CarManager snapshot.")

    # 우리 상사 매물 분리
    owned_cars = [c for c in all_cars if "(주)더쿨모터스" in c.get("sangsa_name", "") or c.get("shop") == "(주)더쿨모터스"]
    market_cars = [c for c in all_cars if c not in owned_cars]

    print(f"[+] Scope Breakdown: Owned={len(owned_cars)} cars, Market={len(market_cars)} cars")

    service = CarManagerSyncService(db_path="data/chamart/chamart_platform_demo.db")

    # 2. 우리 상사 매물 동기화
    owned_res = service.run_sync(current_snapshot=owned_cars, scope="OWNED")
    print(f"[+] Owned Sync Completed:")
    print(f"    - Total: {owned_res['total_inspected']}, New: {owned_res['new_inserted']}, PriceChanged: {owned_res['price_changed']}, Sold: {owned_res['sold_count']}, Status: {owned_res['status']}")

    # 3. 시장 매물 동기화
    market_res = service.run_sync(current_snapshot=market_cars, scope="MARKET_OBSERVED")
    print(f"[+] Market Sync Completed:")
    print(f"    - Total: {market_res['total_inspected']}, New: {market_res['new_inserted']}, PriceChanged: {market_res['price_changed']}, Sold: {market_res['sold_count']}, Status: {market_res['status']}")

    print("========================================================")
    print(f"[+] All Daily Synchronizations Finished Successfully.")
    print("========================================================")

if __name__ == "__main__":
    main()
