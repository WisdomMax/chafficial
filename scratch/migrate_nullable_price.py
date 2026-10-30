import sqlite3
from pathlib import Path

def migrate_observations_table():
    print("================================================================================")
    print(" 마이그레이션: market_listing_observations.price_manwon NOT NULL 제거")
    print("================================================================================")

    db_path = "data/chamart/chamart_platform_demo.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. 기존 테이블 스키마 확인
    c.execute("PRAGMA table_info(market_listing_observations)")
    cols = c.fetchall()
    print("[*] Current columns:", [col[1] for col in cols])

    # 2. 임시 테이블 생성 (price_manwon INTEGER NULL 허용)
    c.execute("""
        CREATE TABLE market_listing_observations_new (
            id VARCHAR(36) PRIMARY KEY,
            run_id VARCHAR(36) NOT NULL,
            encarno VARCHAR(64) NOT NULL,
            observed_at DATETIME NOT NULL,
            raw_price_str VARCHAR(30),
            price_manwon INTEGER,
            mileage_km INTEGER,
            model_year INTEGER,
            model_name VARCHAR(100),
            fuel VARCHAR(30),
            mission VARCHAR(30),
            shop_name VARCHAR(50),
            region VARCHAR(50),
            listing_status VARCHAR(20) NOT NULL,
            photo_count INTEGER,
            raw_hash VARCHAR(64),
            FOREIGN KEY (run_id) REFERENCES market_collection_runs(run_id)
        )
    """)

    # 3. 기존 데이터 복사 (QUARANTINED 된 데이터 포함)
    c.execute("""
        INSERT INTO market_listing_observations_new 
        SELECT * FROM market_listing_observations
    """)
    copied_cnt = c.rowcount
    print(f"[+] Copied {copied_cnt} existing observation records to new table.")

    # 4. 기존 테이블 드롭 및 리네임
    c.execute("DROP TABLE market_listing_observations")
    c.execute("ALTER TABLE market_listing_observations_new RENAME TO market_listing_observations")

    # 5. 인덱스 재생성
    c.execute("CREATE INDEX IF NOT EXISTS idx_obs_encarno_date ON market_listing_observations(encarno, observed_at)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_obs_run_encarno ON market_listing_observations(run_id, encarno)")

    conn.commit()
    conn.close()
    print("[+] Migration completed successfully! price_manwon is now nullable.")

if __name__ == "__main__":
    migrate_observations_table()
