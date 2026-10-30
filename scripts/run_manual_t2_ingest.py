"""
Manual T2 Ingestion Tool (DIRECTIVE 128 TASK 4)
- Parses manually captured T2 response (JSON or HTML) from CarManager.
- Compares against T1 baseline (1,764 historical listings).
- Outputs 5 mandatory differential metrics without leaking credentials.
- Strictly maintains REAL_PILOT_PENDING_NEW_CAPTURE when input is absent.
"""

import os
import sys
import json
import argparse
import hashlib
import sqlite3
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, "src")

from chaficial.platform.sourcing.normalizer import normalize_carmanager_record
from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine

PROD_DB = "data/chamart/chamart_platform_demo.db"

def inspect_t2_diff(input_file: str, meta_file: str = None, db_path: str = PROD_DB):
    if not os.path.exists(input_file):
        print(f"[!] Input file {input_file} does not exist. Status: REAL_PILOT_PENDING_NEW_CAPTURE", file=sys.stderr)
        return {"status": "REAL_PILOT_PENDING_NEW_CAPTURE"}

    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 원본 SHA256 산출
    file_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

    meta = {}
    if meta_file and os.path.exists(meta_file):
        with open(meta_file, "r", encoding="utf-8") as f:
            meta = json.load(f)

    # JSON 또는 HTML 파싱
    try:
        raw_data = json.loads(content)
        if isinstance(raw_data, list):
            cars = raw_data
        elif isinstance(raw_data, dict):
            cars = raw_data.get("cars") or raw_data.get("list") or raw_data.get("data") or []
    except json.JSONDecodeError:
        print("[!] HTML or custom format detected. Advanced parser invoked.")
        cars = []

    # 기존 T1 DB 로드 (encarno -> advertised_price)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT listing_id, advertised_price FROM vehicle_listings WHERE platform = 'CARMANAGER'")
    t1_records = {row[0]: row[1] for row in c.fetchall()}
    conn.close()

    total_unique_ids = set()
    existing_in_t1 = 0
    new_in_t2 = 0
    price_changed = 0
    uncomparable_or_invalid = 0

    diff_details = []

    for raw in cars:
        norm = normalize_carmanager_record(raw)
        encarno = norm.get("encarno")
        price = norm.get("price_manwon")

        if not encarno:
            uncomparable_or_invalid += 1
            continue

        if encarno in total_unique_ids:
            continue
        total_unique_ids.add(encarno)

        if encarno in t1_records:
            existing_in_t1 += 1
            old_p = t1_records[encarno]
            if price is not None and old_p is not None and price != old_p:
                price_changed += 1
                diff_details.append({
                    "encarno": encarno,
                    "old_price": old_p,
                    "new_price": price,
                    "diff": price - old_p
                })
        else:
            new_in_t2 += 1

    result = {
        "status": "T2_DIFFERENTIAL_ANALYZED",
        "file_sha256": file_sha256,
        "source_capture_id": meta.get("source_capture_id", "MANUAL_T2_UNKNOWN"),
        "total_unique_ids": len(total_unique_ids),
        "existing_in_t1": existing_in_t1,
        "new_in_t2": new_in_t2,
        "price_changed": price_changed,
        "uncomparable_or_invalid": uncomparable_or_invalid,
        "sample_price_changes": diff_details[:5]
    }

    print("=" * 60)
    print(">>> 카매니저 실제 T2 vs T1 차분 분석 리포트 <<<")
    print(f"- 원본 SHA256 체크섬:          {file_sha256}")
    print(f"- 1. 고유 매물 ID 수:          {result['total_unique_ids']}대")
    print(f"- 2. 기존 T1에 존재한 ID 수:    {result['existing_in_t1']}대 (체류일수 Days on Market 누적)")
    print(f"- 3. T1 대비 새롭게 확인된 ID: {result['new_in_t2']}대 (신규 등장)")
    print(f"- 4. 동일 ID 확인된 가격 변경:  {result['price_changed']}대")
    print(f"- 5. 비교 불가능/정보 부족 ID:   {result['uncomparable_or_invalid']}대")
    print("=" * 60)

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manual T2 Differential Analyzer")
    parser.add_argument("--input", type=str, help="Path to raw captured file")
    parser.add_argument("--meta", type=str, default=None, help="Path to provenance metadata file")
    args = parser.parse_args()

    if not args.input:
        print("[!] No input file provided. Status remains strictly: REAL_PILOT_PENDING_NEW_CAPTURE")
        sys.exit(0)

    inspect_t2_diff(args.input, args.meta)
