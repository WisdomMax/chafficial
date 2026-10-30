import json
import time
from pathlib import Path
from chaficial.platform.sourcing.quota_enrichment_runner import DailyBudgetEnforcer

def test_daily_budget_enforcer():
    print("=== [TASK 5] 일일 200대 및 요청 예산 강제 단위 테스트 ===")
    test_cp = Path("scratch/test_budget_checkpoint.json")
    if test_cp.exists():
        test_cp.unlink()

    # 1. 초기 상태 검증
    enforcer = DailyBudgetEnforcer(test_cp, daily_car_limit=5, kb_req_limit=3, encar_req_limit=2)
    assert enforcer.can_process_car() is True
    assert enforcer.can_request_kb() is True
    assert enforcer.can_request_encar() is True
    print("[1] 초기 한도 확인 통과: Car=5, KB=3, Encar=2")

    # 2. 차량 처리 누적 및 한도 소진
    for i in range(5):
        assert enforcer.can_process_car() is True
        enforcer.record_car_processed(f"test_veh_{i}")
    
    assert enforcer.can_process_car() is False, "차량 한도 5대 초과 차단 실패!"
    print("[2] 일일 차량 한도 소진 시 can_process_car() -> False 차단 확인 통과!")

    # 3. KB 및 엔카 HTTP 요청 예산 소진
    enforcer.record_kb_request()
    enforcer.record_kb_request()
    enforcer.record_kb_request()
    assert enforcer.can_request_kb() is False, "KB 요청 예산 소진 차단 실패!"
    print("[3] KB 요청 예산 소진 시 can_request_kb() -> False 차단 확인 통과!")

    enforcer.record_encar_request()
    enforcer.record_encar_request()
    assert enforcer.can_request_encar() is False, "엔카 요청 예산 소진 차단 실패!"
    print("[4] 엔카 요청 예산 소진 시 can_request_encar() -> False 차단 확인 통과!")

    # 4. 재부팅 시 체크포인트 복원 검증
    reloaded = DailyBudgetEnforcer(test_cp, daily_car_limit=5, kb_req_limit=3, encar_req_limit=2)
    assert reloaded.can_process_car() is False
    assert reloaded.can_request_kb() is False
    assert reloaded.can_request_encar() is False
    print("[5] 체크포인트 파일 영구 보존 및 재기동 시 상태 복원 통과!")

    if test_cp.exists():
        test_cp.unlink()
    print("[+] TASK 5 일일 200대 제한 및 요청량 제어 단위 테스트 100% 통과!")

if __name__ == "__main__":
    test_daily_budget_enforcer()
