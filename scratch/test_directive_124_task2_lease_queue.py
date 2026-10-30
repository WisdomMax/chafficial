"""
DIRECTIVE 124 TASK 2 테스트: 큐 임대 만료(Lease Expiration) 기반 크래시 복구 및 claim_token 선점 검증 (ISSUE-83)
"""

import os
import sqlite3
import time
from chaficial.platform.sourcing.incremental_market_observer import (
    IncrementalMarketObserver, MarketListingSummary, DiffResult, ObservationAction
)

TEST_DB = "scratch/test_lease_queue.db"

def setup_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    observer = IncrementalMarketObserver(db_path=TEST_DB)
    # 2개 큐 항목 등록
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO market_detail_fetch_queue (
            platform, listing_id, plate_number, model_name, raw_location,
            queue_status, retry_count, discovered_at, updated_at
        ) VALUES 
        ('CARMANAGER', 'CM_CAR_101', '11가1111', '아반떼 CN7', '장안모터프라자', 'PENDING', 0, '2026-10-31T01:00:00+09:00', '2026-10-31T01:00:00+09:00'),
        ('CARMANAGER', 'CM_CAR_102', '22나2222', '그랜저 GN7', '장안모터프라자', 'PENDING', 0, '2026-10-31T01:05:00+09:00', '2026-10-31T01:05:00+09:00')
    """)
    conn.commit()
    conn.close()
    return observer

def test_lease_queue_lifecycle():
    observer = setup_db()

    # 1. 워커 1이 첫 번째 아이템 선점 (임대시간: 10초)
    w1_item = observer.claim_next_queue_item(
        platform="CARMANAGER",
        worker_id="worker_alpha",
        lease_seconds=10
    )
    assert w1_item is not None
    assert w1_item["listing_id"] == "CM_CAR_101"
    assert w1_item["worker_id"] == "worker_alpha"
    assert w1_item["claim_token"] is not None
    assert w1_item["lease_expires_at"] is not None
    print("[+] 1. 정상 선점 확인:", w1_item["listing_id"], w1_item["claim_token"][:8], w1_item["lease_expires_at"])

    # 2. 임대 유효 상태에서 크래시 복구 시도 -> 정상 실행 중인 워커 작업 보호 (0건 복구)
    recovered_active = observer.recover_stale_in_progress_tasks(now_iso="2026-10-31T01:10:00+09:00")
    # w1_item의 만료시간은 대략 현재시간 + 10초이므로 now_iso를 과거 시각(예: 01:00:00)으로 주면 복구 안 됨
    print("[+] 2. 활성 임대 상태 복구 시도 결과 (보호 성공):", recovered_active)
    assert recovered_active == 0, "유효한 임대 상태의 작업이 잘못 복구되었습니다!"

    # 3. 잘못된 claim_token으로 완료 시도 -> 차단 확인
    bad_token_res = observer.mark_queue_item_completed(
        platform="CARMANAGER",
        listing_id="CM_CAR_101",
        claim_token="invalid_fake_token_12345"
    )
    assert bad_token_res is False, "잘못된 claim_token으로 완료 처리됨!"
    print("[+] 3. 잘못된 claim_token 완료 시도 정상 차단")

    # 4. 임대 만료 시뮬레이션 -> 미래 시각으로 복구 호출 시 PENDING으로 안전 복원
    future_time_iso = "2026-10-31T09:00:00+09:00"
    recovered_stale = observer.recover_stale_in_progress_tasks(now_iso=future_time_iso)
    print("[+] 4. 임대 만료 후 복구 결과:", recovered_stale)
    assert recovered_stale == 1, "만료된 작업이 PENDING으로 복구되지 않았습니다!"

    # DB 상태 확인: PENDING 및 worker_id, claim_token 초기화 확인
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("SELECT queue_status, worker_id, claim_token, lease_expires_at FROM market_detail_fetch_queue WHERE listing_id = 'CM_CAR_101'")
    row = c.fetchone()
    conn.close()
    assert row == ('PENDING', None, None, None)
    print("[+] 4-1. DB 초기화 상태 확인:", row)

    # 5. 복구된 아이템을 워커 2가 새로 선점 및 정상 완료
    w2_item = observer.claim_next_queue_item(
        platform="CARMANAGER",
        worker_id="worker_beta",
        lease_seconds=300
    )
    assert w2_item is not None
    assert w2_item["listing_id"] == "CM_CAR_101"
    assert w2_item["worker_id"] == "worker_beta"
    assert w2_item["claim_token"] != w1_item["claim_token"], "새 선점 시 새로운 토큰이 발급되어야 합니다"

    # 이전 워커 1이 뒤늦게 본인의 옛날 토큰으로 완료 시도 -> 차단 확인
    old_worker_res = observer.mark_queue_item_completed(
        platform="CARMANAGER",
        listing_id="CM_CAR_101",
        claim_token=w1_item["claim_token"]
    )
    assert old_worker_res is False, "만료된 구 워커의 완료 요청이 통과되었습니다!"
    print("[+] 5. 만료된 이전 워커(worker_alpha)의 옛날 토큰 완료 요청 정상 차단")

    # 신규 워커 2가 본인의 정상 토큰으로 완료 처리
    w2_complete_res = observer.mark_queue_item_completed(
        platform="CARMANAGER",
        listing_id="CM_CAR_101",
        claim_token=w2_item["claim_token"]
    )
    assert w2_complete_res is True
    print("[+] 5-1. 정당한 워커(worker_beta)의 완료 처리 성공")

    # 6. 두 번째 아이템(CM_CAR_102) 선점 및 실패 재시도 검증
    w3_item = observer.claim_next_queue_item(platform="CARMANAGER", worker_id="worker_gamma")
    assert w3_item["listing_id"] == "CM_CAR_102"
    
    # 1회 실패 처리
    f1 = observer.mark_queue_item_failed("CARMANAGER", "CM_CAR_102", "HTTP 502", claim_token=w3_item["claim_token"], max_retries=2)
    assert f1 is True
    
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("SELECT queue_status, retry_count FROM market_detail_fetch_queue WHERE listing_id = 'CM_CAR_102'")
    fail_row1 = c.fetchone()
    conn.close()
    assert fail_row1 == ('FAILED', 1)
    print("[+] 6. 1차 실패 및 retry_count=1 확인:", fail_row1)

    # 2회 실패 처리 -> max_retries=2 도달 시 REQUIRES_ADMIN_REVIEW 전이
    f2 = observer.mark_queue_item_failed("CARMANAGER", "CM_CAR_102", "Timeout", claim_token=w3_item["claim_token"], max_retries=2)
    assert f2 is True

    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("SELECT queue_status, retry_count FROM market_detail_fetch_queue WHERE listing_id = 'CM_CAR_102'")
    fail_row2 = c.fetchone()
    conn.close()
    assert fail_row2 == ('REQUIRES_ADMIN_REVIEW', 2)
    print("[+] 6-1. 재시도 한도 초과 시 REQUIRES_ADMIN_REVIEW 전이 확인:", fail_row2)

    print("\n[+] DIRECTIVE 124 TASK 2 (ISSUE-83) 큐 임대 만료 및 토큰 기반 동시성/복구 테스트 100% PASS!")

if __name__ == "__main__":
    test_lease_queue_lifecycle()
