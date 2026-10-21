"""원천 플랫폼(엔카, KB차차차, KCar 등) 매물 데이터 표준 규격 및 URL 파서."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass
class StandardListingRecord:
    """원천 플랫폼에서 수집/관측된 매물의 표준 정규화 레코드 (DIRECTIVE 007-B 규격)."""

    source_platform: str  # ENCAR, KB_CHACHACHA, KCAR, DEALER_DIRECT, OTHER
    source_listing_id: str  # 플랫폼 고유 매물 번호
    source_url: str | None = None
    seller_reference: str | None = None

    # 차량 제원 및 세대/라인 정밀 분류
    manufacturer: str = "현대"  # 현대, 기아, 제네시스 등
    model_name: str = "아반떼"  # 아반떼, 그랜저, 쏘나타 등
    model_generation: str | None = None  # CN7, GN7, DN8 등
    sub_model: str = "PRE_FACELIFT"  # PRE_FACELIFT (전기형), FACELIFT (더 뉴 아반떼 등)
    powertrain_line: str = "STANDARD"  # STANDARD (일반), N_LINE (N라인), N (고성능 N)
    trim_name: str | None = None  # 모던, 인스퍼레이션, 스마트 등

    # 연식 및 등록
    model_year: int | None = None  # 모델연도 (형식연도, 미확인 시 None)
    registration_year_month: str | None = None  # 최초등록연월 (예: "2021-09")
    mileage_km: int = 0  # 주행거리 (km)
    fuel_type: str = "가솔린"  # 가솔린, 하이브리드, LPG, 디젤, 전기, UNKNOWN
    transmission: str = "자동"  # 자동, 수동, UNKNOWN

    # 금융 상품 구분 (금융상품 가격 오염 원천 차단)
    product_type: str = "CASH_OR_INSTALLMENT"  # CASH_OR_INSTALLMENT (일반판매), LEASE (리스승계), RENT (렌트승계/이용)
    price_krw: int | None = None  # 차량 총 매매가격 (금융상품의 경우 None 처리)
    monthly_payment_krw: int | None = None  # 월 렌트/리스 납입액

    # 시장 관측 값
    raw_location: str = ""  # 판매 소재지 텍스트
    accident_state: str = "UNKNOWN"  # NO_ACCIDENT, SIMPLE_REPAIR, MAJOR_ACCIDENT, UNKNOWN
    accident_verification: str = "UNVERIFIED"  # OFFICIAL_VERIFIED, SELLER_CLAIM, UNVERIFIED
    has_inspection_record: bool = False  # 성능점검/진단 기록부 교부 여부

    # 시계열 및 데이터 신뢰성 메타데이터
    observed_at: datetime | None = None  # 실제 관측 시점
    listing_status: str = "ACTIVE"  # ACTIVE, PRICE_CHANGED, DELISTED, UNKNOWN
    data_origin: str = "MANUALLY_OBSERVED"  # SYNTHETIC, MANUALLY_OBSERVED, AUTHORIZED_FEED
    raw_specs: dict[str, Any] | None = None
    raw_card_text: str | None = None


class PlatformUrlParser:
    """중고차 플랫폼 URL 분석 및 플랫폼/고유 ID 자동 추출기."""

    @staticmethod
    def identify_platform(url: str) -> str:
        """URL의 hostname을 기반으로 원천 플랫폼을 안전하게 식별."""
        if not url:
            return "UNKNOWN_PLATFORM"
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            if host == "encar.com" or host.endswith(".encar.com"):
                return "ENCAR"
            elif host == "kbchachacha.com" or host.endswith(".kbchachacha.com"):
                return "KB_CHACHACHA"
            elif host == "kcar.com" or host.endswith(".kcar.com"):
                return "KCAR"
        except (ValueError, AttributeError):
            return "UNKNOWN_PLATFORM"
        return "UNKNOWN_PLATFORM"

    @staticmethod
    def extract_source_id(url: str) -> tuple[str, str | None]:
        """URL에서 플랫폼명과 고유 매물 ID 추출."""
        platform = PlatformUrlParser.identify_platform(url)
        if platform == "UNKNOWN_PLATFORM":
            return platform, None

        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        if platform == "ENCAR":
            if query.get("carid"):
                return platform, query["carid"][0]
            path_parts = [p for p in parsed.path.split("/") if p]
            for part in reversed(path_parts):
                if part.isdigit() and len(part) >= 6:
                    return platform, part
            return platform, None

        elif platform == "KB_CHACHACHA":
            if query.get("carSeq"):
                return platform, query["carSeq"][0]
            path_parts = [p for p in parsed.path.split("/") if p]
            for part in reversed(path_parts):
                if part.isdigit():
                    return platform, part
            return platform, None

        elif platform == "KCAR":
            if query.get("i_sCarCd"):
                return platform, query["i_sCarCd"][0]
            return platform, None

        return platform, None
