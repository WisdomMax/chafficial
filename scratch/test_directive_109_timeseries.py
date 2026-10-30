import os
import sqlite3
import shutil
from datetime import datetime, timedelta
from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine

TEST_DB_PATH = "data/chamart/test_directive_109_timeseries.db"
ORIGINAL_DB_PATH = "data/chamart/chamart_platform_demo.db"

def run_3day_timeseries_experiment():
    print("================================================================================")
    print("[*] TASK 4: Executing 3-Day Time-Series Historical Replay Experiment (DIRECTIVE 109)")
    print("================================================================================")

    # 1. 독립 테스트 DB 복제
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    shutil.copyfile(ORIGINAL_DB_PATH, TEST_DB_PATH)

    engine = MarketTimeSeriesEngine(db_path=TEST_DB_PATH)

    day1 = (datetime.now() - timedelta(days=2)).isoformat()
    day2 = (datetime.now() - timedelta(days=1)).isoformat()
    day3 = datetime.now().isoformat()

    # ---------------------------------------------------------
    # [DAY 1] 차량 A(1,500만), 차량 B(1,200만) 유입
    # ---------------------------------------------------------
    print("\n--- [DAY 1] Ingesting Initial Vehicles A & B ---")
    snap_day1 = [
        {"encarno": "CAR_A_ENCARNO", "price_manwon": 1500, "model": "쏘나타 DN8", "mileage": "3만km"},
        {"encarno": "CAR_B_ENCARNO", "price_manwon": 1200, "model": "아반떼 CN7", "mileage": "5만km"}
    ]
    res1 = engine.record_snapshot(snap_day1, started_at=day1, finished_at=day1, pages_collected=89)
    print(f"  * Day 1 Result: Obs={res1['observations_count']}, Appeared={res1['appeared_count']}, PriceDecreased={res1['price_decreased_count']}")
    assert res1['observations_count'] == 2 and res1['appeared_count'] == 2

    # ---------------------------------------------------------
    # [DAY 2] 차량 A(1,450만으로 50만원 인하), 차량 B(1,200만 유지)
    # ---------------------------------------------------------
    print("\n--- [DAY 2] Price Cut on Car A (1,500 -> 1,450), Car B Unchanged ---")
    snap_day2 = [
        {"encarno": "CAR_A_ENCARNO", "price_manwon": 1450, "model": "쏘나타 DN8", "mileage": "30100km"},
        {"encarno": "CAR_B_ENCARNO", "price_manwon": 1200, "model": "아반떼 CN7", "mileage": "50050km"}
    ]
    res2 = engine.record_snapshot(snap_day2, started_at=day2, finished_at=day2, pages_collected=89)
    print(f"  * Day 2 Result: Obs={res2['observations_count']}, PriceDecreased={res2['price_decreased_count']}, Disappeared={res2['disappeared_count']}")
    assert res2['observations_count'] == 2 and res2['price_decreased_count'] == 1 and res2['disappeared_count'] == 0

    # ---------------------------------------------------------
    # [DAY 3] 차량 A(1,390만으로 60만원 추가 인하), 차량 B(목록에서 사라짐)
    # ---------------------------------------------------------
    print("\n--- [DAY 3] Second Price Cut on Car A (1,450 -> 1,390), Car B Disappeared ---")
    snap_day3 = [
        {"encarno": "CAR_A_ENCARNO", "price_manwon": 1390, "model": "쏘나타 DN8", "mileage": "30200km"}
    ]
    res3 = engine.record_snapshot(snap_day3, started_at=day3, finished_at=day3, pages_collected=89)
    print(f"  * Day 3 Result: Obs={res3['observations_count']}, PriceDecreased={res3['price_decreased_count']}, Disappeared={res3['disappeared_count']}")
    assert res3['observations_count'] == 1 and res3['price_decreased_count'] == 1 and res3['disappeared_count'] == 1

    # ---------------------------------------------------------
    # [SQL 정밀 검증]
    # ---------------------------------------------------------
    print("\n--- [SQL Verification] Querying Database for 3-Day History ---")
    conn = sqlite3.connect(TEST_DB_PATH)
    c = conn.cursor()

    # 1. 차량 A의 관측 이력 (정확히 3개 시점 보존)
    c.execute("SELECT observed_at, price_manwon, mileage_km FROM market_listing_observations WHERE encarno = 'CAR_A_ENCARNO' ORDER BY observed_at ASC")
    obs_a = c.fetchall()
    print(f"  * Car A Observation History (Count={len(obs_a)}):")
    for o in obs_a:
        print(f"    - Observed: {o[0]} | Price: {o[1]}만원 | Mileage: {o[2]}km")
    assert len(obs_a) == 3 and [o[1] for o in obs_a] == [1500, 1450, 1390]

    # 2. 차량 A의 가격 인하 이벤트 (정확히 2건 기록)
    c.execute("SELECT from_value, to_value, event_at, notes FROM market_listing_events WHERE encarno = 'CAR_A_ENCARNO' AND event_type = 'PRICE_DECREASED' ORDER BY event_at ASC")
    evts_a = c.fetchall()
    print(f"  * Car A Price Decreased Events (Count={len(evts_a)}):")
    for e in evts_a:
        print(f"    - Event: {e[0]}만 -> {e[1]}만 | {e[3]}")
    assert len(evts_a) == 2 and evts_a[0][0] == '1500' and evts_a[0][1] == '1450' and evts_a[1][0] == '1450' and evts_a[1][1] == '1390'

    # 3. 차량 B의 관측 이력 (2개 시점 보존) 및 사라짐 이벤트 (1건 기록)
    c.execute("SELECT observed_at, price_manwon FROM market_listing_observations WHERE encarno = 'CAR_B_ENCARNO' ORDER BY observed_at ASC")
    obs_b = c.fetchall()
    print(f"  * Car B Observation History (Count={len(obs_b)}):")
    for o in obs_b:
        print(f"    - Observed: {o[0]} | Price: {o[1]}만원")
    assert len(obs_b) == 2

    c.execute("SELECT event_type, from_value, to_value, notes FROM market_listing_events WHERE encarno = 'CAR_B_ENCARNO'")
    evts_b = c.fetchall()
    print(f"  * Car B Events (Count={len(evts_b)}):")
    for e in evts_b:
        print(f"    - {e[0]}: {e[1]} -> {e[2]} ({e[3]})")
    disappeared_evts = [e for e in evts_b if e[0] == 'DELISTED_DISAPPEARED']
    assert len(disappeared_evts) == 1 and "목록에서 미관측" in disappeared_evts[0][3]

    # 4. 가짜 SOLD 이벤트 생성 0건 검증
    c.execute("SELECT count(*) FROM market_listing_events WHERE event_type = 'SOLD' OR event_type = 'EXPLICIT_SOLD'")
    sold_evts = c.fetchone()[0]
    print(f"  * Fake SOLD events generated: {sold_evts} (100% Zero Safe)")
    assert sold_evts == 0

    conn.close()

    # 테스트 DB 정리
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    print("\n================================================================================")
    print("[+] 3-DAY TIME-SERIES REPLAY EXPERIMENT 100% PASSED AND SQL VERIFIED!")
    print("================================================================================")

if __name__ == "__main__":
    run_3day_timeseries_experiment()
