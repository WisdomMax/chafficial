"""
CarManager Production Synchronization Engine (DIRECTIVE 105 P0)
- Unified Schema: Supports both collector fields ('encarno', 'price_manwon', 'model_year', 'plate_tail', 'shop')
  and legacy fields ('carSeq', 'price', 'year', 'plate').
- Zero Fake Values: vin defaults strictly to NULL (No 'VIN-{car_seq}' or 'CM-JHP-*' artificial strings).
- Accurate Ownership: Maps 'OWNED' vs 'MARKET_JANGHANPYEONG' precisely to DB listing_ownership_type.
- Independent Price Locking: Respects is_price_locked flag in condition_detail_json.
- Safe Delisting: Consecutive unverified threshold prevents accidental delisting on partial scrapes.
- Audit Logging: Detailed transaction logs saved to carmanager_sync_logs.
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
        c.execute("PRAGMA table_info(carmanager_sync_logs)")
        cols = [col[1] for col in c.fetchall()]
        if "scope" not in cols:
            c.execute("ALTER TABLE carmanager_sync_logs ADD COLUMN scope VARCHAR(30) NOT NULL DEFAULT 'OWNED'")
        if "unverified_count" not in cols:
            c.execute("ALTER TABLE carmanager_sync_logs ADD COLUMN unverified_count INTEGER NOT NULL DEFAULT 0")

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
          - 'OWNED': 우리 상사 보유 매물 전용 동기화 (listing_ownership_type = 'OWNED')
          - 'MARKET_OBSERVED': 장안평 매매단지 타 상사 관측 매물 전용 동기화 (listing_ownership_type = 'MARKET_JANGHANPYEONG')
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
            target_ownership = "OWNED" if scope == "OWNED" else "MARKET_JANGHANPYEONG"
            cursor.execute(f"""
                SELECT l.listing_id, l.vehicle_id, l.advertised_price, l.listing_status, 
                       v.target_price, v.status, v.is_public, v.condition_detail_json, v.publishing_status,
                       COALESCE(l.unverified_consecutive_count, 0)
                FROM vehicle_listings l
                JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.platform = 'CARMANAGER' AND v.listing_ownership_type = ?
            """, (target_ownership,))
            
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

            active_listing_ids = set()
            now = datetime.now().isoformat()
            branch_id = "61fea9a4-58f0-42bd-862c-14fd16d0d21c"

            # 2. 현재 스냅샷 검사 및 동기화
            for car in current_snapshot:
                # [TASK 4: encarno 및 carSeq 완벽 통합 매핑]
                listing_id = str(car.get("encarno") or car.get("carSeq") or "").strip()
                if not listing_id:
                    continue
                active_listing_ids.add(listing_id)

                # 번호판
                plate = str(car.get("full_plate") or car.get("plate") or car.get("plate_tail") or "").strip()
                
                # 가격 (만원 단위 표준화 -> 원 단위)
                raw_price = car.get("price_manwon") or car.get("price") or 0
                if isinstance(raw_price, str):
                    raw_price = re.sub(r"[^\d]", "", raw_price)
                    price_manwon = int(raw_price) if raw_price else 0
                else:
                    price_manwon = int(raw_price)

                # 1억원 미만 값이면 만원 단위로 입력된 것으로 간주하여 원 단위 변환 (예: 1550 -> 15,500,000)
                price_won = price_manwon * 10000 if price_manwon < 100000 else price_manwon

                # 제목 및 제원
                clean_title = car.get("clean_title") or car.get("title") or car.get("model") or "카매니저 등록 차량"
                maker = car.get("maker") or (clean_title.split()[0] if clean_title else "기타")
                model_name = car.get("model") or clean_title
                
                # 연식
                raw_year = car.get("model_year") or car.get("year") or 0
                year_val = int(re.sub(r"[^\d]", "", str(raw_year))) if str(raw_year).strip() else 0
                if year_val > 2100: year_val = int(str(year_val)[:4])

                # 주행거리
                raw_km = car.get("mileage") or car.get("km") or 0
                km_val = int(re.sub(r"[^\d]", "", str(raw_km))) if str(raw_km).strip() else 0

                fuel = car.get("fuel") or car.get("fuel_type") or ""
                mission = car.get("mission") or car.get("transmission") or ""
                color = car.get("color") or ""
                shop_name = car.get("shop") or car.get("sangsa_name") or ("(주)더쿨모터스" if scope == "OWNED" else "장안평 조합 회원사")
                dealer_name = car.get("dealer") or ""

                # [TASK 4: 가짜 VIN 완전 배제 -> 실데이터 없으면 NULL]
                vin = car.get("vin")
                if vin and ("CM-JHP" in vin or "DUMMY" in vin or "VIN-" in vin):
                    vin = None

                if listing_id not in existing_records:
                    # 신규 매물 등록
                    vehicle_id = str(uuid.uuid4())
                    ownership_type = "CHAMART_OWNED" if scope == "OWNED" else "EXTERNAL"
                    listing_ownership_type = "OWNED" if scope == "OWNED" else "MARKET_JANGHANPYEONG"

                    timeline = [{
                        "event": "INGESTED_VIA_CARMANAGER_SYNC",
                        "scope": scope,
                        "timestamp": now,
                        "price": price_won
                    }]

                    cursor.execute("""
                        INSERT INTO vehicles (
                            id, branch_id, plate_number, model_name, year, mileage, fuel_type,
                            transmission, color, purchase_price, target_price, status, is_demo,
                            ownership_type, listing_ownership_type, is_public, vin,
                            manufacturer, trim, options_json, timeline_json,
                            publishing_status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AVAILABLE', 0, ?, ?, 0, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)
                    """, (
                        vehicle_id, branch_id, plate, model_name, year_val, km_val, fuel,
                        mission, color, 0, price_won, ownership_type, listing_ownership_type,
                        vin, maker, "", "[]", json.dumps(timeline, ensure_ascii=False),
                        now, now
                    ))

                    cursor.execute("""
                        INSERT INTO vehicle_listings (
                            id, vehicle_id, platform, listing_id, listing_url, advertised_price,
                            listing_status, region, is_janghanpyeong, raw_seller_name, observation_notes,
                            first_observed_at, last_observed_at, is_demo
                        ) VALUES (?, ?, 'CARMANAGER', ?, ?, ?, 'DRAFT', '서울 장안평 자동차매매단지', 1, ?, ?, ?, ?, 0)
                    """, (
                        str(uuid.uuid4()), vehicle_id, listing_id, 
                        f"https://www.carmanager.co.kr/Car/Data#{listing_id}", price_won,
                        shop_name, f"수집연동 매물: {listing_id}", now, now
                    ))
                    stats["new_inserted"] += 1
                else:
                    prev = existing_records[listing_id]
                    v_id = prev["vehicle_id"]
                    prev_price = prev["target_price"]
                    is_price_locked = prev["is_price_locked"]

                    # 가격 변경 감지
                    if price_won > 0 and price_won != prev_price:
                        if is_price_locked:
                            # 가격 잠금 차량 보호
                            cursor.execute("SELECT timeline_json FROM vehicles WHERE id = ?", (v_id,))
                            tl_row = cursor.fetchone()
                            timeline = json.loads(tl_row[0]) if tl_row and tl_row[0] else []
                            timeline.append({
                                "event": "SYNC_PRICE_SKIPPED_ADMIN_PRICE_LOCK",
                                "detected_price": price_won,
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
                                "to": price_won,
                                "timestamp": now
                            })
                            cursor.execute("""
                                UPDATE vehicles SET target_price = ?, timeline_json = ?, updated_at = ?
                                WHERE id = ?
                            """, (price_won, json.dumps(timeline, ensure_ascii=False), now, v_id))
                            cursor.execute("""
                                UPDATE vehicle_listings SET advertised_price = ?, last_observed_at = ?
                                WHERE listing_id = ?
                            """, (price_won, now, listing_id))
                            stats["price_changed"] += 1
                    else:
                        # 변동 없음: last_observed_at 및 unverified 카운트 리셋
                        cursor.execute("""
                            UPDATE vehicle_listings 
                            SET last_observed_at = ?, unverified_consecutive_count = 0 
                            WHERE listing_id = ?
                        """, (now, listing_id))
                        stats["unchanged_count"] += 1

            # 3. 판매완료 및 광고중지 감지
            for listing_id, prev_data in existing_records.items():
                if listing_id not in active_listing_ids:
                    v_id = prev_data["vehicle_id"]
                    consec_count = prev_data["unverified_consecutive_count"] + 1

                    # 안전 임계치: 3회 연속 스냅샷 누락 시 DELISTED / SOLD 전환
                    if consec_count >= 3:
                        cursor.execute("""
                            UPDATE vehicle_listings 
                            SET listing_status = 'DELISTED', unverified_consecutive_count = ? 
                            WHERE listing_id = ?
                        """, (consec_count, listing_id))

                        if prev_data["vehicle_status"] == "AVAILABLE":
                            cursor.execute("""
                                UPDATE vehicles 
                                SET status = 'SOLD', is_public = 0, updated_at = ? 
                                WHERE id = ?
                            """, (now, v_id))
                        stats["sold_count"] += 1
                        stats["delisted_count"] += 1
                    else:
                        # 1~2회 누락: UNVERIFIED 보류
                        cursor.execute("""
                            UPDATE vehicle_listings 
                            SET unverified_consecutive_count = ? 
                            WHERE listing_id = ?
                        """, (consec_count, listing_id))
                        stats["unverified_count"] += 1

            conn.commit()

        except Exception as e:
            conn.rollback()
            stats["status"] = f"ERROR: {str(e)}"

        finished_at = datetime.now().isoformat()
        stats["finished_at"] = finished_at

        # 4. 감사 로그 저장
        cursor.execute("""
            INSERT INTO carmanager_sync_logs (
                id, scope, started_at, finished_at, total_inspected,
                new_inserted, price_changed, sold_count, unverified_count,
                delisted_count, unchanged_count, status, summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            stats["sync_id"], stats["scope"], stats["started_at"], stats["finished_at"],
            stats["total_inspected"], stats["new_inserted"], stats["price_changed"],
            stats["sold_count"], stats["unverified_count"], stats["delisted_count"],
            stats["unchanged_count"], stats["status"], json.dumps(stats, ensure_ascii=False)
        ))
        conn.commit()
        conn.close()

        return stats
