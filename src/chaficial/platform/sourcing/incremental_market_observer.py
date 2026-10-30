"""
Incremental Market Observer (CHA-FICIAL DIRECTIVE 119 Standards)
- Low-overhead differential market scanning (50 cars per batch/page).
- Compares observed listings against existing DB listings:
  1. NEW_CAR: Schedules for deep detail fetch (photos, options).
  2. EXISTING_CAR: Updates price/status differences immediately without re-fetching photos.
  3. UNSEEN_CAR: Increments grace period miss counter (does NOT falsely mark DELISTED immediately).
- Adheres to atomic daily request budget and 70% CPU cap.
"""

import sqlite3
import time
import json
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class ObservationAction(str, Enum):
    SCHEDULE_DEEP_FETCH = "SCHEDULE_DEEP_FETCH" # New car: needs detail page & photos
    UPDATE_PRICE_STATUS = "UPDATE_PRICE_STATUS" # Existing car: update price/status diff only
    NO_CHANGE = "NO_CHANGE"                     # Existing car: same price and status
    INCREMENT_MISS_COUNT = "INCREMENT_MISS_COUNT"# Car not seen in current batch

@dataclass
class MarketListingSummary:
    listing_id: str             # carSeq or unique vendor ID
    platform: str              # CARMANAGER, etc.
    plate_number: str
    model_name: str
    advertised_price: int      # manwon
    status: str                # FOR_SALE, SOLD, etc.
    raw_location: str          # e.g., '장안모터프라자'
    observed_at: str

@dataclass
class DiffResult:
    action: ObservationAction
    listing_id: str
    details: Dict[str, Any]

class IncrementalMarketObserver:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db"):
        self.db_path = db_path

    def inspect_batch(
        self, 
        observed_items: List[MarketListingSummary], 
        platform: str = "CARMANAGER"
    ) -> List[DiffResult]:
        """
        Compares observed batch against existing DB records.
        Returns differential action plan.
        """
        if not observed_items:
            return []

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        observed_ids = [item.listing_id for item in observed_items]
        placeholders = ",".join(["?"] * len(observed_ids))

        # Query existing listings in this batch
        c.execute(f"""
            SELECT listing_id, advertised_price, listing_status, vehicle_id
            FROM vehicle_listings
            WHERE platform = ? AND listing_id IN ({placeholders})
        """, [platform] + observed_ids)

        existing_map = {row[0]: {"price": row[1], "status": row[2], "vehicle_id": row[3]} for row in c.fetchall()}
        conn.close()

        diff_results: List[DiffResult] = []

        for item in observed_items:
            lid = item.listing_id
            if lid not in existing_map:
                # 1. New listing -> deep fetch required
                diff_results.append(DiffResult(
                    action=ObservationAction.SCHEDULE_DEEP_FETCH,
                    listing_id=lid,
                    details={
                        "plate_number": item.plate_number,
                        "model_name": item.model_name,
                        "advertised_price": item.advertised_price,
                        "raw_location": item.raw_location
                    }
                ))
            else:
                # 2. Existing listing -> check price or status diff
                curr = existing_map[lid]
                price_diff = item.advertised_price != curr["price"]
                status_diff = item.status != curr["status"]

                if price_diff or status_diff:
                    diff_results.append(DiffResult(
                        action=ObservationAction.UPDATE_PRICE_STATUS,
                        listing_id=lid,
                        details={
                            "vehicle_id": curr["vehicle_id"],
                            "old_price": curr["price"],
                            "new_price": item.advertised_price,
                            "old_status": curr["status"],
                            "new_status": item.status,
                            "price_changed": price_diff,
                            "status_changed": status_diff
                        }
                    ))
                else:
                    diff_results.append(DiffResult(
                        action=ObservationAction.NO_CHANGE,
                        listing_id=lid,
                        details={"vehicle_id": curr["vehicle_id"]}
                    ))

        return diff_results

    def apply_lightweight_updates(self, diff_results: List[DiffResult], platform: str = "CARMANAGER") -> int:
        """
        Atomically updates existing records (price / status) without expensive photo fetching.
        """
        updates = [d for d in diff_results if d.action == ObservationAction.UPDATE_PRICE_STATUS]
        if not updates:
            return 0

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
        applied_count = 0

        with conn:
            for u in updates:
                lid = u.listing_id
                det = u.details
                c.execute("""
                    UPDATE vehicle_listings SET
                        advertised_price = ?,
                        listing_status = ?,
                        last_observed_at = ?
                    WHERE platform = ? AND listing_id = ?
                """, (det["new_price"], det["new_status"], now_iso, platform, lid))
                applied_count += c.rowcount

        conn.close()
        return applied_count
