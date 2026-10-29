"""
D1용 100대 테스트 차량 마이그레이션 SQL 생성 스크립트
"""

import sqlite3
import json

conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
cur = conn.cursor()

cur.execute("SELECT id, branch_id, plate_number, model_name, year, mileage, fuel_type, transmission, color, purchase_price, target_price, status, is_demo, vin, displacement_cc, first_registration_date, drive_type, interior_color, options_json, accident_history_json, primary_photo_url, manufacturer, trim, body_type, is_public, listing_ownership_type, is_priority_exposure, priority_rank, timeline_json, created_at, updated_at FROM vehicles WHERE is_demo = 1;")
rows = cur.fetchall()

sql_lines = [
    "-- DIRECTIVE 075 & 075-A: 100대 정밀 가상 테스트 차량 및 진단 데이터",
    "DELETE FROM vehicle_photos WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);",
    "DELETE FROM vehicles WHERE is_demo = 1;"
]

for r in rows:
    vals = []
    for val in r:
        if val is None:
            vals.append("NULL")
        elif isinstance(val, (int, float)):
            vals.append(str(val))
        else:
            escaped = str(val).replace("'", "''")
            vals.append(f"'{escaped}'")
    sql_lines.append(f"INSERT INTO vehicles (id, branch_id, plate_number, model_name, year, mileage, fuel_type, transmission, color, purchase_price, target_price, status, is_demo, vin, displacement_cc, first_registration_date, drive_type, interior_color, options_json, accident_history_json, primary_photo_url, manufacturer, trim, body_type, is_public, listing_ownership_type, is_priority_exposure, priority_rank, timeline_json, created_at, updated_at) VALUES ({', '.join(vals)});")

# 사진 쿼리
cur.execute("SELECT id, vehicle_id, photo_url, thumb_url, category, sort_order, is_primary, allow_video_use, caption, created_at, view_code, category_code, display_label FROM vehicle_photos WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);")
photo_rows = cur.fetchall()

for pr in photo_rows:
    vals = []
    for val in pr:
        if val is None:
            vals.append("NULL")
        elif isinstance(val, (int, float)):
            vals.append(str(val))
        else:
            escaped = str(val).replace("'", "''")
            vals.append(f"'{escaped}'")
    sql_lines.append(f"INSERT INTO vehicle_photos (id, vehicle_id, photo_url, thumb_url, category, sort_order, is_primary, allow_video_use, caption, created_at, view_code, category_code, display_label) VALUES ({', '.join(vals)});")

conn.close()

out_path = "cloudflare/d1/0003_demo_vehicles_100.sql"
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(sql_lines))

print(f"D1 마이그레이션 SQL 생성 완료: {out_path} ({len(rows)}대 차량, {len(photo_rows)}장 사진, {len(sql_lines)}줄)")
