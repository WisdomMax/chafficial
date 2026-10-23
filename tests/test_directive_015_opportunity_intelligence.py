"""차피셜 기회 매물 탐지 엔진 V1.1 회귀 및 무결성 테스트 (DIRECTIVE 015-A)."""

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


def test_missing_year_blocked_from_priority_review(test_db_session):
    """지침 1 (015-A): 연식이 NOYEAR이거나 미확인된 매물은 우선 추천(PRIORITY_REVIEW)에서 원천 차단 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        # 정상 시세 매물 4대 (2024년식, 2,000만원)
        specs_2024 = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "model_year": "2024",
            "vehicle_fingerprint": "현대_아반떼_CN7_FACELIFT_STANDARD_2023-09_2024_30000_가솔린_모던",
        })
        for i in range(1, 5):
            l = Listing(listing_id=f"peer-{i}", source_platform="ENCAR", source_listing_id=f"20{i}", raw_location="서울")
            s = ListingSnapshot(snapshot_id=f"ps-{i}", listing_id=f"peer-{i}", price_krw=20000000, mileage_km=30000, raw_specs=specs_2024, observed_at=datetime(2026, 10, 22))
            session.add_all([l, s])

        # 연식이 NOYEAR인 매물 (가격이 1,500만원으로 매우 저렴하더라도 연식 미확인으로 우선 추천 보류되어야 함)
        specs_noyear = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "model_year": "",
            "vehicle_fingerprint": "현대_아반떼_CN7_FACELIFT_STANDARD_2025-04_NOYEAR_38185_가솔린_모던",
        })
        l_target = Listing(listing_id="target-noyear", source_platform="ENCAR", source_listing_id="999", raw_location="서울")
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
    """지침 2 (015-A): 동일 실차 중복 광고가 코호트 중앙값을 이중 왜곡하지 않도록 단일 표본만 반영 검증."""
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

        # Car A: 2,000만원
        # Car B: 2,500만원 매물인데 딜러가 3개 ID로 중복 등록함 (2,500만 3건)
        # Car C: 3,000만원
        # 만약 Car B가 3번 반영되면 표본 [2000, 2500, 2500, 2500, 3000]이 되어 Car A 입장에서 중앙값이 2,500만이 됨.
        # 동일 실차 지문이 1건으로 정제되면 [2500, 3000] 중앙값 2,750만 (또는 B 1건만 반영)이 됨.
        la = Listing(listing_id="la", source_platform="ENCAR", source_listing_id="1", raw_location="서울")
        sa = ListingSnapshot(snapshot_id="sa", listing_id="la", price_krw=20000000, mileage_km=30000, raw_specs=specs_car_a, observed_at=datetime(2026, 10, 22))

        lb1 = Listing(listing_id="lb1", source_platform="ENCAR", source_listing_id="2-1", raw_location="서울")
        sb1 = ListingSnapshot(snapshot_id="sb1", listing_id="lb1", price_krw=25000000, mileage_km=30000, raw_specs=specs_car_b, observed_at=datetime(2026, 10, 22))

        lb2 = Listing(listing_id="lb2", source_platform="ENCAR", source_listing_id="2-2", raw_location="서울")
        sb2 = ListingSnapshot(snapshot_id="sb2", listing_id="lb2", price_krw=25000000, mileage_km=30000, raw_specs=specs_car_b, observed_at=datetime(2026, 10, 22))

        lc = Listing(listing_id="lc", source_platform="ENCAR", source_listing_id="3", raw_location="서울")
        sc = ListingSnapshot(snapshot_id="sc", listing_id="lc", price_krw=30000000, mileage_km=30000, raw_specs=specs_car_c, observed_at=datetime(2026, 10, 22))

        session.add_all([la, sa, lb1, sb1, lb2, sb2, lc, sc])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    cand_a = next(c for c in candidates if c.listing_id == "la")
    # 중복 등록된 Car B(lb1, lb2)는 코호트 표본군에서 1건으로 대표 처리되어 Car A 입장의 독립 비교 표본 수는 B 1대 + C 1대 = 2대여야 함!
    assert cand_a.sample_count == 2
    # 또한 추천 목록에도 Car B는 1건만 등록되고 중복 플래그가 설정되어야 함
    cand_b = next((c for c in candidates if c.vehicle_fingerprint == "CAR_B_FINGERPRINT"), None)
    assert cand_b is not None
    assert cand_b.is_duplicate_listing
    assert len(cand_b.duplicate_listing_ids) == 1


def test_profit_scenario_separates_net_profit_and_target_margin():
    """지침 3 (015-A): 순수익(Net Profit)과 목표마진(Target Margin)의 수학적 분리 검증."""
    engine = MarketOpportunityEngine()
    scenario = engine._calc_scenario(
        purchase_price=16_900_000,
        expected_sale_price=22_350_000,
        is_remote=False,
        scenario_type="BASE",
    )

    # 1. 예상 총마진: 22,350,000 - 16,900,000 = 5,450,000원
    assert scenario.estimated_gross_spread_krw == 5_450_000

    # 2. 실제 운영비용 (상품화 80만 + 탁송 30만) = 1,100,000원
    assert scenario.estimated_operating_cost_krw == 1_100_000

    # 3. 실제 예상 순이익 = 5,450,000 - 1,100,000 = 4,350,000원
    assert scenario.estimated_net_profit_krw == 4_350_000

    # 4. 목표 마진: 500,000원 (비용이 아닌 기준치)
    assert scenario.target_margin_krw == 500_000

    # 5. 목표 마진 초과 달성분: 4,350,000 - 500,000 = 3,850,000원
    assert scenario.excess_over_target_krw == 3_850_000


def test_as_of_time_prevents_future_data_leakage(test_db_session):
    """지침 4 (015-A): as_of_time 시점 제한이 적용되어 미래 데이터가 과거 시점 평가에 누수되지 않는지 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        specs_2024 = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "model_year": "2024",
            "vehicle_fingerprint": "현대_아반떼_CN7_FACELIFT_STANDARD_2023-09_2024_30000_가솔린_모던",
        })
        # 10월 20일 시점에 등록된 매물
        l = Listing(listing_id="leak-test-1", source_platform="ENCAR", source_listing_id="901", raw_location="서울", first_observed_at=datetime(2026, 10, 20))
        s_past = ListingSnapshot(snapshot_id="snap-past", listing_id="leak-test-1", price_krw=20000000, mileage_km=30000, raw_specs=specs_2024, observed_at=datetime(2026, 10, 20))

        # 10월 25일에 미래에 관측될 스냅샷 (가격이 1,500만원으로 대폭 하락)
        s_future = ListingSnapshot(snapshot_id="snap-future", listing_id="leak-test-1", price_krw=15000000, mileage_km=30000, raw_specs=specs_2024, observed_at=datetime(2026, 10, 25))

        # 10월 25일에 미래에 발생할 가격 인하 이벤트
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

    # 1. 10월 21일 과거 시점 기준으로 평가 실행
    past_candidates = engine.evaluate_market_opportunities(
        db_path=db_file, as_of_time=datetime(2026, 10, 21, 0, 0, 0)
    )
    assert len(past_candidates) == 1
    past_cand = past_candidates[0]
    # 과거 시점에서는 미래의 1,500만원 스냅샷과 가격 인하 이벤트가 절대 보이지 않아야 함!
    assert past_cand.current_price_krw == 20000000
    assert not past_cand.has_price_drop
    assert past_cand.cumulative_price_drop_krw == 0
    assert past_cand.observation_count == 1

    # 2. 10월 26일 현재 시점 기준으로 평가 실행
    current_candidates = engine.evaluate_market_opportunities(
        db_path=db_file, as_of_time=datetime(2026, 10, 26, 0, 0, 0)
    )
    current_cand = current_candidates[0]
    # 현재 시점에서는 1,500만원 스냅샷과 가격 인하가 정상 반영됨
    assert current_cand.current_price_krw == 15000000
    assert current_cand.has_price_drop
    assert current_cand.cumulative_price_drop_krw == 5000000
    assert current_cand.observation_count == 2


def test_partner_suitability_separated_from_market_grade(test_db_session):
    """지침 5 (015-A): 시장 기회 등급과 파트너 영업 적합성이 독립된 필드로 분리되었는지 검증."""
    engine_obj, db_file = test_db_session

    with Session(engine_obj) as session:
        specs = json.dumps({
            "manufacturer": "현대",
            "model": "아반떼",
            "model_year": "2024",
            "vehicle_fingerprint": "현대_아반떼_CN7_FACELIFT_STANDARD_2023-09_2024_30000_가솔린_모던",
        })
        # 지역이 대구인 원거리 매물
        l = Listing(listing_id="remote-1", source_platform="ENCAR", source_listing_id="501", raw_location="대구")
        s = ListingSnapshot(snapshot_id="rs-1", listing_id="remote-1", price_krw=18000000, mileage_km=30000, raw_specs=specs, observed_at=datetime(2026, 10, 22))
        session.add_all([l, s])
        session.commit()

    engine = MarketOpportunityEngine(config=OpportunityEngineConfig(db_path=db_file))
    candidates = engine.evaluate_market_opportunities(db_path=db_file)

    cand = candidates[0]
    # 파트너 영업 적합성 필드가 분리되어 관리됨
    assert cand.partner_operational_suitability == "REMOTE_REGION_UNSUITABLE"
    assert cand.raw_location == "대구"
    assert any("원거리 지역(대구)" in r for r in cand.risk_factors)
