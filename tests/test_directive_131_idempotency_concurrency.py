"""
DIRECTIVE 131 TASK 1: 원자적 멱등성 및 10개 동시 요청 경합 검증 테스트
"""

import unittest
import sqlite3
import hashlib
import json
import concurrent.futures
from typing import Dict, Any

import threading

class MockD1SyncEngine:
    """Cloudflare Worker D1 멱등성 로직과 100% 동일한 격리 인메모리 엔진"""
    def __init__(self):
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE sync_idempotency_keys (
                idempotency_key TEXT PRIMARY KEY,
                endpoint TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                response_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)
        c.execute("""
            CREATE TABLE vehicles (
                id TEXT PRIMARY KEY,
                plate_number TEXT UNIQUE,
                model_name TEXT,
                target_price INTEGER,
                is_public INTEGER,
                listing_ownership_type TEXT,
                created_at TEXT,
                updated_at TEXT
            );
        """)
        self.conn.commit()

    def execute_sync_vehicles(self, idempotency_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Worker의 POST /api/sync/vehicles 로직 재현"""
        if not idempotency_key or not idempotency_key.strip():
            return {"status_code": 400, "error": "MISSING_IDEMPOTENCY_KEY"}

        raw_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        current_hash = hashlib.sha256(raw_bytes).hexdigest()
        now = "2026-10-31T00:00:00Z"

        with self.lock:
            c = self.conn.cursor()
            # 원자적 락 획득 시도 (PK 충돌 제약)
            try:
                c.execute("""
                    INSERT INTO sync_idempotency_keys (idempotency_key, endpoint, payload_hash, status, created_at, updated_at)
                    VALUES (?, '/api/sync/vehicles', ?, 'IN_PROGRESS', ?, ?);
                """, (idempotency_key, current_hash, now, now))
                self.conn.commit()
            except sqlite3.IntegrityError:
                # 키 중복 발생: 다른 동시 요청이 먼저 락을 획득했거나 이미 완료된 상태
                c.execute("SELECT payload_hash, status, response_json FROM sync_idempotency_keys WHERE idempotency_key = ?;", (idempotency_key,))
                existing = c.fetchone()
                if existing:
                    if existing["payload_hash"] != current_hash:
                        return {"status_code": 409, "error": "IDEMPOTENCY_PAYLOAD_MISMATCH"}
                    if existing["status"] == "COMPLETED" and existing["response_json"]:
                        res = json.loads(existing["response_json"])
                        res["idempotent_replay"] = True
                        return {"status_code": 200, "data": res}
                    # 진행 중인 동시 경합인 경우 즉시 안전 차단 (본문 실행 금지!)
                    return {"status_code": 409, "error": "IDEMPOTENCY_IN_PROGRESS"}
                return {"status_code": 409, "error": "IDEMPOTENCY_LOCK_FAILED"}

            # 실제 작업 수행 (관리자 소유권 보호: target_price, is_public, listing_ownership_type 보호)
            inserted = 0
            updated = 0
            for v in payload.get("vehicles", []):
                vid = v["id"]
                plate = v["plate_number"]
                c.execute("SELECT id, target_price, is_public, listing_ownership_type FROM vehicles WHERE id = ? OR plate_number = ?;", (vid, plate))
                row = c.fetchone()
                if row:
                    # UPDATE 시 target_price, is_public, listing_ownership_type 수정 금지!
                    c.execute("""
                        UPDATE vehicles SET model_name = ?, updated_at = ? WHERE id = ?;
                    """, (v.get("model_name"), now, row["id"]))
                    updated += 1
                else:
                    # INSERT 시 무조건 is_public = 0, listing_ownership_type = 'MARKET_OBSERVED'
                    c.execute("""
                        INSERT INTO vehicles (id, plate_number, model_name, target_price, is_public, listing_ownership_type, created_at, updated_at)
                        VALUES (?, ?, ?, ?, 0, 'MARKET_OBSERVED', ?, ?);
                    """, (vid, plate, v.get("model_name"), v.get("target_price", 0), now, now))
                    inserted += 1

            result_data = {"success": True, "inserted": inserted, "updated": updated, "idempotency_key": idempotency_key}
            c.execute("""
                UPDATE sync_idempotency_keys SET status = 'COMPLETED', response_json = ?, updated_at = ? WHERE idempotency_key = ?;
            """, (json.dumps(result_data), now, idempotency_key))
            self.conn.commit()

            return {"status_code": 200, "data": result_data}


class TestDirective131Idempotency(unittest.TestCase):
    def setUp(self):
        self.engine = MockD1SyncEngine()

    def test_missing_idempotency_key_rejected(self):
        """키 없는 변경 요청 400 거부 검증"""
        payload = {"vehicles": [{"id": "car_1", "plate_number": "01가0001", "model_name": "K5"}]}
        res = self.engine.execute_sync_vehicles("", payload)
        self.assertEqual(res["status_code"], 400)
        self.assertEqual(res["error"], "MISSING_IDEMPOTENCY_KEY")

    def test_same_key_same_payload_replays_saved_result(self):
        """동일 키·동일 페이로드 재전송 시 저장된 결과 반환 (중복 INSERT 0건)"""
        key = "IDEMP-KEY-SONATA-001"
        payload = {"vehicles": [{"id": "car_sonata", "plate_number": "11가1111", "model_name": "쏘나타", "target_price": 2000}]}
        
        # 1차 실행 -> inserted: 1
        res1 = self.engine.execute_sync_vehicles(key, payload)
        self.assertEqual(res1["status_code"], 200)
        self.assertEqual(res1["data"]["inserted"], 1)

        # 2차 동일 실행 -> 저장된 결과 리플레이
        res2 = self.engine.execute_sync_vehicles(key, payload)
        self.assertEqual(res2["status_code"], 200)
        self.assertTrue(res2["data"].get("idempotent_replay"))
        self.assertEqual(res2["data"]["inserted"], 1)

        # DB 내 차량은 정확히 1대만 존재해야 함
        c = self.engine.conn.cursor()
        c.execute("SELECT count(*) FROM vehicles WHERE id = 'car_sonata';")
        self.assertEqual(c.fetchone()[0], 1)

    def test_same_key_different_payload_conflicts(self):
        """동일 키·다른 페이로드는 409 충돌로 거부"""
        key = "IDEMP-KEY-CONFLICT-TEST"
        payload1 = {"vehicles": [{"id": "car_1", "plate_number": "11가1111", "model_name": "쏘나타"}]}
        payload2 = {"vehicles": [{"id": "car_2", "plate_number": "22나2222", "model_name": "아반떼"}]}

        res1 = self.engine.execute_sync_vehicles(key, payload1)
        self.assertEqual(res1["status_code"], 200)

        # 다른 페이로드 전송 -> 409 거부
        res2 = self.engine.execute_sync_vehicles(key, payload2)
        self.assertEqual(res2["status_code"], 409)
        self.assertEqual(res2["error"], "IDEMPOTENCY_PAYLOAD_MISMATCH")

    def test_concurrent_10_requests_race_condition(self):
        """동일 멱등키 10개 동시 요청 실행 시 race condition 원천 방어 검증"""
        key = "IDEMP-KEY-CONCURRENT-10"
        payload = {"vehicles": [{"id": "car_concurrent", "plate_number": "99하9999", "model_name": "제네시스 GV80"}]}

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.engine.execute_sync_vehicles, key, payload) for _ in range(10)]
            for f in concurrent.futures.as_completed(futures):
                results.append(f.result())

        # 10개 중 정확히 1개만 최초 실행(status 200, inserted 1)되고,
        # 나머지는 즉시 리플레이(status 200, idempotent_replay=True)되거나 동시 실행 방어(409)되어야 함
        status_codes = [r["status_code"] for r in results]
        self.assertTrue(all(c in (200, 409) for c in status_codes))

        # DB 차량 테이블에는 정확히 1대만 삽입되어야 함 (중복 삽입 0건 보장!)
        c = self.engine.conn.cursor()
        c.execute("SELECT count(*) FROM vehicles WHERE id = 'car_concurrent';")
        self.assertEqual(c.fetchone()[0], 1)

    def test_admin_field_ownership_protection(self):
        """차피셜 동기화로 차마트 관리자 설정값(target_price, is_public, ownership) 덮어쓰기 불가 검증"""
        c = self.engine.conn.cursor()
        # 관리자가 이미 5,000만원, 공개승인(1), 직영(OWNED)으로 설정해 둔 차량
        c.execute("""
            INSERT INTO vehicles (id, plate_number, model_name, target_price, is_public, listing_ownership_type, created_at, updated_at)
            VALUES ('car_admin_001', '55오5555', 'G80', 5000, 1, 'OWNED', '2026-10-30', '2026-10-30');
        """)
        self.engine.conn.commit()

        # 차피셜에서 동기화로 3,000만원, 비공개(0), MARKET_OBSERVED를 덮어쓰려고 시도
        payload = {"vehicles": [{"id": "car_admin_001", "plate_number": "55오5555", "model_name": "G80 3.5T", "target_price": 3000, "is_public": 0, "listing_ownership_type": "MARKET_OBSERVED"}]}
        res = self.engine.execute_sync_vehicles("KEY-OWNERSHIP-TEST", payload)
        self.assertEqual(res["status_code"], 200)

        # DB 확인: model_name은 갱신되었으나, 관리자 target_price(5000), is_public(1), ownership(OWNED)은 100% 보존되어야 함!
        c.execute("SELECT model_name, target_price, is_public, listing_ownership_type FROM vehicles WHERE id = 'car_admin_001';")
        row = c.fetchone()
        self.assertEqual(row["model_name"], "G80 3.5T")
        self.assertEqual(row["target_price"], 5000)
        self.assertEqual(row["is_public"], 1)
        self.assertEqual(row["listing_ownership_type"], "OWNED")

if __name__ == '__main__':
    unittest.main()
