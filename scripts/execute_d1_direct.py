"""
D1 direct command batch execution (D1_RESET_DO 방지)
"""

import sqlite3
import subprocess
import json

conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
cur = conn.cursor()

# 1. 기존 demo 삭제
print("[1] 기존 is_demo=1 삭제...")
clean_sql = """
DELETE FROM vehicle_photos WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);
DELETE FROM vehicle_defects WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);
DELETE FROM vehicle_listings WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);
DELETE FROM transactions WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);
DELETE FROM dealer_rights_ledgers WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);
DELETE FROM platform_publishing_records WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);
DELETE FROM vehicles WHERE is_demo = 1;
"""
cmd = ["npx", "-y", "wrangler", "d1", "execute", "chamart-db", "--remote", f"--command={clean_sql}"]
subprocess.run(cmd, check=True)

# 2. 100대 차량 인서트 (10대씩 묶음)
cur.execute("SELECT id, branch_id, plate_number, model_name, year, mileage, fuel_type, transmission, color, purchase_price, target_price, status, is_demo, vin, displacement_cc, first_registration_date, drive_type, interior_color, options_json, accident_history_json, primary_photo_url, manufacturer, trim, body_type, is_public, listing_ownership_type, is_priority_exposure, priority_rank, timeline_json FROM vehicles WHERE is_demo = 1;")
vehicles = cur.fetchall()

print(f"[2] 차량 {len(vehicles)}대 인서트 시작...")
cols = "id, branch_id, plate_number, model_name, year, mileage, fuel_type, transmission, color, purchase_price, target_price, status, is_demo, vin, displacement_cc, first_registration_date, drive_type, interior_color, options_json, accident_history_json, primary_photo_url, manufacturer, trim, body_type, is_public, listing_ownership_type, is_priority_exposure, priority_rank, timeline_json, created_at, updated_at"

batch_size = 10
for i in range(0, len(vehicles), batch_size):
    batch = vehicles[i:i + batch_size]
    val_rows = []
    for r in batch:
        vals = []
        for val in r:
            if val is None:
                vals.append("NULL")
            elif isinstance(val, (int, float)):
                vals.append(str(val))
            else:
                escaped = str(val).replace("'", "''")
                vals.append(f"'{escaped}'")
        vals.append("datetime('now')")
        vals.append("datetime('now')")
        val_rows.append(f"({', '.join(vals)})")

    sql = f"INSERT INTO vehicles ({cols}) VALUES {', '.join(val_rows)};"
    cmd = ["npx", "-y", "wrangler", "d1", "execute", "chamart-db", "--remote", f"--command={sql}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"차량 배치 {i} 실패:", res.stderr)
    else:
        print(f"차량 배치 {i+len(batch)}/{len(vehicles)} 성공!")

# 3. 사진 인서트 (50개씩 묶음)
cur.execute("SELECT id, vehicle_id, photo_url, thumb_url, category, sort_order, is_primary, allow_video_use, caption, view_code, category_code, display_label FROM vehicle_photos WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);")
photos = cur.fetchall()
p_cols = "id, vehicle_id, photo_url, thumb_url, category, sort_order, is_primary, allow_video_use, caption, view_code, category_code, display_label, created_at"

print(f"[3] 사진 {len(photos)}건 인서트 시작...")
p_batch_size = 40
for pi in range(0, len(photos), p_batch_size):
    p_batch = photos[pi:pi + p_batch_size]
    val_rows = []
    for pr in p_batch:
        vals = []
        for val in pr:
            if val is None:
                vals.append("NULL")
            elif isinstance(val, (int, float)):
                vals.append(str(val))
            else:
                escaped = str(val).replace("'", "''")
                vals.append(f"'{escaped}'")
        vals.append("datetime('now')")
        val_rows.append(f"({', '.join(vals)})")

    sql = f"INSERT INTO vehicle_photos ({p_cols}) VALUES {', '.join(val_rows)};"
    cmd = ["npx", "-y", "wrangler", "d1", "execute", "chamart-db", "--remote", f"--command={sql}"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"사진 배치 {pi} 실패:", res.stderr)
    else:
        if (pi + len(p_batch)) % 200 == 0 or (pi + len(p_batch)) == len(photos):
            print(f"사진 {pi+len(p_batch)}/{len(photos)} 완료!")

conn.close()
print("D1 마이그레이션 전체 완료!")
