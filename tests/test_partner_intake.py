"""DIRECTIVE 004-A FINAL AUDIT FIX: 파트너 실매물 인입 엔진 무결성 및 ORM 제약조건 실증 테스트."""

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

    # 기본 지역 데이터 시드 주입 (REGION_JANGANPYEONG)
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
        # 트랜잭션 내에서 3건 모두 ORM 엔티티 생성 및 FLUSH
        for record in report.records:
            catalog, identity, listing, snapshot = PartnerListingIntakeValidator.build_orm_entities(
                record,
                target_region_id="REGION_JANGANPYEONG",
                raw_location="서울 성동구 장안평 중고차 매매단지",
            )
            session.add_all([catalog, identity, listing, snapshot])

        # 실제 SQL INSERT 및 제약조건 검증 (예외 발생 시 테스트 실패)
        session.flush()

        # DB 내 적재 확인
        assert len(session.new) == 0  # flush 성공으로 pending 상태 해소
        # DRY RUN 보장을 위해 롤백
        session.rollback()

    # 롤백 후 DB 오염 없음 확인
    with Session(sqlite_test_db) as session:
        from chaficial.models.listing import Listing
        count = session.query(Listing).count()
        assert count == 0, "DRY RUN 후 테스트 DB에 레코드가 잔존하지 않아야 합니다."


def test_forbidden_extra_columns_and_pii_rejection():
    """
    CRITICAL 2: 엄격한 헤더 정책 - 허용되지 않은 추가 컬럼 및
    차량번호/VIN 등 개인정보 컬럼 유입 시 즉시 거절 및 민감값 비노출 검증.
    """
    csv_with_pii = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status,real_plate_number,owner_real_name
LST-PII-001,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED,12가3456,홍길동
"""
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(io.StringIO(csv_with_pii), is_synthetic=True)

    assert report.valid_rows == 0
    assert len(report.errors) > 0

    # FORBIDDEN_EXTRA_COLUMN 또는 PII_COLUMN_PROHIBITED 에러 코드 검출
    error_codes = [e.error_code for e in report.errors]
    assert "FORBIDDEN_EXTRA_COLUMN" in error_codes or "PII_COLUMN_PROHIBITED" in error_codes

    # 에러 메시지 내에 실명이나 차량번호 등 원본 개인정보 값이 노출되지 않는지 확인
    for err in report.errors:
        assert "12가3456" not in err.message
        assert "홍길동" not in err.message


def test_delegation_proof_security_expiry_revocation_and_third_party():
    """
    HIGH 3: 광고 위임 권한 보안 게이트:
    1) 유효기간 만료 시 마케팅 제외
    2) 권한 철회(revoked) 시 마케팅 제외
    3) 제3자 상사(CONSIGNMENT) 차량의 동의 미확인 시 마케팅 제외
    4) 정상 유효 위임장 보유 시에만 마케팅 허용
    """
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
        valid_until=today - timedelta(days=1),  # 어제 만료
        has_signed_document=True,
    )
    proof_revoked = DelegationProof(
        proof_id="PROOF-03",
        internal_listing_id="LST-REVOKED",
        delegation_type="DIRECT_PURCHASE_OWNER",
        valid_until=today + timedelta(days=30),
        has_signed_document=True,
        is_revoked=True,  # 철회됨
    )
    proof_consignment_no_consent = DelegationProof(
        proof_id="PROOF-04",
        internal_listing_id="LST-CONSIGNMENT-NO-CONSENT",
        delegation_type="THIRD_PARTY_CONSIGNMENT",
        valid_until=today + timedelta(days=30),
        has_signed_document=True,
        third_party_firm_consent=False,  # 제3자 동의 없음
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
    assert report.valid_rows == 4  # 데이터 구조 자체는 유효

    # 마케팅 가능 차량은 오직 유효한 proof_valid 1건만 통과되어야 함!
    assert report.marketing_eligible_count == 1
    assert report.records[0].is_marketing_eligible is True
    assert report.records[1].is_marketing_eligible is False  # 만료
    assert report.records[2].is_marketing_eligible is False  # 철회
    assert report.records[3].is_marketing_eligible is False  # 제3자 상사 동의 부재


def test_settlement_missing_amounts_and_negative_amounts_rejection():
    """
    HIGH 4: 정산 완료(SETTLED) 시 금액 누락 및 음수 수수료/비용 차단 검증.
    """
    csv_bad_settlement = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-SETTLE-MISSING,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,2026-10-10,14500000,600000,,,10000,545000,SETTLED
LST-SETTLE-NEG,VEH-02,기아,K5,3세대,노블레스,2020,2026-10-05,65000,가솔린,오토,블랙,없음,없음,없음,무,2026-10-05,INSP-01,18000000,19800000,18800000,DELEGATED,DIRECT_PURCHASE,FIRM-02,DLR-02,2026-10-12,19000000,-500000,15000,30000,10000,-555000,SETTLED
"""
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(io.StringIO(csv_bad_settlement), is_synthetic=True)

    assert report.valid_rows == 0
    assert report.rejected_rows == 2

    error_codes = [e.error_code for e in report.errors]
    assert "MISSING_SETTLED_AMOUNTS" in error_codes  # 비어있는 필드를 0으로 임의 대체하지 않고 거절
    assert "NEGATIVE_SETTLEMENT_AMOUNT" in error_codes  # 음수 수수료 거절


def test_strict_separation_of_synthetic_and_real_data():
    """
    HIGH 5: 합성 데이터와 실데이터의 엄격한 분리:
    - 단순 Boolean `is_synthetic=False` 호출만으로 real_data_count가 오르지 않음.
    - 공식 사장님(관리자) 승인 증빙(IntakeApprovalProof)이 명시적으로 주입되지 않으면 UNVERIFIED_EXTERNAL로 격리.
    """
    csv_data = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-UNVERIFIED-01,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
"""
    # 1. 승인 증빙 없이 is_synthetic=False 로 호출한 경우
    validator_no_proof = PartnerListingIntakeValidator()
    report_unverified = validator_no_proof.validate_csv(io.StringIO(csv_data), is_synthetic=False)

    assert report_unverified.verified_real_data_count == 0  # 검증된 실데이터 건수는 여전히 0!
    assert report_unverified.unverified_external_count == 1  # 미검증 외부 데이터로 안전 격리
    assert report_unverified.records[0].data_classification == "UNVERIFIED_EXTERNAL"

    # 2. 공식 관리자 승인 증빙이 명시된 경우에만 VERIFIED_REAL로 승격
    approval = IntakeApprovalProof(
        approval_id="APP-2026-001",
        approved_by="사장님 (차피셜 총괄)",
        approved_at=datetime.now(UTC),
        data_source="서울 장안평 제휴 상사 실사 자료",
        target_firm_code="FIRM-JANGANPYEONG-01",
        scope_description="최초 실매물 파일럿 검증용",
    )
    validator_approved = PartnerListingIntakeValidator(approval_proof=approval)
    report_approved = validator_approved.validate_csv(io.StringIO(csv_data), is_synthetic=False)

    assert report_approved.verified_real_data_count == 1
    assert report_approved.records[0].data_classification == "VERIFIED_REAL"
