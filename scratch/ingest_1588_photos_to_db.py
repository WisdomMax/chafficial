import sqlite3
import json
import hashlib
import time
import uuid
from pathlib import Path

db_path = Path("data/chamart/chamart_platform_demo.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

photo_base = Path("data/carmanager_raw/photos_100_cars")
car_dirs = sorted(list(photo_base.glob("car_*")))

print(f"[*] Ingesting 1,588 Local Harvested Photos from {len(car_dirs)} Vehicles into DB...")

now_str = time.strftime("%Y-%m-%d %H:%M:%S")

with open("data/carmanager_raw/detailed_100_harvest.json", "r", encoding="utf-8") as f:
    harvest_data = json.load(f)

cars_meta = harvest_data["cars"]
meta_by_enc = {c["encarno"]: c for c in cars_meta}

inserted_photos = 0
skipped_existing_photos = 0
matched_vehicles_count = 0

for idx, c_meta in enumerate(cars_meta, 1):
    enc = c_meta["encarno"]
    cursor.execute("SELECT vehicle_id FROM vehicle_listings WHERE platform = 'CARMANAGER' AND listing_id = ?", (enc,))
    row = cursor.fetchone()
    if not row:
        continue
    
    v_id = row[0]
    matched_vehicles_count += 1

    plate_str = c_meta.get("plate_full") or f"tail_{enc[:8]}"
    safe_plate = plate_str.replace(" ", "_").replace("/", "_")
    car_dir = photo_base / f"car_{idx:03d}_{safe_plate}"

    if not car_dir.exists():
        continue

    photo_files = sorted(list(car_dir.glob("photo_*.jpg")))

    for p_file in photo_files:
        order = int(p_file.stem.split("_")[1])
        file_size = p_file.stat().st_size
        
        with open(p_file, "rb") as f:
            p_hash = hashlib.sha256(f.read()).hexdigest()

        # 정밀 카테고리 분류
        if order in (1, 2, 3, 4):
            cat = "EXTERIOR"
            label = f"외관 실사 ({order}번)"
        elif order in (5, 6, 7):
            cat = "INTERIOR"
            label = f"실내/계기판 ({order}번)"
        elif order in (8, 9):
            cat = "DETAIL"
            label = f"휠/타이어/엔진룸 ({order}번)"
        else:
            cat = "UNKNOWN"
            label = f"기타/옵션 ({order}번)"

        # 멱등성 검사 (동일 차량 + 동일 파일 해시)
        cursor.execute("SELECT id FROM vehicle_photos WHERE vehicle_id = ? AND original_file_hash = ?", (v_id, p_hash))
        existing_p = cursor.fetchone()
        if existing_p:
            skipped_existing_photos += 1
        else:
            photo_url = f"https://img.carmanager.co.kr/photos/{enc}/{p_file.name}"
            p_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO vehicle_photos (
                    id, vehicle_id, photo_url, category, sort_order, is_primary, 
                    allow_video_use, created_at, photo_source, display_label,
                    original_path, file_size_bytes, original_file_hash
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, 'CARMANAGER', ?, ?, ?, ?)
            """, (
                p_id, v_id, photo_url, cat, order, 1 if order == 1 else 0,
                now_str, label, str(p_file), file_size, p_hash
            ))
            inserted_photos += 1

conn.commit()

# 검증 통계
cursor.execute("SELECT count(*) FROM vehicle_photos")
total_photos_in_db = cursor.fetchone()[0]

cursor.execute("SELECT count(*) FROM vehicle_photos WHERE original_path LIKE '%photos_100_cars%'")
total_100_photos_in_db = cursor.fetchone()[0]

cursor.execute("SELECT category, count(*) FROM vehicle_photos WHERE original_path LIKE '%photos_100_cars%' GROUP BY category")
cat_summary = cursor.fetchall()

conn.close()

print(f"\n=======================================================")
print(f"[+] 1,588 PHOTOS DB INGESTION COMPLETED")
print(f"=======================================================")
print(f"  * Matched Target Vehicles    : {matched_vehicles_count}대")
print(f"  * Newly Inserted Photos      : {inserted_photos}장")
print(f"  * Skipped (Idempotent Exists): {skipped_existing_photos}장")
print(f"  * Total 100-Car Photos in DB : {total_100_photos_in_db}장")
print(f"  * Total Photos in Entire DB  : {total_photos_in_db}장")
print(f"  * Photo Category Breakdown   : {cat_summary}")
print(f"=======================================================")
