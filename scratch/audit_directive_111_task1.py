import sqlite3
import json
import random
from pathlib import Path

def audit_task1():
    print("================================================================================")
    print(" DIRECTIVE 111 - TASK 1: 기존 1,764건 시계열 데이터 품질 전수 감사")
    print("================================================================================")

    db_path = "data/chamart/chamart_platform_demo.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. SQL 통계 집계
    c.execute("SELECT COUNT(*) FROM market_listing_observations")
    total_obs = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM market_listing_observations WHERE price_manwon = 0 OR price_manwon IS NULL")
    zero_price_cnt = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM market_listing_observations WHERE model_name IS NULL OR model_name = ''")
    null_model_cnt = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM market_listing_observations WHERE model_year IS NULL")
    null_year_cnt = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM market_listing_observations WHERE shop_name IS NULL OR shop_name = ''")
    null_shop_cnt = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM market_listing_observations WHERE mileage_km IS NULL")
    null_mileage_cnt = c.fetchone()[0]

    c.execute("SELECT COUNT(DISTINCT encarno) FROM market_listing_observations")
    distinct_encarno_cnt = c.fetchone()[0]

    print(f"[*] Total Observations: {total_obs}")
    print(f"[-] Zero Price (0만원) Count: {zero_price_cnt} ({zero_price_cnt/max(1, total_obs)*100:.1f}%)")
    print(f"[-] NULL Model Count: {null_model_cnt} ({null_model_cnt/max(1, total_obs)*100:.1f}%)")
    print(f"[-] NULL Year Count: {null_year_cnt} ({null_year_cnt/max(1, total_obs)*100:.1f}%)")
    print(f"[-] NULL Shop Name Count: {null_shop_cnt} ({null_shop_cnt/max(1, total_obs)*100:.1f}%)")
    print(f"[+] NULL Mileage Count: {null_mileage_cnt} ({null_mileage_cnt/max(1, total_obs)*100:.1f}%)")
    print(f"[*] Distinct Encarno Count: {distinct_encarno_cnt}")

    # 2. 원본 JSON 로드
    raw_path = Path("data/carmanager_raw/janghanpyeong_full_collection.json")
    with open(raw_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    raw_cars = {c["encarno"]: c for c in raw_data.get("cars", []) if "encarno" in c}

    # 3. 무작위 표본 30대 추출하여 원본과 DB 대조
    c.execute("SELECT encarno, price_manwon, model_name, model_year, shop_name, mileage_km FROM market_listing_observations")
    all_db_rows = c.fetchall()
    
    random.seed(42)
    sample_rows = random.sample(all_db_rows, min(30, len(all_db_rows)))
    
    audit_samples = []
    print("\n[*] Random 30 Samples Comparison (Raw vs DB):")
    for r in sample_rows:
        enc = r[0]
        raw_c = raw_cars.get(enc, {})
        raw_price = raw_c.get("price_manwon")
        raw_model = raw_c.get("model")
        raw_year = raw_c.get("model_year")
        raw_shop = raw_c.get("shop")
        raw_km = raw_c.get("mileage")

        diff = {
            "encarno": enc[:15] + "..",
            "price": f"DB={r[1]}만원 vs RAW={raw_price}만원",
            "model": f"DB={r[2]} vs RAW={raw_model[:20] if raw_model else None}",
            "year": f"DB={r[3]} vs RAW={raw_year}",
            "shop": f"DB={r[4]} vs RAW={raw_shop}",
            "km": f"DB={r[5]}km vs RAW={raw_km}"
        }
        audit_samples.append(diff)
        print(f"  * [{diff['encarno']}] Price: {diff['price']} | Model: {diff['model']} | Year: {diff['year']}")

    conn.close()

    result = {
        "total_observations": total_obs,
        "zero_price_count": zero_price_cnt,
        "null_model_count": null_model_cnt,
        "null_year_count": null_year_cnt,
        "null_shop_count": null_shop_cnt,
        "null_mileage_count": null_mileage_cnt,
        "distinct_encarnos": distinct_encarno_cnt,
        "sample_comparisons": audit_samples
    }
    with open("scratch/directive_111_task1_audit_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n[+] Audit result written to scratch/directive_111_task1_audit_result.json")

if __name__ == "__main__":
    audit_task1()
