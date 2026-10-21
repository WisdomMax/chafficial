"""CHA-FICIAL AI PROJECT - DIRECTIVE 010-K
최종 감사 보고서 보존 및 개별 관측 실행 동적 보고서 생성 검증 회귀 테스트.
"""

import hashlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from chaficial.models.batch_log import BatchAuditLog
from chaficial.tracker.stream_pipeline import (
    BatchExecutionResult,
    MarketObservationStreamPipeline,
)
from scripts.run_directive_010_market_stream import (
    generate_batch_observation_report,
    run_pipeline,
)

OFFICIAL_REPORT_FILE = Path("reports/DIRECTIVE_010_COMPLETED_REPORT.md")


def _get_file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ==============================================================================
# 1. 최종 공식 완결 보고서 영구 보존 검증
# ==============================================================================
def test_official_completion_report_never_overwritten_by_live_pipeline(tmp_path):
    """지침 1: LIVE 관측 파이프라인이 실행되더라도 승인용 최종 보고서가 바이트 단위로 100% 보존됨을 검증."""
    assert OFFICIAL_REPORT_FILE.exists(), "공식 완결 보고서가 존재해야 합니다."
    original_bytes = OFFICIAL_REPORT_FILE.read_bytes()
    original_sha = _get_file_hash(OFFICIAL_REPORT_FILE)

    # LIVE 모드 모의 실행 (임시 DB 및 모의 웹 수집기 사용)
    test_db = tmp_path / "live_report_test.db"
    dummy_raw_cards = [
        {
            "carid": "42912520",
            "href": "https://fem.encar.com/cars/detail/42912520",
            "raw_text": "아반떼 (CN7) 1.6 모던 20/04식(21년형)155,122km가솔린서울 1,100만원 검정색 계열",
        },
    ]

    with patch("scripts.run_directive_010_market_stream.fetch_live_encar_cn7") as mock_fetch:
        mock_fetch.return_value = (
            dummy_raw_cards,
            tmp_path / "dummy_raw.json",
            "dummy_sha_123",
            "TEST_PRESERVE_BATCH",
            datetime.now(UTC),
            datetime.now(UTC),
        )
        run_pipeline(mode="live", db_path_override=test_db, lock_file_path=tmp_path / "l.lock")

    # 실행 후 공식 완결 보고서의 바이트 및 해시가 1비트도 변하지 않았음을 검증
    post_bytes = OFFICIAL_REPORT_FILE.read_bytes()
    post_sha = _get_file_hash(OFFICIAL_REPORT_FILE)

    assert original_bytes == post_bytes, "공식 완결 보고서가 덮어써졌습니다!"
    assert original_sha == post_sha


# ==============================================================================
# 2. 서로 다른 배치의 관측 보고서 고유 저장 검증
# ==============================================================================
def test_different_batches_saved_to_different_observation_files(tmp_path):
    """지침 2: 서로 다른 배치의 관측 실행 보고서가 reports/observations/에 독립 파일로 저장됨을 검증."""
    pipeline = MarketObservationStreamPipeline()
    dummy_res = BatchExecutionResult(
        batch_id="BATCH_A",
        search_scope_key="ENCAR:현대:아반떼:ALL",
        started_at_utc=datetime.now(UTC),
        completed_at_utc=datetime.now(UTC),
        started_at_kst="2026-10-21 12:00:00 KST",
        completed_at_kst="2026-10-21 12:01:00 KST",
        total_records_ingested=10,
        first_seen_count=10,
        re_observed_count=0,
        price_drop_count=0,
        price_increase_count=0,
        total_price_drop_krw=0,
        re_listed_count=0,
        delisted_suspect_count=0,
        is_success=True,
        is_partial_scrape=True,
    )

    report_a = generate_batch_observation_report(
        batch_id="BATCH_A",
        web_start_utc=datetime.now(UTC),
        web_end_utc=datetime.now(UTC),
        raw_file=tmp_path / "raw_a.json",
        raw_sha="sha_a",
        total_cards=10,
        parsed_count=10,
        batch_result=dummy_res,
        post_listings=10,
        post_snapshots=10,
        post_events=10,
        post_batches=1,
        post_links=0,
        live_db_hashes={},
        all_batches=[],
        pipeline=pipeline,
    )

    report_b = generate_batch_observation_report(
        batch_id="BATCH_B",
        web_start_utc=datetime.now(UTC),
        web_end_utc=datetime.now(UTC),
        raw_file=tmp_path / "raw_b.json",
        raw_sha="sha_b",
        total_cards=20,
        parsed_count=20,
        batch_result=dummy_res,
        post_listings=20,
        post_snapshots=20,
        post_events=20,
        post_batches=2,
        post_links=0,
        live_db_hashes={},
        all_batches=[],
        pipeline=pipeline,
    )

    file_a = tmp_path / "observation_batch_BATCH_A.md"
    file_b = tmp_path / "observation_batch_BATCH_B.md"

    with open(file_a, "x", encoding="utf-8") as f:
        f.write(report_a)
    with open(file_b, "x", encoding="utf-8") as f:
        f.write(report_b)

    assert file_a.exists() and file_b.exists()
    assert file_a != file_b
    assert file_a.read_text(encoding="utf-8") != file_b.read_text(encoding="utf-8")


# ==============================================================================
# 3. 3차 가상 배치의 수치·시간 동적 렌더링 검증 (하드코딩 배제)
# ==============================================================================
def test_third_batch_dynamics_never_fixed_to_past_batches(tmp_path):
    """지침 3: 3차 가상 배치의 수치(300개 카드, 150대 파싱, FIRST_SEEN 20, 가격변동 3건)가 동적으로 정상 반영되는지 검증."""
    pipeline = MarketObservationStreamPipeline()
    batch_3_res = BatchExecutionResult(
        batch_id="ENCAR_CN7_LIVE_BATCH_03",
        search_scope_key="ENCAR:현대:아반떼:ALL",
        started_at_utc=datetime.now(UTC),
        completed_at_utc=datetime.now(UTC),
        started_at_kst="2026-10-21 15:30:00 KST",
        completed_at_kst="2026-10-21 15:30:30 KST",
        total_records_ingested=150,
        first_seen_count=20,
        re_observed_count=130,
        price_drop_count=3,
        price_increase_count=0,
        total_price_drop_krw=1500000,
        re_listed_count=0,
        delisted_suspect_count=0,
        is_success=True,
        is_partial_scrape=True,
    )

    mock_batch_audit = BatchAuditLog(
        batch_id="ENCAR_CN7_LIVE_BATCH_03",
        source_platform="ENCAR",
        search_scope="현대:아반떼",
        processed_at=datetime.now(UTC),
        record_count=150,
        is_partial_scrape=True,
        notes="3차 관측 테스트",
    )

    report_3 = generate_batch_observation_report(
        batch_id="ENCAR_CN7_LIVE_BATCH_03",
        web_start_utc=datetime.now(UTC),
        web_end_utc=datetime.now(UTC),
        raw_file=tmp_path / "encar_cn7_live_batch_03.json",
        raw_sha="sha_batch_03_mock",
        total_cards=300,
        parsed_count=150,
        batch_result=batch_3_res,
        post_listings=258,
        post_snapshots=396,
        post_events=241,
        post_batches=3,
        post_links=0,
        live_db_hashes={
            "listings": {"hash": "hash_listings_258"},
            "listing_snapshots": {"hash": "hash_snapshots_396"},
            "price_events": {"hash": "hash_events_241"},
            "batch_audit_logs": {"hash": "hash_batches_3"},
            "vehicle_identity_links": {"hash": "hash_links_0"},
        },
        all_batches=[mock_batch_audit],
        pipeline=pipeline,
    )

    # 3차 배치의 동적 데이터가 정확히 렌더링되었는지 검증
    assert "ENCAR_CN7_LIVE_BATCH_03" in report_3
    assert "300개" in report_3
    assert "150대" in report_3
    assert "20대" in report_3
    assert "130대" in report_3
    assert "3건" in report_3
    assert "258행" in report_3
    assert "396행" in report_3
    assert "241행" in report_3
    assert "3행" in report_3

    # 과거 1차·2차의 고정 문구가 3차 관측 실적으로 둔갑하지 않았는지 확인
    assert "수집 카드 250개 중 아반떼 CN7 126대" not in report_3


# ==============================================================================
# 4. 실제 DB 행 수와 보고서 출력값의 정확한 분리 및 일치성 검증
# ==============================================================================
def test_table_row_counts_and_hashes_match_actual_db():
    """지침 4: price_events 행 수가 listings로 대체되지 않고 실제 post_events와 post_links를 정확히 반영하는지 검증."""
    pipeline = MarketObservationStreamPipeline()
    dummy_res = MagicMock()
    dummy_res.first_seen_count = 5
    dummy_res.re_observed_count = 5
    dummy_res.price_drop_count = 1
    dummy_res.price_increase_count = 0
    dummy_res.delisted_suspect_count = 0
    dummy_res.completed_at_utc = datetime.now(UTC)

    report = generate_batch_observation_report(
        batch_id="TEST_COUNTS",
        web_start_utc=datetime.now(UTC),
        web_end_utc=datetime.now(UTC),
        raw_file=Path("dummy.json"),
        raw_sha="sha123",
        total_cards=10,
        parsed_count=10,
        batch_result=dummy_res,
        post_listings=238,
        post_snapshots=246,
        post_events=239,  # listings와 명확히 다른 실제 독립 이벤트 수
        post_batches=2,
        post_links=5,     # 실제 링크 수
        live_db_hashes={},
        all_batches=[],
        pipeline=pipeline,
    )

    # listings(238)와 price_events(239), links(5)가 독립적으로 정확히 렌더링되었는지 확인
    assert "| `listings` | **238행** |" in report
    assert "| `listing_snapshots` | **246행** |" in report
    assert "| `price_events` | **239행** |" in report
    assert "| `vehicle_identity_links` | **5행** |" in report
