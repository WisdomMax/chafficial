#!/usr/bin/env python3
"""
DIRECTIVE 136 Comprehensive E2E Verification Test:
- Step 1: Strict launchd daemon registration check (FAIL if not registered)
- Step 2: CarManager Live Session Ingestion & Distinction (live_my_cars vs cached snapshot, 125,428km precision)
- Step 3: Real D1 Incremental Sync Execution (dry_run=False) & 74 vehicles updated
- Step 4: Remote D1 Query verification (assert 1:1 match of price, mileage, is_public=0, PENDING_REVIEW)
- Step 5: Second Execution yields exact zero-change skip (SKIPPED_NO_CHANGES)
- Step 6: Admin API real record verification (9 photos, 125,428km, 1,090 manwon, _source='CLOUDFLARE_D1_REAL_RECORD')
- Step 7: Public API zero-exposure verification (0 items returned)
"""

import sys
import json
import subprocess
import logging
import urllib.request
import urllib.parse
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chaficial.platform.sourcing.continuous_sync_daemon import ContinuousSyncDaemon

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("test_directive_136_e2e")

D1_DATABASE = "chamart-db"
REMOTE_PROD_URL = "https://chamart.cc"
SYNC_SECRET = "chamart-sync-secret-2026"
LANDROVER_PLATE = "64노3143"

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

def run_directive_136_e2e():
    logger.info("=" * 65)
    logger.info("Executing DIRECTIVE 136 Comprehensive Real E2E Verification")
    logger.info("=" * 65)

    # Step 1: launchd 등록 여부 엄격 검증 (TASK 3)
    p = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
    has_launchd_entry = "com.chaficial.sync" in p.stdout
    assert has_launchd_entry is True, "FAIL: Mac mini launchd 서비스 'com.chaficial.sync'가 등록되어 있지 않습니다."
    logger.info("  [PASS] Step 1: Mac mini launchd 서비스 엄격 등록 확인 (com.chaficial.sync: True)")

    daemon = ContinuousSyncDaemon()

    # Step 2: 실시간 세션 수집 및 인벤토리 분리 검증 (TASK 2)
    inventory, meta = daemon.fetch_live_source_data()
    assert len(inventory) == 74, f"Expected 74 vehicles, got {len(inventory)}"
    assert meta["is_live_session"] is True, "Live CarManager session must be successful"
    assert meta["live_verified_count"] >= 13, f"Expected >= 13 live verified, got {meta['live_verified_count']}"
    assert meta["cached_snapshot_count"] >= 60, f"Expected >= 60 cached, got {meta['cached_snapshot_count']}"

    # 64노3143 정밀 실측 제원 검증 (TASK 2 & TASK 4: 125,428km 원본 주행거리 반영)
    landrover = next((c for c in inventory if c.get("plate_number") == LANDROVER_PLATE), None)
    assert landrover is not None, f"Vehicle {LANDROVER_PLATE} not found in inventory"
    assert landrover["mileage"] == 125428, f"Expected 125428 km, got {landrover['mileage']}"
    assert landrover["target_price"] == 1090, f"Expected 1090 manwon, got {landrover['target_price']}"
    logger.info(f"  [PASS] Step 2: 실시간 세션 연동 및 64노3143 정밀 제원(125,428km, 1,090만원) 바인딩 확인")

    # Step 3: 실제 D1 전송 (dry_run=False, TASK 3)
    daemon.last_state = {"vehicle_hashes": {}, "last_run": None}
    res_sync = daemon.inspect_and_sync_incremental(dry_run=False)
    assert res_sync["sync_result"] == "SUCCESS", f"Sync failed: {res_sync}"
    assert res_sync["updated"] + res_sync["inserted"] == 74, f"Expected 74 updated/inserted, got {res_sync}"
    logger.info(f"  [PASS] Step 3: 실제 D1 전송 완료 (updated={res_sync['updated']}, inserted={res_sync['inserted']}, skipped={res_sync['skipped']})")

    # Step 4: 원격 D1 재조회 1:1 값 일치 검증 (TASK 3)
    d1_records = query_remote_d1(f"SELECT id, plate_number, target_price, mileage, is_public, publishing_status, status FROM vehicles WHERE plate_number = '{LANDROVER_PLATE}';")
    assert len(d1_records) == 1, "Vehicle not found in remote D1"
    rec = d1_records[0]
    assert rec["plate_number"] == LANDROVER_PLATE
    assert rec["target_price"] == 1090, f"D1 target_price mismatch: {rec['target_price']}"
    assert rec["mileage"] == 125428, f"D1 mileage mismatch: {rec['mileage']}"
    assert rec["is_public"] == 0, f"D1 is_public must be 0 (PENDING_REVIEW), got {rec['is_public']}"
    assert rec["publishing_status"] == "PENDING_REVIEW", f"D1 publishing_status must be PENDING_REVIEW, got {rec['publishing_status']}"
    logger.info(f"  [PASS] Step 4: 원격 D1 재조회 1:1 일치 검증 완료 (가격=1090, 주행거리=125428km, is_public=0, PENDING_REVIEW)")

    # Step 5: 2회차 무변동 실행 시 D1 전송 완벽 생략 (TASK 2)
    res_skip = daemon.inspect_and_sync_incremental(dry_run=False)
    assert res_skip["sync_result"] == "SKIPPED_NO_CHANGES", f"Expected SKIPPED_NO_CHANGES, got {res_skip['sync_result']}"
    assert res_skip["changed_count"] == 0, f"Expected 0 changed cars, got {res_skip['changed_count']}"
    logger.info("  [PASS] Step 5: 2회차 무변동 실행 시 D1 전송 완벽 생략 (SKIPPED_NO_CHANGES)")

    # Step 6: 인증된 관리자 API를 통한 실제 D1 레코드 조회 검증 (TASK 4)
    admin_url = f"{REMOTE_PROD_URL}/api/admin/vehicles/{urllib.parse.quote(LANDROVER_PLATE)}?token={SYNC_SECRET}"
    req = urllib.request.Request(admin_url, headers={"User-Agent": "Directive136Verifier/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200, f"Admin API failed: {resp.status}"
        admin_data = json.loads(resp.read().decode('utf-8'))

    assert admin_data["_source"] == "CLOUDFLARE_D1_REAL_RECORD"
    assert admin_data["plate_number"] == LANDROVER_PLATE
    assert admin_data["target_price"] == 1090
    assert admin_data["mileage"] == 125428
    assert admin_data["is_public"] == 0
    assert admin_data["publishing_status"] == "PENDING_REVIEW"
    assert admin_data["photo_count"] == 9
    assert len(admin_data["photos"]) == 9
    assert admin_data["seller_company_name"] == "(주)더쿨모터스"
    assert admin_data["dealer_name"] == "유동호"
    logger.info("  [PASS] Step 6: 관리자 API 실제 D1 레코드(사진 9장, 125,428km, 1,090만원, 비공개) 검증 완료")

    # Step 7: 고객용 공개 API 0대 격리 검증 (TASK 1 & TASK 5)
    pub_url = f"{REMOTE_PROD_URL}/api/chamart/vehicles"
    pub_req = urllib.request.Request(pub_url, headers={"User-Agent": "Directive136Verifier/1.0"})
    with urllib.request.urlopen(pub_req, timeout=10) as resp:
        assert resp.status == 200
        pub_cars = json.loads(resp.read().decode('utf-8'))
    assert len(pub_cars) == 0, f"Expected 0 public cars, got {len(pub_cars)}"
    logger.info("  [PASS] Step 7: 고객용 공개 API 0대 격리 확인 완료")

    logger.info("=" * 65)
    logger.info("ALL 7 DIRECTIVE 136 REAL E2E VERIFICATION STEPS PASSED (100% PASS)")
    logger.info("=" * 65)

if __name__ == "__main__":
    run_directive_136_e2e()
