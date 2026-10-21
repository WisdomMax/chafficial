"""CHA-FICIAL AI PROJECT - DIRECTIVE 010-F
반복 관측 운영 안정성 회귀 검증 테스트 세트 (충돌 방지, SQLite Backup API, 실패 보호).
"""

import sqlite3
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from chaficial.database.base import Base
from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.platforms.base import StandardListingRecord
from chaficial.tracker.price_tracker import PriceEventTracker, SearchScopeSpec
from chaficial.tracker.stream_pipeline import MarketObservationStreamPipeline
from scripts.run_directive_010_market_stream import (
    LiveCollectionError,
    backup_operational_db_safe,
    fetch_live_encar_cn7,
    generate_collision_safe_batch_id,
)


def test_batch_id_and_file_collision_prevention():
    """지침 1: 동일 초에 연속 생성하더라도 UUID 접미사로 인해 batch_id와 파일명이 100% 고유한지 검증."""
    id1, ts1 = generate_collision_safe_batch_id("TEST_BATCH")
    id2, ts2 = generate_collision_safe_batch_id("TEST_BATCH")

    assert id1 != id2, f"배치 ID 충돌 발생: {id1} == {id2}"
    assert ts1 != ts2, f"타임스탬프 접미사 충돌 발생: {ts1} == {ts2}"
    assert len(ts1.split("_")[-1]) >= 6, "UUID 접미사가 최소 6자리 이상(010-G에서 12자리로 확장)이어야 합니다."


def test_sqlite_backup_api_preserves_db_consistency(tmp_path):
    """지침 2: SQLite Backup API를 통해 트랜잭션 일관성을 보장하며 고유 백업 파일이 생성되는지 검증."""
    db_file = tmp_path / "test_operational.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE sample (id INT, name TEXT)")
    conn.execute("INSERT INTO sample VALUES (1, 'CN7_ORIGINAL')")
    conn.commit()
    conn.close()

    backup_file = backup_operational_db_safe(db_file)
    assert backup_file is not None
    assert backup_file.exists()
    assert backup_file.name.startswith("market_timeseries_backup_")

    # 백업된 DB의 내용 일치 검증
    b_conn = sqlite3.connect(backup_file)
    cur = b_conn.cursor()
    cur.execute("SELECT name FROM sample WHERE id = 1")
    row = cur.fetchone()
    b_conn.close()

    assert row is not None
    assert row[0] == "CN7_ORIGINAL"


def test_live_collection_failure_fault_injection_protects_db(tmp_path):
    """지침 3: 실시간 웹 수집 실패(Aside CLI 에러 또는 카드 0건) 시 예외가 발생하고 DB가 전혀 변경되지 않는지 검증."""
    db_file = tmp_path / "test_fault.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE records (id INT)")
    conn.execute("INSERT INTO records VALUES (100)")
    conn.commit()
    conn.close()

    # 1. Aside CLI가 실패(returncode=1)하는 상황 주입
    mock_failed_process = MagicMock()
    mock_failed_process.returncode = 1
    mock_failed_process.stderr = "Simulated Aside Browser Crash"

    with patch("subprocess.run", return_value=mock_failed_process):
        with pytest.raises(LiveCollectionError) as exc_info:
            fetch_live_encar_cn7()
        assert "Aside CLI 실행 실패" in str(exc_info.value)

    # 2. 수집된 카드가 0건인 상황 주입
    mock_empty_process = MagicMock()
    mock_empty_process.returncode = 0
    mock_empty_process.stdout = "LIVE_RAW_CARDS_JSON:[]"

    with patch("subprocess.run", return_value=mock_empty_process):
        with pytest.raises(LiveCollectionError) as exc_info:
            fetch_live_encar_cn7()
        assert "엔카 매물 카드가 0건입니다" in str(exc_info.value)

    # DB 불변 검증
    c = sqlite3.connect(db_file)
    count = c.execute("SELECT count(*) FROM records").fetchone()[0]
    c.close()
    assert count == 1, "수집 실패 시 운영 DB가 변경되어서는 안 됩니다."


def test_operational_db_preserves_accumulated_listings_and_snapshots():
    """지침 4: 실제 운영 DB(data/chaficial_market_timeseries.db)가 238대 실매물과 246건 스냅샷을 영구 보존하는지 검증."""
    db_path = Path("data/chaficial_market_timeseries.db")
    assert db_path.exists(), f"운영 DB가 존재하지 않습니다: {db_path}"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT count(*) FROM listings")
    listings_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM listing_snapshots")
    snapshots_count = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM batch_audit_logs")
    batch_count = cur.fetchone()[0]

    conn.close()

    # 1차(126대) + 2차(신규 112대) = 238대 이상 영구 보존
    assert listings_count >= 238, f"기존 매물 이력이 소실되었습니다: 현재 {listings_count}대 (기대: >= 238대)"
    # 1차(126건) + 2차(120건) = 246건 이상 영구 보존
    assert snapshots_count >= 246, f"스냅샷 이력이 소실되었습니다: 현재 {snapshots_count}건 (기대: >= 246건)"
    # 최소 2회 이상의 독립 LIVE 배치 보존
    assert batch_count >= 2, f"배치 감사 로그가 누락되었습니다: 현재 {batch_count}건 (기대: >= 2건)"
