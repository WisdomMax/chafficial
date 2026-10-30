"""
Market Time-Series & Daily Observation Memory Engine (DIRECTIVE 110-R Standards)
- Daily Observation Memory: Preserves daily observations indefinitely (Never drops observations even if market is unchanged).
- Run-level Idempotency: Duplicate runs with identical run_id return ALREADY_RECORDED with 0 rows inserted.
- Strict Scope Isolation: Prior runs queried strictly within identical (source, search_condition) scope.
- Zero Fake Values: photo_count stored as exact integer if present, else NULL (no fake 0 defaults).
- Complete Auditability: Records exact raw_hash per vehicle, total_found, pages_collected, and unique_cars_count.
- Absolute Dry-Run Safety: In dry-run mode, zero DDL execution (no table creation) and read-only DB connection (mode=ro).
"""

import sqlite3
import json
import uuid
import hashlib
import re
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from chaficial.platform.sourcing.normalizer import (
    normalize_carmanager_record,
    parse_price_manwon,
    parse_mileage_km,
    parse_model_year
)


class MarketTimeSeriesEngine:
    def __init__(self, db_path: str = "data/chamart/chamart_platform_demo.db", dry_run: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        # [DIRECTIVE 110-R TASK 5] dry-run 시 무조건적인 DDL 스키마 생성 차단 (순수 읽기 전용 보장)
        if not dry_run:
            self._ensure_tables()

    def ensure_schema(self):
        """명시적 스키마 초기화 메서드"""
        self._ensure_tables()

    def _ensure_tables(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # A. Collection Runs (수집 실행 이력 메타데이터)
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

        # B. Listing Observations (일일 시계열 스냅샷 - 불변 관측 기록)
        c.execute("""
            CREATE TABLE IF NOT EXISTS market_listing_observations (
                id VARCHAR(36) PRIMARY KEY,
                run_id VARCHAR(36) NOT NULL,
                encarno VARCHAR(64) NOT NULL,
                observed_at DATETIME NOT NULL,
                raw_price_str VARCHAR(30),
                price_manwon INTEGER,
                mileage_km INTEGER,
                model_year INTEGER,
                model_name VARCHAR(100),
                fuel VARCHAR(30),
                mission VARCHAR(30),
                shop_name VARCHAR(50),
                region VARCHAR(50),
                listing_status VARCHAR(20) NOT NULL,
                photo_count INTEGER,
                raw_hash VARCHAR(64),
                FOREIGN KEY (run_id) REFERENCES market_collection_runs(run_id)
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_obs_encarno_date ON market_listing_observations(encarno, observed_at)")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_obs_run_encarno ON market_listing_observations(run_id, encarno)")

        # C. Listing Events (스냅샷 간 시계열 상태/가격 변동 이벤트)
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_runs_raw_sha256 ON market_collection_runs(raw_sha256)")

        # [DIRECTIVE 128 TASK 2]: 메타데이터 분리 컬럼 안전 마이그레이션
        for col, col_type in [
            ("source_capture_id", "VARCHAR(64)"),
            ("source_capture_at", "DATETIME"),
            ("imported_at", "DATETIME"),
            ("observation_scope", "VARCHAR(100)"),
            ("observation_mode", "VARCHAR(30)")
        ]:
            try:
                c.execute(f"ALTER TABLE market_collection_runs ADD COLUMN {col} {col_type};")
            except sqlite3.OperationalError:
                pass
        c.execute("CREATE INDEX IF NOT EXISTS idx_runs_capture_id ON market_collection_runs(source_capture_id)")

        conn.commit()
        conn.close()

    def record_snapshot(
        self,
        snapshot_cars: List[Dict[str, Any]],
        started_at: Optional[str] = None,
        finished_at: Optional[str] = None,
        source: str = "CARMANAGER",
        search_condition: str = "장안평/성동구(1104,1105,1230)",
        total_found: Optional[int] = None,
        pages_collected: int = 89,
        run_id: Optional[str] = None,
        dry_run: bool = False,
        connection: Optional[sqlite3.Connection] = None,
        source_capture_id: Optional[str] = None,
        source_capture_at: Optional[str] = None,
        imported_at: Optional[str] = None,
        observation_scope: Optional[str] = None,
        observation_mode: str = "LIVE_OBSERVED",
        is_partial: bool = False
    ) -> Dict[str, Any]:
        """
        새로운 스냅샷을 시계열 관측 테이블에 적재하고, 직전 동일 스코프 스냅샷과 비교하여 이벤트를 산출한다.
        DIRECTIVE 128: source_capture_id 기반 안정적 멱등성 및 일자별 연속 관측(Days on Market) 완벽 보존.
        """
        effective_dry_run = dry_run or self.dry_run
        run_id = run_id or str(uuid.uuid4())
        raw_json_str = json.dumps(snapshot_cars, ensure_ascii=False)
        raw_sha256 = hashlib.sha256(raw_json_str.encode("utf-8")).hexdigest()
        
        now_iso = datetime.now().isoformat()
        imported_at = imported_at or now_iso
        observation_scope = observation_scope or search_condition

        # [DIRECTIVE 128]: 원본 시각(source_capture_at)이 명시되지 않으면 현재 시각으로 임의 승격하지 않음
        obs_time = source_capture_at or started_at or finished_at or now_iso
        started_at = started_at or obs_time
        finished_at = finished_at or obs_time

        owns_conn = False
        if connection is not None:
            conn = connection
        elif effective_dry_run:
            abs_path = os.path.abspath(self.db_path)
            conn = sqlite3.connect(f"file:{abs_path}?mode=ro", uri=True)
            owns_conn = True
        else:
            conn = sqlite3.connect(self.db_path)
            owns_conn = True
        c = conn.cursor()

        # [TASK 1: run_id 기준 재실행 멱등성 검증 - 동일 run_id 중복 적재 원천 차단]
        c.execute("SELECT run_id FROM market_collection_runs WHERE run_id = ? AND status = 'SUCCESS'", (run_id,))
        existing_run = c.fetchone()
        if existing_run:
            if owns_conn:
                conn.close()
            return {
                "run_id": run_id,
                "status": "ALREADY_RECORDED",
                "observations_count": 0,
                "events_count": 0,
                "appeared_count": 0,
                "price_decreased_count": 0,
                "price_increased_count": 0,
                "disappeared_count": 0,
                "message": f"Execution run_id {run_id} already recorded. Duplicate run skipped."
            }

        # [DIRECTIVE 128 TASK 2: source_capture_id 기준 멱등성 검증]
        if source_capture_id:
            c.execute("""
                SELECT run_id FROM market_collection_runs 
                WHERE source_capture_id = ? AND status = 'SUCCESS' 
                LIMIT 1
            """, (source_capture_id,))
            existing_cap = c.fetchone()
            if existing_cap:
                if owns_conn:
                    conn.close()
                return {
                    "run_id": existing_cap[0],
                    "status": "ALREADY_RECORDED_CAPTURE_ID",
                    "observations_count": 0,
                    "events_count": 0,
                    "appeared_count": 0,
                    "price_decreased_count": 0,
                    "price_increased_count": 0,
                    "disappeared_count": 0,
                    "message": f"Source capture ID '{source_capture_id}' already recorded under run_id {existing_cap[0]}. Duplicate run skipped."
                }
        elif source_capture_at is None and observation_mode == "HISTORICAL_REPLAY":
            # [DIRECTIVE 128 P0 결함 2 시정]: 수집 시각이 없는(NULL) 과거 원본 재실행 시, 현재 시각 관측으로 승격하지 않고 기존 해시로 중복 차단!
            c.execute("""
                SELECT run_id FROM market_collection_runs 
                WHERE source = ? AND search_condition = ? AND raw_sha256 = ? AND source_capture_at IS NULL AND status = 'SUCCESS' 
                LIMIT 1
            """, (source, search_condition, raw_sha256))
            existing_null_cap = c.fetchone()
            if existing_null_cap:
                if owns_conn:
                    conn.close()
                return {
                    "run_id": existing_null_cap[0],
                    "status": "ALREADY_RECORDED_HISTORICAL_HASH",
                    "observations_count": 0,
                    "events_count": 0,
                    "appeared_count": 0,
                    "price_decreased_count": 0,
                    "price_increased_count": 0,
                    "disappeared_count": 0,
                    "message": f"Historical raw_sha256 {raw_sha256} with NULL capture time already recorded under run_id {existing_null_cap[0]}. Duplicate run skipped."
                }
        # [DIRECTIVE 127/128: 동일 관측 세션 재전송 중복 차단 (일자별 연속 관측 보존)]
        # 동일 source, search_condition, 관측시점(started_at), 원본 해시(raw_sha256)가 모두 일치하는 동일 실행 재전송만 차단!
        elif started_at:
            c.execute("""
                SELECT run_id FROM market_collection_runs 
                WHERE source = ? AND search_condition = ? AND raw_sha256 = ? AND started_at = ? AND status = 'SUCCESS' 
                LIMIT 1
            """, (source, search_condition, raw_sha256, started_at))
            existing_same_session = c.fetchone()
            if existing_same_session:
                if owns_conn:
                    conn.close()
                return {
                    "run_id": existing_same_session[0],
                    "status": "ALREADY_RECORDED_SESSION",
                    "observations_count": 0,
                    "events_count": 0,
                    "appeared_count": 0,
                    "price_decreased_count": 0,
                    "price_increased_count": 0,
                    "disappeared_count": 0,
                    "message": f"Session at {started_at} with raw_sha256 {raw_sha256} already successfully recorded under run_id {existing_same_session[0]}. Duplicate transmission blocked."
                }

        # [TASK 4: 동일 source, search_condition, observation_scope 범위 내 최신 run_id 조회]
        c.execute("""
            SELECT run_id, unique_cars_count FROM market_collection_runs 
            WHERE source = ? AND search_condition = ? AND (observation_scope = ? OR (observation_scope IS NULL AND ? IS NULL)) AND status = 'SUCCESS' AND run_id != ?
            ORDER BY finished_at DESC LIMIT 1
        """, (source, search_condition, observation_scope, observation_scope, run_id))
        last_run_row = c.fetchone()
        last_run_id = last_run_row[0] if last_run_row else None
        prev_unique_count = last_run_row[1] if last_run_row else 0

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

        observations_to_insert = []
        events_generated = []
        current_encarnos = set()

        for raw_car in snapshot_cars:
            norm = normalize_carmanager_record(raw_car)
            encarno = norm["encarno"]
            if not encarno or encarno in current_encarnos:
                continue
            current_encarnos.add(encarno)

            price_manwon = norm["price_manwon"]
            obs_id = str(uuid.uuid4())
            observations_to_insert.append((
                obs_id, run_id, encarno, obs_time, norm["raw_price_str"], price_manwon,
                norm["mileage_km"], norm["model_year"], norm["model_name"], norm["fuel"], norm["mission"],
                norm["shop_name"], norm["danji"], "ACTIVE", norm["photo_count"], norm["raw_hash"]
            ))

            # 시계열 이벤트 생성
            if encarno not in prev_obs:
                price_disp = f"{price_manwon}만원" if price_manwon is not None else "가격미정"
                events_generated.append((
                    str(uuid.uuid4()), run_id, encarno, "APPEARED",
                    None, str(price_manwon) if price_manwon is not None else None, obs_time, f"신규 매물 등장 ({price_disp})"
                ))
            else:
                p_prev = prev_obs[encarno]["price_manwon"]
                if price_manwon is not None and p_prev is not None and price_manwon != p_prev:
                    if price_manwon < p_prev:
                        events_generated.append((
                            str(uuid.uuid4()), run_id, encarno, "PRICE_DECREASED",
                            str(p_prev), str(price_manwon), obs_time, f"가격 인하 ({p_prev}만 -> {price_manwon}만, -{p_prev - price_manwon}만원)"
                        ))
                    else:
                        events_generated.append((
                            str(uuid.uuid4()), run_id, encarno, "PRICE_INCREASED",
                            str(p_prev), str(price_manwon), obs_time, f"가격 인상 ({p_prev}만 -> {price_manwon}만, +{price_manwon - p_prev}만원)"
                        ))

        # 목록에서 사라진 차량 감지 (DISAPPEARED)
        # [DIRECTIVE 128 TASK 2 P0 GUARD]: 부분 목록(is_partial)이거나, 전체 수집량이 직전의 유의미한 규모 미만인 경우 DELISTED/SOLD 산출 금지!
        allow_disappeared_events = (
            not is_partial and 
            (prev_unique_count == 0 or len(current_encarnos) >= prev_unique_count * 0.8)
        )
        if allow_disappeared_events:
            for encarno, p_data in prev_obs.items():
                if encarno not in current_encarnos:
                    events_generated.append((
                        str(uuid.uuid4()), run_id, encarno, "DELISTED_DISAPPEARED",
                        p_data["status"], "DISAPPEARED", obs_time, "목록에서 미관측 (광고중지/판매/이동 검토 대상)"
                    ))

        actual_total_found = total_found if total_found is not None else len(current_encarnos)

        if not effective_dry_run:
            # A. Collection Run 저장 (DIRECTIVE 128: 메타데이터 분리 저장)
            c.execute("""
                INSERT INTO market_collection_runs (
                    run_id, started_at, finished_at, source, search_condition,
                    total_found, pages_collected, unique_cars_count, raw_sha256, status,
                    source_capture_id, source_capture_at, imported_at, observation_scope, observation_mode
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'SUCCESS', ?, ?, ?, ?, ?)
            """, (
                run_id, started_at, finished_at, source, search_condition,
                actual_total_found, pages_collected, len(current_encarnos), raw_sha256,
                source_capture_id, source_capture_at, imported_at, observation_scope, observation_mode
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

            if owns_conn:
                conn.commit()

        if owns_conn:
            conn.close()

        summary = {
            "run_id": run_id,
            "status": "SUCCESS" if not effective_dry_run else "DRY_RUN_SUCCESS",
            "total_found": actual_total_found,
            "unique_cars_count": len(current_encarnos),
            "observations_count": len(observations_to_insert),
            "events_count": len(events_generated),
            "appeared_count": sum(1 for e in events_generated if e[3] == "APPEARED"),
            "price_decreased_count": sum(1 for e in events_generated if e[3] == "PRICE_DECREASED"),
            "price_increased_count": sum(1 for e in events_generated if e[3] == "PRICE_INCREASED"),
            "disappeared_count": sum(1 for e in events_generated if e[3] == "DELISTED_DISAPPEARED"),
            "raw_sha256": raw_sha256,
            "dry_run": effective_dry_run
        }
        return summary
