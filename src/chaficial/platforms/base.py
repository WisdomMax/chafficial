"""원천 플랫폼(엔카, KB차차차, KCar 등) 매물 데이터 표준 규격 및 URL 파서."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs, urlparse


@dataclass
class StandardListingRecord:
    """원천 플랫폼에서 수집/관측된 매물의 표준 정규화 레코드."""

    source_platform: str  # ENCAR, KB_CHACHACHA, KCAR, DEALER_DIRECT, OTHER
    source_listing_id: str  # 플랫폼 고유 매물 번호
    source_url: str | None
    seller_reference: str | None

    # 차량 제원
    manufacturer: str  # 현대, 기아, 제네시스 등
    model_name: str  # 아반떼, 그랜저, 쏘나타 등
    model_generation: str | None  # CN7, GN7, DN8 등
    trim_name: str | None  # 모던, 인스퍼레이션, 캘리그래피 등
    model_year: int  # 연식 (예: 2021)
    mileage_km: int  # 주행거리 (km)
    fuel_type: str  # 가솔린, 디젤, 하이브리드, 전기, LPG
    transmission: str  # 자동, 수동

    # 시장 관측 값
    price_krw: int  # 등록 가격 (호가, 원 단위)
    raw_location: str  # 판매 소재지 텍스트
    accident_state: str  # NO_ACCIDENT, SIMPLE_REPAIR, MAJOR_ACCIDENT, UNKNOWN
    has_inspection_record: bool  # 성능점검기록부 교부 여부

    # 시계열 및 데이터 신뢰성 메타데이터
    observed_at: datetime  # 실제 관측 시점
    listing_status: str = "ACTIVE"  # ACTIVE, PRICE_CHANGED, DELISTED, UNKNOWN
    data_origin: str = "MANUALLY_OBSERVED"  # SYNTHETIC, MANUALLY_OBSERVED, AUTHORIZED_FEED
    raw_specs: dict[str, Any] | None = None


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
            # 예: https://car.encar.com/detail?carid=38291023
            # 또는 /dc/dc_cardetailview.do?method=kidiFirstPop&carid=38291023
            if query.get("carid"):
                return platform, query["carid"][0]
            # URL 패스 내 번호 체크: /detail/38291023
            path_parts = [p for p in parsed.path.split("/") if p]
            for part in reversed(path_parts):
                if part.isdigit() and len(part) >= 6:
                    return platform, part
            return platform, None

        elif platform == "KB_CHACHACHA":
            # 예: https://www.kbchachacha.com/public/car/detail.kbc?carSeq=24901823
            if query.get("carSeq"):
                return platform, query["carSeq"][0]
            path_parts = [p for p in parsed.path.split("/") if p]
            for part in reversed(path_parts):
                if part.isdigit():
                    return platform, part
            return platform, None

        elif platform == "KCAR":
            # 예: https://www.kcar.com/bc/detail/carSearchDetail?i_sCarCd=EC60812938
            if query.get("i_sCarCd"):
                return platform, query["i_sCarCd"][0]
            return platform, None

        return platform, None
