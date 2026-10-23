"""CHA-FICIAL AI PROJECT - DIRECTIVE 011 / 011-A / 011-B 회귀 및 결함 방지 테스트 스위트.

총괄 감독 지침(DIRECTIVE 011-B) 검증:
1. 원본 무결성 엄격 검증:
   - JSON 내부 batch_id와 DB batch_id 불일치 시 차단.
   - raw_file_sha256 또는 raw_file_path 누락 시 차단.
   - JSON 파싱 오류 또는 dict 구조 불일치 시 차단.
2. 이벤트 통계 교차 검증:
   - 메타데이터 통계와 실제 DB PriceEvent 간 불일치 시 AUDIT_MISMATCH 감지 및 DB 실측치 채택.
3. 원자적 파일 저장:
   - 임시 파일(.tmp) 작성 후 원자적 교체 및 오류 시 정리.
4. 운영 테스트 독립성:
   - 운영 DB 부재 환경에서도 일반 단위 테스트 100% 통과 보장.
5. 트랜잭션 원자성:
   - auto_commit=False 제어를 통해 실패 시 dirty partial state 없는 완전 롤백 보장.
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


def _create_sample_raw_json(
    file_path: Path, batch_id: str, card_ids: list[str], internal_batch_id: str | None = None
) -> str:
    """원천 JSON 파일을 생성하고 SHA-256 해시를 반환합니다."""
    raw_data = {
        "batch_id": internal_batch_id or batch_id,
        "collected_at_utc": "2026-10-21T03:00:00Z",
        "completed_at_utc": "2026-10-21T03:00:30Z",
        "total_cards_collected": len(card_ids),
        "raw_cards": [{"id": cid, "price": 2000, "mileage": 30000} for cid in card_ids],
    }
    content = json.dumps(raw_data, ensure_ascii=False)
    file_path.write_text(content, encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ==============================================================================
# DIRECTIVE 011-B 신규 무결성 검증 테스트 (지침 1, 2, 3, 5)
# ==============================================================================

def test_directive_011b_raw_json_internal_batch_id_mismatch_fails(isolated_db_and_raw):
    """지침 1: 원본 JSON 파일 내부의 batch_id가 DB의 batch_id와 다르면 복구 실패 및 예외 발생 검증."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    # 파일 내 batch_id는 'OTHER_BATCH_999'이지만 DB에는 'BATCH_TARGET_01'로 기록
    raw_file = raw_dir / "target_batch.json"
    actual_sha = _create_sample_raw_json(
        raw_file, "BATCH_TARGET_01", ["CARD_1"], internal_batch_id="OTHER_BATCH_999"
    )

    with Session() as session:
        audit = BatchAuditLog(
            batch_id="BATCH_TARGET_01",
            source_platform="ENCAR",
            search_scope="ENCAR::HYUNDAI::AVANTE",
            processed_at=datetime.now(UTC),
            record_count=1,
            is_partial_scrape=False,
        )
        audit.set_audit_metadata({
            "raw_file_path": str(raw_file),
            "raw_file_sha256": actual_sha,
        })
        session.add(audit)
        session.commit()

    with pytest.raises(ValueError, match="일치하지 않습니다"):
        reconstruct_batch_report(
            batch_id="BATCH_TARGET_01",
            db_path=db_path,
            output_dir=reports_dir,
            raw_observations_dir=raw_dir,
        )


def test_directive_011b_missing_raw_file_sha_in_metadata_fails(isolated_db_and_raw):
    """지침 1: 신규 배치인데 raw_file_sha256 또는 raw_file_path가 비어있으면 VERIFIED_MATCH 거부 및 예외 발생."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    raw_file = raw_dir / "valid_file.json"
    _create_sample_raw_json(raw_file, "BATCH_INCOMPLETE_META", ["CARD_1"])

    with Session() as session:
        audit = BatchAuditLog(
            batch_id="BATCH_INCOMPLETE_META",
            source_platform="ENCAR",
            search_scope="ENCAR::HYUNDAI::AVANTE",
            processed_at=datetime.now(UTC),
            record_count=1,
            is_partial_scrape=False,
        )
        # raw_file_sha256 누락
        audit.set_audit_metadata({
            "raw_file_path": str(raw_file),
            "raw_file_sha256": None,
        })
        session.add(audit)
        session.commit()

    with pytest.raises(ValueError, match="필수 원본 정보.*누락"):
        reconstruct_batch_report(
            batch_id="BATCH_INCOMPLETE_META",
            db_path=db_path,
            output_dir=reports_dir,
            raw_observations_dir=raw_dir,
        )


def test_directive_011b_event_cross_validation_detects_mismatch(isolated_db_and_raw):
    """지침 2: 메타데이터에 잘못된 가격 인하액(예: 999만원)이 적혀있어도 DB 실제 PriceEvent(150만원)를 진실의 원천으로 채택하고

    AUDIT_MISMATCH 상태를 정확히 마킹함을 검증.
    """
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")
    t1 = datetime(2026, 10, 21, 3, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 10, 21, 5, 0, 0, tzinfo=UTC)

    # 1차 매물 등록
    raw_f1 = raw_dir / "b_init.json"
    sha1 = _create_sample_raw_json(raw_f1, "B_INIT", ["C_AUDIT_01"])
    with Session() as s:
        pipeline.execute_batch(
            records=[StandardListingRecord(source_platform="ENCAR", source_listing_id="C_AUDIT_01", manufacturer="현대", model_name="아반떼", price_krw=20000000, mileage_km=10000, observed_at=t1)],
            session=s,
            batch_id="B_INIT",
            scope=scope,
            observation_time=t1,
            raw_file_path=raw_f1,
            raw_file_sha256=sha1,
        )
        s.commit()

    # 2차 매물: 1850만원으로 실제 150만원 인하
    raw_f2 = raw_dir / "b_mismatch.json"
    sha2 = _create_sample_raw_json(raw_f2, "B_MISMATCH", ["C_AUDIT_01"])
    with Session() as s:
        pipeline.execute_batch(
            records=[StandardListingRecord(source_platform="ENCAR", source_listing_id="C_AUDIT_01", manufacturer="현대", model_name="아반떼", price_krw=18500000, mileage_km=10010, observed_at=t2)],
            session=s,
            batch_id="B_MISMATCH",
            scope=scope,
            observation_time=t2,
            raw_file_path=raw_f2,
            raw_file_sha256=sha2,
        )
        s.commit()

        # 메타데이터를 인위적으로 위조(인하액을 9,990,000원으로 조작)
        audit = s.execute(select(BatchAuditLog).where(BatchAuditLog.batch_id == "B_MISMATCH")).scalar_one()
        meta = audit.get_audit_metadata()
        meta["total_price_drop_krw"] = 9_990_000  # 위조 수치 주입
        audit.set_audit_metadata(meta)
        s.commit()

    # 복구 실행
    rep_file = reconstruct_batch_report(
        batch_id="B_MISMATCH",
        db_path=db_path,
        output_dir=reports_dir,
        raw_observations_dir=raw_dir,
    )
    content = rep_file.read_text(encoding="utf-8")

    # 교차 검증 결과 검증:
    # 1. 상태가 AUDIT_MISMATCH로 마킹되어야 함
    assert "AUDIT_MISMATCH" in content
    # 2. 위조 수치 9,990,000원이 아닌 실제 DB 이벤트 수치 1,500,000원이 보고서에 채택되어야 함
    assert "1,500,000원" in content
    assert "가격 인하 총액 불일치" in content


def test_directive_011b_atomic_file_write_and_error_cleanup(isolated_db_and_raw, monkeypatch):
    """지침 3: 보고서 생성 도중 오류 발생 시 임시 파일이 깨끗이 정리되고 DB 및 대상 디렉토리가 오염되지 않음을 검증."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    raw_file = raw_dir / "atomic_test.json"
    sha = _create_sample_raw_json(raw_file, "B_ATOMIC", ["C1"])

    with Session() as session:
        audit = BatchAuditLog(
            batch_id="B_ATOMIC",
            source_platform="ENCAR",
            search_scope="ENCAR::HYUNDAI::AVANTE",
            processed_at=datetime.now(UTC),
            record_count=1,
            is_partial_scrape=False,
        )
        audit.set_audit_metadata({"raw_file_path": str(raw_file), "raw_file_sha256": sha})
        session.add(audit)
        session.commit()

    # 쓰기 도중 에러를 주입하기 위해 os.replace 및 os.link를 패치
    def broken_replace(src, dst):
        raise IOError("Simulated Disk Full During Atomic Replace")

    monkeypatch.setattr("os.replace", broken_replace)
    monkeypatch.setattr("os.link", broken_replace)

    with pytest.raises(IOError, match="Simulated Disk Full"):
        reconstruct_batch_report(
            batch_id="B_ATOMIC",
            db_path=db_path,
            output_dir=reports_dir,
            raw_observations_dir=raw_dir,
        )

    # 임시 파일(.tmp)과 최종 파일 모두 남아있지 않아야 함
    tmp_files = list(reports_dir.glob("*.tmp"))
    assert len(tmp_files) == 0, f"임시 파일이 정리되지 않았습니다: {tmp_files}"
    assert not (reports_dir / "observation_batch_B_ATOMIC.md").exists()


def test_directive_011b_transaction_rollback_guarantees_clean_db(isolated_db_and_raw):
    """지침 5: auto_commit=False 모드에서 작업 중 예외 발생 시 session.rollback()으로 부분 적재나 감사 로그만 남지 않음을 검증."""
    Session = isolated_db_and_raw["Session"]
    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")
    t = datetime(2026, 10, 21, 3, 0, 0, tzinfo=UTC)

    records = [
        StandardListingRecord(source_platform="ENCAR", source_listing_id="TX_CAR_01", manufacturer="현대", model_name="아반떼", price_krw=1000, mileage_km=1000, observed_at=t),
        StandardListingRecord(source_platform="ENCAR", source_listing_id="TX_CAR_02", manufacturer="현대", model_name="아반떼", price_krw=2000, mileage_km=2000, observed_at=t),
    ]

    with Session() as session:
        try:
            pipeline.execute_batch(
                records=records,
                session=session,
                batch_id="B_TX_FAIL",
                scope=scope,
                observation_time=t,
                auto_commit=False,  # 호출부 트랜잭션 위임
            )
            # 인위적 런타임 오류 발생
            raise RuntimeError("Simulated Crash Before Final Commit")
        except RuntimeError:
            session.rollback()

    # 롤백 후 DB 검증: 아무런 매물, 스냅샷, 감사 로그도 남지 않아야 함
    with Session() as session:
        listings_cnt = session.execute(select(func.count(Listing.listing_id))).scalar()
        snapshots_cnt = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
        batches_cnt = session.execute(select(func.count(BatchAuditLog.batch_id))).scalar()

        assert listings_cnt == 0, "롤백되었으나 매물이 DB에 남아있습니다."
        assert snapshots_cnt == 0, "롤백되었으나 스냅샷이 DB에 남아있습니다."
        assert batches_cnt == 0, "롤백되었으나 감사 로그가 DB에 남아있습니다."


# ==============================================================================
# 기존 실패 시나리오 및 회귀 검증 테스트 (DIRECTIVE 011 / 011-A)
# ==============================================================================

def test_failure_scenario_1_missing_raw_json_raises_error(isolated_db_and_raw):
    """시나리오 1: 메타데이터에 기록된 원본 JSON 파일이 물리적으로 누락된 경우 FileNotFoundError 발생."""
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
    _create_sample_raw_json(raw_file, "BATCH_FAIL_02", ["CARD_01", "CARD_02"])
    recorded_sha = "0000000000000000000000000000000000000000000000000000000000000000"

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

    # overwrite=False 시 차단
    with pytest.raises(FileExistsError, match="보고서 파일이 이미 존재합니다"):
        reconstruct_batch_report(
            batch_id="BATCH_SAFE",
            db_path=db_path,
            output_dir=reports_dir,
            raw_observations_dir=raw_dir,
            overwrite=False,
        )

    # overwrite=True 시 성공
    out2 = reconstruct_batch_report(
        batch_id="BATCH_SAFE",
        db_path=db_path,
        output_dir=reports_dir,
        raw_observations_dir=raw_dir,
        overwrite=True,
    )
    assert out2.exists()


def test_failure_scenario_7_past_batch_reconstruction_after_new_live_added(isolated_db_and_raw):
    """시나리오 7: 신규 LIVE 배치(3차 등)가 추가되어 DB 건수가 늘어나도 과거 1차 배치의 고유 관측 통계가 변질 없이 정확히 복구됨을 검증."""
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")

    # 1차 배치: 2대
    f1 = raw_dir / "b1.json"
    s1 = _create_sample_raw_json(f1, "B1", ["C1", "C2"])
    t1 = datetime(2026, 10, 21, 1, 0, 0, tzinfo=UTC)
    recs1 = [
        StandardListingRecord(source_platform="ENCAR", source_listing_id="C1", manufacturer="현대", model_name="아반떼", price_krw=1000, mileage_km=10000, observed_at=t1),
        StandardListingRecord(source_platform="ENCAR", source_listing_id="C2", manufacturer="현대", model_name="아반떼", price_krw=1200, mileage_km=12000, observed_at=t1),
    ]
    with Session() as s:
        pipeline.execute_batch(records=recs1, session=s, batch_id="B1", scope=scope, observation_time=t1, raw_file_path=f1, raw_file_sha256=s1)
        s.commit()

    # 2차 배치: 3대 추가 (총 5대)
    f2 = raw_dir / "b2.json"
    s2 = _create_sample_raw_json(f2, "B2", ["C3", "C4", "C5"])
    t2 = datetime(2026, 10, 21, 2, 0, 0, tzinfo=UTC)
    recs2 = [
        StandardListingRecord(source_platform="ENCAR", source_listing_id="C3", manufacturer="현대", model_name="아반떼", price_krw=1500, mileage_km=15000, observed_at=t2),
        StandardListingRecord(source_platform="ENCAR", source_listing_id="C4", manufacturer="현대", model_name="아반떼", price_krw=1600, mileage_km=16000, observed_at=t2),
        StandardListingRecord(source_platform="ENCAR", source_listing_id="C5", manufacturer="현대", model_name="아반떼", price_krw=1700, mileage_km=17000, observed_at=t2),
    ]
    with Session() as s:
        pipeline.execute_batch(records=recs2, session=s, batch_id="B2", scope=scope, observation_time=t2, raw_file_path=f2, raw_file_sha256=s2)
        s.commit()

    # B1 복구
    rep_b1 = reconstruct_batch_report(batch_id="B1", db_path=db_path, output_dir=reports_dir, raw_observations_dir=raw_dir)
    b1_text = rep_b1.read_text(encoding="utf-8")

    assert "| **신규 매물 최초 관측 (FIRST_SEEN)** | **2대** |" in b1_text
    assert "**누적 고유 실매물 수 (listings):** **5대**" in b1_text


# ==============================================================================
# DIRECTIVE 011-C 최종 결함 방지 테스트 (지침 1, 2, 3)
# ==============================================================================

def test_directive_011c_live_execution_path_transaction_rollback(tmp_path):
    """지침 1: 실제 실행 경로(run_pipeline)에서 execute_batch 정상 반환 후

    외부 커밋 직전에 예외 발생 시, 5개 테이블의 변경이 전혀 남지 않고 100% 롤백됨을 검증.
    """
    from scripts.run_directive_010_market_stream import run_pipeline

    test_db = tmp_path / "rollback_test.db"
    dummy_input = tmp_path / "replay_input.json"

    # 재생용 샘플 데이터 생성 (엔카 실제 카드 형식 준수)
    raw_cards = [
        {
            "carid": "999901",
            "href": "https://fem.encar.com/cars/detail/999901",
            "raw_text": "엔카진단 무사고 아반떼 (CN7) 1.6 모던 21/05식 30,000km 가솔린 서울 2,000만원",
        }
    ]
    raw_payload = {
        "batch_id": "REPLAY_ROLLBACK_TEST_01",
        "collected_at_utc": "2026-10-21T03:00:00Z",
        "completed_at_utc": "2026-10-21T03:00:30Z",
        "total_cards_collected": 1,
        "raw_cards": raw_cards,
    }
    dummy_input.write_text(json.dumps(raw_payload, ensure_ascii=False), encoding="utf-8")

    # execute_batch 정상 완료 후 외부 커밋 직전 실패 주입
    with pytest.raises(RuntimeError, match="Simulated Crash Immediately After execute_batch"):
        run_pipeline(
            mode="replay",
            input_file=dummy_input,
            db_path_override=test_db,
            test_hook_fail_before_commit=True,
        )

    # 별도 독립 DB 연결로 5개 테이블 레코드 수 검증 (0건 롤백 보장)
    engine = create_engine(f"sqlite:///{test_db}")
    Session = sessionmaker(bind=engine)
    with Session() as s:
        l_cnt = s.execute(select(func.count(Listing.listing_id))).scalar()
        s_cnt = s.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
        e_cnt = s.execute(select(func.count(PriceEvent.event_id))).scalar()
        b_cnt = s.execute(select(func.count(BatchAuditLog.batch_id))).scalar()

        assert l_cnt == 0, f"롤백 실패: listings에 {l_cnt}건 잔존"
        assert s_cnt == 0, f"롤백 실패: listing_snapshots에 {s_cnt}건 잔존"
        assert e_cnt == 0, f"롤백 실패: price_events에 {e_cnt}건 잔존"
        assert b_cnt == 0, f"롤백 실패: batch_audit_logs에 {b_cnt}건 잔존"


def test_directive_011c_same_timestamp_different_batches_event_isolation(isolated_db_and_raw):
    """지침 2: 동일한 observation_time을 가진 서로 다른 두 배치가 생성되어도,

    각 배치의 가격 인하 및 인상 이벤트 통계가 섞이지 않고 독립적으로 정확히 귀속됨을 검증.
    """
    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    pipeline = MarketObservationStreamPipeline()
    scope = SearchScopeSpec(platform="ENCAR", manufacturer="현대", model_name="아반떼")

    # 1단계: 초기 매물 2대 등록 (CAR_DROP, CAR_INCREASE)
    t_init = datetime(2026, 10, 21, 1, 0, 0, tzinfo=UTC)
    with Session() as s:
        pipeline.execute_batch(
            records=[
                StandardListingRecord(source_platform="ENCAR", source_listing_id="CAR_DROP", manufacturer="현대", model_name="아반떼", price_krw=20000000, mileage_km=10000, observed_at=t_init),
                StandardListingRecord(source_platform="ENCAR", source_listing_id="CAR_INCREASE", manufacturer="현대", model_name="아반떼", price_krw=15000000, mileage_km=20000, observed_at=t_init),
            ],
            session=s,
            batch_id="BATCH_INIT",
            scope=scope,
            observation_time=t_init,
        )
        s.commit()

    # 2단계: 동일 시각(t_same)에 두 개의 서로 다른 배치 실행
    t_same = datetime(2026, 10, 21, 3, 0, 0, tzinfo=UTC)

    # 배치 A: CAR_DROP 가격 인하 (2000만 -> 1900만, 100만원 인하)
    raw_fa = raw_dir / "batch_a.json"
    sha_a = _create_sample_raw_json(raw_fa, "BATCH_SAME_A", ["CAR_DROP"])
    with Session() as s:
        pipeline.execute_batch(
            records=[
                StandardListingRecord(source_platform="ENCAR", source_listing_id="CAR_DROP", manufacturer="현대", model_name="아반떼", price_krw=19000000, mileage_km=10010, observed_at=t_same)
            ],
            session=s,
            batch_id="BATCH_SAME_A",
            scope=scope,
            observation_time=t_same,
            raw_file_path=raw_fa,
            raw_file_sha256=sha_a,
        )
        s.commit()

    # 배치 B: CAR_INCREASE 가격 인상 (1500만 -> 1550만, 50만원 인상)
    raw_fb = raw_dir / "batch_b.json"
    sha_b = _create_sample_raw_json(raw_fb, "BATCH_SAME_B", ["CAR_INCREASE"])
    with Session() as s:
        pipeline.execute_batch(
            records=[
                StandardListingRecord(source_platform="ENCAR", source_listing_id="CAR_INCREASE", manufacturer="현대", model_name="아반떼", price_krw=15500000, mileage_km=20010, observed_at=t_same)
            ],
            session=s,
            batch_id="BATCH_SAME_B",
            scope=scope,
            observation_time=t_same,
            raw_file_path=raw_fb,
            raw_file_sha256=sha_b,
        )
        s.commit()

    # 배치 A 복구 검증: 가격 인하 1건(100만원), 가격 인상 0건이어야 함
    rep_a = reconstruct_batch_report(batch_id="BATCH_SAME_A", db_path=db_path, output_dir=reports_dir, raw_observations_dir=raw_dir)
    text_a = rep_a.read_text(encoding="utf-8")
    assert "| **실제 가격 인하 (PRICE_DROP)** | **1건** |" in text_a
    assert "1,000,000원" in text_a
    assert "| **실제 가격 인상 (PRICE_INCREASE)** | **0건** |" in text_a

    # 배치 B 복구 검증: 가격 인상 1건, 가격 인하 0건(0원)이어야 함
    rep_b = reconstruct_batch_report(batch_id="BATCH_SAME_B", db_path=db_path, output_dir=reports_dir, raw_observations_dir=raw_dir)
    text_b = rep_b.read_text(encoding="utf-8")
    assert "| **실제 가격 인하 (PRICE_DROP)** | **0건** |" in text_b
    assert "0원" in text_b
    assert "| **실제 가격 인상 (PRICE_INCREASE)** | **1건** |" in text_b


def test_directive_011c_concurrent_report_reconstruction_prevents_overwrite(isolated_db_and_raw):
    """지침 3: 동일 배치에 대해 두 스레드가 동시에 복구를 시도할 때,

    정확히 하나만 성공하고 다른 하나는 FileExistsError로 안전하게 차단됨을 검증.
    """
    import concurrent.futures

    db_path = isolated_db_and_raw["db_path"]
    reports_dir = isolated_db_and_raw["reports_dir"]
    raw_dir = isolated_db_and_raw["raw_dir"]
    Session = isolated_db_and_raw["Session"]

    raw_file = raw_dir / "conc_batch.json"
    sha = _create_sample_raw_json(raw_file, "BATCH_CONCURRENT", ["C1"])

    with Session() as session:
        audit = BatchAuditLog(
            batch_id="BATCH_CONCURRENT",
            source_platform="ENCAR",
            search_scope="ENCAR::HYUNDAI::AVANTE",
            processed_at=datetime.now(UTC),
            record_count=1,
            is_partial_scrape=False,
        )
        audit.set_audit_metadata({"raw_file_path": str(raw_file), "raw_file_sha256": sha})
        session.add(audit)
        session.commit()

    results = []
    errors = []

    def run_reconstruct():
        try:
            p = reconstruct_batch_report(
                batch_id="BATCH_CONCURRENT",
                db_path=db_path,
                output_dir=reports_dir,
                raw_observations_dir=raw_dir,
                overwrite=False,
            )
            results.append(p)
        except Exception as e:
            errors.append(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(run_reconstruct)
        f2 = executor.submit(run_reconstruct)
        concurrent.futures.wait([f1, f2])

    # 1개는 성공, 1개는 FileExistsError 발생 확인
    assert len(results) == 1, f"성공 건수가 1개가 아닙니다: {len(results)}"
    assert len(errors) == 1, f"차단된 에러 건수가 1개가 아닙니다: {len(errors)}"
    assert isinstance(errors[0], FileExistsError), f"차단 에러가 FileExistsError가 아닙니다: {errors[0]}"
    assert (reports_dir / "observation_batch_BATCH_CONCURRENT.md").exists()


# ==============================================================================
# 운영 DB 영구 보존 및 독립성 검증 (지침 4)
# ==============================================================================

@pytest.mark.skipif(not Path("data/chaficial_market_timeseries.db").exists(), reason="운영 DB가 로컬 환경에 없을 경우 단위 테스트 독립 통과")
def test_operational_db_preservation_and_non_hardcoded_invariants():
    """지침 4: 운영 DB(chaficial_market_timeseries.db)가 존재하는 환경에서 238대 실매물 ID 집합 및 스냅샷이 영구 보존됨을 검증."""
    op_db_path = Path("data/chaficial_market_timeseries.db")

    engine = create_engine(f"sqlite:///{op_db_path}")
    Session = sessionmaker(bind=engine)

    with Session() as session:
        listing_count = session.execute(select(func.count(Listing.listing_id))).scalar()
        snapshot_count = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
        event_count = session.execute(select(func.count(PriceEvent.event_id))).scalar()
        batch_count = session.execute(select(func.count(BatchAuditLog.batch_id))).scalar()

        # 하한선 검증
        assert listing_count >= 238
        assert snapshot_count >= 246
        assert event_count >= 238
        assert batch_count >= 2

        # 배치 키 보존 검증
        batch_ids = set(session.execute(select(BatchAuditLog.batch_id)).scalars().all())
        assert "ENCAR_CN7_LIVE_20261021_01" in batch_ids
        assert "ENCAR_CN7_LIVE_20261021_120825" in batch_ids
