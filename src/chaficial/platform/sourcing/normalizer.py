"""
CarManager Common Normalization Layer (DIRECTIVE 111 P0 Standards)
Unified schema normalization for CarManager crawler, Timeseries Engine, and Operational Sync.
Eliminates all field mismatches across data pipelines.
"""

import re
import json
import hashlib
from typing import Dict, Any, Optional

def parse_price_manwon(val: Any) -> Optional[int]:
    """모든 입력 가격을 순수 '만원 단위 정수'로 표준화 (미확인 시 None)"""
    if val is None or val == "" or str(val).strip() == "":
        return None
    if isinstance(val, (int, float)):
        p = int(val)
    else:
        s = re.sub(r"[^\d]", "", str(val))
        if not s:
            return None
        p = int(s)

    # 10만 이상이면 원 단위(예: 15,000,000원 -> 1500만원)로 변환
    if p >= 100000:
        p = p // 10000
    return p

def parse_mileage_km(val: Any) -> Optional[int]:
    """주행거리 파싱 (예: '13.2만' -> 132000, '5.5만 km' -> 55000)"""
    if val is None or val == "" or str(val).strip() == "":
        return None
    if isinstance(val, (int, float)):
        return int(val)

    s = str(val).replace(",", "").strip()
    m_man = re.search(r"([\d.]+)\s*만", s)
    if m_man:
        try:
            return int(float(m_man.group(1)) * 10000)
        except ValueError:
            pass

    digits = re.sub(r"[^\d]", "", s)
    if digits:
        try:
            return int(digits)
        except ValueError:
            return None
    return None

def parse_model_year(val: Any) -> Optional[int]:
    """연식 파싱 (예: '2019', '2019년', '19년형' -> 2019)"""
    if val is None or val == "" or str(val).strip() == "":
        return None
    if isinstance(val, int) and 1970 <= val <= 2030:
        return val

    s = str(val).strip()
    m4 = re.search(r"(19\d{2}|20\d{2})", s)
    if m4:
        return int(m4.group(1))
    m2 = re.search(r"(\d{2})년", s)
    if m2:
        y = int(m2.group(1))
        return (2000 + y) if y <= 35 else (1900 + y)
    return None

def normalize_carmanager_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    단일 카매니저 원본 레코드를 엄격한 공통 표준 스키마 딕셔너리로 정규화.
    수집기, 시계열 엔진, 운영 동기화 엔진이 100% 동일하게 사용.
    """
    encarno = raw.get("encarno") or raw.get("car_seq") or raw.get("listing_id") or ""
    
    # 1. 가격 정규화
    raw_price = raw.get("price_manwon") if raw.get("price_manwon") is not None else raw.get("price")
    if raw_price is None:
        raw_price = raw.get("advertised_price")
    price_manwon = parse_price_manwon(raw_price)

    # 2. 모델명 정규화
    model_name = raw.get("model") or raw.get("carname") or raw.get("model_name") or raw.get("title")
    if model_name:
        model_name = re.sub(r"^\[.*?\]\s*", "", str(model_name)).strip()

    # 3. 연식 정규화
    raw_year = raw.get("model_year") or raw.get("caryear") or raw.get("year")
    model_year = parse_model_year(raw_year)

    # 4. 주행거리 정규화
    raw_km = raw.get("mileage") if raw.get("mileage") is not None else raw.get("km")
    mileage_km = parse_mileage_km(raw_km)

    # 5. 상사명 & 단지명
    shop_name = raw.get("shop") or raw.get("shopname") or raw.get("sangsa_name") or raw.get("dealer_shop")
    danji = raw.get("danji") or "장안평"

    # 6. 제원 (연료, 변속기)
    fuel = raw.get("fuel") or raw.get("fuel_type")
    mission = raw.get("mission") or raw.get("transmission")

    # 7. 번호판 & 차량번호 상태
    plate = raw.get("plate_number") or raw.get("plate")
    plate_tail = raw.get("plate_tail") or raw.get("car_no_tail")

    # 8. 사진 수
    photo_count = None
    if "photos" in raw and isinstance(raw["photos"], list):
        photo_count = len(raw["photos"])
    elif "photo_count" in raw and raw["photo_count"] is not None:
        try:
            photo_count = int(raw["photo_count"])
        except (ValueError, TypeError):
            photo_count = None

    # 9. 원본 해시
    raw_hash = hashlib.sha256(json.dumps(raw, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    return {
        "encarno": encarno,
        "raw_price_str": str(raw_price) if raw_price is not None else None,
        "price_manwon": price_manwon,
        "model_name": model_name,
        "model_year": model_year,
        "mileage_km": mileage_km,
        "fuel": fuel,
        "mission": mission,
        "shop_name": shop_name,
        "danji": danji,
        "plate": plate,
        "plate_tail": plate_tail,
        "photo_count": photo_count,
        "raw_hash": raw_hash,
        "raw_record": raw
    }
