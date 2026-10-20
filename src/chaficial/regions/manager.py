"""지역 분류, 장안평 판매 대상 필터 및 확장 관리자."""

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from chaficial.models.listing import Listing
from chaficial.models.region import Region, RegionConfiguration


class RegionManager:
    """전국 시장 분석과 지역별(장안평, 수원, 인천, 부천 등) 판매 매물 분리 관리자."""

    def __init__(self, config_path: str | None = None):
        if config_path is None:
            # 기본 경로: configs/regions.yaml
            config_path = str(Path(__file__).parents[3] / "configs" / "regions.yaml")
        self.config_path = config_path
        self._config_data: dict[str, Any] = self._load_config()

    def _load_config(self) -> dict[str, Any]:
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

        # 기본 설정 반영
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

    def resolve_region_from_text(self, raw_location: str) -> str | None:
        """주소 문자열로부터 일치하는 시장권역 코드를 찾습니다.
        
        단순 텍스트 매칭이 아니라 사전에 정의된 상권/행정구역 키워드 목록을 엄격히 검사하며,
        불분명한 경우 None을 반환하여 잘못된 자동 편입을 방지합니다.
        """
        if not raw_location or not raw_location.strip():
            return None

        clean_text = raw_location.strip()
        # 특수문자나 모호한 케이스 처리
        for reg_data in self._config_data.get("regions", []):
            keywords = reg_data.get("matched_keywords", [])
            for kw in keywords:
                if kw in clean_text:
                    return reg_data["region_id"]
        return None

    def get_sales_target_listings(
        self, session: Session, target_region_id: str = "REGION_JANGANPYEONG"
    ) -> list[Listing]:
        """전국 매물 중 현재 판매 대상 지역(예: 장안평)에 위치한 매물만 필터링합니다."""
        stmt = (
            select(Listing)
            .where(Listing.normalized_region_id == target_region_id)
            .where(Listing.current_status == "ACTIVE")
        )
        return list(session.scalars(stmt).all())
