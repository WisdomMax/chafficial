# -*- coding: utf-8 -*-
"""
Chaficial & Chamart Dealership Authorization Registry (DIRECTIVE 137-R)
- Manages legally verified dealership contracts and advertising consent agreements.
- Replaces brittle substring matching ('더쿨' in shop_name) with structured registry verification.
- Supports seamless expansion to additional dealerships (Seonin, DK Dream, etc.) upon partner contract execution.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger("dealership_registry")

DEFAULT_REGISTRY_PATH = Path("data/authorized_partner_dealerships.json")
PACKAGE_REGISTRY_PATH = Path(__file__).resolve().parent / "authorized_partner_dealerships.json"

class DealershipRegistry:
    def __init__(self, registry_path: Path = DEFAULT_REGISTRY_PATH):
        self.registry_path = Path(registry_path)
        if not self.registry_path.exists() and PACKAGE_REGISTRY_PATH.exists():
            self.registry_path = PACKAGE_REGISTRY_PATH
        self.partners: List[Dict[str, Any]] = []
        self.pending: List[Dict[str, Any]] = []
        self._load_registry()

    def _load_registry(self):
        if not self.registry_path.exists():
            logger.warning(f"Dealership registry not found at {self.registry_path}, initializing empty.")
            self.partners = []
            self.pending = []
            return

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.partners = data.get("partner_dealerships", [])
            self.pending = data.get("pending_review_dealerships", [])
            logger.info(f"Loaded Dealership Registry: {len(self.partners)} active partners, {len(self.pending)} pending review.")
        except Exception as e:
            logger.error(f"Failed to load dealership registry: {e}")
            self.partners = []
            self.pending = []

    def verify_advertising_authorization(self, raw_shop_name: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        주어진 상사명에 대해 광고 및 판매 연동 권한이 공식 확인되었는지 정밀 검증.
        Returns:
            (is_authorized: bool, partner_info: Optional[Dict], reason: str)
        """
        if not raw_shop_name:
            return False, None, "EMPTY_SHOP_NAME"

        cleaned_shop = raw_shop_name.strip()

        # 1. 정규 활성 파트너 목록 대조
        for p in self.partners:
            # 계약 상태 및 광고 동의 상태 확인
            if p.get("contract_status") != "ACTIVE":
                continue
            consent = p.get("advertising_consent", {})
            if consent.get("status") != "APPROVED":
                continue

            # 매칭 키 비교 (공식 명칭, 매칭 키 목록)
            official_name = p.get("official_name", "")
            match_keys = p.get("danji_match_keys", [])

            if cleaned_shop == official_name or any(k in cleaned_shop for k in match_keys):
                return True, p, f"AUTHORIZED_BY_CONTRACT_{p.get('dealership_id')}"

        # 2. 검토 대상 상사 확인
        for pend in self.pending:
            official_name = pend.get("official_name", "")
            match_keys = pend.get("danji_match_keys", [])
            if cleaned_shop == official_name or any(k in cleaned_shop for k in match_keys):
                return False, pend, f"PENDING_CONTRACT_OR_UNAUTHORIZED_{pend.get('dealership_id')}"

        return False, None, "UNREGISTERED_MARKET_OBSERVED_DEALERSHIP"

    def get_authorized_partner_ids(self) -> List[str]:
        return [p["dealership_id"] for p in self.partners if p.get("contract_status") == "ACTIVE"]

    def get_authorized_official_names(self) -> List[str]:
        return [p["official_name"] for p in self.partners if p.get("contract_status") == "ACTIVE"]
