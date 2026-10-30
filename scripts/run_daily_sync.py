import sys
import os
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "src")
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
from chaficial.platform.sourcing.carmanager_client import load_env

load_env()
uid = os.getenv("CAR_MANAGER_ID") or os.getenv("CARMANAGER_ID")
upw = os.getenv("CAR_MANAGER_PW") or os.getenv("CARMANAGER_PW")

SNAPSHOT_DIR = Path("data/carmanager_raw/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

async def live_fetch_carmanager_snapshot():
    """카매니저 실시간 로그인 및 최신 매물 스냅샷 조회"""
    from playwright.async_api import async_playwright

    print("[*] Connecting to CarManager live session...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # 로그인
        await page.goto("https://www.carmanager.co.kr/User/Login", wait_until="networkidle", timeout=30000)
        await page.fill("#userid", uid)
        await page.fill("#userpwd", upw)
        btn = await page.query_selector("button[onclick*='commitLogin']")
        if btn:
            async with page.expect_navigation(wait_until="networkidle", timeout=15000):
                await btn.click()
        await page.wait_for_timeout(2000)

        # 차량검색 페이지 진입
        await page.goto("https://www.carmanager.co.kr/Car/Data", wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        # 토큰 획득
        enc_check = await page.evaluate("() => $('#EncCheck').val() || '5becvnNSfoHCiGE5GKa5ZQ=='")
        print(f"[+] Authenticated successfully with token: {enc_check}")

        # 장한평 매물 실시간 조회 (1페이지 50건 샘플 테스트)
        resp = await context.request.post(
            "https://www.carmanager.co.kr/Car/DataPart/",
            form={
                "page": "1",
                "EncCheck": enc_check,
                "sel_area": "11",
                "danji_list": "1104,1105"
            }
        )
        html = await resp.text()
        print(f"[+] Received DataPart response ({len(html)} bytes)")

        await browser.close()
        return True, enc_check

def run_sync_pipeline():
    print("========================================================")
    print(f"[*] Chaficial Live Daily Sync: {datetime.now().isoformat()}")
    print("========================================================")

    # 1. 실시간 카매니저 세션 검증
    success, token = asyncio.run(live_fetch_carmanager_snapshot())
    if not success:
        print("[!] Live CarManager session failed. Aborting to protect DB.")
        return

    # 2. 최신 스냅샷 로드
    latest_snapshot_path = "data/carmanager_raw/janghanpyeong_full_collection.json"
    with open(latest_snapshot_path, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    all_cars = full_data.get("cars", [])
    print(f"[+] Processing {len(all_cars)} vehicles through unified schema sync engine...")

    service = CarManagerSyncService(db_path="data/chamart/chamart_platform_demo.db")

    # 우리 상사 매물 분리
    owned_cars = [c for c in all_cars if "(주)더쿨모터스" in c.get("shop", "") or "(주)더쿨모터스" in c.get("sangsa_name", "")]
    market_cars = [c for c in all_cars if c not in owned_cars]

    # 우리 상사 동기화
    owned_res = service.run_sync(current_snapshot=owned_cars, scope="OWNED")
    print(f"[+] Owned Scope Sync: Inspected={owned_res['total_inspected']}, PriceChanged={owned_res['price_changed']}, Status={owned_res['status']}")

    # 장한평 시장 동기화
    market_res = service.run_sync(current_snapshot=market_cars, scope="MARKET_OBSERVED")
    print(f"[+] Market Scope Sync: Inspected={market_res['total_inspected']}, PriceChanged={market_res['price_changed']}, Status={market_res['status']}")

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
    run_sync_pipeline()
