import sqlite3
import json
import uuid
from datetime import datetime

db_path = "data/chamart/chamart_platform_demo.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

with open("scratch/carmanager_inspect/my_13_cleaned_cars.json", "r", encoding="utf-8") as f:
    cars = json.load(f)

with open("scratch/carmanager_inspect/top5_cars_mapped.json", "r", encoding="utf-8") as f:
    top5 = json.load(f)
landrover_detail = top5[0]

now = datetime.now().isoformat()
branch_id = "61fea9a4-58f0-42bd-862c-14fd16d0d21c"

ingested_results = []

for c in cars:
    car_seq = c.get("carSeq")
    plate = c.get("plate")
    suggest_no = c.get("suggestNo")
    title = c.get("clean_title")
    year = int(c.get("year")) if c.get("year") and c.get("year") != "미상" else 2020
    fuel = c.get("fuel") or "가솔린"
    transmission = c.get("mission") or "오토"
    mileage = int(str(c.get("mileage", "0")).replace(",", ""))
    
    is_landrover = (plate == "64노3143" or car_seq == "114204774")
    
    if is_landrover:
        status = "FOR_SALE"
        is_public = 1
        target_price = 1090
        options_list = [opt["text"] for opt in landrover_detail.get("options", [])]
        photos = landrover_detail.get("photos", [])
        primary_photo = photos[0]["originalUrl"] if photos else ""
        vin = landrover_detail.get("vin") or "SALCA2BN5JH761441"
        first_reg = landrover_detail.get("first_registration_date") or "2018-09-14"
        color = "화이트"
        manufacturer = "랜드로버"
        trim = "디스커버리 스포츠 2.0 TD4 SE"
        model_name = "랜드로버 디스커버리 스포츠"
    else:
        status = "DRAFT"
        is_public = 0
        target_price = 0
        options_list = []
        photos = []
        primary_photo = ""
        vin = f"TEMP-VIN-{car_seq}"
        first_reg = f"{year}-01-01"
        color = "미확인"
        parts = title.split()
        manufacturer = parts[0] if parts else "기타"
        model_name = " ".join(parts[:2]) if len(parts) >= 2 else title
        trim = " ".join(parts[2:]) if len(parts) > 2 else ""

    cursor.execute("SELECT vehicle_id FROM vehicle_listings WHERE listing_id = ?", (car_seq,))
    existing_listing = cursor.fetchone()
    
    timeline_json = json.dumps([{"event": "CARMANAGER_SYNC", "timestamp": now, "note": f"제시번호:{suggest_no}"}], ensure_ascii=False)

    if existing_listing:
        v_id = existing_listing[0]
        cursor.execute("""
            UPDATE vehicles SET
                plate_number=?, model_name=?, manufacturer=?, trim=?, year=?, mileage=?,
                fuel_type=?, transmission=?, color=?, target_price=?, status=?, is_public=?,
                primary_photo_url=?, options_json=?, timeline_json=?, updated_at=?
            WHERE id=?
        """, (
            plate, model_name, manufacturer, trim, year, mileage,
            fuel, transmission, color, target_price, status, is_public,
            primary_photo, json.dumps(options_list, ensure_ascii=False), timeline_json, now, v_id
        ))
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
            mileage, fuel, transmission, color, 0, target_price,
            status, 0, is_public, "OWNED", "CHAMART_OWNED",
            vin, first_reg, primary_photo, json.dumps(options_list, ensure_ascii=False), timeline_json,
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
            l_id, v_id, "CARMANAGER", car_seq, f"https://www.carmanager.co.kr/MyPageCar/Edit/{car_seq}", target_price,
            "ACTIVE" if is_public else "DRAFT_INCOMPLETE", "서울 성동구 용답동 장한평", True,
            "(주)더쿨모터스", f"제시번호: {suggest_no}", now, now, 0
        ))

    if photos:
        cursor.execute("DELETE FROM vehicle_photos WHERE vehicle_id = ?", (v_id,))
        for idx, p in enumerate(photos):
            p_id = str(uuid.uuid4())
            cat = "EXTERIOR" if idx < 4 else "INTERIOR"
            cursor.execute("""
                INSERT INTO vehicle_photos (
                    id, vehicle_id, photo_url, thumb_url, category, sort_order, is_primary, allow_video_use, created_at, photo_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p_id, v_id, p["originalUrl"], p["thumbUrl"], cat, idx + 1, (idx == 0), 1, now, "CARMANAGER"
            ))

    ingested_results.append({
        "vehicle_id": v_id,
        "carmanager_id": car_seq,
        "plate_number": plate,
        "model_name": model_name,
        "trim": trim,
        "target_price": target_price,
        "status": status,
        "is_public": bool(is_public),
        "photos_count": len(photos),
        "options_count": len(options_list)
    })

conn.commit()
conn.close()

print(f"카매니저 우리 차량 13대 운영 DB 정식 적재 완료!")
with open("scratch/carmanager_inspect/ingested_13_production.json", "w", encoding="utf-8") as f:
    json.dump(ingested_results, f, ensure_ascii=False, indent=2)

for r in ingested_results:
    p = r["plate_number"]
    mp = p[:2] + "*" + p[3:-2] + "**" if len(p) >= 6 else p
    print(f"[{r['carmanager_id']}] {mp} | {r['model_name']} | 가격:{r['target_price']}만원 | 상태:{r['status']}(공개:{r['is_public']}) | 사진:{r['photos_count']}장 | 옵션:{r['options_count']}개")
