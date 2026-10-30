import sqlite3
import os
import shutil
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/chamart/chamart_platform_demo.db")
BACKUP_DIR = Path("data/chamart/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
ONLINE_BACKUP_PATH = BACKUP_DIR / f"chamart_online_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
RESTORE_TEST_PATH = BACKUP_DIR / "chamart_restore_test.db"

def run_integrity_audit():
    print("[*] 1. Creating Online Backup via SQLite Online Backup API (WAL-Safe)...")
    src_conn = sqlite3.connect(DB_PATH)
    dst_conn = sqlite3.connect(ONLINE_BACKUP_PATH)
    
    with dst_conn:
        src_conn.backup(dst_conn, pages=100)
    dst_conn.close()
    print(f"[+] Online Backup created: {ONLINE_BACKUP_PATH} ({ONLINE_BACKUP_PATH.stat().st_size} bytes)")

    print("\n[*] 2. Running PRAGMA Integrity Checks...")
    c = src_conn.cursor()
    c.execute("PRAGMA integrity_check")
    integrity_res = c.fetchall()
    print("    PRAGMA integrity_check:", integrity_res)

    c.execute("PRAGMA foreign_key_check")
    fk_res = c.fetchall()
    print("    PRAGMA foreign_key_check (Empty=Pass):", fk_res)

    print("\n[*] 3. Auditing Core Tables, Row Counts, and Indexes...")
    tables = [
        "vehicles", "vehicle_listings", "vehicle_photos",
        "market_collection_runs", "market_listing_observations", "market_listing_events",
        "carmanager_sync_logs"
    ]
    audit_counts = {}
    for t in tables:
        try:
            c.execute(f"SELECT COUNT(*) FROM {t}")
            audit_counts[t] = c.fetchone()[0]
        except Exception as e:
            audit_counts[t] = f"ERROR: {e}"
        print(f"    - Table '{t}': {audit_counts[t]} rows")

    # 인덱스 목록
    c.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_autoindex%'")
    indexes = c.fetchall()
    print(f"\n[*] 4. Active Indexes ({len(indexes)} total):")
    for idx_name, tbl in indexes[:10]:
        print(f"    - {idx_name} on {tbl}")

    print("\n[*] 5. Testing Full Database Restore from Backup...")
    if RESTORE_TEST_PATH.exists():
        RESTORE_TEST_PATH.unlink()
    
    # 백업본에서 복원 테스트
    b_conn = sqlite3.connect(ONLINE_BACKUP_PATH)
    r_conn = sqlite3.connect(RESTORE_TEST_PATH)
    with r_conn:
        b_conn.backup(r_conn, pages=100)
    b_conn.close()
    
    rc = r_conn.cursor()
    rc.execute("PRAGMA integrity_check")
    restore_integrity = rc.fetchall()
    rc.execute("SELECT COUNT(*) FROM vehicles")
    restore_v_cnt = rc.fetchone()[0]
    r_conn.close()
    RESTORE_TEST_PATH.unlink()

    print(f"    Restore integrity: {restore_integrity}")
    print(f"    Restore vehicle count matches source: {restore_v_cnt == audit_counts['vehicles']} ({restore_v_cnt} rows)")

    src_conn.close()

    assert integrity_res == [("ok",)], "DB Integrity must be 'ok'"
    assert fk_res == [], "Foreign Key violations must be empty"
    assert restore_integrity == [("ok",)], "Restored DB Integrity must be 'ok'"

    print("\n================================================================================")
    print("[+] TASK 1-① Database Integrity & Online Backup Audit: 100% PASS")
    print("================================================================================")
    return {
        "backup_path": str(ONLINE_BACKUP_PATH),
        "integrity": integrity_res,
        "foreign_keys": fk_res,
        "counts": audit_counts,
        "indexes_count": len(indexes)
    }

if __name__ == "__main__":
    run_integrity_audit()
