import sys
import os
import asyncio
import json
import re
import time
from pathlib import Path

sys.path.insert(0, "src")
from chaficial.platform.sourcing.carmanager_client import load_env

load_env()
uid = os.getenv("CAR_MANAGER_ID") or os.getenv("CARMANAGER_ID")
upw = os.getenv("CAR_MANAGER_PW") or os.getenv("CARMANAGER_PW")

with open("data/carmanager_raw/janghanpyeong_full_collection.json", "r", encoding="utf-8") as f:
    jhp_data = json.load(f)

# 상위 100대
sample_100 = jhp_data["cars"][:100]

async def run():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("[*] Logging in for 100-car detail harvest...")
        await page.goto("https://www.carmanager.co.kr/User/Login", wait_until="networkidle", timeout=30000)
        await page.fill("#userid", uid)
        await page.fill("#userpwd", upw)
        btn = await page.query_selector("button[onclick*='commitLogin']")
        if btn:
            async with page.expect_navigation(wait_until="networkidle", timeout=15000):
                await btn.click()
        await page.wait_for_timeout(2000)

        await page.goto("https://www.carmanager.co.kr/Car/Data", wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        enc_check = await page.evaluate("() => $('#EncCheck').val() || '5becvnNSfoHCiGE5GKa5ZQ=='")
        print(f"[+] Using EncCheck token: {enc_check}")

        detailed_results = []
        api_request = context.request

        total_photos_discovered = 0
        t_global_start = time.time()

        for idx, car in enumerate(sample_100, 1):
            t_start = time.time()
            encarno = car["encarno"]
            if not encarno:
                continue

            resp = await api_request.post(
                "https://www.carmanager.co.kr/PopupFrame/CarDetailEnc/",
                form={"encarno": encarno, "EncCheck": enc_check}
            )
            html = await resp.text()

            # 전체 고화질 사진 URL 추출
            raw_photos = re.findall(r'https://img\.carmanager\.co\.kr/[^\s"\'<>\)]+\.jpg', html)
            clean_hd_photos = []
            seen_hd = set()
            for p_url in raw_photos:
                hd_url = re.sub(r'(/dims/.*|_TH\.jpg)', '.jpg', p_url)
                if hd_url not in seen_hd:
                    seen_hd.add(hd_url)
                    clean_hd_photos.append(hd_url)

            # 전체 차량번호
            plate_full_m = re.search(r'차량번호\s*</th>\s*<td[^>]*>(.*?)</td>', html, re.DOTALL) or re.search(r'(\d{2,3}[가-힣]\s*\d{4})', html)
            plate_full = re.sub(r'<[^>]+>', '', plate_full_m.group(1)).strip().replace(" ", "").replace("번호복사", "") if plate_full_m else ""

            # 제시번호
            suggest_m = re.search(r'제시번호\s*</th>\s*<td[^>]*>(.*?)</td>', html, re.DOTALL) or re.search(r'제시번호\s*:\s*\[?\s*(\d+)', html)
            suggest_no = re.sub(r'<[^>]+>', '', suggest_m.group(1)).strip() if suggest_m else ""

            has_inspection = "성능점검" in html
            duration = time.time() - t_start
            total_photos_discovered += len(clean_hd_photos)

            detailed_results.append({
                "index": idx,
                "encarno": encarno,
                "plate_full": plate_full,
                "suggest_no": suggest_no,
                "model": car["model"],
                "price": car["price_manwon"],
                "year": car["model_year"],
                "km": car["mileage"],
                "shop": car["shop"],
                "dealer": car["dealer"],
                "total_photos_count": len(clean_hd_photos),
                "photo_urls": clean_hd_photos,
                "has_inspection": has_inspection,
                "harvest_duration_sec": round(duration, 2)
            })

            if idx % 10 == 0 or idx == len(sample_100):
                print(f"  [{idx:03d}/100] Plate: {plate_full or '미상'}, Photos: {len(clean_hd_photos)}장, Cumulative Photos: {total_photos_discovered}장")

            await asyncio.sleep(0.1)

        total_elapsed = time.time() - t_global_start
        out_path = Path("data/carmanager_raw/detailed_100_harvest.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_vehicles": len(detailed_results),
                "total_photos_discovered": total_photos_discovered,
                "avg_photos_per_car": round(total_photos_discovered / len(detailed_results), 1),
                "total_elapsed_sec": round(total_elapsed, 2),
                "avg_sec_per_car": round(total_elapsed / len(detailed_results), 3),
                "cars": detailed_results
            }, f, ensure_ascii=False, indent=2)

        print(f"\n[+] 100-CAR HARVEST COMPLETE:")
        print(f"    - Total Vehicles Harvested   : {len(detailed_results)}대")
        print(f"    - Total Photos Discovered    : {total_photos_discovered}장")
        print(f"    - Average Photos Per Car     : {total_photos_discovered / len(detailed_results):.1f}장/대")
        print(f"    - Total Duration             : {total_elapsed:.2f}초 (대당 {total_elapsed/len(detailed_results):.2f}초)")
        print(f"    - Saved Metadata             : {out_path}")
        await browser.close()

asyncio.run(run())
