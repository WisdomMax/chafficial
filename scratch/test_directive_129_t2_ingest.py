import os
import sys
import json
import tempfile
import hashlib
import shutil

sys.path.insert(0, ".")
sys.path.insert(0, "src")
sys.path.insert(0, "scripts")

from run_manual_t2_ingest import analyze_t2_differential
from chaficial.platform.sourcing.normalizer import normalize_carmanager_record

def run_tests():
    print("=" * 65)
    print("[DIRECTIVE 129 TASK 1 & 4] T2 수동 인계 분석기 정밀 회귀 테스트")
    print("=" * 65)

    temp_dir = tempfile.mkdtemp()
    try:
        # 1. 파일 부재 시 테스트
        print("\n[TEST 1] 파일 부재 시 REAL_PILOT_PENDING_NEW_CAPTURE 반환 검증...")
        res1 = analyze_t2_differential(None, None)
        assert res1["status"] == "REAL_PILOT_PENDING_NEW_CAPTURE", f"Expected REAL_PILOT_PENDING_NEW_CAPTURE, got {res1}"
        print("[PASS] TEST 1: 파일 부재 시 정직하게 REAL_PILOT_PENDING_NEW_CAPTURE 반환 확인!")

        # 2. HTML 파일 주입 시 UNSUPPORTED_FORMAT 거부 검증
        print("\n[TEST 2] HTML 파일 주입 시 UNSUPPORTED_FORMAT 거부 검증...")
        html_file = os.path.join(temp_dir, "fake_cars.html")
        meta_file = os.path.join(temp_dir, "fake_cars.meta.json")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write("<html><body><table><tr><td>11가1111</td></tr></table></body></html>")
        html_sha = hashlib.sha256(open(html_file, "rb").read()).hexdigest()
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "source_capture_id": "T2_TEST_001",
                "source_capture_at": "2026-11-01T10:00:00",
                "observation_scope": "JANGHANPYEONG_50",
                "raw_sha256": html_sha
            }, f)
        res2 = analyze_t2_differential(html_file, meta_file)
        assert res2["status"] == "UNSUPPORTED_FORMAT", f"Expected UNSUPPORTED_FORMAT, got {res2}"
        print("[PASS] TEST 2: HTML 파일 주입 시 UNSUPPORTED_FORMAT으로 명시적 거부 확인!")

        # 3. 메타데이터 부재 또는 필수 필드 누락 시 거부 검증
        print("\n[TEST 3] 메타데이터 필수 필드 누락 시 INVALID_METADATA 거부 검증...")
        json_file = os.path.join(temp_dir, "cars.json")
        bad_meta = os.path.join(temp_dir, "bad.meta.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump([{"encarno": "TEST_01", "price_manwon": 1000}], f)
        with open(bad_meta, "w", encoding="utf-8") as f:
            json.dump({"source_capture_id": "T2_ONLY_ID"}, f) # capture_at, scope 누락
        res3 = analyze_t2_differential(json_file, bad_meta)
        assert res3["status"] == "INVALID_METADATA", f"Expected INVALID_METADATA, got {res3}"
        print("[PASS] TEST 3-A: 메타데이터 필수 필드 누락 시 INVALID_METADATA 거부 확인!")

        # 3-B. SHA256 체크섬 누락 시 MISSING_SHA256 거부 검증 (DIRECTIVE 129 보정)
        print("\n[TEST 3-B] SHA256 체크섬 누락 시 MISSING_SHA256 거부 검증...")
        no_sha_meta = os.path.join(temp_dir, "no_sha.meta.json")
        with open(no_sha_meta, "w", encoding="utf-8") as f:
            json.dump({
                "source_capture_id": "T2_TEST_001",
                "source_capture_at": "2026-11-01T10:00:00",
                "observation_scope": "JANGHANPYEONG_50"
            }, f)
        res3_b = analyze_t2_differential(json_file, no_sha_meta)
        assert res3_b["status"] == "MISSING_SHA256", f"Expected MISSING_SHA256, got {res3_b}"
        print("[PASS] TEST 3-B: SHA256 체크섬 누락 시 건너뛰기 없이 MISSING_SHA256 거부 확인!")

        # 4. SHA256 체크섬 불일치 시 HASH_MISMATCH 거부 검증
        print("\n[TEST 4] SHA256 해시 불일치 시 HASH_MISMATCH 거부 검증...")
        mismatch_meta = os.path.join(temp_dir, "mismatch.meta.json")
        with open(mismatch_meta, "w", encoding="utf-8") as f:
            json.dump({
                "source_capture_id": "T2_TEST_002",
                "source_capture_at": "2026-11-01T10:00:00",
                "observation_scope": "JANGHANPYEONG_50",
                "raw_sha256": "0000000000000000000000000000000000000000000000000000000000000000"
            }, f)
        res4 = analyze_t2_differential(json_file, mismatch_meta)
        assert res4["status"] == "HASH_MISMATCH", f"Expected HASH_MISMATCH, got {res4}"
        print("[PASS] TEST 4: SHA256 불일치 시 HASH_MISMATCH 거부 확인!")

        # 5. 파싱 결과 매물 0건 시 NO_VALID_LISTINGS_EXTRACTED 거부 검증
        print("\n[TEST 5] 매물 0건 빈 목록 시 NO_VALID_LISTINGS_EXTRACTED 거부 검증...")
        empty_json = os.path.join(temp_dir, "empty.json")
        empty_meta = os.path.join(temp_dir, "empty.meta.json")
        with open(empty_json, "w", encoding="utf-8") as f:
            json.dump([], f)
        empty_sha = hashlib.sha256(open(empty_json, "rb").read()).hexdigest()
        with open(empty_meta, "w", encoding="utf-8") as f:
            json.dump({
                "source_capture_id": "T2_TEST_003",
                "source_capture_at": "2026-11-01T10:00:00",
                "observation_scope": "JANGHANPYEONG_50",
                "raw_sha256": empty_sha
            }, f)
        res5 = analyze_t2_differential(empty_json, empty_meta)
        assert res5["status"] == "NO_VALID_LISTINGS_EXTRACTED", f"Expected NO_VALID_LISTINGS_EXTRACTED, got {res5}"
        print("[PASS] TEST 5: 빈 목록 시 NO_VALID_LISTINGS_EXTRACTED 거부 확인!")

        # 6. 정상 T2 모의 50대 목록 + 정밀 차분 산출 검증
        print("\n[TEST 6] 정상 T2 모의 50대 목록 차분 산출 검증...")
        # T1 베이스라인에서 20대 로드하여 정밀 차분 구성
        with open("data/carmanager_raw/janghanpyeong_full_collection.json", "r", encoding="utf-8") as f:
            t1_raw_all = json.load(f)["cars"]

        mock_t2 = []
        t1_used = 0
        for c in t1_raw_all:
            norm_c = normalize_carmanager_record(c)
            enc = norm_c.get("encarno")
            p_val = norm_c.get("price_manwon")
            if not enc or p_val is None:
                continue # 확정 가격 매물만 우선 선택
            
            if t1_used < 5:
                # 1) 가격 변동 5건 (+100만원)
                mock_t2.append({"encarno": enc, "price_manwon": p_val + 100, "carName": norm_c.get("model_name")})
            elif t1_used < 10:
                # 2) 실제 가격 상담 매물 5건 (원시 표기 '상담')
                mock_t2.append({"encarno": enc, "price": "상담", "raw_price_str": "상담", "carName": norm_c.get("model_name")})
            elif t1_used < 20:
                # 3) 무변경 10건
                mock_t2.append({"encarno": enc, "price_manwon": p_val, "carName": norm_c.get("model_name")})
            
            t1_used += 1
            if t1_used >= 20:
                break

        # 4) 30대 신규 매물 추가
        for i in range(30):
            mock_t2.append({
                "encarno": f"NEW_T2_CAR_{i}",
                "price_manwon": 1500 + i * 10,
                "carName": f"신규차량_{i}"
            })

        valid_t2_file = os.path.join(temp_dir, "t2_cars.json")
        valid_meta_file = os.path.join(temp_dir, "t2_cars.meta.json")
        with open(valid_t2_file, "w", encoding="utf-8") as f:
            json.dump(mock_t2, f, ensure_ascii=False, indent=2)

        actual_sha = hashlib.sha256(open(valid_t2_file, "rb").read()).hexdigest()
        with open(valid_meta_file, "w", encoding="utf-8") as f:
            json.dump({
                "source_capture_id": "T2_REAL_TEST_50",
                "source_capture_at": "2026-11-01T10:00:00+09:00",
                "observation_scope": "JANGHANPYEONG_PAGE1_50CARS",
                "raw_sha256": actual_sha
            }, f, indent=2)

        res6 = analyze_t2_differential(valid_t2_file, valid_meta_file)
        assert res6["status"] == "SUCCESS_T2_ANALYZED", f"Analysis failed: {res6}"
        metrics = res6["metrics"]

        assert metrics["total_valid_listings"] == 50, f"Expected 50 valid listings, got {metrics['total_valid_listings']}"
        assert metrics["matched_in_t1_count"] == 20, f"Expected 20 matched in T1, got {metrics['matched_in_t1_count']}"
        assert metrics["new_to_baseline_count"] == 30, f"Expected 30 new to baseline, got {metrics['new_to_baseline_count']}"
        assert metrics["price_changed_count"] == 5, f"Expected 5 price changed, got {metrics['price_changed_count']}"
        assert metrics["price_consultation_unannounced_count"] == 5, f"Expected 5 consultation unannounced, got {metrics['price_consultation_unannounced_count']}"
        assert metrics["price_missing_corrupt_count"] == 0, f"Expected 0 corrupt missing price, got {metrics['price_missing_corrupt_count']}"
        assert metrics["invalid_or_uncomparable_count"] == 0, f"Expected 0 invalid, got {metrics['invalid_or_uncomparable_count']}"

        print("[PASS] TEST 6: 정상 T2 50대 목록 차분 7대 핵심 지표 100% 일치 확인!")
        print(f"  -> Total: {metrics['total_valid_listings']} | T1 Matched: {metrics['matched_in_t1_count']} | New to Baseline: {metrics['new_to_baseline_count']} | Price Changed: {metrics['price_changed_count']} | Consultation: {metrics['price_consultation_unannounced_count']}")

        print("\n" + "=" * 65)
        print(">>> [DIRECTIVE 129] 6대 정밀 회귀 테스트 100% 전수 통과 <<<")
        print("=" * 65)

    finally:
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    run_tests()
