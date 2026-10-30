import os
import sys
import asyncio
import json
import hashlib
import time
from pathlib import Path
from PIL import Image
import io

OUTPUT_BASE = Path("data/carmanager_raw/photos_by_encarno")
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

async def verify_image_bytes(data: bytes):
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            w, h = img.size
        return True, w, h
    except Exception:
        return False, 0, 0

async def run():
    from playwright.async_api import async_playwright

    harvest_file = "data/carmanager_raw/detailed_500_harvest.json"
    with open(harvest_file, "r", encoding="utf-8") as f:
        harvest_data = json.load(f)

    cars = harvest_data.get("cars", [])
    print(f"[*] Starting High-Res (1024x768) Original Photo Download for {len(cars)} Vehicles...")
    print(f"[*] Architecture: Encarno-based ID matching (Zero Index/Sort Order Risk)")

    t0 = time.time()
    total_downloaded = 0
    total_cached = 0
    total_failed = 0
    total_bytes = 0

    manifest_cars = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        api_request = context.request

        for idx, car in enumerate(cars, 1):
            encarno = car["encarno"]
            safe_encarno = encarno.replace("/", "_").replace("+", "-").replace("=", "")
            car_dir = OUTPUT_BASE / safe_encarno
            car_dir.mkdir(parents=True, exist_ok=True)

            raw_urls = car.get("photos", [])
            # _TH.jpg 제거 -> 고화질 1024x768 원본 URL로 정규화
            highres_urls = []
            for u in raw_urls:
                orig_u = u.replace("_TH.jpg", ".jpg").replace("_th.jpg", ".jpg")
                if orig_u not in highres_urls:
                    highres_urls.append(orig_u)

            car_photos_manifest = []

            for p_idx, url in enumerate(highres_urls, 1):
                save_file = car_dir / f"photo_{p_idx:02d}.jpg"

                # 캐시 검증
                if save_file.exists() and save_file.stat().st_size > 1000:
                    with open(save_file, "rb") as rf:
                        content = rf.read()
                    valid, w, h = await verify_image_bytes(content)
                    if valid and w >= 800: # 1024x768 고화질 확인
                        sha = hashlib.sha256(content).hexdigest()
                        total_cached += 1
                        total_bytes += len(content)
                        car_photos_manifest.append({
                            "order": p_idx,
                            "url": url,
                            "local_path": str(save_file),
                            "sha256": sha,
                            "size_bytes": len(content),
                            "width": w,
                            "height": h,
                            "status": "VERIFIED"
                        })
                        continue

                # 고화질 원본 다운로드
                try:
                    resp = await api_request.get(url, timeout=15000, headers={"Referer": "https://www.carmanager.co.kr/"})
                    if resp.status == 200:
                        body = await resp.body()
                        valid, w, h = await verify_image_bytes(body)
                        if valid and len(body) > 1000:
                            sha = hashlib.sha256(body).hexdigest()
                            with open(save_file, "wb") as wf:
                                wf.write(body)
                            total_downloaded += 1
                            total_bytes += len(body)
                            car_photos_manifest.append({
                                "order": p_idx,
                                "url": url,
                                "local_path": str(save_file),
                                "sha256": sha,
                                "size_bytes": len(body),
                                "width": w,
                                "height": h,
                                "status": "VERIFIED"
                            })
                        else:
                            total_failed += 1
                    else:
                        total_failed += 1
                except Exception:
                    total_failed += 1

                # CPU 통제 스로틀링 (0.015초)
                await asyncio.sleep(0.015)

            manifest_cars.append({
                "car_idx": idx,
                "encarno": encarno,
                "full_plate": car.get("full_plate"),
                "plate_tail": car.get("plate_tail"),
                "maker": car.get("maker"),
                "model": car.get("model"),
                "photos_count": len(car_photos_manifest),
                "verified_count": len([p for p in car_photos_manifest if p["status"] == "VERIFIED"]),
                "photos": car_photos_manifest
            })

            if idx % 25 == 0 or idx == len(cars):
                elapsed = time.time() - t0
                total_v = total_downloaded + total_cached
                print(f"[{idx}/{len(cars)}] Verified High-Res: {total_v} (Cached: {total_cached}, New: {total_downloaded}, Failed: {total_failed}) - {round(total_bytes/(1024*1024), 2)}MB in {round(elapsed, 1)}s")

        t_total = time.time() - t0
        manifest_out = Path("data/carmanager_raw/photos_500_highres_manifest.json")
        with open(manifest_out, "w", encoding="utf-8") as f:
            json.dump({
                "total_cars": len(cars),
                "total_photos": total_downloaded + total_cached + total_failed,
                "verified_photos": total_downloaded + total_cached,
                "failed_photos": total_failed,
                "total_bytes": total_bytes,
                "total_mb": round(total_bytes / (1024 * 1024), 2),
                "elapsed_sec": round(t_total, 2),
                "cars": manifest_cars
            }, f, ensure_ascii=False, indent=2)

        print(f"\n[+] HIGH-RES PHOTO HARVEST COMPLETE:")
        print(f"    - Total Verified Photos: {total_downloaded + total_cached} (Cached: {total_cached}, Downloaded: {total_downloaded})")
        print(f"    - Failed: {total_failed}")
        print(f"    - Total Size: {round(total_bytes/(1024*1024), 2)} MB")
        print(f"    - Manifest: {manifest_out}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
