"""차피셜 가격 변동 추적 및 시계열 이벤트 탐지 엔진 (PriceEventTracker - DIRECTIVE 009-A).

매물의 시계열 관측 스트림을 분석하여 신규 등록, 가격 인하, 가격 인상, 비노출 의심, 재등장 이벤트를
정밀하게 탐지하고 데이터베이스에 영구 보존합니다.

개선 사항:
1. price_krw NULL 명시적 보존 (금융상품/결측 시 0원으로 오염 방지)
2. data_origin (REAL_OBSERVED vs SIMULATED) 완전 분리
3. 동일 관측 재실행 시 멱등성(Idempotency) 보장
4. 과거 데이터 지연 입력(Out-of-order) 시 현재 상태 보존
5. 검색 성공 여부에 따른 연속 미노출 카운터 및 DELISTED_SUSPECT 전이
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from chaficial.models.batch_log import BatchAuditLog
from chaficial.models.listing import Listing
from chaficial.models.price_event import PriceEvent
from chaficial.models.snapshot import ListingSnapshot
from chaficial.platforms.base import StandardListingRecord


@dataclass(frozen=True)
class SearchScopeSpec:
    """구조화된 검색 범위 사양.

    단순 문자열 부분 일치로 인한 타 차종/연식/서브모델 교차 오판을 방지하고
    완전 수집된 동일 검색 조건에 대해서만 미노출 판정을 엄격히 한정합니다.
    """
    platform: str = "ENCAR"
    manufacturer: str | None = None
    model_name: str | None = None
    sub_model: str | None = None
    min_year: int | None = None
    max_year: int | None = None

    def to_scope_key(self) -> str:
        """영속 감사 로그용 고유 범위 키 생성."""
        mfg = self.manufacturer or "ALL"
        model = self.model_name or "ALL"
        sub = self.sub_model or "ALL"
        y_range = f"{self.min_year or 'MIN'}~{self.max_year or 'MAX'}"
        return f"{self.platform}:{mfg}:{model}:{sub}:{y_range}"

    def matches_specs(self, specs: dict[str, Any] | None) -> bool:
        """매물 스냅샷 제원과 검색 범위가 일치하는지 정밀하고 구조적으로 검증.

        1. 제원이 결측(None 또는 빈 dict)된 매물은 안전을 위해 미노출 판정에서 제외(False 반환)합니다.
        2. 제조사, 모델, 서브모델에 대해 부분 문자열이 아닌 정규화된 정확 일치를 기본으로 비교합니다.
        3. 연식 범위(min_year, max_year)가 지정된 경우 정확히 범위 내에 있는지 검증합니다.
        """
        if not specs:
            return False

        # 1. 제조사 검증 (정규화된 정확 일치)
        if self.manufacturer and self.manufacturer != "ALL":
            spec_mfg = str(specs.get("manufacturer") or "").strip()
            # 제원에 제조사가 기재되지 않은 경우 안전하게 미포함 처리
            if not spec_mfg or spec_mfg != self.manufacturer.strip():
                # 차량 지문(vehicle_fingerprint)에서 첫 번째 토큰 검사
                fp = str(specs.get("vehicle_fingerprint") or "")
                tokens = fp.split("_")
                if len(tokens) > 0 and tokens[0] != self.manufacturer.strip():
                    return False

        # 2. 모델명 검증 (정규화된 정확 일치)
        if self.model_name and self.model_name != "ALL":
            spec_model = str(specs.get("model") or "").strip()
            target_model = self.model_name.strip()
            if not spec_model or spec_model != target_model:
                return False

        # 3. 서브모델 검증 (지정된 경우 정확 일치)
        if self.sub_model and self.sub_model != "ALL":
            spec_sub = str(specs.get("sub_model") or "").strip()
            target_sub = self.sub_model.strip()
            if not spec_sub or spec_sub != target_sub:
                return False

        # 4. 연식 범위 검증
        if self.min_year or self.max_year:
            year_val = specs.get("model_year") or specs.get("year")
            # 지문에서 연식 토큰 추출 시도
            if not year_val:
                fp = str(specs.get("vehicle_fingerprint") or "")
                tokens = fp.split("_")
                # 형식: 현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2022-07_2023_... (인덱스 6: 2023)
                if len(tokens) >= 7 and tokens[6].isdigit():
                    year_val = int(tokens[6])

            if year_val:
                try:
                    int_year = int(year_val)
                    if self.min_year and int_year < self.min_year:
                        return False
                    if self.max_year and int_year > self.max_year:
                        return False
                except (ValueError, TypeError):
                    return False
            else:
                # 연식이 필수인데 제원에 연식이 없으면 안전을 위해 제외
                return False

        return True


import hashlib
import json

def deterministic_serialize(val: Any) -> str:
    """결정론적 값 직렬화 (NULL, DateTime, JSON dict, bool, number 등)."""
    if val is None:
        return "NULL"
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, dict):
        return json.dumps(val, sort_keys=True, ensure_ascii=False)
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    return str(val)


def compute_db_logical_hashes(session: Session) -> dict[str, Any]:
    """운영 DB의 논리적 데이터 행 기반 SHA-256 해시 계산.

    5개 주요 테이블의 모든 영속 컬럼을 누락 없이 포함하며,
    Primary Key 기준 정렬 및 결정론적 직렬화를 통해 데이터의 절대적 불변성을 검증합니다.
    """
    from chaficial.models.vehicle_link import VehicleIdentityLink

    results = {}

    # 1. listings (전체 10개 영속 컬럼 전수 포함)
    listings = session.execute(select(Listing).order_by(Listing.listing_id)).scalars().all()
    l_rows = []
    for l in listings:
        l_row = (
            deterministic_serialize(l.listing_id),
            deterministic_serialize(l.source_platform),
            deterministic_serialize(l.source_listing_id),
            deterministic_serialize(l.vehicle_id),
            deterministic_serialize(l.seller_reference),
            deterministic_serialize(l.first_observed_at),
            deterministic_serialize(l.raw_location),
            deterministic_serialize(l.normalized_region_id),
            deterministic_serialize(l.current_status),
            deterministic_serialize(l.consecutive_missing_count),
        )
        l_rows.append("::".join(l_row))
    l_payload = "\n".join(l_rows)
    results["listings"] = {
        "count": len(listings),
        "hash": hashlib.sha256(l_payload.encode("utf-8")).hexdigest(),
    }

    # 2. listing_snapshots (전체 10개 영속 컬럼 전수 포함)
    snapshots = session.execute(select(ListingSnapshot).order_by(ListingSnapshot.snapshot_id)).scalars().all()
    s_rows = []
    for s in snapshots:
        s_row = (
            deterministic_serialize(s.snapshot_id),
            deterministic_serialize(s.listing_id),
            deterministic_serialize(s.observed_at),
            deterministic_serialize(s.ingested_at),
            deterministic_serialize(s.price_krw),
            deterministic_serialize(s.mileage_km),
            deterministic_serialize(s.listing_status),
            deterministic_serialize(s.normalized_region_id),
            deterministic_serialize(s.raw_specs),
            deterministic_serialize(s.source_record_hash),
        )
        s_rows.append("::".join(s_row))
    s_payload = "\n".join(s_rows)
    results["listing_snapshots"] = {
        "count": len(snapshots),
        "hash": hashlib.sha256(s_payload.encode("utf-8")).hexdigest(),
    }

    # 3. price_events (전체 19개 영속 컬럼 전수 포함)
    events = session.execute(select(PriceEvent).order_by(PriceEvent.event_id)).scalars().all()
    e_rows = []
    for e in events:
        e_row = (
            deterministic_serialize(e.event_id),
            deterministic_serialize(e.listing_id),
            deterministic_serialize(e.source_platform),
            deterministic_serialize(e.source_listing_id),
            deterministic_serialize(e.event_type),
            deterministic_serialize(e.event_timestamp),
            deterministic_serialize(e.previous_price_krw),
            deterministic_serialize(e.new_price_krw),
            deterministic_serialize(e.price_delta_krw),
            deterministic_serialize(e.price_delta_pct),
            deterministic_serialize(e.initial_price_krw),
            deterministic_serialize(e.cumulative_delta_krw),
            deterministic_serialize(e.cumulative_delta_pct),
            deterministic_serialize(e.mileage_at_event),
            deterministic_serialize(e.days_since_first_observed),
            deterministic_serialize(e.product_type),
            deterministic_serialize(e.data_origin),
            deterministic_serialize(e.is_anomaly),
            deterministic_serialize(e.notes),
        )
        e_rows.append("::".join(e_row))
    e_payload = "\n".join(e_rows)
    results["price_events"] = {
        "count": len(events),
        "hash": hashlib.sha256(e_payload.encode("utf-8")).hexdigest(),
    }

    # 4. vehicle_identity_links (전체 7개 영속 컬럼 전수 포함)
    links = session.execute(select(VehicleIdentityLink).order_by(VehicleIdentityLink.link_id)).scalars().all()
    k_rows = []
    for k in links:
        k_row = (
            deterministic_serialize(k.link_id),
            deterministic_serialize(k.source_listing_id),
            deterministic_serialize(k.target_listing_id),
            deterministic_serialize(k.vehicle_fingerprint),
            deterministic_serialize(k.confidence_grade),
            deterministic_serialize(k.link_basis),
            deterministic_serialize(k.created_at),
        )
        k_rows.append("::".join(k_row))
    k_payload = "\n".join(k_rows)
    results["vehicle_identity_links"] = {
        "count": len(links),
        "hash": hashlib.sha256(k_payload.encode("utf-8")).hexdigest(),
    }

    # 5. batch_audit_logs (전체 7개 영속 컬럼 전수 포함)
    batches = session.execute(select(BatchAuditLog).order_by(BatchAuditLog.batch_id)).scalars().all()
    b_rows = []
    for b in batches:
        b_row = (
            deterministic_serialize(b.batch_id),
            deterministic_serialize(b.source_platform),
            deterministic_serialize(b.search_scope),
            deterministic_serialize(b.processed_at),
            deterministic_serialize(b.record_count),
            deterministic_serialize(b.is_partial_scrape),
            deterministic_serialize(b.notes),
        )
        b_rows.append("::".join(b_row))
    b_payload = "\n".join(b_rows)
    results["batch_audit_logs"] = {
        "count": len(batches),
        "hash": hashlib.sha256(b_payload.encode("utf-8")).hexdigest(),
    }

    return results


class PriceEventTracker:
    """시계열 매물 가격 변동 추적기."""

    def __init__(self, consecutive_missing_threshold: int = 3):
        """
        Args:
            consecutive_missing_threshold: 판매 종료 의심(DELISTED_SUSPECT) 판정에 필요한 최소 연속 미관측 횟수.
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
        data_origin: str | None = None,
    ) -> PriceEvent | None:
        """단일 매물 관측 레코드를 수신하여 시계열 스냅샷 적재 및 가격 변동 이벤트 탐지."""
        obs_utc = self._to_utc(record.observed_at)
        effective_origin = data_origin or record.data_origin or "REAL_OBSERVED"

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
                consecutive_missing_count=0,
            )
            session.add(new_listing)
            session.flush()

            # 최초 스냅샷 생성 (가격 미확인 시 0원이 아닌 NULL로 보존!)
            snapshot = ListingSnapshot(
                listing_id=new_listing.listing_id,
                observed_at=obs_utc,
                price_krw=effective_price,
                mileage_km=record.mileage_km,
                listing_status="ACTIVE",
                raw_specs={
                    "manufacturer": record.manufacturer,
                    "model": record.model_name,
                    "sub_model": record.sub_model,
                    "model_year": record.model_year,
                    "product_type": record.product_type,
                    "monthly_payment": record.monthly_payment_krw,
                    "vehicle_fingerprint": record.vehicle_fingerprint,
                    "data_origin": effective_origin,
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
                data_origin=effective_origin,
                is_anomaly=(is_financial and record.price_krw is not None and record.price_krw <= 1_000_000),
                notes="신규 매물 최초 관측",
            )
            session.add(event)
            return event

        # B. 기존 매물의 재관측 처리
        existing_listing.consecutive_missing_count = 0  # 관측되었으므로 누락 카운터 초기화

        # 멱등성(Idempotency) 검증: 동일한 observed_at 시점에 동일한 스냅샷이 이미 존재하면 중복 이벤트 생성 방지
        exact_duplicate_snapshot = session.execute(
            select(ListingSnapshot).where(
                ListingSnapshot.listing_id == existing_listing.listing_id,
                ListingSnapshot.observed_at == obs_utc,
                ListingSnapshot.price_krw == effective_price,
                ListingSnapshot.mileage_km == record.mileage_km,
            )
        ).scalar_one_or_none()
        if exact_duplicate_snapshot is not None:
            return None

        # 최신 스냅샷 조회
        latest_snapshot = session.execute(
            select(ListingSnapshot)
            .where(ListingSnapshot.listing_id == existing_listing.listing_id)
            .order_by(ListingSnapshot.observed_at.desc())
        ).scalars().first()

        # 시간 역전 방지 (지연 입력 처리)
        latest_obs_utc = self._to_utc(latest_snapshot.observed_at) if latest_snapshot else None
        if latest_snapshot and latest_obs_utc and obs_utc < latest_obs_utc:
            out_of_order_snapshot = ListingSnapshot(
                listing_id=existing_listing.listing_id,
                observed_at=obs_utc,
                price_krw=effective_price,
                mileage_km=record.mileage_km,
                listing_status="ACTIVE",
                raw_specs={"note": "OUT_OF_ORDER_HISTORICAL_OBSERVATION"},
            )
            session.add(out_of_order_snapshot)
            return None

        # 최초 관측 스냅샷 (누적 변동 계산용)
        first_snapshot = session.execute(
            select(ListingSnapshot)
            .where(ListingSnapshot.listing_id == existing_listing.listing_id)
            .order_by(ListingSnapshot.observed_at.asc())
        ).scalars().first()

        initial_price = (
            first_snapshot.price_krw
            if (first_snapshot and first_snapshot.price_krw is not None and first_snapshot.price_krw > 0)
            else effective_price
        )

        prev_price = latest_snapshot.price_krw if latest_snapshot else None

        first_obs_utc = self._to_utc(existing_listing.first_observed_at)
        days_passed = max(0, (obs_utc.date() - first_obs_utc.date()).days)

        event: PriceEvent | None = None

        # DELISTED 또는 DELISTED_SUSPECT 상태였다가 재등장한 경우 (RE_LISTED_SUSPECT)
        if existing_listing.current_status in ("DELISTED", "DELISTED_SUSPECT"):
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
                data_origin=effective_origin,
                notes="비노출 처리되었던 매물의 재등록 관측",
            )
            session.add(event)

        # 가격 변동 탐지 (유효 현금 매매가가 둘 다 존재하고 다를 때만)
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
                data_origin=effective_origin,
                notes=note_str,
            )
            session.add(event)

        # 새로운 상태 스냅샷 저장 (Append-only 불변성 유지, NULL 가격 안전 저장)
        new_snapshot = ListingSnapshot(
            listing_id=existing_listing.listing_id,
            observed_at=obs_utc,
            price_krw=effective_price,
            mileage_km=record.mileage_km,
            listing_status=existing_listing.current_status,
            raw_specs={
                "manufacturer": record.manufacturer,
                "model": record.model_name,
                "sub_model": record.sub_model,
                "model_year": record.model_year,
                "product_type": record.product_type,
                "monthly_payment": record.monthly_payment_krw,
                "vehicle_fingerprint": record.vehicle_fingerprint,
                "data_origin": effective_origin,
            },
        )
        session.add(new_snapshot)

        return event

    def process_batch(
        self,
        records: list[StandardListingRecord],
        session: Session,
        observation_time: datetime | None = None,
        data_origin: str | None = None,
    ) -> list[PriceEvent]:
        """관측 배치 전수 처리 및 가격 변동 이벤트 목록 반환."""
        events: list[PriceEvent] = []
        for rec in records:
            if observation_time and not rec.observed_at:
                rec.observed_at = observation_time
            ev = self.process_observation(rec, session, data_origin=data_origin)
            if ev is not None:
                events.append(ev)

        session.commit()
        return events

    def process_missing_listings(
        self,
        observed_source_listing_ids: set[str],
        session: Session,
        observation_time: datetime,
        batch_id: str,
        scope: SearchScopeSpec | str | None = None,
        search_scope: SearchScopeSpec | str | None = None,
        platform: str = "ENCAR",
        is_partial_scrape: bool = False,
        search_scope_success: bool = True,
        data_origin: str = "REAL_OBSERVED",
        notes: str | None = None,
    ) -> list[PriceEvent]:
        """검색 범위(플랫폼 및 차종/검색조건) 내에서 관측되지 않은 활성 매물의 누락 횟수를 갱신하고
        연속 3회 누락 시 DELISTED_SUSPECT 상태로 안전 전이합니다.

        1. 배치 ID 필수화: batch_id가 누락되거나 빈 문자열이면 명시적인 ValueError를 발생시킵니다.
        2. 수집 실패(search_scope_success=False) 또는 부분 수집(is_partial_scrape=True) 시에는
           절대 누락 카운터를 증가시키지 않습니다.
        3. 고유 batch_id를 통해 동일 배치의 중복 호출/재시도 시 멱등성을 보장합니다.
        4. 구조화된 SearchScopeSpec을 통해 해당 검색 범위에 속하는 매물만 대상으로 한정하여 교차 오판을 방지합니다.
        """
        # 1. 배치 ID 필수성 강제
        if not batch_id or not batch_id.strip():
            raise ValueError("batch_id is strictly required for production missing listing processing.")

        # 2. scope 사양 정규화
        target_scope = scope or search_scope or "ALL"
        if isinstance(target_scope, str):
            scope_spec = SearchScopeSpec(platform=platform, model_name=target_scope)
        else:
            scope_spec = target_scope
            platform = scope_spec.platform

        # 3. 수집 실패 또는 부분 수집 차단
        if not search_scope_success or is_partial_scrape:
            return []

        obs_time_utc = self._to_utc(observation_time)

        # 4. 배치 중복 멱등성 검사: 이미 처리된 batch_id는 재실행되어도 카운터를 다시 올리지 않음
        existing_batch = session.execute(
            select(BatchAuditLog).where(BatchAuditLog.batch_id == batch_id)
        ).scalar_one_or_none()
        if existing_batch is not None:
            return []

        # 5. 해당 플랫폼 및 검색 범위에 속한 활성 매물만 필터링 (교차 오판 방지)
        query = select(Listing).where(
            Listing.source_platform == platform,
            Listing.current_status.in_(("ACTIVE", "PRICE_CHANGED")),
        )
        active_listings = session.execute(query).scalars().all()

        events: list[PriceEvent] = []
        for l in active_listings:
            # 검색 범위(SearchScopeSpec) 구조적 매칭 검증
            if scope_spec.model_name and scope_spec.model_name != "ALL":
                snaps = session.execute(
                    select(ListingSnapshot)
                    .where(ListingSnapshot.listing_id == l.listing_id)
                    .order_by(ListingSnapshot.observed_at.desc())
                ).scalars().all()
                matched = False
                for snap in snaps:
                    if snap.raw_specs and scope_spec.matches_specs(snap.raw_specs):
                        matched = True
                        break
                if not matched:
                    continue

            if l.source_listing_id not in observed_source_listing_ids:
                l.consecutive_missing_count += 1
                if l.consecutive_missing_count >= self.consecutive_missing_threshold:
                    l.current_status = "DELISTED_SUSPECT"
                    first_obs = self._to_utc(l.first_observed_at)
                    days_passed = max(0, (obs_time_utc.date() - first_obs.date()).days)
                    ev = PriceEvent(
                        listing_id=l.listing_id,
                        source_platform=l.source_platform,
                        source_listing_id=l.source_listing_id,
                        event_type="DELISTED_SUSPECT",
                        event_timestamp=obs_time_utc,
                        previous_price_krw=None,
                        new_price_krw=None,
                        price_delta_krw=0,
                        price_delta_pct=0.0,
                        initial_price_krw=None,
                        cumulative_delta_krw=0,
                        cumulative_delta_pct=0.0,
                        mileage_at_event=0,
                        days_since_first_observed=days_passed,
                        data_origin=data_origin,
                        notes=f"연속 {l.consecutive_missing_count}회 미관측으로 판매 종료 의심(DELISTED_SUSPECT) 판정 (범위: {scope_spec.to_scope_key()})",
                    )
                    session.add(ev)
                    events.append(ev)
            else:
                l.consecutive_missing_count = 0

        # 6. 배치 처리 이력 영속 기록 (멱등성 보장용)
        audit_log = BatchAuditLog(
            batch_id=batch_id,
            source_platform=platform,
            search_scope=scope_spec.to_scope_key(),
            processed_at=obs_time_utc,
            record_count=len(observed_source_listing_ids),
            is_partial_scrape=is_partial_scrape,
            notes=notes,
        )
        session.add(audit_log)

        session.commit()
        return events

    @staticmethod
    def get_price_drops_summary(
        session: Session,
        window_days: int = 7,
        data_origin: str | None = None,
    ) -> list[dict[str, Any]]:
        """최근 N일간 발생한 가격 인하(PRICE_DROP) 이벤트 집계 (실제 관측 vs 시뮬레이션 분리)."""
        now = datetime.now(UTC)
        since_time = now - timedelta(days=window_days)

        query = select(PriceEvent).where(
            PriceEvent.event_type == "PRICE_DROP",
            PriceEvent.event_timestamp >= since_time,
        )
        if data_origin:
            query = query.where(PriceEvent.data_origin == data_origin)

        events = session.execute(
            query.order_by(PriceEvent.price_delta_krw.asc())
        ).scalars().all()

        results = []
        for ev in events:
            results.append({
                "event_id": ev.event_id,
                "listing_id": ev.source_listing_id,
                "platform": ev.source_platform,
                "data_origin": ev.data_origin,
                "previous_price_krw": ev.previous_price_krw,
                "new_price_krw": ev.new_price_krw,
                "price_drop_krw": abs(ev.price_delta_krw),
                "price_drop_pct": abs(ev.price_delta_pct),
                "days_since_first_observed": ev.days_since_first_observed,
                "event_timestamp": ev.event_timestamp.isoformat(),
                "notes": ev.notes,
            })
        return results
