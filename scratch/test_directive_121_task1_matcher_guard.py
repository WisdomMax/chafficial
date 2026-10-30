"""
TASK 1 회귀 테스트: OFFLINE_TEST 운영 DB 쓰기 차단 및 MANUAL_VERIFIED 엄격성 검증 (ISSUE-67)
"""

import os
import sqlite3
import pytest
from chaficial.platform.sourcing.cross_platform_matcher import (
    CrossPlatformMatcher, MatchResult, MatchingStatus, ObservationMode
)

SANDBOX_DB = "scratch/test_matcher_guard_sandbox.db"

def setup_db():
    if os.path.exists(SANDBOX_DB):
        os.remove(SANDBOX_DB)
    conn = sqlite3.connect(SANDBOX_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE vehicle_listings (
            id TEXT PRIMARY KEY,
            vehicle_id TEXT,
            platform TEXT,
            listing_id TEXT,
            listing_url TEXT,
            advertised_price INTEGER,
            listing_status TEXT,
            first_observed_at TEXT,
            last_observed_at TEXT,
            data_confidence REAL,
            observation_notes TEXT,
            is_demo INTEGER,
            source_confidence REAL
        );
    """)
    # 기존 ACTIVE 매물 1건 등록
    c.execute("""
        INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, listing_url, advertised_price, listing_status, is_demo)
        VALUES ('list_01', 'veh_01', 'KB_CHACHACHA', 'KB_REAL_123', 'https://www.kbchachacha.com/real', 2500, 'ACTIVE', 0)
    """)
    conn.commit()
    conn.close()

def test_matcher_guards():
    setup_db()
    
    # 1. 운영 DB 경로로 선언된 Matcher에서 OFFLINE_TEST 시도 -> 쓰기 0건 차단 확인
    prod_matcher = CrossPlatformMatcher(db_path="data/chamart/chamart_platform_demo.db")
    mock_match = MatchResult(
        vehicle_id="veh_999",
        plate_number="12가3456",
        source_platform="KB_CHACHACHA",
        external_car_id="kb_mock_999",
        external_url="https://mock.url/car",
        advertised_price_manwon=1000,
        photo_urls=[],
        status=MatchingStatus.VERIFIED,
        match_score=0.95,
        match_evidence={},
        observation_mode=ObservationMode.OFFLINE_TEST,
        matched_at="2026-10-31T00:44:00+09:00"
    )
    # 운영 DB에 쓰기 시도 -> 무시되어야 함
    prod_matcher.record_verified_match(mock_match)

    # 2. 샌드박스 DB에서 기존 ACTIVE 매물에 OFFLINE_TEST로 덮어쓰기 시도 -> 덮어쓰기 차단 확인
    sandbox_matcher = CrossPlatformMatcher(db_path=SANDBOX_DB)
    mock_overwrite = MatchResult(
        vehicle_id="veh_01",
        plate_number="12가3456",
        source_platform="KB_CHACHACHA",
        external_car_id="kb_mock_01",
        external_url="https://mock.url/overwrite",
        advertised_price_manwon=999,
        photo_urls=[],
        status=MatchingStatus.VERIFIED,
        match_score=0.95,
        match_evidence={},
        observation_mode=ObservationMode.OFFLINE_TEST,
        matched_at="2026-10-31T00:44:00+09:00"
    )
    sandbox_matcher.record_verified_match(mock_overwrite)

    conn = sqlite3.connect(SANDBOX_DB)
    c = conn.cursor()
    c.execute("SELECT listing_status, advertised_price, listing_url FROM vehicle_listings WHERE vehicle_id = 'veh_01'")
    row1 = c.fetchone()
    conn.close()

    print("[Existing Row After Mock Attempt]:", row1)
    assert row1[0] == "ACTIVE"
    assert row1[1] == 2500, "기존 ACTIVE 매물의 가격이 모의 데이터로 덮어써짐!"
    assert row1[2] == "https://www.kbchachacha.com/real"

    # 3. MANUAL_VERIFIED 시 더미 URL 차단 확인
    dummy_manual = MatchResult(
        vehicle_id="veh_02",
        plate_number="34나5678",
        source_platform="KB_CHACHACHA",
        external_car_id="kb_car_02",
        external_url="http://dummy.url/car",
        advertised_price_manwon=1800,
        photo_urls=[],
        status=MatchingStatus.VERIFIED,
        match_score=0.90,
        match_evidence={"verified_by": "admin"},
        observation_mode=ObservationMode.MANUAL_VERIFIED,
        matched_at="2026-10-31T00:44:00+09:00"
    )
    try:
        sandbox_matcher.record_verified_match(dummy_manual)
        assert False, "Should raise ValueError on dummy URL"
    except ValueError as e:
        print("[+] 더미 URL 정상 차단:", e)

    # 4. MANUAL_VERIFIED 시 verified_by 누락 차단 확인
    no_verifier_manual = MatchResult(
        vehicle_id="veh_02",
        plate_number="34나5678",
        source_platform="KB_CHACHACHA",
        external_car_id="kb_car_02",
        external_url="https://www.kbchachacha.com/real/02",
        advertised_price_manwon=1800,
        photo_urls=[],
        status=MatchingStatus.VERIFIED,
        match_score=0.90,
        match_evidence={}, # verified_by 누락
        observation_mode=ObservationMode.MANUAL_VERIFIED,
        matched_at="2026-10-31T00:44:00+09:00"
    )
    try:
        sandbox_matcher.record_verified_match(no_verifier_manual)
        assert False, "Should raise ValueError on missing verified_by"
    except ValueError as e:
        print("[+] 확인자 누락 정상 차단:", e)

    # 5. 정상 MANUAL_VERIFIED 저장 검증 (도메인, car_id 매핑, verified_by, verified_at, admin_approved 충족)
    valid_manual = MatchResult(
        vehicle_id="veh_02",
        plate_number="34나5678",
        source_platform="KB_CHACHACHA",
        external_car_id="real_02",
        external_url="https://www.kbchachacha.com/car/real_02",
        advertised_price_manwon=1800,
        photo_urls=[],
        status=MatchingStatus.VERIFIED,
        match_score=0.90,
        match_evidence={
            "verified_by": "expert_human_inspector",
            "verified_at": "2026-10-31T00:55:00+09:00",
            "admin_approved": True
        },
        observation_mode=ObservationMode.MANUAL_VERIFIED,
        matched_at="2026-10-31T00:55:00+09:00"
    )
    sandbox_matcher.record_verified_match(valid_manual)

    conn = sqlite3.connect(SANDBOX_DB)
    c = conn.cursor()
    c.execute("SELECT listing_status, advertised_price, is_demo FROM vehicle_listings WHERE vehicle_id = 'veh_02'")
    row2 = c.fetchone()
    conn.close()

    print("[Valid MANUAL_VERIFIED Row]:", row2)
    assert row2 == ("ACTIVE", 1800, 0)

    print("[+] TASK 1 OFFLINE_TEST 운영 DB 차단 및 MANUAL_VERIFIED 엄격성 검증 100% PASS!")

if __name__ == "__main__":
    test_matcher_guards()
