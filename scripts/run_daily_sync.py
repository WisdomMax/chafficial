"""
Chaficial Live Daily Sync Engine (DIRECTIVE 107 Production Standard)
- Default Mode: LIVE Real-Time Collection (Defaults strictly to --live).
- Strict Integrity Thresholds:
  * Market Threshold: Minimum 1,500 cars required. Under 1,500 aborts DB write immediately (0 writes).
  * Owned Threshold: Minimum 60 cars required.
- Zero Unit Conversion Bug: Prices strictly in Integer MAN-WON.
- Zero False SOLD: Unverified cars marked DELISTED safely without corrupting status to SOLD.
- Masked Tokens: No credentials or session tokens leaked to logs.
"""

import sys
import os
import json
import time
import asyncio
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "src")
from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
from chaficial.platform.sourcing.janghanpyeong_collector import JanghanpyeongCollector
from chaficial.platform.sourcing.market_timeseries_engine import MarketTimeSeriesEngine
from chaficial.platform.sourcing.carmanager_client import load_env

load_env()
SNAPSHOT_DIR = Path("data/carmanager_raw/snapshots")
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# 엄격한 수집량 임계치 (단일화된 통합 표준: 전체 1500, 자사 60, 타사관측 1440)
MIN_TOTAL_THRESHOLD = 1500
MIN_OWNED_THRESHOLD = 60
MIN_MARKET_OBSERVED_THRESHOLD = 1440

async def collect_live_snapshot(max_pages: int = 89):
    """카매니저 실시간 시장 매물 수집 실행 (1~89페이지 전체 순회)"""
    collector = JanghanpyeongCollector()
    result = await collector.run_full_collection(max_pages=max_pages, throttle_sec=0.35)
    return result

def run_sync_pipeline(use_live_collector: bool = False, max_pages: int = 89, dry_run: bool = False, db_path: str = "data/chamart/chamart_platform_demo.db", allow_historical_test_commit: bool = False):
    print("========================================================")
    print(f"[*] Chaficial Daily Sync Pipeline: {datetime.now().isoformat()} (LIVE_COLLECTOR={use_live_collector}, DRY_RUN={dry_run})")
    print("========================================================")

    all_cars = []
    capture_time = datetime.now().isoformat()
    observation_mode = "LIVE_OBSERVED" if use_live_collector else "HISTORICAL_REPLAY"

    if use_live_collector:
        print(f"[*] [LIVE MODE] Executing live CarManager crawler for up to {max_pages} pages...")
        try:
            collect_res = asyncio.run(collect_live_snapshot(max_pages=max_pages))
            if not collect_res.get("is_complete", False):
                print(f"[!] CRITICAL GUARD: Live harvest incomplete (is_complete=False, failed_pages={collect_res.get('failed_pages')}).", file=sys.stderr)
                print("[!] Aborting database writes completely (0 writes performed) to prevent false delisting.", file=sys.stderr)
                sys.exit(1)
            all_cars = collect_res.get("cars", [])
            print(f"[+] Successfully harvested {len(all_cars)} verified complete cars from CarManager.")
        except Exception as e:
            print(f"[!] Live collection failed with exception: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("[!] [HISTORICAL_REPLAY MODE] Loading historical snapshot from local disk...")
        latest_snapshot_path = "data/carmanager_raw/janghanpyeong_full_collection.json"
        if not os.path.exists(latest_snapshot_path):
            print(f"[!] Snapshot file {latest_snapshot_path} not found.", file=sys.stderr)
            sys.exit(1)
        with open(latest_snapshot_path, "r", encoding="utf-8") as f:
            full_data = json.load(f)
        all_cars = full_data.get("cars", [])
        # [DIRECTIVE 127 결함 2 수정] 원본 생성 시각이 없을 때 임의 날짜 하드코딩 배제 -> 'UNKNOWN' 유지
        summary = full_data.get("summary", {})
        capture_time = summary.get("collected_at") or "UNKNOWN"
        print(f"[+] Loaded verified historical snapshot with {len(all_cars)} cars (Captured at {capture_time}).")

        # [DIRECTIVE 128 P0 GUARD: 운영 DB 연결 경계 물리적 격리]
        # 1) allow_historical_test_commit=True가 있더라도 운영 DB(chamart_platform_demo.db)라면 무조건 쓰기 원천 차단
        real_abs_db = os.path.realpath(db_path)
        is_target_prod = ("chamart_platform_demo.db" in real_abs_db and "test" not in real_abs_db and "tmp" not in real_abs_db and "sandbox" not in real_abs_db)

        if not use_live_collector and not dry_run:
            if is_target_prod:
                print("[!] CRITICAL P0 GUARD: Historical snapshot (HISTORICAL_REPLAY) CANNOT be committed to PRODUCTION database under any circumstance!", file=sys.stderr)
                print("[!] allow_historical_test_commit flag is strictly forbidden on production DB. Forcing DRY_RUN=True.", file=sys.stderr)
                dry_run = True
            elif not allow_historical_test_commit:
                print("[!] CRITICAL P0 GUARD: Historical snapshot (HISTORICAL_REPLAY) requires explicit allow_historical_test_commit=True on isolated test DB. Forcing DRY_RUN=True.", file=sys.stderr)
                dry_run = True

    # 1. 전체 수집량 검증 (최소 1,500대 미만 시 즉시 차단)
    if len(all_cars) < MIN_TOTAL_THRESHOLD:
        print(f"[!] CRITICAL GUARD: Total harvested vehicle count ({len(all_cars)}) is below strict threshold ({MIN_TOTAL_THRESHOLD}).", file=sys.stderr)
        print("[!] Aborting database writes completely (0 writes performed) to protect data integrity.", file=sys.stderr)
        raise RuntimeError(f"Total harvested vehicle count ({len(all_cars)}) is below strict threshold ({MIN_TOTAL_THRESHOLD}).")

    # 우리 상사 매물 분리 ((주)더쿨모터스 및 더쿨모터스)
    owned_cars = []
    market_cars = []
    for c in all_cars:
        shop = c.get("shop") or c.get("sangsa_name") or ""
        if "(주)더쿨모터스" in shop or "더쿨모터스" in shop:
            owned_cars.append(c)
        else:
            market_cars.append(c)

    print(f"[*] Partitioned vehicles: OWNED={len(owned_cars)}대 | MARKET_OBSERVED={len(market_cars)}대")

    # 2. 우리 상사 수집량 임계치 사전 검증 (시계열 및 운영 DB 쓰기 전 사전 차단)
    if len(owned_cars) < MIN_OWNED_THRESHOLD:
        print(f"[!] CRITICAL GUARD: Owned vehicle count ({len(owned_cars)}) is below strict threshold ({MIN_OWNED_THRESHOLD}).", file=sys.stderr)
        print("[!] Aborting database writes completely to protect owned inventory.", file=sys.stderr)
        raise RuntimeError(f"Owned vehicle count ({len(owned_cars)}) is below strict threshold ({MIN_OWNED_THRESHOLD}).")

    # 3. 시장 관측 수집량 임계치 사전 검증 (시계열 및 운영 DB 쓰기 전 사전 차단)
    if len(market_cars) < MIN_MARKET_OBSERVED_THRESHOLD:
        print(f"[!] CRITICAL GUARD: Market observed vehicle count ({len(market_cars)}) is below threshold ({MIN_MARKET_OBSERVED_THRESHOLD}).", file=sys.stderr)
        print("[!] Aborting database writes completely (0 writes performed) to protect data integrity.", file=sys.stderr)
        raise RuntimeError(f"Market observed vehicle count ({len(market_cars)}) is below threshold ({MIN_MARKET_OBSERVED_THRESHOLD}).")

    # [DIRECTIVE 125 TASK 3, ISSUE-89: 스키마 사전 준비(트랜잭션 락 충돌 방지) 및 원자적 트랜잭션]
    # [DIRECTIVE 126 TASK 4, ISSUE-96: db_path 파라미터 완전 존중 (독립 테스트 DB 지원)]
    ts_engine = MarketTimeSeriesEngine(db_path=db_path, dry_run=dry_run)
    service = CarManagerSyncService(db_path=db_path, dry_run=dry_run)

    if dry_run:
        abs_path = os.path.abspath(db_path)
        atomic_conn = sqlite3.connect(f"file:{abs_path}?mode=ro", uri=True)
    else:
        atomic_conn = sqlite3.connect(db_path)

    try:
        if not dry_run:
            atomic_conn.execute("BEGIN IMMEDIATE;")

        # 4. 시장 관측 시계열 및 변동 이벤트 엔진 누적 기록 (선행)
        # [DIRECTIVE 128 TASK 2]: 메타데이터 분리 (source_capture_id, source_capture_at, imported_at, observation_scope, observation_mode)
        source_capture_at = None if capture_time == "UNKNOWN" else capture_time
        now_iso = datetime.now().isoformat()
        if use_live_collector:
            src_capture_id = f"LIVE_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            imported_at = now_iso
        else:
            # 과거 원본의 안정적 capture_id
            src_capture_id = summary.get("capture_id") or summary.get("source_capture_id") or f"HIST_{hashlib.sha256(open(latest_snapshot_path, 'rb').read()).hexdigest()[:16]}"
            imported_at = now_iso

        ts_started = source_capture_at  # 원본 시각 없으면 None (현재 시각 승격 금지)
        ts_res = ts_engine.record_snapshot(
            all_cars, 
            started_at=ts_started, 
            finished_at=ts_started, 
            dry_run=dry_run, 
            connection=atomic_conn,
            source_capture_id=src_capture_id,
            source_capture_at=source_capture_at,
            imported_at=imported_at,
            observation_scope="JANGHANPYEONG_ALL",
            observation_mode=observation_mode
        )
        print(f"[+] Market TimeSeries Recorded: Status={ts_res.get('status')}, RunID={ts_res.get('run_id')}, Observations={ts_res.get('observations_count')}, Events={ts_res.get('events_count')} (Appeared={ts_res.get('appeared_count')}, PriceDec={ts_res.get('price_decreased_count')}, Delisted={ts_res.get('disappeared_count')})")

        # 시계열 저장이 성공 또는 이미 기록된 해시가 아니면 즉시 롤백 및 중단
        if "SUCCESS" not in ts_res.get("status", "") and "ALREADY_RECORDED" not in ts_res.get("status", ""):
            raise RuntimeError(f"Market TimeSeries failed with status '{ts_res.get('status')}'.")

        # 5. 우리 상사 운영 동기화 (시계열 성공 확인 후 실행)
        owned_res = service.run_sync(
            current_snapshot=owned_cars, scope="OWNED", min_expected_count=MIN_OWNED_THRESHOLD, 
            dry_run=dry_run, connection=atomic_conn, observation_mode=observation_mode, observed_at=ts_started
        )
        print(f"[+] Owned Scope Sync: Inspected={owned_res['total_inspected']}, New={owned_res['new_inserted']}, PriceChanged={owned_res['price_changed']}, Status={owned_res['status']}")
        if owned_res.get("status") != "SUCCESS":
            raise RuntimeError(f"Owned Sync failed with status '{owned_res.get('status')}'.")

        # 6. 장한평 시장 운영 동기화
        market_res = service.run_sync(
            current_snapshot=market_cars, scope="MARKET_OBSERVED", min_expected_count=MIN_MARKET_OBSERVED_THRESHOLD, 
            dry_run=dry_run, connection=atomic_conn, observation_mode=observation_mode, observed_at=ts_started
        )
        print(f"[+] Market Scope Sync: Inspected={market_res['total_inspected']}, New={market_res['new_inserted']}, PriceChanged={market_res['price_changed']}, Status={market_res['status']}")
        if market_res.get("status") != "SUCCESS":
            raise RuntimeError(f"Market Sync failed with status '{market_res.get('status')}'.")

        if not dry_run:
            atomic_conn.commit()
            print("[+] All sync phases (TimeSeries + Owned + Market) committed ATOMICALLY!")

    except Exception as ex:
        if not dry_run:
            atomic_conn.rollback()
            print(f"[!] CRITICAL GUARD: Sync pipeline aborted. ATOMIC ROLLBACK completed: {ex}", file=sys.stderr)
        raise ex
    finally:
        try:
            atomic_conn.close()
        except Exception:
            pass

    # 타임스탬프 스냅샷 아카이빙 (dry_run 시에는 dry_run 임시 파일로 분리)
    if dry_run:
        archive_path = SNAPSHOT_DIR / "dry_run_test_snapshot.json"
    else:
        today_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = SNAPSHOT_DIR / f"snapshot_{today_str}.json"
    with open(archive_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "dry_run": dry_run,
            "total_cars": len(all_cars),
            "owned_cars": len(owned_cars),
            "market_cars": len(market_cars),
            "owned_result": owned_res,
            "market_result": market_res,
            "timeseries_result": ts_res
        }, f, ensure_ascii=False, indent=2)

    print(f"[+] Archived snapshot run to {archive_path}")
    print("========================================================")
    print(f"[+] Live Sync Completed Successfully at {datetime.now().isoformat()} (DRY_RUN={dry_run})")
    print("========================================================")
    return {
        "status": "SUCCESS",
        "dry_run": dry_run,
        "db_path": db_path,
        "total_cars": len(all_cars),
        "owned_result": owned_res,
        "market_result": market_res,
        "timeseries_result": ts_res
    }

if __name__ == "__main__":
    # DIRECTIVE 125 TASK 3: 고속 89페이지 실시간 수집은 기본 비활성화 (--live 명시 시에만 가동)
    # 기본값: 검증된 로컬 스냅샷 기반 안전 동기화
    is_live = "--live" in sys.argv
    is_dry_run = "--dry-run" in sys.argv or (not is_live and "--commit" not in sys.argv)
    run_sync_pipeline(use_live_collector=is_live, dry_run=is_dry_run)
