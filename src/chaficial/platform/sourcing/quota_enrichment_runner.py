"""
Quota-Controlled Daily Enrichment Runner (CHA-FICIAL DIRECTIVE 115)
- Real cross-platform verification only (NO mock / synthetic generation).
- Strict daily budget enforcement: max 200 cars / day, explicit HTTP request budget per platform.
- Unvisited car state preservation (no false DELISTED).
- Checkpoint persistence and graceful backoff on rate-limits.
"""

import os
import time
import json
import random
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional

from chaficial.platform.sourcing.cross_platform_matcher import (
    CrossPlatformMatcher, MatchResult, MatchingStatus
)

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

    def can_process_car(self) -> bool:
        return self.state["cars_processed"] < self.daily_car_limit

    def can_request_kb(self) -> bool:
        return self.state["kb_requests_spent"] < self.kb_req_limit

    def can_request_encar(self) -> bool:
        return self.state["encar_requests_spent"] < self.encar_req_limit

    def record_car_processed(self, vehicle_id: str) -> None:
        self.state["cars_processed"] += 1
        if vehicle_id not in self.state["processed_vehicle_ids"]:
            self.state["processed_vehicle_ids"].append(vehicle_id)
        self._save()

    def record_kb_request(self) -> None:
        self.state["kb_requests_spent"] += 1
        self._save()

    def record_encar_request(self) -> None:
        self.state["encar_requests_spent"] += 1
        self._save()

class QuotaEnrichmentRunner:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db"):
        self.db_path = db_path
        self.matcher = CrossPlatformMatcher(db_path)
        self.checkpoint_path = Path("data/carmanager_raw/enrichment_checkpoint_real.json")
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.budget = DailyBudgetEnforcer(self.checkpoint_path, daily_car_limit=200, kb_req_limit=200, encar_req_limit=200)

    def get_real_sample_vehicles(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        Extracts vehicles with full plate or strong identifying info for real matching.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # 번호판이 있거나 카매니저 실데이터가 명확한 결손 차량 우선 추출
        c.execute("""
            SELECT v.id, v.plate_number, v.model_name, v.year, v.mileage, 
                   v.fuel_type, v.color, v.target_price,
                   l.listing_id as carmanager_carseq,
                   l.raw_seller_name as shop,
                   l.raw_seller_location as danji
            FROM vehicles v
            JOIN vehicle_listings l ON v.id = l.vehicle_id AND l.platform = 'CARMANAGER'
            WHERE v.is_demo = 0 
              AND v.plate_number IS NOT NULL 
              AND length(v.plate_number) >= 4
            ORDER BY v.id ASC
            LIMIT ?
        """, (count,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
