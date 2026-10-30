import sqlite3
import json
import hashlib
import time
import uuid
from pathlib import Path

db_path = Path("data/chamart/chamart_platform_demo.db")
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

manifest_path = Path("data/carmanager_raw/photos_500_highres_manifest.json")
with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

cars = manifest.get("cars", [])
print(f"[*] Ingesting 3,183 High-Res (1024x768) Photos from {len(cars)} Vehicles into DB...")

now_str = time.strftime("%Y-%m-%d %H:%M:%S")

inserted_photos = 0
updated_photos = 0
matched_vehicles_count = 0

for car_info in cars:
    encarno = car_info["encarno"]
    
    # encarno 기준 매칭 (순번 기반 위험 100% 제거)
    cursor.execute("SELECT vehicle_id FROM vehicle_listings WHERE platform = 'CARMANAGER' AND listing_id = ?", (encarno,))
    row = cursor.fetchone()
    if not row:
        continue
    
    v_id = row[0]
    matched_vehicles_count += 1

    for p in car_info.get("photos", []):
        if p["status"] != "VERIFIED":
            continue

        order = p["order"]
        p_url = p["url"]  # 1024x768 고화질 실제 원본 URL
        l_path = p["local_path"]
        p_hash = p["sha256"]
        f_size = p["size_bytes"]
        w = p.get("width", 1024)
        h = p.get("height", 768)

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
print(f"[+] HIGH-RES 1024x768 PHOTOS DB INGESTION COMPLETED")
print(f"=======================================================")
print(f"  * Matched Vehicles by Encarno : {matched_vehicles_count}대")
print(f"  * Newly Inserted Photos       : {inserted_photos}장")
print(f"  * Updated Existing Photos     : {updated_photos}장")
print(f"  * Vehicles With Photos in DB  : {vehicles_with_photos}대")
print(f"  * Total Photos in Entire DB   : {total_photos_in_db}장")
print(f"=======================================================")
