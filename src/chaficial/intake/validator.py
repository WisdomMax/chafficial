"""차피셜 파트너 실매물 데이터 인입 및 품질 검증 모듈."""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class ValidationError:
    row_number: int
    field_name: str
    error_code: str
    message: str


@dataclass
class IntakeRecordResult:
    row_number: int
    internal_listing_id: str
    is_valid: bool
    is_marketing_eligible: bool
    is_synthetic: bool
    rejection_reasons: list[str] = field(default_factory=list)
    raw_data: dict[str, str] = field(default_factory=dict)
    normalized_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntakeValidationReport:
    total_rows: int = 0
    valid_rows: int = 0
    rejected_rows: int = 0
    marketing_eligible_count: int = 0
    real_data_count: int = 0
    synthetic_data_count: int = 0
    errors_by_field: dict[str, int] = field(default_factory=dict)
    errors: list[ValidationError] = field(default_factory=list)
    records: list[IntakeRecordResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": {
                "total_rows": self.total_rows,
                "valid_rows": self.valid_rows,
                "rejected_rows": self.rejected_rows,
                "marketing_eligible_count": self.marketing_eligible_count,
                "real_data_count": self.real_data_count,
                "synthetic_data_count": self.synthetic_data_count,
                "errors_by_field": self.errors_by_field,
            },
            "records": [asdict(r) for r in self.records],
            "error_count": len(self.errors),
        }


REQUIRED_HEADERS = [
    "internal_listing_id",
    "anonymous_vehicle_code",
    "manufacturer",
    "model_name",
    "sub_model",
    "trim",
    "model_year",
    "first_observed_date",
    "mileage_km",
    "fuel_type",
    "transmission",
    "color_category",
    "outer_panel_rank1_damage",
    "structural_rank2_damage",
    "oil_leak_status",
    "flood_damage_status",
    "inspection_date",
    "inspector_code",
    "cost_price_krw",
    "target_listing_price_krw",
    "min_acceptable_price_krw",
    "advertising_delegation_status",
    "inventory_type",
    "partner_firm_code",
    "partner_dealer_code",
    "contract_closed_date",
    "actual_contract_price_krw",
    "gross_commission_revenue_krw",
    "video_production_cost_krw",
    "ad_spend_krw",
    "other_operational_costs_krw",
    "net_profit_krw",
    "settlement_status",
]


class PartnerListingIntakeValidator:
    """파트너 실매물 CSV 입력값의 무결성 및 광고 권한을 검증하는 엔진."""

    def __init__(self, verified_delegation_ids: set[str] | None = None) -> None:
        """
        verified_delegation_ids: 서면 위임장 또는 제휴 계약서가 실제 확인된 internal_listing_id 집합.
        지정되지 않은 경우 단순 'DELEGATED' 문자열이 있더라도 마케팅 대상에서 제외됨.
        """
        self.verified_delegation_ids = verified_delegation_ids or set()

    def validate_csv(
        self,
        source: str | Path | io.StringIO,
        is_synthetic: bool = True,
    ) -> IntakeValidationReport:
        """CSV 소스를 파싱하고 10대 데이터 품질 규칙을 검증합니다."""
        report = IntakeValidationReport()

        if isinstance(source, (str, Path)) and not isinstance(source, io.StringIO):
            source_path = Path(source)
            if not source_path.exists():
                report.errors.append(
                    ValidationError(0, "file", "FILE_NOT_FOUND", f"파일을 찾을 수 없습니다: {source_path}")
                )
                return report
            with open(source_path, encoding="utf-8-sig") as f:
                content = f.read()
        elif isinstance(source, io.StringIO):
            content = source.getvalue()
        else:
            content = str(source)

        # 주석행(#) 및 빈 행 필터링
        filtered_lines = [
            line for line in content.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        if not filtered_lines:
            report.errors.append(ValidationError(0, "file", "EMPTY_FILE", "유효한 데이터 행이 없습니다."))
            return report

        reader = csv.DictReader(filtered_lines)
        if reader.fieldnames is None:
            report.errors.append(ValidationError(0, "header", "MISSING_HEADER", "CSV 헤더가 존재하지 않습니다."))
            return report

        # 필수 헤더 검증
        missing_headers = [h for h in REQUIRED_HEADERS if h not in reader.fieldnames]
        if missing_headers:
            for mh in missing_headers:
                report.errors.append(
                    ValidationError(0, mh, "MISSING_REQUIRED_COLUMN", f"필수 컬럼이 누락되었습니다: {mh}")
                )
                report.errors_by_field[mh] = report.errors_by_field.get(mh, 0) + 1
            return report

        seen_listing_ids: set[str] = set()

        for row_idx, row in enumerate(reader, start=1):
            report.total_rows += 1
            if is_synthetic:
                report.synthetic_data_count += 1
            else:
                report.real_data_count += 1

            row_errors: list[ValidationError] = []
            normalized: dict[str, Any] = {}

            # 1. internal_listing_id (식별 무결성)
            listing_id = (row.get("internal_listing_id") or "").strip()
            if not listing_id:
                row_errors.append(
                    ValidationError(row_idx, "internal_listing_id", "MISSING_LISTING_ID", "내부 매물 ID는 필수입니다.")
                )
            elif listing_id in seen_listing_ids:
                row_errors.append(
                    ValidationError(
                        row_idx, "internal_listing_id", "DUPLICATE_INTERNAL_ID", f"중복된 매물 ID입니다: {listing_id}"
                    )
                )
            else:
                seen_listing_ids.add(listing_id)
            normalized["internal_listing_id"] = listing_id

            # 2. anonymous_vehicle_code (차량 식별 미확정 허용)
            anon_code = (row.get("anonymous_vehicle_code") or "").strip()
            normalized["anonymous_vehicle_code"] = anon_code if anon_code else None

            # 3. manufacturer, model_name
            mfr = (row.get("manufacturer") or "").strip()
            model = (row.get("model_name") or "").strip()
            if not mfr:
                row_errors.append(
                    ValidationError(row_idx, "manufacturer", "MISSING_MANUFACTURER", "제조사명은 필수입니다.")
                )
            if not model:
                row_errors.append(
                    ValidationError(row_idx, "model_name", "MISSING_MODEL_NAME", "모델명은 필수입니다.")
                )
            normalized["manufacturer"] = mfr
            normalized["model_name"] = model
            normalized["sub_model"] = (row.get("sub_model") or "").strip()
            normalized["trim"] = (row.get("trim") or "").strip()

            # 4. model_year (연식 검증)
            year_str = (row.get("model_year") or "").strip()
            try:
                year = int(year_str)
                current_year = datetime.now(UTC).year
                if year < 1990 or year > current_year + 1:
                    row_errors.append(
                        ValidationError(
                            row_idx, "model_year", "INVALID_MODEL_YEAR", f"비정상적인 연식 범위입니다: {year}"
                        )
                    )
                normalized["model_year"] = year
            except ValueError:
                row_errors.append(
                    ValidationError(
                        row_idx, "model_year", "INVALID_YEAR_TYPE", f"연식은 정수형이어야 합니다: {year_str}"
                    )
                )
                normalized["model_year"] = None

            # 5. mileage_km (음수 주행거리 차단)
            mileage_str = (row.get("mileage_km") or "").strip()
            try:
                mileage = int(mileage_str)
                if mileage < 0:
                    row_errors.append(
                        ValidationError(
                            row_idx, "mileage_km", "NEGATIVE_MILEAGE", f"주행거리는 음수일 수 없습니다: {mileage}"
                        )
                    )
                normalized["mileage_km"] = mileage
            except ValueError:
                row_errors.append(
                    ValidationError(
                        row_idx, "mileage_km", "INVALID_MILEAGE_TYPE", f"주행거리는 정수형이어야 합니다: {mileage_str}"
                    )
                )
                normalized["mileage_km"] = None

            # 6. first_observed_date (필수 날짜)
            obs_date_str = (row.get("first_observed_date") or "").strip()
            if not obs_date_str:
                row_errors.append(
                    ValidationError(
                        row_idx, "first_observed_date", "MISSING_OBSERVED_DATE", "최초 관측일은 필수입니다."
                    )
                )
            else:
                try:
                    datetime.strptime(obs_date_str, "%Y-%m-%d")
                    normalized["first_observed_date"] = obs_date_str
                except ValueError:
                    row_errors.append(
                        ValidationError(
                            row_idx, "first_observed_date", "INVALID_DATE_FORMAT", f"날짜 형식이 올바르지 않습니다(YYYY-MM-DD): {obs_date_str}"
                        )
                    )

            # 7. inspection_date (선택적 날짜, 순서 고정 가정 안 함)
            insp_date_str = (row.get("inspection_date") or "").strip()
            if insp_date_str:
                try:
                    datetime.strptime(insp_date_str, "%Y-%m-%d")
                    normalized["inspection_date"] = insp_date_str
                except ValueError:
                    row_errors.append(
                        ValidationError(
                            row_idx, "inspection_date", "INVALID_DATE_FORMAT", f"점검일 날짜 형식이 올바르지 않습니다: {insp_date_str}"
                        )
                    )
            else:
                normalized["inspection_date"] = None

            # 8. 가격 필드 검증 (호가, 매입가, 최저가 음수 차단)
            target_price_str = (row.get("target_listing_price_krw") or "").strip()
            try:
                target_price = int(target_price_str)
                if target_price <= 0:
                    row_errors.append(
                        ValidationError(
                            row_idx, "target_listing_price_krw", "NEGATIVE_OR_ZERO_PRICE", f"목표 등록가는 0보다 커야 합니다: {target_price}"
                        )
                    )
                normalized["target_listing_price_krw"] = target_price
            except ValueError:
                row_errors.append(
                    ValidationError(
                        row_idx, "target_listing_price_krw", "INVALID_PRICE_TYPE", f"목표 등록가는 정수형이어야 합니다: {target_price_str}"
                    )
                )
                normalized["target_listing_price_krw"] = None

            # 매입가 / 최저가
            for p_field in ["cost_price_krw", "min_acceptable_price_krw"]:
                p_val_str = (row.get(p_field) or "").strip()
                if p_val_str:
                    try:
                        p_val = int(p_val_str)
                        if p_val < 0:
                            row_errors.append(
                                ValidationError(row_idx, p_field, "NEGATIVE_PRICE", f"{p_field}는 음수일 수 없습니다: {p_val}")
                            )
                        normalized[p_field] = p_val
                    except ValueError:
                        row_errors.append(
                            ValidationError(row_idx, p_field, "INVALID_PRICE_TYPE", f"{p_field}는 정수형이어야 합니다: {p_val_str}")
                        )
                else:
                    normalized[p_field] = None

            # 9. 차량 상태 (골격 손상 vs 외판 손상 분리, 침수 미확인 분리)
            outer_damage = (row.get("outer_panel_rank1_damage") or "").strip()
            struct_damage = (row.get("structural_rank2_damage") or "").strip()
            flood_status = (row.get("flood_damage_status") or "").strip()
            inspector = (row.get("inspector_code") or "").strip()

            normalized["outer_panel_rank1_damage"] = outer_damage or "미확인"
            normalized["structural_rank2_damage"] = struct_damage or "미확인"
            normalized["flood_damage_status"] = flood_status or "미확인"
            normalized["inspector_code"] = inspector or None

            # 점검자 코드가 없는데 점검 결과가 '완전무사고' 등으로 기록된 경우 경고/미확인 처리
            if not inspector and (struct_damage != "미확인" or outer_damage != "미확인"):
                row_errors.append(
                    ValidationError(
                        row_idx, "inspector_code", "UNVERIFIED_INSPECTION_RECORD", "성능점검자 식별코드 없이 점검 결과를 확정할 수 없습니다."
                    )
                )

            # 10. 광고 위임 상태 (문자열 'DELEGATED'만으로 승인하지 않음)
            ad_status = (row.get("advertising_delegation_status") or "").strip()
            normalized["advertising_delegation_status"] = ad_status

            # 11. 계약 및 정산 (조기 수익 인식 차단)
            closed_date_str = (row.get("contract_closed_date") or "").strip()
            contract_price_str = (row.get("actual_contract_price_krw") or "").strip()
            net_profit_str = (row.get("net_profit_krw") or "").strip()
            settlement_status = (row.get("settlement_status") or "").strip() or "UNSETTLED"

            if closed_date_str:
                try:
                    datetime.strptime(closed_date_str, "%Y-%m-%d")
                    normalized["contract_closed_date"] = closed_date_str
                except ValueError:
                    row_errors.append(
                        ValidationError(row_idx, "contract_closed_date", "INVALID_DATE_FORMAT", f"계약일 형식 오류: {closed_date_str}")
                    )
            else:
                normalized["contract_closed_date"] = None

            # 미계약 상태인데 계약가나 확정 순수익이 기재된 경우 오류
            if not closed_date_str:
                if contract_price_str:
                    row_errors.append(
                        ValidationError(
                            row_idx, "actual_contract_price_krw", "PREMATURE_CONTRACT_PRICE", "계약일자가 없는 미계약 매물에 계약가를 임의 기재할 수 없습니다."
                        )
                    )
                if net_profit_str:
                    row_errors.append(
                        ValidationError(
                            row_idx, "net_profit_krw", "PREMATURE_PROFIT_RECOGNITION", "미계약 매물의 수익을 확정값으로 기록할 수 없습니다."
                        )
                    )

            # 계약 완료 시 금액 무결성 (순수익 = 수수료 - 비용합산)
            if closed_date_str and settlement_status == "SETTLED":
                try:
                    c_rev = int((row.get("gross_commission_revenue_krw") or "0").strip())
                    v_cost = int((row.get("video_production_cost_krw") or "0").strip())
                    a_cost = int((row.get("ad_spend_krw") or "0").strip())
                    o_cost = int((row.get("other_operational_costs_krw") or "0").strip())
                    actual_net = int((row.get("net_profit_krw") or "0").strip())

                    calculated_net = c_rev - (v_cost + a_cost + o_cost)
                    if actual_net != calculated_net:
                        row_errors.append(
                            ValidationError(
                                row_idx,
                                "net_profit_krw",
                                "NET_PROFIT_MISMATCH",
                                f"순수익 불일치: 수수료({c_rev}) - 비용합계({v_cost+a_cost+o_cost}) = {calculated_net} != 기재순수익({actual_net})",
                            )
                        )
                except ValueError:
                    row_errors.append(
                        ValidationError(row_idx, "net_profit_krw", "INVALID_COST_NUMBER", "정산 금액 필드에 비숫자 값이 포함되어 있습니다.")
                    )

            # 에러 집계 및 행 판정
            is_valid = len(row_errors) == 0

            # 마케팅 가능 여부: 데이터 검증 통과 AND 광고 위임 문자열이 DELEGATED AND 실제 서면 위임 확인됨
            is_marketing_eligible = False
            if is_valid and ad_status == "DELEGATED":
                if listing_id in self.verified_delegation_ids:
                    is_marketing_eligible = True
                else:
                    # 권한 미확인 차량은 데이터 자체는 유효하더라도 마케팅 대상에서는 엄격 제외
                    is_marketing_eligible = False

            if is_valid:
                report.valid_rows += 1
                if is_marketing_eligible:
                    report.marketing_eligible_count += 1
            else:
                report.rejected_rows += 1
                for err in row_errors:
                    report.errors.append(err)
                    report.errors_by_field[err.field_name] = (
                        report.errors_by_field.get(err.field_name, 0) + 1
                    )

            reasons = [e.message for e in row_errors]
            report.records.append(
                IntakeRecordResult(
                    row_number=row_idx,
                    internal_listing_id=listing_id,
                    is_valid=is_valid,
                    is_marketing_eligible=is_marketing_eligible,
                    is_synthetic=is_synthetic,
                    rejection_reasons=reasons,
                    raw_data=dict(row),
                    normalized_data=normalized,
                )
            )

        return report

    @staticmethod
    def preview_orm_mappings(record: IntakeRecordResult) -> dict[str, Any]:
        """
        검증 통과한 레코드를 기존 데이터 엔진 ORM 구조로 변환하는 매핑 미리보기를 제공합니다.
        (DRY-RUN 모드: DB에 실제 쓰지 않음)
        """
        if not record.is_valid:
            raise ValueError(f"유효하지 않은 레코드는 ORM으로 변환할 수 없습니다: {record.rejection_reasons}")

        data = record.normalized_data
        listing_id = data.get("internal_listing_id") or "UNKNOWN"
        anon_code = data.get("anonymous_vehicle_code") or f"ANON_{listing_id}"

        return {
            "VehicleCatalog": {
                "catalog_id": f"CAT_{data.get('manufacturer')}_{data.get('model_name')}_{data.get('model_year')}",
                "manufacturer": data.get("manufacturer"),
                "model_name": data.get("model_name"),
                "sub_model": data.get("sub_model"),
                "trim": data.get("trim"),
                "model_year": data.get("model_year"),
                "fuel_type": data.get("fuel_type"),
                "transmission": data.get("transmission"),
            },
            "VehicleIdentity": {
                "vehicle_id": anon_code,
                "plate_number": None,  # 비식별화 준수: 실차량번호 미수집
                "vin": None,           # 비식별화 준수: 차대번호 미수집
                "identity_status": "ANONYMIZED_PARTNER_CODE",
                "identity_confidence": 0.95,
            },
            "Listing": {
                "listing_id": listing_id,
                "source_platform": "PARTNER_DIRECT_INTAKE",
                "source_listing_id": listing_id,
                "vehicle_id": anon_code,
                "seller_reference": data.get("partner_dealer_code"),
                "first_observed_at": data.get("first_observed_date"),
                "raw_location": "서울 성동구 장안평 중고차 매매단지",
                "normalized_region_id": "REG_SEOUL_JANGANPYEONG",
                "current_status": "ACTIVE" if not data.get("contract_closed_date") else "SOLD",
            },
            "ListingSnapshot": {
                "snapshot_id": f"SNAP_{listing_id}_INIT",
                "listing_id": listing_id,
                "observed_at": data.get("first_observed_date"),
                "price_krw": data.get("target_listing_price_krw"),
                "mileage_km": data.get("mileage_km"),
                "listing_status": "ACTIVE" if not data.get("contract_closed_date") else "SOLD",
                "normalized_region_id": "REG_SEOUL_JANGANPYEONG",
            },
            "SalesCandidate": {
                "candidate_id": f"CAND_{listing_id}",
                "listing_id": listing_id,
                "target_region_id": "REG_SEOUL_JANGANPYEONG",
                "is_marketing_eligible": record.is_marketing_eligible,
            },
        }
