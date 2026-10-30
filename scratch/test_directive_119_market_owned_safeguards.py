import sqlite3
from pathlib import Path
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService

def test_market_owned_safeguards():
    print("=== [TASK 2] 시장 관측 자동 공개 차단 및 OWNED 가격 보호 테스트 ===")
    test_db = "scratch/test_safeguards_sandbox.db"
    if Path(test_db).exists():
        Path(test_db).unlink()

    # 스키마 복제
    src_conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
    test_conn = sqlite3.connect(test_db)
    for line in src_conn.iterdump():
        if "CREATE TABLE" in line:
            test_conn.execute(line)
    test_conn.commit()
    src_conn.close()

    sync_service = CarManagerSyncService(db_path=test_db)

    # 1. MARKET_OBSERVED로 가격이 명확한 신규 차량 수집
    market_new_car = {
        "encarno": "MARKET_NEW_001",
        "full_plate": "55가5555",
        "model_name": "쏘나타 DN8",
        "model_year": "2021",
        "mileage": "3만km",
        "fuel_type": "가솔린",
        "mission": "오토",
        "color": "화이트",
        "price_manwon": "2200",
        "shop": "외부상사",
        "danji": "장안모터프라자"
    }

    sync_service.run_sync([market_new_car], scope="MARKET_OBSERVED")
    
    c = test_conn.cursor()
    c.execute("SELECT publishing_status, is_public, target_price FROM vehicles WHERE plate_number = '55가5555';")
    row = c.fetchone()
    print(f"[1] 시장 신규 차량 상태: publishing_status={row[0]}, is_public={row[1]}, target_price={row[2]}")
    assert row[0] == "DRAFT", f"시장 수집 차량이 DRAFT가 아님: {row[0]}"
    assert row[1] == 0, f"시장 수집 차량이 비공개(0)가 아님: {row[1]}"

    # 2. OWNED 자사 차량 등록 (target_price = 3000만원)
    owned_car = {
        "encarno": "OWNED_SHOP_001",
        "full_plate": "77나7777",
        "model_name": "제네시스 GV70",
        "model_year": "2022",
        "mileage": "2만km",
        "fuel_type": "가솔린",
        "mission": "오토",
        "color": "블랙",
        "price_manwon": "3000",
        "shop": "차마트1호점",
        "danji": "장안평"
    }
    sync_service.run_sync([owned_car], scope="OWNED")

    # 3. 시장 수집기(MARKET_OBSERVED)가 해당 OWNED 차량을 2800만원으로 재수집할 때
    owned_market_scraped = owned_car.copy()
    owned_market_scraped["price_manwon"] = "2800"
    sync_service.run_sync([owned_market_scraped], scope="MARKET_OBSERVED")

    c.execute("""
        SELECT v.target_price, l.advertised_price
        FROM vehicles v
        JOIN vehicle_listings l ON v.id = l.vehicle_id
        WHERE l.listing_id = 'OWNED_SHOP_001'
    """)
    res = c.fetchone()
    print(f"[2] OWNED 차량 가격 대조: vehicles.target_price={res[0]}만원, listings.advertised_price={res[1]}만원")
    assert res[0] == 3000, f"자사 관리자 target_price가 시장 수집기에 의해 오염됨! ({res[0]} != 3000)"
    assert res[1] == 2800, f"listings.advertised_price가 갱신되지 않음! ({res[1]} != 2800)"

    test_conn.close()
    if Path(test_db).exists():
        Path(test_db).unlink()

    print("[+] TASK 2 시장 관측 자동 공개 차단 및 OWNED 가격 보호 회귀 테스트 100% PASS!")

if __name__ == "__main__":
    test_market_owned_safeguards()
