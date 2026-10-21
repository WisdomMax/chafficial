"""CHA-FICIAL AI PROJECT - DIRECTIVE 011
감사 보고서 안전 복구(Reconstruction) 및 시계열 운영 무결성 검증 테스트 세트.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.snapshot import ListingSnapshot
from chaficial.tracker.price_tracker import compute_db_logical_hashes
from scripts.reconstruct_observation_report import reconstruct_batch_report

OPERATIONAL_DB_PATH = Path("data/chaficial_market_timeseries.db")
BATCH_1_ID = "ENCAR_CN7_LIVE_20261021_01"
BATCH_2_ID = "ENCAR_CN7_LIVE_20261021_120825"


def test_reconstruct_report_from_existing_db_batch(tmp_path):
    """지침: 이미 DB에 커밋된 1차 배치로부터 보고서를 안전하게 역조회 재구성할 수 있는지 검증."""
    assert OPERATIONAL_DB_PATH.exists()

    out_file = reconstruct_batch_report(
        batch_id=BATCH_1_ID,
        db_path=OPERATIONAL_DB_PATH,
        output_dir=tmp_path,
        overwrite=True,
    )

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert BATCH_1_ID in content
    assert "126대" in content
    assert "238행" in content
    assert "246행" in content


def test_reconstruct_report_rejects_non_existent_batch(tmp_path):
    """지침: DB에 존재하지 않는 가짜 배치 ID로 복구 시도 시 ValueError 발생 검증."""
    assert OPERATIONAL_DB_PATH.exists()

    with pytest.raises(ValueError, match="감사 로그가 존재하지 않습니다"):
        reconstruct_batch_report(
            batch_id="NON_EXISTENT_BATCH_ID_9999",
            db_path=OPERATIONAL_DB_PATH,
            output_dir=tmp_path,
        )


def test_operational_db_invariants_hold_in_directive_011():
    """지침: DIRECTIVE 011 진입 시점에도 운영 DB의 238대 실매물, 246건 스냅샷이 불변으로 보존되는지 검증."""
    assert OPERATIONAL_DB_PATH.exists()

    engine = create_engine(f"sqlite:///{OPERATIONAL_DB_PATH}")
    with sessionmaker(bind=engine)() as s:
        listing_count = s.execute(select(func.count(Listing.listing_id))).scalar()
        snapshot_count = s.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
        batch_count = s.execute(select(func.count(BatchAuditLog.batch_id))).scalar()

        assert listing_count == 238
        assert snapshot_count == 246
        assert batch_count == 2

        hashes = compute_db_logical_hashes(s)
        assert hashes["listings"]["hash"] == "5183ee9e4666a12c3b721ef9499dd5330fb72014e6bdbd03fc6b952611413d0a"
        assert hashes["listing_snapshots"]["hash"] == "8bf7b94983d7c7d07f7c1b9817cf2a2e28e4150776f4f4996a24f4268dae2bca"
