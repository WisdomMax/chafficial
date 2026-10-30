"""
Manual T2 Ingestion and Baseline Differential Analyzer (DIRECTIVE 129)
- Strictly parses verified JSON responses from CarManager.
- Explicitly rejects HTML or unsupported formats as UNSUPPORTED_FORMAT.
- Requires provenance metadata (source_capture_id, source_capture_at, observation_scope, sha256).
- Compares against fixed T1 baseline (1,764 historical listings in janghanpyeong_full_collection.json).
- Zero database writes (100% read-only audit tool).
- Strictly outputs REAL_PILOT_PENDING_NEW_CAPTURE when real inputs are absent.
"""

import os
import sys
import json
import argparse
import hashlib
from typing import Dict, Any, Optional

sys.path.insert(0, ".")
sys.path.insert(0, "src")

from chaficial.platform.sourcing.normalizer import normalize_carmanager_record

FIXED_T1_BASELINE_JSON = "data/carmanager_raw/janghanpyeong_full_collection.json"

def compute_file_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def analyze_t2_differential(
    input_file: Optional[str] = None,
    meta_file: Optional[str] = None,
    baseline_json: str = FIXED_T1_BASELINE_JSON
) -> Dict[str, Any]:
    # 1. 파일 부재 시 정직하게 대기 상태 반환
    if not input_file or not os.path.exists(input_file):
        print(f"[!] Target input file '{input_file}' not found. Current status: REAL_PILOT_PENDING_NEW_CAPTURE", file=sys.stderr)
        return {
            "status": "REAL_PILOT_PENDING_NEW_CAPTURE",
            "message": "Real T2 capture file is absent. Standing by for operator manual capture handoff."
        }

    # 2. 파일 무결성 해시 계산
    actual_sha256 = compute_file_sha256(input_file)

    # 3. 메타데이터 검증
    if not meta_file or not os.path.exists(meta_file):
        print(f"[!] Provenance metadata file '{meta_file}' is missing. Rejected.", file=sys.stderr)
        return {
            "status": "INVALID_METADATA",
            "error": "Provenance metadata file is required (capture_id, capture_at, scope, expected_sha256)."
        }

    with open(meta_file, "r", encoding="utf-8") as f:
        try:
            meta = json.load(f)
        except Exception as e:
            return {"status": "INVALID_METADATA", "error": f"Metadata JSON parse failed: {e}"}

    required_meta_fields = ["source_capture_id", "source_capture_at", "observation_scope"]
    missing_fields = [k for k in required_meta_fields if not meta.get(k)]
    if missing_fields:
        return {
            "status": "INVALID_METADATA",
            "error": f"Missing mandatory metadata fields: {missing_fields}"
        }

    # SHA256 필수값 검증 및 일치 여부 대조 (건너뛰기 원천 차단)
    expected_sha256 = meta.get("raw_sha256") or meta.get("expected_sha256")
    if not expected_sha256:
        return {
            "status": "MISSING_SHA256",
            "error": "Metadata must explicitly provide expected raw_sha256 checksum."
        }
    if expected_sha256.lower() != actual_sha256.lower():
        return {
            "status": "HASH_MISMATCH",
            "error": f"File SHA256 ({actual_sha256}) does not match expected metadata ({expected_sha256})."
        }

    # 4. 입력 포맷 검증 (HTML 등 미지원 포맷 명시적 거부)
    with open(input_file, "r", encoding="utf-8", errors="replace") as f:
        first_chunk = f.read(2048).strip()

    if first_chunk.startswith("<") or "<html" in first_chunk.lower() or "<table" in first_chunk.lower():
        print("[!] HTML format detected without verified DOM row extractor. Rejected as UNSUPPORTED_FORMAT.", file=sys.stderr)
        return {
            "status": "UNSUPPORTED_FORMAT",
            "error": "HTML input is not supported until verified structural parser is approved. JSON response required."
        }

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            raw_parsed = json.load(f)
    except Exception as e:
        return {
            "status": "UNSUPPORTED_FORMAT",
            "error": f"JSON parsing failed: {e}. Raw response must be valid JSON."
        }

    # JSON 내부의 차량 목록 배열 추출
    cars_raw = []
    if isinstance(raw_parsed, list):
        cars_raw = raw_parsed
    elif isinstance(raw_parsed, dict):
        cars_raw = raw_parsed.get("cars") or raw_parsed.get("list") or raw_parsed.get("data") or []

    if not cars_raw or len(cars_raw) == 0:
        return {
            "status": "NO_VALID_LISTINGS_EXTRACTED",
            "error": "Zero vehicles extracted from JSON input. Cannot process empty listing."
        }

    # 5. T1 불변 기준선 로드 (data/carmanager_raw/janghanpyeong_full_collection.json)
    if not os.path.exists(baseline_json):
        return {
            "status": "BASELINE_NOT_FOUND",
            "error": f"Fixed T1 baseline file '{baseline_json}' not found."
        }

    with open(baseline_json, "r", encoding="utf-8") as f:
        t1_data = json.load(f)
    t1_cars = t1_data.get("cars", [])

    t1_baseline_map = {}
    for c in t1_cars:
        norm_t1 = normalize_carmanager_record(c)
        enc = norm_t1.get("encarno")
        if enc:
            t1_baseline_map[enc] = {
                "price_manwon": norm_t1.get("price_manwon"),
                "model_name": norm_t1.get("model_name"),
                "plate": norm_t1.get("plate")
            }

    # 6. 정밀 차분 대조
    seen_encarnos = set()
    matched_in_t1 = 0
    new_to_baseline = 0
    price_changed = 0
    price_consultation_unannounced = 0
    price_missing_corrupt = 0
    invalid_or_uncomparable = 0

    diff_details = []

    for raw in cars_raw:
        norm = normalize_carmanager_record(raw)
        enc = norm.get("encarno")
        price = norm.get("price_manwon")

        if not enc:
            invalid_or_uncomparable += 1
            continue

        if enc in seen_encarnos:
            continue
        seen_encarnos.add(enc)

        # [DIRECTIVE 129 보정]: 실제 가격 미공개('상담')와 가격 필드 누락/파싱 불가 구분
        raw_price_val = raw.get("price") or raw.get("price_manwon") or raw.get("raw_price_str")
        if price is None:
            if raw_price_val is None or str(raw_price_val).strip() == "":
                price_missing_corrupt += 1
            else:
                price_consultation_unannounced += 1

        if enc in t1_baseline_map:
            matched_in_t1 += 1
            old_price = t1_baseline_map[enc]["price_manwon"]
            if price is not None and old_price is not None and price != old_price:
                price_changed += 1
                diff_details.append({
                    "encarno": enc,
                    "model_name": norm.get("model_name"),
                    "old_price_manwon": old_price,
                    "new_price_manwon": price,
                    "delta_manwon": price - old_price
                })
        else:
            new_to_baseline += 1

    report = {
        "status": "SUCCESS_T2_ANALYZED",
        "provenance": {
            "source_capture_id": meta.get("source_capture_id"),
            "source_capture_at": meta.get("source_capture_at"),
            "observation_scope": meta.get("observation_scope"),
            "raw_sha256": actual_sha256,
            "is_partial_observation": True # 50대 목록은 항상 부분 관측으로 취급
        },
        "metrics": {
            "total_valid_listings": len(seen_encarnos),
            "matched_in_t1_count": matched_in_t1,
            "new_to_baseline_count": new_to_baseline,
            "price_changed_count": price_changed,
            "price_consultation_unannounced_count": price_consultation_unannounced,
            "price_missing_corrupt_count": price_missing_corrupt,
            "invalid_or_uncomparable_count": invalid_or_uncomparable
        },
        "sample_price_changes": diff_details[:10]
    }

    print("=" * 65)
    print(">>> [DIRECTIVE 129] 카매니저 실매물 T2 vs T1 차분 분석 리포트 <<<")
    print(f"- 원본 해시 (SHA256):            {actual_sha256}")
    print(f"- 관측 시점 (Capture At):        {meta.get('source_capture_at')}")
    print(f"- 관측 식별 (Capture ID):        {meta.get('source_capture_id')}")
    print(f"- 관측 범위 (Scope):             {meta.get('observation_scope')} (부분 관측: is_partial=True)")
    print("-" * 65)
    print(f"1. 정상 매물 ID 수:              {report['metrics']['total_valid_listings']}대")
    print(f"2. 과거 T1(1,764대) 일치 ID 수:  {report['metrics']['matched_in_t1_count']}대 (체류일수 누적)")
    print(f"3. T1에 없던 신규 관측 ID 수:     {report['metrics']['new_to_baseline_count']}대 (신규 등장 후보)")
    print(f"4. 동일 ID 확인된 실제 가격 변화: {report['metrics']['price_changed_count']}건")
    print(f"5. 가격 미공개('상담') 매물 수:   {report['metrics']['price_consultation_unannounced_count']}대")
    print(f"6. 가격 결측/파싱 불가 매물 수:   {report['metrics']['price_missing_corrupt_count']}대")
    print(f"7. 식별 불가/정보 부족 매물 수:   {report['metrics']['invalid_or_uncomparable_count']}대")
    print("=" * 65)

    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manual T2 Differential Analyzer (DIRECTIVE 129)")
    parser.add_argument("--input", type=str, default=None, help="Path to raw captured JSON file")
    parser.add_argument("--meta", type=str, default=None, help="Path to provenance metadata JSON file")
    parser.add_argument("--baseline", type=str, default=FIXED_T1_BASELINE_JSON, help="Path to T1 baseline JSON")
    args = parser.parse_args()

    result = analyze_t2_differential(args.input, args.meta, args.baseline)
    print(f"\nFinal Tool Status: {result.get('status')}")
