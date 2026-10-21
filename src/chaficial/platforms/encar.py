"""엔카(Encar) 원천 웹/모바일 매물 카드 텍스트 정밀 파서 (DIRECTIVE 008)."""

import re
from datetime import UTC, datetime


class EncarCardParser:
    """엔카 매물 카드 텍스트 파싱 및 표준 레코드 변환기."""

    @staticmethod
    def parse_card(c: dict, now_iso: str | None = None) -> dict | None:
        """원천 카드 텍스트에서 008 무결성 규격 레코드 딕셔너리 추출."""
        raw_text = c.get("raw_text", "").strip()
        carid = str(c.get("carid", "")).strip()
        if not carid or not raw_text:
            return None

        # 아반떼 CN7 필터
        if "CN7" not in raw_text:
            return None

        obs_time = now_iso or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        # 1. 페이스리프트 구분 (더 뉴 아반떼 vs 전기형)
        sub_model = "FACELIFT" if "더 뉴 아반떼" in raw_text else "PRE_FACELIFT"

        # 2. 파워트레인 라인 구분 (N-Line 우선 판별하여 N 오분류 차단)
        if "N Line" in raw_text or "N라인" in raw_text or "N-Line" in raw_text:
            powertrain_line = "N_LINE"
        elif "2.0 N" in raw_text or " N " in raw_text or "아반떼 N" in raw_text:
            powertrain_line = "N"
        else:
            powertrain_line = "STANDARD"

        # 3. 트림 파싱
        trim_name = ""
        if "인스퍼레이션" in raw_text:
            trim_name = "인스퍼레이션"
        elif "모던" in raw_text:
            trim_name = "모던"
        elif "스마트" in raw_text:
            trim_name = "스마트"

        # 4. 연식 파싱: 최초등록연월 및 모델연도 분리
        # 모델연도 미표기 시 등록연도 대체 금지 (추정 주입 금지 -> 빈 문자열 보존)
        reg_match = re.search(r"(\d{2})/(\d{2})식", raw_text)
        if not reg_match:
            return None
        reg_yy = int(reg_match.group(1))
        reg_mm = int(reg_match.group(2))
        reg_ym = f"20{reg_yy:02d}-{reg_mm:02d}"

        model_year_str = ""
        model_year_match = re.search(r"\((\d{2})년형\)", raw_text)
        if model_year_match:
            model_year_str = str(2000 + int(model_year_match.group(1)))

        # 5. 주행거리 파싱
        km_match = re.search(r"([\d,]+)km", raw_text)
        if not km_match:
            return None
        mileage_km = int(km_match.group(1).replace(",", ""))

        # 6. 금융상품(렌트/리스) 식별 및 가격 분리
        # DIRECTIVE 008-A: 옵션 추가금액(스마트센스 1(115만원), 컴포트 1(120만원) 등) 오탐 원천 차단
        product_type = "CASH_OR_INSTALLMENT"
        price_krw = None
        monthly_payment_krw = None

        m_rent = re.search(r"렌트\s*월\s*([\d,]+)만원", raw_text)
        m_lease = re.search(r"리스\s*월\s*([\d,]+)만원", raw_text)

        if m_rent or "렌트승계" in raw_text or "장기렌트" in raw_text:
            product_type = "RENT"
            if m_rent:
                monthly_payment_krw = int(m_rent.group(1).replace(",", "")) * 10_000
        elif m_lease or "리스승계" in raw_text or "운용리스" in raw_text or "금융리스" in raw_text:
            product_type = "LEASE"
            if m_lease:
                monthly_payment_krw = int(m_lease.group(1).replace(",", "")) * 10_000
        else:
            # 1) 옵션 괄호 안의 모든 금액 제거: 예: "(115만원)", "(120만원)"
            clean_text = re.sub(r"\([^)]*?[\d,]+만원[^)]*?\)", "", raw_text)
            # 2) 월납입금 문구 제거
            clean_text = re.sub(r"(?:렌트|리스)\s*월\s*[\d,]+만원", "", clean_text)
            # 3) 차량 본체 가격 후보 추출
            price_matches = re.findall(r"([\d,]+)만원", clean_text)
            if price_matches:
                # 엔카 카드는 차량 가격이 맨 마지막에 위치함 (예: 경기 수원 1,780만원)
                # 후보들 중 정상 중고차 가격대(300만원 ~ 8,000만원)에 부합하는 마지막 금액 선택
                valid_candidates = []
                for pm in price_matches:
                    val = int(pm.replace(",", "")) * 10_000
                    if 3_000_000 <= val <= 80_000_000:
                        valid_candidates.append(val)
                if valid_candidates:
                    price_krw = valid_candidates[-1]
                else:
                    # 후보가 범위 밖이면 마지막 매칭값 적용
                    price_krw = int(price_matches[-1].replace(",", "")) * 10_000

        # 7. 연료 및 변속기
        fuel_type = "UNKNOWN"
        if "가솔린+전기" in raw_text or "하이브리드" in raw_text:
            fuel_type = "하이브리드"
        elif "가솔린" in raw_text:
            fuel_type = "가솔린"
        elif "LPG" in raw_text or "LPI" in raw_text:
            fuel_type = "LPG"
        elif "디젤" in raw_text:
            fuel_type = "디젤"

        transmission = "수동" if ("수동" in raw_text or "M/T" in raw_text) else "UNKNOWN"

        # 8. 소재지 파싱 (실제 매매단지 지명 추출)
        raw_location = ""
        for loc_candidate in [
            "서울 강남", "서울 강서", "서울 성동", "서울 동대문", "서울 양천",
            "경기 수원", "경기 용인", "경기 부천", "경기 김포", "경기 고양", "경기 안산",
            "인천 서구", "인천 미추홀", "대구", "부산", "광주", "대전", "충남 천안"
        ]:
            if loc_candidate in raw_text:
                raw_location = loc_candidate
                break

        # 9. 사고 상태 및 공인 진단 분리
        accident_state = "UNKNOWN"
        accident_verification = "UNVERIFIED"
        has_inspection = ("성능점검" in raw_text or "진단" in raw_text)

        if "엔카진단" in raw_text:
            accident_verification = "OFFICIAL_VERIFIED"
            if "무사고" in raw_text:
                accident_state = "NO_ACCIDENT"
        elif "무사고" in raw_text:
            accident_verification = "SELLER_CLAIM"
            accident_state = "NO_ACCIDENT"

        if "단순수리" in raw_text or "단순교환" in raw_text:
            accident_state = "SIMPLE_REPAIR"

        url = f"https://car.encar.com/detail?carid={carid}"

        # 실차 고유 지문 생성 (동일 차량 중복 등록 및 Leave-One-Out 데이터 누출 차단용)
        fp = f"현대_아반떼_CN7_{sub_model}_{powertrain_line}_{reg_ym}_{model_year_str or 'NOYEAR'}_{mileage_km}_{price_krw or 'NOPRICE'}_{trim_name or 'NOTRIM'}"

        price_status = "VERIFIED"
        if product_type == "CASH_OR_INSTALLMENT":
            if price_krw is None or price_krw < 3_000_000:
                price_status = "PRICE_UNVERIFIED"

        return {
            "source_platform": "ENCAR",
            "source_listing_id": carid,
            "source_url": url,
            "seller_reference": "",
            "manufacturer": "현대",
            "model_name": "아반떼",
            "model_generation": "CN7",
            "sub_model": sub_model,
            "powertrain_line": powertrain_line,
            "trim_name": trim_name,
            "model_year": model_year_str,
            "registration_year_month": reg_ym,
            "mileage_km": mileage_km,
            "fuel_type": fuel_type,
            "transmission": transmission,
            "product_type": product_type,
            "price_krw": str(price_krw) if price_krw is not None else "",
            "monthly_payment_krw": str(monthly_payment_krw) if monthly_payment_krw is not None else "",
            "raw_location": raw_location,
            "accident_state": accident_state,
            "accident_verification": accident_verification,
            "has_inspection_record": "Y" if has_inspection else "N",
            "observed_at": obs_time,
            "listing_status": "ACTIVE",
            "data_origin": "MANUALLY_OBSERVED",
            "vehicle_fingerprint": fp,
            "price_status": price_status,
            "raw_card_text": raw_text,
        }
