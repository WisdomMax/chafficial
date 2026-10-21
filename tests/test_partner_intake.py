"""DIRECTIVE 004-B: 파트너 실매물 인입 사전 검증 및 시계열 무결성 반례 테스트."""

import io
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from chaficial.database.base import Base
from chaficial.intake.validator import (
    DelegationProof,
    IntakeApprovalProof,
    PartnerListingIntakeValidator,
)
from chaficial.models.region import Region


@pytest.fixture
def sqlite_test_db():
    """격리된 SQLite 인메모리 테스트 데이터베이스 fixture."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        region_nation = Region(
            region_id="REGION_NATIONWIDE",
            region_name="전국",
            region_type="COUNTRY",
            is_active=True,
        )
        region_seoul = Region(
            region_id="REGION_SEOUL",
            region_name="서울특별시",
            region_type="METROPOLIS",
            parent=region_nation,
            is_active=True,
        )
        region_jangan = Region(
            region_id="REGION_JANGANPYEONG",
            region_name="서울 장안평 중고차 시장",
            region_type="MARKET_COMPLEX",
            parent=region_seoul,
            is_active=True,
        )
        session.add_all([region_nation, region_seoul, region_jangan])
        session.commit()

    yield engine
    engine.dispose()


def test_suite_a_normal_synthetic_3_cars_flush_and_rollback(sqlite_test_db):
    """
    [테스트 A: 정상 데이터 및 ORM 정합성 실증]
    - 합성 매물 3건 가격/연식/주행거리 검증 통과.
    - ORM 엔티티 생성 및 SQLite 실제 INSERT/FLUSH 성공.
    - ROLLBACK 후 DB 오염 없음 검증.
    - 현실 세계 실데이터 건수는 0건 유지.
    """
    sample_path = Path("templates/PARTNER_LISTING_INTAKE_SYNTHETIC_SAMPLE.csv")
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(sample_path, is_synthetic=True)

    assert report.total_rows == 3
    assert report.valid_rows == 3
    assert report.synthetic_data_count == 3
    assert report.verified_real_data_count == 0  # 실데이터 0건 유지
    assert report.real_ad_delegation_count == 0
    assert report.actual_ad_spend_krw == 0

    with Session(sqlite_test_db) as session:
        for record in report.records:
            catalog, identity, listing, snapshots = PartnerListingIntakeValidator.build_orm_entities(
                record,
                target_region_id="REGION_JANGANPYEONG",
                raw_location="서울 성동구 장안평 중고차 매매단지",
            )
            session.add_all([catalog, identity, listing])
            session.add_all(snapshots)

        session.flush()
        assert len(session.new) == 0
        session.rollback()

    with Session(sqlite_test_db) as session:
        from chaficial.models.listing import Listing
        assert session.query(Listing).count() == 0, "DRY RUN 후 레코드가 잔존하지 않아야 합니다."


def test_suite_b_time_travel_future_leakage_prevention(sqlite_test_db):
    """
    [테스트 B: 시계열 판매 상태 미래 정보 누출 방지 (Time-Travel)]
    - 10월 1일 매물 등록 (최초 관측가 1500만원, ACTIVE)
    - 10월 10일 실제 계약 체결 (계약가 1420만원, DELISTED)
    - 10월 15일 시스템 일괄 적재
    - 검증: 최초 관측 스냅샷(INIT)은 사후 계약과 무관하게 10월 1일 당시 상태인 ACTIVE 및 등록가를 보존해야 함.
    - 사후 계약 정보는 10월 10일 관측 시점의 별도 스냅샷(CLOSED)으로 분리 기록되어 과거 시점 조회의 불변성을 보장.
    """
    csv_single_sold_car = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-TIME-001,VEH-T01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,2026-10-10,14200000,600000,15000,30000,10000,545000,SETTLED
"""
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(io.StringIO(csv_single_sold_car), is_synthetic=True)
    assert report.valid_rows == 1
    record = report.records[0]

    system_ingest_time = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)
    _, _, listing, snapshots = PartnerListingIntakeValidator.build_orm_entities(
        record,
        target_region_id="REGION_JANGANPYEONG",
        raw_location="서울 장안평 매매단지",
        system_ingested_at=system_ingest_time,
    )
    assert listing.current_status == "DELISTED"

    # 스냅샷이 2개(최초 등록 시점, 계약 체결 시점)로 분리 생성되었는지 확인
    assert len(snapshots) == 2

    init_snap = snapshots[0]
    closed_snap = snapshots[1]

    # 최초 스냅샷 검증: 미래의 계약 정보 누출 차단
    assert init_snap.observed_at == datetime(2026, 10, 1, tzinfo=UTC)
    assert init_snap.listing_status == "ACTIVE", "최초 관측 스냅샷은 계약 여부와 무관하게 ACTIVE여야 합니다."
    assert init_snap.price_krw == 15000000
    assert init_snap.ingested_at == system_ingest_time

    # 계약 스냅샷 검증: 계약 체결 시점에 새로 기록됨
    assert closed_snap.observed_at == datetime(2026, 10, 10, tzinfo=UTC)
    assert closed_snap.listing_status == "DELISTED"
    assert closed_snap.price_krw == 14200000
    assert closed_snap.ingested_at == system_ingest_time

    # 10월 5일 시점 조회 시뮬레이션:
    query_time_oct_5 = datetime(2026, 10, 5, tzinfo=UTC)
    valid_snapshots_on_oct_5 = [s for s in snapshots if s.observed_at <= query_time_oct_5]
    assert len(valid_snapshots_on_oct_5) == 1
    assert valid_snapshots_on_oct_5[0].listing_status == "ACTIVE", "10월 5일 시점에는 차량이 여전히 활성 매물이어야 합니다."


def test_suite_c_delegation_and_live_ad_permission_separation():
    """
    [테스트 C: 권한 증빙 및 실제 게시 허가의 분리]
    - 신뢰할 수 없는 승인 객체는 SIMULATED_AUTHORIZED로 격리.
    - 만료된 위임, 철회된 위임, 제3자 상사 미동의 차량은 is_marketing_eligible = False.
    - 모든 경우에 is_live_ad_authorized는 False (실제 SNS 게시 및 유료 광고 집행 불가).
    """
    today = datetime.now(UTC).date()
    proof_valid = DelegationProof(
        proof_id="PROOF-V",
        internal_listing_id="LST-01",
        delegation_type="DIRECT_PURCHASE_OWNER",
        valid_until=today + timedelta(days=30),
        has_signed_document=True,
    )
    proof_expired = DelegationProof(
        proof_id="PROOF-E",
        internal_listing_id="LST-02",
        delegation_type="DIRECT_PURCHASE_OWNER",
        valid_until=today - timedelta(days=2),
        has_signed_document=True,
    )
    proof_revoked = DelegationProof(
        proof_id="PROOF-R",
        internal_listing_id="LST-03",
        delegation_type="DIRECT_PURCHASE_OWNER",
        valid_until=today + timedelta(days=30),
        has_signed_document=True,
        is_revoked=True,
    )
    proof_consignment_unapproved = DelegationProof(
        proof_id="PROOF-C",
        internal_listing_id="LST-04",
        delegation_type="THIRD_PARTY_CONSIGNMENT",
        valid_until=today + timedelta(days=30),
        has_signed_document=True,
        third_party_firm_consent=False,
    )

    csv_data = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-01,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
LST-02,VEH-02,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
LST-03,VEH-03,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
LST-04,VEH-04,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,CONSIGNMENT,FIRM-01,DLR-01,,,,,,,,UNSETTLED
"""
    # 일반 모의 승인 객체 주입
    mock_approval = IntakeApprovalProof(
        approval_id="MOCK-01",
        approved_by="시뮬레이터",
        approved_at=datetime.now(UTC),
        data_source="가상 테스트",
        target_firm_code="FIRM-01",
        scope_description="단위 테스트",
    )
    validator = PartnerListingIntakeValidator(
        delegation_proofs=[proof_valid, proof_expired, proof_revoked, proof_consignment_unapproved],
        approval_proof=mock_approval,
    )
    report = validator.validate_csv(io.StringIO(csv_data), is_synthetic=False)

    assert report.total_rows == 4
    assert report.valid_rows == 4

    # 1) 실데이터 분리: 현장 검증 토큰이 없으므로 SIMULATED_AUTHORIZED로 격리
    assert report.simulated_authorized_count == 4
    assert report.verified_real_data_count == 0  # 실데이터는 엄격히 0건!

    # 2) 마케팅 게이트: 유효한 서면 위임 보유 1건만 통과
    assert report.marketing_eligible_count == 1
    assert report.records[0].is_marketing_eligible is True
    assert report.records[1].is_marketing_eligible is False  # 만료
    assert report.records[2].is_marketing_eligible is False  # 철회
    assert report.records[3].is_marketing_eligible is False  # 제3자 미동의

    # 3) 실제 게시 허가: Phase 1에서는 모든 매물이 False여야 함
    assert report.live_ad_authorized_count == 0
    for r in report.records:
        assert r.is_live_ad_authorized is False


def test_suite_d_csv_parser_rfc4180_edge_cases():
    """
    [테스트 D: CSV 형식 및 파서 반례 검증]
    - 인용부호 안의 줄바꿈 및 쉼표 포함 정상 파싱.
    - 인용부호 안의 #로 시작하는 줄이 주석으로 오인되어 삭제되지 않음.
    - 중복 헤더 차단.
    - 열 개수 오류 차단.
    - 개인정보 컬럼 차단 및 오류 메시지에 개인정보 비노출.
    """
    # 1) 인용부호 내 # 포함 텍스트 보존
    csv_quoted_hash = '''internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-HASH-01,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,"#특이사항: 전면 휀더 교환
#사고없음",없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
'''
    validator = PartnerListingIntakeValidator()
    report_hash = validator.validate_csv(io.StringIO(csv_quoted_hash), is_synthetic=True)
    assert report_hash.valid_rows == 1
    damage_text = report_hash.records[0].normalized_data["outer_panel_rank1_damage"]
    assert "#특이사항" in damage_text, "인용부호 내의 '#' 라인이 주석으로 오인되어 유실되어선 안 됩니다."

    # 2) 중복 헤더 차단
    csv_dup = "internal_listing_id,internal_listing_id,model_name\n1,2,아반떼\n"
    report_dup = validator.validate_csv(io.StringIO(csv_dup), is_synthetic=True)
    assert report_dup.valid_rows == 0
    assert any(e.error_code == "DUPLICATE_HEADER" for e in report_dup.errors)

    # 3) 열 개수 불일치 차단
    csv_col_err = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-SHORT,VEH-01,현대,아반떼
"""
    report_col_err = validator.validate_csv(io.StringIO(csv_col_err), is_synthetic=True)
    assert report_col_err.valid_rows == 0
    assert any(e.error_code == "COLUMN_COUNT_MISMATCH" for e in report_col_err.errors)

    # 4) 개인정보 추가 컬럼 및 민감값 비노출 검증
    csv_pii = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status,real_plate_number,owner_phone
LST-PII,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED,12가3456,010-1234-5678
"""
    report_pii = validator.validate_csv(io.StringIO(csv_pii), is_synthetic=True)
    assert report_pii.valid_rows == 0
    for err in report_pii.errors:
        assert "12가3456" not in err.message
        assert "010-1234-5678" not in err.message
