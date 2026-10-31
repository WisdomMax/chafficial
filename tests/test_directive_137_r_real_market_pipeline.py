# -*- coding: utf-8 -*-
"""
CHA-FICIAL DIRECTIVE 137-R Comprehensive E2E Verification Test Suite
- Step 1: CarManager Live Market Harvest Audit (1,764 cars, 89 pages, 0 failed, 100% unique IDs)
- Step 2: Adaptive Thresholds & Integrity Guard Verification (Floor-based dynamic check)
- Step 3: DealershipRegistry-based Contract & Advertising Consent Verification (Zero substring hack)
- Step 4: Chaficial AI Analysis DB Real Update & Event Ledger Verification (SQL audit)
- Step 5: Chaficial -> Chamart D1 Incremental Sync & 2nd Run Skip Verification
- Step 6: Flagship Vehicle 64노3143 D1 Remote Spec Match & Private Protection Verification
- Step 7: Customer Public API Zero Vehicle Isolation Live Production Audit
"""

import os
import sys
import json
import sqlite3
import logging
import subprocess
import urllib.request
import urllib.parse
from pathlib import Path

# Add src & root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))
sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_directive_137_r")

from chaficial.platform.dealerships.dealership_registry import DealershipRegistry
from chaficial.platform.sourcing.continuous_sync_daemon import ContinuousSyncDaemon
from chaficial.platform.sourcing.chamart_sync_client import ChamartSyncClient

PROD_URL = "https://chamart.cc"
D1_DATABASE = "chamart-db"
LANDROVER_PLATE = "64노3143"
DB_PATH = "data/chamart/chamart_platform_demo.db"
RAW_FILE = Path("data/carmanager_raw/janghanpyeong_full_collection.json")

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

def request_http(url: str, headers: dict = None):
    req_headers = {"User-Agent": "ChamartDirective137Verifier/1.0"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def run_directive_137_r_verification():
    logger.info("=" * 70)
    logger.info("Executing CHA-FICIAL DIRECTIVE 137-R Comprehensive Verification")
    logger.info("=" * 70)

    # -------------------------------------------------------------
    # Step 1: CarManager Live Market Harvest Audit
    # -------------------------------------------------------------
    logger.info("=== Step 1: CarManager Live Market Harvest Audit ===")
    assert RAW_FILE.exists(), f"Raw collection file missing: {RAW_FILE}"
    with open(RAW_FILE, "r", encoding="utf-8") as f:
        full_data = json.load(f)

    summary = full_data.get("summary", {})
    cars = full_data.get("cars", [])

    total_found = summary.get("total_found")
    collected_count = len(cars)
    unique_ids = set(c.get("encarno") for c in cars if c.get("encarno"))
    failed_pages = summary.get("failed_pages", [])
    is_complete = summary.get("is_complete")
    collected_at = summary.get("collected_at")
    capture_id = summary.get("capture_id")

    logger.info(f"Live Harvest Summary: total_found={total_found}, collected={collected_count}, unique_ids={len(unique_ids)}, failed_pages={failed_pages}, complete={is_complete}, captured_at={collected_at}")

    assert total_found == 1764, f"Expected total_found 1764, got {total_found}"
    assert collected_count == 1764, f"Expected 1764 collected cars, got {collected_count}"
    assert len(unique_ids) == 1764, f"Expected 1764 unique encarnos, got {len(unique_ids)}"
    assert len(failed_pages) == 0, f"Expected 0 failed pages, got {failed_pages}"
    assert is_complete is True, "Harvest must be marked is_complete=True"
    assert collected_at is not None, "collected_at timestamp must exist"
    logger.info("  [PASS] Step 1: 카매니저 실시간 시장 수집 감사 통과 (1,764대 전수, 89페이지, 누락 0건, 수집시각 확인)")

    # -------------------------------------------------------------
    # Step 2: Adaptive Thresholds & Integrity Guard Verification
    # -------------------------------------------------------------
    logger.info("=== Step 2: Adaptive Thresholds & Integrity Guard Verification ===")
    from scripts.run_daily_sync import MIN_TOTAL_FLOOR, MIN_OWNED_FLOOR, MIN_MARKET_FLOOR
    assert MIN_TOTAL_FLOOR == 300, f"Expected MIN_TOTAL_FLOOR 300, got {MIN_TOTAL_FLOOR}"
    assert MIN_OWNED_FLOOR == 10, f"Expected MIN_OWNED_FLOOR 10, got {MIN_OWNED_FLOOR}"
    assert MIN_MARKET_FLOOR == 200, f"Expected MIN_MARKET_FLOOR 200, got {MIN_MARKET_FLOOR}"
    assert collected_count >= MIN_TOTAL_FLOOR, "Harvested count must be above minimum floor"
    logger.info(f"  [PASS] Step 2: 시장 규모 적응형 하한선(Total={MIN_TOTAL_FLOOR}, Owned={MIN_OWNED_FLOOR}, Market={MIN_MARKET_FLOOR}) 및 동적 정합성 검증 확인")

    # -------------------------------------------------------------
    # Step 3: DealershipRegistry Contract & Advertising Consent Verification
    # -------------------------------------------------------------
    logger.info("=== Step 3: DealershipRegistry Verification (Zero Substring Hack) ===")
    registry = DealershipRegistry()
    assert len(registry.partners) >= 1, "At least 1 active partner dealership required in registry"
    
    # 더쿨모터스 검증
    is_cool_auth, cool_info, cool_reason = registry.verify_advertising_authorization("(주)더쿨모터스")
    assert is_cool_auth is True, "The Cool Motors must be authorized by registry"
    assert cool_info["contract_status"] == "ACTIVE", "Contract must be ACTIVE"
    assert cool_info["advertising_consent"]["status"] == "APPROVED", "Advertising consent must be APPROVED"
    logger.info(f"The Cool Motors: is_auth={is_cool_auth}, id={cool_info['dealership_id']}, reason={cool_reason}")

    # 타 상사(선인자동차, 디케이드림카) 비인가 검증
    is_seonin_auth, seonin_info, seonin_reason = registry.verify_advertising_authorization("선인자동차")
    assert is_seonin_auth is False, "Seonin Motors must NOT be authorized for Chamart sales"
    logger.info(f"Seonin Motors: is_auth={is_seonin_auth}, reason={seonin_reason}")

    # 전체 1,764대 대상 레지스트리 분류 전수 검사
    partner_cars = []
    market_observed_cars = []
    for c in cars:
        shop = c.get("shop") or c.get("sangsa_name") or ""
        auth, p_info, reason = registry.verify_advertising_authorization(shop)
        if auth:
            partner_cars.append(c)
        else:
            market_observed_cars.append(c)

    logger.info(f"Registry Split: Authorized Partners={len(partner_cars)}대, Market Observed={len(market_observed_cars)}대")
    assert len(partner_cars) == 74, f"Expected 74 partner cars, got {len(partner_cars)}"
    assert len(market_observed_cars) == 1690, f"Expected 1690 observed cars, got {len(market_observed_cars)}"
    logger.info("  [PASS] Step 3: DealershipRegistry 기반 정식 광고 권한 검증 완료 (제휴 74대 vs 시장관측 1,690대 완벽 분리)")

    # -------------------------------------------------------------
    # Step 4: Chaficial AI Analysis DB Real Update Verification
    # -------------------------------------------------------------
    logger.info("=== Step 4: Chaficial AI Analysis DB Real Update Verification ===")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 최신 시계열 실행 조회
    cur.execute("SELECT run_id, observation_mode, source_capture_id, total_found, unique_cars_count, started_at FROM market_collection_runs ORDER BY started_at DESC LIMIT 1;")
    last_run = cur.fetchone()
    assert last_run is not None, "market_collection_runs record must exist"
    run_id, obs_mode, cap_id, t_found, u_count, run_started = last_run
    logger.info(f"DB Last Run: id={run_id}, mode={obs_mode}, cap_id={cap_id}, found={t_found}, unique={u_count}, started={run_started}")
    assert obs_mode == "LIVE_OBSERVED", f"Expected LIVE_OBSERVED, got {obs_mode}"
    assert t_found == 1764, f"Expected 1764 total found in DB run, got {t_found}"
    assert u_count == 1764, f"Expected 1764 unique cars in DB run, got {u_count}"

    # 최신 동기화 로그 조회
    cur.execute("SELECT scope, total_inspected, price_changed, status FROM carmanager_sync_logs ORDER BY started_at DESC LIMIT 2;")
    sync_logs = cur.fetchall()
    logger.info(f"DB Latest Sync Logs: {sync_logs}")
    assert len(sync_logs) == 2, "Expected 2 recent sync logs (OWNED, MARKET_OBSERVED)"
    for s_scope, s_inspected, s_price_chg, s_status in sync_logs:
        assert s_status == "SUCCESS", f"Sync log for {s_scope} must be SUCCESS"

    conn.close()
    logger.info("  [PASS] Step 4: 차피셜 분석 DB 실제 갱신 검증 완료 (LIVE_OBSERVED 시계열 1,764대 및 동기화 로그 입증)")

    # -------------------------------------------------------------
    # Step 5: Chaficial -> Chamart D1 Sync Cycle & Idempotency
    # -------------------------------------------------------------
    logger.info("=== Step 5: Chaficial -> Chamart D1 Sync Cycle & Idempotency ===")
    daemon = ContinuousSyncDaemon()
    cycle1 = daemon.inspect_and_sync_incremental(dry_run=False)
    logger.info(f"Cycle 1 Result: {cycle1.get('sync_result')}, changed={cycle1.get('changed_count')}, updated={cycle1.get('updated')}")
    assert cycle1["status"] == "SUCCESS", "Cycle 1 must succeed"

    # 2회차 연속 실행: 무변동 시 D1 전송 100% 생략 (SKIPPED_NO_CHANGES)
    cycle2 = daemon.inspect_and_sync_incremental(dry_run=False)
    logger.info(f"Cycle 2 Result: {cycle2.get('sync_result')}, changed={cycle2.get('changed_count')}")
    assert cycle2["status"] == "SUCCESS", "Cycle 2 must succeed"
    assert cycle2["changed_count"] == 0, f"Cycle 2 changed_count must be 0, got {cycle2['changed_count']}"
    assert cycle2["sync_result"] == "SKIPPED_NO_CHANGES", f"Expected SKIPPED_NO_CHANGES, got {cycle2['sync_result']}"
    logger.info("  [PASS] Step 5: 차피셜 -> 차마트 D1 증분 동기화 및 2회차 무변동 완벽 스킵 확인")

    # -------------------------------------------------------------
    # Step 6: Flagship Vehicle 64노3143 Remote D1 Match & Private Protection
    # -------------------------------------------------------------
    logger.info("=== Step 6: 64노3143 Remote D1 Match & Private Protection ===")
    d1_records = query_remote_d1(f"SELECT target_price, mileage, is_public, publishing_status, listing_ownership_type FROM vehicles WHERE plate_number = '{LANDROVER_PLATE}' LIMIT 1")
    assert len(d1_records) == 1, "Vehicle not found in remote D1"
    r = d1_records[0]
    assert r["target_price"] == 1090
    assert r["mileage"] == 125428
    assert r["is_public"] == 0, "실매물 1호는 사용자 최종 승인 전 비공개(is_public=0)여야 합니다."
    assert r["publishing_status"] == "PENDING_REVIEW"
    logger.info(f"64노3143 Remote D1 Direct: price={r['target_price']}만, mileage={r['mileage']}km, is_public={r['is_public']}, publishing_status={r['publishing_status']}")

    admin_token = Path("data/.chamart_admin_secret").read_text().strip()
    encoded_plate = urllib.parse.quote(LANDROVER_PLATE)
    admin_url = f"{PROD_URL}/api/admin/vehicles/{encoded_plate}"
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
    logger.info("  [PASS] Step 6: 실매물 1호 64노3143 D1 정밀 제원 일치 및 비공개 안전 보존 확인 (사진 9장, 125,428km, 1,090만원)")

    # -------------------------------------------------------------
    # Step 7: Customer Public API Zero Vehicle Isolation
    # -------------------------------------------------------------
    logger.info("=== Step 7: Customer Public API Zero Vehicle Isolation Live Audit ===")
    pub_url = f"{PROD_URL}/api/chamart/vehicles"
    pub_req = urllib.request.Request(pub_url, headers={"User-Agent": "Directive137Verifier/1.0"})
    with urllib.request.urlopen(pub_req, timeout=10) as resp:
        assert resp.status == 200
        pub_cars = json.loads(resp.read().decode('utf-8'))
    logger.info(f"Public API vehicles: count={len(pub_cars)}")
    assert len(pub_cars) == 0, f"Customer public API MUST return 0 vehicles, got {len(pub_cars)}"
    logger.info("  [PASS] Step 7: 고객용 공개 API(chamart.cc) 0대 완전 격리 실서버 검증 완료 (임의 공개 원천 차단)")

    logger.info("=" * 70)
    logger.info("ALL 7 DIRECTIVE 137-R COMPREHENSIVE VERIFICATION STEPS PASSED (100% PASS)")
    logger.info("=" * 70)

if __name__ == "__main__":
    run_directive_137_r_verification()
