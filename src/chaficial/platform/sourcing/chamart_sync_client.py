"""
Chaficial to Chamart Cloudflare Auto-Sync Client (DIRECTIVE 130 TASK 3)
- HTTPS API based incremental synchronization
- Outbox pattern for offline resilience and idempotency
- Exponential backoff retry logic
- Protects admin-managed prices and public states
"""

import os
import sys
import json
import time
import sqlite3
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

DEFAULT_PROD_URL = "https://chamart.cc"

class ChamartSyncClient:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db", target_url: str = DEFAULT_PROD_URL, api_key: Optional[str] = None):
        self.db_path = db_path
        self.target_url = (os.environ.get("CHAMART_API_URL") or target_url).rstrip("/")
        # DIRECTIVE 130 P0 보안 보정: 하드코딩 기본 토큰 폐기, 환경변수 또는 명시적 인자 필수
        self.api_key = os.environ.get("CHAMART_SYNC_API_KEY") or api_key
        if not self.api_key:
            sec_file = Path("data/.chamart_sync_secret")
            if sec_file.exists():
                self.api_key = sec_file.read_text(encoding="utf-8").strip()
        self._init_outbox()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_outbox(self):
        """로컬 오프라인 보존용 아웃박스 테이블 초기화"""
        conn = self._get_connection()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS chamart_sync_outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                retry_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                created_at DATETIME NOT NULL,
                sent_at DATETIME
            );
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_sync_outbox_status ON chamart_sync_outbox(status);")
        conn.commit()
        conn.close()

    def enqueue_vehicle_sync(self, vehicle_dict: Dict[str, Any]):
        """차량 정보 동기화 아웃박스 큐 적재"""
        conn = self._get_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        # 멱등성 보장: 동일 entity_id가 PENDING 상태이면 최신 페이로드로 갱신
        c.execute("SELECT id FROM chamart_sync_outbox WHERE entity_type = 'VEHICLE' AND entity_id = ? AND status = 'PENDING';", (vehicle_dict["id"],))
        existing = c.fetchone()
        
        if existing:
            c.execute("UPDATE chamart_sync_outbox SET payload_json = ?, created_at = ? WHERE id = ?;",
                      (json.dumps(vehicle_dict, ensure_ascii=False), now, existing[0]))
        else:
            c.execute("""
                INSERT INTO chamart_sync_outbox (entity_type, entity_id, payload_json, status, created_at)
                VALUES ('VEHICLE', ?, ?, 'PENDING', ?);
            """, (vehicle_dict["id"], json.dumps(vehicle_dict, ensure_ascii=False), now))
            
        conn.commit()
        conn.close()

    def enqueue_photos_sync(self, vehicle_id: str, photos: List[Dict[str, Any]]):
        """실제 사진 메타데이터 동기화 아웃박스 적재"""
        conn = self._get_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        payload = {"vehicle_id": vehicle_id, "photos": photos}
        
        c.execute("SELECT id FROM chamart_sync_outbox WHERE entity_type = 'PHOTO' AND entity_id = ? AND status = 'PENDING';", (vehicle_id,))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE chamart_sync_outbox SET payload_json = ?, created_at = ? WHERE id = ?;",
                      (json.dumps(payload, ensure_ascii=False), now, existing[0]))
        else:
            c.execute("""
                INSERT INTO chamart_sync_outbox (entity_type, entity_id, payload_json, status, created_at)
                VALUES ('PHOTO', ?, ?, 'PENDING', ?);
            """, (vehicle_id, json.dumps(payload, ensure_ascii=False), now))
            
        conn.commit()
        conn.close()

    def enqueue_status_sync(self, vehicle_ids: List[str], status: str, reason: str = "OFFLINE_SYNC"):
        """판매완료/광고중지 상태 동기화 아웃박스 적재"""
        conn = self._get_connection()
        c = conn.cursor()
        now = datetime.now().isoformat()
        payload = {"vehicle_ids": vehicle_ids, "status": status, "reason": reason}
        batch_id = f"STATUS_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        c.execute("""
            INSERT INTO chamart_sync_outbox (entity_type, entity_id, payload_json, status, created_at)
            VALUES ('STATUS', ?, ?, 'PENDING', ?);
        """, (batch_id, json.dumps(payload, ensure_ascii=False), now))
        conn.commit()
        conn.close()

    def _send_request(self, endpoint: str, payload: Dict[str, Any], max_retries: int = 3) -> Dict[str, Any]:
        """HTTPS API 안전 호출 (Bearer 토큰 인증 + SHA-256 멱등성 키 + 지수 백오프 재시도)"""
        url = f"{self.target_url}{endpoint}"
        raw_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        idempotency_key = hashlib.sha256(raw_bytes).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": idempotency_key,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (ChaficialSync)"
        }

        last_error = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url, data=raw_bytes, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body)
            except urllib.error.HTTPError as e:
                # 4xx 클라이언트 에러는 재시도하지 않고 즉시 예외 발생
                if 400 <= e.code < 500:
                    err_body = e.read().decode("utf-8") if e.fp else str(e)
                    raise RuntimeError(f"HTTP {e.code}: {err_body}")
                last_error = e
            except Exception as e:
                last_error = e

            # 5xx 또는 네트워크 단절 시 지수 백오프 대기 (2^attempt * 0.5초)
            if attempt < max_retries - 1:
                backoff_sec = (2 ** attempt) * 0.5
                time.sleep(backoff_sec)

        raise last_error or RuntimeError("Request failed after retries")

    def drain_outbox(self, max_batch_size: int = 50) -> Dict[str, int]:
        """아웃박스 누락분 자동 전송 및 재시도 처리 (지수 백오프 적용)"""
        conn = self._get_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT id, entity_type, entity_id, payload_json, retry_count
            FROM chamart_sync_outbox
            WHERE status = 'PENDING' OR (status = 'FAILED' AND retry_count < 5)
            ORDER BY id ASC
            LIMIT ?;
        """, (max_batch_size,))
        rows = c.fetchall()
        
        stats = {"sent": 0, "failed": 0, "total": len(rows)}
        
        # 차량 묶음 배치 처리
        vehicle_items = [r for r in rows if r[1] == 'VEHICLE']
        other_items = [r for r in rows if r[1] != 'VEHICLE']
        
        if vehicle_items:
            v_payloads = [json.loads(r[3]) for r in vehicle_items]
            try:
                res = self._send_request("/api/sync/vehicles", {
                    "vehicles": v_payloads,
                    "source": "CHAFICIAL_MAC_MINI",
                    "timestamp": datetime.now().isoformat()
                })
                now = datetime.now().isoformat()
                item_ids = [r[0] for r in vehicle_items]
                c.execute(f"UPDATE chamart_sync_outbox SET status = 'SENT', sent_at = ? WHERE id IN ({','.join(['?']*len(item_ids))});",
                          [now] + item_ids)
                stats["sent"] += len(vehicle_items)
            except Exception as e:
                err_msg = str(e)
                for r in vehicle_items:
                    c.execute("""
                        UPDATE chamart_sync_outbox 
                        SET status = 'FAILED', retry_count = retry_count + 1, last_error = ?
                        WHERE id = ?;
                    """, (err_msg, r[0]))
                stats["failed"] += len(vehicle_items)

        # 개별 사진 및 상태 항목 처리
        for r in other_items:
            row_id, entity_type, entity_id, payload_json, retry_count = r
            endpoint = "/api/sync/photos" if entity_type == 'PHOTO' else "/api/sync/status"
            try:
                payload = json.loads(payload_json)
                res = self._send_request(endpoint, payload)
                now = datetime.now().isoformat()
                c.execute("UPDATE chamart_sync_outbox SET status = 'SENT', sent_at = ? WHERE id = ?;", (now, row_id))
                stats["sent"] += 1
            except Exception as e:
                c.execute("""
                    UPDATE chamart_sync_outbox 
                    SET status = 'FAILED', retry_count = retry_count + 1, last_error = ?
                    WHERE id = ?;
                """, (str(e), row_id))
                stats["failed"] += 1

        conn.commit()
        conn.close()
        return stats

    def check_remote_health(self) -> Dict[str, Any]:
        """차마트 원격 동기화 상태 헬스체크"""
        url = f"{self.target_url}/api/sync/status"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (ChaficialSync)"
            },
            method="GET"
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read().decode("utf-8"))
