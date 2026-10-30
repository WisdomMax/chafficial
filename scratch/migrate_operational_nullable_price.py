import sqlite3
import shutil
import os
from pathlib import Path

DB_PATH = Path("data/chamart/chamart_platform_demo.db")
BACKUP_PATH = Path("data/chamart/chamart_platform_demo.db.backup_directive112")

def migrate():
    print(f"[*] Starting Operational DB Nullable Price Migration...")
    
    # 안전 백업 생성
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"[+] Backup created at {BACKUP_PATH} ({BACKUP_PATH.stat().st_size} bytes)")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. vehicles 테이블 DDL 가져오기
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='vehicles'")
    vehicles_sql = c.fetchone()[0]
    
    # target_price INTEGER NOT NULL -> target_price INTEGER
    new_vehicles_sql = vehicles_sql.replace("target_price INTEGER NOT NULL", "target_price INTEGER")
    new_vehicles_sql = new_vehicles_sql.replace("target_price INTEGER,", "target_price INTEGER,")
    # 테이블명 임시 변경
    new_vehicles_sql = new_vehicles_sql.replace("CREATE TABLE vehicles", "CREATE TABLE vehicles_new")
    
    print("[*] Recreating vehicles table with NULLABLE target_price...")
    c.execute(new_vehicles_sql)
    c.execute("INSERT INTO vehicles_new SELECT * FROM vehicles")
    c.execute("DROP TABLE vehicles")
    c.execute("ALTER TABLE vehicles_new RENAME TO vehicles")

    # 2. vehicle_listings 테이블 DDL 가져오기
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='vehicle_listings'")
    vl_sql = c.fetchone()[0]
    
    new_vl_sql = vl_sql.replace("advertised_price INTEGER NOT NULL", "advertised_price INTEGER")
    new_vl_sql = new_vl_sql.replace("CREATE TABLE vehicle_listings", "CREATE TABLE vehicle_listings_new")
    
    print("[*] Recreating vehicle_listings table with NULLABLE advertised_price...")
    c.execute(new_vl_sql)
    c.execute("INSERT INTO vehicle_listings_new SELECT * FROM vehicle_listings")
    c.execute("DROP TABLE vehicle_listings")
    c.execute("ALTER TABLE vehicle_listings_new RENAME TO vehicle_listings")

    # 3. 기존 카매니저 0원 가격 매물 정정 (외부 장한평 매물 중 가격 0원인 것은 '상담' 미공개 매물이므로 NULL로 전환)
    c.execute("""
        UPDATE vehicles
        SET target_price = NULL
        WHERE target_price = 0 AND (ownership_type = 'EXTERNAL' OR listing_ownership_type != 'OWNED')
    """)
    corrected_vehicles = c.rowcount

    c.execute("""
        UPDATE vehicle_listings
        SET advertised_price = NULL
        WHERE advertised_price = 0 AND platform = 'CARMANAGER'
    """)
    corrected_listings = c.rowcount

    conn.commit()

    # 검증
    c.execute("PRAGMA table_info(vehicles)")
    for col in c.fetchall():
        if col[1] == 'target_price':
            print(f"[+] vehicles.target_price schema: notnull={col[3]} (0=Nullable)")
    
    c.execute("PRAGMA table_info(vehicle_listings)")
    for col in c.fetchall():
        if col[1] == 'advertised_price':
            print(f"[+] vehicle_listings.advertised_price schema: notnull={col[3]} (0=Nullable)")

    c.execute("SELECT COUNT(*) FROM vehicles WHERE target_price IS NULL")
    null_v = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vehicles WHERE target_price = 0")
    zero_v = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vehicles WHERE target_price > 0")
    valid_v = c.fetchone()[0]

    print("\n================================================================================")
    print(f"[+] Operational DB Migration Successfully Completed!")
    print(f"    - Corrected Vehicles (0 -> NULL): {corrected_vehicles}")
    print(f"    - Corrected Listings (0 -> NULL): {corrected_listings}")
    print(f"    - Vehicles target_price IS NULL (상담/미공개): {null_v}")
    print(f"    - Vehicles target_price == 0 (왜곡 잔존): {zero_v}")
    print(f"    - Vehicles target_price > 0 (확정 가격): {valid_v}")
    print("================================================================================")

    conn.close()

if __name__ == "__main__":
    migrate()
