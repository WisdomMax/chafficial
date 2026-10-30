import sys
import os
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "src")
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
from chaficial.platform.sourcing.janghanpyeong_collector import JanghanpyeongCollector
from chaficial.platform.sourcing.carmanager_client import load_env

load_env()
SNAPSHOT_DIR = Path("data/carmanager_raw/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

async def collect_live_snapshot(max_pages: int = 89):
    """카매니저 실시간 시장 매물 수집 실행"""
    collector = JanghanpyeongCollector()
    result = await collector.run_full_collection(max_pages=max_pages, throttle_sec=0.3)
    return result

def run_sync_pipeline(use_live_collector: bool = False, max_pages: int = 89):
    print("========================================================")
    print(f"[*] Chaficial Live Daily Sync: {datetime.now().isoformat()}")
    print("========================================================")

    all_cars = []

    if use_live_collector:
        print(f"[*] Executing live crawler for up to {max_pages} pages...")
        try:
            collect_res = asyncio.run(collect_live_snapshot(max_pages=max_pages))
            all_cars = collect_res.get("cars", [])
            print(f"[+] Successfully harvested {len(all_cars)} live cars from CarManager.")
        except Exception as e:
            print(f"[!] Live collection failed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # 안전한 스냅샷 백업 파일 로드 (사전 수집본)
        latest_snapshot_path = "data/carmanager_raw/janghanpyeong_full_collection.json"
        if not os.path.exists(latest_snapshot_path):
            print(f"[!] Snapshot file {latest_snapshot_path} not found.", file=sys.stderr)
            sys.exit(1)
        with open(latest_snapshot_path, "r", encoding="utf-8") as f:
            full_data = json.load(f)
        all_cars = full_data.get("cars", [])
        print(f"[+] Loaded verified snapshot with {len(all_cars)} cars.")

    if len(all_cars) < 50:
        print(f"[!] Aborting: collected vehicle count too low ({len(all_cars)} < 50) to protect DB integrity.", file=sys.stderr)
        sys.exit(1)

    service = CarManagerSyncService(db_path="data/chamart/chamart_platform_demo.db")

    # 우리 상사 매물 분리 ((주)더쿨모터스 및 더쿨모터스)
    owned_cars = []
    market_cars = []
    for c in all_cars:
        shop = c.get("shop") or c.get("sangsa_name") or ""
        if "(주)더쿨모터스" in shop or "더쿨모터스" in shop:
            owned_cars.append(c)
        else:
            market_cars.append(c)

    print(f"[*] Partitioned vehicles: OWNED={len(owned_cars)}대 | MARKET_OBSERVED={len(market_cars)}대")

    # 1. 우리 상사 동기화 (최소 50대 기대)
    owned_res = service.run_sync(current_snapshot=owned_cars, scope="OWNED", min_expected_count=50)
    print(f"[+] Owned Scope Sync: Inspected={owned_res['total_inspected']}, New={owned_res['new_inserted']}, PriceChanged={owned_res['price_changed']}, Status={owned_res['status']}")
    if "ERROR" in owned_res["status"]:
        print(f"[!] Owned Sync Error: {owned_res['status']}", file=sys.stderr)
        sys.exit(1)

    # 2. 장한평 시장 동기화 (최소 1,000대 기대)
    market_res = service.run_sync(current_snapshot=market_cars, scope="MARKET_OBSERVED", min_expected_count=1000)
    print(f"[+] Market Scope Sync: Inspected={market_res['total_inspected']}, New={market_res['new_inserted']}, PriceChanged={market_res['price_changed']}, Status={market_res['status']}")
    if "ERROR" in market_res["status"]:
        print(f"[!] Market Sync Error: {market_res['status']}", file=sys.stderr)
        sys.exit(1)

    # 타임스탬프 스냅샷 아카이빙
    today_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = SNAPSHOT_DIR / f"snapshot_{today_str}.json"
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_cars": len(all_cars),
            "owned_cars": len(owned_cars),
            "market_cars": len(market_cars),
            "owned_result": owned_res,
            "market_result": market_res
        }, f, ensure_ascii=False, indent=2)

    print(f"[+] Archived snapshot run to {archive_path}")
    print("========================================================")
    print(f"[+] Live Sync Completed Successfully at {datetime.now().isoformat()}")
    print("========================================================")

if __name__ == "__main__":
    live_flag = "--live" in sys.argv
    run_sync_pipeline(use_live_collector=live_flag)
