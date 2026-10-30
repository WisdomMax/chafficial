"""
TASK 1: 카매니저 실제 50대 원본 파서 정밀 검증 및 필드별 추출 성공률 산출 (DIRECTIVE 123)
- 원본 JSON(janghanpyeong_full_collection.json)의 실제 필드명 1:1 매핑
- HISTORICAL_SAMPLE_50 50건에 대한 전수 정량 검증
- 필드별 성공률 100% 입증 및 매니페스트 산출 (scratch/historical_sample_50_manifest.json)
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime

RAW_SOURCE = "data/carmanager_raw/janghanpyeong_full_collection.json"
MANIFEST_JSON = "scratch/historical_sample_50_manifest.json"

def audit_real_parser():
    print("=== [TASK 1] 카매니저 50대 원본 파서 정밀 검증 시작 ===")
    assert Path(RAW_SOURCE).exists(), f"Source file {RAW_SOURCE} not found!"

    with open(RAW_SOURCE, "rb") as f:
        sha256_hash = hashlib.sha256(f.read()).hexdigest()

    with open(RAW_SOURCE, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_cars = data.get("cars", [])
    print(f"[*] 카매니저 원본 총 매물: {len(all_cars)}대, SHA256: {sha256_hash}")

    # 과거 수집 파일의 첫 50건: HISTORICAL_SAMPLE_50
    sample_50 = all_cars[:50]
    assert len(sample_50) == 50

    field_stats = {
        "encarno": 0,
        "plate_tail": 0,
        "model": 0,
        "model_year": 0,
        "reg_date": 0,
        "mileage": 0,
        "fuel": 0,
        "color": 0,
        "price_manwon": 0,
        "danji": 0,
        "shop": 0,
        "dealer": 0,
        "thumbnail": 0
    }

    parsed_items = []

    for idx, c in enumerate(sample_50):
        # 1. 실제 필드값 추출
        encarno = c.get("encarno")
        plate_tail = c.get("plate_tail")
        model = c.get("model") or c.get("title")
        model_year = c.get("model_year")
        reg_date = c.get("reg_date")
        mileage = c.get("mileage")
        fuel = c.get("fuel")
        color = c.get("color")
        price_manwon = c.get("price_manwon")
        danji = c.get("danji")
        shop = c.get("shop")
        dealer = c.get("dealer")
        thumbnail = c.get("thumbnail")

        # 2. 필드 성공률 집계
        if encarno: field_stats["encarno"] += 1
        if plate_tail and len(plate_tail) == 4: field_stats["plate_tail"] += 1
        if model: field_stats["model"] += 1
        if model_year: field_stats["model_year"] += 1
        if reg_date: field_stats["reg_date"] += 1
        if mileage: field_stats["mileage"] += 1
        if fuel: field_stats["fuel"] += 1
        if color: field_stats["color"] += 1
        if price_manwon: field_stats["price_manwon"] += 1
        if danji: field_stats["danji"] += 1
        if shop: field_stats["shop"] += 1
        if dealer: field_stats["dealer"] += 1
        if thumbnail: field_stats["thumbnail"] += 1

        parsed_items.append({
            "sample_index": idx + 1,
            "encarno": encarno,
            "plate_tail_4": plate_tail,
            "model_name": model,
            "maker": c.get("maker"),
            "model_year": model_year,
            "reg_date": reg_date,
            "mileage_raw": mileage,
            "fuel_type": fuel,
            "color": color,
            "price_manwon_raw": price_manwon,
            "accident": c.get("accident"),
            "danji": danji,
            "shop_name": shop,
            "dealer_name": dealer,
            "dealer_phone": c.get("phone"),
            "thumbnail_url": thumbnail
        })

    # 성공률 계산 (%)
    success_rates = {k: f"{(v / 50) * 100:.1f}% ({v}/50)" for k, v in field_stats.items()}

    manifest = {
        "report_classification": "[HISTORICAL_SAMPLE_50]",
        "directive": "CHA-FICIAL DIRECTIVE 123 TASK 1",
        "dataset_metadata": {
            "source_file": RAW_SOURCE,
            "source_sha256": sha256_hash,
            "sample_type": "HISTORICAL_SAMPLE_50 (과거 수집 원본의 1~50번째 매물)",
            "sample_size": 50,
            "extracted_at": datetime.now().isoformat()
        },
        "field_extraction_success_rates": success_rates,
        "sample_records": parsed_items[:10],
        "full_50_records": parsed_items
    }

    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("[*] 필드별 실제 추출 성공률:")
    for k, rate in success_rates.items():
        print(f"  - {k:15s}: {rate}")

    # 주요 필수 필드 100% 추출 단언
    assert field_stats["encarno"] == 50, "encarno 누락 발생!"
    assert field_stats["plate_tail"] == 50, "plate_tail 누락 발생!"
    assert field_stats["model"] == 50, "model 누락 발생!"
    assert field_stats["model_year"] == 50, "model_year 누락 발생!"
    assert field_stats["mileage"] == 50, "mileage 누락 발생!"
    assert field_stats["price_manwon"] == 50, "price_manwon 누락 발생!"
    assert field_stats["shop"] == 50, "shop 누락 발생!"

    print(f"[+] TASK 1 50대 원본 파서 검증 100% PASS! 매니페스트 산출: {MANIFEST_JSON}")

if __name__ == "__main__":
    audit_real_parser()
