"""차마트(CHAMART) 전역 검색 및 입력 데이터 정규화 모듈.

DIRECTIVE 046-B & 046-C 명세 준수:
1. 유니코드 NFC/NFKC 정규화, 영문 대소문자 무시, 공백 정리
2. 한글 초성 분해 및 초성 검색 알고리즘 (예: 'ㅇㅂㄸ' -> '아반떼')
3. 전화번호 표준화 (01012345678 형태 저장, 010-1234-5678 표시)
4. 금액 파싱 및 세자리 쉼표 포맷팅
5. 차량, 고객, 상담, 거래, 영상 통합 전역 검색 (Universal Search)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

# 한글 자모 상수 (호환용 자모: U+3131 ~ U+314E)
CHOSUNG_LIST = [
    "ㄱ", "ㄲ", "ㄴ", "ㄷ", "ㄸ", "ㄹ", "ㅁ", "ㅂ", "ㅃ", "ㅅ",
    "ㅆ", "ㅇ", "ㅈ", "ㅉ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"
]

# 조합형 첫소리 자모(U+1100 ~ U+1112) -> 호환용 자모(U+3131 ~ U+314E) 매핑 테이블
LEAD_JAMO_TO_COMPAT = {
    chr(0x1100 + i): CHOSUNG_LIST[i] for i in range(19)
}

def to_compat_chosung(ch: str) -> str:
    """단일 문자가 첫소리 자모이거나 호환 자모인 경우 표준 호환 자모로 변환."""
    if ch in LEAD_JAMO_TO_COMPAT:
        return LEAD_JAMO_TO_COMPAT[ch]
    if ch in CHOSUNG_LIST:
        return ch
    return ch


def normalize_text(text: Optional[str]) -> str:
    """유니코드 NFKC 정규화(전각 영숫자 변환) 및 자모 호환 매핑, 공백 축소, 소문자화."""
    if not text:
        return ""
    # 1. NFKC 정규화 (전각 문자, 기호, 특수 호환형 표준화)
    normalized = unicodedata.normalize("NFKC", str(text))
    # 2. 조합형 첫가소리 자모(U+1100대)가 있다면 표준 호환 자모(U+3131대)로 통일
    chars = [to_compat_chosung(c) for c in normalized]
    # 3. 앞뒤 공백 제거 및 연속 공백을 단일 공백으로
    res = re.sub(r"\s+", " ", "".join(chars)).strip()
    return res.casefold()


def extract_chosung(text: Optional[str]) -> str:
    """텍스트에서 한글 음절의 초성을 추출하고, 영숫자/기호 및 단독 자모는 표준 호환 자모로 변환."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFC", str(text))
    result = []
    for ch in normalized:
        code = ord(ch)
        # 한글 음절 범위: 가(0xAC00) ~ 힣(0xD7A3)
        if 0xAC00 <= code <= 0xD7A3:
            chosung_idx = (code - 0xAC00) // (21 * 28)
            result.append(CHOSUNG_LIST[chosung_idx])
        elif ch in LEAD_JAMO_TO_COMPAT:
            result.append(LEAD_JAMO_TO_COMPAT[ch])
        elif ch in CHOSUNG_LIST:
            result.append(ch)
        else:
            result.append(ch.casefold())
    return "".join(result)


def is_chosung_query(query: str) -> bool:
    """검색어가 순수 초성 또는 초성+영숫자로 구성되어 있는지 판별.
    
    완성형 한글(0xAC00~0xD7A3)이 포함되어 있으면 일반 완성형 검색어로 취급.
    초성(ㄱ~ㅎ)이 최소 1자 이상 포함되어야 함.
    """
    cleaned = query.replace(" ", "")
    if not cleaned:
        return False
    
    # 완성형 한글이 포함되어 있는지 확인
    for ch in cleaned:
        if 0xAC00 <= ord(ch) <= 0xD7A3:
            return False
            
    # 초성 포함 여부 확인 (첫소리 자모 또는 호환 자모)
    has_chosung = any(
        (ch in CHOSUNG_LIST or ch in LEAD_JAMO_TO_COMPAT) for ch in cleaned
    )
    return has_chosung


def normalize_phone_number(raw_phone: Optional[str]) -> str:
    """전화번호에서 숫자만 추출하고 표준 국내/국제 형식으로 정규화."""
    if not raw_phone:
        return ""
    # 유니코드 전각 숫자 정규화
    text = unicodedata.normalize("NFKC", str(raw_phone))
    # +82 국가번호 처리
    text = re.sub(r"^\+?82\s*", "0", text)
    # 숫자만 추출
    digits = re.sub(r"[^\d]", "", text)
    return digits


def normalize_plate_number(raw_plate: Optional[str]) -> str:
    """차량번호판 문자열을 유니코드 정규화 및 표준 띄어쓰기 형식으로 변환.
    
    예시:
    - '  55  누   1122  ' -> '55누 1122'
    - '５５누　１１２２' -> '55누 1122'
    - '123가4567' -> '123가 4567'
    - '서울12가3456' -> '서울 12가 3456'
    """
    if not raw_plate:
        return ""
    # 유니코드 NFKC 정규화 (전각 영숫자 및 전각 기호 변환)
    text = unicodedata.normalize("NFKC", str(raw_plate)).strip()
    # 내부 공백 축약
    text_no_spaces = re.sub(r"\s+", "", text)
    
    # 1. 지역명 포함 번호판 패턴 (예: 서울 12가 3456)
    m_region = re.match(r"^([가-힣]{2})(\d{2,3})([가-힣])(\d{4})$", text_no_spaces)
    if m_region:
        region, f_digits, mid_char, b_digits = m_region.groups()
        return f"{region} {f_digits}{mid_char} {b_digits}"
        
    # 2. 전국 번호판 패턴 (예: 55누 1122, 123가 4567)
    m_standard = re.match(r"^(\d{2,3})([가-힣])(\d{4})$", text_no_spaces)
    if m_standard:
        f_digits, mid_char, b_digits = m_standard.groups()
        return f"{f_digits}{mid_char} {b_digits}"
        
    # 3. 그 외 형식은 다중 공백만 단일 공백으로 치환
    return re.sub(r"\s+", " ", text)


def format_phone_display(phone_digits: Optional[str]) -> str:
    """정규화된 전화번호 숫자를 사용자 표시용 하이픈 형식으로 변환."""
    if not phone_digits:
        return ""
    digits = normalize_phone_number(phone_digits)
    # 11자리 휴대폰 (010-1234-5678)
    if len(digits) == 11 and digits.startswith("01"):
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    # 10자리 (010-123-4567 또는 서울 02-1234-5678)
    elif len(digits) == 10:
        if digits.startswith("02"):
            return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    # 9자리 서울 (02-123-4567)
    elif len(digits) == 9 and digits.startswith("02"):
        return f"{digits[:2]}-{digits[2:5]}-{digits[5:]}"
    # 8자리 대표번호 (1588-1234)
    elif len(digits) == 8:
        return f"{digits[:4]}-{digits[4:]}"
    return digits


def parse_currency_amount(val: Any) -> Optional[int]:
    """다양한 형식의 금액 입력값을 안전한 정수(원)로 파싱 (빈칸은 None)."""
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    # ₩ 기호, 쉼표, 공백 제거
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("₩", "").replace(",", "").replace(" ", "").replace("원", "")
    if not s:
        return None
    try:
        # 소수점 입력 시 반올림 처리
        amount = int(round(float(s)))
        return amount
    except (ValueError, TypeError):
        return None


def format_currency_display(amount: Optional[int], unit_suffix: bool = True) -> str:
    """원 단위 정수 금액을 3자리 쉼표 표시 문자열로 변환."""
    if amount is None:
        return "-"
    formatted = f"{amount:,}"
    return f"{formatted}원" if unit_suffix else formatted


def match_field(field_val: Optional[str], query: str, is_chosung: bool) -> bool:
    """단일 필드에 대해 일반 검색, 초성 검색, 전화번호 검색 복합 매칭."""
    if not field_val:
        return False
    norm_val = normalize_text(field_val)
    norm_query = normalize_text(query)

    # 1. 일반 부분 일치
    if norm_query in norm_val:
        return True

    # 2. 전화번호 숫자 검색
    phone_digits_val = normalize_phone_number(field_val)
    phone_digits_query = normalize_phone_number(query)
    if phone_digits_query and len(phone_digits_query) >= 3 and phone_digits_query in phone_digits_val:
        return True

    # 3. 초성 검색 매칭
    if is_chosung:
        chosung_val = extract_chosung(field_val)
        chosung_query = extract_chosung(query)
        if chosung_query and chosung_query in chosung_val:
            return True

    return False


def universal_search(db: Session, raw_query: str) -> Dict[str, Any]:
    """플랫폼 전역 검색 (차량, 고객, 상담, 거래, 영상 프로젝트).
    
    복합 검색어 지원: 공백으로 분리된 모든 키워드가 레코드 내에 매칭되는지 확인.
    """
    cleaned_query = normalize_text(raw_query)
    if not cleaned_query:
        return {
            "query": "",
            "total_count": 0,
            "vehicles": [],
            "customers": [],
            "consultations": [],
            "transactions": [],
            "media_projects": [],
        }

    keywords = cleaned_query.split()
    is_chosung = is_chosung_query(cleaned_query)

    from chaficial.platform.db import (
        Consultation,
        Customer,
        MediaProject,
        Transaction,
        Vehicle,
    )

    results: Dict[str, Any] = {
        "query": cleaned_query,
        "total_count": 0,
        "vehicles": [],
        "customers": [],
        "consultations": [],
        "transactions": [],
        "media_projects": [],
    }

    # 1. 차량 검색 (모델명, 번호판, 연식, 주행거리, 희망판매가, 딜러명, 상사명, VIN, 플랫폼 매물 ID, 상태)
    vehicles = db.query(Vehicle).all()
    for v in vehicles:
        dealer_text = f"{v.dealer.name} {v.dealer.dealership_name}" if v.dealer else "차마트직영"
        listings_text = " ".join(f"{l.platform} {l.listing_id}" for l in v.listings)
        compact_plate = v.plate_number.replace(" ", "") if v.plate_number else ""
        norm_plate = normalize_plate_number(v.plate_number)
        combined_text = (
            f"{v.model_name} {v.plate_number} {compact_plate} {norm_plate} {v.year} {v.mileage} {v.fuel_type} {v.color} "
            f"{v.target_price} {v.status} {v.ownership_type or ''} {v.vin or ''} {dealer_text} {listings_text} {v.branch_id}"
        )
        if all(match_field(combined_text, kw, is_chosung) for kw in keywords):
            dealer_name = v.dealer.dealership_name if v.dealer else "차마트 직영"
            results["vehicles"].append({
                "id": v.id,
                "plate_number": v.plate_number,
                "model_name": v.model_name,
                "year": v.year,
                "model_year": v.year,  # 호환성 유지
                "mileage": v.mileage,
                "mileage_km": v.mileage,  # 호환성 유지
                "target_price": v.target_price,
                "advertised_price": v.target_price,  # 호환성 유지
                "formatted_price": format_currency_display(v.target_price),
                "status": v.status,
                "ownership_type": v.ownership_type or "CHAMART_OWNED",
                "dealer_name": dealer_name,
                "primary_photo_url": v.primary_photo_url,
                "branch_id": v.branch_id,
            })

    # 2. 고객 CRM 검색 (고객명, 전화번호, 희망차종, 예산, 상태, 담당자, 메모)
    customers = db.query(Customer).all()
    for c in customers:
        combined_text = f"{c.name} {c.phone} {c.target_vehicle_model or ''} {c.budget_max or ''} {c.assigned_staff or ''} {c.notes or ''} {c.status} {c.branch_id}"
        if all(match_field(combined_text, kw, is_chosung) for kw in keywords):
            results["customers"].append({
                "id": c.id,
                "name": c.name,
                "phone": format_phone_display(c.phone),
                "target_vehicle_model": c.target_vehicle_model,
                "interest_model": c.target_vehicle_model,  # 호환성 유지
                "budget_max": c.budget_max,
                "budget_krw": c.budget_max,  # 호환성 유지
                "formatted_budget": format_currency_display(c.budget_max),
                "assigned_staff": c.assigned_staff,
                "notes": c.notes,
                "status": c.status,
                "branch_id": c.branch_id,
            })

    # 3. 상담 기록 검색 (상담 내용, 채널, 담당자 등 상세 메모)
    consultations = db.query(Consultation).all()
    for cs in consultations:
        cust = db.query(Customer).filter(Customer.id == cs.customer_id).first()
        cust_name = cust.name if cust else ""
        combined_text = f"{cust_name} {cs.content} {cs.channel} {cs.staff_name or ''}"
        if all(match_field(combined_text, kw, is_chosung) for kw in keywords):
            results["consultations"].append({
                "id": cs.id,
                "customer_id": cs.customer_id,
                "customer_name": cust_name,
                "channel": cs.channel,
                "content": cs.content,
                "staff_name": cs.staff_name,
                "created_at": cs.created_at.strftime("%Y-%m-%d %H:%M") if cs.created_at else "",
            })

    # 4. 거래 관리 검색 (거래 유형, 금액, 거래상대방, 정산상태, 메모)
    transactions = db.query(Transaction).all()
    for t in transactions:
        combined_text = f"{t.transaction_type} {t.amount} {t.party_name} {t.settlement_status} {t.notes or ''}"
        if all(match_field(combined_text, kw, is_chosung) for kw in keywords):
            results["transactions"].append({
                "id": t.id,
                "transaction_type": t.transaction_type,
                "amount": t.amount,
                "formatted_amount": format_currency_display(t.amount),
                "party_name": t.party_name,
                "settlement_status": t.settlement_status,
            })

    # 5. 영상 스튜디오 검색 (프로젝트 제목, 컨셉, 포맷, 타겟플랫폼, 상태)
    media_projects = db.query(MediaProject).all()
    for m in media_projects:
        combined_text = f"{m.title} {m.concept or ''} {m.content_format or ''} {m.target_platform or ''} {m.status}"
        if all(match_field(combined_text, kw, is_chosung) for kw in keywords):
            results["media_projects"].append({
                "id": m.id,
                "title": m.title,
                "concept": m.concept,
                "content_format": m.content_format,
                "target_platform": m.target_platform,
                "status": m.status,
            })

    results["total_count"] = (
        len(results["vehicles"])
        + len(results["customers"])
        + len(results["consultations"])
        + len(results["transactions"])
        + len(results["media_projects"])
    )
    return results
