"""
Quota-Controlled Daily Enrichment Runner (CHA-FICIAL DIRECTIVE 116)
- Pure multi-attribute verification engine (NO mock / synthetic generation).
- Atomic daily budget enforcement: max 200 cars / day, explicit HTTP request budget per platform.
- Unvisited car state preservation (no false DELISTED).
- Atomic deduction prior to network execution.
"""

import os
import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional

from chaficial.platform.sourcing.atomic_budget_enforcer import SqliteAtomicBudgetEnforcer
from chaficial.platform.sourcing.cross_platform_matcher import (
    CrossPlatformMatcher, MatchResult, MatchingStatus
)

class QuotaExhaustedException(Exception):
    """Raised when daily car quota or platform HTTP budget is exhausted."""
    pass

class DailyBudgetEnforcer:
    def __init__(self, checkpoint_path: Path, daily_car_limit: int = 200, kb_req_limit: int = 200, encar_req_limit: int = 200):
        self.checkpoint_path = checkpoint_path
        self.daily_car_limit = daily_car_limit
        self.kb_req_limit = kb_req_limit
        self.encar_req_limit = encar_req_limit
        self.state = self._load()

    def _load(self) -> Dict[str, Any]:
        today = time.strftime("%Y-%m-%d")
        if self.checkpoint_path.exists():
            try:
                with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("date") == today:
                        return data
            except Exception:
                pass
        return {
            "date": today,
            "cars_processed": 0,
            "kb_requests_spent": 0,
            "encar_requests_spent": 0,
            "processed_vehicle_ids": []
        }

    def _save(self) -> None:
        with open(self.checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    def check_and_deduct_car(self, vehicle_id: str) -> None:
        if self.state["cars_processed"] >= self.daily_car_limit:
            raise QuotaExhaustedException(f"Daily car limit ({self.daily_car_limit}) reached.")
        self.state["cars_processed"] += 1
        if vehicle_id not in self.state["processed_vehicle_ids"]:
            self.state["processed_vehicle_ids"].append(vehicle_id)
        self._save()

    def check_and_deduct_kb(self) -> None:
        if self.state["kb_requests_spent"] >= self.kb_req_limit:
            raise QuotaExhaustedException(f"KB HTTP request budget ({self.kb_req_limit}) reached.")
        self.state["kb_requests_spent"] += 1
        self._save()

    def check_and_deduct_encar(self) -> None:
        if self.state["encar_requests_spent"] >= self.encar_req_limit:
            raise QuotaExhaustedException(f"Encar HTTP request budget ({self.encar_req_limit}) reached.")
        self.state["encar_requests_spent"] += 1
        self._save()

class QuotaEnrichmentRunner:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db", daily_limit: int = 200):
        self.db_path = db_path
        self.matcher = CrossPlatformMatcher(db_path)
        self.checkpoint_path = Path("data/carmanager_raw/enrichment_checkpoint_real.json")
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.budget = SqliteAtomicBudgetEnforcer(self.db_path, daily_car_limit=daily_limit, kb_req_limit=daily_limit, encar_req_limit=daily_limit)

    def process_vehicle_safe(self, vehicle: Dict[str, Any], kb_candidate: Optional[Dict[str, Any]] = None, encar_candidate: Optional[Dict[str, Any]] = None) -> Optional[MatchResult]:
        """
        Executes matching with atomic pre-network budget deduction.
        """
        v_id = vehicle["id"]
        # 1. 일일 차량 예산 원자적 검사 및 차감 (초과 시 예외 발생하여 네트워크 호출 차단)
        self.budget.check_and_deduct_car(v_id)

        # 2. KB차차차 조회 전 예산 검사 및 차감
        self.budget.check_and_deduct_kb()
        if kb_candidate:
            score, ev = self.matcher.calculate_match_score(vehicle, kb_candidate)
            status = self.matcher.classify_match(score, ev)
            if status in (MatchingStatus.VERIFIED, MatchingStatus.CANDIDATE):
                res = MatchResult(
                    vehicle_id=v_id,
                    plate_number=vehicle.get("plate_number"),
                    source_platform="KB_CHACHACHA",
                    external_car_id=kb_candidate.get("car_id"),
                    external_url=kb_candidate.get("url"),
                    advertised_price_manwon=kb_candidate.get("price"),
                    photo_urls=kb_candidate.get("photos", []),
                    status=status,
                    match_score=score,
                    match_evidence=ev,
                    matched_at=time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
                )
                self.matcher.record_match_in_db(res)
                return res

        # 3. 2순위 엔카 조회 전 예산 검사 및 차감
        self.budget.check_and_deduct_encar()
        if encar_candidate:
            score, ev = self.matcher.calculate_match_score(vehicle, encar_candidate)
            status = self.matcher.classify_match(score, ev)
            if status in (MatchingStatus.VERIFIED, MatchingStatus.CANDIDATE):
                res = MatchResult(
                    vehicle_id=v_id,
                    plate_number=vehicle.get("plate_number"),
                    source_platform="ENCAR",
                    external_car_id=encar_candidate.get("car_id"),
                    external_url=encar_candidate.get("url"),
                    advertised_price_manwon=encar_candidate.get("price"),
                    photo_urls=encar_candidate.get("photos", []),
                    status=status,
                    match_score=score,
                    match_evidence=ev,
                    matched_at=time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
                )
                self.matcher.record_match_in_db(res)
                return res

        return None
