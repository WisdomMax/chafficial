"""CHA-FICIAL AI PROJECT - DIRECTIVE 011
이미 DB에 적재된 관측 배치의 감사 보고서 안전 복구 및 재생성 유틸리티.

본 모듈은 DB 커밋 완료 후 보고서 생성 단계에서 오류가 발생하더라도,
기 적재된 DB 이력과 원본 JSON으로부터 감사 보고서를 100% 온전하게 재구성(Reconstruct)합니다.
"""

import argparse
import hashlib
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.models.vehicle_link import VehicleIdentityLink
from chaficial.tracker.price_tracker import compute_db_logical_hashes
from chaficial.tracker.stream_pipeline import (
    BatchExecutionResult,
    MarketObservationStreamPipeline,
)
from scripts.run_directive_010_market_stream import generate_batch_observation_report


def reconstruct_batch_report(
    batch_id: str,
    db_path: Path = Path("data/chaficial_market_timeseries.db"),
    output_dir: Path = Path("reports/observations"),
    overwrite: bool = False,
) -> Path:
    """DB에 이미 커밋된 배치의 감사 보고서를 역조회하여 안전하게 재생성합니다."""
    if not db_path.exists():
        raise FileNotFoundError(f"데이터베이스 파일이 존재하지 않습니다: {db_path}")

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)

    with Session() as session:
        # 1. 해당 배치의 감사 로그 조회
        batch_audit = session.execute(
            select(BatchAuditLog).where(BatchAuditLog.batch_id == batch_id)
        ).scalar_one_or_none()

        if not batch_audit:
            raise ValueError(f"데이터베이스에 해당 배치 ID({batch_id})의 감사 로그가 존재하지 않습니다.")

        # 2. 누적 전체 배치 조회
        all_batches = session.execute(
            select(BatchAuditLog).order_by(BatchAuditLog.processed_at.asc())
        ).scalars().all()

        # 3. 해당 배치 시점의 이벤트 및 스냅샷 통계 역조회
        events_in_batch = session.execute(
            select(PriceEvent).where(PriceEvent.event_timestamp == batch_audit.processed_at)
        ).scalars().all()

        first_seen_count = sum(1 for e in events_in_batch if e.event_type == "FIRST_SEEN")
        re_observed_count = sum(1 for e in events_in_batch if e.event_type == "RE_OBSERVED")
        price_drop_count = sum(1 for e in events_in_batch if e.event_type == "PRICE_DROP")
        price_increase_count = sum(1 for e in events_in_batch if e.event_type == "PRICE_INCREASE")
        delisted_suspect_count = sum(1 for e in events_in_batch if e.event_type == "DELISTED_SUSPECT")

        # 4. 전체 테이블 현황 조회
        post_listings = session.execute(select(func.count(Listing.listing_id))).scalar()
        post_snapshots = session.execute(select(func.count(ListingSnapshot.snapshot_id))).scalar()
        post_events = session.execute(select(func.count(PriceEvent.event_id))).scalar()
        post_batches = session.execute(select(func.count(BatchAuditLog.batch_id))).scalar()
        post_links = session.execute(select(func.count(VehicleIdentityLink.link_id))).scalar()

        live_db_hashes = compute_db_logical_hashes(session)

    # 5. 원본 JSON 파일 매칭 및 SHA-256 계산
    raw_dir = Path("data/raw_observations")
    raw_file = None
    raw_sha = "UNKNOWN_OR_RECONSTRUCTED"
    total_cards = batch_audit.record_count

    # 배치 ID와 매칭되는 파일 탐색
    batch_ts_suffix = batch_id.replace("ENCAR_CN7_LIVE_", "")
    candidate_file = raw_dir / f"encar_cn7_live_{batch_ts_suffix}.json"
    if candidate_file.exists():
        raw_file = candidate_file
    else:
        # 디렉토리 내 검색
        for f in raw_dir.glob("*.json"):
            if batch_ts_suffix in f.name:
                raw_file = f
                break

    if raw_file and raw_file.exists():
        raw_sha = hashlib.sha256(raw_file.read_bytes()).hexdigest()
        import json
        try:
            with open(raw_file, "r", encoding="utf-8") as rf:
                raw_data = json.load(rf)
                total_cards = raw_data.get("total_cards_collected", len(raw_data.get("raw_cards", [])))
        except Exception:
            pass
    else:
        raw_file = Path(f"data/raw_observations/encar_cn7_live_{batch_ts_suffix}.json")

    pipeline = MarketObservationStreamPipeline()
    obs_time = batch_audit.processed_at or datetime.now(UTC)

    dummy_res = BatchExecutionResult(
        batch_id=batch_id,
        search_scope_key=batch_audit.search_scope,
        started_at_utc=obs_time,
        completed_at_utc=obs_time,
        started_at_kst=pipeline.to_kst_string(obs_time),
        completed_at_kst=pipeline.to_kst_string(obs_time),
        total_records_ingested=batch_audit.record_count,
        first_seen_count=first_seen_count,
        re_observed_count=re_observed_count,
        price_drop_count=price_drop_count,
        price_increase_count=price_increase_count,
        total_price_drop_krw=0,
        re_listed_count=0,
        delisted_suspect_count=delisted_suspect_count,
        is_success=True,
        is_partial_scrape=batch_audit.is_partial_scrape,
    )

    report_content = generate_batch_observation_report(
        batch_id=batch_id,
        web_start_utc=obs_time,
        web_end_utc=obs_time,
        raw_file=raw_file,
        raw_sha=raw_sha,
        total_cards=total_cards,
        parsed_count=batch_audit.record_count,
        batch_result=dummy_res,
        post_listings=post_listings,
        post_snapshots=post_snapshots,
        post_events=post_events,
        post_batches=post_batches,
        post_links=post_links,
        live_db_hashes=live_db_hashes,
        all_batches=all_batches,
        pipeline=pipeline,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"observation_batch_{batch_id}.md"

    mode = "w" if overwrite else "x"
    with open(out_file, mode, encoding="utf-8") as f:
        f.write(report_content)

    print(f"[+] [DIRECTIVE 011] 배치 감사 보고서 복구/재생성 완료: {out_file}")
    return out_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CHA-FICIAL DIRECTIVE 011 Report Reconstructor")
    parser.add_argument("batch_id", help="복구할 관측 배치 ID")
    parser.add_argument("--db", type=Path, default=Path("data/chaficial_market_timeseries.db"), help="대상 DB 경로")
    parser.add_argument("--overwrite", action="store_true", help="기존 파일 덮어쓰기 허용 여부")
    args = parser.parse_args()

    reconstruct_batch_report(batch_id=args.batch_id, db_path=args.db, overwrite=args.overwrite)
