import multiprocessing
import sqlite3
import time
from pathlib import Path
from chaficial.platform.sourcing.atomic_budget_enforcer import (
    SqliteAtomicBudgetEnforcer, QuotaExhaustedException
)

def worker_process(db_path: str, worker_id: int, return_dict: dict):
    enforcer = SqliteAtomicBudgetEnforcer(db_path, daily_car_limit=50, kb_req_limit=50, encar_req_limit=50)
    success = 0
    blocked = 0
    for i in range(30):
        try:
            enforcer.check_and_deduct_car(f"proc_veh_{worker_id}_{i}")
            success += 1
        except QuotaExhaustedException:
            blocked += 1
        time.sleep(0.005)
    return_dict[worker_id] = (success, blocked)

def test_multiprocess_atomic_and_next_day():
    print("=== [TASK 3] 독립 멀티프로세스 동시성 및 다음날 재관측 검증 ===")
    test_db = "scratch/test_multiprocess_atomic.db"
    if Path(test_db).exists():
        Path(test_db).unlink()

    # 1. 5개 독립 프로세스 동시 실행 (각각 30회, 총 150회 차감 경쟁)
    manager = multiprocessing.Manager()
    return_dict = manager.dict()
    processes = []

    for w_id in range(5):
        p = multiprocessing.Process(target=worker_process, args=(test_db, w_id, return_dict))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    total_success = sum(v[0] for v in return_dict.values())
    total_blocked = sum(v[1] for v in return_dict.values())

    print(f"[1] 멀티프로세스 경쟁 결과:")
    print(f"    - 총 시도: 150건 (5개 프로세스)")
    print(f"    - 총 성공: {total_success}건")
    print(f"    - 총 차단: {total_blocked}건")
    assert total_success == 50, f"정확히 50건만 성공해야 함: {total_success}"
    assert total_blocked == 100, f"정확히 100건 차단되어야 함: {total_blocked}"

    # 2. 다음 날 동일 차량 재관측 허용 검증을 위해 새 독립 테스트 DB 사용
    test_db_next = "scratch/test_next_day.db"
    if Path(test_db_next).exists():
        Path(test_db_next).unlink()

    enforcer_next = SqliteAtomicBudgetEnforcer(test_db_next, daily_car_limit=10, kb_req_limit=10, encar_req_limit=10)

    # 어제 날짜('2026-10-30')로 차량 'veh_repeat' 관측 기록 삽입
    conn = sqlite3.connect(test_db_next)
    c = conn.cursor()
    c.execute("""
        INSERT INTO quota_processed_vehicles (processed_date, vehicle_id, processed_at)
        VALUES ('2026-10-30', 'veh_repeat', '2026-10-30T15:00:00')
    """)
    conn.commit()
    conn.close()

    # 오늘 날짜('2026-10-31')에 동일 차량('veh_repeat') 차감 시도 -> 정상 허용!
    enforcer_next.check_and_deduct_car("veh_repeat")
    print("[2] 어제 관측된 동일 차량('veh_repeat')이 오늘 날짜에 정상 재관측 허용됨 확인 통과!")

    # 오늘 날짜에 같은 차량 2회차 시도 -> 이미 오늘 처리되었으므로 예산 추가 차감 없이 통과
    enforcer_next.check_and_deduct_car("veh_repeat")
    status = enforcer_next.get_status()
    print(f"[3] 오늘 동일 차량 2회 중복 호출 시 예산 중복 차감 없음 (현재 차감: {status['cars_processed']}대)")
    assert status["cars_processed"] == 1, "동일 차량 당일 중복 차감 방지 실패"

    if Path(test_db).exists():
        Path(test_db).unlink()
    if Path(test_db_next).exists():
        Path(test_db_next).unlink()

    print("[+] TASK 3 독립 멀티프로세스 경쟁 및 다음날 재관측 검증 100% 통과!")

if __name__ == "__main__":
    test_multiprocess_atomic_and_next_day()
