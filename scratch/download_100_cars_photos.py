import os
import sys
import asyncio
import json
import hashlib
import time
from pathlib import Path

with open("data/carmanager_raw/detailed_100_harvest.json", "r", encoding="utf-8") as f:
    harvest_data = json.load(f)

cars = harvest_data["cars"]
photo_base = Path("data/carmanager_raw/photos_100_cars")
photo_base.mkdir(parents=True, exist_ok=True)

async def run():
    from playwright.async_api import async_playwright

    print(f"[*] Starting Full Download of 1,588 Photos across 100 Real Vehicles...")
    t_global_start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        api_request = context.request

        total_downloaded_photos = 0
        total_downloaded_bytes = 0
        failed_photos = 0

        for car_idx, car in enumerate(cars, 1):
            t_car_start = time.time()
            plate_str = car.get("plate_full") or f"tail_{car.get('encarno', '')[:8]}"
            safe_plate = plate_str.replace(" ", "_").replace("/", "_")
            car_dir = photo_base / f"car_{car_idx:03d}_{safe_plate}"
            car_dir.mkdir(exist_ok=True)

            photo_urls = car.get("photo_urls", [])
            downloaded_for_this_car = 0

            for p_idx, url in enumerate(photo_urls, 1):
                save_file = car_dir / f"photo_{p_idx:02d}.jpg"
                
                # 이미 다운로드되어 있고 크기가 정상인 경우 스킵 (멱등성)
                if save_file.exists() and save_file.stat().st_size > 1000:
                    total_downloaded_photos += 1
                    total_downloaded_bytes += save_file.stat().st_size
                    downloaded_for_this_car += 1
                    continue

                try:
                    resp = await api_request.get(url, timeout=10000)
                    if resp.status == 200:
                        body = await resp.body()
                        with open(save_file, "wb") as f_out:
                            f_out.write(body)
                        total_downloaded_photos += 1
                        total_downloaded_bytes += len(body)
                        downloaded_for_this_car += 1
                    else:
                        failed_photos += 1
                except Exception:
                    failed_photos += 1

                # CPU 및 네트워크 완급 조절 (스로틀링: CPU < 50% 유지)
                await asyncio.sleep(0.04)

            car_dur = time.time() - t_car_start
            if car_idx % 10 == 0 or car_idx == len(cars):
                print(f"  [{car_idx:03d}/100] Car: {car['model'][:20]} | Photos: {downloaded_for_this_car}/{len(photo_urls)} | Total Done: {total_downloaded_photos}장 ({total_downloaded_bytes/(1024*1024):.1f}MB)")

        total_time = time.time() - t_global_start
        print(f"\n=======================================================")
        print(f"[+] 100-CAR PHOTO DOWNLOAD OPERATION COMPLETED")
        print(f"=======================================================")
        print(f"  * Total Vehicles Processed   : {len(cars)}대")
        print(f"  * Total Downloaded Photos    : {total_downloaded_photos}장")
        print(f"  * Failed Photos Count        : {failed_photos}장")
        print(f"  * Total Volume Downloaded    : {total_downloaded_bytes / (1024*1024):.2f} MB")
        print(f"  * Average Size Per Photo     : {total_downloaded_bytes / max(1, total_downloaded_photos) / 1024:.1f} KB")
        print(f"  * Total Elapsed Time         : {total_time:.2f}초")
        print(f"  * Storage Destination        : {photo_base}")
        print(f"=======================================================")

        await browser.close()

asyncio.run(run())
