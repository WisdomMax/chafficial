"""
TASK 2: 일일 동기화 ABORTED_BELOW_THRESHOLD 에러 전파 통합 테스트 (ISSUE-61)
"""

import sys
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService

DB_PATH = "data/chamart/chamart_platform_demo.db"

def test_daily_sync_status_propagation():
    service = CarManagerSyncService(db_path=DB_PATH, dry_run=True)
    
    # 1. OWNED 기준 미달 (50대 < 60대)
    sample_50 = [{"encarno": f"test_{i}", "car_name": f"Car {i}", "price": 1000} for i in range(50)]
    owned_res = service.run_sync(current_snapshot=sample_50, scope="OWNED", min_expected_count=60, dry_run=True)
    print("Owned Fail Test:", owned_res["status"])
    assert owned_res.get("status") != "SUCCESS", "Should not be SUCCESS"
    assert "ABORTED_BELOW_THRESHOLD" in owned_res.get("status")

    # 2. MARKET 기준 미달 (1000대 < 1500대)
    sample_1000 = [{"encarno": f"test_m_{i}", "car_name": f"Market Car {i}", "price": 1500} for i in range(1000)]
    market_res = service.run_sync(current_snapshot=sample_1000, scope="MARKET_OBSERVED", min_expected_count=1500, dry_run=True)
    print("Market Fail Test:", market_res["status"])
    assert market_res.get("status") != "SUCCESS", "Should not be SUCCESS"
    assert "ABORTED_BELOW_THRESHOLD" in market_res.get("status")

    # 3. OWNED 정상 (74대 >= 60대)
    sample_74 = [{"encarno": f"test_o_{i}", "car_name": f"Owned Car {i}", "price": 2000} for i in range(74)]
    owned_ok = service.run_sync(current_snapshot=sample_74, scope="OWNED", min_expected_count=60, dry_run=True)
    print("Owned OK Test:", owned_ok["status"])
    assert owned_ok.get("status") == "SUCCESS"

    print("[+] TASK 2 상태별 실패 전파 검증 100% PASS!")

if __name__ == "__main__":
    test_daily_sync_status_propagation()
