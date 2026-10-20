"""지역 분류, 장안평 판매 대상 필터 및 확장 관리자."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session
from chaficial.models.listing import Listing
from chaficial.models.region import Region, RegionConfiguration


@dataclass(frozen=True)
class RegionResolution:
    """지역 판정 세부 결과.
    
    행정구역명만으로 매매단지로 오분류되는 것을 차단하고,
    판정 근거와 신뢰 수준을 제공합니다.
    """
    region_id: Optional[str]
    confidence: str  # CONFIRMED, UNCONFIRMED, CONFIRMED_BY_PARTNER, AMBIGUOUS
    is_market_complex: bool
    matched_rule: str
    source_note: Optional[str] = None


class RegionManager:
    """전국 시장 분석과 지역별(장안평, 수원, 인천, 부천 등) 판매 매물 분리 관리자."""

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = str(Path(__file__).parents[3] / "configs" / "regions.yaml")
        self.config_path = config_path
        self._config_data: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def seed_default_regions(self, session: Session) -> None:
        """설정 파일에 정의된 기본 지역 정보를 데이터베이스에 반영합니다."""
        for reg_data in self._config_data.get("regions", []):
            existing = session.get(Region, reg_data["region_id"])
            if not existing:
                region = Region(
                    region_id=reg_data["region_id"],
                    region_name=reg_data["region_name"],
                    region_type=reg_data["region_type"],
                    parent_region_id=reg_data.get("parent_region_id"),
                    is_active=reg_data.get("is_active", True),
                )
                session.add(region)

        existing_cfg = session.scalar(select(RegionConfiguration))
        if not existing_cfg:
            defaults = self._config_data.get("defaults", {})
            cfg = RegionConfiguration(
                analysis_region_scope=defaults.get("market_analysis_scope", "NATIONWIDE"),
                sales_region_ids=[defaults.get("primary_sales_region_id", "REGION_JANGANPYEONG")],
                customer_target_regions=[],
            )
            session.add(cfg)
        session.commit()

    def resolve_region_detailed(
        self,
        raw_location: str,
        partner_operating_region: Optional[str] = None,
    ) -> RegionResolution:
        """주소 문자열을 정밀 분석하여 판정 결과와 신뢰도 메타데이터를 반환합니다.
        
        - 파트너가 직접 확인한 매물인 경우 파트너의 관할 권역을 최우선 신뢰.
        - 일반 행정구역(동, 구, 시)만 있는 경우 매매단지 소속으로 자동 확정하지 않음(is_market_complex=False).
        - 구체적인 중고차 매매단지 키워드가 확인된 경우에만 CONFIRMED로 매매단지 소속 부여.
        """
        # 1. 파트너 직영 확인 출처
        if partner_operating_region:
            return RegionResolution(
                region_id=partner_operating_region,
                confidence="CONFIRMED_BY_PARTNER",
                is_market_complex=True,
                matched_rule="PARTNER_DIRECT_VERIFICATION",
                source_note="실무 파트너 직접 실차 및 소재지 확인",
            )

        if not raw_location or not raw_location.strip():
            return RegionResolution(
                region_id=None,
                confidence="UNCONFIRMED",
                is_market_complex=False,
                matched_rule="EMPTY_LOCATION",
            )

        clean_text = raw_location.strip()

        # 2. 매매단지(MARKET_COMPLEX) 정밀 키워드 매칭
        for reg_data in self._config_data.get("regions", []):
            if reg_data.get("region_type") == "MARKET_COMPLEX":
                keywords = reg_data.get("matched_complex_keywords", [])
                for kw in keywords:
                    if kw in clean_text:
                        return RegionResolution(
                            region_id=reg_data["region_id"],
                            confidence="CONFIRMED",
                            is_market_complex=True,
                            matched_rule=f"COMPLEX_KEYWORD_MATCH: {kw}",
                        )

        # 3. 매매단지 키워드가 없는 일반 주소/주거지인 경우
        return RegionResolution(
            region_id=None,
            confidence="UNCONFIRMED",
            is_market_complex=False,
            matched_rule="NO_COMPLEX_KEYWORD_FOUND",
            source_note="일반 주거지/행정구역 주소로 추정되어 매매단지 자동 편입 차단",
        )

    def resolve_region_from_text(self, raw_location: str) -> Optional[str]:
        """기존 인터페이스 호환용: 매매단지로 확정된 경우에만 region_id 반환."""
        res = self.resolve_region_detailed(raw_location)
        return res.region_id if res.is_market_complex else None

    def get_sales_target_listings(
        self, session: Session, target_region_id: str = "REGION_JANGANPYEONG"
    ) -> List[Listing]:
        """전국 매물 중 현재 판매 대상 지역(예: 장안평)에 위치한 매물만 필터링합니다."""
        stmt = (
            select(Listing)
            .where(Listing.normalized_region_id == target_region_id)
            .where(Listing.current_status.in_(["ACTIVE", "PRICE_CHANGED"]))
        )
        return list(session.scalars(stmt).all())
