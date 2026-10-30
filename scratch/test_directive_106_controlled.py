import os
import sqlite3
import shutil
import json
import unittest
from datetime import datetime
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService, parse_price_manwon, parse_mileage_km, parse_plate_info

TEST_DB_PATH = "data/chamart/test_directive_106_controlled.db"
ORIGINAL_DB_PATH = "data/chamart/chamart_platform_demo.db"

def run_controlled_10_experiments():
    print("================================================================================")
    print("[*] TASK 5: Executing 10 Controlled Isolation Experiments (DIRECTIVE 106)")
    print("================================================================================")

    # 1. 독립 테스트 DB 준비 (운영 DB 복제본)
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    shutil.copyfile(ORIGINAL_DB_PATH, TEST_DB_PATH)

    service = CarManagerSyncService(db_path=TEST_DB_PATH)
    conn = sqlite3.connect(TEST_DB_PATH)
    c = conn.cursor()

    # 테스트 기준 차량 1대 선정 (더쿨모터스 차량)
    c.execute("""
        SELECT l.listing_id, v.id, v.target_price, v.plate_number, v.mileage, v.status
        FROM vehicle_listings l
        JOIN vehicles v ON l.vehicle_id = v.id
        WHERE v.listing_ownership_type = 'OWNED' AND v.target_price > 0
        LIMIT 1
    """)
    t_car = c.fetchone()
    test_listing_id = t_car[0]
    test_v_id = t_car[1]
    orig_price = t_car[2]
    print(f"[*] Base Test Vehicle: {test_v_id} | Listing: {test_listing_id} | Orig Price: {orig_price}만원")

    results = {}

    # ---------------------------------------------------------
    # 실험 1: 가격 단위 혼용 테스트 (1,500만원 vs 15,000,000원 -> 모두 1,500 저장)
    # ---------------------------------------------------------
    p_won = parse_price_manwon(15000000)
    p_man = parse_price_manwon(1500)
    p_str = parse_price_manwon("1,500")
    assert p_won == 1500 and p_man == 1500 and p_str == 1500
    results["EXP_01_PRICE_UNIT_MIX"] = {
        "pass": True,
        "detail": f"15,000,000원 -> {p_won}만원, 1,500만원 -> {p_man}만원, '1,500' -> {p_str}만원 완벽 일치"
    }

    # ---------------------------------------------------------
    # 실험 2: 실제 가격 변경 테스트 (1,500만원 -> 1,400만원 정상 인하 감지)
    # ---------------------------------------------------------
    c.execute("UPDATE vehicles SET target_price = 1500 WHERE id = ?", (test_v_id,))
    c.execute("UPDATE vehicle_listings SET advertised_price = 1500 WHERE listing_id = ?", (test_listing_id,))
    conn.commit()

    snap_exp2 = [{
        "encarno": test_listing_id,
        "price_manwon": 1400,
        "plate": "12가3456",
        "clean_title": "테스트 차량",
        "model_year": 2023,
        "mileage": "30,000km"
    }]
    res2 = service.run_sync(snap_exp2, scope="OWNED", min_expected_count=1)
    
    c.execute("SELECT target_price FROM vehicles WHERE id = ?", (test_v_id,))
    new_price = c.fetchone()[0]
    c.execute("SELECT advertised_price FROM vehicle_listings WHERE listing_id = ?", (test_listing_id,))
    new_adv_price = c.fetchone()[0]
    
    assert res2["price_changed"] == 1 and new_price == 1400 and new_adv_price == 1400
    results["EXP_02_PRICE_CHANGE_DETECTION"] = {
        "pass": True,
        "detail": f"1500만원 -> 1400만원 정상 감지 (target: {new_price}만원, advertised: {new_adv_price}만원)"
    }

    # ---------------------------------------------------------
    # 실험 3: 관리자 가격 잠금 테스트 (is_price_locked = True 시 외부 가격 무시)
    # ---------------------------------------------------------
    c.execute("UPDATE vehicles SET condition_detail_json = json_set(COALESCE(condition_detail_json, '{}'), '$.is_price_locked', 1) WHERE id = ?", (test_v_id,))
    conn.commit()

    snap_exp3 = [{
        "encarno": test_listing_id,
        "price_manwon": 1200, # 외부에서 1200으로 변경 시도
        "plate": "12가3456"
    }]
    res3 = service.run_sync(snap_exp3, scope="OWNED", min_expected_count=1)

    c.execute("SELECT target_price, timeline_json FROM vehicles WHERE id = ?", (test_v_id,))
    locked_row = c.fetchone()
    assert res3["price_changed"] == 0 and locked_row[0] == 1400 and "SYNC_PRICE_SKIPPED_ADMIN_PRICE_LOCK" in locked_row[1]
    results["EXP_03_ADMIN_PRICE_LOCK"] = {
        "pass": True,
        "detail": f"1200만원 인하 시도 무시, 1400만원 및 잠금 타임라인 정상 보존 (SQL locked_price: {locked_row[0]})"
    }

    # 잠금 해제 복구
    c.execute("UPDATE vehicles SET condition_detail_json = json_set(condition_detail_json, '$.is_price_locked', 0) WHERE id = ?", (test_v_id,))
    conn.commit()

    # ---------------------------------------------------------
    # 실험 4: 주행거리 '만 km' 변환 테스트
    # ---------------------------------------------------------
    km1 = parse_mileage_km("5.5만 km")
    km2 = parse_mileage_km("12.3만km")
    km3 = parse_mileage_km("55,000km")
    km4 = parse_mileage_km(None)
    assert km1 == 55000 and km2 == 123000 and km3 == 55000 and km4 is None
    results["EXP_04_MILEAGE_PARSING"] = {
        "pass": True,
        "detail": f"'5.5만 km' -> {km1}km, '12.3만km' -> {km2}km, '55,000km' -> {km3}km, None -> {km4}"
    }

    # ---------------------------------------------------------
    # 실험 5: 전체 차량번호 누락 테스트 (끝 4자리만 유입 시 plate_number=None)
    # ---------------------------------------------------------
    dummy_encarno_tail = "EXP05_TAIL_ONLY"
    snap_exp5 = [{
        "encarno": dummy_encarno_tail,
        "plate": "1234", # 끝 4자리만
        "price_manwon": 2000,
        "clean_title": "끝번호 차량"
    }]
    res5 = service.run_sync(snap_exp5, scope="OWNED", min_expected_count=1)
    
    c.execute("""
        SELECT v.plate_number, l.observation_notes 
        FROM vehicles v JOIN vehicle_listings l ON v.id = l.vehicle_id 
        WHERE l.listing_id = ?
    """, (dummy_encarno_tail,))
    exp5_row = c.fetchone()
    assert exp5_row[0] == "UNVERIFIED" and "끝번호: 1234" in exp5_row[1]
    results["EXP_05_INCOMPLETE_PLATE_PROTECTION"] = {
        "pass": True,
        "detail": f"끝 4자리(1234) 입력 시 plate_number='UNVERIFIED' 미확인 안전 보존, observation_notes에 '{exp5_row[1]}' 기록"
    }

    # ---------------------------------------------------------
    # 실험 6: 목록 일부 페이지 실패 테스트 (스냅샷 수량 미달 시 delisting 방지)
    # ---------------------------------------------------------
    c.execute("SELECT unverified_consecutive_count FROM vehicle_listings WHERE listing_id != ? AND platform='CARMANAGER' LIMIT 1", (test_listing_id,))
    unv_before = c.fetchone()[0]

    # 전체 OWNED가 85대인데, 스크랩 실패로 1대만 넘어왔을 때(min_expected_count=50) 누락 카운트 증가 방지
    res6 = service.run_sync([{"encarno": test_listing_id, "price_manwon": 1400}], scope="OWNED", min_expected_count=50)
    c.execute("SELECT unverified_consecutive_count FROM vehicle_listings WHERE listing_id != ? AND platform='CARMANAGER' LIMIT 1", (test_listing_id,))
    unv_after = c.fetchone()[0]
    assert res6["unverified_count"] == 0 and unv_before == unv_after
    results["EXP_06_SCRAPE_FAILURE_DELIST_GUARD"] = {
        "pass": True,
        "detail": f"수집량 1건 < min_expected_count(50) -> 미출현 차량 카운트 누적 중단(unverified_count: 0, count유지: {unv_before}->{unv_after}) 안전 방어"
    }

    # ---------------------------------------------------------
    # 실험 7: 3회 연속 누락 및 재등장 테스트
    # ---------------------------------------------------------
    dummy_delist_id = "EXP07_DELIST_REAPPEAR"
    # 등록
    service.run_sync([{"encarno": dummy_delist_id, "price_manwon": 1500, "plate": "77가7777"}], scope="OWNED", min_expected_count=1)
    
    # 1회 누락
    service.run_sync([], scope="OWNED", min_expected_count=0)
    c.execute("SELECT unverified_consecutive_count, listing_status FROM vehicle_listings WHERE listing_id = ?", (dummy_delist_id,))
    cnt1, stat1 = c.fetchone()
    
    # 2회 누락
    service.run_sync([], scope="OWNED", min_expected_count=0)
    # 3회 누락 -> DELISTED 전환
    service.run_sync([], scope="OWNED", min_expected_count=0)
    c.execute("SELECT unverified_consecutive_count, listing_status FROM vehicle_listings WHERE listing_id = ?", (dummy_delist_id,))
    cnt3, stat3 = c.fetchone()

    # 재등장! -> 다시 스냅샷에 포함되면 unverified=0 리셋
    service.run_sync([{"encarno": dummy_delist_id, "price_manwon": 1500, "plate": "77가7777"}], scope="OWNED", min_expected_count=1)
    c.execute("SELECT unverified_consecutive_count, listing_status FROM vehicle_listings WHERE listing_id = ?", (dummy_delist_id,))
    cnt_re, stat_re = c.fetchone()

    assert cnt1 == 1 and cnt3 == 3 and stat3 == "DELISTED" and cnt_re == 0
    results["EXP_07_CONSECUTIVE_DELIST_AND_REAPPEAR"] = {
        "pass": True,
        "detail": f"1회누락({cnt1}회) -> 3회누락({cnt3}회, {stat3}) -> 재등장 복구({cnt_re}회 리셋) 완벽 통과"
    }

    # ---------------------------------------------------------
    # 실험 8: 실제 SOLD 확인 테스트 (sold_snapshot 명시 전달)
    # ---------------------------------------------------------
    dummy_sold_id = "EXP08_REAL_SOLD"
    service.run_sync([{"encarno": dummy_sold_id, "price_manwon": 1800, "plate": "88가8888"}], scope="OWNED", min_expected_count=1)
    
    # 카매니저 명시적 판매완료 스냅샷 유입
    res8 = service.run_sync([], sold_snapshot=[{"encarno": dummy_sold_id}], scope="OWNED", min_expected_count=0)
    c.execute("""
        SELECT v.status, v.is_public, l.listing_status 
        FROM vehicles v JOIN vehicle_listings l ON v.id = l.vehicle_id 
        WHERE l.listing_id = ?
    """, (dummy_sold_id,))
    v_stat, is_pub, l_stat = c.fetchone()
    assert res8["sold_count"] == 1 and v_stat == "SOLD" and is_pub == 0 and l_stat == "SOLD"
    results["EXP_08_EXPLICIT_SOLD_DETECTION"] = {
        "pass": True,
        "detail": f"명시적 sold_snapshot 유입 시 status='SOLD', is_public=0, listing_status='SOLD' 정상 전환"
    }

    # ---------------------------------------------------------
    # 실험 9: 동일 스냅샷 재실행 멱등성 테스트 (변동 0건)
    # ---------------------------------------------------------
    idemp_snap = [{"encarno": test_listing_id, "price_manwon": 1400, "plate": "12가3456"}]
    res9_1 = service.run_sync(idemp_snap, scope="OWNED", min_expected_count=1)
    res9_2 = service.run_sync(idemp_snap, scope="OWNED", min_expected_count=1)
    assert res9_2["new_inserted"] == 0 and res9_2["price_changed"] == 0 and res9_2["sold_count"] == 0 and res9_2["unchanged_count"] == 1
    results["EXP_09_IDEMPOTENCY"] = {
        "pass": True,
        "detail": f"동일 스냅샷 2회차 실행 시 new=0, price_changed=0, sold=0, unchanged=1 완벽한 멱등성 유지"
    }

    # ---------------------------------------------------------
    # 실험 10: 스코프별 OWNED / MARKET 상호 격리 보호 테스트
    # ---------------------------------------------------------
    c.execute("SELECT count(*) FROM vehicles WHERE listing_ownership_type = 'MARKET_JANGHANPYEONG'")
    market_count_before = c.fetchone()[0]

    # OWNED 스코프로 동기화 실행
    service.run_sync(idemp_snap, scope="OWNED", min_expected_count=1)

    c.execute("SELECT count(*) FROM vehicles WHERE listing_ownership_type = 'MARKET_JANGHANPYEONG'")
    market_count_after = c.fetchone()[0]
    assert market_count_before == market_count_after
    results["EXP_10_SCOPE_ISOLATION_PROTECTION"] = {
        "pass": True,
        "detail": f"OWNED 동기화 시 MARKET_JANGHANPYEONG 매물({market_count_before}대) 영향 0건 완벽 격리"
    }

    conn.close()

    # 테스트 DB 정리
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    print("\n[+] 10 Controlled Isolation Experiments Results:")
    for k, v in results.items():
        print(f"  * [{k}]: PASS={v['pass']} -> {v['detail']}")

    print("================================================================================")
    print("[+] ALL 10 CONTROLLED EXPERIMENTS 100% PASSED & VERIFIED VIA SQL!")
    print("================================================================================")

if __name__ == "__main__":
    run_controlled_10_experiments()
