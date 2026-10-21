"""CHA-FICIAL AI PROJECT - DIRECTIVE 010-J
자동 생성 완결 보고서의 정합성, 과장 표현 배제 및 감사 지침 준수 회귀 검증 테스트.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chaficial.tracker.stream_pipeline import MarketObservationStreamPipeline
from scripts.run_directive_010_market_stream import generate_directive_010_report


def test_generated_report_consistency_and_no_hyperbole():
    """지침: 자동 보고서 생성 결과가 010-J 정합성을 준수하고 금지된 과장 표현이 배제되었는지 검증."""
    pipeline = MarketObservationStreamPipeline()
    dummy_hashes = {
        "listings": {"count": 238, "hash": "dummy_listings_hash_123"},
        "listing_snapshots": {"count": 246, "hash": "dummy_snapshots_hash_456"},
        "price_events": {"count": 238, "hash": "dummy_events_hash_789"},
        "batch_audit_logs": {"count": 2, "hash": "dummy_batches_hash_abc"},
        "vehicle_identity_links": {"count": 0, "hash": "dummy_links_hash_def"},
    }

    report_md = generate_directive_010_report(
        web_start_utc=datetime.now(UTC),
        batch_id="ENCAR_CN7_LIVE_TEST",
        raw_file_name="encar_cn7_live_test.json",
        post_listings=238,
        post_snapshots=246,
        post_batches=2,
        live_db_hashes=dummy_hashes,
        pipeline=pipeline,
    )

    # 1. 보고서 제목이 DIRECTIVE 010-J인지 검증
    assert "## DIRECTIVE 010-J 완결 보고서" in report_md

    # 2. 금지된 과장 표현이 전혀 없음을 엄격히 검증
    forbidden_hyperboles = [
        "수학적으로 완벽 차단",
        "수학적으로 완벽",
        "수학적으로 충돌 불가능",
        "오염 가능성을 100% 원천 차단",
        "100% 원천 차단",
        "완벽 보장",
    ]
    for phrase in forbidden_hyperboles:
        assert phrase not in report_md, f"금지된 과장 표현 발견: '{phrase}'"

    # 3. 010-J 핵심 감사 항목이 정상 명시되었는지 검증
    assert "test_db_partial_write_rollback_preserves_hashes" in report_md
    assert "test_past_data_preservation_and_real_mutation_test" in report_md
    assert "test_backup_exclusive_reservation_and_multiprocess_lock_contention" in report_md
    assert "238" in report_md
    assert "246" in report_md
    assert "dummy_listings_hash_123" in report_md
