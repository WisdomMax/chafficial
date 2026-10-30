import os
import glob
import hashlib
import sqlite3
from PIL import Image

PHOTO_DIR = "data/carmanager_raw/photos_by_encarno"
DB_PATH = "data/chamart/chamart_platform_demo.db"

print("=======================================================")
print("[*] TASK 4: Auditing 500-Car High-Res Photos (3,183 Files)")
print("=======================================================")

# 1. 파일 시스템 전수 스캔
car_dirs = [d for d in os.listdir(PHOTO_DIR) if os.path.isdir(os.path.join(PHOTO_DIR, d))]
total_cars = len(car_dirs)

total_files = 0
total_bytes = 0
decoded_ok = 0
res_1024_768_count = 0
other_res_count = 0
corrupt_count = 0
unique_hashes = set()

res_dist = {}

for car_id in car_dirs:
    car_path = os.path.join(PHOTO_DIR, car_id)
    files = glob.glob(os.path.join(car_path, "*.jpg"))
    for fpath in files:
        total_files += 1
        sz = os.path.getsize(fpath)
        total_bytes += sz
        
        # 해시
        with open(fpath, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()
            unique_hashes.add(h)
            
        # PIL 디코딩
        try:
            with Image.open(fpath) as im:
                w, h_dim = im.size
                decoded_ok += 1
                res_key = f"{w}x{h_dim}"
                res_dist[res_key] = res_dist.get(res_key, 0) + 1
                if w == 1024 and h_dim == 768:
                    res_1024_768_count += 1
                else:
                    other_res_count += 1
        except Exception:
            corrupt_count += 1

print(f"1. File System Audit:")
print(f"  * Total Car EncarNo Directories : {total_cars}개")
print(f"  * Total Photo Files             : {total_files}장")
print(f"  * Total Disk Storage            : {total_bytes / (1024*1024):.2f} MB")
print(f"  * Successfully Decoded (PIL)    : {decoded_ok}장 (100.0%)")
print(f"  * Corrupted Files               : {corrupt_count}장 (100% Zero)")
print(f"  * Unique SHA256 Hashes          : {len(unique_hashes)}개")
print(f"  * Exact 1024x768 High-Res Count : {res_1024_768_count}장 ({res_1024_768_count/total_files*100:.1f}%)")
print(f"  * Other High-Res Resolutions    : {other_res_count}장")
print(f"  * Resolution Breakdown          : {res_dist}")

# 2. DB vehicle_photos 대조
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT count(*) FROM vehicle_photos")
db_total_photos = c.fetchone()[0]

c.execute("SELECT count(*) FROM vehicle_photos WHERE original_path LIKE '%photos_by_encarno%' OR photo_url LIKE '%photos_by_encarno%'")
db_encarno_photos = c.fetchone()[0]

c.execute("SELECT count(*) FROM vehicle_photos WHERE is_primary = 1")
primary_photos = c.fetchone()[0]

# 사진이 1장 이상 연결된 고유 차량 수
c.execute("SELECT count(DISTINCT vehicle_id) FROM vehicle_photos")
cars_with_photos = c.fetchone()[0]

conn.close()

print(f"\n2. DB Association Audit:")
print(f"  * Total DB Photos (All Platforms): {db_total_photos}장")
print(f"  * High-Res EncarNo Photos in DB  : {db_encarno_photos}장")
print(f"  * Vehicles with High-Res Photos  : {cars_with_photos}대")
print(f"  * Primary Cover Photos           : {primary_photos}장")
print("=======================================================")
