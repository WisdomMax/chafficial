import os
import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional

class QuotaExhaustedException(Exception):
    """Raised when daily car quota or platform HTTP budget is exhausted."""
    pass

class SqliteAtomicBudgetEnforcer:
    """
    SQLite-backed atomic budget enforcer.
    Prevents race conditions across multiple concurrent processes via ACID transactions.
    """
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db", daily_car_limit: int = 200, kb_req_limit: int = 200, encar_req_limit: int = 200):
        self.db_path = db_path
        self.daily_car_limit = daily_car_limit
        self.kb_req_limit = kb_req_limit
        self.encar_req_limit = encar_req_limit
        self._ensure_table()

    def _ensure_table(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS quota_ledger (
                ledger_date VARCHAR(10) PRIMARY KEY,
                cars_processed INTEGER NOT NULL DEFAULT 0,
                kb_requests_spent INTEGER NOT NULL DEFAULT 0,
                encar_requests_spent INTEGER NOT NULL DEFAULT 0,
                updated_at DATETIME NOT NULL
            );
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS quota_processed_vehicles (
                vehicle_id VARCHAR(36) PRIMARY KEY,
                processed_date VARCHAR(10) NOT NULL,
                processed_at DATETIME NOT NULL
            );
        """)
        conn.commit()
        conn.close()

    def _get_or_init_today(self, conn) -> str:
        today = time.strftime("%Y-%m-%d")
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO quota_ledger (ledger_date, cars_processed, kb_requests_spent, encar_requests_spent, updated_at)
            VALUES (?, 0, 0, 0, ?)
        """, (today, now_iso))
        return today

    def check_and_deduct_car(self, vehicle_id: str) -> None:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            with conn:
                today = self._get_or_init_today(conn)
                c = conn.cursor()
                
                # 중복 처리 확인
                c.execute("SELECT 1 FROM quota_processed_vehicles WHERE vehicle_id = ?", (vehicle_id,))
                if c.fetchone():
                    return  # 이미 처리된 차량은 예산 차감 없이 통과

                # 원자적 한도 검사 및 증가 (cars_processed < daily_car_limit 일 때만 1 증가)
                now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
                c.execute("""
                    UPDATE quota_ledger
                    SET cars_processed = cars_processed + 1, updated_at = ?
                    WHERE ledger_date = ? AND cars_processed < ?
                """, (now_iso, today, self.daily_car_limit))
                
                if c.rowcount == 0:
                    raise QuotaExhaustedException(f"Daily car quota limit ({self.daily_car_limit}) exhausted for date {today}.")

                c.execute("""
                    INSERT INTO quota_processed_vehicles (vehicle_id, processed_date, processed_at)
                    VALUES (?, ?, ?)
                """, (vehicle_id, today, now_iso))
        finally:
            conn.close()

    def check_and_deduct_kb(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            with conn:
                today = self._get_or_init_today(conn)
                c = conn.cursor()
                now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
                c.execute("""
                    UPDATE quota_ledger
                    SET kb_requests_spent = kb_requests_spent + 1, updated_at = ?
                    WHERE ledger_date = ? AND kb_requests_spent < ?
                """, (now_iso, today, self.kb_req_limit))
                
                if c.rowcount == 0:
                    raise QuotaExhaustedException(f"KB HTTP request budget ({self.kb_req_limit}) exhausted for date {today}.")
        finally:
            conn.close()

    def check_and_deduct_encar(self) -> None:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            with conn:
                today = self._get_or_init_today(conn)
                c = conn.cursor()
                now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+09:00")
                c.execute("""
                    UPDATE quota_ledger
                    SET encar_requests_spent = encar_requests_spent + 1, updated_at = ?
                    WHERE ledger_date = ? AND encar_requests_spent < ?
                """, (now_iso, today, self.encar_req_limit))
                
                if c.rowcount == 0:
                    raise QuotaExhaustedException(f"Encar HTTP request budget ({self.encar_req_limit}) exhausted for date {today}.")
        finally:
            conn.close()

    def get_status(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        today = time.strftime("%Y-%m-%d")
        c.execute("SELECT cars_processed, kb_requests_spent, encar_requests_spent, updated_at FROM quota_ledger WHERE ledger_date = ?", (today,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                "date": today,
                "cars_processed": row[0],
                "kb_requests_spent": row[1],
                "encar_requests_spent": row[2],
                "updated_at": row[3]
            }
        return {"date": today, "cars_processed": 0, "kb_requests_spent": 0, "encar_requests_spent": 0}
