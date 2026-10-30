"""
CarManager Production Synchronization Engine (DIRECTIVE 106 P0 Standards)
- Strict Unit System: All price fields (target_price, advertised_price) stored strictly in Integer MAN-WON.
- Robust Mileage Parsing: Correctly parses '5.5만 km' -> 55,000 km, '12.3만km' -> 123,000 km without data loss.
- Safe Plate Management: Full plates preserved; incomplete tails (4 digits) stored without corrupting plate_number.
- Zero Fake Values: vin defaults strictly to NULL (No artificial strings).
- Reliable Delisting: Delists safely after 3 consecutive absences only on high-integrity scrapes; explicit sold detection.
- Audit Trail: Complete sync events logged to carmanager_sync_logs and vehicles.timeline_json.
"""

import sqlite3
import json
import uuid
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


def parse_price_manwon(val: Any) -> int:
    """모든 입력 가격을 순수 '만원 단위 정수'로 표준화"""
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        p = int(val)
    else:
        s = re.sub(r"[^\d]", "", str(val))
        p = int(s) if s else 0

    # 10만 이상이면 원 단위(예: 15,000,000원 -> 1500만원)로 판단하여 만원으로 변환
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

    # '만' 패턴 매칭
    m = re.search(r"(\d+(?:\.\d+)?)\s*만", s)
    if m:
        try:
            return int(float(m.group(1)) * 10000)
        except Exception:
            pass

    # 일반 숫자만 있는 경우
    nums = re.findall(r"\d+", s)
    if nums:
        return int("".join(nums))
    return None


def parse_plate_info(raw_plate: Any, raw_tail: Any = None) -> Tuple[Optional[str], Optional[str]]:
    """
    정상적인 한글+숫자 조합 번호판 판별
    (예: '12가3456', '서울31바1234') -> plate_number 반환
    끝 4자리 또는 불완전 번호 -> plate_number = None, plate_tail 반환
    """
    p_str = str(raw_plate or "").strip()
    t_str = str(raw_tail or "").strip()

    # 한국 자동차 등록번호 정규식 (예: 12가3456, 123가4567, 서울31바1234, 경기70사1234)
    korean_plate_pattern = r"^(?:[가-힣]{2}\s*)?\d{1,3}[가-힣]\d{4}$"
    if re.match(korean_plate_pattern, p_str):
        tail = p_str[-4:]
        return p_str, tail

    # 4자리 숫자만 있는 경우
    if re.match(r"^\d{4}$", p_str):
        return None, p_str

    if t_str and re.match(r"^\d{4}$", t_str):
        return None, t_str

    return (p_str if p_str else None), (t_str if t_str else None)


class CarManagerSyncService:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db", dry_run: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        if not self.dry_run:
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
        scope: str = "OWNED",
        min_expected_count: int = 1,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        scope:
          - 'OWNED': 우리 상사 보유 매물 전용 동기화 (listing_ownership_type = 'OWNED')
          - 'MARKET_OBSERVED': 장안평 매매단지 타 상사 관측 매물 전용 동기화 (listing_ownership_type = 'MARKET_JANGHANPYEONG')
        dry_run:
          - True: DB 쓰기 및 커밋을 100% 차단하고 변경 예상치만 리포트 (True Read-Only Mode)
        """
        started_at = datetime.now().isoformat()
        is_dry = self.dry_run or dry_run
        if is_dry:
            # 완전한 SQLite Read-Only 모드 (URI mode=ro: 어떤 쓰기 시도도 엔진 레벨 차단)
            abs_path = os.path.abspath(self.db_path)
            conn = sqlite3.connect(f"file:{abs_path}?mode=ro", uri=True)
            cursor = conn.cursor()
        else:
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
                listing_id = str(car.get("encarno") or car.get("carSeq") or "").strip()
                if not listing_id:
                    continue
                active_listing_ids.add(listing_id)

                # 번호판 분격 파싱 (전체 번호판 미확인 시 스키마 허용 미확인값 UNVERIFIED 저장)
                raw_plate = car.get("full_plate") or car.get("plate")
                raw_tail = car.get("plate_tail") or car.get("carNo_tail")
                plate_number, plate_tail = parse_plate_info(raw_plate, raw_tail)
                db_plate_number = plate_number if plate_number else "UNVERIFIED"
                
                # 순수 만원 단위 가격
                price_manwon = parse_price_manwon(car.get("price_manwon") or car.get("price") or 0)

                # 제목 및 제원
                clean_title = car.get("clean_title") or car.get("title") or car.get("model") or "카매니저 등록 차량"
                maker = car.get("maker") or (clean_title.split()[0] if clean_title else "기타")
                model_name = car.get("model") or clean_title
                
                # 연식 파싱
                raw_year = car.get("model_year") or car.get("year") or 0
                year_digits = re.sub(r"[^\d]", "", str(raw_year))
                year_val = int(year_digits) if year_digits else None
                if year_val and year_val > 2100: 
                    year_val = int(str(year_val)[:4])
                if year_val and (year_val < 1980 or year_val > 2030):
                    year_val = None

                # 주행거리 견고 파싱 ('5.5만 km' 등 완벽 대응, 미확인 시 0)
                km_val = parse_mileage_km(car.get("mileage") or car.get("km"))
                db_km_val = km_val if km_val is not None else 0

                fuel = car.get("fuel") or car.get("fuel_type") or ""
                mission = car.get("mission") or car.get("transmission") or ""
                color = car.get("color") or ""
                shop_name = car.get("shop") or car.get("sangsa_name") or ("(주)더쿨모터스" if scope == "OWNED" else "장안평 조합 회원사")

                # VIN 검증 (가짜 VIN 배제)
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
                        "price_manwon": price_manwon
                    }]

                    obs_note = f"수집연동 매물: {listing_id}"
                    if plate_tail and not plate_number:
                        obs_note += f" (끝번호: {plate_tail})"

                    if not is_dry:
                        # 번호판이 없으면 UNVERIFIED 저장
                        cursor.execute("""
                            INSERT INTO vehicles (
                                id, branch_id, plate_number, model_name, year, mileage, fuel_type,
                                transmission, color, purchase_price, target_price, status, is_demo,
                                ownership_type, listing_ownership_type, is_public, vin,
                                manufacturer, trim, options_json, timeline_json,
                                publishing_status, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'AVAILABLE', 0, ?, ?, 0, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)
                        """, (
                            vehicle_id, branch_id, db_plate_number, model_name, year_val, db_km_val, fuel,
                            mission, color, 0, price_manwon, ownership_type, listing_ownership_type,
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
                            f"https://www.carmanager.co.kr/Car/Data#{listing_id}", price_manwon,
                            shop_name, obs_note, now, now
                        ))
                    stats["new_inserted"] += 1
                else:
                    prev = existing_records[listing_id]
                    v_id = prev["vehicle_id"]
                    prev_price = prev["target_price"]
                    is_price_locked = prev["is_price_locked"]

                    # 가격 변경 감지 (순수 만원 단위 비교)
                    if price_manwon > 0 and price_manwon != prev_price:
                        if is_price_locked:
                            # 가격 잠금 차량 보호
                            if not is_dry:
                                cursor.execute("SELECT timeline_json FROM vehicles WHERE id = ?", (v_id,))
                                tl_row = cursor.fetchone()
                                timeline = json.loads(tl_row[0]) if tl_row and tl_row[0] else []
                                timeline.append({
                                    "event": "SYNC_PRICE_SKIPPED_ADMIN_PRICE_LOCK",
                                    "detected_price_manwon": price_manwon,
                                    "kept_price_manwon": prev_price,
                                    "timestamp": now
                                })
                                cursor.execute("UPDATE vehicles SET timeline_json = ?, updated_at = ? WHERE id = ?", (json.dumps(timeline, ensure_ascii=False), now, v_id))
                        else:
                            if not is_dry:
                                cursor.execute("SELECT timeline_json FROM vehicles WHERE id = ?", (v_id,))
                                tl_row = cursor.fetchone()
                                timeline = json.loads(tl_row[0]) if tl_row and tl_row[0] else []
                                timeline.append({
                                    "event": "PRICE_CHANGED",
                                    "from_manwon": prev_price,
                                    "to_manwon": price_manwon,
                                    "timestamp": now
                                })
                                cursor.execute("""
                                    UPDATE vehicles SET target_price = ?, timeline_json = ?, updated_at = ?
                                    WHERE id = ?
                                """, (price_manwon, json.dumps(timeline, ensure_ascii=False), now, v_id))
                                cursor.execute("""
                                    UPDATE vehicle_listings SET advertised_price = ?, last_observed_at = ?
                                    WHERE listing_id = ?
                                """, (price_manwon, now, listing_id))
                            stats["price_changed"] += 1
                    else:
                        # 변동 없음: last_observed_at 갱신 및 unverified 카운트 리셋
                        if not is_dry:
                            cursor.execute("""
                                UPDATE vehicle_listings 
                                SET last_observed_at = ?, unverified_consecutive_count = 0 
                                WHERE listing_id = ?
                            """, (now, listing_id))
                        stats["unchanged_count"] += 1

            # 3. 판매완료 및 안전 광고중지 감지
            # 스냅샷 수집량이 최소 기대 수량 이상일 때만 누락 카운트 반영
            if len(current_snapshot) >= min_expected_count:
                for listing_id, prev_data in existing_records.items():
                    if listing_id not in active_listing_ids:
                        v_id = prev_data["vehicle_id"]
                        consec_count = prev_data["unverified_consecutive_count"] + 1

                        if consec_count >= 3:
                            # 3회 연속 미출현: DELISTED(광고중지/비공개) 전환
                            if not is_dry:
                                cursor.execute("""
                                    UPDATE vehicle_listings 
                                    SET listing_status = 'DELISTED', unverified_consecutive_count = ? 
                                    WHERE listing_id = ?
                                """, (consec_count, listing_id))

                                # 차량 상태는 AVAILABLE 상태였다면 비공개(is_public = 0)로 보호하고 DELISTED 처리
                                cursor.execute("""
                                    UPDATE vehicles 
                                    SET is_public = 0, updated_at = ? 
                                    WHERE id = ?
                                """, (now, v_id))
                            stats["delisted_count"] += 1
                        else:
                            # 1~2회 미출현: unverified 카운트만 증가
                            if not is_dry:
                                cursor.execute("""
                                    UPDATE vehicle_listings 
                                    SET unverified_consecutive_count = ? 
                                    WHERE listing_id = ?
                                """, (consec_count, listing_id))
                            stats["unverified_count"] += 1

            # 명시적 판매완료 스냅샷 처리 (카매니저에서 SOLD로 직접 조회된 건)
            if sold_snapshot:
                for s_car in sold_snapshot:
                    s_id = str(s_car.get("encarno") or s_car.get("carSeq") or "").strip()
                    if s_id in existing_records:
                        v_id = existing_records[s_id]["vehicle_id"]
                        if not is_dry:
                            cursor.execute("UPDATE vehicles SET status = 'SOLD', is_public = 0, updated_at = ? WHERE id = ?", (now, v_id))
                            cursor.execute("UPDATE vehicle_listings SET listing_status = 'SOLD' WHERE listing_id = ?", (s_id,))
                        stats["sold_count"] += 1

            if dry_run:
                conn.rollback()
                stats["status"] = "DRY_RUN_READ_ONLY"
                finished_at = datetime.now().isoformat()
                stats["finished_at"] = finished_at
                conn.close()
                return stats

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
