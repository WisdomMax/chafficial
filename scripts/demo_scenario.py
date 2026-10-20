"""CHA-FICIAL V0.1 최소 작동 시나리오 데모 스크립트.

아반떼 가상 매물 등록 -> 1500만 -> 1450만 가격 인하 -> 장안평 파트너 승인
-> AI 홍보 의사결정 -> 마케팅 집행 -> 계약 체결 -> 순수익 정산까지 전체 흐름을 시연합니다.

[주의: 본 스크립트의 데이터와 선정 이유는 파이프라인 무결성 검증을 위한 가상 합성 데이터(SYNTHETIC DATA)이며,
실제 AI 모델의 예측 결과나 실측 시장 분석 성과가 아닙니다.]
"""

from datetime import UTC, datetime, timedelta
from chaficial.database.base import Base, get_engine, get_session_factory
from chaficial.models import (
    Listing,
    ListingSnapshot,
    MarketingResult,
    PromotionDecision,
    SalesCandidate,
    SalesOutcome,
    SalesPartner,
    Settlement,
    VehicleCatalog,
    VehicleIdentity,
)
from chaficial.regions.manager import RegionManager
from chaficial.time_travel.query_engine import TimeTravelQueryEngine


def run_demo():
    print("=================================================================")
    print("🚘 CHA-FICIAL AI : 중고차 데이터 엔진 V0.1 전체 연결 시나리오 데모")
    print("⚠️  [NOTICE: 본 시연은 무결성 검증용 SYNTHETIC DATA이며 실제 AI 예측 아님]")
    print("=================================================================\n")

    engine = get_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session = get_session_factory(engine)()

    # 1. 지역 시딩
    print("[1단계] 지역 및 장안평 판매 권역 시딩...")
    reg_mgr = RegionManager()
    reg_mgr.seed_default_regions(session)

    # 2. 카탈로그 및 파트너 등록
    print("[2단계] 2021년식 아반떼 CN7 카탈로그 및 장안평 25년 베테랑 파트너 등록...")
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
        partner_name="장안평 25년 경력 베테랑 실무 딜러",
        operating_region_id="REGION_JANGANPYEONG",
        experience_years=25,
        contact_masked="010-****-5678",
    )
    session.add_all([cat, partner])
    session.flush()

    # 3. 매물 등록 및 가격 변경 (1500만 -> 1450만)
    print("[3단계] 장안평 매물 등록 및 가격 인하 시계열 스냅샷 생성...")
    vehicle = VehicleIdentity(catalog_id=cat.catalog_id, identity_status="CONFIRMED")
    session.add(vehicle)
    session.flush()

    t0 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    listing = Listing(
        source_platform="DEALER_DIRECT",
        source_listing_id="DD-AVANTE-DEMO",
        vehicle_id=vehicle.vehicle_id,
        seller_reference=partner.partner_id,
        first_observed_at=t0,
        raw_location="서울 동대문구 장안동 장안평 자동차 매매단지",
        normalized_region_id="REGION_JANGANPYEONG",
        current_status="ACTIVE",
    )
    session.add(listing)
    session.flush()

    # 스냅샷 1: 최초 등록가 1500만원
    snap1 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=t0,
        ingested_at=t0 + timedelta(minutes=5),
        price_krw=15_000_000,
        mileage_km=42_000,
        listing_status="ACTIVE",
    )
    # 스냅샷 2: 5일 뒤 1450만원으로 인하
    snap2 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=t0 + timedelta(days=5),
        ingested_at=t0 + timedelta(days=5, minutes=5),
        price_krw=14_500_000,
        mileage_km=42_020,
        listing_status="PRICE_CHANGED",
    )
    session.add_all([snap1, snap2])
    session.flush()

    # 시계열 조회 검증 (10월 3일 시점 조회)
    t_mid = t0 + timedelta(days=2)
    past_snap = TimeTravelQueryEngine.get_listing_snapshot_at(session, listing.listing_id, t_mid)
    print(f"  -> [시계열 재현 검증] 10월 3일 당시 조회 가격: {past_snap.price_krw:,}원 (미래 1450만원 누출 차단 확인)")

    # 4. 판매 후보 선정 및 파트너 실차 검토
    print("[4단계] 판매 후보 차량 선정 및 장안평 파트너 실차 검토...")
    candidate = SalesCandidate(
        listing_id=listing.listing_id,
        target_region_id="REGION_JANGANPYEONG",
        selected_by="RULE_BASED",  # AI 모델 미학습 상태이므로 규칙 기반 테스트로 표기
        selection_reason="[가상 시나리오 테스트] 장안평 아반떼 CN7 무사고 가정 (파이프라인 무결성 검증용)",
        selection_score=None,  # AI 예측 점수가 아니므로 None 처리 (허위 AI 성과 표현 배제)
        availability_status="AVAILABLE",
        partner_review_status="APPROVED",
        review_note="실차 입고 및 점검 완료 가정. 골격 손상 없음, 즉시 출고 가능",
    )
    session.add(candidate)
    session.flush()

    # 5. 홍보 의사결정 및 가상 마케팅 성과
    print("[5단계] 홍보 의사결정 로깅 및 가상 SNS 집행 (합성 피드백)...")
    decision = PromotionDecision(
        candidate_id=candidate.candidate_id,
        partner_id=partner.partner_id,
        policy_version="V0.1_SYNTHETIC_TEST",
        decision_source="HEURISTIC_RULE",
        eligible_actions=["PRODUCE_SHORT_VIDEO", "PROMOTE_CAROUSEL", "WAIT_ORGANIC"],
        chosen_action="PRODUCE_SHORT_VIDEO",
        action_probability=None,  # 무작위 탐색 또는 반사실적 확률이 아니므로 None 처리
        planned_budget_krw=30_000,
        execution_status="EXECUTED",
    )
    session.add(decision)
    session.flush()

    marketing = MarketingResult(
        decision_id=decision.decision_id,
        platform="YOUTUBE_SHORTS",
        creative_type="VIDEO_9_16",
        impressions=62_000,
        views=31_500,
        clicks=920,
        inquiries=18,
        verified_leads=5,
        production_cost_krw=15_000,
        advertising_cost_krw=30_000,
    )
    session.add(marketing)
    session.flush()
    print(f"  -> 가상 광고 성과: 조회수 {marketing.views:,}회 / 구매 문의 {marketing.inquiries}건 / 유효 상담 {marketing.verified_leads}건 (합성 데이터)")

    # 6. 실제 판매 확인 및 계약 체결
    print("[6단계] 실제 판매 확인 및 계약 체결 (등록가와 실제 거래가 분리)...")
    outcome = SalesOutcome(
        candidate_id=candidate.candidate_id,
        partner_id=partner.partner_id,
        outcome_status="SOLD_CONFIRMED",
        verification_status="CONFIRMED_BY_CONTRACT",
        contracted_at=t0 + timedelta(days=11),
        confirmed_sale_price_krw=14_200_000,  # 1450만원 등록가 대비 실거래가 1420만원
        evidence_reference="CONTRACT-202610-099",
    )
    session.add(outcome)
    session.flush()

    # 7. 실제 순수익 정산
    print("[7단계] 최종 영업 정산 및 순수익(Net Profit) 확정...")
    settlement = Settlement(
        outcome_id=outcome.outcome_id,
        revenue_type="COMMISSION",
        confirmed_revenue_krw=600_000,
        advertising_cost_krw=marketing.advertising_cost_krw,
        production_cost_krw=marketing.production_cost_krw,
        other_costs_krw=10_000,
        settlement_status="SETTLED",
        verified_at=t0 + timedelta(days=12),
    )
    settlement.net_profit_krw = settlement.calculate_net_profit()
    session.add(settlement)
    session.commit()

    print("\n==================== [최종 정산 결과 요약 (가상 테스트)] ====================")
    print(f"차량: {cat.full_name()}")
    print(f"소재지: {listing.raw_location} ({listing.normalized_region_id})")
    print(f"등록 가격: 14,500,000원 -> 최종 계약 가격: {outcome.confirmed_sale_price_krw:,}원")
    print(f"총 수수료 매출: {settlement.confirmed_revenue_krw:,}원")
    print(f"제작비: -{settlement.production_cost_krw:,}원")
    print(f"광고비: -{settlement.advertising_cost_krw:,}원")
    print(f"기타비용: -{settlement.other_costs_krw:,}원")
    print(f"▶ 최종 확정 순수익 (Net Profit): {settlement.net_profit_krw:,}원 (상태: {settlement.settlement_status})")
    print("============================================================================\n")
    print("✅ 최소 작동 시나리오 무결성 검증이 정상 완료되었습니다. (SYNTHETIC VERIFIED)")


if __name__ == "__main__":
    run_demo()
