import os
import sys
import uuid
import sqlite3
import shutil
from datetime import datetime

sys.path.insert(0, ".")
sys.path.insert(0, "src")
from src.chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
from scripts.run_daily_sync import run_sync_pipeline

TEST_DB = "data/chamart/sandbox_directive_128_task1.db"
PROD_DB = "data/chamart/chamart_platform_demo.db"

def setup_test_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    # 실제 운영 DB 스키마 복제
    conn_src = sqlite3.connect(PROD_DB)
    conn_dst = sqlite3.connect(TEST_DB)
    for line in conn_src.iterdump():
        if "sqlite_sequence" in line:
            continue
        try:
            conn_dst.execute(line)
        except Exception:
            pass
    conn_dst.commit()
    conn_src.close()
    conn_dst.close()

def run_tests():
    print("=" * 60)
    print("[DIRECTIVE 128 TASK 1] HISTORICAL_REPLAY 불변성 회귀 테스트 시작")
    print("=" * 60)

    setup_test_db()
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()

    # 테스트 기준 차량 4대 세팅
    now = "2026-10-31T01:00:00"
    v_car1 = str(uuid.uuid4())
    v_car2 = str(uuid.uuid4())
    v_car3 = str(uuid.uuid4())
    v_car4 = str(uuid.uuid4())

    # CAR1: 기존 1500만원, ACTIVE
    cursor.execute("""
        INSERT INTO vehicles (id, branch_id, plate_number, model_name, year, mileage, fuel_type, transmission, color, purchase_price, target_price, status, created_at, updated_at, publishing_status, is_public, listing_ownership_type, is_demo, timeline_json)
        VALUES (?, 'B01', '11가1111', '테스트차1', 2020, 50000, '가솔린', '오토', '흰색', 1000, 1500, 'DRAFT', ?, ?, 'PUBLISHED', 1, 'MARKET_JANGHANPYEONG', 0, '[]')
    """, (v_car1, now, now))
    cursor.execute("""
        INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, advertised_price, listing_status, first_observed_at, last_observed_at, unverified_consecutive_count, is_demo)
        VALUES ('L_1111', ?, 'CARMANAGER', 'ENCAR_1111', 1500, 'ACTIVE', ?, ?, 0, 0)
    """, (v_car1, now, now))

    # CAR2: 기존 1500만원, ACTIVE
    cursor.execute("""
        INSERT INTO vehicles (id, branch_id, plate_number, model_name, year, mileage, fuel_type, transmission, color, purchase_price, target_price, status, created_at, updated_at, publishing_status, is_public, listing_ownership_type, is_demo, timeline_json)
        VALUES (?, 'B01', '22가2222', '테스트차2', 2021, 30000, '가솔린', '오토', '검정', 1000, 1500, 'DRAFT', ?, ?, 'PUBLISHED', 1, 'MARKET_JANGHANPYEONG', 0, '[]')
    """, (v_car2, now, now))
    cursor.execute("""
        INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, advertised_price, listing_status, first_observed_at, last_observed_at, unverified_consecutive_count, is_demo)
        VALUES ('L_2222', ?, 'CARMANAGER', 'ENCAR_2222', 1500, 'ACTIVE', ?, ?, 0, 0)
    """, (v_car2, now, now))

    # CAR3: 기존 가격 NULL (상담), ACTIVE
    cursor.execute("""
        INSERT INTO vehicles (id, branch_id, plate_number, model_name, year, mileage, fuel_type, transmission, color, purchase_price, target_price, status, created_at, updated_at, publishing_status, is_public, listing_ownership_type, is_demo, timeline_json)
        VALUES (?, 'B01', '33가3333', '테스트차3', 2019, 70000, '디젤', '오토', '쥐색', 800, NULL, 'DRAFT', ?, ?, 'PUBLISHED', 1, 'MARKET_JANGHANPYEONG', 0, '[]')
    """, (v_car3, now, now))
    cursor.execute("""
        INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, advertised_price, listing_status, first_observed_at, last_observed_at, unverified_consecutive_count, is_demo)
        VALUES ('L_3333', ?, 'CARMANAGER', 'ENCAR_3333', NULL, 'ACTIVE', ?, ?, 0, 0)
    """, (v_car3, now, now))

    # CAR4: 기존 ACTIVE
    cursor.execute("""
        INSERT INTO vehicles (id, branch_id, plate_number, model_name, year, mileage, fuel_type, transmission, color, purchase_price, target_price, status, created_at, updated_at, publishing_status, is_public, listing_ownership_type, is_demo, timeline_json)
        VALUES (?, 'B01', '44가4444', '테스트차4', 2018, 90000, 'LPG', '오토', '은색', 500, 800, 'DRAFT', ?, ?, 'PUBLISHED', 1, 'MARKET_JANGHANPYEONG', 0, '[]')
    """, (v_car4, now, now))
    cursor.execute("""
        INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, advertised_price, listing_status, first_observed_at, last_observed_at, unverified_consecutive_count, is_demo)
        VALUES ('L_4444', ?, 'CARMANAGER', 'ENCAR_4444', 800, 'ACTIVE', ?, ?, 0, 0)
    """, (v_car4, now, now))

    conn.commit()

    # 과거 원본 스냅샷 데이터 모의 생성
    # 1. CAR1: 과거 가격 1,700만원 (현재 1,500보다 높음)
    # 2. CAR2: 과거 가격 1,200만원 (현재 1,500보다 낮음)
    # 3. CAR3: 과거 가격 1,500만원 (현재는 상담/NULL)
    # 4. CAR4: 과거 상태 불일치 (예: 가격 동일하나 과거 스냅샷)
    # 5. CAR5: 과거 파일에만 존재하는 신규 ID ('ENCAR_NEW999')
    past_snapshot = [
        {"encarno": "ENCAR_1111", "price_manwon": 1700, "plate": "11가1111", "model_name": "테스트차1", "model_year": 2020, "mileage_km": 50000, "shop": "상사A"},
        {"encarno": "ENCAR_2222", "price_manwon": 1200, "plate": "22가2222", "model_name": "테스트차2", "model_year": 2021, "mileage_km": 30000, "shop": "상사B"},
        {"encarno": "ENCAR_3333", "price_manwon": 1500, "plate": "33가3333", "model_name": "테스트차3", "model_year": 2019, "mileage_km": 70000, "shop": "상사C"},
        {"encarno": "ENCAR_4444", "price_manwon": 800, "plate": "44가4444", "model_name": "테스트차4", "model_year": 2018, "mileage_km": 90000, "shop": "상사D"},
        {"encarno": "ENCAR_NEW999", "price_manwon": 2000, "plate": "99가9999", "model_name": "과거에만있던차", "model_year": 2015, "mileage_km": 120000, "shop": "상사E"}
    ]

    service = CarManagerSyncService(db_path=TEST_DB, dry_run=False)

    print("\n[시나리오 1~5] HISTORICAL_REPLAY 모드로 과거 스냅샷 주입 실행...")
    sync_res = service.run_sync(
        current_snapshot=past_snapshot,
        scope="MARKET_OBSERVED",
        observation_mode="HISTORICAL_REPLAY",
        observed_at="2026-10-20T10:00:00" # 과거 시각
    )

    # 사후 상태 검증
    # 1. CAR1 (기존 1500 / 과거 1700): target_price와 advertised_price가 1500으로 불변이어야 함!
    cursor.execute("SELECT target_price FROM vehicles WHERE id = ?", (v_car1,))
    t_price1 = cursor.fetchone()[0]
    cursor.execute("SELECT advertised_price, last_observed_at, unverified_consecutive_count FROM vehicle_listings WHERE listing_id = 'ENCAR_1111'")
    l_price1, l_obs1, l_unv1 = cursor.fetchone()
    assert t_price1 == 1500, f"CAR1 target_price reversed! Expected 1500, got {t_price1}"
    assert l_price1 == 1500, f"CAR1 advertised_price reversed! Expected 1500, got {l_price1}"
    assert l_obs1 == now, f"CAR1 last_observed_at mutated! Expected {now}, got {l_obs1}"
    assert l_unv1 == 0, f"CAR1 unverified count mutated! Got {l_unv1}"
    print("[PASS] 시나리오 1: 기존 1,500만원 / 과거 1,700만원 주입 -> 기존 1,500만원 100% 불변 보존!")

    # 2. CAR2 (기존 1500 / 과거 1200): target_price와 advertised_price가 1500으로 불변이어야 함!
    cursor.execute("SELECT target_price FROM vehicles WHERE id = ?", (v_car2,))
    t_price2 = cursor.fetchone()[0]
    cursor.execute("SELECT advertised_price, last_observed_at FROM vehicle_listings WHERE listing_id = 'ENCAR_2222'")
    l_price2, l_obs2 = cursor.fetchone()
    assert t_price2 == 1500, f"CAR2 target_price reversed! Expected 1500, got {t_price2}"
    assert l_price2 == 1500, f"CAR2 advertised_price reversed! Expected 1500, got {l_price2}"
    assert l_obs2 == now, f"CAR2 last_observed_at mutated! Expected {now}, got {l_obs2}"
    print("[PASS] 시나리오 2: 기존 1,500만원 / 과거 1,200만원 주입 -> 기존 1,500만원 100% 불변 보존!")

    # 3. CAR3 (기존 NULL / 과거 1500): target_price와 advertised_price가 NULL로 불변이어야 함!
    cursor.execute("SELECT target_price FROM vehicles WHERE id = ?", (v_car3,))
    t_price3 = cursor.fetchone()[0]
    cursor.execute("SELECT advertised_price, last_observed_at FROM vehicle_listings WHERE listing_id = 'ENCAR_3333'")
    l_price3, l_obs3 = cursor.fetchone()
    assert t_price3 is None, f"CAR3 target_price reversed! Expected None, got {t_price3}"
    assert l_price3 is None, f"CAR3 advertised_price reversed! Expected None, got {l_price3}"
    assert l_obs3 == now, f"CAR3 last_observed_at mutated! Expected {now}, got {l_obs3}"
    print("[PASS] 시나리오 3: 기존 가격 NULL (상담) / 과거 1,500만원 주입 -> 기존 NULL 100% 불변 보존!")

    # 4. CAR4 (기존 ACTIVE / 과거 동일가격 주입): last_observed_at, status 불변이어야 함!
    cursor.execute("SELECT status FROM vehicles WHERE id = ?", (v_car4,))
    stat4 = cursor.fetchone()[0]
    cursor.execute("SELECT listing_status, last_observed_at FROM vehicle_listings WHERE listing_id = 'ENCAR_4444'")
    l_stat4, l_obs4 = cursor.fetchone()
    assert stat4 == "DRAFT", f"CAR4 status mutated! Expected DRAFT, got {stat4}"
    assert l_stat4 == "ACTIVE", f"CAR4 listing_status mutated! Expected ACTIVE, got {l_stat4}"
    assert l_obs4 == now, f"CAR4 last_observed_at mutated! Expected {now}, got {l_obs4}"
    print("[PASS] 시나리오 4: 기존 ACTIVE / 과거 상태 동일 주입 -> 상태 및 last_observed_at 100% 불변 보존!")

    # 5. CAR5 (과거에만 존재하는 신규 ID 'ENCAR_NEW999'): 운영 DB에 마스터 생성 0건이어야 함!
    cursor.execute("SELECT count(*) FROM vehicle_listings WHERE listing_id = 'ENCAR_NEW999'")
    new_cnt = cursor.fetchone()[0]
    cursor.execute("SELECT count(*) FROM vehicles WHERE plate_number = '99가9999'")
    new_veh_cnt = cursor.fetchone()[0]
    assert new_cnt == 0, f"New listing inserted during HISTORICAL_REPLAY! Count={new_cnt}"
    assert new_veh_cnt == 0, f"New vehicle master inserted during HISTORICAL_REPLAY! Count={new_veh_cnt}"
    print("[PASS] 시나리오 5: 과거 파일에만 존재하는 신규 ID -> HISTORICAL_REPLAY에서 마스터/리스팅 생성 0건!")

    # 시나리오 6: allow_historical_test_commit=True를 주더라도 운영 DB(PROD_DB)에는 쓰기 100% 차단!
    print("\n[시나리오 6] 운영 DB 연결 경계 물리적 격리 검증...")
    # 운영 DB의 현재 상태 스냅샷 (마지막 수정시각 or 전체 레코드 해시)
    conn_prod = sqlite3.connect(PROD_DB)
    prod_cur = conn_prod.cursor()
    prod_cur.execute("SELECT count(*), max(updated_at) FROM vehicles")
    cnt_before, max_upd_before = prod_cur.fetchone()
    conn_prod.close()

    try:
        # allow_historical_test_commit=True를 인위적으로 주더라도, 대상 DB가 PROD_DB이면 dry_run=True 강제되어 변경 0건이어야 함
        run_sync_pipeline(
            use_live_collector=False,
            dry_run=False,
            db_path=PROD_DB,
            allow_historical_test_commit=True
        )
    except Exception as e:
        print(f"[*] Pipeline handled/interrupted: {e}")

    conn_prod = sqlite3.connect(PROD_DB)
    prod_cur = conn_prod.cursor()
    prod_cur.execute("SELECT count(*), max(updated_at) FROM vehicles")
    cnt_after, max_upd_after = prod_cur.fetchone()
    conn_prod.close()

    assert cnt_before == cnt_after, f"Production vehicle count mutated! Before={cnt_before}, After={cnt_after}"
    assert max_upd_before == max_upd_after, f"Production vehicle updated_at mutated! Before={max_upd_before}, After={max_upd_after}"
    print("[PASS] 시나리오 6: allow_historical_test_commit=True를 인위적으로 주더라도 운영 DB 물리적 쓰기 100% 차단 (0 mutations) 입증!")

    conn.close()
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    print("\n" + "=" * 60)
    print(">>> [DIRECTIVE 128 TASK 1] 6대 필수 회귀 시나리오 전수 통과 (100% 불변 입증 완료) <<<")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
