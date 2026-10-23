"""차피셜 기회 매물 탐지 엔진 V1 회귀 및 무결성 테스트 (DIRECTIVE 015)."""

from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
import pytest

from chaficial.database.base import Base
from chaficial.intelligence.config import CostAssumptions, OpportunityEngineConfig
from chaficial.intelligence.opportunity_engine import (
    MarketOpportunityEngine,
    OpportunityCandidate,
    ProfitScenario,
)
from chaficial.models import BatchAuditLog, Listing, ListingSnapshot, PriceEvent
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def test_db_session(tmp_path):
    """격리된 테스트 더블 데이터베이스 세션 생성."""
    db_file = tmp_path / "test_opportunity.db"
    db_file.touch()
    engine = create_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(engine)
    return engine, db_file


def test_no_duplicate_listings_in_recommendations(test_db_session):
    """지침 4: 동일 매물이 추천 목록에 중복으로 포함되지 않는지 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        # 매물 1개 생성
        l1 = Listing(
            listing_id="list-001",
            source_platform="ENCAR",
            source_listing_id="40001",
            raw_location="서울",
            current_status="ACTIVE",
        )
        session.add(l1)

        # 동일 매물에 대해 3개의 서로 다른 시점 스냅샷 추가
        specs = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "vehicle_fingerprint": "현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2021-01_2021_30000_가솔린_모던",
        })
        s1 = ListingSnapshot(
            snapshot_id="snap-1", listing_id="list-001", price_krw=17000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 20)
        )
        s2 = ListingSnapshot(
            snapshot_id="snap-2", listing_id="list-001", price_krw=16500000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 21)
        )
        s3 = ListingSnapshot(
            snapshot_id="snap-3", listing_id="list-001", price_krw=16000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 22)
        )
        session.add_all([s1, s2, s3])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    # 매물 1개이므로 결과도 정확히 1개여야 함 (스냅샷 3개라고 3개 추천되지 않음)
    assert len(candidates) == 1
    assert candidates[0].listing_id == "list-001"
    assert candidates[0].current_price_krw == 16000000  # 최신 스냅샷 가격 반영
    assert candidates[0].observation_count == 3


def test_snapshots_not_counted_as_independent_peers(test_db_session):
    """지침 4: 동일 차량의 과거 여러 스냅샷이 독립 비교 매물(peer)로 중복 집계되지 않는지 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        specs = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "vehicle_fingerprint": "현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2021-01_2021_30000_가솔린_모던",
        })
        # 매물 A (스냅샷 3개)
        la = Listing(listing_id="list-A", source_platform="ENCAR", source_listing_id="101", raw_location="서울")
        sa1 = ListingSnapshot(snapshot_id="sa-1", listing_id="list-A", price_krw=17000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 20))
        sa2 = ListingSnapshot(snapshot_id="sa-2", listing_id="list-A", price_krw=16500000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 21))
        sa3 = ListingSnapshot(snapshot_id="sa-3", listing_id="list-A", price_krw=16000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 22))

        # 매물 B (스냅샷 1개)
        lb = Listing(listing_id="list-B", source_platform="ENCAR", source_listing_id="102", raw_location="서울")
        sb1 = ListingSnapshot(snapshot_id="sb-1", listing_id="list-B", price_krw=16200000, mileage_km=32000, raw_specs=specs, observed_at=datetime(2026, 10, 22))

        session.add_all([la, sa1, sa2, sa3, lb, sb1])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    # A 입장에서 비교 표본 수는 B 1개뿐이어야 함 (A의 과거 스냅샷 sa1, sa2가 비교군으로 들어가면 안 됨)
    cand_a = next(c for c in candidates if c.listing_id == "list-A")
    assert cand_a.sample_count == 1  # 오직 B 1대만 독립 비교군으로 집계
    assert cand_a.data_confidence == "LOW"
    assert cand_a.recommendation_category == "INSUFFICIENT_DATA"  # 표본 3개 미만이므로 보류


def test_overpriced_car_with_price_drop_not_overrated(test_db_session):
    """지침 4: 가격 인하 폭이 크더라도 여전히 시세보다 비싼 매물은 과대평가 방지(EXCLUDED 처리) 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        specs = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "vehicle_fingerprint": "현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2021-01_2021_30000_가솔린_모던",
        })
        # 정상 시세 매물 4대 (약 1,500만원)
        for i in range(1, 5):
            l = Listing(listing_id=f"peer-{i}", source_platform="ENCAR", source_listing_id=f"20{i}", raw_location="서울")
            s = ListingSnapshot(snapshot_id=f"ps-{i}", listing_id=f"peer-{i}", price_krw=15000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 22))
            session.add_all([l, s])

        # 원래 2,200만원에 등록했다가 300만원 대폭 인하하여 1,900만원인 매물 (여전히 시세 1,500만 대비 +26% 비쌈)
        target = Listing(listing_id="overpriced-target", source_platform="ENCAR", source_listing_id="999", raw_location="서울")
        ts = ListingSnapshot(snapshot_id="ts-1", listing_id="overpriced-target", price_krw=19000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 22))
        ev = PriceEvent(
            event_id="ev-1",
            listing_id="overpriced-target",
            source_platform="ENCAR",
            source_listing_id="999",
            event_type="PRICE_DROP",
            previous_price_krw=22000000,
            new_price_krw=19000000,
            price_delta_krw=-3000000,
            price_delta_pct=-13.64,
            event_timestamp=datetime(2026, 10, 22),
            detected_at=datetime(2026, 10, 22),
        )
        session.add_all([target, ts, ev])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    target_cand = next(c for c in candidates if c.listing_id == "overpriced-target")
    # 300만원(13.6%)이나 인하되었지만 시세 대비 26.7% 비싸므로 EXCLUDED 되어야 함
    assert target_cand.relative_price_gap_pct < 0
    assert target_cand.recommendation_category == "EXCLUDED"
    assert any("고가" in r for r in target_cand.risk_factors)


def test_cheap_car_without_price_drop_can_be_recommended(test_db_session):
    """지침 4: 가격 인하가 없더라도 시세 대비 충분히 저렴하면 PRIORITY_REVIEW 추천 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        specs = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "vehicle_fingerprint": "현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2021-01_2021_30000_가솔린_모던",
        })
        # 시세 매물 4대 (2,000만원)
        for i in range(1, 5):
            l = Listing(listing_id=f"peer-{i}", source_platform="ENCAR", source_listing_id=f"30{i}", raw_location="서울")
            s = ListingSnapshot(snapshot_id=f"ps-{i}", listing_id=f"peer-{i}", price_krw=20000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 22))
            session.add_all([l, s])

        # 가격 인하 이력은 전혀 없지만 애초에 1,600만원에 등록된 알짜 매물 (시세 대비 20% 저렴)
        target = Listing(listing_id="cheap-target", source_platform="ENCAR", source_listing_id="888", raw_location="서울")
        ts = ListingSnapshot(snapshot_id="ts-1", listing_id="cheap-target", price_krw=16000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 22))
        session.add_all([target, ts])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    target_cand = next(c for c in candidates if c.listing_id == "cheap-target")
    assert not target_cand.has_price_drop
    assert target_cand.relative_price_gap_pct == 20.0  # 20% 저렴
    assert target_cand.recommendation_category == "PRIORITY_REVIEW"
    assert target_cand.base_scenario.net_profit_krw > 0


def test_region_unknown_does_not_falsely_claim_janganpyeong(test_db_session):
    """지침 1.3: 지역 정보가 UNKNOWN인 매물은 서울 장안평 매물로 왜곡하지 않고 REGION_UNVERIFIED로 표기 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        specs = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "vehicle_fingerprint": "현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2021-01_2021_30000_가솔린_모던",
        })
        l = Listing(listing_id="unk-1", source_platform="ENCAR", source_listing_id="777", raw_location="UNKNOWN")
        s = ListingSnapshot(snapshot_id="us-1", listing_id="unk-1", price_krw=18000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 22))
        session.add_all([l, s])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    cand = candidates[0]
    assert cand.raw_location == "UNKNOWN"
    assert cand.region_suitability == "REGION_UNVERIFIED"
    assert any("지역 정보 미확인" in r for r in cand.risk_factors)


def test_financial_product_rent_lease_excluded(test_db_session):
    """지침 2: 렌트/리스 등 금융 상품 매물은 무조건 EXCLUDED 처리 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        specs = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "product_type": "LEASE_OR_RENT",
            "vehicle_fingerprint": "현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2021-01_2021_30000_가솔린_모던",
        })
        l = Listing(listing_id="lease-1", source_platform="ENCAR", source_listing_id="666", raw_location="서울")
        s = ListingSnapshot(snapshot_id="ls-1", listing_id="lease-1", price_krw=10000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 22))
        session.add_all([l, s])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    cand = candidates[0]
    assert cand.recommendation_category == "EXCLUDED"
    assert "FINANCIAL_PRODUCT" in cand.risk_factors
