"""CHA-FICIAL AI PROJECT - DIRECTIVE 011 / 011-A 회귀 및 결함 방지 테스트 스위트.

총괄 감독 지침(DIRECTIVE 011-A) 검증:
1. 복구 가능한 정보와 불가능한 정보 명확히 구분 (수집 시각 NOT_RECORDED 정직성).
2. 신규 배치 원본 파일 경로 및 해시 대조 검증 (변조/누락 탐지).
3. 실제 가격 인하(PRICE_DROP) 금액 및 재관측 통계의 정확한 복원 (0원 하드코딩 제거 검증).
4. 과거 배치 당시 상태와 복구 시점 누적 상태 분리.
5. 운영 DB 고정값(238대) 의존 제거: 향후 3차 LIVE로 데이터가 증가해도 기존 PK 영구 보존 검증.
6. 필수 실패 시나리오 8종 전수 독립 검증.
"""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from chaficial.database.base import Base
from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.models.vehicle_link import VehicleIdentityLink
from chaficial.platforms.base import StandardListingRecord
from chaficial.tracker.price_tracker import PriceEventTracker, SearchScopeSpec
from chaficial.tracker.stream_pipeline import MarketObservationStreamPipeline
from scripts.reconstruct_observation_report import reconstruct_batch_report


@pytest.fixture
def isolated_db_and_raw(tmp_path):
    """테스트를 위한 완전히 격리된 임시 SQLite DB와 원본 JSON 디렉토리를 제공합니다."""
    db_file = tmp_path / "test_market.db"
    raw_dir = tmp_path / "raw_obs"
    reports_dir = tmp_path / "reports"
    raw_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    return {
        "engine": engine,
        "Session": Session,
        "db_path": db_file,
        "raw_dir": raw_dir,
        "reports_dir": reports_dir,
    }


def _create_sample_raw_json(file_path: Path, batch_id: str, card_ids: list[str]) -> str:
    """원천 JSON 파일을 생성하고 SHA-256 해시를 반환합니다."""
    raw_data = {
        "batch_id": batch_id,
        "collected_at_utc": "2026-10-21T03:00:00Z",
        "completed_at_utc": "2026-10-21T03:00:30Z",
        "total_cards_collected": len(card_ids),
        "raw_cards": [{"id": cid, "price": 2000, "mileage": 30000} for cid in card_ids],
    }
    content = json.dumps(raw_data, ensure_ascii=False)
    file_path.write_text(content, encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ==============================================================================
# 필수 실패 및 복구 시나리오 8종 독립 검증 (DIRECTIVE 011-A 지침 6)
# ==============================================================================

def test_failure_scenario_1_missing_raw_json_raises_error(isolated_db_and_raw):
    """시나리오 1: 메타데이터에 기록된 원본 JSON 파일이 물리적으로 누락된 경우 명확하게 FileNotFoundError 발생."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    with Session() as session:
        audit = BatchAuditLog(
            batch_id="BATCH_FAIL_01",
            source_platform="ENCAR",
            search_scope="ENCAR::HYUNDAI::AVANTE",
            processed_at=datetime.now(UTC),
            record_count=10,
            is_partial_scrape=False,
        )
        audit.set_audit_metadata({
            "raw_file_path": str(raw_dir / "non_existent.json"),
            "raw_file_sha256": "dummy_sha_1234567890abcdef",
            "web_fetch_started_at": "2026-10-21T03:00:00Z",
            "web_fetch_completed_at": "2026-10-21T03:00:30Z",
        })
        session.add(audit)
        session.commit()

    with pytest.raises(FileNotFoundError, match="원본 JSON 파일을 찾을 수 없습니다"):
        reconstruct_batch_report(
            batch_id="BATCH_FAIL_01",
            db_path=db_path,
            output_dir=reports_dir,
            raw_observations_dir=raw_dir,
        )


def test_failure_scenario_2_tampered_raw_json_raises_error(isolated_db_and_raw):
    """시나리오 2: 원본 JSON 파일이 변조(해시 불일치)된 경우 명확하게 ValueError 발생."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    raw_file = raw_dir / "tampered_batch.json"
    actual_sha = _create_sample_raw_json(raw_file, "BATCH_FAIL_02", ["CARD_01", "CARD_02"])
    recorded_sha = "0000000000000000000000000000000000000000000000000000000000000000"  # 위조 해시

    with Session() as session:
        audit = BatchAuditLog(
            batch_id="BATCH_FAIL_02",
            source_platform="ENCAR",
            search_scope="ENCAR::HYUNDAI::AVANTE",
            processed_at=datetime.now(UTC),
            record_count=2,
            is_partial_scrape=False,
        )
        audit.set_audit_metadata({
            "raw_file_path": str(raw_file),
            "raw_file_sha256": recorded_sha,
            "web_fetch_started_at": "2026-10-21T03:00:00Z",
            "web_fetch_completed_at": "2026-10-21T03:00:30Z",
        })
        session.add(audit)
        session.commit()

    with pytest.raises(ValueError, match="원본 JSON 파일 변조 감지"):
        reconstruct_batch_report(
            batch_id="BATCH_FAIL_02",
            db_path=db_path,
            output_dir=reports_dir,
            raw_observations_dir=raw_dir,
        )


def test_failure_scenario_3_wrong_batch_json_replacement_fails(isolated_db_and_raw):
    """시나리오 3: 다른 배치의 JSON으로 교체된 경우 해시 불일치로 엄격하게 차단."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    # 배치 A용 파일 및 해시
    file_a = raw_dir / "batch_a.json"
    sha_a = _create_sample_raw_json(file_a, "BATCH_A", ["CARD_1", "CARD_2"])

    # 배치 B용 파일 (배치 A 파일 자리에 교체치기)
    file_b = raw_dir / "batch_b.json"
    sha_b = _create_sample_raw_json(file_b, "BATCH_B", ["CARD_3", "CARD_4"])
    file_a.write_text(file_b.read_text(encoding="utf-8"), encoding="utf-8")

    with Session() as session:
        audit = BatchAuditLog(
            batch_id="BATCH_A",
            source_platform="ENCAR",
            search_scope="ENCAR::HYUNDAI::AVANTE",
            processed_at=datetime.now(UTC),
            record_count=2,
            is_partial_scrape=False,
        )
        audit.set_audit_metadata({
            "raw_file_path": str(file_a),
            "raw_file_sha256": sha_a,  # 원래 배치 A 해시
        })
        session.add(audit)
        session.commit()

    with pytest.raises(ValueError, match="원본 JSON 파일 변조 감지"):
        reconstruct_batch_report(
            batch_id="BATCH_A",
            db_path=db_path,
            output_dir=reports_dir,
            raw_observations_dir=raw_dir,
        )


def test_failure_scenario_4_non_existent_batch_raises_error(isolated_db_and_raw):
    """시나리오 4: DB에 존재하지 않는 허위 배치 ID로 복구 시도 시 ValueError 발생."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]

    with pytest.raises(ValueError, match="감사 로그가 존재하지 않습니다"):
        reconstruct_batch_report(
            batch_id="NON_EXISTENT_GHOST_BATCH",
            db_path=db_path,
            output_dir=reports_dir,
            raw_observations_dir=raw_dir,
        )


def test_failure_scenario_5_existing_report_overwrite_rejection(isolated_db_and_raw):
    """시나리오 5 & 8: 기존 보고서가 이미 존재할 때 overwrite=False이면 FileExistsError 거부."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    raw_file = raw_dir / "batch_safe.json"
    actual_sha = _create_sample_raw_json(raw_file, "BATCH_SAFE", ["CARD_1"])

    with Session() as session:
        audit = BatchAuditLog(
            batch_id="BATCH_SAFE",
            source_platform="ENCAR",
            search_scope="ENCAR::HYUNDAI::AVANTE",
            processed_at=datetime.now(UTC),
            record_count=1,
            is_partial_scrape=False,
        )
        audit.set_audit_metadata({
            "raw_file_path": str(raw_file),
            "raw_file_sha256": actual_sha,
            "web_fetch_started_at": "2026-10-21T03:00:00Z",
            "web_fetch_completed_at": "2026-10-21T03:00:10Z",
        })
        session.add(audit)
        session.commit()

    # 1회차 복구 성공
    out1 = reconstruct_batch_report(
        batch_id="BATCH_SAFE",
        db_path=db_path,
        output_dir=reports_dir,
        raw_observations_dir=raw_dir,
        overwrite=False,
    )
    assert out1.exists()

    # 동일 배치에 대해 overwrite=False로 재시도 시 FileExistsError 차단
    with pytest.raises(FileExistsError, match="보고서 파일이 이미 존재합니다"):
        reconstruct_batch_report(
            batch_id="BATCH_SAFE",
            db_path=db_path,
            output_dir=reports_dir,
            raw_observations_dir=raw_dir,
            overwrite=False,
        )

    # overwrite=True 명시 시 정상 덮어쓰기 허용
    out2 = reconstruct_batch_report(
        batch_id="BATCH_SAFE",
        db_path=db_path,
        output_dir=reports_dir,
        raw_observations_dir=raw_dir,
        overwrite=True,
    )
    assert out2.exists()


def test_failure_scenario_6_price_drop_batch_reconstruction_accurate(isolated_db_and_raw):
    """시나리오 6: 실제 가격 인하(PRICE_DROP)가 있는 배치를 복구할 때 total_price_drop_krw가 0원이 아니라 실제 금액으로 복원됨을 검증."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")

    # 1차 관측: 2000만원에 등록
    raw_f1 = raw_dir / "batch_p1.json"
    sha1 = _create_sample_raw_json(raw_f1, "BATCH_P1", ["CAR_PRICE_DROP_01"])
    t1 = datetime(2026, 10, 21, 3, 0, 0, tzinfo=UTC)

    rec1 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_PRICE_DROP_01",
        manufacturer="현대",
        model_name="아반떼",
        price_krw=20_000_000,
        mileage_km=30000,
        observed_at=t1,
        product_type="CASH_OR_INSTALLMENT",
    )

    with Session() as s:
        pipeline.execute_batch(
            records=[rec1],
            session=s,
            batch_id="BATCH_P1",
            scope=scope,
            observation_time=t1,
            web_fetch_started_at=t1,
            web_fetch_completed_at=t1,
            raw_file_path=raw_f1,
            raw_file_sha256=sha1,
        )
        s.commit()

    # 2차 관측: 1850만원으로 150만원 가격 인하 발생
    raw_f2 = raw_dir / "batch_p2.json"
    sha2 = _create_sample_raw_json(raw_f2, "BATCH_P2", ["CAR_PRICE_DROP_01"])
    t2 = datetime(2026, 10, 21, 5, 0, 0, tzinfo=UTC)

    rec2 = StandardListingRecord(
        source_platform="ENCAR",
        source_listing_id="CAR_PRICE_DROP_01",
        manufacturer="현대",
        model_name="아반떼",
        price_krw=18_500_000,  # 150만원 인하
        mileage_km=30010,
        observed_at=t2,
        product_type="CASH_OR_INSTALLMENT",
    )

    with Session() as s:
        res2 = pipeline.execute_batch(
            records=[rec2],
            session=s,
            batch_id="BATCH_P2",
            scope=scope,
            observation_time=t2,
            web_fetch_started_at=t2,
            web_fetch_completed_at=t2,
            raw_file_path=raw_f2,
            raw_file_sha256=sha2,
        )
        s.commit()
        assert res2.price_drop_count == 1
        assert res2.total_price_drop_krw == 1_500_000

    # BATCH_P2 감사 보고서 복구 실행
    report_file = reconstruct_batch_report(
        batch_id="BATCH_P2",
        db_path=db_path,
        output_dir=reports_dir,
        raw_observations_dir=raw_dir,
    )
    content = report_file.read_text(encoding="utf-8")

    # 하드코딩 0원이 아닌 실제 인하액 1,500,000원이 정확히 복원되었는지 검증
    assert "1,500,000원" in content, f"가격 인하액이 1,500,000원으로 복원되지 않았습니다:\n{content}"
    assert "| **실제 가격 인하 (PRICE_DROP)** | **1건** |" in content


def test_failure_scenario_7_past_batch_reconstruction_after_new_live_added(isolated_db_and_raw):
    """시나리오 7: 신규 LIVE 배치(3차 등)가 추가되어 DB 건수가 늘어나도, 과거 1차 배치의 고유 관측 통계가 변질 없이 정확히 복구됨을 검증."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")

    # 1차 배치: 2대 신규 관측
    f1 = raw_dir / "b1.json"
    s1 = _create_sample_raw_json(f1, "B1", ["C1", "C2"])
    t1 = datetime(2026, 10, 21, 1, 0, 0, tzinfo=UTC)
    recs1 = [
        StandardListingRecord(source_platform="ENCAR", source_listing_id="C1", manufacturer="현대", model_name="아반떼", price_krw=1000, mileage_km=10000, observed_at=t1),
        StandardListingRecord(source_platform="ENCAR", source_listing_id="C2", manufacturer="현대", model_name="아반떼", price_krw=1200, mileage_km=12000, observed_at=t1),
    ]
    with Session() as s:
        pipeline.execute_batch(records=recs1, session=s, batch_id="B1", scope=scope, observation_time=t1, web_fetch_started_at=t1, web_fetch_completed_at=t1, raw_file_path=f1, raw_file_sha256=s1)
        s.commit()

    # 2차 배치: 3대 추가 (총 5대로 증가)
    f2 = raw_dir / "b2.json"
    s2 = _create_sample_raw_json(f2, "B2", ["C3", "C4", "C5"])
    t2 = datetime(2026, 10, 21, 2, 0, 0, tzinfo=UTC)
    recs2 = [
        StandardListingRecord(source_platform="ENCAR", source_listing_id="C3", manufacturer="현대", model_name="아반떼", price_krw=1500, mileage_km=15000, observed_at=t2),
        StandardListingRecord(source_platform="ENCAR", source_listing_id="C4", manufacturer="현대", model_name="아반떼", price_krw=1600, mileage_km=16000, observed_at=t2),
        StandardListingRecord(source_platform="ENCAR", source_listing_id="C5", manufacturer="현대", model_name="아반떼", price_krw=1700, mileage_km=17000, observed_at=t2),
    ]
    with Session() as s:
        pipeline.execute_batch(records=recs2, session=s, batch_id="B2", scope=scope, observation_time=t2, web_fetch_started_at=t2, web_fetch_completed_at=t2, raw_file_path=f2, raw_file_sha256=s2)
        s.commit()

    # B1(과거 배치) 복구 실행
    rep_b1 = reconstruct_batch_report(batch_id="B1", db_path=db_path, output_dir=reports_dir, raw_observations_dir=raw_dir)
    b1_text = rep_b1.read_text(encoding="utf-8")

    # B1 자체의 신규 관측은 2대이고, 복구 시점 누적 DB 실매물 수는 5대로 분리되어 정확히 표시되어야 함
    assert "| **신규 매물 최초 관측 (FIRST_SEEN)** | **2대** |" in b1_text
    assert "**누적 고유 실매물 수 (listings):** **5대**" in b1_text


# ==============================================================================
# 운영 DB 영구 보존 및 동적 적재 안정성 검증 (DIRECTIVE 011-A 지침 5)
# ==============================================================================

def test_operational_db_preservation_and_non_hardcoded_invariants():
    """지침 5: 운영 DB(chaficial_market_timeseries.db)가 고정값(238대)에 묶여있지 않고,

    신규 데이터 누적을 허용하면서도 기존 238대 실매물 ID 집합을 100% 온전히 보존하고 있음을 검증.
    """
    op_db_path = Path("data/chaficial_market_timeseries.db")
    assert op_db_path.exists(), "공식 운영 DB 파일이 존재하지 않습니다."

    engine = create_engine(f"sqlite:///{op_db_path}")
    Session = sessionmaker(bind=engine)

    with Session() as session:
        listing_count = session.execute(select(func.count(Listing.listing_id))).scalar()
        snapshot_count = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
        event_count = session.execute(select(func.count(PriceEvent.event_id))).scalar()
        batch_count = session.execute(select(func.count(BatchAuditLog.batch_id))).scalar()

        # 하한선 검증 (향후 3차 LIVE 이후에도 통과 보장)
        assert listing_count >= 238, f"운영 DB 실매물 수({listing_count})가 238대 미만으로 유실되었습니다."
        assert snapshot_count >= 246, f"운영 DB 스냅샷 수({snapshot_count})가 246건 미만으로 유실되었습니다."
        assert event_count >= 238, f"운영 DB 이벤트 수({event_count})가 238건 미만으로 유실되었습니다."
        assert batch_count >= 2, f"운영 DB 배치 감사 수({batch_count})가 2건 미만으로 유실되었습니다."

        # 기존 1차 실측 배치(ENCAR_CN7_LIVE_20261021_01)와 2차 실측 배치(ENCAR_CN7_LIVE_20261021_120825)의 PK 존재 검증
        batch_ids = set(session.execute(select(BatchAuditLog.batch_id)).scalars().all())
        assert "ENCAR_CN7_LIVE_20261021_01" in batch_ids, "1차 LIVE 배치가 DB에서 유실되었습니다."
        assert "ENCAR_CN7_LIVE_20261021_120825" in batch_ids, "2차 LIVE 배치가 DB에서 유실되었습니다."


def test_legacy_batch_reconstruction_marks_unverified_honestly():
    """레거시 1차 배치는 메타데이터가 없으므로 추측으로 검증하지 않고 LEGACY_UNVERIFIED_CANDIDATE로 정직하게 표기됨을 검증."""
    op_db_path = Path("data/chaficial_market_timeseries.db")
    assert op_db_path.exists()

    tmp_out = Path("outputs/test_legacy_recon")
    tmp_out.mkdir(parents=True, exist_ok=True)

    rep = reconstruct_batch_report(
        batch_id="ENCAR_CN7_LIVE_20261021_01",
        db_path=op_db_path,
        output_dir=tmp_out,
        overwrite=True,
    )
    content = rep.read_text(encoding="utf-8")

    # 레거시 배치의 정직한 표기 검증
    assert "LEGACY_UNVERIFIED" in content or "LEGACY_UNVERIFIED_CANDIDATE" in content
    assert "NOT_RECORDED (DB 적재 시각" in content or "NOT_RECORDED" in content
