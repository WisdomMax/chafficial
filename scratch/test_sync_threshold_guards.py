"""
P0-1 회귀 테스트: min_expected_count 임계치 미달 시 동기화 차단 및 TypeError 방지 검증
"""

import os
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService

DB_PATH = "data/chamart/chamart_platform_demo.db"

def test_threshold_guard():
    service = CarManagerSyncService(db_path=DB_PATH, dry_run=True)
    
    # 1. 50대 데이터로 60대 미만 임계치 테스트 -> 차단 검증
    sample_50 = [{"encarno": f"test_{i}", "car_name": f"Car {i}", "price": 1000} for i in range(50)]
    res = service.run_sync(current_snapshot=sample_50, scope="OWNED", min_expected_count=60, dry_run=True)
    
    print("임계치 미달 결과:", res)
    assert "ABORTED_BELOW_THRESHOLD" in res["status"]
    assert res["new_inserted"] == 0
    assert res["price_changed"] == 0

    # 2. 70대 데이터로 60대 이상 정상 수행 테스트
    sample_70 = [{"encarno": f"test_{i}", "car_name": f"Car {i}", "price": 1000} for i in range(70)]
    res2 = service.run_sync(current_snapshot=sample_70, scope="OWNED", min_expected_count=60, dry_run=True)
    print("임계치 충족 결과:", res2["status"])
    assert res2["status"] == "SUCCESS"

    print("[+] P0-1 min_expected_count 임계치 가드 회귀 테스트 100% PASS!")

if __name__ == "__main__":
    test_threshold_guard()
