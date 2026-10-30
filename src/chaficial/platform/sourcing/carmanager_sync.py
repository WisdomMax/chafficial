"""
CarManager Production Synchronization Engine (DIRECTIVE 096 P0)
- Explicit scope separation: 'OWNED' (내차 13대) vs 'MARKET_OBSERVED' (장안평 관측 매물).
- Zero Auto-Publishing: All newly ingested vehicles default to DRAFT / is_public=0 until manual admin approval.
- Independent Price Locking: Separated from is_priority_exposure (uses explicit is_price_locked field).
- Safe Delisting: Does not immediately delist on single snapshot omission; marks UNVERIFIED first.
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
                scope VARCHAR(30) NOT NULL DEFAULT 'OWNED',
                started_at DATETIME NOT NULL,
                finished_at DATETIME NOT NULL,
                total_inspected INTEGER NOT NULL,
                new_inserted INTEGER NOT NULL,
                price_changed INTEGER NOT NULL,
                sold_count INTEGER NOT NULL,
                unverified_count INTEGER NOT NULL,
                delisted_count INTEGER NOT NULL,
                unchanged_count INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL,
                summary_json TEXT NOT NULL
            )
        """)
        # 기존 테이블에 scope 및 unverified_count 컬럼 추가 보장
        c.execute("PRAGMA table_info(carmanager_sync_logs)")
        cols = [col[1] for col in c.fetchall()]
        if "scope" not in cols:
            c.execute("ALTER TABLE carmanager_sync_logs ADD COLUMN scope VARCHAR(30) NOT NULL DEFAULT 'OWNED'")
        if "unverified_count" not in cols:
            c.execute("ALTER TABLE carmanager_sync_logs ADD COLUMN unverified_count INTEGER NOT NULL DEFAULT 0")

        # vehicle_listings 테이블에 unverified_consecutive_count 컬럼 추가 보장
        c.execute("PRAGMA table_info(vehicle_listings)")
        vl_cols = [col[1] for col in c.fetchall()]
        if "unverified_consecutive_count" not in vl_cols:
            c.execute("ALTER TABLE vehicle_listings ADD COLUMN unverified_consecutive_count INTEGER NOT NULL DEFAULT 0")

        conn.commit()
        conn.close()

    def run_sync(
        self, 
        current_snapshot: List[Dict[str, Any]], 
        sold_snapshot: Optional[List[Dict[str, Any]]] = None,
        scope: str = "OWNED"
    ) -> Dict[str, Any]:
        """
        scope:
          - 'OWNED': 우리 상사 보유 매물(내차관리 13대) 전용 동기화
          - 'MARKET_OBSERVED': 장안평 매매단지 타 상사 관측 매물 전용 동기화
        """
        started_at = datetime.now().isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {
            "sync_id": str(uuid.uuid4()),
            "scope": scope,
            "started_at": started_at,
            "total_inspected": len(current_snapshot),
            "new_inserted": 0,
            "price_changed": 0,
            "sold_count": 0,
            "unverified_count": 0,
            "delisted_count": 0,
            "unchanged_count": 0,
            "status": "SUCCESS"
        }

        try:
            # 1. 대상 scope에 해당하는 기존 리스팅만 로드 (타 범위 매물 보호)
            ownership_filter = "AND v.listing_ownership_type = 'OWNED'" if scope == "OWNED" else "AND v.listing_ownership_type = 'EXTERNAL'"
            cursor.execute(f"""
                SELECT l.listing_id, l.vehicle_id, l.advertised_price, l.listing_status, 
                       v.target_price, v.status, v.is_public, v.condition_detail_json, v.publishing_status,
                       COALESCE(l.unverified_consecutive_count, 0)
                FROM vehicle_listings l
                JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.platform = 'CARMANAGER' {ownership_filter}
            """)
            
            existing_records = {}
            for r in cursor.fetchall():
                cond_json = {}
                try:
                    if r[7]: cond_json = json.loads(r[7])
                except Exception:
                    pass
                existing_records[r[0]] = {
                    "vehicle_id": r[1],
                    "listing_price": r[2],
                    "listing_status": r[3],
                    "target_price": r[4],
                    "vehicle_status": r[5],
                    "is_public": r[6],
                    "is_price_locked": bool(cond_json.get("is_price_locked")),
                    "publishing_status": r[8],
                    "unverified_consecutive_count": r[9]
                }

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
                    # [TASK 2: 신규 차량은 가격 유무와 관계없이 무조건 DRAFT / is_public=0]
                    vehicle_id = str(uuid.uuid4())
                    timeline = [{
                        "event": "CARMANAGER_SYNC_NEW",
                        "timestamp": now,
                        "note": f"카매니저 실계정 신규 수집 (Seq: {car_seq}) - 관리자 승인 대기"
                    }]

                    ownership_type = "CHAMART_OWNED" if scope == "OWNED" else "MARKET_OBSERVED"
                    listing_ownership = "OWNED" if scope == "OWNED" else "EXTERNAL"

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
                        "DRAFT", 0, 0, listing_ownership, ownership_type,
                        f"VIN-{car_seq}", None, None, "[]", json.dumps(timeline, ensure_ascii=False),
                        "DRAFT", now, now
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
                        "DRAFT", "서울 장안평 자동차매매단지", True,
                        "차마트 직영" if scope == "OWNED" else "장안평 조합 회원사",
                        f"제시번호: {car.get('suggestNo', '-')}", now, now, 0
                    ))
                    stats["new_inserted"] += 1
                else:
                    prev = existing_records[car_seq]
                    v_id = prev["vehicle_id"]
                    prev_price = prev["target_price"]

                    # [TASK 5: 명시적 가격 잠금 검사 (우선순위 노출 플래그와 완전 분리)]
                    is_price_locked = prev["is_price_locked"]

                    if price_val > 0 and price_val != prev_price:
                        if is_price_locked:
                            # 가격 잠금 차량: 동기화 가격 덮어쓰기 차단 및 로그 기록
                            cursor.execute("SELECT timeline_json FROM vehicles WHERE id = ?", (v_id,))
                            tl_row = cursor.fetchone()
                            timeline = json.loads(tl_row[0]) if tl_row and tl_row[0] else []
                            timeline.append({
                                "event": "SYNC_PRICE_SKIPPED_ADMIN_PRICE_LOCK",
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

                    # 스냅샷 관측 성공 시: 미조회 카운트 리셋 및 ACTIVE 복구
                    cursor.execute("""
                        UPDATE vehicle_listings SET 
                            last_observed_at = ?,
                            unverified_consecutive_count = 0,
                            listing_status = CASE WHEN listing_status = 'UNVERIFIED' THEN 'ACTIVE' ELSE listing_status END
                        WHERE listing_id = ?
                    """, (now, car_seq))

            # 3. [DIRECTIVE 096 TASK 4: 3회 연속 미조회 카운팅 및 3회째 DELISTED/비공개 자동 전환]
            missing_seqs = set(existing_records.keys()) - active_car_seqs
            for m_seq in missing_seqs:
                rec = existing_records[m_seq]
                v_id = rec["vehicle_id"]
                current_unverified = rec["unverified_consecutive_count"] + 1

                if current_unverified < 3:
                    # 1~2회 미조회: 경고(UNVERIFIED) 마킹 및 카운트 누적 (즉시 비공개 강등 금지)
                    cursor.execute("""
                        UPDATE vehicle_listings SET 
                            unverified_consecutive_count = ?,
                            listing_status = 'UNVERIFIED',
                            observation_notes = observation_notes || ?
                        WHERE listing_id = ?
                    """, (current_unverified, f' [{current_unverified}회 스냅샷 미조회]', m_seq))
                    stats["unverified_count"] += 1
                else:
                    # 3회 연속 미조회: 정식 DELISTED 확정 및 is_public=0 비공개 안전 전환
                    cursor.execute("""
                        UPDATE vehicles SET 
                            status = 'DELISTED', 
                            is_public = 0, 
                            updated_at = ?
                        WHERE id = ?
                    """, (now, v_id))
                    cursor.execute("""
                        UPDATE vehicle_listings SET 
                            unverified_consecutive_count = ?,
                            listing_status = 'DELISTED', 
                            last_observed_at = ?,
                            observation_notes = observation_notes || ' [3회 연속 미조회로 비공개 전환]'
                        WHERE listing_id = ?
                    """, (current_unverified, now, m_seq))
                    stats["delisted_count"] += 1

            # 4. 판매완료 확정 매물 처리 (sold_snapshot 명시 시)
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
                    id, scope, started_at, finished_at, total_inspected, new_inserted,
                    price_changed, sold_count, unverified_count, delisted_count, unchanged_count,
                    status, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stats["sync_id"], stats["scope"], stats["started_at"], finished_at,
                stats["total_inspected"], stats["new_inserted"],
                stats["price_changed"], stats["sold_count"],
                stats["unverified_count"], stats["delisted_count"], stats["unchanged_count"],
                stats["status"], json.dumps(stats, ensure_ascii=False)
            ))
            conn.commit()
            conn.close()

        return stats
