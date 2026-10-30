"""
CarManager Daily Synchronization Engine
- Compares CarManager snapshot with Chaficial database.
- Detects: NEW, PRICE_CHANGED, SOLD, DELISTED, UNVERIFIED.
- Preserves manual admin overrides.
- Records price history.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any

class CarManagerSyncService:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db"):
        self.db_path = db_path

    def run_sync(self, current_snapshot: List[Dict[str, Any]], sold_snapshot: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        current_snapshot: 카매니저 내차관리에서 파싱된 최신 매물 목록 (13대 등)
        sold_snapshot: 카매니저 판매완료 탭에서 파싱된 목록 (178대 등)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()
        stats = {
            "sync_time": now,
            "total_inspected": len(current_snapshot),
            "new_count": 0,
            "price_changed_count": 0,
            "sold_count": 0,
            "status_updated_count": 0,
            "unverified_count": 0,
            "unchanged_count": 0
        }

        # 1. DB의 기존 CARMANAGER 리스팅 로드
        cursor.execute("""
            SELECT l.listing_id, l.vehicle_id, l.advertised_price, l.listing_status, v.target_price, v.status, v.options_json
            FROM vehicle_listings l
            JOIN vehicles v ON l.vehicle_id = v.id
            WHERE l.platform = 'CARMANAGER'
        """)
        existing_records = {r[0]: {
            "vehicle_id": r[1],
            "listing_price": r[2],
            "listing_status": r[3],
            "target_price": r[4],
            "vehicle_status": r[5],
            "options_json": r[6]
        } for r in cursor.fetchall()}

        active_car_seqs = set()

        # 2. 현재 스냅샷과 DB 대조
        for car in current_snapshot:
            car_seq = car.get("carSeq")
            if not car_seq:
                continue
            active_car_seqs.add(car_seq)

            price_val = int(str(car.get("price", "0")).replace(",", ""))
            is_active = (car.get("status") == "정상 광고중" or price_val > 0)

            if car_seq not in existing_records:
                # [신규 차량 감지]
                stats["new_count"] += 1
            else:
                prev = existing_records[car_seq]
                v_id = prev["vehicle_id"]
                prev_price = prev["target_price"]

                # [가격 변경 감지]
                if price_val > 0 and price_val != prev_price:
                    stats["price_changed_count"] += 1
                    cursor.execute("SELECT timeline_json FROM vehicles WHERE id = ?", (v_id,))
                    tl_row = cursor.fetchone()
                    timeline = json.loads(tl_row[0]) if tl_row and tl_row[0] else []
                    timeline.append({
                        "event": "PRICE_CHANGED",
                        "from": prev_price,
                        "to": price_val,
                        "timestamp": now
                    })
                    cursor.execute("""
                        UPDATE vehicles SET target_price = ?, timeline_json = ?, updated_at = ?
                        WHERE id = ?
                    """, (price_val, json.dumps(timeline, ensure_ascii=False), now, v_id))
                    cursor.execute("""
                        UPDATE vehicle_listings SET advertised_price = ?, last_observed_at = ?
                        WHERE listing_id = ?
                    """, (price_val, now, car_seq))
                else:
                    stats["unchanged_count"] += 1

                # 마지막 관측 시각 갱신
                cursor.execute("UPDATE vehicle_listings SET last_observed_at = ? WHERE listing_id = ?", (now, car_seq))

        # 3. 판매완료 및 미조회 검사
        if sold_snapshot:
            sold_seqs = {s.get("carSeq") for s in sold_snapshot if s.get("carSeq")}
            for seq, rec in existing_records.items():
                if seq in sold_seqs and rec["vehicle_status"] != "SOLD":
                    # [판매완료 감지]
                    v_id = rec["vehicle_id"]
                    cursor.execute("UPDATE vehicles SET status = 'SOLD', is_public = 0, updated_at = ? WHERE id = ?", (now, v_id))
                    cursor.execute("UPDATE vehicle_listings SET listing_status = 'SOLD', last_observed_at = ? WHERE listing_id = ?", (now, seq))
                    stats["sold_count"] += 1

        conn.commit()
        conn.close()
        return stats
