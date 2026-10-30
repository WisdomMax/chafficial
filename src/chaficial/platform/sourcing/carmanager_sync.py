"""
CarManager Production Synchronization Engine (DIRECTIVE 095 P0)
- Compares CarManager snapshot with Chaficial database.
- Detects:
    1. NEW: Actually inserts into vehicles and vehicle_listings with full fields.
    2. PRICE_CHANGED: Updates price and records audit timeline (respects admin overrides).
    3. SOLD: Marks status='SOLD', is_public=0 upon confirmation in sold tab.
    4. DELISTED / UNVERIFIED: Safely transitions missing listings to UNVERIFIED/DELISTED without data loss.
    5. ADMIN OVERRIDES: Protects manual admin fields (priority, manual prices).
- Records all run statistics into carmanager_sync_logs.
"""

import sqlite3
import json
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Optional

class CarManagerSyncService:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db"):
        self.db_path = db_path
        self._ensure_log_table()

    def _ensure_log_table(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS carmanager_sync_logs (
                id VARCHAR(36) PRIMARY KEY,
                started_at DATETIME NOT NULL,
                finished_at DATETIME NOT NULL,
                total_inspected INTEGER NOT NULL,
                new_inserted INTEGER NOT NULL,
                price_changed INTEGER NOT NULL,
                sold_count INTEGER NOT NULL,
                delisted_count INTEGER NOT NULL,
                unchanged_count INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL,
                summary_json TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def run_sync(self, current_snapshot: List[Dict[str, Any]], sold_snapshot: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        current_snapshot: 카매니저 실계정/전산 내차관리 매물 리스트
        sold_snapshot: 카매니저 판매완료 탭 매물 리스트
        """
        started_at = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {
            "sync_id": str(uuid.uuid4()),
            "started_at": started_at,
            "total_inspected": len(current_snapshot),
            "new_inserted": 0,
            "price_changed": 0,
            "sold_count": 0,
            "delisted_count": 0,
            "unchanged_count": 0,
            "status": "SUCCESS"
        }

        try:
            # 1. DB의 기존 CARMANAGER 활성 리스팅 로드
            cursor.execute("""
                SELECT l.listing_id, l.vehicle_id, l.advertised_price, l.listing_status, 
                       v.target_price, v.status, v.is_public, v.is_priority_exposure, v.publishing_status
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
                "is_public": r[6],
                "is_priority": r[7],
                "publishing_status": r[8]
            } for r in cursor.fetchall()}

            active_car_seqs = set()
            now = datetime.now().isoformat()
            branch_id = "61fea9a4-58f0-42bd-862c-14fd16d0d21c"

            # 2. 현재 스냅샷 검사 및 동기화
            for car in current_snapshot:
                car_seq = str(car.get("carSeq") or "").strip()
                if not car_seq:
                    continue
                active_car_seqs.add(car_seq)

                plate = str(car.get("plate") or "").strip()
                raw_price = str(car.get("price", "0")).replace(",", "").strip()
                price_val = int(raw_price) if raw_price.isdigit() else 0
                clean_title = car.get("clean_title") or car.get("title") or "카매니저 등록 차량"
                
                # 모델/제조사 분리
                parts = clean_title.split()
                manufacturer = parts[0] if parts else "기타"
                model_name = " ".join(parts[:2]) if len(parts) >= 2 else clean_title
                trim = " ".join(parts[2:]) if len(parts) > 2 else ""

                year_val = int(car.get("year")) if str(car.get("year", "")).isdigit() else 0
                mileage_raw = str(car.get("mileage", "0")).replace(",", "").strip()
                mileage_val = int(mileage_raw) if mileage_raw.isdigit() else 0
                fuel_val = car.get("fuel") or "미확인"
                trans_val = car.get("mission") or "오토"

                if car_seq not in existing_records:
                    # [신규 차량 감지 -> 실제 INSERT 수행]
                    vehicle_id = str(uuid.uuid4())
                    is_public = 1 if (price_val > 0 and car.get("status") == "정상 광고중") else 0
                    v_status = "FOR_SALE" if is_public else "DRAFT"
                    pub_status = "APPROVED" if is_public else "DRAFT"

                    timeline = [{
                        "event": "CARMANAGER_SYNC_NEW",
                        "timestamp": now,
                        "note": f"카매니저 실계정 최초 동기화 (Seq: {car_seq})"
                    }]

                    cursor.execute("""
                        INSERT INTO vehicles (
                            id, branch_id, plate_number, model_name, manufacturer, trim, year,
                            mileage, fuel_type, transmission, color, purchase_price, target_price,
                            status, is_demo, is_public, listing_ownership_type, ownership_type,
                            vin, first_registration_date, primary_photo_url, options_json, timeline_json,
                            publishing_status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        vehicle_id, branch_id, plate, model_name, manufacturer, trim, year_val,
                        mileage_val, fuel_val, trans_val, "미확인", 0, price_val,
                        v_status, 0, is_public, "OWNED", "CHAMART_OWNED",
                        f"VIN-{car_seq}", None, None, "[]", json.dumps(timeline, ensure_ascii=False),
                        pub_status, now, now
                    ))

                    cursor.execute("""
                        INSERT INTO vehicle_listings (
                            id, vehicle_id, platform, listing_id, listing_url, advertised_price,
                            listing_status, region, is_janghanpyeong, raw_seller_name, observation_notes,
                            first_observed_at, last_observed_at, is_demo
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()), vehicle_id, "CARMANAGER", car_seq, 
                        f"https://www.carmanager.co.kr/Car/Data#{car_seq}", price_val,
                        "ACTIVE" if is_public else "DRAFT", "서울 장안평 자동차매매단지", True,
                        "차마트 직영", f"제시번호: {car.get('suggestNo', '-')}", now, now, 0
                    ))
                    stats["new_inserted"] += 1
                else:
                    prev = existing_records[car_seq]
                    v_id = prev["vehicle_id"]
                    prev_price = prev["target_price"]

                    # 관리자 수동 고정 우선순위 검사 (Override 보호)
                    is_admin_locked = (prev["is_priority"] == 1)

                    # [가격 변경 감지]
                    if price_val > 0 and price_val != prev_price:
                        if is_admin_locked:
                            # 관리자 보호 차량: 가격 변경 보류 및 로그만 기록
                            cursor.execute("SELECT timeline_json FROM vehicles WHERE id = ?", (v_id,))
                            tl_row = cursor.fetchone()
                            timeline = json.loads(tl_row[0]) if tl_row and tl_row[0] else []
                            timeline.append({
                                "event": "SYNC_PRICE_SKIPPED_ADMIN_LOCK",
                                "detected_price": price_val,
                                "kept_price": prev_price,
                                "timestamp": now
                            })
                            cursor.execute("UPDATE vehicles SET timeline_json = ?, updated_at = ? WHERE id = ?", (json.dumps(timeline, ensure_ascii=False), now, v_id))
                        else:
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
                            stats["price_changed"] += 1
                    else:
                        stats["unchanged_count"] += 1

                    cursor.execute("UPDATE vehicle_listings SET last_observed_at = ? WHERE listing_id = ?", (now, car_seq))

            # 3. 미조회 / 광고중지 차량 안전 처리 (스냅샷에서 사라진 활성 매물)
            missing_seqs = set(existing_records.keys()) - active_car_seqs
            for m_seq in missing_seqs:
                rec = existing_records[m_seq]
                v_id = rec["vehicle_id"]
                if rec["vehicle_status"] in ("FOR_SALE", "AVAILABLE"):
                    # 즉시 삭제가 아닌 안전한 DELISTED 및 비공개 처리
                    cursor.execute("""
                        UPDATE vehicles SET status = 'DELISTED', is_public = 0, updated_at = ?
                        WHERE id = ?
                    """, (now, v_id))
                    cursor.execute("""
                        UPDATE vehicle_listings SET listing_status = 'DELISTED', last_observed_at = ?
                        WHERE listing_id = ?
                    """, (now, m_seq))
                    stats["delisted_count"] += 1

            # 4. 판매완료 확정 매물 처리
            if sold_snapshot:
                sold_seqs = {str(s.get("carSeq") or "").strip() for s in sold_snapshot if s.get("carSeq")}
                for s_seq in sold_seqs:
                    if s_seq in existing_records:
                        rec = existing_records[s_seq]
                        if rec["vehicle_status"] != "SOLD":
                            v_id = rec["vehicle_id"]
                            cursor.execute("""
                                UPDATE vehicles SET status = 'SOLD', is_public = 0, updated_at = ?
                                WHERE id = ?
                            """, (now, v_id))
                            cursor.execute("""
                                UPDATE vehicle_listings SET listing_status = 'SOLD', last_observed_at = ?
                                WHERE listing_id = ?
                            """, (now, s_seq))
                            stats["sold_count"] += 1

            conn.commit()

        except Exception as e:
            stats["status"] = f"ERROR: {str(e)}"
            conn.rollback()

        finally:
            finished_at = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO carmanager_sync_logs (
                    id, started_at, finished_at, total_inspected, new_inserted,
                    price_changed, sold_count, delisted_count, unchanged_count,
                    status, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stats["sync_id"], stats["started_at"], finished_at,
                stats["total_inspected"], stats["new_inserted"],
                stats["price_changed"], stats["sold_count"],
                stats["delisted_count"], stats["unchanged_count"],
                stats["status"], json.dumps(stats, ensure_ascii=False)
            ))
            conn.commit()
            conn.close()

        return stats
