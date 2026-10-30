import sys
import os
import asyncio
import json
import re
import time
import hashlib
from pathlib import Path
import urllib.request

sys.path.insert(0, "src")
from chaficial.platform.sourcing.carmanager_client import load_env

load_env()
uid = os.getenv("CAR_MANAGER_ID") or os.getenv("CARMANAGER_ID")
upw = os.getenv("CAR_MANAGER_PW") or os.getenv("CARMANAGER_PW")

with open("data/carmanager_raw/janghanpyeong_full_collection.json", "r", encoding="utf-8") as f:
    jhp_data = json.load(f)

# 10대 샘플
sample_10 = jhp_data["cars"][:10]
photo_dir = Path("data/carmanager_raw/photos_10_cars")
photo_dir.mkdir(parents=True, exist_ok=True)

async def run():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        print("[*] Logging in for 10-car full photo harvest...")
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

        total_downloaded_bytes = 0
        total_downloaded_count = 0

        for idx, car in enumerate(sample_10, 1):
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
            plate_full = re.sub(r'<[^>]+>', '', plate_full_m.group(1)).strip().replace(" ", "").replace("번호복사", "") if plate_full_m else f"끝4자리 {car['plate_tail']}"

            # 제시번호
            suggest_m = re.search(r'제시번호\s*</th>\s*<td[^>]*>(.*?)</td>', html, re.DOTALL) or re.search(r'제시번호\s*:\s*\[?\s*(\d+)', html)
            suggest_no = re.sub(r'<[^>]+>', '', suggest_m.group(1)).strip() if suggest_m else ""

            # 차량별 사진 저장 디렉토리
            car_sub_dir = photo_dir / f"car_{idx:02d}_{plate_full}"
            car_sub_dir.mkdir(exist_ok=True)

            downloaded_files = []
            for p_idx, p_url in enumerate(clean_hd_photos, 1):
                file_name = f"photo_{p_idx:02d}.jpg"
                save_path = car_sub_dir / file_name

                # 다운로드 (세션 헤더 활용)
                try:
                    img_resp = await api_request.get(p_url)
                    if img_resp.status == 200:
                        img_bytes = await img_resp.body()
                        with open(save_path, "wb") as img_f:
                            img_f.write(img_bytes)

                        file_size = len(img_bytes)
                        sha256 = hashlib.sha256(img_bytes).hexdigest()
                        total_downloaded_bytes += file_size
                        total_downloaded_count += 1

                        downloaded_files.append({
                            "order": p_idx,
                            "url": p_url,
                            "local_path": str(save_path),
                            "file_size": file_size,
                            "sha256": sha256
                        })
                except Exception as e:
                    print(f"    [!] Failed to download {p_url}: {e}")

                await asyncio.sleep(0.05)

            duration = time.time() - t_start
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
                "downloaded_photos_count": len(downloaded_files),
                "photos": downloaded_files,
                "harvest_duration_sec": round(duration, 2)
            })

            print(f"  [{idx:02d}/10] Plate: {plate_full}, Total Photos: {len(clean_hd_photos)}장 (Downloaded: {len(downloaded_files)}), took {duration:.2f}s")
            await asyncio.sleep(0.3)

        out_path = Path("data/carmanager_raw/detailed_10_harvest.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(detailed_results, f, ensure_ascii=False, indent=2)

        print(f"\n[+] HARVEST COMPLETE:")
        print(f"    - Total Downloaded Photos: {total_downloaded_count}장")
        print(f"    - Total Downloaded Volume: {total_downloaded_bytes / (1024*1024):.2f} MB")
        print(f"    - Saved Metadata: {out_path}")
        await browser.close()

asyncio.run(run())
