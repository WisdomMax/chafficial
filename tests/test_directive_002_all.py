"""DIRECTIVE 002 필수 테스트 20선 및 무결성 제약 검증.

한국형 중고차 시장 데이터 엔진 V0.1의 모든 요구사항을 철저히 검증합니다.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from chaficial.models import (
    DataSourcePermission,
    Listing,
    ListingSnapshot,
    MarketingResult,
    PromotionDecision,
    SalesCandidate,
    SalesOutcome,
    SalesPartner,
    Settlement,
    VehicleCatalog,
    VehicleCondition,
    VehicleIdentity,
    VehicleOption,
)
from chaficial.regions.manager import RegionManager
from chaficial.time_travel.query_engine import TimeTravelQueryEngine


@pytest.fixture(autouse=True)
def setup_default_regions(db_session):
    """모든 테스트 실행 전 기본 지역 데이터를 시딩하여 외래키 무결성을 보장합니다."""
    reg_mgr = RegionManager()
    reg_mgr.seed_default_regions(db_session)


def _create_test_listing_and_candidate(db_session, source_id="TEST-LST", region_id="REGION_JANGANPYEONG"):
    """테스트용 기본 매물 및 후보 객체 생성 헬퍼 함수."""
    listing = Listing(
        source_platform="DEALER_DIRECT",
        source_listing_id=source_id,
        raw_location="서울 동대문구 장안동 장안평 매매단지",
        normalized_region_id=region_id,
        current_status="ACTIVE",
    )
    db_session.add(listing)
    db_session.flush()

    candidate = SalesCandidate(
        listing_id=listing.listing_id,
        target_region_id=region_id,
        selection_reason="테스트 후보 매물",
        availability_status="AVAILABLE",
    )
    db_session.add(candidate)
    db_session.flush()
    return listing, candidate


# TEST 01. 매물 등록 및 조회
def test_01_listing_crud(db_session):
    listing = Listing(
        source_platform="DEALER_DIRECT",
        source_listing_id="TEST-001",
        raw_location="서울 동대문구 장안동 장안평 매매단지",
        normalized_region_id="REGION_JANGANPYEONG",
        first_observed_at=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        current_status="ACTIVE",
    )
    db_session.add(listing)
    db_session.commit()

    saved = db_session.get(Listing, listing.listing_id)
    assert saved is not None
    assert saved.source_platform == "DEALER_DIRECT"
    assert saved.current_status == "ACTIVE"


# TEST 02. 가격 변경 시 과거 가격 보존
def test_02_price_history_preservation(db_session):
    listing = Listing(
        source_platform="ENCAR",
        source_listing_id="ENCAR-002",
        raw_location="서울 장안평",
        normalized_region_id="REGION_JANGANPYEONG",
        first_observed_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    db_session.add(listing)
    db_session.flush()

    snap1 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=datetime(2026, 10, 1, 10, 0, tzinfo=UTC),
        price_krw=15_000_000,
        mileage_km=50_000,
        listing_status="ACTIVE",
    )
    snap2 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=datetime(2026, 10, 5, 14, 0, tzinfo=UTC),
        price_krw=14_500_000,
        mileage_km=50_020,
        listing_status="PRICE_CHANGED",
    )
    db_session.add_all([snap1, snap2])
    db_session.commit()

    snapshots = db_session.scalars(
        select(ListingSnapshot)
        .where(ListingSnapshot.listing_id == listing.listing_id)
        .order_by(ListingSnapshot.observed_at)
    ).all()

    assert len(snapshots) == 2
    assert snapshots[0].price_krw == 15_000_000
    assert snapshots[1].price_krw == 14_500_000


# TEST 03. 관측 시점 및 입력 시점에 따른 미래 정보 누출 방지
def test_03_time_travel_leakage_prevention(db_session):
    listing = Listing(
        source_platform="ENCAR",
        source_listing_id="ENCAR-003",
        raw_location="서울 장안평",
        normalized_region_id="REGION_JANGANPYEONG",
        first_observed_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    db_session.add(listing)
    db_session.flush()

    snap1 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=datetime(2026, 10, 1, 12, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 10, 1, 12, 5, tzinfo=UTC),
        price_krw=20_000_000,
        mileage_km=30_000,
        listing_status="ACTIVE",
    )
    snap2 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=datetime(2026, 10, 10, 12, 0, tzinfo=UTC),
        ingested_at=datetime(2026, 10, 10, 12, 5, tzinfo=UTC),
        price_krw=18_000_000,
        mileage_km=30_050,
        listing_status="PRICE_CHANGED",
    )
    db_session.add_all([snap1, snap2])
    db_session.commit()

    t_decision = datetime(2026, 10, 5, 0, 0, tzinfo=UTC)
    past_snap = TimeTravelQueryEngine.get_listing_snapshot_at(db_session, listing.listing_id, t_decision)

    assert past_snap is not None
    assert past_snap.price_krw == 20_000_000

    t_before = datetime(2026, 9, 30, 0, 0, tzinfo=UTC)
    none_snap = TimeTravelQueryEngine.get_listing_snapshot_at(db_session, listing.listing_id, t_before)
    assert none_snap is None


# TEST 04. 동일 차량의 여러 플랫폼 등록 구분
def test_04_multi_platform_listing_separation(db_session):
    vehicle = VehicleIdentity(identity_status="CONFIRMED")
    db_session.add(vehicle)
    db_session.flush()

    listing_encar = Listing(
        source_platform="ENCAR",
        source_listing_id="ENCAR-999",
        vehicle_id=vehicle.vehicle_id,
        raw_location="서울 장안평",
        normalized_region_id="REGION_JANGANPYEONG",
    )
    listing_kb = Listing(
        source_platform="KB_CHACHACHA",
        source_listing_id="KB-888",
        vehicle_id=vehicle.vehicle_id,
        raw_location="서울 장안평",
        normalized_region_id="REGION_JANGANPYEONG",
    )
    db_session.add_all([listing_encar, listing_kb])
    db_session.commit()

    assert listing_encar.listing_id != listing_kb.listing_id
    assert listing_encar.source_platform == "ENCAR"
    assert listing_kb.source_platform == "KB_CHACHACHA"


# TEST 05. 차량 동일성 미확정 상태 유지
def test_05_identity_unconfirmed_state(db_session):
    vehicle = VehicleIdentity(
        plate_number=None,
        vin=None,
        identity_status="UNCONFIRMED",
        identity_confidence=0.3,
    )
    db_session.add(vehicle)
    db_session.commit()

    saved = db_session.get(VehicleIdentity, vehicle.vehicle_id)
    assert saved.identity_status == "UNCONFIRMED"
    assert saved.identity_confidence == 0.3
    assert saved.plate_number is None


# TEST 06. 한국형 차량 세대·트림 구분 (아반떼 AD vs CN7 페이스리프트)
def test_06_korean_generation_and_trim_separation(db_session):
    ad = VehicleCatalog(
        manufacturer="현대",
        model_name="아반떼",
        generation="AD",
        is_facelift=False,
        trim="스마트",
        model_year=2017,
        fuel_type="가솔린",
    )
    cn7_fl = VehicleCatalog(
        manufacturer="현대",
        model_name="아반떼",
        generation="CN7",
        is_facelift=True,
        sub_model="더 뉴 아반떼 CN7",
        trim="인스퍼레이션",
        model_year=2023,
        fuel_type="하이브리드",
    )
    db_session.add_all([ad, cn7_fl])
    db_session.commit()

    assert ad.generation != cn7_fl.generation
    assert cn7_fl.is_facelift is True
    assert "CN7" in cn7_fl.full_name()
    assert "AD" in ad.full_name()


# TEST 07. 미확인 옵션과 미장착 옵션 구분 (PRESENT vs ABSENT vs UNKNOWN)
def test_07_option_status_distinction(db_session):
    opt_present = VehicleOption(option_code="SUNROOF", option_status="PRESENT")
    opt_absent = VehicleOption(option_code="HUD", option_status="ABSENT")
    opt_unknown = VehicleOption(option_code="SMART_CRUISE", option_status="UNKNOWN")

    db_session.add_all([opt_present, opt_absent, opt_unknown])
    db_session.commit()

    assert opt_present.option_status == "PRESENT"
    assert opt_absent.option_status == "ABSENT"
    assert opt_unknown.option_status == "UNKNOWN"


# TEST 08. 외판 교환과 주요 골격 손상 정보 구분
def test_08_outer_panel_vs_structural_damage_distinction(db_session):
    cond = VehicleCondition(
        inspection_status="CONFIRMED",
        accident_classification="MAJOR_ACCIDENT",
        outer_panel_repairs={"fender_replaced": True},
        structural_damages={"pillar_repaired": True, "wheelhouse_welded": True},
        observed_at=datetime.now(UTC),
    )
    db_session.add(cond)
    db_session.commit()

    saved = db_session.get(VehicleCondition, cond.condition_id)
    assert saved.outer_panel_repairs.get("fender_replaced") is True
    assert saved.structural_damages.get("wheelhouse_welded") is True
    assert saved.accident_classification == "MAJOR_ACCIDENT"


# TEST 09. 미확인 사고·보험 정보 처리
def test_09_unconfirmed_accident_insurance_handling(db_session):
    cond = VehicleCondition(
        inspection_status="UNCONFIRMED",
        accident_classification="UNCONFIRMED",
        insurance_record_verified=False,
        my_damage_amount_krw=0,
        other_damage_amount_krw=0,
        engine_condition="UNCONFIRMED",
        observed_at=datetime.now(UTC),
    )
    db_session.add(cond)
    db_session.commit()

    saved = db_session.get(VehicleCondition, cond.condition_id)
    assert saved.insurance_record_verified is False
    assert saved.accident_classification == "UNCONFIRMED"
    assert saved.engine_condition == "UNCONFIRMED"


# TEST 10. 전국 분석 범위와 장안평 판매 대상 범위 분리
def test_10_market_analysis_vs_sales_target_separation(seeded_db):
    reg_mgr = RegionManager()

    all_listings = seeded_db.scalars(select(Listing)).all()
    assert len(all_listings) >= 100

    janganpyeong_listings = reg_mgr.get_sales_target_listings(
        seeded_db, target_region_id="REGION_JANGANPYEONG"
    )
    assert len(janganpyeong_listings) > 0
    assert len(janganpyeong_listings) < len(all_listings)
    for l in janganpyeong_listings:
        assert l.normalized_region_id == "REGION_JANGANPYEONG"


# TEST 11. 수원·인천·부천 추가 시 지역 필터 정상 동작
def test_11_region_expansion(seeded_db):
    reg_mgr = RegionManager()

    suwon_listings = reg_mgr.get_sales_target_listings(seeded_db, target_region_id="REGION_SUWON")
    incheon_listings = reg_mgr.get_sales_target_listings(seeded_db, target_region_id="REGION_INCHEON")
    bucheon_listings = reg_mgr.get_sales_target_listings(seeded_db, target_region_id="REGION_BUCHEON")

    assert len(suwon_listings) > 0
    assert len(incheon_listings) > 0
    assert len(bucheon_listings) > 0


# TEST 12. 지역 미확정 매물의 잘못된 자동 편입 방지
def test_12_unconfirmed_region_filter(db_session):
    reg_mgr = RegionManager()

    resolved = reg_mgr.resolve_region_from_text("모호한 도로명 주소 123번지")
    assert resolved is None

    empty_resolved = reg_mgr.resolve_region_from_text("")
    assert empty_resolved is None


# TEST 13. 매물 삭제를 판매 확정으로 자동 처리하지 않는지 확인
def test_13_delisted_not_sold_confirmation(db_session):
    _, candidate = _create_test_listing_and_candidate(db_session, source_id="DELIST-1")
    candidate.listing.current_status = "DELISTED"

    outcome = SalesOutcome(
        candidate_id=candidate.candidate_id,
        outcome_status="DELISTED_UNKNOWN",
        verification_status="UNVERIFIED",
    )
    db_session.add(outcome)
    db_session.commit()

    saved_outcome = db_session.get(SalesOutcome, outcome.outcome_id)
    assert saved_outcome.outcome_status == "DELISTED_UNKNOWN"
    assert saved_outcome.outcome_status != "SOLD_CONFIRMED"
    assert saved_outcome.confirmed_sale_price_krw is None


# TEST 14. 파트너 판매 가능 여부 기록
def test_14_partner_availability_tracking(db_session):
    partner = SalesPartner(
        partner_name="장안평 25년 베테랑",
        operating_region_id="REGION_JANGANPYEONG",
        experience_years=25,
    )
    db_session.add(partner)
    db_session.flush()

    _, candidate = _create_test_listing_and_candidate(db_session, source_id="PARTNER-1")
    candidate.availability_status = "AVAILABLE"
    candidate.partner_review_status = "APPROVED"
    candidate.review_note = "실차 확인 완료, 침수 흔적 없음, 판매 가능"
    db_session.commit()

    saved = db_session.get(SalesCandidate, candidate.candidate_id)
    assert saved.availability_status == "AVAILABLE"
    assert saved.partner_review_status == "APPROVED"
    assert "판매 가능" in saved.review_note


# TEST 15. 광고 결정 및 행동 이력 저장 (강화학습 로깅)
def test_15_promotion_decision_logging(db_session):
    _, candidate = _create_test_listing_and_candidate(db_session, source_id="DECISION-1")

    decision = PromotionDecision(
        candidate_id=candidate.candidate_id,
        policy_version="BANDIT_EPSILON_0.1",
        decision_source="AI_AGENT",
        eligible_actions=["PRODUCE_SHORT_VIDEO", "PROMOTE_CAROUSEL", "WAIT_ORGANIC"],
        chosen_action="PRODUCE_SHORT_VIDEO",
        action_probability=0.85,
        planned_budget_krw=50_000,
        execution_status="EXECUTED",
    )
    db_session.add(decision)
    db_session.commit()

    saved = db_session.get(PromotionDecision, decision.decision_id)
    assert saved.chosen_action == "PRODUCE_SHORT_VIDEO"
    assert saved.action_probability == 0.85
    assert "WAIT_ORGANIC" in saved.eligible_actions
    assert saved.execution_status == "EXECUTED"


# TEST 16. 가상 광고 성과와 실제 판매 결과를 서로 구분
def test_16_marketing_vs_outcome_separation(db_session):
    _, candidate = _create_test_listing_and_candidate(db_session, source_id="MKT-OUTCOME-1")

    decision = PromotionDecision(
        candidate_id=candidate.candidate_id,
        policy_version="V1",
        eligible_actions=["PRODUCE_SHORT_VIDEO"],
        chosen_action="PRODUCE_SHORT_VIDEO",
    )
    db_session.add(decision)
    db_session.flush()

    m_result = MarketingResult(
        decision_id=decision.decision_id,
        platform="YOUTUBE_SHORTS",
        creative_type="VIDEO_9_16",
        views=150_000,
        inquiries=12,
        verified_leads=3,
        advertising_cost_krw=30_000,
    )
    outcome = SalesOutcome(
        candidate_id=candidate.candidate_id,
        outcome_status="NOT_YET_SOLD",
        verification_status="UNVERIFIED",
    )
    db_session.add_all([m_result, outcome])
    db_session.commit()

    assert m_result.views == 150_000
    assert outcome.outcome_status == "NOT_YET_SOLD"


# TEST 17. 등록가격과 실제 거래가격 분리
def test_17_listing_vs_actual_deal_price_separation(db_session):
    listing, candidate = _create_test_listing_and_candidate(db_session, source_id="DEAL-PRICE-1")

    snap = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=datetime.now(UTC),
        price_krw=15_000_000,  # 등록 가격
        mileage_km=50_000,
    )
    outcome = SalesOutcome(
        candidate_id=candidate.candidate_id,
        outcome_status="SOLD_CONFIRMED",
        verification_status="CONFIRMED_BY_CONTRACT",
        confirmed_sale_price_krw=14_300_000,  # 실제 계약 거래가
    )
    db_session.add_all([snap, outcome])
    db_session.commit()

    assert snap.price_krw == 15_000_000
    assert outcome.confirmed_sale_price_krw == 14_300_000
    assert snap.price_krw != outcome.confirmed_sale_price_krw


# TEST 18. 정산 미확정 시 실제 수익 확정 방지
def test_18_settlement_unconfirmed_revenue_protection(db_session):
    _, candidate = _create_test_listing_and_candidate(db_session, source_id="SETTLE-1")

    outcome = SalesOutcome(
        candidate_id=candidate.candidate_id,
        outcome_status="SOLD_CONFIRMED",
        verification_status="CONFIRMED_BY_CONTRACT",
        confirmed_sale_price_krw=15_000_000,
    )
    db_session.add(outcome)
    db_session.flush()

    settle = Settlement(
        outcome_id=outcome.outcome_id,
        revenue_type="COMMISSION",
        confirmed_revenue_krw=500_000,
        advertising_cost_krw=50_000,
        production_cost_krw=20_000,
        net_profit_krw=430_000,
        settlement_status="PENDING",
    )
    db_session.add(settle)
    db_session.commit()

    assert settle.settlement_status == "PENDING"
    assert settle.verified_at is None


# TEST 19. 데이터 출처와 사용 권한 구분
def test_19_source_permissions_verification(db_session):
    perm_encar = DataSourcePermission(
        source_id="ENCAR",
        source_name="엔카닷컴",
        permission_status="RESTRICTED",
        republication_allowed=False,
        authorization_reference="약관상 재배포 금지",
    )
    perm_partner = DataSourcePermission(
        source_id="JANGANPYEONG_PARTNER",
        source_name="장안평 파트너 딜러",
        permission_status="AUTHORIZED",
        republication_allowed=True,
        authorization_reference="광고 위탁 계약",
    )
    db_session.add_all([perm_encar, perm_partner])
    db_session.commit()

    assert perm_encar.republication_allowed is False
    assert perm_partner.republication_allowed is True


# TEST 20. 가상 매물 등록부터 선정·홍보 기록·판매·정산까지 전체 연결 테스트
def test_20_end_to_end_scenario(db_session):
    cat = VehicleCatalog(
        manufacturer="현대",
        model_name="아반떼",
        generation="CN7",
        is_facelift=False,
        trim="모던",
        model_year=2021,
        fuel_type="가솔린",
    )
    partner = SalesPartner(
        partner_name="장안평 베테랑 파트너",
        operating_region_id="REGION_JANGANPYEONG",
        experience_years=25,
    )
    db_session.add_all([cat, partner])
    db_session.flush()

    vehicle = VehicleIdentity(catalog_id=cat.catalog_id, identity_status="CONFIRMED")
    db_session.add(vehicle)
    db_session.flush()

    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    listing = Listing(
        source_platform="DEALER_DIRECT",
        source_listing_id="DD-AVANTE-2021",
        vehicle_id=vehicle.vehicle_id,
        seller_reference=partner.partner_id,
        first_observed_at=t0,
        raw_location="서울 동대문구 장안동 장안평 매매단지",
        normalized_region_id="REGION_JANGANPYEONG",
        current_status="ACTIVE",
    )
    db_session.add(listing)
    db_session.flush()

    snap1 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=t0,
        price_krw=15_000_000,
        mileage_km=45_000,
        listing_status="ACTIVE",
    )
    snap2 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=t0 + timedelta(days=5),
        price_krw=14_500_000,
        mileage_km=45_010,
        listing_status="PRICE_CHANGED",
    )
    db_session.add_all([snap1, snap2])
    db_session.flush()

    candidate = SalesCandidate(
        listing_id=listing.listing_id,
        target_region_id="REGION_JANGANPYEONG",
        selected_by="AI_AGENT",
        selection_reason="장안평 무사고 아반떼 CN7 가성비 우수",
        selection_score=0.92,
        availability_status="AVAILABLE",
        partner_review_status="APPROVED",
        review_note="실차 확인 및 딜러 협의 완료, 판매 가능",
    )
    db_session.add(candidate)
    db_session.flush()

    decision = PromotionDecision(
        candidate_id=candidate.candidate_id,
        partner_id=partner.partner_id,
        policy_version="V0.1_TEST",
        decision_source="AI_AGENT",
        eligible_actions=["PRODUCE_SHORT_VIDEO", "WAIT_ORGANIC"],
        chosen_action="PRODUCE_SHORT_VIDEO",
        action_probability=1.0,
        planned_budget_krw=30_000,
        execution_status="EXECUTED",
    )
    db_session.add(decision)
    db_session.flush()

    marketing = MarketingResult(
        decision_id=decision.decision_id,
        platform="YOUTUBE_SHORTS",
        creative_type="VIDEO_9_16",
        impressions=50_000,
        views=25_000,
        clicks=800,
        inquiries=15,
        verified_leads=4,
        production_cost_krw=15_000,
        advertising_cost_krw=30_000,
    )
    db_session.add(marketing)
    db_session.flush()

    outcome = SalesOutcome(
        candidate_id=candidate.candidate_id,
        partner_id=partner.partner_id,
        outcome_status="SOLD_CONFIRMED",
        verification_status="CONFIRMED_BY_CONTRACT",
        contracted_at=t0 + timedelta(days=12),
        confirmed_sale_price_krw=14_300_000,
        evidence_reference="CONTRACT-202610-099",
    )
    db_session.add(outcome)
    db_session.flush()

    settlement = Settlement(
        outcome_id=outcome.outcome_id,
        revenue_type="COMMISSION",
        confirmed_revenue_krw=600_000,
        advertising_cost_krw=marketing.advertising_cost_krw,
        production_cost_krw=marketing.production_cost_krw,
        other_costs_krw=10_000,
        settlement_status="SETTLED",
        verified_at=t0 + timedelta(days=13),
    )
    settlement.net_profit_krw = settlement.calculate_net_profit()
    db_session.add(settlement)
    db_session.commit()

    final_settle = db_session.get(Settlement, settlement.settlement_id)
    assert final_settle.settlement_status == "SETTLED"
    assert final_settle.net_profit_krw == (600_000 - 30_000 - 15_000 - 10_000)
    assert final_settle.net_profit_krw == 545_000
    assert final_settle.outcome.confirmed_sale_price_krw == 14_300_000
    assert final_settle.outcome.candidate.listing.listing_id == listing.listing_id


# 추가 무결성 검증 1: 음수 가격 차단
def test_integrity_negative_price_blocked(db_session):
    listing, _ = _create_test_listing_and_candidate(db_session, source_id="NEG-1")

    invalid_snap = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=datetime.now(UTC),
        price_krw=-5_000_000,
        mileage_km=10_000,
    )
    db_session.add(invalid_snap)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# 추가 무결성 검증 2: 동일 계약 중복 정산 차단 (Unique Constraint)
def test_integrity_duplicate_settlement_blocked(db_session):
    _, candidate = _create_test_listing_and_candidate(db_session, source_id="DUP-1")

    outcome = SalesOutcome(
        candidate_id=candidate.candidate_id,
        outcome_status="SOLD_CONFIRMED",
        verification_status="CONFIRMED_BY_CONTRACT",
    )
    db_session.add(outcome)
    db_session.flush()

    settle1 = Settlement(
        outcome_id=outcome.outcome_id,
        confirmed_revenue_krw=100_000,
    )
    settle2 = Settlement(
        outcome_id=outcome.outcome_id,
        confirmed_revenue_krw=200_000,
    )
    db_session.add(settle1)
    db_session.flush()
    db_session.add(settle2)

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
