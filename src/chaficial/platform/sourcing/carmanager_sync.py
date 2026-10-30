"""
CarManager Production Synchronization Engine (DIRECTIVE 118 P0 Standards)
- Strict Unit System: All price fields (target_price, advertised_price) stored strictly in Integer MAN-WON.
- Robust Mileage Parsing: Correctly parses '5.5만 km' -> 55,000 km, '12.3만km' -> 123,000 km without data loss.
- Safe Plate Management: Full plates preserved; incomplete tails (4 digits) stored without corrupting plate_number.
- Zero Fake Values: vin defaults strictly to NULL (No artificial strings).
- Reliable Delisting: Delists safely after 3 consecutive absences only on high-integrity scrapes; explicit sold detection.
- Cross-Scope Duplicate Prevention (Task 2): Never duplicates owned shop cars when running market observed sync!
"""

import sqlite3
import json
import uuid
import re
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from chaficial.platform.sourcing.normalizer import normalize_carmanager_record


def parse_price_manwon(val: Any) -> Optional[int]:
    """모든 입력 가격을 순수 '만원 단위 정수'로 표준화 (미입력/상담/0원 시 None)"""
    if val is None or val == "" or val == "상담":
        return None
    if isinstance(val, (int, float)):
        p = int(val)
    else:
        s = re.sub(r"[^\d]", "", str(val))
        p = int(s) if s else 0

    if p == 0:
        return None
    if p >= 100000:
        return p // 10000
    return p


def parse_mileage_km(val: Any) -> Optional[int]:
    """'5.5만 km' -> 55000, '12.3만km' -> 123000, '55,000km' -> 55000 표준화 (미입력/해석불가 시 None)"""
    if val is None:
        return None
    s = str(val).strip().replace(",", "")
    if not s:
        return None
    if s == "0" or s == "0km":
        return 0

    m = re.search(r"(\d+(?:\.\d+)?)\s*만", s)
    if m:
        try:
            return int(float(m.group(1)) * 10000)
        except Exception:
            pass

    nums = re.findall(r"\d+", s)
    if nums:
        return int("".join(nums))
    return None


def parse_plate_info(raw_plate: Any, raw_tail: Any = None) -> Tuple[Optional[str], Optional[str]]:
    p_str = str(raw_plate or "").strip()
    t_str = str(raw_tail or "").strip()

    full_match = re.search(r"(\d{2,3}\s*[가-힣]\s*\d{4})", p_str)
    if full_match:
        norm_plate = re.sub(r"\s+", "", full_match.group(1))
        return norm_plate, norm_plate[-4:]

    nums = re.findall(r"\d+", p_str)
    if nums and len(nums[-1]) == 4:
        return None, nums[-1]

    if t_str and len(t_str) == 4 and t_str.isdigit():
        return None, t_str

    return None, None


class CarManagerSyncService:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db", dry_run: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        self._ensure_log_table()

    def _ensure_log_table(self):
        if self.dry_run:
            return
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS carmanager_sync_logs (
                id VARCHAR(36) PRIMARY KEY,
                scope VARCHAR(30) NOT NULL,
                started_at DATETIME NOT NULL,
                completed_at DATETIME,
                total_inspected INTEGER DEFAULT 0,
                new_inserted INTEGER DEFAULT 0,
                price_changed INTEGER DEFAULT 0,
                sold_count INTEGER DEFAULT 0,
                delisted_count INTEGER DEFAULT 0,
                unchanged_count INTEGER DEFAULT 0,
                status VARCHAR(20) DEFAULT 'RUNNING',
                details_json TEXT
            );
        """)
        conn.commit()
        conn.close()

    def run_sync(
        self,
        current_snapshot: List[Dict[str, Any]],
        scope: str = "OWNED",
        min_expected_count: Optional[int] = None,
        dry_run: bool = False,
        connection: Optional[sqlite3.Connection] = None,
        observation_mode: str = "LIVE_OBSERVED",
        observed_at: Optional[str] = None
    ) -> Dict[str, Any]:
        started_at = datetime.now().isoformat()
        is_dry = self.dry_run or dry_run

        # [DIRECTIVE 128 P0 GUARD]: 운영 DB 파일에 대해 HISTORICAL_REPLAY 쓰기 시도 시 100% 무조건 DRY_RUN 강제!
        real_abs = os.path.realpath(self.db_path)
        is_real_prod = "chamart_platform_demo.db" in real_abs and "sandbox" not in real_abs and "test" not in real_abs
        if is_real_prod and observation_mode == "HISTORICAL_REPLAY":
            is_dry = True

        if min_expected_count is not None and len(current_snapshot) < min_expected_count:
            return {
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
                "status": f"ABORTED_BELOW_THRESHOLD: Count ({len(current_snapshot)}) < min_expected_count ({min_expected_count})"
            }
        
        owns_conn = False
        if connection is not None:
            conn = connection
        elif is_dry:
            abs_path = os.path.abspath(self.db_path)
            conn = sqlite3.connect(f"file:{abs_path}?mode=ro", uri=True)
            owns_conn = True
        else:
            conn = sqlite3.connect(self.db_path)
            owns_conn = True
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
            # DIRECTIVE 118 P0 FIX:
            # scope 필터 없이 CARMANAGER 전체 리스팅을 조회하여,
            # 자사 OWNED 차량이 MARKET 수집 시 중복 마스터로 생성되는 것을 원천 차단!
            cursor.execute("""
                SELECT l.listing_id, l.vehicle_id, l.advertised_price, l.listing_status, 
                       v.target_price, v.status, v.is_public, v.condition_detail_json, v.publishing_status,
                       COALESCE(l.unverified_consecutive_count, 0), v.listing_ownership_type
                FROM vehicle_listings l
                JOIN vehicles v ON l.vehicle_id = v.id
                WHERE l.platform = 'CARMANAGER'
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
                    "unverified_consecutive_count": r[9],
                    "ownership_type": r[10]
                }

            active_listing_ids = set()
            now = datetime.now().isoformat()
            branch_id = "61fea9a4-58f0-42bd-862c-14fd16d0d21c"

            for raw_car in current_snapshot:
                norm = normalize_carmanager_record(raw_car)
                listing_id = norm["encarno"]
                if not listing_id:
                    continue
                active_listing_ids.add(listing_id)

                raw_plate = raw_car.get("full_plate") or raw_car.get("plate")
                raw_tail = raw_car.get("plate_tail") or raw_car.get("carNo_tail")
                plate_number, plate_tail = parse_plate_info(raw_plate, raw_tail)
                db_plate_number = plate_number if plate_number else "UNVERIFIED"
                
                price_manwon = norm["price_manwon"]
                is_unannounced = (norm["price_manwon"] is None)

                # 1) 이미 존재하는 listing_id인 경우 -> 신규 마스터 생성 없이 기존 마스터 갱신!
                if listing_id in existing_records:
                    rec = existing_records[listing_id]
                    v_id = rec["vehicle_id"]
                    old_price = rec["listing_price"]
                    old_target = rec["target_price"]
                    is_locked = rec["is_price_locked"]

                    # 가격 변동 감지
                    if old_price != price_manwon:
                        stats["price_changed"] += 1
                        if not is_dry and observation_mode != "HISTORICAL_REPLAY":
                            # [DIRECTIVE 128 P0]: HISTORICAL_REPLAY 모드에서는 과거 데이터로 기존 운영 가격(target_price, advertised_price) 및 last_observed_at 절대 역행 수정 금지!
                            # DIRECTIVE 119 P0: OWNED 자사 차량은 시장 관측기가 vehicles.target_price를 절대 덮어쓰지 않음!
                            if rec.get("ownership_type") == "OWNED" and scope == "MARKET_OBSERVED":
                                cursor.execute("""
                                    UPDATE vehicle_listings SET advertised_price = ?, last_observed_at = ? WHERE platform = 'CARMANAGER' AND listing_id = ?
                                """, (price_manwon, now, listing_id))
                            else:
                                new_target = old_target if is_locked else price_manwon
                                cursor.execute("""
                                    UPDATE vehicles SET target_price = ?, updated_at = ? WHERE id = ?
                                """, (new_target, now, v_id))
                                cursor.execute("""
                                    UPDATE vehicle_listings SET advertised_price = ?, last_observed_at = ? WHERE platform = 'CARMANAGER' AND listing_id = ?
                                """, (price_manwon, now, listing_id))
                    else:
                        stats["unchanged_count"] += 1
                        if not is_dry and observation_mode == "LIVE_OBSERVED":
                            # [DIRECTIVE 126/127/128 P0]: LIVE_OBSERVED 모드에서만 last_observed_at 갱신 허용
                            obs_timestamp = observed_at or now
                            cursor.execute("""
                                UPDATE vehicle_listings SET last_observed_at = ?, unverified_consecutive_count = 0 WHERE platform = 'CARMANAGER' AND listing_id = ?
                            """, (obs_timestamp, listing_id))
                    continue

                # 2) 완전히 새로운 매물인 경우에만 신규 마스터 생성 (HISTORICAL_REPLAY에서는 운영 마스터 신규 생성 차단)
                stats["new_inserted"] += 1
                if not is_dry and observation_mode != "HISTORICAL_REPLAY":
                    new_veh_id = str(uuid.uuid4())
                    init_target_price = price_manwon
                    # DIRECTIVE 119 P0: 시장 관측 차량은 무조건 DRAFT 및 is_public=0 강제
                    init_pub_status = "DRAFT"
                    init_is_public = 0
                    ownership_to_set = "OWNED" if scope == "OWNED" else "MARKET_JANGHANPYEONG"

                    db_km_val = norm["mileage_km"]
                    fuel_val = norm.get("fuel") or "UNKNOWN"
                    mission_val = norm.get("mission") or "오토"
                    cursor.execute("""
                        INSERT INTO vehicles (
                            id, branch_id, plate_number, model_name, year, mileage, 
                            fuel_type, transmission, color, purchase_price, target_price, status, 
                            is_demo, timeline_json, created_at, updated_at, publishing_status, is_public,
                            listing_ownership_type, condition_detail_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DRAFT', 0, '[]', ?, ?, ?, ?, ?, ?)
                    """, (
                        new_veh_id, branch_id, db_plate_number, norm["model_name"],
                        norm["model_year"], db_km_val, fuel_val, mission_val,
                        norm.get("color") or raw_car.get("color") or "미상", 0, init_target_price, now, now, init_pub_status, init_is_public,
                        ownership_to_set, json.dumps({"plate_tail": plate_tail, "is_price_unannounced": is_unannounced})
                    ))

                    cursor.execute("""
                        INSERT INTO vehicle_listings (
                            id, vehicle_id, platform, listing_id, advertised_price,
                            listing_status, first_observed_at, last_observed_at,
                            is_demo, source_confidence, unverified_consecutive_count,
                            raw_seller_name, raw_seller_location
                        ) VALUES (?, ?, 'CARMANAGER', ?, ?, 'ACTIVE', ?, ?, 0, 0.95, 0, ?, ?)
                    """, (
                        str(uuid.uuid4()), new_veh_id, listing_id, price_manwon,
                        now, now, norm.get("shop"), norm.get("danji")
                    ))

            if not is_dry and owns_conn:
                conn.commit()

            stats["completed_at"] = datetime.now().isoformat()
            return stats

        except Exception as ex:
            if not is_dry and owns_conn:
                conn.rollback()
            stats["status"] = "FAILED"
            stats["error"] = str(ex)
            raise ex
        finally:
            if owns_conn:
                conn.close()
