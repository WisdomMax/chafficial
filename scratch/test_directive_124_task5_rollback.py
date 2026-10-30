"""
DIRECTIVE 124 TASK 5: 일일 운영 가드 중간 실패 시 부분 커밋 방지 및 원자적 롤백 검증 (ISSUE-86)
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
    # 초기 스키마 및 더미 차량 1건 생성
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

def test_atomic_rollback_on_intermediate_failure():
    setup_test_db()

    # 모의 차량 데이터
    mock_all_cars = [
        {"encarno": "enc_owned_new", "model": "자사 신규차량", "shop": "더쿨모터스", "price": "2000", "mileage": "3만km", "year": "2022"},
        {"encarno": "enc_market_new", "model": "시장 신규차량", "shop": "타사상사", "price": "1500", "mileage": "4만km", "year": "2021"}
    ]
    owned_cars = [mock_all_cars[0]]
    market_cars = [mock_all_cars[1]]

    ts_engine = MarketTimeSeriesEngine(db_path=TEST_DB)
    sync_service = CarManagerSyncService(db_path=TEST_DB)

    # 1. 단일 원자적 트랜잭션 개시
    atomic_conn = sqlite3.connect(TEST_DB)
    atomic_conn.execute("BEGIN IMMEDIATE;")
    rolled_back = False

    try:
        # 1-1. 시계열 기록 (4단계) - 성공
        ts_res = ts_engine.record_snapshot(mock_all_cars, connection=atomic_conn)
        assert ts_res["status"] == "SUCCESS"
        print("[+] Phase 4 (TimeSeries) executed in transaction")

        # 1-2. OWNED 자사 차량 동기화 (5단계) - 성공
        owned_res = sync_service.run_sync(current_snapshot=owned_cars, scope="OWNED", connection=atomic_conn)
        assert owned_res["status"] == "SUCCESS"
        print("[+] Phase 5 (Owned Sync) executed in transaction")

        # 1-3. MARKET 시장 동기화 (6단계) 도중 치명적 장애 발생 시뮬레이션!
        raise RuntimeError("Simulated network timeout or threshold failure in Phase 6 (Market Scope)")

        # 정상이라면 commit 수행
        atomic_conn.commit()

    except Exception as ex:
        print("[!] Exception caught, rolling back atomically:", ex)
        atomic_conn.rollback()
        rolled_back = True
    finally:
        atomic_conn.close()

    assert rolled_back is True, "트랜잭션이 롤백되지 않았습니다!"

    # 2. 롤백 후 DB 상태 전수 검사
    verify_conn = sqlite3.connect(TEST_DB)
    c = verify_conn.cursor()

    # 시계열 테이블 검사: 단 1건도 커밋되지 않았어야 함 (0건)
    c.execute("SELECT COUNT(*) FROM market_collection_runs")
    run_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM market_listing_observations")
    obs_count = c.fetchone()[0]

    # 차량 테이블 검사: 초기 1대만 존재해야 함 (신규 자사 차량 커밋 방지)
    c.execute("SELECT COUNT(*) FROM vehicles")
    veh_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM vehicle_listings")
    list_count = c.fetchone()[0]

    verify_conn.close()

    print(f"\n[Rollback Verification Audit]:")
    print(f"  - market_collection_runs count: {run_count} (기대값: 0)")
    print(f"  - market_listing_observations count: {obs_count} (기대값: 0)")
    print(f"  - vehicles count: {veh_count} (기대값: 1 - 초기 차량 유지)")
    print(f"  - vehicle_listings count: {list_count} (기대값: 1 - 초기 매물 유지)")

    assert run_count == 0, f"market_collection_runs에 잔류 데이터 존재: {run_count}"
    assert obs_count == 0, f"market_listing_observations에 잔류 데이터 존재: {obs_count}"
    assert veh_count == 1, f"vehicles에 중간 커밋된 신규 차량 존재: {veh_count}"
    assert list_count == 1, f"vehicle_listings에 중간 커밋된 리스팅 존재: {list_count}"

    print("\n[+] DIRECTIVE 124 TASK 5 (ISSUE-86) 단일 원자적 롤백 및 스테이징 무결성 100% PASS!")

if __name__ == "__main__":
    test_atomic_rollback_on_intermediate_failure()
