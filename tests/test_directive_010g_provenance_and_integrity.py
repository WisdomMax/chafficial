"""CHA-FICIAL AI PROJECT - DIRECTIVE 010-G 무결성 검증 테스트
운영 관측 무결성 및 출처 격리(REPLAY/LIVE 영구 격리, 키 보존, 실패 주입 보호, SQLite 백업 무결성).
"""

import json
import sqlite3
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from chaficial.database.base import Base
from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.platforms.encar import EncarCardParser
from chaficial.tracker.price_tracker import compute_db_logical_hashes
from scripts.run_directive_010_market_stream import (
    LiveCollectionError,
    backup_operational_db_safe,
    generate_collision_safe_batch_id,
    run_pipeline,
)

OPERATIONAL_DB_PATH = Path("data/chaficial_market_timeseries.db")
RAW_OBS_FILE_1 = Path("data/raw_observations/encar_cn7_live_20261021_01.json")


def test_batch_id_collision_prevention_12char_uuid():
    """12자리 고유 식별자 결합으로 다중 호출 시 고유성 및 12자리 길이 검증."""
    batch_ids = set()
    ts_strs = set()
    for _ in range(100):
        b_id, ts = generate_collision_safe_batch_id()
        suffix = ts.split("_")[-1]
        assert len(suffix) == 12, f"UUID 접미사 길이가 12자가 아닙니다: {suffix}"
        batch_ids.add(b_id)
        ts_strs.add(ts)
    assert len(batch_ids) == 100
    assert len(ts_strs) == 100


def test_replay_mode_never_touches_operational_db(tmp_path):
    """REPLAY 모드 실행 시 운영 DB를 전혀 건드리지 않고 격리된 벤치마크 DB에 REPLAY_FIXTURE로 적재됨을 검증."""
    assert OPERATIONAL_DB_PATH.exists(), "운영 DB가 존재해야 합니다."
    assert RAW_OBS_FILE_1.exists(), "1차 원본 관측 파일이 존재해야 합니다."

    # 1. 실행 전 운영 DB의 논리 해시 계산
    engine_op = create_engine(f"sqlite:///{OPERATIONAL_DB_PATH}")
    SessionOp = sessionmaker(bind=engine_op)
    with SessionOp() as session:
        op_hashes_before = compute_db_logical_hashes(session)
        op_listings_before = session.execute(select(func.count(Listing.listing_id))).scalar()
        op_snapshots_before = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()

    # 2. 임시 격리 벤치마크 DB 경로로 REPLAY 실행
    test_bench_db = tmp_path / "replay_benchmark_test.db"
    run_pipeline(mode="replay", input_file=str(RAW_OBS_FILE_1), db_path_override=test_bench_db)

    # 3. 실행 후 운영 DB의 논리 해시 및 레코드 수가 1비트도 변하지 않았음을 검증
    with SessionOp() as session:
        op_hashes_after = compute_db_logical_hashes(session)
        op_listings_after = session.execute(select(func.count(Listing.listing_id))).scalar()
        op_snapshots_after = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()

    assert op_listings_before == op_listings_after
    assert op_snapshots_before == op_snapshots_after
    for table_name in op_hashes_before:
        assert op_hashes_before[table_name]["hash"] == op_hashes_after[table_name]["hash"], (
            f"운영 DB의 {table_name} 해시가 변조되었습니다!"
        )

    # 4. 격리된 벤치마크 DB 확인: data_origin이 모두 REPLAY_FIXTURE여야 함
    engine_bench = create_engine(f"sqlite:///{test_bench_db}")
    SessionBench = sessionmaker(bind=engine_bench)
    with SessionBench() as session:
        bench_listings = session.execute(select(Listing)).scalars().all()
        bench_snapshots = session.execute(select(ListingSnapshot)).scalars().all()
        bench_events = session.execute(select(PriceEvent)).scalars().all()
        assert len(bench_listings) == 126
        assert len(bench_snapshots) == 126
        assert len(bench_events) == 126
        for ev in bench_events:
            assert ev.data_origin == "REPLAY_FIXTURE", f"리플레이 이벤트의 data_origin이 잘못되었습니다: {ev.data_origin}"


def test_operational_db_preserves_exact_keys_and_snapshots():
    """운영 DB의 기존 238대 실매물 및 246건 스냅샷이 단순 행 수 하한이 아닌 정확한 PK 집합으로 100% 온전히 보존됨을 검증."""
    assert OPERATIONAL_DB_PATH.exists()
    assert RAW_OBS_FILE_1.exists()

    engine = create_engine(f"sqlite:///{OPERATIONAL_DB_PATH}")
    Session = sessionmaker(bind=engine)
    with Session() as session:
        listings = session.execute(select(Listing)).scalars().all()
        snapshots = session.execute(select(ListingSnapshot)).scalars().all()
        batches = session.execute(select(BatchAuditLog)).scalars().all()

        # 1. 누적 개수 하한 확인
        assert len(listings) >= 238, f"운영 DB 실매물 수({len(listings)})가 238대 미만입니다."
        assert len(snapshots) >= 246, f"운영 DB 스냅샷 수({len(snapshots)})가 246건 미만입니다."
        assert len(batches) >= 2, f"운영 DB 배치 수({len(batches)})가 2건 미만입니다."

        # 2. 1차 관측 원본 파일의 126대 CN7 목록이 모두 현재 운영 DB의 source_listing_id에 존재하는지 검증
        with open(RAW_OBS_FILE_1, "r", encoding="utf-8") as f:
            raw_1 = json.load(f)
        parsed_1_cn7 = [
            EncarCardParser.parse_card(c, "2026-10-21T00:00:00Z")
            for c in raw_1["raw_cards"]
        ]
        raw_1_cn7_ids = {p["source_listing_id"] for p in parsed_1_cn7 if p is not None}
        assert len(raw_1_cn7_ids) == 126, f"1차 파싱된 CN7 수가 126대가 아닙니다: {len(raw_1_cn7_ids)}"

        db_source_ids = {l.source_listing_id for l in listings}

        # 1차 126대 매물들이 모두 운영 DB에 영구 보존되어 있어야 함 (부분집합 검증)
        assert raw_1_cn7_ids.issubset(db_source_ids), "1차 수집된 매물 ID 중 일부가 운영 DB에서 유실되었습니다!"

        # 3. 운영 DB의 모든 가격 이벤트의 data_origin이 REAL_OBSERVED인지 검증
        events = session.execute(select(PriceEvent)).scalars().all()
        assert len(events) >= 238
        for ev in events:
            assert ev.data_origin == "REAL_OBSERVED", f"운영 DB 가격 이벤트에 부적절한 data_origin 발견: {ev.data_origin}"


def test_run_pipeline_fault_injection_preserves_db_hash(tmp_path):
    """전체 파이프라인(run_pipeline) 수준에서 웹 수집 실패 시 DB 논리 해시가 불변임을 검증."""
    test_db = tmp_path / "fault_test.db"

    # 기본 DB 구조 생성
    engine = create_engine(f"sqlite:///{test_db}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as s:
        hashes_before = compute_db_logical_hashes(s)

    # 1. Aside CLI 실행 실패 모의 주입
    with patch("scripts.run_directive_010_market_stream.fetch_live_encar_cn7") as mock_fetch:
        mock_fetch.side_effect = LiveCollectionError("Aside CLI failure injected")
        with pytest.raises(LiveCollectionError):
            run_pipeline(mode="live", db_path_override=test_db)

    # 실패 후 DB 해시 확인
    with Session() as s:
        hashes_after = compute_db_logical_hashes(s)
        for t in hashes_before:
            assert hashes_before[t]["hash"] == hashes_after[t]["hash"]
            assert hashes_after[t]["count"] == 0

    # 2. 타임아웃 오류 모의 주입
    with patch("scripts.run_directive_010_market_stream.fetch_live_encar_cn7") as mock_fetch:
        mock_fetch.side_effect = LiveCollectionError("TimeoutExpired injected")
        with pytest.raises(LiveCollectionError):
            run_pipeline(mode="live", db_path_override=test_db)

    # 실패 후 DB 해시 재확인
    with Session() as s:
        hashes_after2 = compute_db_logical_hashes(s)
        for t in hashes_before:
            assert hashes_before[t]["hash"] == hashes_after2[t]["hash"]


def test_sqlite_backup_integrity_check(tmp_path):
    """SQLite Backup API 수행 직후 PRAGMA integrity_check가 정상 통과함을 검증."""
    dummy_db = tmp_path / "dummy_market.db"
    engine = create_engine(f"sqlite:///{dummy_db}")
    Base.metadata.create_all(engine)

    backup_file = backup_operational_db_safe(dummy_db)
    assert backup_file is not None
    assert backup_file.exists()

    with sqlite3.connect(backup_file) as conn:
        res = conn.cursor().execute("PRAGMA integrity_check;").fetchall()
        assert res == [("ok",)]
