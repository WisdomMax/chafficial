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

# 상위 500대 대상
all_cars = jhp_data["cars"]
target_500 = all_cars[:500]

# 기존 100대 캐시 확인
existing_cache = {}
cached_file = "data/carmanager_raw/detailed_100_harvest.json"
if os.path.exists(cached_file):
    try:
        with open(cached_file, "r", encoding="utf-8") as f:
            cdata = json.load(f)
            for c in cdata.get("cars", []):
                existing_cache[c["encarno"]] = c
        print(f"[+] Loaded {len(existing_cache)} existing cars from 100-harvest cache.")
    except Exception as e:
        print(f"[!] Warning reading cache: {e}")

async def run():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("[*] Logging in to CarManager for 500-car detail harvest...")
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

        for idx, car in enumerate(target_500, 1):
            encarno = car["encarno"]
            if not encarno:
                continue

            # 캐시가 있으면 재사용
            if encarno in existing_cache:
                old_c = existing_cache[encarno]
                # 통일된 구조로 변환
                c_item = {
                    "idx": idx,
                    "encarno": encarno,
                    "title": old_c.get("model", car.get("title", "")),
                    "plate_tail": car.get("plate_tail"),
                    "full_plate": old_c.get("plate_full") or car.get("full_plate"),
                    "vin": old_c.get("vin"),
                    "maker": car.get("maker"),
                    "model": old_c.get("model", car.get("model")),
                    "model_year": old_c.get("year", car.get("model_year")),
                    "mileage": old_c.get("km", car.get("mileage")),
                    "price_manwon": old_c.get("price", car.get("price_manwon")),
                    "fuel": car.get("fuel"),
                    "mission": car.get("mission"),
                    "shop": old_c.get("shop", car.get("shop")),
                    "dealer": old_c.get("dealer", car.get("dealer")),
                    "phone": car.get("phone"),
                    "danji": car.get("danji"),
                    "photos": old_c.get("photo_urls", old_c.get("photos", [])),
                    "photo_count": len(old_c.get("photo_urls", old_c.get("photos", []))),
                    "options": old_c.get("options", []),
                    "fetch_time_sec": old_c.get("harvest_duration_sec", 0.1)
                }
                detailed_results.append(c_item)
                total_photos_discovered += len(c_item["photos"])
                if idx % 50 == 0 or idx == len(target_500):
                    print(f"[{idx}/500] (CACHED) {c_item['title']} - photos: {len(c_item['photos'])}")
                continue

            t_start = time.time()
            resp = await api_request.post(
                "https://www.carmanager.co.kr/PopupFrame/CarDetailEnc/",
                form={"encarno": encarno, "EncCheck": enc_check}
            )
            html = await resp.text()

            # 1. 고화질 사진 URL 추출
            photo_urls = []
            m_photos = re.findall(r'src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png))["\']', html, re.I)
            for u in m_photos:
                if any(x in u for x in ["carpicture", "car_pic", "Photo", "photo", "Upload", "images", "img."]) and "ico" not in u and "banner" not in u and "btn" not in u:
                    if u not in photo_urls:
                        photo_urls.append(u)

            # 2. 추가 정보 추출 (VIN, 정식 차량번호, 상세 옵션)
            vin_match = re.search(r'차대번호\s*</th>\s*<td[^>]*>([^<]+)</td>', html)
            full_plate_match = re.search(r'차량번호\s*</th>\s*<td[^>]*>([^<]+)</td>', html)
            
            raw_vin = vin_match.group(1).strip() if vin_match else None
            raw_full_plate = full_plate_match.group(1).strip() if full_plate_match else None

            # 옵션 태그
            options = []
            m_opts = re.findall(r'<li[^>]*class=["\'][^"\']*active[^"\']*["\'][^>]*>([^<]+)</li>', html)
            if not m_opts:
                m_opts = re.findall(r'class=["\'][^"\']*on[^"\']*["\'][^>]*><span>([^<]+)</span>', html)
            for opt in m_opts:
                cleaned = opt.strip()
                if cleaned and cleaned not in options:
                    options.append(cleaned)

            car_detail = {
                "idx": idx,
                "encarno": encarno,
                "title": car["title"],
                "plate_tail": car["plate_tail"],
                "full_plate": raw_full_plate,
                "vin": raw_vin,
                "maker": car["maker"],
                "model": car["model"],
                "model_year": car["model_year"],
                "mileage": car["mileage"],
                "price_manwon": car["price_manwon"],
                "fuel": car["fuel"],
                "mission": car["mission"],
                "shop": car["shop"],
                "dealer": car["dealer"],
                "phone": car["phone"],
                "danji": car["danji"],
                "photos": photo_urls,
                "photo_count": len(photo_urls),
                "options": options,
                "fetch_time_sec": round(time.time() - t_start, 2)
            }
            detailed_results.append(car_detail)
            total_photos_discovered += len(photo_urls)

            if idx % 20 == 0 or idx == len(target_500):
                print(f"[{idx}/500] {car['title']} ({raw_full_plate or car['plate_tail']}) - photos: {len(photo_urls)} ({round(time.time() - t_start, 2)}s)")

            # CPU 및 네트워크 배려 스로틀링
            await asyncio.sleep(0.05)

        t_global_total = time.time() - t_global_start
        print(f"\n[+] Harvested {len(detailed_results)} cars details in {round(t_global_total, 2)}s")
        print(f"[+] Total photos discovered across {len(detailed_results)} cars: {total_photos_discovered} photos")
        print(f"[+] Average photos per car: {round(total_photos_discovered / len(detailed_results), 1)}")

        output_path = "data/carmanager_raw/detailed_500_harvest.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_vehicles": len(detailed_results),
                "total_photos_discovered": total_photos_discovered,
                "avg_photos_per_car": round(total_photos_discovered / len(detailed_results), 1),
                "total_elapsed_sec": round(t_global_total, 2),
                "cars": detailed_results
            }, f, ensure_ascii=False, indent=2)
        print(f"[+] Saved output to {output_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
