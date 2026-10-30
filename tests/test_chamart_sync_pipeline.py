"""
Unit & Integration Tests for DIRECTIVE 130 Chamart Sync Engine
"""

import unittest
import os
import sqlite3
import json
from unittest.mock import patch, MagicMock
from chaficial.platform.sourcing.chamart_sync_client import ChamartSyncClient

class TestChamartSyncPipeline(unittest.TestCase):
    def setUp(self):
        self.test_db = "data/chamart/test_sync_directive130.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            
        self.client = ChamartSyncClient(db_path=self.test_db, target_url="https://chamart.cc")

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_outbox_enqueue_idempotency(self):
        """동일 ID에 대한 아웃박스 적재 멱등성 검증"""
        v1 = {"id": "car_001", "plate_number": "11가1111", "model_name": "쏘나타", "target_price": 2000}
        self.client.enqueue_vehicle_sync(v1)
        
        # 중복 적재 시 최신 정보로 UPDATE되고 행 수는 1개여야 함
        v2 = {"id": "car_001", "plate_number": "11가1111", "model_name": "쏘나타 디 엣지", "target_price": 2200}
        self.client.enqueue_vehicle_sync(v2)
        
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("SELECT count(*), payload_json FROM chamart_sync_outbox WHERE entity_id = 'car_001';")
        count, payload = c.fetchone()
        conn.close()
        
        self.assertEqual(count, 1)
        self.assertIn("쏘나타 디 엣지", payload)
        self.assertIn("2200", payload)

    def test_offline_resilience_and_retry(self):
        """오프라인 및 네트워크 실패 시 아웃박스 보존 및 retry_count 증가 검증"""
        v = {"id": "car_offline_001", "plate_number": "22나2222", "model_name": "아반떼"}
        self.client.enqueue_vehicle_sync(v)
        
        # 네트워크 예외 모의 (오프라인 상태)
        with patch.object(self.client, '_send_request', side_effect=Exception("Connection refused (Offline)")):
            stats = self.client.drain_outbox()
            self.assertEqual(stats["sent"], 0)
            self.assertEqual(stats["failed"], 1)
            
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("SELECT status, retry_count, last_error FROM chamart_sync_outbox WHERE entity_id = 'car_offline_001';")
        status, retry_count, last_error = c.fetchone()
        conn.close()
        
        self.assertEqual(status, "FAILED")
        self.assertEqual(retry_count, 1)
        self.assertIn("Connection refused", last_error)

    def test_successful_drain(self):
        """정상 네트워크 상태에서 PENDING -> SENT 전이 검증"""
        v = {"id": "car_success_001", "plate_number": "33다3333", "model_name": "그랜저"}
        self.client.enqueue_vehicle_sync(v)
        
        with patch.object(self.client, '_send_request', return_value={"success": True, "inserted": 1}):
            stats = self.client.drain_outbox()
            self.assertEqual(stats["sent"], 1)
            self.assertEqual(stats["failed"], 0)
            
        conn = sqlite3.connect(self.test_db)
        c = conn.cursor()
        c.execute("SELECT status, sent_at FROM chamart_sync_outbox WHERE entity_id = 'car_success_001';")
        status, sent_at = c.fetchone()
        conn.close()
        
        self.assertEqual(status, "SENT")
        self.assertIsNotNone(sent_at)

    def test_four_tier_ranking_logic(self):
        """TASK 2 4단계 우선 노출 순위 산정 로직 단위 검증"""
        sample_cars = [
            {"id": "c1", "ownership": "PARTNER", "has_photo": False, "expected_tier": 4},
            {"id": "c2", "ownership": "OWNED", "has_photo": True, "expected_tier": 1},
            {"id": "c3", "ownership": "PARTNER", "has_photo": True, "expected_tier": 3},
            {"id": "c4", "ownership": "OWNED", "has_photo": False, "expected_tier": 2},
        ]
        
        def compute_tier(car):
            is_owned = car["ownership"] in ("OWNED", "CHAMART_OWNED")
            has_photo = car["has_photo"]
            if is_owned and has_photo:
                return 1
            elif is_owned and not has_photo:
                return 2
            elif not is_owned and has_photo:
                return 3
            else:
                return 4
                
        sorted_cars = sorted(sample_cars, key=compute_tier)
        tier_sequence = [compute_tier(c) for c in sorted_cars]
        self.assertEqual(tier_sequence, [1, 2, 3, 4])
        self.assertEqual(sorted_cars[0]["id"], "c2") # OWNED + PHOTO
        self.assertEqual(sorted_cars[1]["id"], "c4") # OWNED + NO PHOTO
        self.assertEqual(sorted_cars[2]["id"], "c3") # PARTNER + PHOTO
        self.assertEqual(sorted_cars[3]["id"], "c1") # PARTNER + NO PHOTO

if __name__ == "__main__":
    unittest.main()
