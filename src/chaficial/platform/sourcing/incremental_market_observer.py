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

    def ensure_schema(self):
        """명시적 스키마 초기화 메서드"""
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
                queue_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, IN_PROGRESS, COMPLETED, FAILED, REQUIRES_ADMIN_REVIEW
                retry_count INTEGER DEFAULT 0,
                discovered_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                error_message TEXT,
                worker_id VARCHAR(50),
                claim_token VARCHAR(64),
                lease_expires_at DATETIME,
                next_retry_at DATETIME,
                PRIMARY KEY (platform, listing_id)
            );
        """)
        # 컬럼 마이그레이션 (DIRECTIVE 124 TASK 2, ISSUE-83 & DIRECTIVE 126 TASK 2, ISSUE-94)
        for col, col_type in [("worker_id", "VARCHAR(50)"), ("claim_token", "VARCHAR(64)"), ("lease_expires_at", "DATETIME"), ("next_retry_at", "DATETIME")]:
            try:
                c.execute(f"ALTER TABLE market_detail_fetch_queue ADD COLUMN {col} {col_type};")
            except sqlite3.OperationalError:
                pass
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

    def claim_next_queue_item(
        self, 
        platform: str = "CARMANAGER", 
        worker_id: Optional[str] = None,
        lease_seconds: int = 300,
        max_retries: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Atomically claims next pending or retryable failed item using BEGIN IMMEDIATE and conditional UPDATE.
        DIRECTIVE 125 TASK 2: Supports queue_status IN ('PENDING', 'FAILED') for retry cycle (ISSUE-88).
        Issues a unique claim_token and sets lease_expires_at.
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        c = conn.cursor()
        now_epoch = time.time()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime(now_epoch))
        lease_expires_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime(now_epoch + lease_seconds))
        active_worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        claim_token = str(uuid.uuid4())
        
        claimed_row = None
        with conn:
            c.execute("BEGIN IMMEDIATE;")
            # DIRECTIVE 126 TASK 2 (ISSUE-94): PENDING 및 재시도 기한(next_retry_at) 도래한 FAILED 상태 선점
            c.execute("""
                SELECT platform, listing_id, plate_number, model_name, raw_location, retry_count, queue_status
                FROM market_detail_fetch_queue
                WHERE platform = ? 
                  AND (
                      queue_status = 'PENDING' 
                      OR (queue_status = 'FAILED' AND (next_retry_at IS NULL OR next_retry_at <= ?))
                  )
                  AND retry_count < ?
                ORDER BY CASE WHEN queue_status = 'PENDING' THEN 0 ELSE 1 END, discovered_at ASC
                LIMIT 1
            """, (platform, now_iso, max_retries))
            row = c.fetchone()
            if row:
                # 조건부 UPDATE로 원자적 상태 변경 (IN_PROGRESS with lease & token, next_retry_at 리셋)
                c.execute("""
                    UPDATE market_detail_fetch_queue SET
                        queue_status = 'IN_PROGRESS',
                        worker_id = ?,
                        claim_token = ?,
                        lease_expires_at = ?,
                        next_retry_at = NULL,
                        updated_at = ?
                    WHERE platform = ? AND listing_id = ? 
                      AND (
                          queue_status = 'PENDING' 
                          OR (queue_status = 'FAILED' AND (next_retry_at IS NULL OR next_retry_at <= ?))
                      )
                """, (active_worker_id, claim_token, lease_expires_iso, now_iso, row[0], row[1], now_iso))
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
            "retry_count": claimed_row[5],
            "prior_status": claimed_row[6],
            "worker_id": active_worker_id,
            "claim_token": claim_token,
            "lease_expires_at": lease_expires_iso
        }

    def mark_queue_item_completed(self, platform: str, listing_id: str, claim_token: str) -> bool:
        """
        Marks item completed. 
        DIRECTIVE 125/126 TASK 2: claim_token is STRICTLY REQUIRED (None prohibited).
        DIRECTIVE 126 TASK 2: lease_expires_at MUST NOT be NULL and must be active (lease_expires_at >= now).
        """
        if not claim_token or not isinstance(claim_token, str):
            raise ValueError("claim_token is strictly required to mark queue item completed.")

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
        with conn:
            c.execute("""
                UPDATE market_detail_fetch_queue SET
                    queue_status = 'COMPLETED',
                    worker_id = NULL,
                    claim_token = NULL,
                    lease_expires_at = NULL,
                    next_retry_at = NULL,
                    updated_at = ?
                WHERE platform = ? 
                  AND listing_id = ? 
                  AND claim_token = ? 
                  AND queue_status = 'IN_PROGRESS'
                  AND lease_expires_at IS NOT NULL
                  AND lease_expires_at >= ?
            """, (now_iso, platform, listing_id, claim_token, now_iso))
            success = (c.rowcount > 0)
        conn.close()
        return success

    def mark_queue_item_failed(
        self, 
        platform: str, 
        listing_id: str, 
        error_msg: str, 
        claim_token: str,
        max_retries: int = 3
    ) -> bool:
        """
        Marks item failed. 
        DIRECTIVE 125/126 TASK 2: claim_token is strictly required.
        DIRECTIVE 126 TASK 2 (ISSUE-94): 
        - lease_expires_at MUST NOT be NULL and must be active (lease_expires_at >= now).
        - Assigns backoff next_retry_at = now + 60s * retry_count.
        - Resets worker_id, claim_token, lease_expires_at so it can be reclaimed after backoff.
        - If retry_count reaches max_retries, permanently transitions to REQUIRES_ADMIN_REVIEW.
        """
        if not claim_token or not isinstance(claim_token, str):
            raise ValueError("claim_token is strictly required to mark queue item failed.")

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now_epoch = time.time()
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime(now_epoch))
        success = False
        try:
            with conn:
                c.execute("""
                    SELECT retry_count FROM market_detail_fetch_queue 
                    WHERE platform = ? AND listing_id = ? AND claim_token = ? AND queue_status = 'IN_PROGRESS'
                      AND lease_expires_at IS NOT NULL
                      AND lease_expires_at >= ?
                """, (platform, listing_id, claim_token, now_iso))
                r = c.fetchone()
                if r:
                    cur_retries = r[0] + 1
                    if cur_retries >= max_retries:
                        next_status = "REQUIRES_ADMIN_REVIEW"
                        next_retry_iso = None
                    else:
                        next_status = "FAILED"
                        backoff_seconds = 60 * cur_retries
                        next_retry_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00", time.localtime(now_epoch + backoff_seconds))

                    c.execute("""
                        UPDATE market_detail_fetch_queue SET
                            queue_status = ?,
                            retry_count = ?,
                            error_message = ?,
                            worker_id = NULL,
                            claim_token = NULL,
                            lease_expires_at = NULL,
                            next_retry_at = ?,
                            updated_at = ?
                        WHERE platform = ? AND listing_id = ? AND claim_token = ?
                    """, (next_status, cur_retries, error_msg, next_retry_iso, now_iso, platform, listing_id, claim_token))
                    success = (c.rowcount > 0)
        finally:
            conn.close()
        return success

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
