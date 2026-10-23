"""차피셜 기회 매물 탐지 엔진 V1.2 회귀 및 무결성 테스트 (DIRECTIVE 015-B)."""

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


def test_same_timestamp_snapshots_returns_exactly_single_row(test_db_session):
    """지침 1 (015-B): 동일 시각 스냅샷이 복수 개 존재해도 CTE ROW_NUMBER()에 의해 매물당 정확히 1행만 반환되는지 검증."""
    engine_obj, db_file = test_db_session

    same_time = datetime(2026, 10, 22, 12, 0, 0)
    specs = json.dumps({
        "manufacturer": "현대",
        "model": "아반떼",
        "model_year": "2024",
        "vehicle_fingerprint": "현대_아반떼_CN7_FACELIFT_STANDARD_2023-09_2024_30000_가솔린_모던",
    })

    with Session(engine_obj) as session:
        l = Listing(listing_id="same-time-list", source_platform="ENCAR", source_listing_id="111", raw_location="서울", first_observed_at=same_time)
        # 동일한 observed_at을 갖는 서로 다른 snapshot_id 2개 주입 (타이브레이커 snap-b가 우선 선택되어야 함)
        s1 = ListingSnapshot(snapshot_id="snap-a", listing_id="same-time-list", price_krw=20000000, mileage_km=30000, raw_specs=specs, observed_at=same_time)
        s2 = ListingSnapshot(snapshot_id="snap-b", listing_id="same-time-list", price_krw=19500000, mileage_km=30000, raw_specs=specs, observed_at=same_time)
        session.add_all([l, s1, s2])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    # 동일 시각 스냅샷 2개임에도 중복 없이 정확히 1건의 후보만 반환되어야 함
    assert len(candidates) == 1
    assert candidates[0].listing_id == "same-time-list"
    # ORDER BY observed_at DESC, snapshot_id DESC 타이브레이커에 따라 snap-b의 가격(19,500,000)이 결정적으로 선택되어야 함
    assert candidates[0].current_price_krw == 19500000


def test_missing_year_blocked_from_priority_review(test_db_session):
    """지침 1 (015-A): 연식이 NOYEAR이거나 미확인된 매물은 우선 추천(PRIORITY_REVIEW)에서 원천 차단 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        specs_2024 = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "model_year": "2024",
            "vehicle_fingerprint": "현대_아반떼_CN7_FACELIFT_STANDARD_2023-09_2024_30000_가솔린_모던",
        })
        for i in range(1, 5):
            l = Listing(listing_id=f"peer-{i}", source_platform="ENCAR", source_listing_id=f"20{i}", raw_location="서울", first_observed_at=datetime(2026, 10, 22))
            s = ListingSnapshot(snapshot_id=f"ps-{i}", listing_id=f"peer-{i}", price_krw=20000000, mileage_km=30000, raw_specs=specs_2024, observed_at=datetime(2026, 10, 22))
            session.add_all([l, s])

        specs_noyear = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "model_year": "",
            "vehicle_fingerprint": "현대_아반떼_CN7_FACELIFT_STANDARD_2025-04_NOYEAR_38185_가솔린_모던",
        })
        l_target = Listing(listing_id="target-noyear", source_platform="ENCAR", source_listing_id="999", raw_location="서울", first_observed_at=datetime(2026, 10, 22))
        s_target = ListingSnapshot(snapshot_id="ts-1", listing_id="target-noyear", price_krw=15000000, mileage_km=30000, raw_specs=specs_noyear, observed_at=datetime(2026, 10, 22))
        session.add_all([l_target, s_target])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    target_cand = next(c for c in candidates if c.listing_id == "target-noyear")
    assert target_cand.model_year is None
    assert target_cand.market_opportunity_grade == "INSUFFICIENT_DATA"
    assert any("연식 정보 미확인" in r for r in target_cand.risk_factors)


def test_duplicate_fingerprint_does_not_distort_cohort_median(test_db_session):
    """지침 2 (015-B): 동일 실차 중복 광고가 POSSIBLE_DUPLICATE로 관리되고 코호트 중앙값을 이중 왜곡하지 않음 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        specs_car_a = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "model_year": "2024",
            "vehicle_fingerprint": "CAR_A_FINGERPRINT",
        })
        specs_car_b = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "model_year": "2024",
            "vehicle_fingerprint": "CAR_B_FINGERPRINT",
        })
        specs_car_c = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "model_year": "2024",
            "vehicle_fingerprint": "CAR_C_FINGERPRINT",
        })

        la = Listing(listing_id="la", source_platform="ENCAR", source_listing_id="1", raw_location="서울", first_observed_at=datetime(2026, 10, 22))
        sa = ListingSnapshot(snapshot_id="sa", listing_id="la", price_krw=20000000, mileage_km=30000, raw_specs=specs_car_a, observed_at=datetime(2026, 10, 22))

        lb1 = Listing(listing_id="lb1", source_platform="ENCAR", source_listing_id="2-1", raw_location="서울", first_observed_at=datetime(2026, 10, 22))
        sb1 = ListingSnapshot(snapshot_id="sb1", listing_id="lb1", price_krw=25000000, mileage_km=30000, raw_specs=specs_car_b, observed_at=datetime(2026, 10, 22))

        lb2 = Listing(listing_id="lb2", source_platform="ENCAR", source_listing_id="2-2", raw_location="서울", first_observed_at=datetime(2026, 10, 22))
        sb2 = ListingSnapshot(snapshot_id="sb2", listing_id="lb2", price_krw=25000000, mileage_km=30000, raw_specs=specs_car_b, observed_at=datetime(2026, 10, 22))

        lc = Listing(listing_id="lc", source_platform="ENCAR", source_listing_id="3", raw_location="서울", first_observed_at=datetime(2026, 10, 22))
        sc = ListingSnapshot(snapshot_id="sc", listing_id="lc", price_krw=30000000, mileage_km=30000, raw_specs=specs_car_c, observed_at=datetime(2026, 10, 22))

        session.add_all([la, sa, lb1, sb1, lb2, sb2, lc, sc])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    cand_a = next(c for c in candidates if c.listing_id == "la")
    assert cand_a.sample_count == 2

    cand_b = next((c for c in candidates if c.vehicle_fingerprint == "CAR_B_FINGERPRINT"), None)
    assert cand_b is not None
    assert cand_b.duplicate_status == "POSSIBLE_DUPLICATE"
    assert len(cand_b.duplicate_listing_ids) == 1


def test_profit_scenario_separates_net_profit_and_target_margin():
    """지침 3 (015-B): 가정 기반 순수익(Hypothetical Net Profit)과 목표마진(Target Margin)의 분리 검증."""
    engine = MarketOpportunityEngine()
    scenario = engine._calc_scenario(
        purchase_price=16_900_000,
        expected_sale_price=22_350_000,
        is_remote=False,
        scenario_type="BASE",
    )

    # 1. 가정 총마진: 22,350,000 - 16,900,000 = 5,450,000원
    assert scenario.hypothetical_gross_spread_krw == 5_450_000

    # 2. 실제 운영비용 (상품화 80만 + 탁송 30만) = 1,100,000원
    assert scenario.hypothetical_operating_cost_krw == 1_100_000

    # 3. 가정 순이익 = 5,450,000 - 1,100,000 = 4,350,000원
    assert scenario.hypothetical_net_profit_krw == 4_350_000

    # 4. 목표 마진: 500,000원
    assert scenario.target_margin_krw == 500_000

    # 5. 목표 마진 초과 달성분: 4,350,000 - 500,000 = 3,850,000원
    assert scenario.excess_over_target_krw == 3_850_000
    assert "미반영 가정치" in scenario.unreflected_costs_note


def test_as_of_time_prevents_future_data_leakage(test_db_session):
    """지침 4 (015-B): as_of_time 시점 제한이 적용되어 미래 데이터가 과거 시점 평가에 누수되지 않는지 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        specs_2024 = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "model_year": "2024",
            "vehicle_fingerprint": "현대_아반떼_CN7_FACELIFT_STANDARD_2023-09_2024_30000_가솔린_모던",
        })
        l = Listing(listing_id="leak-test-1", source_platform="ENCAR", source_listing_id="901", raw_location="서울", first_observed_at=datetime(2026, 10, 20))
        s_past = ListingSnapshot(snapshot_id="snap-past", listing_id="leak-test-1", price_krw=20000000, mileage_km=30000, raw_specs=specs_2024, observed_at=datetime(2026, 10, 20))
        s_future = ListingSnapshot(snapshot_id="snap-future", listing_id="leak-test-1", price_krw=15000000, mileage_km=30000, raw_specs=specs_2024, observed_at=datetime(2026, 10, 25))

        ev_future = PriceEvent(
            event_id="ev-future",
            listing_id="leak-test-1",
            source_platform="ENCAR",
            source_listing_id="901",
            event_type="PRICE_DROP",
            previous_price_krw=20000000,
            new_price_krw=15000000,
            price_delta_krw=-5000000,
            price_delta_pct=-25.0,
            event_timestamp=datetime(2026, 10, 25),
            detected_at=datetime(2026, 10, 25),
        )

        session.add_all([l, s_past, s_future, ev_future])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))

    # 1. 10월 21일 과거 시점 기준 평가
    past_candidates = engine.evaluate_market_opportunities(
        db_path=db_file, as_of_time=datetime(2026, 10, 21, 0, 0, 0)
    )
    assert len(past_candidates) == 1
    past_cand = past_candidates[0]
    assert past_cand.current_price_krw == 20000000
    assert not past_cand.has_price_drop
    assert past_cand.cumulative_price_drop_krw == 0

    # 2. 10월 26일 현재 시점 기준 평가
    current_candidates = engine.evaluate_market_opportunities(
        db_path=db_file, as_of_time=datetime(2026, 10, 26, 0, 0, 0)
    )
    current_cand = current_candidates[0]
    assert current_cand.current_price_krw == 15000000
    assert current_cand.has_price_drop
    assert current_cand.cumulative_price_drop_krw == 5000000
