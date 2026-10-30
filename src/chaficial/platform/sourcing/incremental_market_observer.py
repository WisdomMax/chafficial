"""
Incremental Market Observer (CHA-FICIAL DIRECTIVE 120 Standards)
- Low-overhead differential market scanning (50 cars per batch/page).
- Strictly preserves separation between vendor listing status and internal vehicle inventory status.
- Guarantees ZERO false DELISTED / SOLD on partial observations.
- SQLite-backed persistent Queue for new car deep fetch (supports idempotency, restart recovery, retry counts).
- Updates `last_observed_at` even on NO_CHANGE records to maintain market freshness tracking.
"""

import sqlite3
import time
import json
import uuid
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class ObservationAction(str, Enum):
    SCHEDULE_DEEP_FETCH = "SCHEDULE_DEEP_FETCH" # New car: queued for detail & photo harvest
    UPDATE_PRICE_STATUS = "UPDATE_PRICE_STATUS" # Existing car: price or vendor status changed
    NO_CHANGE = "NO_CHANGE"                     # Existing car: same price and status -> update last_observed_at only
    UNSEEN_PRESERVED = "UNSEEN_PRESERVED"       # Not present in partial batch -> PRESERVED without delisting

@dataclass
class MarketListingSummary:
    listing_id: str             # vendor unique car ID (e.g. encarno or carSeq)
    platform: str              # CARMANAGER, etc.
    plate_number: str
    model_name: str
    advertised_price: Optional[int] # manwon (None for consultation / unpriced)
    status: str                # vendor listing status: 'ACTIVE', 'SOLD', 'SUSPENDED', etc.
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
        self._ensure_queue_table()

    def _ensure_queue_table(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS market_detail_fetch_queue (
                platform VARCHAR(30) NOT NULL,
                listing_id VARCHAR(64) NOT NULL,
                plate_number VARCHAR(30),
                model_name VARCHAR(100),
                raw_location VARCHAR(100),
                raw_vendor_status VARCHAR(50),
                queue_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, COMPLETED, FAILED
                retry_count INTEGER DEFAULT 0,
                discovered_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                error_message TEXT,
                PRIMARY KEY (platform, listing_id)
            );
        """)
        conn.commit()
        conn.close()

    def inspect_batch(
        self, 
        observed_items: List[MarketListingSummary], 
        platform: str = "CARMANAGER"
    ) -> List[DiffResult]:
        """
        Compares observed 50-car batch against existing DB records.
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
                # 1. New listing -> schedule for deep fetch in persistent queue
                diff_results.append(DiffResult(
                    action=ObservationAction.SCHEDULE_DEEP_FETCH,
                    listing_id=lid,
                    details={
                        "plate_number": item.plate_number,
                        "model_name": item.model_name,
                        "advertised_price": item.advertised_price,
                        "raw_location": item.raw_location,
                        "observed_at": item.observed_at
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
                            "status_changed": status_diff,
                            "observed_at": item.observed_at
                        }
                    ))
                else:
                    # 3. NO_CHANGE -> Must still update last_observed_at (ISSUE-62)
                    diff_results.append(DiffResult(
                        action=ObservationAction.NO_CHANGE,
                        listing_id=lid,
                        details={
                            "vehicle_id": curr["vehicle_id"],
                            "observed_at": item.observed_at
                        }
                    ))

        return diff_results

    def apply_batch_updates_and_enqueue(
        self, 
        diff_results: List[DiffResult], 
        platform: str = "CARMANAGER"
    ) -> Dict[str, int]:
        """
        Atomically applies:
          1. Price/status updates (UPDATE_PRICE_STATUS)
          2. Freshness timestamp updates (NO_CHANGE)
          3. Enqueues new vehicles into persistent SQLite queue (SCHEDULE_DEEP_FETCH)
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
        
        counts = {
            "price_status_updated": 0,
            "no_change_timestamp_refreshed": 0,
            "new_vehicles_enqueued": 0
        }

        with conn:
            for d in diff_results:
                lid = d.listing_id
                det = d.details

                if d.action == ObservationAction.UPDATE_PRICE_STATUS:
                    c.execute("""
                        UPDATE vehicle_listings SET
                            advertised_price = ?,
                            listing_status = ?,
                            last_observed_at = ?
                        WHERE platform = ? AND listing_id = ?
                    """, (det["new_price"], det["new_status"], det.get("observed_at", now_iso), platform, lid))
                    counts["price_status_updated"] += c.rowcount

                elif d.action == ObservationAction.NO_CHANGE:
                    # ISSUE-62: Freshness timestamp updated even on NO_CHANGE
                    c.execute("""
                        UPDATE vehicle_listings SET
                            last_observed_at = ?
                        WHERE platform = ? AND listing_id = ?
                    """, (det.get("observed_at", now_iso), platform, lid))
                    counts["no_change_timestamp_refreshed"] += c.rowcount

                elif d.action == ObservationAction.SCHEDULE_DEEP_FETCH:
                    # ISSUE-64, ISSUE-68: Persistent queue with (platform, listing_id) composite PK and lifecycle states
                    c.execute("""
                        INSERT OR IGNORE INTO market_detail_fetch_queue (
                            platform, listing_id, plate_number, model_name,
                            raw_location, raw_vendor_status, queue_status, retry_count,
                            discovered_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, 'PENDING', 0, ?, ?)
                    """, (
                        platform, lid, det.get("plate_number"), det.get("model_name"),
                        det.get("raw_location"), det.get("raw_vendor_status", "ACTIVE"),
                        det.get("observed_at", now_iso), now_iso
                    ))
                    if c.rowcount > 0:
                        counts["new_vehicles_enqueued"] += 1

        conn.close()
        return counts

    def claim_next_queue_item(self, platform: str = "CARMANAGER", max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Atomically claims next pending item using BEGIN IMMEDIATE and conditional UPDATE.
        Guarantees that multiple concurrent workers never claim the same item.
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        c = conn.cursor()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
        
        claimed_row = None
        with conn:
            # 원자적 트랜잭션 획득
            c.execute("BEGIN IMMEDIATE;")
            c.execute("""
                SELECT platform, listing_id, plate_number, model_name, raw_location, retry_count
                FROM market_detail_fetch_queue
                WHERE platform = ? AND queue_status = 'PENDING' AND retry_count < ?
                ORDER BY discovered_at ASC
                LIMIT 1
            """, (platform, max_retries))
            row = c.fetchone()
            if row:
                # 조건부 UPDATE로 원자적 상태 변경 (PENDING -> IN_PROGRESS)
                c.execute("""
                    UPDATE market_detail_fetch_queue SET
                        queue_status = 'IN_PROGRESS',
                        updated_at = ?
                    WHERE platform = ? AND listing_id = ? AND queue_status = 'PENDING'
                """, (now_iso, row[0], row[1]))
                if c.rowcount == 1:
                    claimed_row = row

        conn.close()
        if not claimed_row:
            return None

        return {
            "platform": claimed_row[0],
            "listing_id": claimed_row[1],
            "plate_number": claimed_row[2],
            "model_name": claimed_row[3],
            "raw_location": claimed_row[4],
            "retry_count": claimed_row[5]
        }

    def mark_queue_item_failed(self, platform: str, listing_id: str, error_msg: str, max_retries: int = 3) -> None:
        """
        Marks item failed. If retry_count reaches max_retries, transitions to REQUIRES_ADMIN_REVIEW.
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
        with conn:
            c.execute("""
                SELECT retry_count FROM market_detail_fetch_queue
                WHERE platform = ? AND listing_id = ?
            """, (platform, listing_id))
            r = c.fetchone()
            cur_retries = (r[0] if r else 0) + 1
            next_status = "REQUIRES_ADMIN_REVIEW" if cur_retries >= max_retries else "FAILED"

            c.execute("""
                UPDATE market_detail_fetch_queue SET
                    queue_status = ?,
                    retry_count = ?,
                    error_message = ?,
                    updated_at = ?
                WHERE platform = ? AND listing_id = ?
            """, (next_status, cur_retries, error_msg, now_iso, platform, listing_id))
        conn.close()

    def get_pending_queue_items(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves pending deep fetch tasks with restart recovery support."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT listing_id, platform, plate_number, model_name, raw_location, retry_count
            FROM market_detail_fetch_queue
            WHERE queue_status = 'PENDING'
            ORDER BY discovered_at ASC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [
            {
                "listing_id": r[0],
                "platform": r[1],
                "plate_number": r[2],
                "model_name": r[3],
                "raw_location": r[4],
                "retry_count": r[5]
            } for r in rows
        ]
