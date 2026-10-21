"""DIRECTIVE 004-A FINAL GATE: 파트너 실매물 인입 엔진 엄격성 및 반례 실증 테스트."""

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


def test_synthetic_3_cars_actual_orm_insert_and_flush(sqlite_test_db):
    """
    CRITICAL 1: 합성 매물 3건의 ORM 변환 결과가 실제 SQLite DB의
    모든 NOT NULL, CHECK, FK 제약조건을 100% 충족하며 INSERT/FLUSH 됨을 실증.
    (테스트 후 ROLLBACK으로 무결성 유지)
    """
    sample_path = Path("templates/PARTNER_LISTING_INTAKE_SYNTHETIC_SAMPLE.csv")
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(sample_path, is_synthetic=True)

    assert report.total_rows == 3
    assert report.valid_rows == 3

    with Session(sqlite_test_db) as session:
        for record in report.records:
            catalog, identity, listing, snapshot = PartnerListingIntakeValidator.build_orm_entities(
                record,
                target_region_id="REGION_JANGANPYEONG",
                raw_location="서울 성동구 장안평 중고차 매매단지",
            )
            session.add_all([catalog, identity, listing, snapshot])

        session.flush()
        assert len(session.new) == 0
        session.rollback()

    with Session(sqlite_test_db) as session:
        from chaficial.models.listing import Listing
        count = session.query(Listing).count()
        assert count == 0, "DRY RUN 후 테스트 DB에 레코드가 잔존하지 않아야 합니다."


def test_no_hallucinated_specs_null_displacement_and_seating():
    """
    CRITICAL 1-A: 부존재 차량 제원 생성 차단 실증:
    - 입력 근거 없는 배기량 및 좌석수는 1999cc, 5명 등으로 날조하지 않고 NULL(None) 유지.
    - 필수 연식 누락 시 인입 거절.
    """
    sample_path = Path("templates/PARTNER_LISTING_INTAKE_SYNTHETIC_SAMPLE.csv")
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(sample_path, is_synthetic=True)
    record = report.records[0]

    catalog, _, _, _ = PartnerListingIntakeValidator.build_orm_entities(record)
    assert catalog.displacement_cc is None, "미확인 배기량을 임의 값으로 채워선 안 됩니다."
    assert catalog.seating_capacity is None, "미확인 좌석수를 임의 값으로 채워선 안 됩니다."

    # 연식 누락 반례
    csv_missing_year = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-NO-YEAR,VEH-01,현대,아반떼,CN7,모던,,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
"""
    report_no_year = validator.validate_csv(io.StringIO(csv_missing_year), is_synthetic=True)
    assert report_no_year.valid_rows == 0
    assert "MISSING_MODEL_YEAR" in [e.error_code for e in report_no_year.errors]


def test_no_default_location_hallucination():
    """
    HIGH 3-A: 위치 및 지역 정보 임의 생성 차단:
    - 위치 미지정 시 장안평 주소나 지역 ID로 날조하지 않고 None / LOCATION_UNCONFIRMED 보존.
    """
    sample_path = Path("templates/PARTNER_LISTING_INTAKE_SYNTHETIC_SAMPLE.csv")
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(sample_path, is_synthetic=True)
    record = report.records[0]

    _, _, listing, snapshot = PartnerListingIntakeValidator.build_orm_entities(
        record, target_region_id=None, raw_location=None
    )
    assert listing.normalized_region_id is None, "근거 없는 지역 ID를 임의 부여해선 안 됩니다."
    assert listing.raw_location == "LOCATION_UNCONFIRMED"
    assert snapshot.normalized_region_id is None


def test_csv_parser_rfc4180_multiline_comma_duplicate_header_and_col_mismatch():
    """
    HIGH 4-A: 표준 CSV 파서 검증:
    1) 인용부호 내 줄바꿈 및 쉼표 포함 정상 파싱
    2) 중복 헤더 차단
    3) 열 개수 불일치 감지 및 거절
    """
    # 1) 필드 내 쉼표 및 줄바꿈 포함
    csv_multiline = '''internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-ML-01,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,"단순교환(도어,
휀더)",없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
'''
    validator = PartnerListingIntakeValidator()
    report_ml = validator.validate_csv(io.StringIO(csv_multiline), is_synthetic=True)
    assert report_ml.valid_rows == 1
    assert "단순교환(도어,\n휀더)" in report_ml.records[0].normalized_data["outer_panel_rank1_damage"]

    # 2) 중복 헤더 차단
    csv_dup_header = """internal_listing_id,internal_listing_id,manufacturer,model_name
1,2,현대,아반떼
"""
    report_dup = validator.validate_csv(io.StringIO(csv_dup_header), is_synthetic=True)
    assert report_dup.valid_rows == 0
    assert "DUPLICATE_HEADER" in [e.error_code for e in report_dup.errors]

    # 3) 열 개수 불일치
    csv_col_mismatch = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-SHORT-01,VEH-01,현대,아반떼
"""
    report_short = validator.validate_csv(io.StringIO(csv_col_mismatch), is_synthetic=True)
    assert report_short.valid_rows == 0
    assert "COLUMN_COUNT_MISMATCH" in [e.error_code for e in report_short.errors]


def test_simulated_authorized_vs_real_data_separation():
    """
    CRITICAL 2-A: 실데이터 증빙 객체와 실제 검증 완료의 엄격한 분리:
    - 승인 객체 존재하더라도 현장 검증(is_real_world_verified)이 없으면 SIMULATED_AUTHORIZED로 격리.
    - 현실 세계의 verified_real_data_count는 항상 0건 유지.
    """
    csv_data = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-SIM-01,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
"""
    mock_approval = IntakeApprovalProof(
        approval_id="TEST-APP-01",
        approved_by="테스트 관리자",
        approved_at=datetime.now(UTC),
        data_source="가상 시뮬레이션",
        target_firm_code="FIRM-01",
        scope_description="단위 테스트 전용",
        is_real_world_verified=False,
    )
    validator = PartnerListingIntakeValidator(approval_proof=mock_approval)
    report = validator.validate_csv(io.StringIO(csv_data), is_synthetic=False)

    assert report.valid_rows == 1
    assert report.simulated_authorized_count == 1
    assert report.verified_real_data_count == 0  # 현실 세계 실제 데이터는 엄격히 0!
    assert report.real_ad_delegation_count == 0
    assert report.real_settled_count == 0


def test_forbidden_extra_columns_and_pii_rejection():
    """개인정보 컬럼 및 추가 컬럼 거절 검증."""
    csv_with_pii = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status,real_plate_number,owner_real_name
LST-PII-001,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED,12가3456,홍길동
"""
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(io.StringIO(csv_with_pii), is_synthetic=True)

    assert report.valid_rows == 0
    error_codes = [e.error_code for e in report.errors]
    assert "FORBIDDEN_EXTRA_COLUMN" in error_codes or "PII_COLUMN_PROHIBITED" in error_codes

    for err in report.errors:
        assert "12가3456" not in err.message
        assert "홍길동" not in err.message


def test_delegation_proof_security_expiry_revocation_and_third_party():
    """광고 위임 권한 보안 게이트 (만료, 철회, 제3자 상사 동의 부재)."""
    today = datetime.now(UTC).date()
    proof_valid = DelegationProof(
        proof_id="PROOF-01",
        internal_listing_id="LST-VALID",
        delegation_type="DIRECT_PURCHASE_OWNER",
        valid_until=today + timedelta(days=30),
        has_signed_document=True,
    )
    proof_expired = DelegationProof(
        proof_id="PROOF-02",
        internal_listing_id="LST-EXPIRED",
        delegation_type="DIRECT_PURCHASE_OWNER",
        valid_until=today - timedelta(days=1),
        has_signed_document=True,
    )
    proof_revoked = DelegationProof(
        proof_id="PROOF-03",
        internal_listing_id="LST-REVOKED",
        delegation_type="DIRECT_PURCHASE_OWNER",
        valid_until=today + timedelta(days=30),
        has_signed_document=True,
        is_revoked=True,
    )
    proof_consignment_no_consent = DelegationProof(
        proof_id="PROOF-04",
        internal_listing_id="LST-CONSIGNMENT-NO-CONSENT",
        delegation_type="THIRD_PARTY_CONSIGNMENT",
        valid_until=today + timedelta(days=30),
        has_signed_document=True,
        third_party_firm_consent=False,
    )

    csv_data = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-VALID,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
LST-EXPIRED,VEH-02,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
LST-REVOKED,VEH-03,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
LST-CONSIGNMENT-NO-CONSENT,VEH-04,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,CONSIGNMENT,FIRM-01,DLR-01,,,,,,,,UNSETTLED
"""
    validator = PartnerListingIntakeValidator(
        delegation_proofs=[proof_valid, proof_expired, proof_revoked, proof_consignment_no_consent]
    )
    report = validator.validate_csv(io.StringIO(csv_data), is_synthetic=True)

    assert report.total_rows == 4
    assert report.valid_rows == 4
    assert report.marketing_eligible_count == 1
    assert report.records[0].is_marketing_eligible is True
    assert report.records[1].is_marketing_eligible is False
    assert report.records[2].is_marketing_eligible is False
    assert report.records[3].is_marketing_eligible is False


def test_settlement_missing_amounts_and_negative_amounts_rejection():
    """정산 완료(SETTLED) 시 금액 누락 및 음수 수수료/비용 차단 검증."""
    csv_bad_settlement = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-SETTLE-MISSING,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,2026-10-10,14500000,600000,,,10000,545000,SETTLED
LST-SETTLE-NEG,VEH-02,기아,K5,3세대,노블레스,2020,2026-10-05,65000,가솔린,오토,블랙,없음,없음,없음,무,2026-10-05,INSP-01,18000000,19800000,18800000,DELEGATED,DIRECT_PURCHASE,FIRM-02,DLR-02,2026-10-12,19000000,-500000,15000,30000,10000,-555000,SETTLED
"""
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(io.StringIO(csv_bad_settlement), is_synthetic=True)

    assert report.valid_rows == 0
    assert report.rejected_rows == 2

    error_codes = [e.error_code for e in report.errors]
    assert "MISSING_SETTLED_AMOUNTS" in error_codes
    assert "NEGATIVE_SETTLEMENT_AMOUNT" in error_codes
