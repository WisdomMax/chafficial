"""
Market Time-Series Observation & Event Engine (CHA-FICIAL DIRECTIVE 109 P0)
- Stores immutable daily listing observations (Runs, Observations, Events).
- Preserves complete price change history, days on market (DOM), and delisting transitions.
- Fully decoupled from primary vehicles table: zero risk of operational data corruption.
- Strict Integer Manwon standard: raw and normalized prices tracked distinctly.
"""

import sqlite3
import json
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


class MarketTimeSeriesEngine:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db"):
        self.db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # A. Collection Runs
        c.execute("""
            CREATE TABLE IF NOT EXISTS market_collection_runs (
                run_id VARCHAR(36) PRIMARY KEY,
                started_at DATETIME NOT NULL,
                finished_at DATETIME NOT NULL,
                source VARCHAR(30) NOT NULL,
                search_condition VARCHAR(100) NOT NULL,
                total_found INTEGER NOT NULL,
                pages_collected INTEGER NOT NULL,
                unique_cars_count INTEGER NOT NULL,
                raw_sha256 VARCHAR(64) NOT NULL,
                status VARCHAR(20) NOT NULL
            )
        """)

        # B. Listing Observations (일일 시계열 스냅샷)
        c.execute("""
            CREATE TABLE IF NOT EXISTS market_listing_observations (
                id VARCHAR(36) PRIMARY KEY,
                run_id VARCHAR(36) NOT NULL,
                encarno VARCHAR(64) NOT NULL,
                observed_at DATETIME NOT NULL,
                raw_price_str VARCHAR(30),
                price_manwon INTEGER NOT NULL,
                mileage_km INTEGER,
                model_year INTEGER,
                model_name VARCHAR(100),
                fuel VARCHAR(30),
                mission VARCHAR(30),
                shop_name VARCHAR(50),
                region VARCHAR(50),
                listing_status VARCHAR(20) NOT NULL,
                photo_count INTEGER NOT NULL DEFAULT 0,
                raw_hash VARCHAR(64),
                FOREIGN KEY (run_id) REFERENCES market_collection_runs(run_id)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_obs_encarno_date ON market_listing_observations(encarno, observed_at)")

        # C. Listing Events (스냅샷 간 시계열 이벤트)
        c.execute("""
            CREATE TABLE IF NOT EXISTS market_listing_events (
                event_id VARCHAR(36) PRIMARY KEY,
                run_id VARCHAR(36) NOT NULL,
                encarno VARCHAR(64) NOT NULL,
                event_type VARCHAR(30) NOT NULL,
                from_value TEXT,
                to_value TEXT,
                event_at DATETIME NOT NULL,
                notes TEXT,
                FOREIGN KEY (run_id) REFERENCES market_collection_runs(run_id)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_encarno_type ON market_listing_events(encarno, event_type)")

        conn.commit()
        conn.close()

    def record_snapshot(
        self,
        snapshot_cars: List[Dict[str, Any]],
        started_at: str,
        finished_at: str,
        source: str = "CARMANAGER",
        search_condition: str = "장안평/성동구(1104,1105,1230)",
        pages_collected: int = 89,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        새로운 스냅샷을 시계열 관측 테이블에 적재하고, 이전 최근 스냅샷과 비교하여 이벤트를 산출한다.
        """
        run_id = str(uuid.uuid4())
        raw_json_str = json.dumps(snapshot_cars, ensure_ascii=False)
        raw_sha256 = hashlib.sha256(raw_json_str.encode("utf-8")).hexdigest()
        now = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # 직전 최신 run_id 조회
        c.execute("SELECT run_id FROM market_collection_runs WHERE status = 'SUCCESS' ORDER BY finished_at DESC LIMIT 1")
        last_run_row = c.fetchone()
        last_run_id = last_run_row[0] if last_run_row else None

        # 직전 관측 레코드 로드 (encarno -> price_manwon, status, model_name)
        prev_obs = {}
        if last_run_id:
            c.execute("""
                SELECT encarno, price_manwon, listing_status, model_name, mileage_km 
                FROM market_listing_observations 
                WHERE run_id = ?
            """, (last_run_id,))
            for r in c.fetchall():
                prev_obs[r[0]] = {
                    "price_manwon": r[1],
                    "status": r[2],
                    "model_name": r[3],
                    "mileage_km": r[4]
                }

        events_generated = []
        observations_to_insert = []
        current_encarnos = set()

        for car in snapshot_cars:
            encarno = str(car.get("encarno") or car.get("carSeq") or "").strip()
            if not encarno:
                continue
            current_encarnos.add(encarno)

            # 가격 정규화
            raw_p = car.get("price_manwon") or car.get("price") or 0
            if isinstance(raw_p, str):
                p_digits = "".join(filter(str.isdigit, raw_p))
                p_val = int(p_digits) if p_digits else 0
            else:
                p_val = int(raw_p)
            price_manwon = p_val // 10000 if p_val >= 100000 else p_val

            raw_km = car.get("mileage") or car.get("km")
            km_val = None
            if raw_km:
                s_km = str(raw_km).replace(",", "")
                import re
                m_man = re.search(r"(\d+(?:\.\d+)?)\s*만", s_km)
                if m_man:
                    km_val = int(float(m_man.group(1)) * 10000)
                else:
                    nums = "".join(filter(str.isdigit, s_km))
                    if nums: km_val = int(nums)

            model_name = car.get("clean_title") or car.get("model") or car.get("title") or "미확인차종"
            shop_name = car.get("shop") or car.get("sangsa_name") or ""
            fuel = car.get("fuel") or ""
            mission = car.get("mission") or ""
            model_year = int(str(car.get("model_year") or car.get("year") or 0)[:4]) if (car.get("model_year") or car.get("year")) else None

            obs_id = str(uuid.uuid4())
            observations_to_insert.append((
                obs_id, run_id, encarno, now, str(raw_p), price_manwon,
                km_val, model_year, model_name, fuel, mission,
                shop_name, "장안평", "ACTIVE", 0, ""
            ))

            # 이벤트 비교 (이전 스냅샷 대조)
            if encarno not in prev_obs:
                events_generated.append((
                    str(uuid.uuid4()), run_id, encarno, "APPEARED",
                    None, str(price_manwon), now, f"신규 매물 등장 ({price_manwon}만원)"
                ))
            else:
                p_prev = prev_obs[encarno]["price_manwon"]
                if price_manwon > 0 and p_prev > 0 and price_manwon != p_prev:
                    if price_manwon < p_prev:
                        events_generated.append((
                            str(uuid.uuid4()), run_id, encarno, "PRICE_DECREASED",
                            str(p_prev), str(price_manwon), now, f"가격 인하 ({p_prev}만 -> {price_manwon}만, -{p_prev - price_manwon}만원)"
                        ))
                    else:
                        events_generated.append((
                            str(uuid.uuid4()), run_id, encarno, "PRICE_INCREASED",
                            str(p_prev), str(price_manwon), now, f"가격 인상 ({p_prev}만 -> {price_manwon}만, +{price_manwon - p_prev}만원)"
                        ))

        # 목록에서 사라진 차량 감지 (DISAPPEARED)
        for encarno, p_data in prev_obs.items():
            if encarno not in current_encarnos:
                events_generated.append((
                    str(uuid.uuid4()), run_id, encarno, "DELISTED_DISAPPEARED",
                    p_data["status"], "DISAPPEARED", now, "목록에서 미관측 (광고중지/판매/이동 검토 대상)"
                ))

        if not dry_run:
            # A. Collection Run 저장
            c.execute("""
                INSERT INTO market_collection_runs (
                    run_id, started_at, finished_at, source, search_condition,
                    total_found, pages_collected, unique_cars_count, raw_sha256, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'SUCCESS')
            """, (
                run_id, started_at, finished_at, source, search_condition,
                len(current_encarnos), pages_collected, len(current_encarnos), raw_sha256
            ))

            # B. Observations 배치 저장
            c.executemany("""
                INSERT INTO market_listing_observations (
                    id, run_id, encarno, observed_at, raw_price_str, price_manwon,
                    mileage_km, model_year, model_name, fuel, mission,
                    shop_name, region, listing_status, photo_count, raw_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, observations_to_insert)

            # C. Events 배치 저장
            c.executemany("""
                INSERT INTO market_listing_events (
                    event_id, run_id, encarno, event_type, from_value, to_value, event_at, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, events_generated)

            conn.commit()
        else:
            conn.rollback()

        conn.close()

        summary = {
            "run_id": run_id,
            "observations_count": len(observations_to_insert),
            "events_count": len(events_generated),
            "appeared_count": sum(1 for e in events_generated if e[3] == "APPEARED"),
            "price_decreased_count": sum(1 for e in events_generated if e[3] == "PRICE_DECREASED"),
            "price_increased_count": sum(1 for e in events_generated if e[3] == "PRICE_INCREASED"),
            "disappeared_count": sum(1 for e in events_generated if e[3] == "DELISTED_DISAPPEARED"),
            "dry_run": dry_run
        }
        return summary
