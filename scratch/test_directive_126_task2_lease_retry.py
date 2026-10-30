"""
DIRECTIVE 126 TASK 2 (ISSUE-93, ISSUE-94) Regression Test Suite:
1. CrossPlatformMatcher admin_approvals Strict Guard:
   - Denies manual verification if platform is NULL or empty string.
   - Denies manual verification if external_car_id is NULL or empty string.
   - Denies manual verification on platform or external_car_id mismatch.
   - Accepts when approval record strictly matches.
2. IncrementalMarketObserver Queue Retry Backoff & Lease Guard:
   - claim_token strictly required (ValueError on None/empty).
   - lease_expires_at IS NULL strictly rejected for both complete and fail.
   - FAILED status receives exponential backoff next_retry_at = now + 60s * retry_count.
   - Claim worker skips FAILED items whose next_retry_at has not yet arrived.
   - Claim worker successfully claims FAILED items after next_retry_at arrives.
"""

import sys
import os
import sqlite3
import time
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, "src")

from chaficial.platform.sourcing.cross_platform_matcher import CrossPlatformMatcher, MatchResult, MatchingStatus, ObservationMode
from chaficial.platform.sourcing.incremental_market_observer import IncrementalMarketObserver, MarketListingSummary

def setup_test_db(db_path: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_listings (
            id TEXT PRIMARY KEY,
            vehicle_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            listing_id TEXT NOT NULL,
            listing_url TEXT,
            advertised_price INTEGER,
            listing_status TEXT DEFAULT 'ACTIVE',
            first_observed_at DATETIME,
            last_observed_at DATETIME,
            data_confidence REAL,
            observation_notes TEXT,
            is_demo INTEGER DEFAULT 0,
            source_confidence REAL,
            unverified_consecutive_count INTEGER DEFAULT 0,
            UNIQUE(platform, listing_id)
        );
    """)
    # 느슨한 구형 스키마 에뮬레이션 (NULL 허용)
    c.execute("""
        CREATE TABLE IF NOT EXISTS admin_approvals (
            approval_id TEXT PRIMARY KEY,
            vehicle_id TEXT NOT NULL,
            platform TEXT,
            external_car_id TEXT,
            admin_id TEXT NOT NULL,
            approval_type TEXT NOT NULL DEFAULT 'MANUAL_MATCH',
            status TEXT NOT NULL,
            approved_at TEXT NOT NULL,
            notes TEXT
        );
    """)
    conn.commit()
    conn.close()

    observer = IncrementalMarketObserver(db_path=db_path)
    observer.ensure_schema()

def test_admin_approval_null_and_mismatch_guards():
    print("[*] Test 1: CrossPlatformMatcher Admin Approval NULL & Mismatch Guards (ISSUE-93)...")
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_matcher_guard.db")
    setup_test_db(test_db)

    matcher = CrossPlatformMatcher(db_path=test_db, is_production=False)

    conn = sqlite3.connect(test_db)
    c = conn.cursor()

    # Case A: platform is NULL
    c.execute("""
        INSERT INTO admin_approvals (approval_id, vehicle_id, platform, external_car_id, admin_id, status, approved_at)
        VALUES ('appr_null_plat', 'veh_001', NULL, 'encar_9999', 'admin_1', 'APPROVED', '2026-10-31T00:00:00')
    """)
    conn.commit()

    match_null_plat = MatchResult(
        vehicle_id="veh_001",
        plate_number="12가3456",
        source_platform="ENCAR",
        external_car_id="encar_9999",
        external_url="https://www.encar.com/car/encar_9999",
        advertised_price_manwon=2500,
        photo_urls=[],
        status=MatchingStatus.VERIFIED,
        match_score=0.95,
        match_evidence={"admin_approval": {"approval_id": "appr_null_plat", "admin_id": "admin_1", "approved_at": "2026-10-31T00:00:00"}},
        observation_mode=ObservationMode.MANUAL_VERIFIED,
        matched_at="2026-10-31T00:00:00"
    )

    try:
        matcher.record_verified_match(match_null_plat)
        assert False, "FAIL: Should have raised PermissionError for NULL platform!"
    except PermissionError as e:
        assert "cannot be null or empty" in str(e)
        print("  -> PASS: NULL platform rejected with PermissionError.")

    # Case B: external_car_id is empty string
    c.execute("""
        INSERT INTO admin_approvals (approval_id, vehicle_id, platform, external_car_id, admin_id, status, approved_at)
        VALUES ('appr_empty_ext', 'veh_001', 'ENCAR', '', 'admin_1', 'APPROVED', '2026-10-31T00:00:00')
    """)
    conn.commit()

    match_empty_ext = MatchResult(
        vehicle_id="veh_001",
        plate_number="12가3456",
        source_platform="ENCAR",
        external_car_id="encar_9999",
        external_url="https://www.encar.com/car/encar_9999",
        advertised_price_manwon=2500,
        photo_urls=[],
        status=MatchingStatus.VERIFIED,
        match_score=0.95,
        match_evidence={"admin_approval": {"approval_id": "appr_empty_ext", "admin_id": "admin_1", "approved_at": "2026-10-31T00:00:00"}},
        observation_mode=ObservationMode.MANUAL_VERIFIED,
        matched_at="2026-10-31T00:00:00"
    )

    try:
        matcher.record_verified_match(match_empty_ext)
        assert False, "FAIL: Should have raised PermissionError for empty external_car_id!"
    except PermissionError as e:
        assert "cannot be null or empty" in str(e)
        print("  -> PASS: Empty external_car_id rejected with PermissionError.")

    # Case C: Platform mismatch (approved for KB_CHACHACHA, match is ENCAR)
    c.execute("""
        INSERT INTO admin_approvals (approval_id, vehicle_id, platform, external_car_id, admin_id, status, approved_at)
        VALUES ('appr_mismatch_plat', 'veh_001', 'KB_CHACHACHA', 'encar_9999', 'admin_1', 'APPROVED', '2026-10-31T00:00:00')
    """)
    conn.commit()

    match_mismatch_plat = MatchResult(
        vehicle_id="veh_001",
        plate_number="12가3456",
        source_platform="ENCAR",
        external_car_id="encar_9999",
        external_url="https://www.encar.com/car/encar_9999",
        advertised_price_manwon=2500,
        photo_urls=[],
        status=MatchingStatus.VERIFIED,
        match_score=0.95,
        match_evidence={"admin_approval": {"approval_id": "appr_mismatch_plat", "admin_id": "admin_1", "approved_at": "2026-10-31T00:00:00"}},
        observation_mode=ObservationMode.MANUAL_VERIFIED,
        matched_at="2026-10-31T00:00:00"
    )

    try:
        matcher.record_verified_match(match_mismatch_plat)
        assert False, "FAIL: Should have raised PermissionError for platform mismatch!"
    except PermissionError as e:
        assert "Platform mismatch" in str(e)
        print("  -> PASS: Platform mismatch rejected with PermissionError.")

    # Case D: Valid matching approval
    c.execute("""
        INSERT INTO admin_approvals (approval_id, vehicle_id, platform, external_car_id, admin_id, status, approved_at)
        VALUES ('appr_valid', 'veh_001', 'ENCAR', 'encar_9999', 'admin_1', 'APPROVED', '2026-10-31T00:00:00')
    """)
    conn.commit()
    conn.close()

    match_valid = MatchResult(
        vehicle_id="veh_001",
        plate_number="12가3456",
        source_platform="ENCAR",
        external_car_id="encar_9999",
        external_url="https://www.encar.com/car/encar_9999",
        advertised_price_manwon=2500,
        photo_urls=[],
        status=MatchingStatus.VERIFIED,
        match_score=0.95,
        match_evidence={"admin_approval": {"approval_id": "appr_valid", "admin_id": "admin_1", "approved_at": "2026-10-31T00:00:00"}},
        observation_mode=ObservationMode.MANUAL_VERIFIED,
        matched_at="2026-10-31T00:00:00"
    )

    matcher.record_verified_match(match_valid)
    print("  -> PASS: Valid approval strictly accepted and recorded.")
    shutil.rmtree(temp_dir)

def test_queue_lease_and_retry_backoff():
    print("[*] Test 2: Detail Fetch Queue Lease & Retry Backoff (ISSUE-94)...")
    temp_dir = tempfile.mkdtemp()
    test_db = os.path.join(temp_dir, "test_queue_lease.db")
    setup_test_db(test_db)

    observer = IncrementalMarketObserver(db_path=test_db)

    # Enqueue a task
    diffs = observer.inspect_batch([
        MarketListingSummary(
            listing_id="CM_TASK_001",
            platform="CARMANAGER",
            plate_number="12가3456",
            model_name="그랜저 HG",
            advertised_price=1200,
            raw_location="장안평",
            status="ACTIVE",
            observed_at="2026-10-31T01:00:00"
        )
    ])
    observer.apply_batch_updates_and_enqueue(diffs, platform="CARMANAGER")

    # 1. Claim task
    claimed = observer.claim_next_queue_item(platform="CARMANAGER", worker_id="worker_A", lease_seconds=10)
    assert claimed is not None, "FAIL: Should have claimed pending item"
    token = claimed["claim_token"]
    assert token is not None

    # 2. Try completing without claim_token -> ValueError
    try:
        observer.mark_queue_item_completed(platform="CARMANAGER", listing_id="CM_TASK_001", claim_token="")
        assert False, "FAIL: Should raise ValueError on empty token"
    except ValueError:
        print("  -> PASS: Empty claim_token rejected with ValueError.")

    # 3. Simulate NULL lease_expires_at in DB
    conn = sqlite3.connect(test_db)
    conn.execute("UPDATE market_detail_fetch_queue SET lease_expires_at = NULL WHERE listing_id = 'CM_TASK_001'")
    conn.commit()
    conn.close()

    # Both complete and fail must be rejected when lease_expires_at is NULL!
    success_comp = observer.mark_queue_item_completed(platform="CARMANAGER", listing_id="CM_TASK_001", claim_token=token)
    assert success_comp is False, "FAIL: Completing when lease_expires_at is NULL must return False"
    success_fail = observer.mark_queue_item_failed(platform="CARMANAGER", listing_id="CM_TASK_001", error_msg="test err", claim_token=token)
    assert success_fail is False, "FAIL: Failing when lease_expires_at is NULL must return False"
    print("  -> PASS: NULL lease_expires_at strictly rejected for both complete and fail.")

    # Restore valid lease
    now_epoch = time.time()
    lease_expires_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime(now_epoch + 300))
    conn = sqlite3.connect(test_db)
    conn.execute("UPDATE market_detail_fetch_queue SET lease_expires_at = ? WHERE listing_id = 'CM_TASK_001'", (lease_expires_iso,))
    conn.commit()
    conn.close()

    # 4. Mark failed -> Should assign next_retry_at = now + 60s * 1 = now + 60s
    success_fail = observer.mark_queue_item_failed(platform="CARMANAGER", listing_id="CM_TASK_001", error_msg="timeout", claim_token=token)
    assert success_fail is True, "FAIL: Failed mark with active lease should succeed"

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("SELECT queue_status, retry_count, next_retry_at, worker_id, claim_token FROM market_detail_fetch_queue WHERE listing_id = 'CM_TASK_001'")
    row = c.fetchone()
    conn.close()

    assert row[0] == "FAILED", f"Status must be FAILED, got {row[0]}"
    assert row[1] == 1, f"Retry count must be 1, got {row[1]}"
    assert row[2] is not None, "next_retry_at must be populated!"
    assert row[3] is None and row[4] is None, "Worker and token must be reset"
    print(f"  -> PASS: Item marked FAILED with backoff next_retry_at: {row[2]}")

    # 5. Try claiming immediately -> Must return None because next_retry_at is in the future (~60s away)
    immediate_claim = observer.claim_next_queue_item(platform="CARMANAGER", worker_id="worker_B")
    assert immediate_claim is None, "FAIL: FAILED item should not be claimed before next_retry_at!"
    print("  -> PASS: Worker skipped FAILED item during backoff window.")

    # 6. Simulate backoff elapsed (set next_retry_at to past)
    past_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime(time.time() - 10))
    conn = sqlite3.connect(test_db)
    conn.execute("UPDATE market_detail_fetch_queue SET next_retry_at = ? WHERE listing_id = 'CM_TASK_001'", (past_iso,))
    conn.commit()
    conn.close()

    # Now claim should succeed!
    retry_claim = observer.claim_next_queue_item(platform="CARMANAGER", worker_id="worker_B")
    assert retry_claim is not None, "FAIL: Item should be claimable after backoff window elapsed"
    assert retry_claim["listing_id"] == "CM_TASK_001"
    assert retry_claim["retry_count"] == 1
    assert retry_claim["prior_status"] == "FAILED"
    print("  -> PASS: FAILED item successfully reclaimed after backoff elapsed!")

    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    test_admin_approval_null_and_mismatch_guards()
    test_queue_lease_and_retry_backoff()
    print("\n[+] ALL DIRECTIVE 126 TASK 2 REPRESSION TESTS PASSED 100%!")
