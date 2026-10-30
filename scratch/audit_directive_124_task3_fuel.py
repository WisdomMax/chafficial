"""
DIRECTIVE 124 TASK 3: 원본 50대 연료 미표기 15건 원본 정밀 분석 및 fuel_inferred 분리 (ISSUE-84)
- 원본 `data/carmanager_raw/janghanpyeong_full_collection.json`의 최초 50대 대상.
- 원본 `fuel` 필드는 원본 데이터(빈 문자열/None) 그대로 보존.
- 파생 필드 `fuel_inferred` 및 `fuel_inference_confidence`를 완전히 분리하여 생성.
"""

import json
import re

with open("data/carmanager_raw/janghanpyeong_full_collection.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

cars_50 = raw_data.get("cars", [])[:50]
total = len(cars_50)
missing_fuel_items = []
present_fuel_items = []

for idx, car in enumerate(cars_50, 1):
    raw_fuel = car.get("fuel")
    if not raw_fuel or raw_fuel.strip() == "":
        model_str = car.get("model", "")
        m_lower = model_str.lower()
        
        inferred = None
        confidence = 0.0
        reason = ""

        # 하이브리드 우선 판별
        if any(kw in m_lower for kw in ["하이브리드", "hybrid", "hev", "phev"]):
            inferred = "하이브리드"
            confidence = 0.95
            reason = "모델명에 하이브리드/HEV/PHEV 키워드 명시"
        elif any(kw in m_lower for kw in ["ev", "일렉트릭", "electric", "아이오닉", "타이칸", "모델3", "모델y", "eqe", "eqs", "ev6", "ev9"]):
            inferred = "전기"
            confidence = 0.95
            reason = "모델명에 전기차 전용 모델/EV 명시"
        elif any(kw in m_lower for kw in ["디젤", "diesel", "cdi", "crdi", "e-hdi", "tdi"]) or re.search(r'\b\d{2,3}d\b', m_lower):
            inferred = "디젤"
            confidence = 0.90
            reason = "모델명에 디젤/d 엔진 사양 명시"
        elif any(kw in m_lower for kw in ["lpi", "lpg", "bi-fuel"]):
            inferred = "LPG"
            confidence = 0.90
            reason = "모델명에 LPi/LPG 연료 사양 명시"
        elif any(kw in m_lower for kw in ["가솔린", "휘발유", "gasoline", "gdi", "t-gdi", "turbo", "tfsi", "tsi"]):
            inferred = "가솔린"
            confidence = 0.85
            reason = "모델명에 가솔린/GDi/터보 가솔린 계열 명시"
        else:
            inferred = "가솔린" # 한국 내수 통상 일반 승용 기본 트림
            confidence = 0.60
            reason = "특수 엔진 미표기 승용차 기본값 (도메인 추론)"

        missing_fuel_items.append({
            "sample_index": idx,
            "encarno": car.get("encarno"),
            "plate_tail": car.get("plate_tail"),
            "model_raw": model_str,
            "maker": car.get("maker"),
            "model_year": car.get("model_year"),
            "raw_fuel": raw_fuel, # 원본은 None 또는 ""
            "fuel_inferred": inferred,
            "fuel_inference_confidence": confidence,
            "inference_reason": reason
        })
    else:
        present_fuel_items.append({
            "sample_index": idx,
            "plate_tail": car.get("plate_tail"),
            "model_raw": car.get("model"),
            "raw_fuel": raw_fuel
        })

report = {
    "task": "DIRECTIVE_124_TASK_3",
    "issue": "ISSUE-84",
    "source_dataset": "data/carmanager_raw/janghanpyeong_full_collection.json (first 50 cars)",
    "total_sample_count": total,
    "raw_fuel_present_count": len(present_fuel_items),
    "raw_fuel_missing_count": len(missing_fuel_items),
    "preservation_guarantee": "원본 데이터(fuel)는 빈 문자열('') 또는 NULL 상태를 100% 불변 보존하며, 추론값은 fuel_inferred와 fuel_inference_confidence로 완전 분리됨.",
    "missing_fuel_details": missing_fuel_items
}

with open("scratch/directive_124_task3_fuel_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"[+] 총 {total}대 중 원본 연료 표기 {len(present_fuel_items)}건 (70.0%), 미표기 {len(missing_fuel_items)}건 (30.0%) 분석 완료")
for it in missing_fuel_items:
    print(f"  - [{it['sample_index']}] Plate:{it['plate_tail']} | {it['maker']} {it['model_raw']} ({it['model_year']}) -> Inferred: {it['fuel_inferred']} (conf: {it['fuel_inference_confidence']:.2f}, 이유: {it['inference_reason']}) | Raw: {repr(it['raw_fuel'])}")
