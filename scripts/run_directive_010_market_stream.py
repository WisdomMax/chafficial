"""CHA-FICIAL AI PROJECT - DIRECTIVE 010-H
운영 관측 무결성 및 격리 보완 파이프라인 (REPLAY 경로 강제 차단, 파일 락 동시성 제어, SQLite Backup 무결성 검증, 실패 보호).

본 모듈은 총괄 감독님의 DIRECTIVE 010-H 지침에 따라:
1. REPLAY 모드에서 운영 DB(data/chaficial_market_timeseries.db) 경로 지정 시 resolve() 검증으로 즉시 거부하여 운영 DB 오염 원천 차단.
2. 프로세스 간 실행 잠금(File Lock: fcntl.flock)을 도입하여 LIVE 관측의 동시 실행 및 경쟁 조건 방지.
3. 타임스탬프와 12자리 UUID(uuid.uuid4().hex[:12])를 결합하여 고유 배치 ID 및 배타적 원본 파일 생성.
4. 운영 DB 백업에 SQLite Backup API(source.backup(dst)) 및 PRAGMA integrity_check 무결성 검사를 적용하여 트랜잭션 일관성 보장.
5. 웹 수집 실패(CLI 오류, 타임아웃, 잘못된 JSON, 카드 0건, CN7 0건 등) 시 운영 DB 불변 보장.
6. 운영 DB의 기존 238대 실매물 및 246건 스냅샷 이력을 영구 보존합니다.
"""

import argparse
import csv
import fcntl
import hashlib
import json
import sqlite3
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from chaficial.database.base import Base
from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.models.vehicle_link import VehicleIdentityLink
from chaficial.pipeline.ingest_and_score import OpportunityPipeline
from chaficial.platforms.base import StandardListingRecord
from chaficial.platforms.encar import EncarCardParser
from chaficial.tracker.price_tracker import (
    PriceEventTracker,
    SearchScopeSpec,
    compute_db_logical_hashes,
)
from chaficial.tracker.stream_pipeline import (
    BatchExecutionResult,
    MarketObservationStreamPipeline,
)

KST = ZoneInfo("Asia/Seoul")
OFFICIAL_OPERATIONAL_DB_PATH = Path("data/chaficial_market_timeseries.db").resolve()


class LiveCollectionError(Exception):
    """실시간 웹 수집 실패 시 발생하는 예외."""


class OperationalLockError(Exception):
    """동시 실행 방지 잠금 획득 실패 시 발생하는 예외."""


class FileLockContext:
    """fcntl 기반 프로세스 간 배타적 파일 락 컨텍스트 매니저."""

    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.fp = None

    def __enter__(self):
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.fp = open(self.lock_file, "w")
        try:
            fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            self.fp.close()
            self.fp = None
            raise OperationalLockError(f"다른 관측 프로세스가 이미 실행 중입니다 (잠금 파일: {self.lock_file}).")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.fp:
            try:
                fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
            self.fp.close()
            self.fp = None


def get_file_sha256(filepath: Path) -> str:
    """파일의 SHA-256 해시를 계산합니다."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_collision_safe_batch_id(prefix: str = "ENCAR_CN7_LIVE") -> tuple[str, str]:
    """초 단위 타임스탬프와 고유 식별자(UUID 12자)를 결합하여 충돌 없는 고유 배치 ID 및 타임스탬프 문자열 생성."""
    now_kst = datetime.now(KST)
    unique_suffix = uuid.uuid4().hex[:12]
    ts_str = f"{now_kst.strftime('%Y%m%d_%H%M%S')}_{unique_suffix}"
    batch_id = f"{prefix}_{ts_str}"
    return batch_id, ts_str


def generate_batch_observation_report(
    batch_id: str,
    web_start_utc: datetime,
    web_end_utc: datetime,
    raw_file: Path,
    raw_sha: str,
    total_cards: int,
    parsed_count: int,
    batch_result: BatchExecutionResult,
    post_listings: int,
    post_snapshots: int,
    post_events: int,
    post_batches: int,
    post_links: int,
    live_db_hashes: dict[str, dict],
    all_batches: list[BatchAuditLog],
    pipeline: MarketObservationStreamPipeline,
) -> str:
    """DIRECTIVE 010-K 정합성에 부합하는 개별 관측 실행 동적 보고서 생성 (하드코딩 배제)."""
    start_kst = pipeline.to_kst_string(web_start_utc)
    end_kst = pipeline.to_kst_string(web_end_utc)
    completed_kst = pipeline.to_kst_string(batch_result.completed_at_utc)

    # 1. 누적 배치 감사 로그 테이블 동적 생성
    batch_rows = []
    for b in all_batches:
        b_time_kst = pipeline.to_kst_string(b.processed_at) if b.processed_at else "-"
        b_partial = "부분표본" if b.is_partial_scrape else "전체수집"
        batch_rows.append(
            f"| `{b.batch_id}` | {b_time_kst} | {b.record_count}건 | {b_partial} | {b.notes or '-'} |"
        )
    batch_table_md = "\n".join(batch_rows) if batch_rows else "| - | - | - | - | - |"

    return f"""# CHA-FICIAL AI PROJECT
## 시장 관측 실행 동적 보고서 (배치: {batch_id})

- **배치 식별자:** `{batch_id}`
- **수집 시작 (KST):** {start_kst}
- **수집 종료 (KST):** {end_kst}
- **DB 적재 완료 (KST):** {completed_kst}
- **원천 파일:** `{raw_file.name}`
- **원천 파일 SHA-256:** `{raw_sha}`

---

### 1. 해당 배치 관측 실적 (동적 산출)

| 지표 | 실측값 | 설명 |
| :--- | :--- | :--- |
| **수집 원천 카드 수** | **{total_cards}개** | 모바일 웹 스크롤 수집 카드 수 |
| **정밀 파싱 실매물 수** | **{parsed_count}대** | 아반떼 CN7 유효 규격 파싱 매물 |
| **최초 발견 (`FIRST_SEEN`)** | **{batch_result.first_seen_count}대** | 시스템 최초 관측 매물 (시장 등록일 아님) |
| **재관측 (`RE_OBSERVED`)** | **{batch_result.re_observed_count}대** | 기존 관측 이력 보유 매물 재확인 |
| **실제 가격 변동** | **{batch_result.price_drop_count + batch_result.price_increase_count}건** | 인하: {batch_result.price_drop_count}건, 인상: {batch_result.price_increase_count}건 |
| **미노출 의심 (`DELISTED_SUSPECT`)** | **{batch_result.delisted_suspect_count}건** | 결측 임계치 도달 의심 매물 |

---

### 2. 적재 직후 데이터베이스 현황 및 논리 해시

| 테이블 명 | 관리 레코드 수 | 논리 SHA-256 해시 |
| :--- | :---: | :---: |
| `listings` | **{post_listings}행** | `{live_db_hashes.get('listings', {}).get('hash', '-')}` |
| `listing_snapshots` | **{post_snapshots}행** | `{live_db_hashes.get('listing_snapshots', {}).get('hash', '-')}` |
| `price_events` | **{post_events}행** | `{live_db_hashes.get('price_events', {}).get('hash', '-')}` |
| `batch_audit_logs` | **{post_batches}행** | `{live_db_hashes.get('batch_audit_logs', {}).get('hash', '-')}` |
| `vehicle_identity_links` | **{post_links}행** | `{live_db_hashes.get('vehicle_identity_links', {}).get('hash', '-')}` |

---

### 3. 데이터베이스 누적 관측 배치 감사 이력 (DB 동적 조회)

| 배치 ID | 처리 시각 (KST) | 수집 건수 | 수집 구분 | 감사 비고 |
| :--- | :---: | :---: | :---: | :--- |
{batch_table_md}
"""


def backup_operational_db_safe(db_path: Path) -> Path | None:
    """SQLite Backup API를 사용하여 실행 중 일관성을 보장하며 배타적 파일 예약 및 PRAGMA integrity_check 무결성 검증."""
    if not db_path.exists():
        return None
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    _, ts_str = generate_collision_safe_batch_id()
    backup_file = backup_dir / f"market_timeseries_backup_{ts_str}.db"

    # DIRECTIVE 010-I: OS 수준의 배타적 파일 생성(O_CREAT | O_EXCL)으로 경쟁 조건 차단
    import os
    try:
        fd = os.open(backup_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
        os.close(fd)
    except FileExistsError:
        raise FileExistsError(f"백업 파일이 이미 존재하거나 예약 충돌이 발생했습니다: {backup_file}")

    # SQLite Backup API 사용: 일관된 스냅샷 덤프 보장
    with sqlite3.connect(db_path) as src_conn:
        with sqlite3.connect(backup_file) as dst_conn:
            src_conn.backup(dst_conn)

    # 백업 대상 DB 무결성 PRAGMA integrity_check 검증
    with sqlite3.connect(backup_file) as check_conn:
        cursor = check_conn.cursor()
        res = cursor.execute("PRAGMA integrity_check;").fetchall()
        if not res or res[0][0] != "ok":
            raise RuntimeError(f"백업 파일 SQLite 무결성 검사 실패: {res}")

    print(f"[+] [DIRECTIVE 010-I] SQLite Backup API 및 PRAGMA integrity_check 완료: {backup_file}")
    return backup_file


def fetch_live_encar_cn7(timeout_sec: int = 45, batch_id_override: str | None = None) -> tuple[list[dict], Path, str, str, datetime, datetime]:
    """실제 엔카 모바일 웹에서 아반떼 CN7 카드를 실시간 수집하고 검증 실패 시 즉시 에러 발생."""
    start_utc = datetime.now(UTC)
    if batch_id_override:
        batch_id = batch_id_override
        # 파일명 충돌 방지용 접미사 추출
        suffix = batch_id.replace("ENCAR_CN7_LIVE_", "")
        ts_str = suffix
    else:
        batch_id, ts_str = generate_collision_safe_batch_id("ENCAR_CN7_LIVE")

    print(f"[*] [LIVE 수집 개시] 엔카 모바일 웹 실시간 조회 (배치: {batch_id}, 시작: {start_utc.astimezone(KST).strftime('%Y-%m-%d %H:%M:%S KST')})...")

    search_obj = {
        "type": "car",
        "action": "(And.Hidden.N._.(C.CarType.Y._.(C.Manufacturer.현대._.ModelGroup.아반떼.)))",
        "title": "현대 아반떼",
        "sort": "MobileModifiedDate",
    }
    encoded_search = json.dumps(search_obj)

    js_code = f"""
async function run() {{
  const searchStr = {json.dumps(encoded_search)};
  const url = 'https://car.encar.com/list/car?page=1&search=' + encodeURIComponent(searchStr);
  
  await openTab(url);
  await sleep(4000);

  for (let s = 0; s < 6; s++) {{
    await page.evaluate(() => window.scrollBy(0, 1500));
    await sleep(1500);
  }}

  const rawCards = await page.evaluate(() => {{
    const anchors = Array.from(document.querySelectorAll('a[href*="/cars/detail/"], a[href*="carid="]'));
    const unique = new Map();

    anchors.forEach(a => {{
      const href = a.href || '';
      const m = href.match(/\\/cars\\/detail\\/(\\d+)/) || href.match(/carid=(\\d+)/);
      if (m && !unique.has(m[1])) {{
        const text = a.innerText.replace(/\\s+/g, ' ').trim();
        if (text.length > 20) {{
          unique.set(m[1], {{ carid: m[1], href, raw_text: text }});
        }}
      }}
    }});

    return Array.from(unique.values());
  }});

  console.log('LIVE_RAW_CARDS_JSON:' + JSON.stringify(rawCards));
}}
await run();
"""

    try:
        res = subprocess.run(
            ["/Users/wisdom/.local/bin/aside", "--profile", "c759b216-69cc-436b-941a-dab4e621632d", "repl", js_code],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as e:
        raise LiveCollectionError(f"엔카 실시간 웹 수집 명령 타임아웃 ({timeout_sec}초 초과): {e}")

    if res.returncode != 0:
        raise LiveCollectionError(f"Aside CLI 실행 실패 (exit code {res.returncode}): {res.stderr}")

    raw_cards: list[dict] = []
    for line in res.stdout.splitlines():
        if line.startswith("LIVE_RAW_CARDS_JSON:"):
            try:
                raw_cards = json.loads(line[len("LIVE_RAW_CARDS_JSON:") :])
                break
            except Exception as e:
                raise LiveCollectionError(f"수집된 원천 카드 JSON 파싱 실패: {e}")

    if not raw_cards:
        raise LiveCollectionError("실시간 수집된 엔카 매물 카드가 0건입니다 (웹 세션 이상 또는 응답 구조 변경).")

    end_utc = datetime.now(UTC)

    raw_dir = Path("data/raw_observations")
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_file = raw_dir / f"encar_cn7_live_{ts_str}.json"

    if raw_file.exists():
        raise FileExistsError(f"배타적 파일 생성 실패 (이미 파일 존재): {raw_file}")

    meta_payload = {
        "batch_id": batch_id,
        "source_platform": "ENCAR",
        "search_scope": "현대 아반떼 CN7",
        "search_parameters": search_obj,
        "collected_at_utc": start_utc.isoformat(),
        "collected_at_kst": start_utc.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST"),
        "completed_at_utc": end_utc.isoformat(),
        "completed_at_kst": end_utc.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST"),
        "total_cards_collected": len(raw_cards),
        "raw_cards": raw_cards,
    }

    # 배타적 파일 쓰기 모드 ('x' 모드)
    with open(raw_file, "x", encoding="utf-8") as f:
        json.dump(meta_payload, f, ensure_ascii=False, indent=2)

    raw_sha = get_file_sha256(raw_file)
    print(f"[+] 실시간 원본 배타적 저장 완료: {raw_file} (SHA: {raw_sha[:12]}..., 카드: {len(raw_cards)}개, 소요: {(end_utc - start_utc).total_seconds():.1f}초)")

    return raw_cards, raw_file, raw_sha, batch_id, start_utc, end_utc


def run_pipeline(
    mode: str = "live",
    input_file: str | None = None,
    db_path_override: Path | None = None,
    lock_file_path: Path | None = None,
    test_hook_fail_after_records: int | None = None,
    test_hook_fail_before_commit: bool = False,
    batch_id: str | None = None,
    **kwargs,
):
    """DIRECTIVE 010-I 실행 메인 파이프라인 (REPLAY/LIVE 완전 격리, 실행 잠금, 부분 쓰기 롤백 보장)."""
    print("=" * 80)
    print(f"CHA-FICIAL AI PROJECT - DIRECTIVE 010-I 실행 (모드: {mode.upper()})")
    print("=" * 80)

    # DIRECTIVE 010-H: 모드별 대상 DB 및 data_origin 엄격 분리
    if mode == "live":
        target_db_path = db_path_override or Path("data/chaficial_market_timeseries.db")
        data_origin = "REAL_OBSERVED"
    elif mode == "replay":
        target_db_path = db_path_override or Path("data/chaficial_replay_benchmark.db")
        data_origin = "REPLAY_FIXTURE"
        # DIRECTIVE 010-H 지침 1: resolve() 기반 운영 DB 지정 차단 (심볼릭 링크 포함)
        if target_db_path.resolve() == OFFICIAL_OPERATIONAL_DB_PATH:
            raise ValueError(
                f"[REPLAY 격리 오류] 운영 DB({OFFICIAL_OPERATIONAL_DB_PATH})는 REPLAY 모드의 대상이 될 수 없습니다. "
                "독립된 벤치마크 DB 또는 임시 DB 경로를 지정하십시오."
            )
    else:
        raise ValueError(f"지원하지 않는 모드입니다: {mode} (live 또는 replay만 허용)")

    # DIRECTIVE 010-H 지침 2: LIVE 모드 실행 시 프로세스 간 실행 잠금 (동시 실행 방지)
    lock_file = lock_file_path or Path("data/.live_run.lock")
    if mode == "live":
        lock_context = FileLockContext(lock_file)
    else:
        # replay 모드는 테스트 병렬 실행 등을 고려하여 별도 잠금 없이 격리 DB 사용
        from contextlib import nullcontext
        lock_context = nullcontext()

    with lock_context:
        target_db_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. 기존 DB 안전 백업 (존재할 경우 SQLite Backup API 및 무결성 검증, 덮어쓰기 금지)
        if target_db_path.exists():
            backup_operational_db_safe(target_db_path)

        # 2. 데이터 수집 또는 재생 로드
        if mode == "live":
            raw_cards, raw_file, raw_sha, batch_id, web_start_utc, web_end_utc = fetch_live_encar_cn7(batch_id_override=batch_id)
        else:
            assert input_file and Path(input_file).exists(), f"입력 파일이 존재하지 않습니다: {input_file}"
            raw_file = Path(input_file)
            raw_sha = get_file_sha256(raw_file)
            with open(raw_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            batch_id = data.get("batch_id") or f"REPLAY_{raw_file.stem}"
            web_start_utc = datetime.fromisoformat(data["collected_at_utc"])
            web_end_utc = datetime.fromisoformat(data["completed_at_utc"])
            raw_cards = data.get("raw_cards", [])
            print(f"[+] 재생 원본 로드: {raw_file} (배치: {batch_id}, 카드: {len(raw_cards)}개, 기원: {data_origin})")

        if not raw_cards:
            raise LiveCollectionError("수집/로드된 매물 카드가 0건입니다.")

        now_iso = web_start_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        live_records: list[StandardListingRecord] = []
        skipped_non_cn7 = 0

        for c in raw_cards:
            parsed_dict = EncarCardParser.parse_card(c, now_iso)
            if not parsed_dict:
                skipped_non_cn7 += 1
                continue

            price_val = int(parsed_dict["price_krw"]) if parsed_dict["price_krw"] else None
            m_val = int(parsed_dict["monthly_payment_krw"]) if parsed_dict["monthly_payment_krw"] else None

            rec = StandardListingRecord(
                source_platform=parsed_dict["source_platform"],
                source_listing_id=parsed_dict["source_listing_id"],
                manufacturer=parsed_dict["manufacturer"],
                model_name=parsed_dict["model_name"],
                model_generation=parsed_dict["model_generation"],
                sub_model=parsed_dict["sub_model"],
                powertrain_line=parsed_dict["powertrain_line"],
                trim_name=parsed_dict["trim_name"],
                model_year=parsed_dict["model_year"],
                registration_year_month=parsed_dict["registration_year_month"],
                mileage_km=int(parsed_dict["mileage_km"]),
                price_krw=price_val,
                monthly_payment_krw=m_val,
                product_type=parsed_dict["product_type"],
                raw_location=parsed_dict["raw_location"],
                vehicle_fingerprint=parsed_dict["vehicle_fingerprint"],
                observed_at=web_start_utc,
                data_origin=data_origin,
            )
            live_records.append(rec)

        if not live_records:
            raise LiveCollectionError(f"파싱된 아반떼 CN7 매물이 0건입니다 (원천 카드 {len(raw_cards)}개 중 CN7 파싱 실패).")

        parsing_rate = (len(live_records) / len(raw_cards)) * 100.0 if raw_cards else 0.0
        print(f"[+] 파싱 완료: 총 {len(raw_cards)}개 카드 중 아반떼 CN7 {len(live_records)}대 정밀 파싱 (파싱률: {parsing_rate:.1f}%, 비CN7 {skipped_non_cn7}개 제외, data_origin={data_origin}).")

        # 3. 타깃 DB 연결 (운영 DB 또는 격리된 벤치마크 DB)
        engine = create_engine(f"sqlite:///{target_db_path}")
        Base.metadata.create_all(engine)
        SessionMaker = sessionmaker(bind=engine)
        session = SessionMaker()

        tracker = PriceEventTracker(consecutive_missing_threshold=3)
        pipeline = MarketObservationStreamPipeline(tracker=tracker)

        scope_cn7 = SearchScopeSpec(
            platform="ENCAR",
            manufacturer="현대",
            model_name="아반떼",
            sub_model="ALL",
        )

        # 실행 전 DB 통계
        pre_listings = session.execute(select(func.count(Listing.listing_id))).scalar()
        pre_snapshots = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
        pre_events = session.execute(select(func.count(PriceEvent.event_id))).scalar()
        pre_batches = session.execute(select(func.count(BatchAuditLog.batch_id))).scalar()

        print(f"[*] 적재 전 DB({target_db_path.name}) 상태: 매물 {pre_listings}대, 스냅샷 {pre_snapshots}건, 이벤트 {pre_events}건, 배치 {pre_batches}건.")

        # 4. 배치 실행 (부분 쓰기 보호, 롤백 보장 및 3대 시각 기록)
        try:
            if test_hook_fail_after_records is not None and test_hook_fail_after_records > 0:
                # DIRECTIVE 010-I: 실제 부분 쓰기(flush) 후 런타임 예외 발생 시뮬레이션
                for r in live_records[:test_hook_fail_after_records]:
                    tracker.process_observation(r, session, data_origin=data_origin)
                session.flush()
                raise RuntimeError(f"Simulated DB Ingest Failure After {test_hook_fail_after_records} Records Written")

            res = pipeline.execute_batch(
                records=live_records,
                session=session,
                batch_id=batch_id,
                scope=scope_cn7,
                observation_time=web_start_utc,
                is_partial_scrape=True,
                data_origin=data_origin,
                web_fetch_started_at=web_start_utc,
                web_fetch_completed_at=web_end_utc,
                notes=f"엔카 아반떼 CN7 관측 ({mode.upper()} 모드, 카드 {len(raw_cards)}개 중 {len(live_records)}대 적재, 부분수집 보호)",
                raw_file_path=raw_file,
                raw_file_sha256=raw_sha,
                auto_commit=False,
            )

            # DIRECTIVE 011-C: execute_batch 정상 반환 후 외부 커밋 직전 실패 주입 훅
            if test_hook_fail_before_commit:
                raise RuntimeError("Simulated Crash Immediately After execute_batch Before Final Commit")

            session.commit()
        except Exception:
            session.rollback()
            session.close()
            raise

        # 실행 후 DB 통계
        post_listings = session.execute(select(func.count(Listing.listing_id))).scalar()
        post_snapshots = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
        post_events = session.execute(select(func.count(PriceEvent.event_id))).scalar()
        post_batches = session.execute(select(func.count(BatchAuditLog.batch_id))).scalar()
        post_links = session.execute(select(func.count(VehicleIdentityLink.link_id))).scalar()

        print(f"[+] 적재 후 DB({target_db_path.name}) 상태: 매물 {post_listings}대 (신규 +{post_listings - pre_listings}), 스냅샷 {post_snapshots}건 (추가 +{post_snapshots - pre_snapshots}), 이벤트 {post_events}건, 배치 {post_batches}건.")
        print(f"[+] 배치 실행 실적: 수집 {res.total_records_ingested}대, FIRST_SEEN(최초발견) {res.first_seen_count}대, 재관측 {res.re_observed_count}대, 가격변동 {res.price_drop_count}건, 미노출의심 {res.delisted_suspect_count}건.")

        # 5. DB 영속 컬럼 논리 SHA-256 해시 계산
        live_db_hashes = compute_db_logical_hashes(session)

    # 6. 공식 운영 LIVE 모드 실행 시 운영 CSV 및 개별 관측 실행 보고서 생성 (DIRECTIVE 010-K 지침)
    if mode == "live" and target_db_path.resolve() == OFFICIAL_OPERATIONAL_DB_PATH:
        # 전체 배치 감사 요약 CSV 갱신
        all_batches = session.execute(
            select(BatchAuditLog).order_by(BatchAuditLog.processed_at.asc())
        ).scalars().all()

        audit_csv = Path("outputs/directive_010_real_market_audit_summary.csv")
        with open(audit_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "batch_id", "source_platform", "search_scope", "processed_at_utc", "processed_at_kst",
                "record_count", "is_partial_scrape", "notes"
            ])
            for b in all_batches:
                writer.writerow([
                    b.batch_id, b.source_platform, b.search_scope,
                    b.processed_at.isoformat() if b.processed_at else "",
                    pipeline.to_kst_string(b.processed_at) if b.processed_at else "",
                    b.record_count, b.is_partial_scrape, b.notes
                ])
        print(f"[+] 누적 배치 감사 요약 CSV 저장: {audit_csv} (총 {len(all_batches)}개 배치 기록)")

        # 전체 실매물 목록 CSV 갱신
        all_listings = session.execute(
            select(Listing).order_by(Listing.first_observed_at.asc())
        ).scalars().all()

        listings_csv = Path("outputs/directive_010_real_observed_listings.csv")
        with open(listings_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "listing_id", "source_platform", "source_listing_id", "first_observed_at",
                "raw_location", "current_status", "consecutive_missing_count"
            ])
            for l in all_listings:
                writer.writerow([
                    l.listing_id, l.source_platform, l.source_listing_id,
                    l.first_observed_at.isoformat(), l.raw_location, l.current_status,
                    l.consecutive_missing_count
                ])
        print(f"[+] 운영 DB 실매물 목록 CSV 저장: {listings_csv} (총 {len(all_listings)}대)")

        # DIRECTIVE 010-K: 최종 승인 감사 보고서(DIRECTIVE_010_COMPLETED_REPORT.md)는 절대 덮어쓰지 않고 보존
        # 각 실행별 관측 보고서는 reports/observations/에 배치 고유 파일명으로 배타적 저장
        obs_dir = Path("reports/observations")
        obs_dir.mkdir(parents=True, exist_ok=True)
        obs_report_file = obs_dir / f"observation_batch_{batch_id}.md"

        obs_report_content = generate_batch_observation_report(
            batch_id=batch_id,
            web_start_utc=web_start_utc,
            web_end_utc=web_end_utc,
            raw_file=raw_file,
            raw_sha=raw_sha,
            total_cards=len(raw_cards),
            parsed_count=len(live_records),
            batch_result=res,
            post_listings=post_listings,
            post_snapshots=post_snapshots,
            post_events=post_events,
            post_batches=post_batches,
            post_links=post_links,
            live_db_hashes=live_db_hashes,
            all_batches=all_batches,
            pipeline=pipeline,
        )

        try:
            with open(obs_report_file, "x", encoding="utf-8") as f:
                f.write(obs_report_content)
            print(f"[+] [DIRECTIVE 010-K] 배치 관측 실행 보고서 배타적 저장 완료: {obs_report_file}")
        except FileExistsError:
            print(f"[!] [DIRECTIVE 010-K] 배치 관측 보고서가 이미 존재합니다 (보존 유지): {obs_report_file}")

    session.close()
    print("=" * 80)
    print(f"[+] DIRECTIVE 010-K 실행 성공! (모드: {mode.upper()})")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CHA-FICIAL DIRECTIVE 010-K Pipeline")
    parser.add_argument("--mode", choices=["live", "replay"], default="live", help="수집 모드 (live 또는 replay)")
    parser.add_argument("--input", type=str, default=None, help="replay 모드 시 입력 JSON 파일 경로")
    args = parser.parse_args()

    run_pipeline(mode=args.mode, input_file=args.input)
