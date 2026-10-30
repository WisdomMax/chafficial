import sqlite3
from pathlib import Path
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService

def test_cross_scope_duplicate_prevention():
    print("=== [TASK 2] 크로스 스코프(OWNED -> MARKET) 중복 재발 방지 회귀 테스트 ===")
    test_db = "scratch/test_sync_duplicate_prevention.db"
    if Path(test_db).exists():
        Path(test_db).unlink()

    # 원본 DB에서 스키마 복제
    src_conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
    test_conn = sqlite3.connect(test_db)
    
    # 테이블 구조만 복제
    for line in src_conn.iterdump():
        if "CREATE TABLE" in line:
            test_conn.execute(line)
    test_conn.commit()
    src_conn.close()

    sync_service = CarManagerSyncService(db_path=test_db)

    # 1. 1단계: OWNED 자사 매물로 '차량 A' 동기화
    sample_car = {
        "encarno": "TEST_ENCARNO_UNIQUE_001",
        "full_plate": "12가3456",
        "model_name": "그랜저 IG 2.4 프리미엄",
        "model_year": "2019",
        "mileage": "4.5만km",
        "fuel_type": "가솔린",
        "mission": "오토",
        "color": "검정",
        "price_manwon": "1850",
        "shop": "차마트1호점",
        "danji": "성동구/장안모터프라"
    }

    res1 = sync_service.run_sync([sample_car], scope="OWNED")
    print(f"[1] OWNED 동기화 완료: new_inserted={res1['new_inserted']}")
    assert res1["new_inserted"] == 1

    c = test_conn.cursor()
    c.execute("SELECT count(*) FROM vehicles;")
    assert c.fetchone()[0] == 1, "초기 마스터 1개 생성 실패"
    c.execute("SELECT count(*) FROM vehicle_listings WHERE platform = 'CARMANAGER';")
    assert c.fetchone()[0] == 1, "초기 리스팅 1개 생성 실패"

    # 2. 2단계: MARKET_OBSERVED 시장 관측 스코프로 동일 차량(TEST_ENCARNO_UNIQUE_001) 재수집!
    # 가격이 1800만원으로 변경된 상황 가정
    sample_car_market = sample_car.copy()
    sample_car_market["price_manwon"] = "1800"

    res2 = sync_service.run_sync([sample_car_market], scope="MARKET_OBSERVED")
    print(f"[2] MARKET_OBSERVED 재수집 완료: new_inserted={res2['new_inserted']}, price_changed={res2['price_changed']}")
    assert res2["new_inserted"] == 0, "중복 마스터가 생성되었습니다!"
    assert res2["price_changed"] == 1, "기존 마스터 가격 갱신 실패"

    c.execute("SELECT count(*) FROM vehicles;")
    veh_count_after = c.fetchone()[0]
    print(f"[3] 재수집 후 총 차량 마스터 수: {veh_count_after}대 (마스터 증가 0대!)")
    assert veh_count_after == 1, f"마스터가 중복 생성됨: {veh_count_after} != 1"

    c.execute("SELECT count(*) FROM vehicle_listings WHERE platform = 'CARMANAGER';")
    listing_count_after = c.fetchone()[0]
    print(f"[4] 재수집 후 총 리스팅 수: {listing_count_after}건 (리스팅 중복 0건!)")
    assert listing_count_after == 1, f"리스팅이 중복 생성됨: {listing_count_after} != 1"

    test_conn.close()
    if Path(test_db).exists():
        Path(test_db).unlink()

    print("[+] TASK 2 크로스 스코프 중복 재발 방지 회귀 테스트 100% 통과!")

if __name__ == "__main__":
    test_cross_scope_duplicate_prevention()
