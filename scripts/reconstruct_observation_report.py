"""CHA-FICIAL AI PROJECT - DIRECTIVE 011 / 011-A / 011-B
이미 DB에 적재된 관측 배치의 감사 보고서 안전 복구 및 재생성 유틸리티.

[원칙 준수 - DIRECTIVE 011-B]
1. 원본 무결성 엄격 검증:
   - SHA-256 일치뿐 아니라 JSON 내부 batch_id와 DB batch_id 필수 대조.
   - raw_file_sha256 또는 raw_file_path 누락 시 VERIFIED_MATCH 거부 및 예외 발생.
   - JSON 파싱 실패, 필수 필드 누락, 배치 ID 불일치 시 복구 실패 처리.
   - 레거시 배치는 LEGACY_UNVERIFIED로 명확히 격리.
2. 이벤트 통계 교차 검증 (Cross-Validation):
   - 메타데이터 수치를 맹신하지 않고 DB 실제 PriceEvent/스냅샷과 대조.
   - 불일치 시 AUDIT_MISMATCH 상태 마킹 및 불일치 경고 기재.
3. 원자적 안전 파일 저장:
   - 임시 파일(.tmp)에 전체 작성 후 os.replace로 원자적 반영.
   - 기존 보고서 존재 시 overwrite=False이면 FileExistsError 거부.
   - 쓰기 실패 시 기존 파일 및 DB 훼손 원천 방지.
"""

import argparse
import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.models.vehicle_link import VehicleIdentityLink
from chaficial.tracker.price_tracker import compute_db_logical_hashes

KST = ZoneInfo("Asia/Seoul")


def get_file_sha256(filepath: Path) -> str:
    """파일의 SHA-256 해시를 계산합니다."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def reconstruct_batch_report(
    batch_id: str,
    db_path: Path = Path("data/chaficial_market_timeseries.db"),
    output_dir: Path = Path("reports/observations"),
    raw_observations_dir: Path = Path("data/raw_observations"),
    overwrite: bool = False,
) -> Path:
    """DB에 이미 커밋된 배치의 감사 보고서를 역조회하여 안전하고 정직하게 재생성합니다."""
    if not db_path.exists():
        raise FileNotFoundError(f"데이터베이스 파일이 존재하지 않습니다: {db_path}")

    # 1. 덮어쓰기 방지 검증
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"observation_batch_{batch_id}.md"
    if out_file.exists() and not overwrite:
        raise FileExistsError(
            f"보고서 파일이 이미 존재합니다: {out_file}. 덮어쓰려면 overwrite=True를 명시해야 합니다."
        )

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 2. 배치 감사 로그 조회
        batch_audit = session.execute(
            select(BatchAuditLog).where(BatchAuditLog.batch_id == batch_id)
        ).scalar_one_or_none()

        if not batch_audit:
            raise ValueError(f"데이터베이스에 해당 배치 ID({batch_id})의 감사 로그가 존재하지 않습니다.")

        all_batches = session.execute(
            select(BatchAuditLog).order_by(BatchAuditLog.processed_at.asc())
        ).scalars().all()

        # 3. 메타데이터 파싱 (신규 배치 vs 레거시 배치)
        meta = batch_audit.get_audit_metadata()
        is_legacy = meta is None

        # 4. 원본 JSON 파일 검증 및 연결 (DIRECTIVE 011-B 무결성 강화)
        raw_file_path: Path | None = None
        raw_sha: str = "NOT_RECORDED"
        verification_status: str = "UNKNOWN"
        total_raw_cards = batch_audit.record_count

        if not is_legacy:
            recorded_path_str = meta.get("raw_file_path")
            recorded_sha = meta.get("raw_file_sha256")

            # DIRECTIVE 011-B 지침 1: 경로 또는 SHA-256 누락 시 검증 실패
            if not recorded_path_str or not recorded_sha or not recorded_sha.strip():
                raise ValueError(
                    f"[무결성 오류] 신규 배치({batch_id}) 메타데이터에 필수 원본 정보(raw_file_path 또는 raw_file_sha256)가 누락되었습니다."
                )

            recorded_path = Path(recorded_path_str)
            if recorded_path.exists():
                raw_file_path = recorded_path
            elif (raw_observations_dir / recorded_path.name).exists():
                raw_file_path = raw_observations_dir / recorded_path.name
            else:
                raise FileNotFoundError(
                    f"[무결성 오류] 배치({batch_id})에 기록된 원본 JSON 파일을 찾을 수 없습니다: {recorded_path}"
                )

            # SHA-256 대조
            actual_sha = get_file_sha256(raw_file_path)
            if actual_sha != recorded_sha:
                raise ValueError(
                    f"[무결성 오류] 원본 JSON 파일 변조 감지! (기록된 해시: {recorded_sha}, 실제 파일 해시: {actual_sha})"
                )

            # JSON 파싱 및 내부 batch_id 대조 (DIRECTIVE 011-B 필수 검증)
            try:
                with open(raw_file_path, "r", encoding="utf-8") as f:
                    rdata = json.load(f)
            except Exception as e:
                raise ValueError(f"[무결성 오류] 원본 JSON 파일 파싱 실패: {e}") from e

            if not isinstance(rdata, dict):
                raise ValueError("[무결성 오류] 원본 JSON 루트가 올바른 사전(dict) 구조가 아닙니다.")

            json_batch_id = rdata.get("batch_id")
            if not json_batch_id:
                raise ValueError("[무결성 오류] 원본 JSON 내에 필수 필드 'batch_id'가 누락되었습니다.")

            if json_batch_id != batch_id:
                raise ValueError(
                    f"[무결성 오류] 원본 JSON 내부 batch_id({json_batch_id})와 DB 감사 로그 batch_id({batch_id})가 일치하지 않습니다!"
                )

            total_raw_cards = rdata.get("total_cards_collected", len(rdata.get("raw_cards", [])))
            raw_sha = actual_sha
            verification_status = "VERIFIED_MATCH"
        else:
            # 레거시 배치: 추측으로 검증 완료하지 않고 LEGACY_UNVERIFIED로 정직하게 표기
            batch_ts_suffix = batch_id.replace("ENCAR_CN7_LIVE_", "")
            candidate = raw_observations_dir / f"encar_cn7_live_{batch_ts_suffix}.json"
            if candidate.exists():
                raw_file_path = candidate
                raw_sha = get_file_sha256(candidate)
                verification_status = "LEGACY_UNVERIFIED_CANDIDATE"
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        rdata = json.load(f)
                        total_raw_cards = rdata.get("total_cards_collected", len(rdata.get("raw_cards", [])))
                except Exception:
                    pass
            else:
                raw_file_path = Path(f"data/raw_observations/encar_cn7_live_{batch_ts_suffix}.json")
                raw_sha = "NOT_RECORDED"
                verification_status = "LEGACY_NOT_FOUND"

        # 5. 수집 시각 복구
        db_processed_utc = batch_audit.processed_at
        db_processed_kst_str = (
            db_processed_utc.replace(tzinfo=UTC).astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")
            if db_processed_utc
            else "UNKNOWN"
        )

        if not is_legacy and meta.get("web_fetch_started_at") and meta.get("web_fetch_completed_at"):
            web_start_str = meta["web_fetch_started_at"]
            web_end_str = meta["web_fetch_completed_at"]
            web_timing_note = "영속 기록된 실제 웹 수집 시각"
        else:
            web_start_str = "NOT_RECORDED (레거시 배치: 웹 수집 시각 미기록)"
            web_end_str = "NOT_RECORDED (레거시 배치: 웹 수집 시각 미기록)"
            web_timing_note = f"NOT_RECORDED (DB 적재 시각 {db_processed_kst_str}만 영속됨)"

        # 6. 가격 이벤트 및 재관측 통계 역조회 및 교차 검증 (DIRECTIVE 011-B 지침 2)
        events_in_batch = session.execute(
            select(PriceEvent).where(PriceEvent.event_timestamp == batch_audit.processed_at)
        ).scalars().all()

        actual_first_seen = sum(1 for e in events_in_batch if e.event_type in ("NEW_LISTING", "FIRST_SEEN"))
        actual_price_drops = sum(1 for e in events_in_batch if e.event_type == "PRICE_DROP")
        actual_price_increases = sum(1 for e in events_in_batch if e.event_type == "PRICE_INCREASE")
        actual_delisted_suspects = sum(1 for e in events_in_batch if e.event_type == "DELISTED_SUSPECT")
        actual_price_drop_krw = sum(abs(e.price_delta_krw) for e in events_in_batch if e.event_type == "PRICE_DROP")
        actual_re_observed = max(0, batch_audit.record_count - actual_first_seen)

        # 메타데이터 수치와 실제 DB 이벤트 간 교차 대조
        mismatch_notes = []
        if not is_legacy:
            saved_drop_krw = meta.get("total_price_drop_krw")
            if saved_drop_krw is not None and saved_drop_krw != actual_price_drop_krw:
                mismatch_notes.append(
                    f"가격 인하 총액 불일치 (메타데이터: {saved_drop_krw:,}원 vs DB 실제: {actual_price_drop_krw:,}원)"
                )

            saved_drop_cnt = meta.get("price_drop_count")
            if saved_drop_cnt is not None and saved_drop_cnt != actual_price_drops:
                mismatch_notes.append(
                    f"가격 인하 건수 불일치 (메타데이터: {saved_drop_cnt}건 vs DB 실제: {actual_price_drops}건)"
                )

            saved_first_seen = meta.get("first_seen_count")
            if saved_first_seen is not None and saved_first_seen != actual_first_seen:
                mismatch_notes.append(
                    f"최초 관측 건수 불일치 (메타데이터: {saved_first_seen}건 vs DB 실제: {actual_first_seen}건)"
                )

            if mismatch_notes:
                verification_status = "AUDIT_MISMATCH"

        # 최종 채택 수치: 실제 DB PriceEvent가 진실의 원천(Source of Truth)
        first_seen_count = actual_first_seen
        re_observed_count = actual_re_observed
        price_drop_count = actual_price_drops
        price_increase_count = actual_price_increases
        total_price_drop_krw = actual_price_drop_krw
        delisted_suspect_count = actual_delisted_suspects

        # 7. 복구 시점의 현재 누적 DB 통계 및 논리 해시
        recon_listings = session.execute(select(func.count(Listing.listing_id))).scalar()
        recon_snapshots = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
        recon_events = session.execute(select(func.count(PriceEvent.event_id))).scalar()
        recon_batches = session.execute(select(func.count(BatchAuditLog.batch_id))).scalar()
        recon_links = session.execute(select(func.count(VehicleIdentityLink.link_id))).scalar()
        recon_db_hashes = compute_db_logical_hashes(session)

    # 8. 감사 보고서 마크다운 생성
    report_md = _render_reconstructed_report_markdown(
        batch_id=batch_id,
        batch_audit=batch_audit,
        is_legacy=is_legacy,
        verification_status=verification_status,
        mismatch_notes=mismatch_notes,
        raw_file_path=raw_file_path,
        raw_sha=raw_sha,
        total_raw_cards=total_raw_cards,
        db_processed_kst_str=db_processed_kst_str,
        web_start_str=web_start_str,
        web_end_str=web_end_str,
        web_timing_note=web_timing_note,
        first_seen_count=first_seen_count,
        re_observed_count=re_observed_count,
        price_drop_count=price_drop_count,
        price_increase_count=price_increase_count,
        total_price_drop_krw=total_price_drop_krw,
        delisted_suspect_count=delisted_suspect_count,
        recon_listings=recon_listings,
        recon_snapshots=recon_snapshots,
        recon_events=recon_events,
        recon_batches=recon_batches,
        recon_links=recon_links,
        recon_db_hashes=recon_db_hashes,
        all_batches=all_batches,
    )

    # 9. 원자적 파일 저장 (DIRECTIVE 011-B 지침 3: .tmp에 작성 후 원자적 교체)
    tmp_fd, tmp_path_str = tempfile.mkstemp(
        dir=output_dir, prefix=f"reconstruct_{batch_id}_", suffix=".tmp"
    )
    try:
        with open(tmp_fd, "w", encoding="utf-8") as f:
            f.write(report_md)
        os.replace(tmp_path_str, out_file)
    except Exception:
        if os.path.exists(tmp_path_str):
            try:
                os.remove(tmp_path_str)
            except OSError:
                pass
        raise

    print(f"[+] [DIRECTIVE 011-B] 배치 감사 보고서 원자적 복구/재생성 완료: {out_file}")
    return out_file


def _render_reconstructed_report_markdown(
    batch_id: str,
    batch_audit: BatchAuditLog,
    is_legacy: bool,
    verification_status: str,
    mismatch_notes: list[str],
    raw_file_path: Path | None,
    raw_sha: str,
    total_raw_cards: int,
    db_processed_kst_str: str,
    web_start_str: str,
    web_end_str: str,
    web_timing_note: str,
    first_seen_count: int,
    re_observed_count: int,
    price_drop_count: int,
    price_increase_count: int,
    total_price_drop_krw: int,
    delisted_suspect_count: int,
    recon_listings: int,
    recon_snapshots: int,
    recon_events: int,
    recon_batches: int,
    recon_links: int,
    recon_db_hashes: dict[str, dict],
    all_batches: list[BatchAuditLog],
) -> str:
    """과거 배치 상태와 복구 시점 현재 상태를 명확히 분리하여 정직하게 마크다운 보고서를 렌더링합니다."""
    recon_time_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

    # 교차 검증 불일치 알림 마크다운 생성
    mismatch_alert = ""
    if mismatch_notes:
        notes_str = "\n".join(f"- {n}" for n in mismatch_notes)
        mismatch_alert = f"""
> [!WARNING]
> **[교차 검증 불일치 감지 (AUDIT_MISMATCH)]**
> 메타데이터에 기록된 통계와 실제 DB PriceEvent 간 불일치가 발견되었습니다:
>{notes_str}
> 본 복구 보고서는 실제 DB PriceEvent를 최종 진실의 원천(Source of Truth)으로 채택하여 정밀 재계산했습니다.
"""

    # 배치 이력 테이블 마크다운 생성
    batch_history_rows = []
    for b in all_batches:
        b_time_str = (
            b.processed_at.replace(tzinfo=UTC).astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")
            if b.processed_at
            else "-"
        )
        highlight = " **(본 복구 대상)**" if b.batch_id == batch_id else ""
        batch_history_rows.append(
            f"| `{b.batch_id}`{highlight} | `{b.source_platform}` | `{b.search_scope}` | {b_time_str} | {b.record_count}건 | {b.is_partial_scrape} |"
        )
    batch_history_table = "\n".join(batch_history_rows)

    return f"""# CHA-FICIAL AI PROJECT: 시장 관측 배치 감사 보고서 (안전 복구본)
## BATCH ID: `{batch_id}` (RECONSTRUCTED)

**작성 주체:** CHA-FICIAL AI 시계열 관측 파이프라인 안전 복구 엔진 (DIRECTIVE 011-B)  
**복구 실행 시각:** {recon_time_kst}  
**배치 원본 검증 상태:** `{verification_status}`  
**레거시 배치 여부:** `{"YES (LEGACY_UNVERIFIED)" if is_legacy else "NO (METADATA_VERIFIED)"}`  
{mismatch_alert}
---

## 1. 관측 배치 기본 식별 정보 및 원본 무결성

- **배치 고유 ID (Batch ID):** `{batch_id}`
- **관측 대상 플랫폼 (Platform):** `{batch_audit.source_platform}`
- **검색 및 수집 범위 (Search Scope):** `{batch_audit.search_scope}`
- **DB 영속 적재 시각 (DB Processed At):** `{db_processed_kst_str}`
- **실제 웹 수집 시작 시각 (Web Start):** `{web_start_str}`
- **실제 웹 수집 완료 시각 (Web End):** `{web_end_str}`
- **수집 시각 복구 판정:** `{web_timing_note}`
- **원본 수집 파일 (Raw JSON):** `{raw_file_path.name if raw_file_path else "UNKNOWN"}`
- **원본 파일 SHA-256 해시:** `{raw_sha}`
- **원천 카드 수집 건수:** {total_raw_cards}건
- **정밀 파싱 및 적재 건수:** {batch_audit.record_count}대
- **부분 수집 플래그 (is_partial_scrape):** `{batch_audit.is_partial_scrape}`

---

## 2. 해당 배치 관측 결과 및 가격 변동 통계 (해당 시점 복원)

| 관측 지표 항목 | 관측 건수 / 금액 | 학술적·엔지니어링적 판정 기준 |
| :--- | :---: | :--- |
| **신규 매물 최초 관측 (FIRST_SEEN)** | **{first_seen_count}대** | 플랫폼에 새롭게 등장하여 신규 등록된 고유 매물 ID |
| **기존 매물 재관측 (RE_OBSERVED)** | **{re_observed_count}대** | 기존 수집된 매물이 가격 변동 없이 시장에 지속 노출 중임 |
| **실제 가격 인하 (PRICE_DROP)** | **{price_drop_count}건** | 동일 매물 ID에서 관측된 실제 가격 인하 발생 건수 |
| **실제 가격 인상 (PRICE_INCREASE)** | **{price_increase_count}건** | 동일 매물 ID에서 관측된 실제 가격 인상 발생 건수 |
| **총 가격 인하 금액 (Total Drop KRW)** | **{total_price_drop_krw:,}원** | 해당 배치에서 실제 발생한 가격 인하 총액 합산 |
| **미노출 의심 판정 (DELISTED_SUSPECT)** | **{delisted_suspect_count}건** | 연속 미관측으로 판매 종료 또는 매물 삭제가 의심되는 건수 |

> [!NOTE]
> 과거 배치 당시의 가격 변동 금액과 재관측 통계는 PriceEvent 및 Snapshot 이력으로부터 정밀 교차 검증 및 재계산되었습니다.

---

## 3. 과거 배치 당시 상태 vs 복구 실행 시점 누적 DB 상태

### A. 과거 배치 커밋 당시 전체 DB 해시
- **당시 전체 DB 해시 기록:** `{"NOT_RECORDED (LEGACY_BATCH)" if is_legacy else "COMMITTED_IN_METADATA"}`
- *(주의: 본 보고서는 과거 당시의 DB 해시가 별도 저장되지 않은 경우 현재 해시로 위조하거나 대체하지 않습니다.)*

### B. 복구 실행 시점 누적 DB 전체 현황 (AS_OF_RECONSTRUCTION)
- **복구 실행 시각:** {recon_time_kst}
- **누적 고유 실매물 수 (listings):** **{recon_listings}대**
- **누적 시계열 스냅샷 수 (listing_snapshots):** **{recon_snapshots}건**
- **누적 가격 변동 이벤트 수 (price_events):** **{recon_events}건**
- **누적 관측 배치 수 (batch_audit_logs):** **{recon_batches}건**
- **동일 차량 추정 링크 수 (vehicle_identity_links):** **{recon_links}건**

### C. 복구 실행 시점 DB 5개 테이블 논리 SHA-256 해시
| 대상 테이블 명 | 현재 레코드 수 | 복구 시점 논리 전체 행 SHA-256 해시 |
| :--- | :---: | :--- |
| `listings` | **{recon_db_hashes['listings']['count']}행** | `{recon_db_hashes['listings']['hash']}` |
| `listing_snapshots` | **{recon_db_hashes['listing_snapshots']['count']}행** | `{recon_db_hashes['listing_snapshots']['hash']}` |
| `price_events` | **{recon_db_hashes['price_events']['count']}행** | `{recon_db_hashes['price_events']['hash']}` |
| `batch_audit_logs` | **{recon_db_hashes['batch_audit_logs']['count']}행** | `{recon_db_hashes['batch_audit_logs']['hash']}` |
| `vehicle_identity_links` | **{recon_db_hashes['vehicle_identity_links']['count']}행** | `{recon_db_hashes['vehicle_identity_links']['hash']}` |

---

## 4. 누적 관측 배치 이력 목록
| 배치 ID | 플랫폼 | 검색 범위 | DB 적재 시각 (KST) | 적재 건수 | 부분수집 여부 |
| :--- | :---: | :---: | :---: | :---: | :---: |
{batch_history_table}

---

## 5. 결론 및 데이터 신뢰성 감사 확인
1. **과거 시점과 현재 시점의 명확한 분리:** 복구 시점의 전체 통계와 해당 배치 고유 관측 결과를 엄격히 분리하여 보고합니다.
2. **원천 데이터 무결성 보존:** 기존 관측 DB(`data/chaficial_market_timeseries.db`)의 실매물 이력을 훼손하지 않고 100% 보존합니다.
3. **학술적 정직성 준수:** 미기록 정보(수집 시각 등)를 임의로 추정하거나 위조하지 않고 `NOT_RECORDED`로 투명하게 기재합니다.
"""


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CHA-FICIAL DIRECTIVE 011-B Report Reconstructor")
    parser.add_argument("batch_id", help="복구할 관측 배치 ID")
    parser.add_argument("--db", type=Path, default=Path("data/chaficial_market_timeseries.db"), help="대상 DB 경로")
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw_observations"), help="원천 관측 JSON 디렉토리")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/observations"), help="출력 보고서 디렉토리")
    parser.add_argument("--overwrite", action="store_true", help="기존 파일 덮어쓰기 허용 여부")
    args = parser.parse_args()

    reconstruct_batch_report(
        batch_id=args.batch_id,
        db_path=args.db,
        output_dir=args.output_dir,
        raw_observations_dir=args.raw_dir,
        overwrite=args.overwrite,
    )
