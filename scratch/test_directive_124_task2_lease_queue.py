"""
DIRECTIVE 125 TASK 2: 큐 재시도 사이클(FAILED -> 재선점 -> 한도초과 REQUIRES_ADMIN_REVIEW) 및 Lease 보안 엄격 검증 (ISSUE-88)
"""

import os
import sqlite3
import time
from chaficial.platform.sourcing.incremental_market_observer import (
    IncrementalMarketObserver
)

TEST_DB = "scratch/test_lease_queue.db"

def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    observer = IncrementalMarketObserver(db_path=TEST_DB)
    # 1개 큐 항목 등록
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO market_detail_fetch_queue (
            platform, listing_id, plate_number, model_name, raw_location,
            queue_status, retry_count, discovered_at, updated_at
        ) VALUES 
        ('CARMANAGER', 'CM_CAR_101', '11가1111', '아반떼 CN7', '장안모터프라자', 'PENDING', 0, '2026-10-31T01:00:00+09:00', '2026-10-31T01:00:00+09:00')
    """)
    conn.commit()
    conn.close()
    return observer

def test_queue_full_retry_lifecycle():
    observer = setup_db()

    # 1. 1차 선점: 워커 1이 아이템 선점
    w1 = observer.claim_next_queue_item(platform="CARMANAGER", worker_id="worker_01", lease_seconds=10, max_retries=2)
    assert w1 is not None
    assert w1["listing_id"] == "CM_CAR_101"
    token_1 = w1["claim_token"]
    print("[+] 1. 1차 정상 선점:", w1["listing_id"], "Token:", token_1[:8])

    # 2. 토큰 누락(None/빈값) 시도 -> ValueError 차단 확인
    try:
        observer.mark_queue_item_completed(platform="CARMANAGER", listing_id="CM_CAR_101", claim_token=None)
        assert False, "claim_token=None should raise ValueError"
    except ValueError as e:
        print("[+] 2. 완료 시 claim_token 누락 정상 차단:", e)

    try:
        observer.mark_queue_item_failed(platform="CARMANAGER", listing_id="CM_CAR_101", error_msg="err", claim_token="")
        assert False, "claim_token='' should raise ValueError"
    except ValueError as e:
        print("[+] 2-1. 실패 시 claim_token 누락 정상 차단:", e)

    # 3. 1차 실패 처리 (유효 토큰 전달)
    f1_res = observer.mark_queue_item_failed(
        platform="CARMANAGER", 
        listing_id="CM_CAR_101", 
        error_msg="Temporary HTTP 504 Gateway Timeout", 
        claim_token=token_1, 
        max_retries=2
    )
    assert f1_res is True
    print("[+] 3. 1차 실패 처리 성공 (status='FAILED', retry_count=1)")

    # DB 상태 검증: FAILED로 전이되고 worker_id, claim_token, lease_expires_at이 초기화되어 재선점 대기 상태여야 함
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("SELECT queue_status, retry_count, worker_id, claim_token, lease_expires_at FROM market_detail_fetch_queue WHERE listing_id = 'CM_CAR_101'")
    row_f1 = c.fetchone()
    conn.close()
    assert row_f1 == ('FAILED', 1, None, None, None)
    print("[+] 3-1. DB 초기화 상태 확인:", row_f1)

    # 이전 워커 1의 만료된 token_1으로 완료 시도 -> 차단 확인 (상태가 IN_PROGRESS가 아니므로)
    stale_complete = observer.mark_queue_item_completed(platform="CARMANAGER", listing_id="CM_CAR_101", claim_token=token_1)
    assert stale_complete is False
    print("[+] 3-2. 실패 처리 후 이전 토큰 완료 시도 정상 차단")

    # 4. 2차 선점: FAILED 상태의 아이템이 정상 재선점되는지 검증 (DIRECTIVE 125 핵심 요구사항!)
    w2 = observer.claim_next_queue_item(platform="CARMANAGER", worker_id="worker_02", lease_seconds=10, max_retries=2)
    assert w2 is not None, "FAILED 상태 아이템이 재선점되지 않았습니다!"
    assert w2["listing_id"] == "CM_CAR_101"
    assert w2["retry_count"] == 1
    token_2 = w2["claim_token"]
    assert token_2 != token_1, "새 선점 시 새로운 토큰이 발급되어야 합니다"
    print("[+] 4. FAILED 매물 재선점 성공: Worker:", w2["worker_id"], "New Token:", token_2[:8])

    # 5. 2차 실패 처리 (재시도 한도 max_retries=2 도달 시뮬레이션)
    f2_res = observer.mark_queue_item_failed(
        platform="CARMANAGER",
        listing_id="CM_CAR_101",
        error_msg="Persistent HTTP 404 Not Found",
        claim_token=token_2,
        max_retries=2
    )
    assert f2_res is True
    print("[+] 5. 2차 실패 처리 성공 (한도 도달 -> REQUIRES_ADMIN_REVIEW 전이)")

    # DB 상태 검증: REQUIRES_ADMIN_REVIEW로 전이되고 retry_count=2
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("SELECT queue_status, retry_count FROM market_detail_fetch_queue WHERE listing_id = 'CM_CAR_101'")
    row_f2 = c.fetchone()
    conn.close()
    assert row_f2 == ('REQUIRES_ADMIN_REVIEW', 2)
    print("[+] 5-1. 최종 REQUIRES_ADMIN_REVIEW 전이 확인:", row_f2)

    # 6. 추가 선점 시도 -> 더 이상 선점되지 않음(None) 확인
    w3 = observer.claim_next_queue_item(platform="CARMANAGER", worker_id="worker_03", max_retries=2)
    assert w3 is None, "한도 초과된 관리자 검토 아이템이 잘못 선점되었습니다!"
    print("[+] 6. 관리자 검토 큐 매물 재선점 제외 확인 (w3 is None)")

    print("\n[+] DIRECTIVE 125 TASK 2 (ISSUE-88) 큐 재시도 사이클 및 토큰 보안 테스트 100% PASS!")

if __name__ == "__main__":
    test_queue_full_retry_lifecycle()
