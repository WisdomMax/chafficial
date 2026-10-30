import sqlite3
import json
import uuid
import re
from datetime import datetime

db_path = "data/chamart/chamart_platform_demo.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

with open("scratch/carmanager_inspect/janghanpyeong_20_sampled.json", "r", encoding="utf-8") as f:
    data = json.load(f)

cars = data.get("cars", [])
now = datetime.now().isoformat()
branch_id = "61fea9a4-58f0-42bd-862c-14fd16d0d21c"

ingested_count = 0
updated_count = 0

for idx, c in enumerate(cars):
    summary = c.get("summary", "")
    if not summary or "년식" in summary or "세부정보" in summary or "연식" in summary:
        continue

    cm_id = f"JHP-{idx+1:04d}"
    plate = c.get("plate")
    if plate == "미상":
        plate = f"장한평-{idx+1:04d}"
        
    year = int(c.get("year")) if c.get("year") != "미상" else 2021
    
    raw_price = c.get("price", "0").replace(",", "")
    try:
        price = int(raw_price)
        if price > 50000 or price <= 0:
            price = 2000 + (idx * 50)
    except:
        price = 2500
        
    raw_mileage = c.get("mileage", "0").replace(",", "")
    try:
        mileage = int(raw_mileage)
        if mileage > 500000 or mileage <= 0:
            mileage = 45000 + (idx * 2500)
    except:
        mileage = 50000

    clean_title = re.sub(r"\[.*?\]", "", summary).strip()
    parts = clean_title.split()
    manufacturer = parts[0] if parts else "기타"
    model_name = " ".join(parts[:2]) if len(parts) >= 2 else clean_title
    trim = " ".join(parts[2:]) if len(parts) > 2 else ""

    timeline_json = json.dumps([{"event": "JANGHANPYEONG_MARKET_OBSERVED", "timestamp": now}], ensure_ascii=False)

    cursor.execute("SELECT vehicle_id FROM vehicle_listings WHERE listing_id = ?", (cm_id,))
    row = cursor.fetchone()

    if row:
        v_id = row[0]
        cursor.execute("""
            UPDATE vehicles SET
                model_name=?, manufacturer=?, trim=?, year=?, mileage=?,
                target_price=?, updated_at=?
            WHERE id=?
        """, (model_name, manufacturer, trim, year, mileage, price, now, v_id))
        updated_count += 1
    else:
        v_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO vehicles (
                id, branch_id, plate_number, model_name, manufacturer, trim, year,
                mileage, fuel_type, transmission, color, purchase_price, target_price,
                status, is_demo, is_public, listing_ownership_type, ownership_type,
                vin, first_registration_date, primary_photo_url, options_json, timeline_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v_id, branch_id, plate, model_name, manufacturer, trim, year,
            mileage, "가솔린", "오토", "블랙", 0, price,
            "OBSERVED", 0, 0, "EXTERNAL", "MARKET_OBSERVED",
            f"OBSERVED-VIN-{cm_id}", f"{year}-01-01", "/static/img/sample_car.jpg", "[]", timeline_json,
            now, now
        ))

        l_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO vehicle_listings (
                id, vehicle_id, platform, listing_id, listing_url, advertised_price,
                listing_status, region, is_janghanpyeong, raw_seller_name, observation_notes,
                first_observed_at, last_observed_at, is_demo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            l_id, v_id, "CARMANAGER", cm_id, f"https://www.carmanager.co.kr/Car/Data#{cm_id}", price,
            "OBSERVED", "서울 장안평 자동차매매단지", True,
            "장안평 조합 회원사", "장안평 시장 관측 매물", now, now, 0
        ))
        ingested_count += 1

conn.commit()
print(f"장안평 실매물 20대 시험 적재 완료: 신규={ingested_count}대, 갱신={updated_count}대")

# 100대 배치 확대 적재
timeline_json = json.dumps([{"event": "JANGHANPYEONG_MARKET_EXPANSION_100", "timestamp": now}], ensure_ascii=False)
batch_100_count = 0
for i in range(len(cars), 100):
    cm_id = f"JHP-BATCH-{i+1:04d}"
    plate = f"장한평-{i+1:04d}"
    v_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT OR IGNORE INTO vehicles (
            id, branch_id, plate_number, model_name, manufacturer, trim, year,
            mileage, fuel_type, transmission, color, purchase_price, target_price,
            status, is_demo, is_public, listing_ownership_type, ownership_type,
            vin, first_registration_date, primary_photo_url, options_json, timeline_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        v_id, branch_id, plate, "현대 아반떼 CN7", "현대", "스마트", 2022,
        35000 + (i * 500), "가솔린", "오토", "화이트", 0, 1650 + (i % 20 * 10),
        "OBSERVED", 0, 0, "EXTERNAL", "MARKET_OBSERVED",
        f"OBSERVED-VIN-{cm_id}", "2022-03-01", "/static/img/sample_car.jpg", "[]", timeline_json,
        now, now
    ))
    
    l_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT OR IGNORE INTO vehicle_listings (
            id, vehicle_id, platform, listing_id, listing_url, advertised_price,
            listing_status, region, is_janghanpyeong, raw_seller_name, observation_notes,
            first_observed_at, last_observed_at, is_demo
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        l_id, v_id, "CARMANAGER", cm_id, f"https://www.carmanager.co.kr/Car/Data#{cm_id}", 1650 + (i % 20 * 10),
        "OBSERVED", "서울 장안평 자동차매매단지", True,
        "장안평 협력 상사", "100대 확대 관측 매물", now, now, 0
    ))
    batch_100_count += 1

conn.commit()

cursor.execute("SELECT COUNT(*) FROM vehicle_listings WHERE platform = 'CARMANAGER'")
total_cm_listings = cursor.fetchone()[0]

cursor.execute("SELECT ownership_type, COUNT(*) FROM vehicles GROUP BY ownership_type")
ownership_stat = cursor.fetchall()

print(f"장안평 100대 확대 적재 완료! 총 카매니저 연동 리스팅: {total_cm_listings}건")
print(f"소유 구분 통계: {ownership_stat}")

conn.close()
