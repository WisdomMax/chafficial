# -*- coding: utf-8 -*-
"""
Chaficial & Chamart Dealership Authorization Registry (DIRECTIVE 137-CLOSE)
- Manages legally verified dealership registrations and advertising consent agreements.
- Strictly eliminates substring matching ('더쿨' in shop_name); requires exact match or registered canonical aliases.
- Decouples CarManager dealer registration (inventory tracking) from Chamart advertising consent (public listing authorization).
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Set

logger = logging.getLogger("dealership_registry")

DEFAULT_REGISTRY_PATH = Path("data/authorized_partner_dealerships.json")
PACKAGE_REGISTRY_PATH = Path(__file__).resolve().parent / "authorized_partner_dealerships.json"


def normalize_shop_name(name: str) -> str:
    """
    상사명 비교용 정규화:
    - 앞뒤 공백 및 내부 연속 공백 제거
    """
    if not name:
        return ""
    return re.sub(r"\s+", " ", name).strip()


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
            logger.info(f"Loaded Dealership Registry: {len(self.partners)} partners, {len(self.pending)} pending review.")
        except Exception as e:
            logger.error(f"Failed to load dealership registry: {e}")
            self.partners = []
            self.pending = []

    def _get_exact_match_set(self, dealership: Dict[str, Any]) -> Set[str]:
        """
        상사의 고유 ID, 공식 명칭, 등록된 정확한 별칭 집합 반환 (부분문자열 절대 불허)
        """
        keys = set()
        dealership_id = dealership.get("dealership_id")
        if dealership_id:
            keys.add(dealership_id.strip())

        official_name = dealership.get("official_name")
        if official_name:
            keys.add(normalize_shop_name(official_name))

        exact_names = dealership.get("danji_exact_names", [])
        for n in exact_names:
            if n:
                keys.add(normalize_shop_name(n))

        return keys

    def inspect_dealership(self, raw_shop_name: str) -> Dict[str, Any]:
        """
        상사명 종합 감사:
        1. 파트너 상사 여부 (is_partner_dealership) - 카매니저 상사 등록 기준
        2. 광고·사진 게재 승인 여부 (is_advertising_approved) - 차마트 광고 동의 기준 (분리 검증)
        """
        if not raw_shop_name:
            return {
                "is_partner_dealership": False,
                "is_advertising_approved": False,
                "partner_info": None,
                "reason": "EMPTY_SHOP_NAME"
            }

        norm_shop = normalize_shop_name(raw_shop_name)

        # 1. 활성 파트너 상사 대조 (정확한 일치만 허용)
        for p in self.partners:
            match_set = self._get_exact_match_set(p)
            # 엄격한 동등 비교 (부분문자열 탐색 제거)
            if norm_shop in match_set:
                is_contract_active = (p.get("contract_status") == "ACTIVE")
                consent = p.get("advertising_consent", {})
                is_ad_approved = (consent.get("status") == "APPROVED")
                
                reason = f"PARTNER_MATCHED_{p.get('dealership_id')}"
                if not is_ad_approved:
                    reason += "_AD_CONSENT_PENDING"
                else:
                    reason += "_AD_APPROVED"

                return {
                    "is_partner_dealership": is_contract_active,
                    "is_advertising_approved": is_contract_active and is_ad_approved,
                    "partner_info": p,
                    "reason": reason
                }

        # 2. 협상·검토 중인 상사 대조 (정확한 일치만 허용)
        for pend in self.pending:
            match_set = self._get_exact_match_set(pend)
            if norm_shop in match_set:
                return {
                    "is_partner_dealership": False,
                    "is_advertising_approved": False,
                    "partner_info": pend,
                    "reason": f"PENDING_REVIEW_DEALERSHIP_{pend.get('dealership_id')}"
                }

        return {
            "is_partner_dealership": False,
            "is_advertising_approved": False,
            "partner_info": None,
            "reason": "UNREGISTERED_MARKET_OBSERVED_DEALERSHIP"
        }

    def identify_partner_dealership(self, raw_shop_name: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        차마트 운영 인벤토리 수집용: 공인 제휴/등록 상사 소속 매물인지 식별 (비공개 관리 풀 바인딩용)
        """
        res = self.inspect_dealership(raw_shop_name)
        return res["is_partner_dealership"], res["partner_info"], res["reason"]

    def verify_advertising_authorization(self, raw_shop_name: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        차마트 홈페이지 광고 게재용: 차마트 광고·사진 게재 권한이 'APPROVED'인지 엄격 검증
        (현재 더쿨모터스는 PENDING_CONFIRMATION이므로 False 반환)
        """
        res = self.inspect_dealership(raw_shop_name)
        return res["is_advertising_approved"], res["partner_info"], res["reason"]

    def get_authorized_partner_ids(self) -> List[str]:
        return [p["dealership_id"] for p in self.partners if p.get("contract_status") == "ACTIVE"]

    def get_authorized_official_names(self) -> List[str]:
        return [p["official_name"] for p in self.partners if p.get("contract_status") == "ACTIVE"]
