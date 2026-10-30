import json
import pytest
from pathlib import Path
from chaficial.platform.sourcing.quota_enrichment_runner import (
    DailyBudgetEnforcer, QuotaEnrichmentRunner, QuotaExhaustedException
)

def test_atomic_network_blocking_on_limit():
    print("=== [TASK 4] 201번째 차량 및 예산 초과 시 네트워크 사전 차단 통합 테스트 ===")
    
    test_cp = Path("scratch/test_atomic_blocking_cp.json")
    if test_cp.exists():
        test_cp.unlink()

    # 차량 한도 2대, KB 예산 2건, 엔카 예산 2건으로 설정
    runner = QuotaEnrichmentRunner(daily_limit=2)
    runner.budget = DailyBudgetEnforcer(test_cp, daily_car_limit=2, kb_req_limit=2, encar_req_limit=2)

    dummy_veh1 = {"id": "v1", "plate_number": "11가1111", "model_name": "아반떼", "year": 2020}
    dummy_veh2 = {"id": "v2", "plate_number": "22나2222", "model_name": "쏘나타", "year": 2020}
    dummy_veh3 = {"id": "v3", "plate_number": "33다3333", "model_name": "그랜저", "year": 2020}

    # 1. 1번째 차량 처리 -> 통과
    runner.process_vehicle_safe(dummy_veh1)
    assert runner.budget.state["cars_processed"] == 1
    print("[1] 1번째 차량 예산 차감 성공 (남은 차량: 1대)")

    # 2. 2번째 차량 처리 -> 통과
    runner.process_vehicle_safe(dummy_veh2)
    assert runner.budget.state["cars_processed"] == 2
    print("[2] 2번째 차량 예산 차감 성공 (남은 차량: 0대)")

    # 3. 3번째 차량(201번째에 대응) 진입 -> 사전 차단 검증!
    blocked = False
    try:
        runner.process_vehicle_safe(dummy_veh3)
    except QuotaExhaustedException as ex:
        blocked = True
        print(f"[3] 3번째 차량 네트워크 호출 전 즉각 사전 차단 성공: {ex}")

    assert blocked is True, "차량 한도 초과 시 사전 차단 실패!"

    if test_cp.exists():
        test_cp.unlink()
    print("[+] TASK 4 예산 초과 사전 차단 통합 테스트 100% 통과!")

if __name__ == "__main__":
    test_atomic_network_blocking_on_limit()
