"""CHA-FICIAL AI PROJECT - DIRECTIVE 010-J
자동 생성 완결 보고서의 정합성, 과장 표현 배제 및 감사 지침 준수 회귀 검증 테스트.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import MagicMock
from chaficial.tracker.stream_pipeline import MarketObservationStreamPipeline
from scripts.run_directive_010_market_stream import generate_batch_observation_report


def test_generated_report_consistency_and_no_hyperbole():
    """지침: 자동 보고서 생성 결과가 010-J/K 정합성을 준수하고 금지된 과장 표현이 배제되었는지 검증."""
    pipeline = MarketObservationStreamPipeline()
    dummy_hashes = {
        "listings": {"count": 238, "hash": "dummy_listings_hash_123"},
        "listing_snapshots": {"count": 246, "hash": "dummy_snapshots_hash_456"},
        "price_events": {"count": 238, "hash": "dummy_events_hash_789"},
        "batch_audit_logs": {"count": 2, "hash": "dummy_batches_hash_abc"},
        "vehicle_identity_links": {"count": 0, "hash": "dummy_links_hash_def"},
    }
    dummy_res = MagicMock()
    dummy_res.first_seen_count = 10
    dummy_res.re_observed_count = 0
    dummy_res.price_drop_count = 0
    dummy_res.price_increase_count = 0
    dummy_res.delisted_suspect_count = 0
    dummy_res.completed_at_utc = datetime.now(UTC)

    report_md = generate_batch_observation_report(
        batch_id="ENCAR_CN7_LIVE_TEST",
        web_start_utc=datetime.now(UTC),
        web_end_utc=datetime.now(UTC),
        raw_file=Path("encar_cn7_live_test.json"),
        raw_sha="dummy_sha_123",
        total_cards=200,
        parsed_count=100,
        batch_result=dummy_res,
        post_listings=238,
        post_snapshots=246,
        post_events=238,
        post_batches=2,
        post_links=0,
        live_db_hashes=dummy_hashes,
        all_batches=[],
        pipeline=pipeline,
    )

    # 1. 보고서 제목이 관측 실행 보고서인지 검증
    assert "## 시장 관측 실행 동적 보고서" in report_md

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

    # 3. 실측 수치 및 해시 정상 반영 검증
    assert "ENCAR_CN7_LIVE_TEST" in report_md
    assert "200개" in report_md
    assert "100대" in report_md
    assert "238행" in report_md
    assert "246행" in report_md
    assert "dummy_listings_hash_123" in report_md
