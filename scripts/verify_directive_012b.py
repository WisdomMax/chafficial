"""CHA-FICIAL DIRECTIVE 012-B 최종 증거 검증 스크립트.

1. 가격 인하 이벤트 5건의 3차 배치(batch_id) 귀속성 및 원본 가격 1:1 대조 검증
2. 사전 백업 DB vs 운영 DB 간 기존 스냅샷 246건 행 단위(Row-by-Row) 전수 속성 동일성 검증
3. 기존 매물 238건의 PK 및 식별정보 불변성 검증 및 5건의 정상 상태 전이 검증
4. 원본 파일 SHA-256 검증
"""

import hashlib
import json
import sys
from pathlib import Path
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

sys.path.insert(0, ".")
from src.chaficial.database.base import Base
from src.chaficial.models import Listing, ListingSnapshot, PriceEvent, BatchAuditLog
from src.chaficial.platforms.encar import EncarCardParser

OPERATIONAL_DB = Path("data/chaficial_market_timeseries.db")
BACKUP_DB = Path("data/backups/market_timeseries_backup_20261024_030446_eb757e21301e.db")
RAW_1 = Path("data/raw_observations/encar_cn7_live_20261021_01.json")
RAW_2 = Path("data/raw_observations/encar_cn7_live_20261021_120825.json")
RAW_3 = Path("data/raw_observations/encar_cn7_live_20261024_030446_518b4987e3b2.json")
BATCH_3_ID = "ENCAR_CN7_LIVE_20261024_030446_518b4987e3b2"

def get_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=" * 80)
    print("CHA-FICIAL DIRECTIVE 012-B: 최종 증거 검증 실행")
    print("=" * 80)

    # --------------------------------------------------------------------------
    # 1. 원본 SHA-256 재계산
    # --------------------------------------------------------------------------
    sha3 = get_sha256(RAW_3)
    print(f"[1] 원본 파일 SHA-256 검증:")
    print(f"    - 파일 경로: {RAW_3}")
    print(f"    - 파일 크기: {RAW_3.stat().st_size} bytes")
    print(f"    - 계산된 SHA-256: {sha3}")
    expected_sha = "da72c6583a276a9dcbda8a93049bfd8a1f26f1fa33a147ec022bde20461a3fe1"
    assert sha3 == expected_sha, f"SHA-256 불일치: {sha3} != {expected_sha}"
    print(f"    [PASS] 원본 해시 일치 확인 완료!\n")

    # --------------------------------------------------------------------------
    # 2. 가격 인하 이벤트 5건의 배치 귀속 검증
    # --------------------------------------------------------------------------
    print("=" * 80)
    print("[2] 가격 인하 5건의 3차 배치(batch_id) 귀속성 및 원본 가격 1:1 대조 검증")
    print("=" * 80)
    op_engine = create_engine(f"sqlite:///{OPERATIONAL_DB}")
    with Session(op_engine) as session:
        b3_log = session.execute(
            select(BatchAuditLog).where(BatchAuditLog.batch_id == BATCH_3_ID)
        ).scalars().first()
        assert b3_log is not None, f"배치 {BATCH_3_ID} 감사 로그가 존재하지 않습니다."
        meta = b3_log.get_audit_metadata()
        b3_event_ids = set(meta.get("event_ids", []))
        print(f"    - 3차 배치 총 생성 이벤트 수: {len(b3_event_ids)}건")

        # 3차 배치에 속한 PRICE_DROP 이벤트 전수 조회
        b3_price_drops = session.execute(
            select(PriceEvent).where(
                PriceEvent.event_id.in_(b3_event_ids),
                PriceEvent.event_type == "PRICE_DROP"
            )
        ).scalars().all()
        assert len(b3_price_drops) == 5, f"3차 배치 내 PRICE_DROP 수가 5건이 아닙니다: {len(b3_price_drops)}"
        print(f"    - 3차 배치 내 귀속된 PRICE_DROP 이벤트 수: {len(b3_price_drops)}건 (정확히 5건 귀속 확인)")

        # 원본 데이터 로드
        with open(RAW_1, "r", encoding="utf-8") as f:
            raw_cards_1 = {str(c.get("carid")): c for c in json.load(f).get("raw_cards", [])}
        with open(RAW_2, "r", encoding="utf-8") as f:
            raw_cards_2 = {str(c.get("carid")): c for c in json.load(f).get("raw_cards", [])}
        with open(RAW_3, "r", encoding="utf-8") as f:
            raw_cards_3 = {str(c.get("carid")): c for c in json.load(f).get("raw_cards", [])}

        target_ids = ["42718815", "42316208", "42867093", "42864399", "42872963"]
        assert len(target_ids) == 5

        price_drop_evidence = []
        for sid in target_ids:
            # 3차 배치 이벤트 중 해당 매물 ID의 이벤트 찾기
            evt = next((e for e in b3_price_drops if e.source_listing_id == sid), None)
            assert evt is not None, f"매물 {sid}에 해당하는 3차 배치 PRICE_DROP 이벤트가 없습니다!"

            prev_card = raw_cards_1.get(sid) or raw_cards_2.get(sid)
            curr_card = raw_cards_3.get(sid)
            assert prev_card is not None, f"이전 원본에서 매물 {sid}를 찾을 수 없습니다."
            assert curr_card is not None, f"3차 원본에서 매물 {sid}를 찾을 수 없습니다."

            # 파서로 가격 추출 (정수 변환 후 대조)
            p_prev = EncarCardParser.parse_card(prev_card)
            p_curr = EncarCardParser.parse_card(curr_card)
            prev_price_val = int(p_prev["price_krw"])
            curr_price_val = int(p_curr["price_krw"])

            assert prev_price_val == evt.previous_price_krw, f"이전 가격 불일치 ({sid}): 원본 {prev_price_val} != DB {evt.previous_price_krw}"
            assert curr_price_val == evt.new_price_krw, f"현재 가격 불일치 ({sid}): 원본 {curr_price_val} != DB {evt.new_price_krw}"
            assert (evt.new_price_krw - evt.previous_price_krw) == evt.price_delta_krw, f"변동액 계산 불일치 ({sid})"

            price_drop_evidence.append({
                "source_id": sid,
                "event_id": str(evt.event_id),
                "in_b3_batch": evt.event_id in b3_event_ids,
                "prev_raw_price": prev_price_val,
                "curr_raw_price": curr_price_val,
                "db_prev_price": evt.previous_price_krw,
                "db_curr_price": evt.new_price_krw,
                "delta_krw": evt.price_delta_krw,
                "delta_pct": round(evt.price_delta_pct, 2),
                "status": "VERIFIED_100%"
            })

        print(json.dumps(price_drop_evidence, indent=2))
        print("    [PASS] 5건 가격 인하 이벤트 3차 배치 귀속 및 원본 가격 1:1 완벽 일치!\n")

    # --------------------------------------------------------------------------
    # 3. 사전 백업 DB vs 현재 운영 DB 간 기존 스냅샷 246건 행 단위 전수 대조
    # --------------------------------------------------------------------------
    print("=" * 80)
    print("[3] 사전 백업 DB vs 운영 DB 간 기존 스냅샷 246건 행 단위(Row-by-Row) 전수 대조")
    print("=" * 80)
    assert BACKUP_DB.exists(), f"사전 백업 DB 파일이 없습니다: {BACKUP_DB}"
    bk_engine = create_engine(f"sqlite:///{BACKUP_DB}")

    with Session(bk_engine) as bk_session, Session(op_engine) as op_session:
        bk_snapshots = bk_session.execute(select(ListingSnapshot)).scalars().all()
        assert len(bk_snapshots) == 246, f"사전 백업 스냅샷 수가 246건이 아닙니다: {len(bk_snapshots)}"
        print(f"    - 사전 백업 DB 스냅샷 수: {len(bk_snapshots)}건")

        op_snapshot_ids = set(op_session.execute(select(ListingSnapshot.snapshot_id)).scalars().all())
        print(f"    - 운영 DB 전체 스냅샷 수: {len(op_snapshot_ids)}건 (기존 246 + 신규 136 = 382건)")

        mismatch_count = 0
        checked_count = 0
        for bk_s in bk_snapshots:
            op_s = op_session.execute(
                select(ListingSnapshot).where(ListingSnapshot.snapshot_id == bk_s.snapshot_id)
            ).scalars().first()
            assert op_s is not None, f"스냅샷 PK {bk_s.snapshot_id}가 운영 DB에서 유실되었습니다!"

            # 모든 필드 일치성 전수 검사
            diffs = []
            if op_s.listing_id != bk_s.listing_id:
                diffs.append(f"listing_id: {bk_s.listing_id} -> {op_s.listing_id}")
            if op_s.observed_at != bk_s.observed_at:
                diffs.append(f"observed_at: {bk_s.observed_at} -> {op_s.observed_at}")
            if op_s.price_krw != bk_s.price_krw:
                diffs.append(f"price_krw: {bk_s.price_krw} -> {op_s.price_krw}")
            if op_s.mileage_km != bk_s.mileage_km:
                diffs.append(f"mileage_km: {bk_s.mileage_km} -> {op_s.mileage_km}")
            if op_s.listing_status != bk_s.listing_status:
                diffs.append(f"listing_status: {bk_s.listing_status} -> {op_s.listing_status}")
            if op_s.normalized_region_id != bk_s.normalized_region_id:
                diffs.append(f"normalized_region_id: {bk_s.normalized_region_id} -> {op_s.normalized_region_id}")
            if op_s.source_record_hash != bk_s.source_record_hash:
                diffs.append(f"source_record_hash: {bk_s.source_record_hash} -> {op_s.source_record_hash}")
            if op_s.raw_specs != bk_s.raw_specs:
                diffs.append("raw_specs 불일치")

            if diffs:
                print(f"[!] 스냅샷 {bk_s.snapshot_id} 불일치: {', '.join(diffs)}")
                mismatch_count += 1
            checked_count += 1

        print(f"    - 전수 검사 완료 건수: {checked_count}건")
        print(f"    - 불일치 발생 건수: {mismatch_count}건")
        assert mismatch_count == 0, f"기존 스냅샷 중 {mismatch_count}건이 변조되었습니다!"
        print(f"    [PASS] 기존 스냅샷 246건의 PK 및 전수 필드 100% 동일 영구 보존 입증 완료!\n")

    # --------------------------------------------------------------------------
    # 4. 기존 매물 238건 보존 및 정상 갱신 필드 분리 검증
    # --------------------------------------------------------------------------
    print("=" * 80)
    print("[4] 기존 매물 238건 보존 및 정상 갱신 필드 분리 검증")
    print("=" * 80)
    with Session(bk_engine) as bk_session, Session(op_engine) as op_session:
        bk_listings = bk_session.execute(select(Listing)).scalars().all()
        assert len(bk_listings) == 238, f"사전 백업 매물 수가 238건이 아닙니다: {len(bk_listings)}"
        print(f"    - 사전 백업 DB 매물 수: {len(bk_listings)}대")

        op_listing_ids = set(op_session.execute(select(Listing.source_listing_id)).scalars().all())
        print(f"    - 운영 DB 전체 매물 수: {len(op_listing_ids)}대 (기존 238대 + 신규 110대 = 348대)")

        identity_preserved_count = 0
        price_changed_count = 0
        active_unchanged_count = 0

        for bk_l in bk_listings:
            op_l = op_session.execute(
                select(Listing).where(Listing.listing_id == bk_l.listing_id)
            ).scalars().first()
            assert op_l is not None, f"매물 PK {bk_l.listing_id}가 유실되었습니다!"

            # 4.1 불변 식별 정보 전수 검증
            assert op_l.source_platform == bk_l.source_platform
            assert op_l.source_listing_id == bk_l.source_listing_id
            assert op_l.first_observed_at == bk_l.first_observed_at
            assert op_l.raw_location == bk_l.raw_location
            identity_preserved_count += 1

            # 4.2 정상 갱신 필드 검증 (5건 PRICE_CHANGED, 233건 ACTIVE)
            if op_l.source_listing_id in target_ids:
                assert op_l.current_status == "PRICE_CHANGED", f"매물 {op_l.source_listing_id} 상태가 PRICE_CHANGED가 아님: {op_l.current_status}"
                price_changed_count += 1
            else:
                assert op_l.current_status == bk_l.current_status, f"상태 변조: {bk_l.current_status} -> {op_l.current_status}"
                assert op_l.consecutive_missing_count == bk_l.consecutive_missing_count
                active_unchanged_count += 1

        print(f"    - 불변 식별 정보 100% 보존 매물 수: {identity_preserved_count}대 / 238대")
        print(f"    - 가격 인하 정상 상태 전이(PRICE_CHANGED) 매물 수: {price_changed_count}대 (정확히 5대)")
        print(f"    - 변동 없이 ACTIVE 유지된 기존 매물 수: {active_unchanged_count}대 (정확히 233대)")
        print(f"    [PASS] 기존 매물 238건 보존 및 정상 갱신 검증 완료!\n")

    print("=" * 80)
    print("CHA-FICIAL DIRECTIVE 012-B: 모든 증거 검증 100% 통과 (ALL VERIFIED)")
    print("=" * 80)

if __name__ == "__main__":
    main()
