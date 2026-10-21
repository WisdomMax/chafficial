"""DIRECTIVE 004-B FINAL AUDIT: 인입 엔진 보안·데이터 무결성 및 TimeTravel 시계열 실증 테스트."""

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
from chaficial.time_travel.query_engine import TimeTravelQueryEngine


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
    [필수 반례 1: 정상 합성 매물 3건의 ORM 생성 및 SQLite 실제 FLUSH/ROLLBACK 검증]
    - 합성 매물 3건 가격/연식/주행거리 검증 통과.
    - ORM 엔티티 생성 및 SQLite 실제 INSERT/FLUSH 성공.
    - ROLLBACK 후 DB 잔존 레코드 0건 검증.
    """
    sample_path = Path("templates/PARTNER_LISTING_INTAKE_SYNTHETIC_SAMPLE.csv")
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(sample_path, is_synthetic=True)

    assert report.total_rows == 3
    assert report.valid_rows == 3
    assert report.synthetic_data_count == 3
    assert report.verified_real_data_count == 0  # 실데이터 0건 유지

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
        assert session.query(Listing).count() == 0


def test_time_travel_query_engine_point_in_time_ingestion(sqlite_test_db):
    """
    [CRITICAL 2: TimeTravelQueryEngine을 통한 실제 DB 기반 과거 조회 검증]
    - 2026-10-01: 최초 등록 사실 발생 (observed_at = 10/01)
    - 2026-10-10: 실제 계약 체결 (observed_at = 10/10)
    - 2026-10-15: 위 두 사실을 차피셜 DB에 적재 (ingested_at = 10/15)
    - 조회 검증:
      * 10월 5일 조회: 스냅샷 없음 (ingested_at이 10/15이므로 당시엔 알 수 없었음)
      * 10월 11일 조회: 스냅샷 없음 (10/15 적재 전이므로 당시엔 알 수 없었음)
      * 10월 14일 조회: 스냅샷 없음 (10/15 적재 전이므로 당시엔 알 수 없었음)
      * 10월 16일 조회: 10/15까지 실제 적재된 기록에 따라 10/10 계약 스냅샷(DELISTED) 정상 조회
    """
    csv_single_sold_car = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-TT-01,VEH-T01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,2026-10-10,14200000,600000,15000,30000,10000,545000,SETTLED
"""
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(io.StringIO(csv_single_sold_car), is_synthetic=True)
    record = report.records[0]

    # 시스템 적재 시각: 10월 15일 12:00:00 UTC
    ingest_time_oct_15 = datetime(2026, 10, 15, 12, 0, 0, tzinfo=UTC)

    with Session(sqlite_test_db) as session:
        catalog, identity, listing, snapshots = PartnerListingIntakeValidator.build_orm_entities(
            record,
            target_region_id="REGION_JANGANPYEONG",
            raw_location="서울 장안평 매매단지",
            system_ingested_at=ingest_time_oct_15,
            contract_ingested_at=ingest_time_oct_15,
        )
        session.add_all([catalog, identity, listing])
        session.add_all(snapshots)
        session.commit()

        # 1) 10월 5일 과거 시점 조회 (ingested_at 10/15 이전이므로 스냅샷 없어야 함)
        snap_oct_5 = TimeTravelQueryEngine.get_listing_snapshot_at(
            session, "LST-TT-01", datetime(2026, 10, 5, tzinfo=UTC)
        )
        assert snap_oct_5 is None, "10월 5일 당시에는 DB에 적재되지 않았으므로 스냅샷이 조회되면 안 됩니다."

        # 2) 10월 11일 과거 시점 조회 (ingested_at 10/15 이전이므로 스냅샷 없어야 함)
        snap_oct_11 = TimeTravelQueryEngine.get_listing_snapshot_at(
            session, "LST-TT-01", datetime(2026, 10, 11, tzinfo=UTC)
        )
        assert snap_oct_11 is None, "10월 11일 당시에도 DB 적재 전이므로 조회되면 안 됩니다."

        # 3) 10월 14일 과거 시점 조회 (적재 전)
        snap_oct_14 = TimeTravelQueryEngine.get_listing_snapshot_at(
            session, "LST-TT-01", datetime(2026, 10, 14, tzinfo=UTC)
        )
        assert snap_oct_14 is None

        # 4) 10월 16일 조회 (10/15 적재 이후이므로 최신 DELISTED 스냅샷 정상 조회)
        snap_oct_16 = TimeTravelQueryEngine.get_listing_snapshot_at(
            session, "LST-TT-01", datetime(2026, 10, 16, tzinfo=UTC)
        )
        assert snap_oct_16 is not None
        assert snap_oct_16.listing_status == "DELISTED"
        assert snap_oct_16.observed_at.date() == datetime(2026, 10, 10, tzinfo=UTC).date()


def test_separation_of_asking_price_and_contract_price(sqlite_test_db):
    """
    [HIGH 3: 등록가(호가)와 실제 계약가의 혼동 방지 실증]
    - 등록가 1,500만원, 확정 계약가 1,420만원인 차량에서
    - 종료 스냅샷의 price_krw는 시장 등록가 호가(1,500만원)를 그대로 유지해야 하며,
    - 실계약가는 raw_specs에 분리 기록되어야 함 (호가 왜곡 방지).
    """
    csv_car = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-PRICE-01,VEH-P01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,2026-10-10,14200000,600000,15000,30000,10000,545000,SETTLED
"""
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(io.StringIO(csv_car), is_synthetic=True)
    record = report.records[0]

    _, _, _, snapshots = PartnerListingIntakeValidator.build_orm_entities(record)
    assert len(snapshots) == 2
    closed_snap = snapshots[1]

    # 호가 불변성: 스냅샷 price_krw는 1500만원이어야 함
    assert closed_snap.price_krw == 15000000, "시장 호가 이력의 price_krw가 실계약가로 왜곡되어선 안 됩니다."
    # 실계약가는 raw_specs에 분리 보존
    assert closed_snap.raw_specs["actual_contract_price_krw"] == 14200000


def test_disallow_hallucinated_specs_null_displacement_and_seating():
    """
    [필수 반례 2: 부존재 차량 제원 날조 방지]
    - 입력 근거 없는 배기량 및 좌석수는 NULL(None) 유지.
    - 연식 누락 시 인입 거절.
    """
    sample_path = Path("templates/PARTNER_LISTING_INTAKE_SYNTHETIC_SAMPLE.csv")
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(sample_path, is_synthetic=True)
    record = report.records[0]

    catalog, _, _, _ = PartnerListingIntakeValidator.build_orm_entities(record)
    assert catalog.displacement_cc is None
    assert catalog.seating_capacity is None

    csv_no_year = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-NO-YEAR,VEH-01,현대,아반떼,CN7,모던,,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
"""
    report_no_year = validator.validate_csv(io.StringIO(csv_no_year), is_synthetic=True)
    assert report_no_year.valid_rows == 0
    assert "MISSING_MODEL_YEAR" in [e.error_code for e in report_no_year.errors]


def test_no_default_location_hallucination():
    """
    [필수 반례 3: 위치 및 지역 정보 임의 생성 차단]
    - 위치 미지정 시 None / LOCATION_UNCONFIRMED 보존.
    """
    sample_path = Path("templates/PARTNER_LISTING_INTAKE_SYNTHETIC_SAMPLE.csv")
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(sample_path, is_synthetic=True)
    record = report.records[0]

    _, _, listing, snapshot = PartnerListingIntakeValidator.build_orm_entities(
        record, target_region_id=None, raw_location=None
    )
    assert listing.normalized_region_id is None
    assert listing.raw_location == "LOCATION_UNCONFIRMED"
    assert snapshot[0].normalized_region_id is None


def test_real_world_token_removal_and_bypass_prevention():
    """
    [CRITICAL 1: 공개 소스의 승인 토큰 제거 및 실데이터 승격 차단 실증]
    - 임의의 토큰이나 구버전 토큰, 단순 승인 객체를 주입하더라도
      VERIFIED_REAL로 승격되지 않고 SIMULATED_AUTHORIZED로 안전 격리됨.
    - verified_real_data_count는 항상 0건 유지.
    """
    csv_data = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-SEC-01,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
"""
    # 과거 구버전 토큰 주입 시도
    fake_proof = IntakeApprovalProof(
        approval_id="FAKE-01",
        approved_by="공격자",
        approved_at=datetime.now(UTC),
        data_source="외부",
        target_firm_code="FIRM-01",
        scope_description="우회 시도",
        verification_token="CHAFICIAL_DIRECTOR_2026_OFFICIAL_VERIFIED",
        is_real_world_verified=True,
    )
    validator = PartnerListingIntakeValidator(approval_proof=fake_proof)
    report = validator.validate_csv(io.StringIO(csv_data), is_synthetic=False)

    assert report.valid_rows == 1
    # 실데이터 승격이 원천 차단되어 0건으로 유지되어야 함!
    assert report.verified_real_data_count == 0
    assert report.simulated_authorized_count == 1
    assert report.records[0].data_classification == "SIMULATED_AUTHORIZED"


def test_forbidden_extra_columns_and_pii_rejection():
    """[필수 반례 4: 개인정보 컬럼 차단 및 오류 메시지 내 민감값 비노출]."""
    csv_pii = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status,real_plate_number,owner_real_name
LST-PII-001,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED,12가3456,홍길동
"""
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(io.StringIO(csv_pii), is_synthetic=True)

    assert report.valid_rows == 0
    error_codes = [e.error_code for e in report.errors]
    assert "FORBIDDEN_EXTRA_COLUMN" in error_codes or "PII_COLUMN_PROHIBITED" in error_codes

    for err in report.errors:
        assert "12가3456" not in err.message
        assert "홍길동" not in err.message


def test_delegation_proof_security_expiry_revocation_and_third_party():
    """[필수 반례 5: 광고 위임 권한 보안 게이트 (만료, 철회, 제3자 상사 동의 부재)]."""
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
    assert report.live_ad_authorized_count == 0  # 실제 게시 허가는 항상 False


def test_settlement_missing_amounts_and_negative_amounts_rejection():
    """[필수 반례 6: 정산 완료(SETTLED) 시 금액 누락 및 음수 수수료/비용 차단 검증]."""
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


def test_csv_parser_rfc4180_edge_cases():
    """
    [필수 반례 7: CSV 형식 및 파서 반례 검증]
    - 인용부호 내 줄바꿈 및 쉼표 포함 정상 파싱.
    - 인용부호 내 #로 시작하는 줄 보존.
    - 중복 헤더 차단.
    - 열 개수 오류 차단.
    """
    csv_quoted_hash = '''internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-HASH-01,VEH-01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,"#특이사항: 전면 휀더 교환
#사고없음",없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
'''
    validator = PartnerListingIntakeValidator()
    report_hash = validator.validate_csv(io.StringIO(csv_quoted_hash), is_synthetic=True)
    assert report_hash.valid_rows == 1
    damage_text = report_hash.records[0].normalized_data["outer_panel_rank1_damage"]
    assert "#특이사항" in damage_text

    csv_dup = "internal_listing_id,internal_listing_id,model_name\n1,2,아반떼\n"
    report_dup = validator.validate_csv(io.StringIO(csv_dup), is_synthetic=True)
    assert report_dup.valid_rows == 0
    assert any(e.error_code == "DUPLICATE_HEADER" for e in report_dup.errors)

    csv_col_err = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-SHORT,VEH-01,현대,아반떼
"""
    report_col_err = validator.validate_csv(io.StringIO(csv_col_err), is_synthetic=True)
    assert report_col_err.valid_rows == 0
    assert any(e.error_code == "COLUMN_COUNT_MISMATCH" for e in report_col_err.errors)
