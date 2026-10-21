"""DIRECTIVE 004-A: 파트너 실매물 인입 검증기 및 데이터 품질 규칙 테스트."""

import io
from pathlib import Path

from chaficial.intake.validator import PartnerListingIntakeValidator


def test_intake_synthetic_sample_3_cars_success():
    """테스트 1: 정상 합성 매물 3건은 데이터 구조 검증을 100% 통과해야 함."""
    sample_path = Path("templates/PARTNER_LISTING_INTAKE_SYNTHETIC_SAMPLE.csv")
    assert sample_path.exists(), "합성 샘플 파일이 존재해야 합니다."

    # 서면 위임 증빙이 확인되지 않은 기본 상태
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(sample_path, is_synthetic=True)

    assert report.total_rows == 3
    assert report.valid_rows == 3
    assert report.rejected_rows == 0
    assert report.synthetic_data_count == 3
    assert report.real_data_count == 0  # 현재 실제 데이터 수는 0건

    # 서면 위임 증빙이 없으므로 마케팅 가능 차량은 0건이어야 함 (안전 게이트)
    assert report.marketing_eligible_count == 0
    assert len(report.errors) == 0

    # ORM 매핑 미리보기 검증 (DRY-RUN)
    valid_record = report.records[0]
    orm_preview = PartnerListingIntakeValidator.preview_orm_mappings(valid_record)
    assert orm_preview["VehicleCatalog"]["manufacturer"] == "현대"
    assert orm_preview["Listing"]["source_platform"] == "PARTNER_DIRECT_INTAKE"
    assert orm_preview["VehicleIdentity"]["plate_number"] is None  # 비식별화 준수


def test_intake_rejection_on_negative_price_duplicate_id_and_invalid_date():
    """테스트 2: 음수 가격, 중복 ID, 잘못된 날짜, 미계약 차량의 조기수익 기재 등 오류 감지 및 인입 거절."""
    csv_bad_data = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-BAD-001,VEH-B01,현대,아반떼,CN7,모던,2021,2026-10-01,-5000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,-15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
LST-BAD-001,VEH-B02,기아,K5,3세대,노블레스,2020,INVALID_DATE,65000,가솔린,오토,블랙,없음,없음,없음,무,2026-10-05,INSP-01,18000000,19800000,18800000,DELEGATED,CONSIGNMENT,FIRM-02,DLR-02,,,,,,,,UNSETTLED
LST-BAD-003,VEH-B03,현대,그랜저,IG,익스클루시브,2019,2026-10-08,88000,가솔린,오토,그레이,없음,없음,없음,무,2026-10-08,INSP-01,16200000,17900000,16900000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,17500000,,,500000,,UNSETTLED
"""
    validator = PartnerListingIntakeValidator()
    report = validator.validate_csv(io.StringIO(csv_bad_data), is_synthetic=True)

    assert report.total_rows == 3
    assert report.valid_rows == 0
    assert report.rejected_rows == 3

    # 필드별 오류 발생 확인
    assert "mileage_km" in report.errors_by_field  # 음수 주행거리
    assert "target_listing_price_krw" in report.errors_by_field  # 음수 목표가
    assert "internal_listing_id" in report.errors_by_field  # 중복 ID
    assert "first_observed_date" in report.errors_by_field  # 잘못된 날짜
    assert "actual_contract_price_krw" in report.errors_by_field  # 미계약 매물의 조기 계약가 기재


def test_intake_delegation_gate_marketing_eligibility():
    """테스트 3: 광고 권한 미확인 차량은 데이터 구조가 정상이어도 마케팅 대상에서 엄격 제외되어야 함."""
    csv_mixed_delegation = """internal_listing_id,anonymous_vehicle_code,manufacturer,model_name,sub_model,trim,model_year,first_observed_date,mileage_km,fuel_type,transmission,color_category,outer_panel_rank1_damage,structural_rank2_damage,oil_leak_status,flood_damage_status,inspection_date,inspector_code,cost_price_krw,target_listing_price_krw,min_acceptable_price_krw,advertising_delegation_status,inventory_type,partner_firm_code,partner_dealer_code,contract_closed_date,actual_contract_price_krw,gross_commission_revenue_krw,video_production_cost_krw,ad_spend_krw,other_operational_costs_krw,net_profit_krw,settlement_status
LST-AUTH-001,VEH-A01,현대,아반떼,CN7,모던,2021,2026-10-01,42000,가솔린,오토,화이트,없음,없음,없음,무,2026-10-01,INSP-01,13500000,15000000,14000000,DELEGATED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
LST-NOAUTH-002,VEH-A02,기아,K5,3세대,노블레스,2020,2026-10-05,65000,가솔린,오토,블랙,없음,없음,없음,무,2026-10-05,INSP-01,18000000,19800000,18800000,DELEGATED,CONSIGNMENT,FIRM-02,DLR-02,,,,,,,,UNSETTLED
LST-DENIED-003,VEH-A03,현대,그랜저,IG,익스클루시브,2019,2026-10-08,88000,가솔린,오토,그레이,없음,없음,없음,무,2026-10-08,INSP-01,16200000,17900000,16900000,UNVERIFIED,DIRECT_PURCHASE,FIRM-01,DLR-01,,,,,,,,UNSETTLED
"""
    # LST-AUTH-001 건에 대해서만 실물 서면 위임장이 확보/확인된 상태 주입
    validator = PartnerListingIntakeValidator(verified_delegation_ids={"LST-AUTH-001"})
    report = validator.validate_csv(io.StringIO(csv_mixed_delegation), is_synthetic=True)

    assert report.total_rows == 3
    assert report.valid_rows == 3
    assert report.rejected_rows == 0

    # 3건 모두 데이터 무결성은 통과했으나, 오직 서면 위임이 검증된 1건만 마케팅 대상
    assert report.marketing_eligible_count == 1
    assert report.records[0].is_marketing_eligible is True
    assert report.records[1].is_marketing_eligible is False  # 'DELEGATED' 문자열만 있고 서면 미확인
    assert report.records[2].is_marketing_eligible is False  # UNVERIFIED
