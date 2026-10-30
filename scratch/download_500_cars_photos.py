import os
import sys
import asyncio
import json
import hashlib
import time
from pathlib import Path
from PIL import Image
import io

OUTPUT_DIR = Path("data/carmanager_raw/photos_500_cars")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OLD_100_DIR = Path("data/carmanager_raw/photos_100_cars")

async def verify_local_file(file_path: Path):
    """로컬 이미지 PIL 디코딩 및 SHA256 검증"""
    try:
        with open(file_path, "rb") as f:
            b = f.read()
        if len(b) < 1000:
            return False, "", len(b), 0, 0
        sha = hashlib.sha256(b).hexdigest()
        with Image.open(io.BytesIO(b)) as img:
            img.verify()
        with Image.open(io.BytesIO(b)) as img:
            w, h = img.size
        return True, sha, len(b), w, h
    except Exception:
        return False, "", 0, 0, 0

async def run():
    from playwright.async_api import async_playwright

    harvest_file = "data/carmanager_raw/detailed_500_harvest.json"
    if not os.path.exists(harvest_file):
        print(f"[!] Harvest file not found: {harvest_file}")
        return

    with open(harvest_file, "r", encoding="utf-8") as f:
        harvest_data = json.load(f)

    cars = harvest_data.get("cars", [])
    print(f"[*] Starting Verified Photo Download for {len(cars)} Vehicles...")
    t_global_start = time.time()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        api_request = context.request

        total_downloaded_photos = 0
        total_cached_photos = 0
        total_downloaded_bytes = 0
        failed_photos = 0

        manifest_cars = []

        for car_idx, car in enumerate(cars, 1):
            encarno = car["encarno"]
            plate_str = car.get("full_plate") or car.get("plate_tail") or encarno[:8]
            safe_plate = plate_str.replace(" ", "_").replace("/", "_")
            car_dir = OUTPUT_DIR / f"car_{car_idx:03d}_{safe_plate}"
            car_dir.mkdir(exist_ok=True)

            photo_urls = car.get("photos", [])
            car_photos_manifest = []

            for p_idx, url in enumerate(photo_urls, 1):
                save_file = car_dir / f"photo_{p_idx:02d}.jpg"

                # 1. 500 디렉터리에 이미 정상 파일이 있는지 검증
                if save_file.exists() and save_file.stat().st_size > 1000:
                    valid, sha, b_size, w, h = await verify_local_file(save_file)
                    if valid:
                        total_cached_photos += 1
                        total_downloaded_bytes += b_size
                        car_photos_manifest.append({
                            "order": p_idx,
                            "url": url,
                            "local_path": str(save_file),
                            "sha256": sha,
                            "size_bytes": b_size,
                            "width": w,
                            "height": h,
                            "status": "VERIFIED"
                        })
                        continue

                # 2. 100 디렉터리에 기존 파일이 있는지 확인하여 복사
                old_car_dirs = list(OLD_100_DIR.glob(f"car_{car_idx:03d}_*"))
                if old_car_dirs:
                    old_file = old_car_dirs[0] / f"photo_{p_idx:02d}.jpg"
                    if old_file.exists() and old_file.stat().st_size > 1000:
                        valid, sha, b_size, w, h = await verify_local_file(old_file)
                        if valid:
                            with open(old_file, "rb") as rf:
                                content = rf.read()
                            with open(save_file, "wb") as wf:
                                wf.write(content)
                            total_cached_photos += 1
                            total_downloaded_bytes += b_size
                            car_photos_manifest.append({
                                "order": p_idx,
                                "url": url,
                                "local_path": str(save_file),
                                "sha256": sha,
                                "size_bytes": b_size,
                                "width": w,
                                "height": h,
                                "status": "VERIFIED"
                            })
                            continue

                # 3. 신규 네트워크 다운로드
                try:
                    resp = await api_request.get(url, timeout=15000)
                    if resp.status == 200:
                        body = await resp.body()
                        if len(body) > 1000:
                            # PIL 디코딩 검증
                            try:
                                with Image.open(io.BytesIO(body)) as img:
                                    img.verify()
                                with Image.open(io.BytesIO(body)) as img:
                                    w, h = img.size
                            except Exception:
                                failed_photos += 1
                                continue

                            sha = hashlib.sha256(body).hexdigest()
                            with open(save_file, "wb") as wf:
                                wf.write(body)

                            # 저장 후 해시 일치 검증
                            with open(save_file, "rb") as rf:
                                disk_sha = hashlib.sha256(rf.read()).hexdigest()
                            if disk_sha != sha:
                                failed_photos += 1
                                continue

                            total_downloaded_photos += 1
                            total_downloaded_bytes += len(body)
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
                            failed_photos += 1
                    else:
                        failed_photos += 1
                except Exception:
                    failed_photos += 1

                # CPU 배려 스로틀링
                await asyncio.sleep(0.02)

            manifest_cars.append({
                "car_idx": car_idx,
                "encarno": encarno,
                "full_plate": car.get("full_plate"),
                "plate_tail": car.get("plate_tail"),
                "maker": car.get("maker"),
                "model": car.get("model"),
                "photos_count": len(car_photos_manifest),
                "verified_count": len([p for p in car_photos_manifest if p["status"] == "VERIFIED"]),
                "photos": car_photos_manifest
            })

            if car_idx % 25 == 0 or car_idx == len(cars):
                elapsed = time.time() - t_global_start
                total_v = total_downloaded_photos + total_cached_photos
                print(f"[{car_idx}/{len(cars)}] Verified: {total_v} (Cached: {total_cached_photos}, New: {total_downloaded_photos}, Failed: {failed_photos}) - {round(total_downloaded_bytes/(1024*1024), 2)}MB in {round(elapsed, 1)}s")

        t_global_total = time.time() - t_global_start
        manifest_path = Path("data/carmanager_raw/photos_500_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({
                "total_cars": len(cars),
                "total_photos": total_downloaded_photos + total_cached_photos + failed_photos,
                "verified_photos": total_downloaded_photos + total_cached_photos,
                "failed_photos": failed_photos,
                "total_bytes": total_downloaded_bytes,
                "total_mb": round(total_downloaded_bytes / (1024 * 1024), 2),
                "elapsed_sec": round(t_global_total, 2),
                "cars": manifest_cars
            }, f, ensure_ascii=False, indent=2)

        print(f"\n[+] 500-CAR PHOTOS DOWNLOAD & DECODING VERIFICATION COMPLETE!")
        print(f"    - Verified Photos: {total_downloaded_photos + total_cached_photos} (Cached: {total_cached_photos}, Downloaded: {total_downloaded_photos})")
        print(f"    - Failed Photos  : {failed_photos}")
        print(f"    - Total Size     : {round(total_downloaded_bytes / (1024 * 1024), 2)} MB")
        print(f"    - Elapsed Time   : {round(t_global_total, 2)} s")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
