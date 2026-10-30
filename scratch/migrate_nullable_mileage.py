import sqlite3
from pathlib import Path

DB_PATH = Path("data/chamart/chamart_platform_demo.db")

def migrate_mileage():
    print("[*] Migrating vehicles.mileage to NULLABLE INTEGER...")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='vehicles'")
    vehicles_sql = c.fetchone()[0]

    # mileage INTEGER NOT NULL -> mileage INTEGER
    assert "mileage INTEGER NOT NULL" in vehicles_sql, "Must contain mileage INTEGER NOT NULL"
    new_sql = vehicles_sql.replace("mileage INTEGER NOT NULL", "mileage INTEGER")
    new_sql = new_sql.replace('CREATE TABLE "vehicles"', 'CREATE TABLE "vehicles_new"').replace("CREATE TABLE vehicles", "CREATE TABLE vehicles_new")

    c.execute(new_sql)
    c.execute("INSERT INTO vehicles_new SELECT * FROM vehicles")
    c.execute("DROP TABLE vehicles")
    c.execute("ALTER TABLE vehicles_new RENAME TO vehicles")

    conn.commit()

    c.execute("PRAGMA table_info(vehicles)")
    for col in c.fetchall():
        if col[1] == 'mileage':
            print(f"[+] vehicles.mileage schema: notnull={col[3]} (0=Nullable)")

    c.execute("PRAGMA integrity_check")
    assert c.fetchone() == ("ok",)
    c.execute("PRAGMA foreign_key_check")
    assert c.fetchall() == []
    print("[+] Mileage migration successfully completed and integrity verified!")
    conn.close()

if __name__ == "__main__":
    migrate_mileage()
