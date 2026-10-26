"""차마트(CHAMART) 실매물 자동 소싱 어댑터 기반 인터페이스 (DIRECTIVE 049).

엔카, KB차차차, K Car 등 다중 플랫폼 확장을 위한 공통 추상 규격 정의.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class RawListing:
    """플랫폼에서 원본 수집된 표준 매물 데이터 구조체."""
    source: str  # ENCAR, KB_CHACHACHA 등
    source_listing_id: str  # 플랫폼 고유 매물 번호
    source_url: str  # 원본 매물 웹 상세 링크
    
    # 차량 스펙
    manufacturer: str  # 현대, 기아 등
    model: str  # 쏘나타, 그랜저 등
    trim: Optional[str] = None  # 세부 등급
    model_year: int = 0  # 연식 (예: 2020)
    mileage_km: int = 0  # 주행거리 (km)
    price_krw: int = 0  # 광고 가격 (만원 단위)
    fuel_type: str = "가솔린"  # 가솔린, 디젤, 하이브리드, 전기 등
    transmission: str = "오토"  # 오토, 수동 등
    
    # 지역 및 판매자
    raw_region: str = "서울"
    raw_seller_location: Optional[str] = None  # 상사/전시장 주소
    raw_seller_name: Optional[str] = None  # 상사명 또는 딜러명
    plate_number: Optional[str] = None  # 차량등록번호 (제공 시)
    
    # 사진 및 부가정보
    primary_photo_url: Optional[str] = None
    photos: List[str] = field(default_factory=list)
    options: List[str] = field(default_factory=list)
    
    # 관측 메타데이터
    observed_at: datetime = field(default_factory=datetime.utcnow)
    listing_status: str = "ACTIVE"  # ACTIVE, CONTRACT, SOLD, DELISTED
    source_confidence: float = 0.95
    raw_payload: Dict[str, Any] = field(default_factory=dict)


class BaseSourceAdapter(ABC):
    """다중 중고차 플랫폼 소싱 어댑터 추상 베이스 클래스."""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    @abstractmethod
    def fetch_listings(
        self,
        region: str = "서울",
        page: int = 1,
        limit: int = 20,
    ) -> List[RawListing]:
        """해당 지역의 매물 목록을 페이지 단위로 수집."""
        pass

    @abstractmethod
    def fetch_listing_detail(self, source_listing_id: str) -> Optional[Dict[str, Any]]:
        """매물 상세 정보(상사 주소, 딜러 정보, 전시장 등) 조회."""
        pass
