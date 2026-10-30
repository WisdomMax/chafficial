"""
DIRECTIVE 125 TASK 3: MARKET 함수 내부 실제 SQL 오류 주입 및 단일 트랜잭션 전체 롤백 무결성 검증 (ISSUE-89)
"""

import os
import sqlite3
import pytest
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine

TEST_DB = "scratch/test_atomic_rollback.db"

def setup_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    # 초기 스키마 및 초기 기준 차량 1건 생성
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE vehicles (
            id TEXT PRIMARY KEY,
            branch_id TEXT,
            plate_number TEXT,
            model_name TEXT,
            year TEXT,
            mileage INTEGER,
            fuel_type TEXT,
            transmission TEXT,
            color TEXT,
            purchase_price INTEGER,
            target_price INTEGER,
            status TEXT,
            is_demo INTEGER,
            timeline_json TEXT,
            created_at TEXT,
            updated_at TEXT,
            publishing_status TEXT,
            is_public INTEGER,
            listing_ownership_type TEXT,
            condition_detail_json TEXT
        );
    """)
    c.execute("""
        CREATE TABLE vehicle_listings (
            id TEXT PRIMARY KEY,
            vehicle_id TEXT,
            platform TEXT,
            listing_id TEXT,
            advertised_price INTEGER,
            listing_status TEXT,
            first_observed_at TEXT,
            last_observed_at TEXT,
            is_demo INTEGER,
            source_confidence REAL,
            unverified_consecutive_count INTEGER,
            raw_seller_name TEXT,
            raw_seller_location TEXT
        );
    """)
    c.execute("""
        INSERT INTO vehicles (id, branch_id, plate_number, model_name, year, mileage, status, is_public, target_price)
        VALUES ('base_veh_001', 'br_01', '11가1111', '초기차량', '2020', 50000, 'DRAFT', 0, 1000)
    """)
    c.execute("""
        INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, advertised_price, listing_status, is_demo)
        VALUES ('base_list_001', 'base_veh_001', 'CARMANAGER', 'enc_base_001', 1000, 'ACTIVE', 0)
    """)
    conn.commit()
    conn.close()

def test_market_internal_sql_error_atomic_rollback():
    setup_test_db()

    # 스키마 사전 확인 (BEGIN IMMEDIATE 락 충돌 방지 검증)
    ts_engine = MarketTimeSeriesEngine(db_path=TEST_DB)
    sync_service = CarManagerSyncService(db_path=TEST_DB)

    mock_all_cars = [
        {"encarno": "enc_owned_new", "model": "자사 신규차량", "shop": "더쿨모터스", "price": "2000", "mileage": "3만km", "year": "2022"},
        {"encarno": "enc_market_bad", "model": "시장 결함차량", "shop": "타사상사", "price": "1500", "mileage": "4만km", "year": "2021"}
    ]
    owned_cars = [mock_all_cars[0]]
    market_cars = [mock_all_cars[1]]

    atomic_conn = sqlite3.connect(TEST_DB)
    atomic_conn.execute("BEGIN IMMEDIATE;")
    rolled_back = False

    try:
        # 1. 4단계: 시계열 관측 기록 (정상 실행)
        ts_res = ts_engine.record_snapshot(mock_all_cars, connection=atomic_conn)
        assert ts_res["status"] == "SUCCESS"
        print("[+] Phase 4: TimeSeries executed successfully in transaction")

        # 2. 5단계: OWNED 자사 차량 동기화 (정상 실행 - DB 쓰기 발생)
        owned_res = sync_service.run_sync(current_snapshot=owned_cars, scope="OWNED", connection=atomic_conn)
        assert owned_res["status"] == "SUCCESS"
        assert owned_res["new_inserted"] == 1
        print("[+] Phase 5: Owned Sync executed successfully (1 car staged in transaction)")

        # 3. 6단계: MARKET 동기화 함수 내부에서 실제 SQL 장애 주입!
        # (예: 외래키/NOT NULL 제약 위반 또는 의도된 문법 오류를 sync_service에 주입)
        class FaultySyncService(CarManagerSyncService):
            def run_sync(self, *args, **kwargs):
                # 내부 cursor로 잘못된 쿼리를 직접 실행하여 sqlite3.OperationalError 발생
                conn = kwargs.get("connection")
                c = conn.cursor()
                c.execute("INSERT INTO non_existent_corrupted_table VALUES (1, 2, 3);")
                return super().run_sync(*args, **kwargs)

        faulty_market_service = FaultySyncService(db_path=TEST_DB)
        market_res = faulty_market_service.run_sync(
            current_snapshot=market_cars, 
            scope="MARKET_OBSERVED", 
            connection=atomic_conn
        )
        atomic_conn.commit()

    except Exception as ex:
        print("[!] Phase 6 내부 실제 SQL 에러 발생 확인:", ex)
        atomic_conn.rollback()
        rolled_back = True
    finally:
        atomic_conn.close()

    assert rolled_back is True, "트랜잭션이 롤백되지 않았습니다!"

    # 4. 롤백 후 DB 전수 검증: 4단계 시계열 및 5단계 OWNED 차량이 단 1건도 잔류하지 않고 100% 롤백되었는지 검증!
    verify_conn = sqlite3.connect(TEST_DB)
    c = verify_conn.cursor()

    c.execute("SELECT COUNT(*) FROM market_collection_runs")
    run_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM market_listing_observations")
    obs_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vehicles")
    veh_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vehicle_listings")
    list_count = c.fetchone()[0]

    verify_conn.close()

    print(f"\n[Post-Rollback Exhaustive Audit]:")
    print(f"  - market_collection_runs: {run_count} (기대값: 0 - 4단계 롤백 완료)")
    print(f"  - market_listing_observations: {obs_count} (기대값: 0 - 4단계 롤백 완료)")
    print(f"  - vehicles count: {veh_count} (기대값: 1 - 5단계 신규차량 롤백 완료, 초기차량만 보존)")
    print(f"  - vehicle_listings count: {list_count} (기대값: 1 - 5단계 신규매물 롤백 완료, 초기매물만 보존)")

    assert run_count == 0, "market_collection_runs가 롤백되지 않음!"
    assert obs_count == 0, "market_listing_observations가 롤백되지 않음!"
    assert veh_count == 1, "5단계에서 추가된 신규 차량이 롤백되지 않고 잔류함!"
    assert list_count == 1, "5단계에서 추가된 신규 리스팅이 롤백되지 않고 잔류함!"

    print("\n[+] DIRECTIVE 125 TASK 3 (ISSUE-89) MARKET 내부 실제 SQL 오류 시 전체 원자적 롤백 100% PASS!")

if __name__ == "__main__":
    test_market_internal_sql_error_atomic_rollback()
