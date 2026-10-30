import sqlite3
import uuid
import json
import pytest
from datetime import datetime
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService

def setup_test_db(db_path: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id VARCHAR(36) PRIMARY KEY,
            branch_id VARCHAR(36) NOT NULL,
            plate_number VARCHAR(20) NOT NULL,
            model_name VARCHAR(100) NOT NULL,
            year INTEGER,
            mileage INTEGER NOT NULL,
            fuel_type VARCHAR(20),
            transmission VARCHAR(20),
            color VARCHAR(30),
            purchase_price INTEGER NOT NULL,
            target_price INTEGER,
            status VARCHAR(20) NOT NULL,
            is_demo BOOLEAN NOT NULL DEFAULT 0,
            timeline_json TEXT,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            ownership_type VARCHAR(20) NOT NULL,
            vin VARCHAR(50),
            manufacturer VARCHAR(50),
            trim VARCHAR(100),
            options_json TEXT,
            condition_detail_json TEXT,
            publishing_status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
            is_public BOOLEAN NOT NULL DEFAULT 0,
            listing_ownership_type VARCHAR(30) NOT NULL DEFAULT 'MARKET_JANGHANPYEONG'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_listings (
            id VARCHAR(36) PRIMARY KEY,
            vehicle_id VARCHAR(36) NOT NULL,
            platform VARCHAR(20) NOT NULL,
            listing_id VARCHAR(50) NOT NULL,
            listing_url VARCHAR(255),
            advertised_price INTEGER,
            listing_status VARCHAR(20) NOT NULL,
            first_observed_at DATETIME NOT NULL,
            last_observed_at DATETIME NOT NULL,
            region VARCHAR(50),
            is_janghanpyeong BOOLEAN NOT NULL DEFAULT 1,
            raw_seller_name VARCHAR(100),
            observation_notes TEXT,
            is_demo BOOLEAN NOT NULL DEFAULT 0,
            unverified_consecutive_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def test_price_transitions():
    test_db = "scratch/test_directive_112_sync.db"
    setup_test_db(test_db)
    service = CarManagerSyncService(db_path=test_db, dry_run=False)

    encarno = "TEST_TRANSITION_CAR_001"
    
    # 1. 최초 등록: 가격 미공개(상담) 매물 -> target_price = None (NULL)
    snap1 = [{
        "encarno": encarno,
        "model": "제네시스 G80 3.5T",
        "price_manwon": "상담",
        "model_year": "2023",
        "mileage": "2.5만km",
        "shop": "테스트상사"
    }]
    res1 = service.run_sync(snap1, scope="MARKET_OBSERVED")
    assert res1["new_inserted"] == 1

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("SELECT target_price FROM vehicles WHERE plate_number = 'UNVERIFIED'")
    assert c.fetchone()[0] is None, "상담 매물은 target_price가 NULL이어야 함"
    c.execute("SELECT advertised_price FROM vehicle_listings WHERE listing_id = ?", (encarno,))
    assert c.fetchone()[0] is None, "상담 매물은 advertised_price가 NULL이어야 함"
    conn.close()
    print("[PASS] 1. 최초 등록 시 상담 매물 NULL 저장 확인 완료")

    # 2. 가격 전환: 상담 -> 확정 가격 (예: 5200만원)
    snap2 = [{
        "encarno": encarno,
        "model": "제네시스 G80 3.5T",
        "price_manwon": "5200",
        "model_year": "2023",
        "mileage": "2.5만km",
        "shop": "테스트상사"
    }]
    res2 = service.run_sync(snap2, scope="MARKET_OBSERVED")
    assert res2["price_changed"] == 1, "상담 -> 확정가격 전환은 price_changed=1이어야 함"

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("SELECT target_price FROM vehicles")
    assert c.fetchone()[0] == 5200, "전환된 확정가격 5200이 저장되어야 함"
    c.execute("SELECT advertised_price FROM vehicle_listings WHERE listing_id = ?", (encarno,))
    assert c.fetchone()[0] == 5200, "전환된 확정가격 5200이 저장되어야 함"
    conn.close()
    print("[PASS] 2. 상담 -> 확정 가격 전환 감지 및 5200만원 정상 반영 완료")

    # 3. 가격 전환: 확정 가격 (5200만) -> 다시 상담('상담') 전환
    snap3 = [{
        "encarno": encarno,
        "model": "제네시스 G80 3.5T",
        "price_manwon": "상담",
        "model_year": "2023",
        "mileage": "2.5만km",
        "shop": "테스트상사"
    }]
    res3 = service.run_sync(snap3, scope="MARKET_OBSERVED")
    assert res3["price_changed"] == 1, "확정가격 -> 상담 전환은 price_changed=1이어야 함"

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("SELECT target_price FROM vehicles")
    assert c.fetchone()[0] is None, "상담으로 전환 시 target_price가 NULL이어야 함"
    c.execute("SELECT advertised_price FROM vehicle_listings WHERE listing_id = ?", (encarno,))
    assert c.fetchone()[0] is None, "상담으로 전환 시 advertised_price가 NULL이어야 함"
    conn.close()
    print("[PASS] 3. 확정 가격 -> 상담 전환 감지 및 NULL 안전 정정 완료")

    # 4. 관리자 가격 잠금 차량 보호 테스트
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("UPDATE vehicles SET target_price = 6000, condition_detail_json = '{\"is_price_locked\": true}'")
    conn.commit()
    conn.close()

    snap4 = [{
        "encarno": encarno,
        "model": "제네시스 G80 3.5T",
        "price_manwon": "4800",
        "model_year": "2023",
        "mileage": "2.5만km",
        "shop": "테스트상사"
    }]
    res4 = service.run_sync(snap4, scope="MARKET_OBSERVED")
    # 관리자 가격 잠금 시에는 target_price가 변경되지 않고 보존됨
    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("SELECT target_price FROM vehicles")
    assert c.fetchone()[0] == 6000, "관리자 가격 잠금 차량은 가격이 6000으로 보존되어야 함"
    conn.close()
    print("[PASS] 4. 관리자 설정 가격 잠금(is_price_locked) 보호 검증 완료")

if __name__ == "__main__":
    test_price_transitions()
    print("\n[ALL 4 TESTS PASSED 100%]")
