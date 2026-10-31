# -*- coding: utf-8 -*-
"""
CHA-FICIAL DIRECTIVE 137 Comprehensive E2E Verification Test:
- TASK 1: CarManager Janghanpyeong full market collection (1,764 vehicles, 49 shops)
- TASK 2: Chaficial AI full market analytics pool (1,801 vehicles in local DB)
- TASK 3: Strict demarcation of verified partner pool (74 cars) vs market observed pool (1,690 cars)
- TASK 4: Real-time session binding, D1 incremental sync, 1:1 remote record matching, skip-on-no-changes
- TASK 5: Zero customer exposure isolation (0 cars public) and gate protection
"""

import os
import sys
import json
import sqlite3
import subprocess
import logging
import urllib.request
import urllib.parse
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chaficial.platform.sourcing.continuous_sync_daemon import ContinuousSyncDaemon

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("test_directive_137_market_sync")

D1_DATABASE = "chamart-db"
REMOTE_PROD_URL = "https://chamart.cc"
LANDROVER_PLATE = "64노3143"
LOCAL_DB_PATH = "data/chamart/chamart_platform_demo.db"

def query_remote_d1(sql: str):
    cmd = [
        "npx", "wrangler", "d1", "execute", D1_DATABASE,
        "--remote", "--json",
        "--command", sql
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"wrangler d1 query failed: {p.stderr}")
    data = json.loads(p.stdout)
    return data[0]["results"]

def run_directive_137_verification():
    logger.info("=" * 70)
    logger.info("Executing CHA-FICIAL DIRECTIVE 137 Comprehensive Verification")
    logger.info("=" * 70)

    admin_token = os.environ.get("CHAMART_ADMIN_TOKEN")
    if not admin_token:
        secret_file = Path("data/.chamart_admin_secret")
        if secret_file.exists():
            admin_token = secret_file.read_text(encoding="utf-8").strip()
            os.environ["CHAMART_ADMIN_TOKEN"] = admin_token

    assert admin_token and len(admin_token) >= 32, "CHAMART_ADMIN_TOKEN must be set with 256-bit entropy"

    daemon = ContinuousSyncDaemon()

    # -------------------------------------------------------------
    # Step 1: 카매니저 장한평 전체 시장 수집 검증 (TASK 1)
    # -------------------------------------------------------------
    market_pool, market_stats = daemon.fetch_janghanpyeong_market_pool()
    total_collected = market_stats["total_collected"]
    unique_encarno = market_stats["unique_encarno_count"]
    distinct_shops = market_stats["distinct_dealerships"]

    logger.info(f"Step 1 Market Audit: total={total_collected}, unique_encarno={unique_encarno}, shops={distinct_shops}")
    assert total_collected == 1764, f"Expected 1,764 total collected vehicles, got {total_collected}"
    assert unique_encarno == 1764, f"Expected 1,764 unique encarno records, got {unique_encarno}"
    assert distinct_shops == 49, f"Expected 49 distinct dealerships, got {distinct_shops}"
    logger.info("  [PASS] Step 1: 카매니저 장한평 전체 시장 수집 (1,764대, 49개 상사 전수) 검증 완료")

    # -------------------------------------------------------------
    # Step 2: 차피셜 AI 전체 시장 분석 DB 정합성 검증 (TASK 2)
    # -------------------------------------------------------------
    assert Path(LOCAL_DB_PATH).exists(), f"Local DB {LOCAL_DB_PATH} not found"
    conn = sqlite3.connect(LOCAL_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count(*) FROM vehicles")
    db_total = c.fetchone()[0]

    c.execute("SELECT listing_ownership_type, count(*) FROM vehicles GROUP BY listing_ownership_type")
    ownership_breakdown = dict(c.fetchall())
    conn.close()

    logger.info(f"Step 2 Chaficial DB Audit: total={db_total}, breakdown={ownership_breakdown}")
    assert db_total == 1801, f"Expected 1,801 total vehicles in Chaficial DB, got {db_total}"
    assert ownership_breakdown.get("MARKET_JANGHANPYEONG") == 1770, "Expected 1,770 market observed vehicles"
    assert ownership_breakdown.get("OWNED") == 31, "Expected 31 owned/direct vehicles"
    logger.info("  [PASS] Step 2: 차피셜 AI 분석 DB (총 1,801대: 장한평 관측 1,770대 + 직영 31대) 정합성 확인 완료")

    # -------------------------------------------------------------
    # Step 3: 광고 권한 확인 매물 vs 시장 관측 매물 분리 검증 (TASK 3)
    # -------------------------------------------------------------
    authorized_partner_vehicles = market_stats["authorized_partner_vehicles"]
    market_observed_vehicles = market_stats["market_observed_vehicles"]

    logger.info(f"Step 3 Authorization Split: partner={authorized_partner_vehicles}, observed={market_observed_vehicles}")
    assert authorized_partner_vehicles == 74, f"Expected 74 partner vehicles for TheCool Motors, got {authorized_partner_vehicles}"
    assert market_observed_vehicles == 1690, f"Expected 1,690 market observed vehicles, got {market_observed_vehicles}"
    assert authorized_partner_vehicles + market_observed_vehicles == total_collected
    logger.info("  [PASS] Step 3: 광고 권한 확보 매물(더쿨모터스 74대) vs 시장 관측 매물(1,690대) 100% 엄격 분리 확인")

    # -------------------------------------------------------------
    # Step 4: 카매니저 실시간 세션 연동 및 차마트 판매 풀 동기화 검증 (TASK 4)
    # -------------------------------------------------------------
    sync_inventory, sync_meta = daemon.fetch_live_source_data()
    assert len(sync_inventory) == 74, f"Expected 74 vehicles in sync inventory, got {len(sync_inventory)}"

    landrover = next((x for x in sync_inventory if x.get("plate_number") == LANDROVER_PLATE), None)
    assert landrover is not None, f"Landrover {LANDROVER_PLATE} must exist in sync inventory"
    assert landrover["target_price"] == 1090, f"Expected 1090 manwon, got {landrover['target_price']}"
    assert landrover["mileage"] == 125428, f"Expected 125428 km, got {landrover['mileage']}"
    assert landrover["is_demo"] == 0
    assert landrover["is_live_verified"] is True
    logger.info("  [PASS] Step 4: 카매니저 실시간 세션 연동 및 64노3143 정밀 제원 바인딩 확인")

    # -------------------------------------------------------------
    # Step 5: 실제 D1 전송 및 원격 D1 재조회 1:1 값 일치 검증 (TASK 4)
    # -------------------------------------------------------------
    res_sync = daemon.inspect_and_sync_incremental(dry_run=False)
    assert res_sync["status"] == "SUCCESS"
    logger.info(f"  [PASS] Step 5: D1 증분 동기화 완료: {res_sync}")

    # 원격 D1 재조회
    d1_records = query_remote_d1(f"SELECT target_price, mileage, is_public, publishing_status, listing_ownership_type FROM vehicles WHERE plate_number = '{LANDROVER_PLATE}' LIMIT 1")
    assert len(d1_records) == 1, "Vehicle not found in remote D1"
    r = d1_records[0]
    assert r["target_price"] == 1090
    assert r["mileage"] == 125428
    assert r["is_public"] == 0, "실매물 1호는 사용자 최종 승인 전 비공개(is_public=0)여야 합니다."
    assert r["publishing_status"] == "PENDING_REVIEW"
    logger.info("  [PASS] Step 5: 원격 D1 재조회 1:1 일치 확인 (가격=1090, 주행거리=125428, is_public=0, PENDING_REVIEW)")

    # -------------------------------------------------------------
    # Step 6: 2회차 무변동 실행 시 D1 전송 완벽 생략 검증 (TASK 4)
    # -------------------------------------------------------------
    res_skip = daemon.inspect_and_sync_incremental(dry_run=False)
    assert res_skip["sync_result"] == "SKIPPED_NO_CHANGES"
    assert res_skip["changed_count"] == 0
    logger.info("  [PASS] Step 6: 2회차 무변동 실행 시 D1 전송 완벽 생략 (SKIPPED_NO_CHANGES)")

    # -------------------------------------------------------------
    # Step 7: 관리자 API 정상 조회 및 고객용 공개 API 0대 격리 확인 (TASK 5)
    # -------------------------------------------------------------
    # 관리자 API 조회
    encoded_plate = urllib.parse.quote(LANDROVER_PLATE)
    admin_url = f"{REMOTE_PROD_URL}/api/admin/vehicles/{encoded_plate}"
    req = urllib.request.Request(admin_url, headers={
        "User-Agent": "Directive137Verifier/1.0",
        "Authorization": f"Bearer {admin_token}"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        admin_car = json.loads(resp.read().decode('utf-8'))
    assert admin_car["_source"] == "CLOUDFLARE_D1_REAL_RECORD"
    assert admin_car["plate_number"] == LANDROVER_PLATE
    assert admin_car["target_price"] == 1090
    assert admin_car["mileage"] == 125428
    assert admin_car["photo_count"] == 9
    assert admin_car["is_public"] == 0
    logger.info("  [PASS] Step 7: 관리자 API 실제 D1 원격 레코드 정상 조회 (사진 9장, 125,428km, 1,090만원)")

    # 고객용 공개 API 0대 격리 확인
    pub_url = f"{REMOTE_PROD_URL}/api/chamart/vehicles"
    pub_req = urllib.request.Request(pub_url, headers={"User-Agent": "Directive137Verifier/1.0"})
    with urllib.request.urlopen(pub_req, timeout=10) as resp:
        assert resp.status == 200
        pub_cars = json.loads(resp.read().decode('utf-8'))
    assert len(pub_cars) == 0, f"Public vehicle list must be 0, got {len(pub_cars)}"
    logger.info("  [PASS] Step 7: 고객용 공개 API(chamart.cc) 0대 완전 격리 유지 확인 (임의 공개 원천 차단)")

    logger.info("=" * 70)
    logger.info("ALL 7 DIRECTIVE 137 COMPREHENSIVE VERIFICATION STEPS PASSED (100% PASS)")
    logger.info("=" * 70)

if __name__ == "__main__":
    run_directive_137_verification()
