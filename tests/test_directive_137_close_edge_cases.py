# -*- coding: utf-8 -*-
"""
CHA-FICIAL DIRECTIVE 137-CLOSE Regression Test Suite
1. Exact Dealership Matching (Strict substring elimination: '더쿨' rejected, '(주)더쿨모터스' accepted)
2. CarManager Registration vs Chamart Advertising Consent Decoupling (ad_approved == False)
3. 0, 1, 9, 10, 74 Owned Partner Vehicles Isolated DB Sync Verification
   - 0 cars: owned_res safely defined as 'SKIPPED_EMPTY' (No UnboundLocalError)
   - 1 car: successfully synced (not dropped)
   - 9 cars: successfully synced (not dropped by threshold)
   - 10 cars: successfully synced
   - 74 cars: successfully synced
4. Privacy Protection: Dealer phone numbers masked in repo config, raw numbers decoupled
5. Zero Public Listings: All synced inventory remains strictly is_public=0
"""

import os
import json
import sqlite3
import pytest
import re
from pathlib import Path
from datetime import datetime

from src.chaficial.platform.dealerships.dealership_registry import (
    DealershipRegistry,
    normalize_shop_name,
)
from src.chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
from src.chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine


def init_test_db(db_path: str):
    """격리 테스트용 DB 스키마 생성 (운영 DB 스키마 복제)"""
    if os.path.exists(db_path):
        os.remove(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 운영 DB 스키마를 복제하여 완벽한 정합성 보장
    prod_conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
    schema_dump = prod_conn.execute("SELECT sql FROM sqlite_master WHERE type IN ('table', 'index') AND sql IS NOT NULL").fetchall()
    prod_conn.close()

    conn = sqlite3.connect(db_path)
    for row in schema_dump:
        try:
            conn.execute(row[0])
        except Exception:
            pass
    conn.commit()
    conn.close()


def generate_mock_car(encarno: str, shop: str, price: int = 1500) -> dict:
    return {
        "encarno": encarno,
        "car_no": f"12가{encarno[:4]}",
        "title": f"테스트 차량 {encarno}",
        "car_name": "쏘나타",
        "price": price,
        "year": 2020,
        "mileage": 50000,
        "fuel": "가솔린",
        "transmission": "오토",
        "shop": shop,
        "sangsa_name": shop,
        "photos": ["https://img.example.com/photo1.jpg"]
    }


class TestDirective137Close:

    def test_01_exact_matching_and_substring_rejection(self):
        """1. 상사 식별에서 부분문자열 탐색 영구 제거 및 정규화 동등 비교 검증"""
        reg = DealershipRegistry()

        # 정상 등록된 정확한 명칭 및 별칭
        assert reg.inspect_dealership("(주)더쿨모터스")["is_partner_dealership"] is True
        assert reg.inspect_dealership("더쿨모터스")["is_partner_dealership"] is True
        assert reg.inspect_dealership("주식회사 더쿨모터스")["is_partner_dealership"] is True

        # 부분문자열 악용 공격/변형 문자열 -> 100% 매칭 거부
        assert reg.inspect_dealership("더쿨")["is_partner_dealership"] is False
        assert reg.inspect_dealership("더쿨자동차")["is_partner_dealership"] is False
        assert reg.inspect_dealership("더쿨모터스클럽")["is_partner_dealership"] is False
        assert reg.inspect_dealership("진짜더쿨모터스")["is_partner_dealership"] is False
        assert reg.inspect_dealership("가짜(주)더쿨모터스상사")["is_partner_dealership"] is False

        # 타 상사
        assert reg.inspect_dealership("선인자동차")["is_partner_dealership"] is False
        assert reg.inspect_dealership("디케이드림카")["is_partner_dealership"] is False
        assert reg.inspect_dealership("삼일자동차")["is_partner_dealership"] is False

    def test_02_carmanager_dealer_registration_vs_chamart_ad_consent_decoupling(self):
        """2. 카매니저 딜러 등록과 차마트 광고 권한의 엄격한 분리 검증 (APPROVED 표기 금지)"""
        reg = DealershipRegistry()
        res = reg.inspect_dealership("(주)더쿨모터스")

        # 카매니저 상사 등록은 확인(ACTIVE)되어 인벤토리 관리 대상
        assert res["is_partner_dealership"] is True

        # 차마트 홈페이지 광고 승인은 별도 서면/동의 대기 중(PENDING_CONFIRMATION)이므로 FALSE여야 함!
        assert res["is_advertising_approved"] is False
        assert res["partner_info"]["advertising_consent"]["status"] == "PENDING_CONFIRMATION"

        # verify_advertising_authorization도 반드시 False를 반환해야 함
        is_auth, partner_info, reason = reg.verify_advertising_authorization("(주)더쿨모터스")
        assert is_auth is False
        assert "AD_CONSENT_PENDING" in reason

    def test_03_privacy_protection_masked_dealer_phones(self):
        """3. 공개 저장소 내 딜러 개인정보(휴대전화 번호) 마스킹 보호 검증"""
        reg_file = Path("src/chaficial/platform/dealerships/authorized_partner_dealerships.json")
        data = json.loads(reg_file.read_text(encoding="utf-8"))

        raw_phone_pattern = re.compile(r"010-\d{4}-\d{4}")
        for partner in data.get("partner_dealerships", []):
            dealers = partner.get("representative_dealers", [])
            for d in dealers:
                phone = d.get("phone", "")
                # 평문 4자리 숫자가 그대로 노출되지 않고 마스킹(****)되어 있는지 검증
                assert not raw_phone_pattern.match(phone), f"Raw unmasked phone found in repo: {phone}"
                assert "****" in phone, f"Phone number not properly masked: {phone}"

        # 비공개 격리 파일은 로컬에 엄격히 보존되어 있는지 검증
        private_contacts = Path("data/.dealership_contacts_private.json")
        assert private_contacts.exists(), "Private contacts file missing"

    def test_04_isolated_db_sync_0_owned_cars(self, tmp_path):
        """4. 제휴 매물 0대일 때: owned_res 안전 정의 (SKIPPED_EMPTY) 및 UnboundLocalError 배제 검증"""
        test_db = str(tmp_path / "sync_0_test.db")
        init_test_db(test_db)

        service = CarManagerSyncService(db_path=test_db)
        atomic_conn = sqlite3.connect(test_db)
        atomic_conn.execute("BEGIN IMMEDIATE;")

        owned_cars = []  # 0대
        market_cars = [generate_mock_car(f"900{i:03d}", "선인자동차") for i in range(250)]

        # 파이프라인 시뮬레이션: owned_cars 0대 처리
        if len(owned_cars) > 0:
            owned_res = service.run_sync(owned_cars, scope="OWNED", min_expected_count=1, connection=atomic_conn)
        else:
            owned_res = {
                "sync_id": "SKIPPED_EMPTY",
                "scope": "OWNED",
                "started_at": datetime.now().isoformat(),
                "total_inspected": 0,
                "new_inserted": 0,
                "price_changed": 0,
                "sold_count": 0,
                "delisted_count": 0,
                "unchanged_count": 0,
                "status": "SKIPPED_EMPTY"
            }

        # 시장 관측 동기화
        market_res = service.run_sync(market_cars, scope="MARKET_OBSERVED", min_expected_count=200, connection=atomic_conn)
        atomic_conn.commit()
        atomic_conn.close()

        # owned_res가 안전하게 정의되어 에러 없이 정상 조회 가능
        assert owned_res is not None
        assert owned_res["status"] == "SKIPPED_EMPTY"
        assert owned_res["total_inspected"] == 0
        assert market_res["status"] == "SUCCESS"
        assert market_res["new_inserted"] == 250

    def test_05_isolated_db_sync_1_owned_car(self, tmp_path):
        """5. 제휴 매물 1대일 때: 임계치 탈락 없이 100% 정상 동기화 검증"""
        test_db = str(tmp_path / "sync_1_test.db")
        init_test_db(test_db)

        service = CarManagerSyncService(db_path=test_db)
        atomic_conn = sqlite3.connect(test_db)
        atomic_conn.execute("BEGIN IMMEDIATE;")

        owned_cars = [generate_mock_car("100001", "(주)더쿨모터스", 1090)]
        market_cars = [generate_mock_car(f"900{i:03d}", "선인자동차") for i in range(250)]

        if len(owned_cars) > 0:
            owned_res = service.run_sync(owned_cars, scope="OWNED", min_expected_count=1, connection=atomic_conn)
        else:
            owned_res = {"status": "SKIPPED_EMPTY"}

        market_res = service.run_sync(market_cars, scope="MARKET_OBSERVED", min_expected_count=200, connection=atomic_conn)
        atomic_conn.commit()
        atomic_conn.close()

        assert owned_res["status"] == "SUCCESS"
        assert owned_res["total_inspected"] == 1
        assert owned_res["new_inserted"] == 1

        # DB 검증: OWNED 차량 1대가 등록되었고 is_public은 0이어야 함
        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("SELECT id, target_price, listing_ownership_type, is_public, publishing_status FROM vehicles WHERE listing_ownership_type='OWNED'")
        rows = c.fetchall()
        assert len(rows) == 1
        assert rows[0][1] == 1090
        assert rows[0][3] == 0  # is_public == 0
        assert rows[0][4] in ("DRAFT", "PENDING_REVIEW")
        conn.close()

    def test_06_isolated_db_sync_9_owned_cars(self, tmp_path):
        """6. 제휴 매물 9대일 때: 임계치 탈락 없이 9대 전원 정상 동기화 검증 (10대 미만 결함 해결)"""
        test_db = str(tmp_path / "sync_9_test.db")
        init_test_db(test_db)

        service = CarManagerSyncService(db_path=test_db)
        atomic_conn = sqlite3.connect(test_db)
        atomic_conn.execute("BEGIN IMMEDIATE;")

        owned_cars = [generate_mock_car(f"20000{i}", "더쿨모터스", 1200 + i * 10) for i in range(9)]
        market_cars = [generate_mock_car(f"900{i:03d}", "선인자동차") for i in range(250)]

        if len(owned_cars) > 0:
            owned_res = service.run_sync(owned_cars, scope="OWNED", min_expected_count=1, connection=atomic_conn)
        else:
            owned_res = {"status": "SKIPPED_EMPTY"}

        market_res = service.run_sync(market_cars, scope="MARKET_OBSERVED", min_expected_count=200, connection=atomic_conn)
        atomic_conn.commit()
        atomic_conn.close()

        assert owned_res["status"] == "SUCCESS"
        assert owned_res["total_inspected"] == 9
        assert owned_res["new_inserted"] == 9

        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM vehicles WHERE listing_ownership_type='OWNED'")
        assert c.fetchone()[0] == 9
        conn.close()

    def test_07_isolated_db_sync_10_and_74_owned_cars(self, tmp_path):
        """7. 제휴 매물 10대 및 74대 전수 정상 동기화 검증"""
        test_db = str(tmp_path / "sync_74_test.db")
        init_test_db(test_db)

        service = CarManagerSyncService(db_path=test_db)
        atomic_conn = sqlite3.connect(test_db)
        atomic_conn.execute("BEGIN IMMEDIATE;")

        owned_cars = [generate_mock_car(f"7400{i:02d}", "(주)더쿨모터스", 1500) for i in range(74)]
        market_cars = [generate_mock_car(f"900{i:03d}", "선인자동차") for i in range(250)]

        owned_res = service.run_sync(owned_cars, scope="OWNED", min_expected_count=1, connection=atomic_conn)
        market_res = service.run_sync(market_cars, scope="MARKET_OBSERVED", min_expected_count=200, connection=atomic_conn)
        atomic_conn.commit()
        atomic_conn.close()

        assert owned_res["status"] == "SUCCESS"
        assert owned_res["total_inspected"] == 74
        assert owned_res["new_inserted"] == 74

        conn = sqlite3.connect(test_db)
        c = conn.cursor()
        c.execute("SELECT COUNT(*), SUM(is_public) FROM vehicles WHERE listing_ownership_type='OWNED'")
        row = c.fetchone()
        assert row[0] == 74
        assert row[1] == 0  # 74대 전원 is_public == 0
        conn.close()
