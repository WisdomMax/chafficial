"""
TASK 1 & 3 오프라인 통합 테스트: QuotaEnrichmentRunner + CrossPlatformMatcher
- 외부 네트워크 호출 없는 순수 오프라인 통합 테스트
- 예산 차감 원자성 및 초과 차단 검증
- VERIFIED -> ACTIVE, CANDIDATE -> REVIEW_PENDING 격리 검증
"""

import os
import sqlite3
import pytest
from pathlib import Path
from chaficial.platform.sourcing.quota_enrichment_runner import QuotaEnrichmentRunner, QuotaExhaustedException
from chaficial.platform.sourcing.cross_platform_matcher import CrossPlatformMatcher, ObservationMode, MatchingStatus

SANDBOX_DB = "scratch/test_enrichment_offline_sandbox.db"

def setup_sandbox_db():
    if os.path.exists(SANDBOX_DB):
        os.remove(SANDBOX_DB)
    
    conn = sqlite3.connect(SANDBOX_DB)
    c = conn.cursor()
    c.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE vehicles (
            id TEXT PRIMARY KEY,
            plate_number TEXT,
            model_name TEXT,
            model_year INTEGER,
            year INTEGER,
            mileage INTEGER,
            fuel_type TEXT,
            color TEXT,
            transmission TEXT,
            price INTEGER,
            advertised_price INTEGER,
            target_price INTEGER,
            purchase_price INTEGER DEFAULT 0,
            status TEXT DEFAULT 'AVAILABLE',
            publishing_status TEXT DEFAULT 'DRAFT',
            is_public INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            timeline_json TEXT DEFAULT '{}'
        );

        CREATE TABLE vehicle_listings (
            id TEXT PRIMARY KEY,
            vehicle_id TEXT NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
            platform TEXT NOT NULL,
            listing_id TEXT NOT NULL,
            listing_url TEXT,
            advertised_price INTEGER,
            listing_status TEXT DEFAULT 'ACTIVE',
            first_observed_at TEXT,
            last_observed_at TEXT,
            data_confidence REAL DEFAULT 1.0,
            observation_notes TEXT,
            is_demo INTEGER DEFAULT 0,
            source_confidence REAL DEFAULT 1.0
        );

        INSERT INTO vehicles (id, plate_number, model_name, year, mileage, fuel_type, color, created_at, updated_at)
        VALUES 
            ('car_01', '12가3456', '그랜저 HG240 모던', 2015, 85000, '가솔린', '검정', datetime('now'), datetime('now')),
            ('car_02', '34나5678', '아반떼 AD 1.6 스마트', 2018, 52000, '가솔린', '흰색', datetime('now'), datetime('now')),
            ('car_03', '56다7890', '쏘나타 DN8 2.0 프리미엄', 2020, 31000, '가솔린', '회색', datetime('now'), datetime('now'));
    """)
    conn.commit()
    conn.close()

def test_offline_integration():
    setup_sandbox_db()
    runner = QuotaEnrichmentRunner(db_path=SANDBOX_DB, daily_limit=2)

    # 1. Car 01: 완전 일치 KB 후보 -> VERIFIED -> DB listing_status='ACTIVE'
    v1 = {
        "id": "car_01",
        "plate_number": "12가3456",
        "model_name": "그랜저 HG240 모던",
        "year": 2015,
        "mileage": 85000,
        "fuel_type": "가솔린",
        "color": "검정"
    }
    kb_cand1 = {
        "car_id": "kb_car_01",
        "plate_number": "12가3456",
        "model_name": "현대 그랜저 HG240 모던",
        "year": 2015,
        "mileage": 85500,
        "fuel_type": "가솔린",
        "color": "검정색",
        "price": 1150,
        "url": "https://www.kbchachacha.com/car_01",
        "photos": ["https://img.kb.com/1.jpg"]
    }

    res1 = runner.process_vehicle_safe(v1, kb_candidate=kb_cand1, mode=ObservationMode.OFFLINE_TEST)
    assert res1 is not None
    assert res1.status == MatchingStatus.VERIFIED
    assert res1.match_score >= 0.85

    # 2. Car 02: 번호판 뒤 4자리만 일치 -> CANDIDATE -> DB listing_status='REVIEW_PENDING'
    v2 = {
        "id": "car_02",
        "plate_number": "34나5678",
        "model_name": "아반떼 AD 1.6 스마트",
        "year": 2018,
        "mileage": 52000,
        "fuel_type": "가솔린",
        "color": "흰색"
    }
    encar_cand2 = {
        "car_id": "encar_car_02",
        "plate_number": "5678", # 앞 번호 마스킹, 뒤 4자리 일치
        "model_name": "현대 아반떼 AD 1.6 가솔린 스마트",
        "year": 2018,
        "mileage": 52000,
        "fuel_type": "가솔린",
        "color": "흰색",
        "price": 1080,
        "url": "http://www.encar.com/car_02",
        "photos": ["http://img.encar.com/2.jpg"]
    }

    res2 = runner.process_vehicle_safe(v2, encar_candidate=encar_cand2, mode=ObservationMode.OFFLINE_TEST)
    assert res2 is not None
    assert res2.status == MatchingStatus.CANDIDATE

    # DB 격리 상태 검증
    conn = sqlite3.connect(SANDBOX_DB)
    c = conn.cursor()
    c.execute("SELECT vehicle_id, platform, listing_status, advertised_price FROM vehicle_listings ORDER BY vehicle_id")
    rows = c.fetchall()
    conn.close()

    print("[DB Rows]:", rows)
    assert len(rows) == 2
    assert rows[0] == ('car_01', 'KB_CHACHACHA', 'ACTIVE', 1150)
    assert rows[1] == ('car_02', 'ENCAR', 'REVIEW_PENDING', 1080)

    # 3. Car 03: 일일 차량 한도(2대) 초과 검증 -> QuotaExhaustedException 발생
    v3 = {
        "id": "car_03",
        "plate_number": "56다7890",
        "model_name": "쏘나타 DN8",
        "year": 2020,
        "mileage": 31000,
        "fuel_type": "가솔린",
        "color": "회색"
    }
    try:
        runner.process_vehicle_safe(v3, kb_candidate=kb_cand1)
        assert False, "Should have raised QuotaExhaustedException"
    except QuotaExhaustedException as e:
        print("[+] 예산 초과 정상 차단:", e)

    print("[+] TASK 1 & TASK 3 오프라인 통합 테스트 100% PASS!")

if __name__ == "__main__":
    test_offline_integration()
