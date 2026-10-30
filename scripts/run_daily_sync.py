"""
Chaficial Live Daily Sync Engine (DIRECTIVE 107 Production Standard)
- Default Mode: LIVE Real-Time Collection (Defaults strictly to --live).
- Strict Integrity Thresholds:
  * Market Threshold: Minimum 1,500 cars required. Under 1,500 aborts DB write immediately (0 writes).
  * Owned Threshold: Minimum 60 cars required.
- Zero Unit Conversion Bug: Prices strictly in Integer MAN-WON.
- Zero False SOLD: Unverified cars marked DELISTED safely without corrupting status to SOLD.
- Masked Tokens: No credentials or session tokens leaked to logs.
"""

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

# 엄격한 수집량 임계치 (기준 미달 시 즉시 DB 쓰기 전면 차단)
MIN_MARKET_THRESHOLD = 1500
MIN_OWNED_THRESHOLD = 60

async def collect_live_snapshot(max_pages: int = 89):
    """카매니저 실시간 시장 매물 수집 실행 (1~89페이지 전체 순회)"""
    collector = JanghanpyeongCollector()
    result = await collector.run_full_collection(max_pages=max_pages, throttle_sec=0.35)
    return result

def run_sync_pipeline(use_live_collector: bool = True, max_pages: int = 89, dry_run: bool = False):
    print("========================================================")
    print(f"[*] Chaficial Live Daily Sync: {datetime.now().isoformat()} (DRY_RUN={dry_run})")
    print("========================================================")

    all_cars = []

    if use_live_collector:
        print(f"[*] [LIVE MODE] Executing live CarManager crawler for up to {max_pages} pages...")
        try:
            collect_res = asyncio.run(collect_live_snapshot(max_pages=max_pages))
            all_cars = collect_res.get("cars", [])
            print(f"[+] Successfully harvested {len(all_cars)} live cars from CarManager.")
        except Exception as e:
            print(f"[!] Live collection failed with exception: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("[!] [DRY-RUN / FALLBACK MODE] Loading snapshot from local disk...")
        latest_snapshot_path = "data/carmanager_raw/janghanpyeong_full_collection.json"
        if not os.path.exists(latest_snapshot_path):
            print(f"[!] Snapshot file {latest_snapshot_path} not found.", file=sys.stderr)
            sys.exit(1)
        with open(latest_snapshot_path, "r", encoding="utf-8") as f:
            full_data = json.load(f)
        all_cars = full_data.get("cars", [])
        print(f"[+] Loaded verified snapshot with {len(all_cars)} cars.")

    # 1. 엄격한 전체 수집량 검증 (최소 1,500대 미만 시 즉시 차단)
    if len(all_cars) < MIN_MARKET_THRESHOLD:
        print(f"[!] CRITICAL GUARD: Harvested vehicle count ({len(all_cars)}) is below strict threshold ({MIN_MARKET_THRESHOLD}).", file=sys.stderr)
        print("[!] Aborting database writes completely (0 writes performed) to protect data integrity.", file=sys.stderr)
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

    # 2. 우리 상사 수집량 임계치 검증
    if len(owned_cars) < MIN_OWNED_THRESHOLD:
        print(f"[!] CRITICAL GUARD: Owned vehicle count ({len(owned_cars)}) is below strict threshold ({MIN_OWNED_THRESHOLD}).", file=sys.stderr)
        print("[!] Aborting database writes completely to protect owned inventory.", file=sys.stderr)
        sys.exit(1)

    # 3. 우리 상사 동기화 (최소 60대 기대)
    owned_res = service.run_sync(current_snapshot=owned_cars, scope="OWNED", min_expected_count=MIN_OWNED_THRESHOLD, dry_run=dry_run)
    print(f"[+] Owned Scope Sync: Inspected={owned_res['total_inspected']}, New={owned_res['new_inserted']}, PriceChanged={owned_res['price_changed']}, Status={owned_res['status']}")
    if "ERROR" in owned_res["status"]:
        print(f"[!] Owned Sync Error: {owned_res['status']}", file=sys.stderr)
        sys.exit(1)

    # 4. 장한평 시장 동기화 (최소 1,500대 기대)
    market_res = service.run_sync(current_snapshot=market_cars, scope="MARKET_OBSERVED", min_expected_count=MIN_MARKET_THRESHOLD, dry_run=dry_run)
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
            "dry_run": dry_run,
            "total_cars": len(all_cars),
            "owned_cars": len(owned_cars),
            "market_cars": len(market_cars),
            "owned_result": owned_res,
            "market_result": market_res
        }, f, ensure_ascii=False, indent=2)

    print(f"[+] Archived snapshot run to {archive_path}")
    print("========================================================")
    print(f"[+] Live Sync Completed Successfully at {datetime.now().isoformat()} (DRY_RUN={dry_run})")
    print("========================================================")

if __name__ == "__main__":
    # 기본값: LIVE 실시간 크롤링 실행 (--dry-run 명시 시에만 읽기 전용 및 로컬 파일 사용)
    is_dry_run = "--dry-run" in sys.argv
    run_sync_pipeline(use_live_collector=(not is_dry_run), dry_run=is_dry_run)
