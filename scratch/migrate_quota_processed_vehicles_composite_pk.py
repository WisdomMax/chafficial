"""
TASK 4: 운영 DB SQLite 예산기 스키마 마이그레이션
- quota_processed_vehicles의 단일 PK(vehicle_id)를 복합 PK(processed_date, vehicle_id)로 안전 마이그레이션
- 다음 날 재관측 허용 및 당일 동일 차량 중복 차감 방지 보장
- 마이그레이션 후 무결성 검사(PRAGMA integrity_check) 및 동시성 검증
"""

import sqlite3
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from chaficial.platform.sourcing.atomic_budget_enforcer import SqliteAtomicBudgetEnforcer

DB_PATH = "data/chamart/chamart_platform_demo.db"

def migrate_schema():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    print("=== [TASK 4] quota_processed_vehicles 복합키 마이그레이션 시작 ===")
    
    # 1. 현재 스키마 확인
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='quota_processed_vehicles'")
    curr_sql = c.fetchone()[0]
    print(f"현재 스키마: {curr_sql}")

    # 2. 원자적 테이블 교체
    with conn:
        c.execute("""
            CREATE TABLE quota_processed_vehicles_new (
                processed_date VARCHAR(10) NOT NULL,
                vehicle_id VARCHAR(36) NOT NULL,
                processed_at DATETIME NOT NULL,
                PRIMARY KEY (processed_date, vehicle_id)
            );
        """)
        c.execute("""
            INSERT OR IGNORE INTO quota_processed_vehicles_new (processed_date, vehicle_id, processed_at)
            SELECT processed_date, vehicle_id, processed_at FROM quota_processed_vehicles;
        """)
        c.execute("DROP TABLE quota_processed_vehicles;")
        c.execute("ALTER TABLE quota_processed_vehicles_new RENAME TO quota_processed_vehicles;")
    
    # 3. 무결성 확인
    c.execute("PRAGMA integrity_check;")
    chk = c.fetchall()
    print(f"PRAGMA integrity_check: {chk}")
    assert chk == [('ok',)]

    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='quota_processed_vehicles'")
    new_sql = c.fetchone()[0]
    print(f"새 스키마: {new_sql}")
    assert "PRIMARY KEY (processed_date, vehicle_id)" in new_sql

    conn.close()
    print("[+] 마이그레이션 성공!")

def verify_concurrent_same_vehicle():
    print("=== [TASK 4] 동일 차량 20회 동시 처리 시 1회만 예산 차감 검증 ===")
    enforcer = SqliteAtomicBudgetEnforcer(DB_PATH, daily_car_limit=200)
    
    # 오늘 날짜 시작 시점 카운트 확인
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = enforcer._get_or_init_today(conn)
    c.execute("SELECT cars_processed FROM quota_ledger WHERE ledger_date = ?", (today,))
    initial_cars = c.fetchone()[0]
    conn.close()

    target_vehicle_id = "test_concurrent_deduct_v01"

    def attempt_deduct(thread_id):
        try:
            enforcer.check_and_deduct_car(target_vehicle_id)
            return True
        except Exception as e:
            return False

    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(attempt_deduct, range(20)))

    # 확인: 첫 번째만 예산 차감되고, 나머지 19회는 동일 차량이므로 예산 차감 없이 pass 처리되어야 함!
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT cars_processed FROM quota_ledger WHERE ledger_date = ?", (today,))
    final_cars = c.fetchone()[0]
    c.execute("SELECT count(*) FROM quota_processed_vehicles WHERE processed_date = ? AND vehicle_id = ?", (today, target_vehicle_id))
    processed_count = c.fetchone()[0]

    # 테스트 데이터 정리
    c.execute("DELETE FROM quota_processed_vehicles WHERE vehicle_id = ?", (target_vehicle_id,))
    c.execute("UPDATE quota_ledger SET cars_processed = ? WHERE ledger_date = ?", (initial_cars, today))
    conn.commit()
    conn.close()

    print(f"Initial: {initial_cars}, Final: {final_cars}, Delta: {final_cars - initial_cars}, Processed rows: {processed_count}")
    assert final_cars - initial_cars == 1, "동일 차량 20회 시도 중 예산은 정확히 1회만 차감되어야 함!"
    assert processed_count == 1, "quota_processed_vehicles에는 정확히 1건만 기록되어야 함!"
    print("[+] TASK 4 동시성 및 중복 방지 검증 100% 통과!")

if __name__ == "__main__":
    migrate_schema()
    verify_concurrent_same_vehicle()
