"""DIRECTIVE 012-B 최종 증거 검증 테스트 스위트.

1. 5건의 가격 인하 이벤트 3차 배치 귀속 및 원본 가격 1:1 일치성 검증
2. 사전 백업본 대비 기존 스냅샷 246건 행 단위(Row-by-Row) 전수 속성 불변성 검증
3. 기존 매물 238건 식별 정보 보존 및 5건의 정상 상태 전이 검증
"""

import hashlib
import json
from pathlib import Path
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from chaficial.models import Listing, ListingSnapshot, PriceEvent, BatchAuditLog
from chaficial.platforms.encar import EncarCardParser

OPERATIONAL_DB = Path("data/chaficial_market_timeseries.db")
BACKUP_DB = Path("data/backups/market_timeseries_backup_20261024_030446_eb757e21301e.db")
RAW_1 = Path("data/raw_observations/encar_cn7_live_20261021_01.json")
RAW_2 = Path("data/raw_observations/encar_cn7_live_20261021_120825.json")
RAW_3 = Path("data/raw_observations/encar_cn7_live_20261024_030446_518b4987e3b2.json")
BATCH_3_ID = "ENCAR_CN7_LIVE_20261024_030446_518b4987e3b2"
EXPECTED_SHA = "da72c6583a276a9dcbda8a93049bfd8a1f26f1fa33a147ec022bde20461a3fe1"
TARGET_IDS = ["42718815", "42316208", "42867093", "42864399", "42872963"]


def test_raw_observation_sha256():
    """원본 파일 바이트 해시 무결성 검증."""
    h = hashlib.sha256()
    with open(RAW_3, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    assert h.hexdigest() == EXPECTED_SHA


def test_price_drop_attribution_and_raw_match():
    """가격 인하 5건의 3차 배치 귀속성 및 원본 가격 1:1 일치 검증."""
    engine = create_engine(f"sqlite:///{OPERATIONAL_DB}")
    with Session(engine) as session:
        b3_log = session.execute(
            select(BatchAuditLog).where(BatchAuditLog.batch_id == BATCH_3_ID)
        ).scalars().first()
        assert b3_log is not None
        meta = b3_log.get_audit_metadata()
        b3_event_ids = set(meta.get("event_ids", []))

        b3_price_drops = session.execute(
            select(PriceEvent).where(
                PriceEvent.event_id.in_(b3_event_ids),
                PriceEvent.event_type == "PRICE_DROP"
            )
        ).scalars().all()
        assert len(b3_price_drops) == 5

        with open(RAW_1, "r", encoding="utf-8") as f:
            cards_1 = {str(c.get("carid")): c for c in json.load(f).get("raw_cards", [])}
        with open(RAW_2, "r", encoding="utf-8") as f:
            cards_2 = {str(c.get("carid")): c for c in json.load(f).get("raw_cards", [])}
        with open(RAW_3, "r", encoding="utf-8") as f:
            cards_3 = {str(c.get("carid")): c for c in json.load(f).get("raw_cards", [])}

        for sid in TARGET_IDS:
            evt = next((e for e in b3_price_drops if e.source_listing_id == sid), None)
            assert evt is not None, f"매물 {sid}의 3차 배치 PRICE_DROP 이벤트 누락"

            prev_card = cards_1.get(sid) or cards_2.get(sid)
            curr_card = cards_3.get(sid)
            p_prev = EncarCardParser.parse_card(prev_card)
            p_curr = EncarCardParser.parse_card(curr_card)

            assert int(p_prev["price_krw"]) == evt.previous_price_krw
            assert int(p_curr["price_krw"]) == evt.new_price_krw
            assert (evt.new_price_krw - evt.previous_price_krw) == evt.price_delta_krw


def test_existing_snapshots_row_by_row_preservation():
    """사전 백업 DB 대비 기존 스냅샷 246건의 PK 및 전수 필드 불변성 검증."""
    bk_engine = create_engine(f"sqlite:///{BACKUP_DB}")
    op_engine = create_engine(f"sqlite:///{OPERATIONAL_DB}")

    with Session(bk_engine) as bk_session, Session(op_engine) as op_session:
        bk_snapshots = bk_session.execute(select(ListingSnapshot)).scalars().all()
        assert len(bk_snapshots) == 246

        for bk_s in bk_snapshots:
            op_s = op_session.execute(
                select(ListingSnapshot).where(ListingSnapshot.snapshot_id == bk_s.snapshot_id)
            ).scalars().first()
            assert op_s is not None, f"스냅샷 {bk_s.snapshot_id} 유실"

            assert op_s.listing_id == bk_s.listing_id
            assert op_s.observed_at == bk_s.observed_at
            assert op_s.price_krw == bk_s.price_krw
            assert op_s.mileage_km == bk_s.mileage_km
            assert op_s.listing_status == bk_s.listing_status
            assert op_s.normalized_region_id == bk_s.normalized_region_id
            assert op_s.source_record_hash == bk_s.source_record_hash
            assert op_s.raw_specs == bk_s.raw_specs


def test_existing_listings_identity_preservation_and_state_transition():
    """기존 매물 238건의 고유 식별 정보 보존 및 5건의 정상 상태 전이 검증."""
    bk_engine = create_engine(f"sqlite:///{BACKUP_DB}")
    op_engine = create_engine(f"sqlite:///{OPERATIONAL_DB}")

    with Session(bk_engine) as bk_session, Session(op_engine) as op_session:
        bk_listings = bk_session.execute(select(Listing)).scalars().all()
        assert len(bk_listings) == 238

        price_changed_count = 0
        active_count = 0
        for bk_l in bk_listings:
            op_l = op_session.execute(
                select(Listing).where(Listing.listing_id == bk_l.listing_id)
            ).scalars().first()
            assert op_l is not None, f"매물 {bk_l.listing_id} 유실"

            assert op_l.source_platform == bk_l.source_platform
            assert op_l.source_listing_id == bk_l.source_listing_id
            assert op_l.first_observed_at == bk_l.first_observed_at
            assert op_l.raw_location == bk_l.raw_location

            if op_l.source_listing_id in TARGET_IDS:
                assert op_l.current_status == "PRICE_CHANGED"
                price_changed_count += 1
            else:
                assert op_l.current_status == bk_l.current_status
                assert op_l.consecutive_missing_count == bk_l.consecutive_missing_count
                active_count += 1

        assert price_changed_count == 5
        assert active_count == 233
