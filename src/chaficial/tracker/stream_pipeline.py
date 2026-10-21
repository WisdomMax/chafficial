"""CHA-FICIAL AI PROJECT - DIRECTIVE 010
실제 시장 반복 관측 스트림 파이프라인 (Market Observation Stream Pipeline).

본 모듈은:
1. 수집 배치마다 고유한 batch_id와 UTC/KST 시각을 기록하고 BatchAuditLog를 영속화합니다.
2. 각 배치의 매물을 순차 처리하여 최초 발견(FIRST_SEEN), 재관측, 가격 변동(PRICE_DROP/PRICE_INCREASE)을 정밀 탐지합니다.
3. 완전 성공 배치에 한해 구조화된 SearchScopeSpec 범위 내 미노출 매물을 추적합니다.
4. 실제 시장 관측(REAL_OBSERVED)과 가상 시뮬레이션(SIMULATED) 데이터를 영구 격리합니다.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.platforms.base import StandardListingRecord
from chaficial.tracker.price_tracker import PriceEventTracker, SearchScopeSpec


KST = ZoneInfo("Asia/Seoul")


@dataclass
class BatchExecutionResult:
    """단일 관측 배치 실행 결과 집계."""
    batch_id: str
    search_scope_key: str
    started_at_utc: datetime
    completed_at_utc: datetime
    started_at_kst: str
    completed_at_kst: str
    total_records_ingested: int
    first_seen_count: int
    re_observed_count: int
    price_drop_count: int
    price_increase_count: int
    total_price_drop_krw: int
    re_listed_count: int
    delisted_suspect_count: int
    is_success: bool
    is_partial_scrape: bool
    notes: str | None = None


class MarketObservationStreamPipeline:
    """실제 시장 반복 수집 파이프라인 관리자."""

    def __init__(self, tracker: PriceEventTracker | None = None):
        self.tracker = tracker or PriceEventTracker(consecutive_missing_threshold=3)

    @staticmethod
    def to_kst_string(dt: datetime) -> str:
        """UTC datetime을 한국시간(KST, UTC+9) 문자열로 포맷."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        kst_dt = dt.astimezone(KST)
        return kst_dt.strftime("%Y-%m-%d %H:%M:%S KST")

    def execute_batch(
        self,
        records: list[StandardListingRecord],
        session: Session,
        batch_id: str,
        scope: SearchScopeSpec,
        observation_time: datetime | None = None,
        is_partial_scrape: bool = False,
        is_success: bool = True,
        data_origin: str = "REAL_OBSERVED",
        notes: str | None = None,
    ) -> BatchExecutionResult:
        """단일 수집 배치를 원자적으로 실행하고 상세 통계를 반환합니다."""
        # 1. 배치 ID 필수성 검증
        if not batch_id or not batch_id.strip():
            raise ValueError("batch_id is strictly required for executing an observation batch.")

        obs_utc = self.tracker._to_utc(observation_time) if observation_time else datetime.now(UTC)
        start_utc = obs_utc
        scope_key = scope.to_scope_key()

        # 2. 배치 중복 멱등성 검사
        existing_batch = session.execute(
            select(BatchAuditLog).where(BatchAuditLog.batch_id == batch_id)
        ).scalar_one_or_none()
        if existing_batch is not None:
            end_utc = start_utc + timedelta(seconds=1)
            return BatchExecutionResult(
                batch_id=batch_id,
                search_scope_key=scope_key,
                started_at_utc=start_utc,
                completed_at_utc=end_utc,
                started_at_kst=self.to_kst_string(start_utc),
                completed_at_kst=self.to_kst_string(end_utc),
                total_records_ingested=0,
                first_seen_count=0,
                re_observed_count=0,
                price_drop_count=0,
                price_increase_count=0,
                total_price_drop_krw=0,
                re_listed_count=0,
                delisted_suspect_count=0,
                is_success=True,
                is_partial_scrape=is_partial_scrape,
                notes="ALREADY_PROCESSED_IDEMPOTENT_SKIP",
            )

        # 3. 매물 레코드 처리
        first_seen_count = 0
        re_observed_count = 0
        price_drop_count = 0
        price_increase_count = 0
        total_price_drop_krw = 0
        re_listed_count = 0

        observed_source_ids: set[str] = set()

        for rec in records:
            observed_source_ids.add(rec.source_listing_id)
            # 기존 매물 여부 사전 확인
            existing_listing = session.execute(
                select(Listing).where(
                    Listing.source_platform == rec.source_platform,
                    Listing.source_listing_id == rec.source_listing_id,
                )
            ).scalar_one_or_none()

            is_new = existing_listing is None
            ev = self.tracker.process_observation(rec, session, data_origin=data_origin)

            if is_new:
                first_seen_count += 1
            else:
                re_observed_count += 1
                if ev:
                    if ev.event_type == "PRICE_DROP":
                        price_drop_count += 1
                        total_price_drop_krw += abs(ev.price_delta_krw)
                    elif ev.event_type == "PRICE_INCREASE":
                        price_increase_count += 1
                    elif ev.event_type == "RE_LISTED_SUSPECT":
                        re_listed_count += 1

        # 4. 미노출 매물 처리 (완전 성공 배치인 경우에만 수행)
        delisted_suspect_events = []
        if is_success and not is_partial_scrape:
            delisted_suspect_events = self.tracker.process_missing_listings(
                observed_source_listing_ids=observed_source_ids,
                session=session,
                observation_time=obs_utc,
                batch_id=batch_id,
                scope=scope,
                is_partial_scrape=is_partial_scrape,
                search_scope_success=is_success,
                data_origin=data_origin,
                notes=notes,
            )
        else:
            # 부분 수집 또는 실패 시 감사 로그만 별도 기록
            audit_log = BatchAuditLog(
                batch_id=batch_id,
                source_platform=scope.platform,
                search_scope=scope_key,
                processed_at=obs_utc,
                record_count=len(records),
                is_partial_scrape=is_partial_scrape,
                notes=f"PARTIAL_OR_FAILED_BATCH: {notes or ''}",
            )
            session.add(audit_log)
            session.commit()

        end_utc = obs_utc + timedelta(seconds=2)

        return BatchExecutionResult(
            batch_id=batch_id,
            search_scope_key=scope_key,
            started_at_utc=start_utc,
            completed_at_utc=end_utc,
            started_at_kst=self.to_kst_string(start_utc),
            completed_at_kst=self.to_kst_string(end_utc),
            total_records_ingested=len(records),
            first_seen_count=first_seen_count,
            re_observed_count=re_observed_count,
            price_drop_count=price_drop_count,
            price_increase_count=price_increase_count,
            total_price_drop_krw=total_price_drop_krw,
            re_listed_count=re_listed_count,
            delisted_suspect_count=len(delisted_suspect_events),
            is_success=is_success,
            is_partial_scrape=is_partial_scrape,
            notes=notes,
        )
