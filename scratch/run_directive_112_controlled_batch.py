"""
DIRECTIVE 112 TASK 4: 60대 통제 배치 사진 확대 수집 및 안전 권한 검증 스크립트
"""

import os
import sys
import json
import re
import time
import uuid
import hashlib
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import sqlite3
from PIL import Image
import io
from datetime import datetime

from playwright.async_api import async_playwright
from chaficial.platform.sourcing.carmanager_client import load_env

load_env()

PHOTOS_BASE_DIR = Path("data/carmanager_raw/photos_controlled_batch")
PHOTOS_BASE_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_FILE = Path("scratch/directive_112_photo_evidence.json")
DB_PATH = "data/chamart/chamart_platform_demo.db"

def sanitize_filename(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', s)

def verify_image_bytes(b: bytes):
    if len(b) < 1000:
        return False, "", 0, 0
    sha = hashlib.sha256(b).hexdigest()
    try:
        with Image.open(io.BytesIO(b)) as img:
            img.verify()
        with Image.open(io.BytesIO(b)) as img:
            w, h = img.size
        return True, sha, w, h
    except Exception:
        return False, "", 0, 0

async def run_controlled_batch():
    username = os.getenv("CAR_MANAGER_ID") or os.getenv("CARMANAGER_ID")
    password = os.getenv("CAR_MANAGER_PW") or os.getenv("CARMANAGER_PW")
    if not username or not password:
        raise ValueError("CAR_MANAGER_ID and CAR_MANAGER_PW must be provided via env. Hardcoding strictly forbidden.")

    print("[*] Selecting 60 unphotod vehicles for Controlled Photo Expansion Batch...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 사전 통계
    c.execute("SELECT COUNT(DISTINCT vehicle_id) FROM vehicle_photos")
    initial_photod_vehicles = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vehicle_photos")
    initial_total_photos = c.fetchone()[0]

    # 사진이 없는 카매니저 차량 60대 추출
    c.execute("""
        SELECT l.listing_id, v.id, v.model_name
        FROM vehicles v
        JOIN vehicle_listings l ON v.id = l.vehicle_id
        WHERE l.platform = 'CARMANAGER'
          AND v.id NOT IN (SELECT DISTINCT vehicle_id FROM vehicle_photos)
        LIMIT 60
    """)
    target_rows = c.fetchall()
    print(f"[*] Target batch size: {len(target_rows)} vehicles")

    # 카매니저 로그인 및 토큰 획득
    print("[*] Logging into CarManager via Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.carmanager.co.kr/User/Login", wait_until="networkidle", timeout=30000)
        await page.fill("#userid", username)
        await page.fill("#userpwd", password)
        btn = await page.query_selector("button[onclick*='commitLogin']")
        if btn:
            async with page.expect_navigation(wait_until="networkidle", timeout=15000):
                await btn.click()
        await page.wait_for_timeout(2000)

        await page.goto("https://www.carmanager.co.kr/Car/Data", wait_until="networkidle", timeout=20000)
        enc_check = await page.evaluate(r"() => document.querySelector('#EncCheck')?.value || ''")
        print(f"[+] Acquired EncCheck token: {enc_check[:6]}****")

        api_request = context.request

        batch_results = []
        vehicles_with_photos = 0
        vehicles_without_photos = 0
        total_downloaded = 0
        total_highres = 0
        total_thumbnails = 0
        corrupt_images = 0
        all_unique_shas = set()
        db_inserted_records = 0

        for idx, (listing_id, vehicle_id, model_name) in enumerate(target_rows, 1):
            car_dir = PHOTOS_BASE_DIR / sanitize_filename(listing_id)
            car_dir.mkdir(parents=True, exist_ok=True)

            # 상세 팝업 요청
            try:
                resp = await api_request.post(
                    "https://www.carmanager.co.kr/PopupFrame/CarDetailEnc/",
                    form={"encarno": listing_id, "EncCheck": enc_check}
                )
                html = await resp.text()
            except Exception as ex:
                print(f"[-] Car {idx} ({listing_id[:10]}) detail request failed: {ex}")
                vehicles_without_photos += 1
                continue

            # 순수 카매니저 실사진 URL 정밀 필터링
            raw_matches = re.findall(r'https?://img\.carmanager\.co\.kr/temp/photo/\d+/[A-Fa-f0-9]+(?:_TH)?\.jpg[^\s"\'<>]*', html)
            photo_urls = []
            for u in raw_matches:
                clean_u = re.sub(r'(/dims/.*|\?.*)', '', u).replace("_TH.jpg", ".jpg")
                if clean_u not in photo_urls:
                    photo_urls.append(clean_u)

            if not photo_urls:
                vehicles_without_photos += 1
                batch_results.append({
                    "vehicle_id": vehicle_id,
                    "listing_id": listing_id,
                    "model_name": model_name,
                    "photos_found": 0,
                    "status": "NO_PHOTOS_ON_SOURCE"
                })
                continue

            vehicles_with_photos += 1
            car_records = []

            for p_idx, url in enumerate(photo_urls, 1):
                target_file = car_dir / f"photo_{p_idx:02d}.jpg"
                if not target_file.exists():
                    try:
                        img_resp = await api_request.get(url)
                        b = await img_resp.body()
                        with open(target_file, "wb") as f:
                            f.write(b)
                        total_downloaded += 1
                    except Exception as dl_err:
                        continue
                else:
                    with open(target_file, "rb") as f:
                        b = f.read()

                valid, sha, w, h = verify_image_bytes(b)
                if not valid:
                    corrupt_images += 1
                    continue

                all_unique_shas.add(sha)
                is_highres = (w >= 800 and h >= 600)
                if is_highres:
                    total_highres += 1
                else:
                    total_thumbnails += 1

                p_id = str(uuid.uuid4())
                cat = "EXTERIOR" if p_idx <= 4 else "INTERIOR"

                # DIRECTIVE 112 P0 보안 강화: 미확인 사진은 기본값 비공개/미승인/영상불허로 엄격 격리
                car_records.append((
                    p_id, vehicle_id, url, url, cat,
                    p_idx, (1 if p_idx == 1 else 0), 0, f"카매니저 실사진 #{p_idx}",
                    datetime.now().isoformat(), "UNVERIFIED", "CARMANAGER", sha,
                    "PENDING_VERIFICATION", str(target_file), "PRIVATE", "PENDING_REVIEW",
                    "image/jpeg", len(b)
                ))

            # DB 적재
            if car_records:
                c.executemany("""
                    INSERT OR REPLACE INTO vehicle_photos (
                        id, vehicle_id, photo_url, thumb_url, category,
                        sort_order, is_primary, allow_video_use, caption,
                        created_at, verification_status, photo_source, original_file_hash,
                        usage_rights_status, original_path, public_visibility, approval_status,
                        mime_type, file_size_bytes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, car_records)
                conn.commit()
                db_inserted_records += len(car_records)

            batch_results.append({
                "vehicle_id": vehicle_id,
                "listing_id": listing_id,
                "model_name": model_name,
                "photos_found": len(photo_urls),
                "photos_ingested": len(car_records),
                "status": "PHOTOS_INGESTED"
            })

            if idx % 10 == 0 or idx == len(target_rows):
                print(f"  [Batch {idx}/{len(target_rows)}] Verified Photos: {len(car_records)} | Model: {model_name[:20]}")

            await asyncio.sleep(0.3)

        await browser.close()

    # 사후 통계
    c.execute("SELECT COUNT(DISTINCT vehicle_id) FROM vehicle_photos")
    final_photod_vehicles = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vehicle_photos")
    final_total_photos = c.fetchone()[0]
    conn.close()

    net_new_photod_vehicles = final_photod_vehicles - initial_photod_vehicles
    net_new_photos = final_total_photos - initial_total_photos

    evidence = {
        "directive": "DIRECTIVE 112 TASK 4",
        "timestamp": datetime.now().isoformat(),
        "batch_size": len(target_rows),
        "vehicles_with_photos": vehicles_with_photos,
        "vehicles_without_photos": vehicles_without_photos,
        "total_downloaded_photos": total_downloaded,
        "total_highres_photos": total_highres,
        "total_thumbnails": total_thumbnails,
        "corrupt_images": corrupt_images,
        "unique_shas_count": len(all_unique_shas),
        "db_inserted_records": db_inserted_records,
        "initial_photod_vehicles": initial_photod_vehicles,
        "final_photod_vehicles": final_photod_vehicles,
        "net_new_photod_vehicles": net_new_photod_vehicles,
        "initial_total_photos": initial_total_photos,
        "final_total_photos": final_total_photos,
        "net_new_photos": net_new_photos,
        "rights_status_summary": {
            "usage_rights_status": "PENDING_VERIFICATION (100%)",
            "public_visibility": "PRIVATE (100%)",
            "approval_status": "PENDING_REVIEW (100%)",
            "allow_video_use": "0 (100% Forbidden)"
        },
        "commercial_usable_photos": 0,
        "batch_details_sample": batch_results[:10]
    }

    with open(EVIDENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)

    print("\n================================================================================")
    print("[+] DIRECTIVE 112 60-Car Controlled Batch Completed Successfully!")
    print(f"    - Target Batch Inspected: {len(target_rows)}")
    print(f"    - Vehicles with Photos Found: {vehicles_with_photos}")
    print(f"    - Vehicles with No Photos (Source-Level): {vehicles_without_photos}")
    print(f"    - High-Resolution Photos Verified: {total_highres}")
    print(f"    - Unique SHA256 Photos: {len(all_unique_shas)}")
    print(f"    - Net New Vehicles with Photos in DB: +{net_new_photod_vehicles}")
    print(f"    - Net New Photos in DB: +{net_new_photos}")
    print(f"    - Security: 100% PRIVATE & PENDING_REVIEW (Commercial Use = 0)")
    print(f"    - Evidence saved to: {EVIDENCE_FILE}")
    print("================================================================================")
    return evidence

if __name__ == "__main__":
    asyncio.run(run_controlled_batch())
