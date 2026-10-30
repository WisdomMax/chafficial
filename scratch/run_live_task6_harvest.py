import asyncio
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, "src")
from chaficial.platform.sourcing.janghanpyeong_collector import JanghanpyeongCollector
from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine
from chaficial.platform.sourcing.normalizer import normalize_carmanager_record

async def run_live_harvest():
    print("================================================================================")
    print(" DIRECTIVE 111 - TASK 6: 카매니저 최신 실매물 실시간 라이브 전수 수집 및 적재")
    print("================================================================================")

    collector = JanghanpyeongCollector()
    t_start = datetime.now().isoformat()
    print(f"[*] Starting Live Traversal at {t_start}...")

    # 실시간 크롤링 실행 (89페이지 전체 순회)
    res = await collector.run_full_collection(max_pages=89, throttle_sec=0.35)
    t_end = datetime.now().isoformat()

    cars = res.get("cars", [])
    total_found = res.get("total_found")
    max_pages = res.get("max_pages")
    is_complete = res.get("is_complete", False)
    failed_pages = res.get("failed_pages", [])

    print(f"\n[+] Live Harvest Finished at {t_end}")
    print(f"    - Total Found: {total_found}")
    print(f"    - Total Collected Cars: {len(cars)}")
    print(f"    - Max Pages: {max_pages}")
    print(f"    - Failed Pages: {failed_pages}")
    print(f"    - Is Complete: {is_complete}")

    assert is_complete, f"Harvest must be verified complete! Failed pages: {failed_pages}"

    # 공통 정규화 계층으로 필드 검증
    priced_count = 0
    consult_count = 0
    zero_price_distortion = 0
    valid_model_count = 0
    valid_year_count = 0
    valid_shop_count = 0

    for c in cars:
        norm = normalize_carmanager_record(c)
        if norm["price_manwon"] is not None:
            if norm["price_manwon"] == 0:
                zero_price_distortion += 1
            else:
                priced_count += 1
        else:
            consult_count += 1

        if norm["model_name"]:
            valid_model_count += 1
        if norm["model_year"]:
            valid_year_count += 1
        if norm["shop_name"]:
            valid_shop_count += 1

    print("\n[*] Live Harvest Data Quality Stats:")
    print(f"    * Valid Priced Cars: {priced_count} ({priced_count/len(cars)*100:.1f}%)")
    print(f"    * Unpriced / Consultation Required: {consult_count} ({consult_count/len(cars)*100:.1f}%)")
    print(f"    * ZERO Price Distortion (0원 무료 왜곡): {zero_price_distortion} (100% Zero Safe)")
    print(f"    * Valid Model Names: {valid_model_count} ({valid_model_count/len(cars)*100:.1f}%)")
    print(f"    * Valid Model Years: {valid_year_count} ({valid_year_count/len(cars)*100:.1f}%)")
    print(f"    * Valid Shop Names: {valid_shop_count} ({valid_shop_count/len(cars)*100:.1f}%)")

    assert zero_price_distortion == 0
    assert valid_model_count == len(cars)
    assert valid_year_count == len(cars)
    assert valid_shop_count == len(cars)

    # 시계열 엔진에 최신 라이브 관측 적재
    db_path = "data/chamart/chamart_platform_demo.db"
    engine = MarketTimeSeriesEngine(db_path=db_path, dry_run=False)
    live_run_id = str(uuid.uuid4())

    ts_res = engine.record_snapshot(
        snapshot_cars=cars,
        started_at=t_start,
        finished_at=t_end,
        source="CARMANAGER",
        search_condition="장안평/성동구(1104,1105,1230)",
        total_found=total_found,
        pages_collected=max_pages,
        run_id=live_run_id,
        dry_run=False
    )
    print(f"\n[+] Live TimeSeries Ingestion Result: Status={ts_res['status']}, RunID={ts_res['run_id']}")
    print(f"    - Observations Stored: {ts_res['observations_count']}")
    print(f"    - Events Count: {ts_res['events_count']}")

    # 무작위 30대 추출하여 원본과 DB 일치 여부 대조
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT encarno, price_manwon, model_name, model_year, shop_name, mileage_km 
        FROM market_listing_observations 
        WHERE run_id = ?
    """, (live_run_id,))
    db_rows = c.fetchall()

    raw_car_map = {car["encarno"]: car for car in cars if "encarno" in car}
    import random
    random.seed(42)
    sample_30 = random.sample(db_rows, min(30, len(db_rows)))

    print("\n[*] Auditing 30 Random Samples from Live Ingestion:")
    match_count = 0
    sample_audit = []
    for r in sample_30:
        raw_c = raw_car_map[r[0]]
        norm_exp = normalize_carmanager_record(raw_c)
        is_match = (
            r[1] == norm_exp["price_manwon"] and
            r[2] == norm_exp["model_name"] and
            r[3] == norm_exp["model_year"] and
            r[4] == norm_exp["shop_name"] and
            r[5] == norm_exp["mileage_km"]
        )
        if is_match:
            match_count += 1
        detail = {
            "encarno": r[0][:15] + "..",
            "model": r[2],
            "price": f"{r[1]}만원" if r[1] is not None else "상담(미공개)",
            "year": r[3],
            "shop": r[4],
            "km": f"{r[5]}km",
            "match": is_match
        }
        sample_audit.append(detail)
        print(f"  * [{detail['encarno']}] Model={detail['model'][:25]} | Price={detail['price']} | Year={detail['year']} | Match={is_match}")

    conn.close()

    print(f"\n[+] 30 Random Samples Match Rate: {match_count}/30 (100.0%)")
    assert match_count == 30

    evidence = {
        "live_harvest_started": t_start,
        "live_harvest_finished": t_end,
        "run_id": live_run_id,
        "total_found": total_found,
        "pages_collected": max_pages,
        "total_cars": len(cars),
        "priced_cars_count": priced_count,
        "consult_cars_count": consult_count,
        "zero_price_distortion": zero_price_distortion,
        "valid_models_count": valid_model_count,
        "valid_years_count": valid_year_count,
        "valid_shops_count": valid_shop_count,
        "samples_match_rate": f"{match_count}/30 (100.0%)",
        "sample_audit": sample_audit
    }
    with open("scratch/directive_111_live_harvest_evidence.json", "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)

    print("\n[+] Evidence saved to scratch/directive_111_live_harvest_evidence.json")

if __name__ == "__main__":
    asyncio.run(run_live_harvest())
