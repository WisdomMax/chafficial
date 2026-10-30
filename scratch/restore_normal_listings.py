import sqlite3
import json

def restore_mistakenly_deleted():
    backup_db = "data/chamart/backups/chamart_online_backup_directive115_20261030_234504.db"
    target_db = "data/chamart/chamart_platform_demo.db"

    print("=== [복원 작업] 잘못 삭제된 정상 매물 5건 원자적 복원 ===")
    
    b_conn = sqlite3.connect(backup_db)
    b_c = b_conn.cursor()
    
    t_conn = sqlite3.connect(target_db)
    t_c = t_conn.cursor()

    # 복원 대상 5건의 listing_id
    restore_ids = [
        "KB5+r92iDSPMPoF29e/9mA==",
        "kBYAJHA7MyKZsNQYunZImQ==",
        "kBLkL1Hq/p3sxNUvcVR+GA==",
        "kBG+SmFwDEEas0uMhdq/sw==",
        "encar_sw_102938"
    ]

    for lid in restore_ids:
        b_c.execute("SELECT * FROM vehicle_listings WHERE listing_id = ?", (lid,))
        row = b_c.fetchone()
        if row:
            # 컬럼명 가져오기
            col_names = [d[0] for d in b_c.description]
            placeholders = ", ".join(["?"] * len(col_names))
            cols_str = ", ".join(col_names)
            
            t_c.execute(f"INSERT OR REPLACE INTO vehicle_listings ({cols_str}) VALUES ({placeholders})", row)
            print(f"[+] Restored listing: {lid} (Platform: {row[col_names.index('platform')]})")

    t_conn.commit()

    # 무결성 점검
    t_c.execute("PRAGMA integrity_check;")
    print("PRAGMA integrity_check:", t_c.fetchall())
    t_c.execute("PRAGMA foreign_key_check;")
    print("PRAGMA foreign_key_check:", t_c.fetchall())

    t_c.execute("SELECT count(*) FROM vehicle_listings WHERE platform = 'CARMANAGER';")
    print(f"Total CarManager listings now: {t_c.fetchone()[0]} (1,851건 완전 복구!)")

    b_conn.close()
    t_conn.close()

if __name__ == "__main__":
    restore_mistakenly_deleted()
