"""차피셜 가격 변동 추적 및 이벤트 탐지 엔진 (PriceEventTracker - DIRECTIVE 009).

매물의 시계열 관측 스트림을 분석하여 신규 등록, 가격 인하, 가격 인상, 비노출/재등록 이벤트를
정밀하게 탐지하고 데이터베이스에 영구 보존합니다.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.models.vehicle_link import VehicleIdentityLink
from chaficial.platforms.base import StandardListingRecord


class PriceEventTracker:
    """시계열 매물 가격 변동 추적기."""

    def __init__(self, consecutive_missing_threshold: int = 3):
        """
        Args:
            consecutive_missing_threshold: 판매 종료(DELISTED) 판정에 필요한 최소 연속 미관측 횟수.
                                          1회 검색 누락으로 인한 섣부른 판매 완료 판정을 방지합니다.
        """
        self.consecutive_missing_threshold = consecutive_missing_threshold

    @staticmethod
    def _to_utc(dt: datetime | None) -> datetime:
        """일관된 UTC datetime 변환."""
        if dt is None:
            return datetime.now(UTC)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    def process_observation(
        self,
        record: StandardListingRecord,
        session: Session,
    ) -> PriceEvent | None:
        """단일 매물 관측 레코드를 수신하여 시계열 스냅샷 적재 및 가격 변동 이벤트 탐지."""
        obs_utc = self._to_utc(record.observed_at)

        # 금융상품 및 비정상 가격 검증: 월납입액을 차량 총가격으로 오인하는 결함 차단
        is_financial = record.product_type in ("RENT", "LEASE")
        valid_cash_price = (
            record.price_krw is not None
            and record.price_krw > 0
            and not is_financial
        )

        effective_price = record.price_krw if valid_cash_price else None

        # 1. 기존 매물 식별 정보 조회
        existing_listing = session.execute(
            select(Listing).where(
                Listing.source_platform == record.source_platform,
                Listing.source_listing_id == record.source_listing_id,
            )
        ).scalar_one_or_none()

        # A. 신규 매물 (NEW_LISTING) 최초 관측
        if existing_listing is None:
            new_listing = Listing(
                source_platform=record.source_platform,
                source_listing_id=record.source_listing_id,
                seller_reference=record.seller_reference,
                first_observed_at=obs_utc,
                raw_location=record.raw_location or "UNKNOWN",
                current_status="ACTIVE",
            )
            session.add(new_listing)
            session.flush()

            # 최초 스냅샷 생성
            snapshot = ListingSnapshot(
                listing_id=new_listing.listing_id,
                observed_at=obs_utc,
                price_krw=effective_price if effective_price is not None else 0,
                mileage_km=record.mileage_km,
                listing_status="ACTIVE",
                raw_specs={
                    "model": record.model_name,
                    "sub_model": record.sub_model,
                    "product_type": record.product_type,
                    "monthly_payment": record.monthly_payment_krw,
                    "vehicle_fingerprint": record.vehicle_fingerprint,
                },
            )
            session.add(snapshot)

            # 최초 관측 이벤트 생성
            event = PriceEvent(
                listing_id=new_listing.listing_id,
                source_platform=record.source_platform,
                source_listing_id=record.source_listing_id,
                event_type="NEW_LISTING",
                event_timestamp=obs_utc,
                previous_price_krw=None,
                new_price_krw=effective_price,
                price_delta_krw=0,
                price_delta_pct=0.0,
                initial_price_krw=effective_price,
                cumulative_delta_krw=0,
                cumulative_delta_pct=0.0,
                mileage_at_event=record.mileage_km,
                days_since_first_observed=0,
                product_type=record.product_type,
                is_anomaly=(is_financial and record.price_krw is not None and record.price_krw <= 1_000_000),
                notes="신규 매물 최초 관측",
            )
            session.add(event)
            return event

        # B. 기존 매물의 재관측 (동일 listing_id 시계열 유지 - 주행거리 변경 시에도 연속성 보장)
        latest_snapshot = session.execute(
            select(ListingSnapshot)
            .where(ListingSnapshot.listing_id == existing_listing.listing_id)
            .order_by(ListingSnapshot.observed_at.desc())
        ).scalars().first()

        # 최초 관측 스냅샷 (누적 변동 계산용)
        first_snapshot = session.execute(
            select(ListingSnapshot)
            .where(ListingSnapshot.listing_id == existing_listing.listing_id)
            .order_by(ListingSnapshot.observed_at.asc())
        ).scalars().first()

        initial_price = (
            first_snapshot.price_krw
            if (first_snapshot and first_snapshot.price_krw > 0)
            else effective_price
        )

        prev_price = latest_snapshot.price_krw if latest_snapshot else None
        if prev_price == 0:
            prev_price = None

        first_obs_utc = self._to_utc(existing_listing.first_observed_at)
        days_passed = max(0, (obs_utc.date() - first_obs_utc.date()).days)

        event: PriceEvent | None = None

        # DELISTED 상태였다가 재등장한 경우 (RE_LISTED_SUSPECT)
        if existing_listing.current_status == "DELISTED":
            existing_listing.current_status = "ACTIVE"
            event = PriceEvent(
                listing_id=existing_listing.listing_id,
                source_platform=record.source_platform,
                source_listing_id=record.source_listing_id,
                event_type="RE_LISTED_SUSPECT",
                event_timestamp=obs_utc,
                previous_price_krw=prev_price,
                new_price_krw=effective_price,
                price_delta_krw=0,
                price_delta_pct=0.0,
                initial_price_krw=initial_price,
                cumulative_delta_krw=0,
                cumulative_delta_pct=0.0,
                mileage_at_event=record.mileage_km,
                days_since_first_observed=days_passed,
                product_type=record.product_type,
                notes="비노출 처리되었던 매물의 재등록 관측",
            )
            session.add(event)

        # 가격 변동 탐지 (유효 현금 매매가 존재할 때만)
        if (
            valid_cash_price
            and prev_price is not None
            and prev_price > 0
            and effective_price != prev_price
        ):
            delta_krw = effective_price - prev_price
            delta_pct = round((delta_krw / prev_price) * 100.0, 2)

            cum_delta_krw = effective_price - initial_price if initial_price else delta_krw
            cum_delta_pct = (
                round((cum_delta_krw / initial_price) * 100.0, 2)
                if initial_price and initial_price > 0
                else delta_pct
            )

            # 가격 인하 (PRICE_DROP) vs 가격 인상 (PRICE_INCREASE)
            if delta_krw < 0:
                ev_type = "PRICE_DROP"
                existing_listing.current_status = "PRICE_CHANGED"
                note_str = f"가격 인하 탐지: {prev_price:,}원 -> {effective_price:,}원 ({delta_krw:+,}원, {delta_pct:+.2f}%)"
            else:
                ev_type = "PRICE_INCREASE"
                existing_listing.current_status = "PRICE_CHANGED"
                note_str = f"가격 인상 탐지: {prev_price:,}원 -> {effective_price:,}원 ({delta_krw:+,}원, {delta_pct:+.2f}%)"

            event = PriceEvent(
                listing_id=existing_listing.listing_id,
                source_platform=record.source_platform,
                source_listing_id=record.source_listing_id,
                event_type=ev_type,
                event_timestamp=obs_utc,
                previous_price_krw=prev_price,
                new_price_krw=effective_price,
                price_delta_krw=delta_krw,
                price_delta_pct=delta_pct,
                initial_price_krw=initial_price,
                cumulative_delta_krw=cum_delta_krw,
                cumulative_delta_pct=cum_delta_pct,
                mileage_at_event=record.mileage_km,
                days_since_first_observed=days_passed,
                product_type=record.product_type,
                notes=note_str,
            )
            session.add(event)

        # 새로운 상태 스냅샷 저장 (Append-only 불변성 유지)
        # 가격이 같더라도 주행거리가 변경되었거나 시간이 경과한 경우 새로운 관측 스냅샷 추가
        is_duplicate_snapshot = (
            latest_snapshot is not None
            and latest_snapshot.observed_at == obs_utc
            and latest_snapshot.price_krw == (effective_price or 0)
            and latest_snapshot.mileage_km == record.mileage_km
        )

        if not is_duplicate_snapshot:
            new_snapshot = ListingSnapshot(
                listing_id=existing_listing.listing_id,
                observed_at=obs_utc,
                price_krw=effective_price if effective_price is not None else 0,
                mileage_km=record.mileage_km,
                listing_status=existing_listing.current_status,
                raw_specs={
                    "model": record.model_name,
                    "sub_model": record.sub_model,
                    "product_type": record.product_type,
                    "monthly_payment": record.monthly_payment_krw,
                    "vehicle_fingerprint": record.vehicle_fingerprint,
                },
            )
            session.add(new_snapshot)

        return event

    def process_batch(
        self,
        records: list[StandardListingRecord],
        session: Session,
        observation_time: datetime | None = None,
    ) -> list[PriceEvent]:
        """관측 배치 전수 처리 및 가격 변동 이벤트 목록 반환."""
        events: list[PriceEvent] = []
        for rec in records:
            if observation_time and not rec.observed_at:
                rec.observed_at = observation_time
            ev = self.process_observation(rec, session)
            if ev is not None:
                events.append(ev)

        session.commit()
        return events

    @staticmethod
    def get_price_drops_summary(
        session: Session,
        window_days: int = 7,
    ) -> list[dict[str, Any]]:
        """최근 N일간 발생한 가격 인하(PRICE_DROP) 이벤트 집계."""
        now = datetime.now(UTC)
        since_time = now - timedelta(days=window_days)

        events = session.execute(
            select(PriceEvent)
            .where(
                PriceEvent.event_type == "PRICE_DROP",
                PriceEvent.event_timestamp >= since_time,
            )
            .order_by(PriceEvent.price_delta_krw.asc())  # 인하폭이 큰 순서
        ).scalars().all()

        results = []
        for ev in events:
            results.append({
                "event_id": ev.event_id,
                "listing_id": ev.source_listing_id,
                "platform": ev.source_platform,
                "previous_price_krw": ev.previous_price_krw,
                "new_price_krw": ev.new_price_krw,
                "price_drop_krw": abs(ev.price_delta_krw),
                "price_drop_pct": abs(ev.price_delta_pct),
                "days_since_first_observed": ev.days_since_first_observed,
                "event_timestamp": ev.event_timestamp.isoformat(),
                "notes": ev.notes,
            })
        return results
