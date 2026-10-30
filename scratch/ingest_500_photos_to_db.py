import sqlite3
import json
import hashlib
import time
import uuid
from pathlib import Path
from PIL import Image

db_path = Path("data/chamart/chamart_platform_demo.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

manifest_path = Path("data/carmanager_raw/photos_500_manifest.json")
if not manifest_path.exists():
    print("[!] Manifest not found yet.")
    exit(0)

with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

cars = manifest.get("cars", [])
print(f"[*] Ingesting Verified Photos and Metadata for {len(cars)} Vehicles into DB...")

now_str = time.strftime("%Y-%m-%d %H:%M:%S")

inserted_photos = 0
updated_photos = 0
matched_vehicles_count = 0
updated_plates_count = 0
updated_vins_count = 0

for car_info in cars:
    encarno = car_info["encarno"]
    
    # 1. 차량 조회
    cursor.execute("SELECT vehicle_id FROM vehicle_listings WHERE platform = 'CARMANAGER' AND listing_id = ?", (encarno,))
    row = cursor.fetchone()
    if not row:
        continue
    
    v_id = row[0]
    matched_vehicles_count += 1

    # 2. 실데이터 보강 (정식 번호판 및 VIN 업데이트)
    full_plate = car_info.get("full_plate")
    vin = car_info.get("vin")
    if full_plate:
        cursor.execute("UPDATE vehicles SET plate_number = ? WHERE id = ? AND (plate_number = '' OR plate_number LIKE '%*%')", (full_plate, v_id))
        if cursor.rowcount > 0:
            updated_plates_count += 1

    if vin:
        cursor.execute("UPDATE vehicles SET vin = ? WHERE id = ? AND (vin IS NULL OR vin LIKE 'CM-JHP-%')", (vin, v_id))
        if cursor.rowcount > 0:
            updated_vins_count += 1

    # 3. 사진 데이터 삽입 (원본 URL 그대로 보존)
    for p in car_info.get("photos", []):
        if p["status"] != "VERIFIED":
            continue

        order = p["order"]
        p_url = p["url"]  # 원본 실제 URL 100% 보존
        l_path = p["local_path"]
        p_hash = p["sha256"]
        f_size = p["size_bytes"]
        w = p.get("width", 0)
        h = p.get("height", 0)

        # 카테고리 매핑
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

        # 중복 여부 확인
        cursor.execute("SELECT id FROM vehicle_photos WHERE vehicle_id = ? AND original_file_hash = ?", (v_id, p_hash))
        existing_p = cursor.fetchone()
        
        if existing_p:
            # 기존 레코드의 URL이 조립된 가짜 URL이면 원본 URL로 업데이트
            cursor.execute("""
                UPDATE vehicle_photos 
                SET photo_url = ?, original_path = ?, file_size_bytes = ?, display_label = ?
                WHERE id = ?
            """, (p_url, l_path, f_size, label, existing_p[0]))
            updated_photos += 1
        else:
            p_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO vehicle_photos (
                    id, vehicle_id, photo_url, category, sort_order, is_primary, 
                    allow_video_use, created_at, photo_source, display_label,
                    original_path, file_size_bytes, original_file_hash
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, 'CARMANAGER', ?, ?, ?, ?)
            """, (
                p_id, v_id, p_url, cat, order, 1 if order == 1 else 0,
                now_str, label, l_path, f_size, p_hash
            ))
            inserted_photos += 1

conn.commit()

# 통계 출력
cursor.execute("SELECT count(*) FROM vehicle_photos")
total_photos_in_db = cursor.fetchone()[0]

cursor.execute("SELECT count(DISTINCT vehicle_id) FROM vehicle_photos")
vehicles_with_photos = cursor.fetchone()[0]

conn.close()

print(f"\n=======================================================")
print(f"[+] 500-CAR PHOTOS & METADATA DB INGESTION COMPLETED")
print(f"=======================================================")
print(f"  * Matched Target Vehicles    : {matched_vehicles_count}대")
print(f"  * Newly Inserted Photos      : {inserted_photos}장")
print(f"  * Updated Existing Photos    : {updated_photos}장")
print(f"  * Updated Full Plates        : {updated_plates_count}건")
print(f"  * Updated Genuine VINs       : {updated_vins_count}건")
print(f"  * Vehicles With Photos in DB : {vehicles_with_photos}대")
print(f"  * Total Photos in Entire DB  : {total_photos_in_db}장")
print(f"=======================================================")
