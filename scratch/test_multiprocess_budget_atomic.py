import concurrent.futures
import sqlite3
from pathlib import Path
from chaficial.platform.sourcing.atomic_budget_enforcer import (
    SqliteAtomicBudgetEnforcer, QuotaExhaustedException
)

def test_concurrent_atomic_budget():
    print("=== [TASK 3] SQLite 기반 원자적 예산 관리 다중 스레드 경쟁 테스트 ===")
    test_db = "scratch/test_concurrent_budget.db"
    if Path(test_db).exists():
        Path(test_db).unlink()

    # 일일 한도 50대로 설정
    enforcer = SqliteAtomicBudgetEnforcer(test_db, daily_car_limit=50, kb_req_limit=50, encar_req_limit=50)

    success_count = 0
    blocked_count = 0

    def attempt_deduct(v_idx):
        nonlocal success_count, blocked_count
        try:
            enforcer.check_and_deduct_car(f"veh_{v_idx}")
            return "SUCCESS"
        except QuotaExhaustedException:
            return "BLOCKED"

    # 10개의 워커 스레드가 동시에 150대의 차량 차감 경쟁 시도
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_deduct, i) for i in range(150)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res == "SUCCESS":
                success_count += 1
            else:
                blocked_count += 1

    status = enforcer.get_status()
    print(f"[1] 다중 스레드 경쟁 실행 결과:")
    print(f"    - 총 시도: 150건")
    print(f"    - 차감 성공 건수: {success_count}건")
    print(f"    - 한도 초과 차단 건수: {blocked_count}건")
    print(f"    - DB quota_ledger 최종 기록: {status['cars_processed']}건")

    assert success_count == 50, f"정확히 50건만 성공해야 함: {success_count}"
    assert blocked_count == 100, f"정확히 100건 차단되어야 함: {blocked_count}"
    assert status["cars_processed"] == 50, f"DB 카운트 불일치: {status['cars_processed']}"

    # KB 및 Encar 요청 한도 경쟁 테스트 (한도 10건)
    kb_success = 0
    kb_blocked = 0
    def attempt_kb():
        nonlocal kb_success, kb_blocked
        try:
            enforcer.check_and_deduct_kb()
            return "SUCCESS"
        except QuotaExhaustedException:
            return "BLOCKED"

    enforcer.kb_req_limit = 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_kb) for _ in range(30)]
        for f in concurrent.futures.as_completed(futures):
            if f.result() == "SUCCESS":
                kb_success += 1
            else:
                kb_blocked += 1

    print(f"[2] KB HTTP 요청 예산 경쟁 결과: 성공 {kb_success}건, 차단 {kb_blocked}건")
    assert kb_success == 10, f"KB 예산 초과 차단 실패: {kb_success}"
    assert kb_blocked == 20, f"KB 예산 초과 차단 실패: {kb_blocked}"

    if Path(test_db).exists():
        Path(test_db).unlink()
    print("[+] TASK 3 SQLite 기반 원자적 예산 강제기 다중 경쟁 테스트 100% PASS!")

if __name__ == "__main__":
    test_concurrent_atomic_budget()
