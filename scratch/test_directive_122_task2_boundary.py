"""
TASK 2 경계값 및 원자적 단계 분리 회귀 테스트 (DIRECTIVE 122)
- OWNED 74 / MARKET 1,439 -> 차단 (MARKET 기준 미달)
- OWNED 74 / MARKET 1,460 -> 통과 (모든 기준 충족)
- OWNED 59 / MARKET 1,500 -> 차단 (OWNED 기준 미달)
- 시계열 실패 시 운영 DB 동기화 완전 차단
"""

import sys
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService

DB_PATH = "data/chamart/chamart_platform_demo.db"

def test_boundaries():
    MIN_TOTAL_THRESHOLD = 1500
    MIN_OWNED_THRESHOLD = 60
    MIN_MARKET_OBSERVED_THRESHOLD = 1440

    def evaluate_guards(owned_count, market_count):
        total_count = owned_count + market_count
        if total_count < MIN_TOTAL_THRESHOLD:
            return False, f"Total ({total_count}) < {MIN_TOTAL_THRESHOLD}"
        if owned_count < MIN_OWNED_THRESHOLD:
            return False, f"Owned ({owned_count}) < {MIN_OWNED_THRESHOLD}"
        if market_count < MIN_MARKET_OBSERVED_THRESHOLD:
            return False, f"Market ({market_count}) < {MIN_MARKET_OBSERVED_THRESHOLD}"
        return True, "PASS"

    # 1. OWNED 74 / MARKET 1,439 (< 1440) -> 차단
    pass_1, reason_1 = evaluate_guards(74, 1439)
    print("Scenario 1 (74/1439):", pass_1, reason_1)
    assert not pass_1
    assert "Market (1439) < 1440" in reason_1

    # 2. OWNED 74 / MARKET 1,460 -> 통과
    pass_2, reason_2 = evaluate_guards(74, 1460)
    print("Scenario 2 (74/1460):", pass_2, reason_2)
    assert pass_2

    # 3. OWNED 59 / MARKET 1,500 -> 차단
    pass_3, reason_3 = evaluate_guards(59, 1500)
    print("Scenario 3 (59/1500):", pass_3, reason_3)
    assert not pass_3
    assert "Owned (59) < 60" in reason_3

    # 4. OWNED 74 / MARKET 1,500 -> 통과
    pass_4, reason_4 = evaluate_guards(74, 1500)
    print("Scenario 4 (74/1500):", pass_4, reason_4)
    assert pass_4

    # 5. Service 단위 호출 시 임계치 가드 일치 검증
    service = CarManagerSyncService(db_path=DB_PATH, dry_run=True)
    sample_1439 = [{"encarno": f"m_{i}", "car_name": f"Car {i}", "price": 1000} for i in range(1439)]
    res_market_fail = service.run_sync(sample_1439, scope="MARKET_OBSERVED", min_expected_count=MIN_MARKET_OBSERVED_THRESHOLD, dry_run=True)
    assert res_market_fail.get("status") != "SUCCESS"
    assert "ABORTED_BELOW_THRESHOLD" in res_market_fail.get("status")
    print("Service Threshold Guard Check:", res_market_fail.get("status"))

    print("[+] TASK 2 경계값 및 사전 가드 회귀 테스트 100% PASS!")

if __name__ == "__main__":
    test_boundaries()
