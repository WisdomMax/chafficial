"""차피셜 파트너 실매물 데이터 인입 및 무결성·권한 검증 모듈 (004-B PREFLIGHT).

- RFC 4180 표준 CSV 파싱 (인용부호 내 줄바꿈, 쉼표, '#' 포함 텍스트 완벽 보호)
- 중복 헤더 및 열 개수 불일치 엄격 차단
- 개인정보(PII) 컬럼 차단 및 오류 보고서 내 민감값 원천 비노출
- 부존재 자동차 제원(배기량, 좌석수, 세대, 지역) 날조/임의 기본값 생성 전면 차단
- 최초 관측 스냅샷의 미래 정보 누출 원천 차단 (계약일과 무관하게 INIT 스냅샷은 ACTIVE 보존)
- 승인 객체와 실제 사실의 분리 (테스트용은 SIMULATED_AUTHORIZED로 격리)
- 광고 권한(is_marketing_eligible)과 실제 게시 허가(is_live_ad_authorized=False)의 명확한 분리
- 현실 세계 지표(실데이터, 실광고권한, 실계약정산, 광고집행비) 0건 엄격 유지
- DRY RUN 기본 원칙
"""

from __future__ import annotations

import csv
import io
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from chaficial.models.catalog import VehicleCatalog
from chaficial.models.listing import Listing
from chaficial.models.snapshot import ListingSnapshot
from chaficial.models.vehicle import VehicleIdentity


@dataclass
class ValidationError:
    row_number: int
    field_name: str
    error_code: str
    message: str


@dataclass
class DelegationProof:
    """광고 위임 서면 증빙 모델."""

    proof_id: str
    internal_listing_id: str
    delegation_type: str  # DIRECT_PURCHASE_OWNER, THIRD_PARTY_CONSIGNMENT
    valid_until: date
    has_signed_document: bool
    is_revoked: bool = False
    third_party_firm_consent: bool = False  # 제3자 상사 동의 여부


@dataclass
class IntakeApprovalProof:
    """실데이터 인입에 대한 총괄 관리자(사장님) 공식 승인 증빙."""

    approval_id: str
    approved_by: str
    approved_at: datetime
    data_source: str
    target_firm_code: str
    scope_description: str
    verification_token: str | None = None  # 현장 감사 검증 토큰 (공식 승인 시에만 발급)
    is_real_world_verified: bool = False  # 실제 현장 검증 완료 여부 (기본 False)


@dataclass
class IntakeRecordResult:
    row_number: int
    internal_listing_id: str
    is_valid: bool
    is_marketing_eligible: bool
    is_live_ad_authorized: bool  # 실제 SNS 게시·광고 집행 허가 여부 (Phase 1 항상 False)
    data_classification: str     # SYNTHETIC, UNVERIFIED_EXTERNAL, SIMULATED_AUTHORIZED, VERIFIED_REAL
    rejection_reasons: list[str] = field(default_factory=list)
    normalized_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntakeValidationReport:
    total_rows: int = 0
    valid_rows: int = 0
    rejected_rows: int = 0
    marketing_eligible_count: int = 0
    live_ad_authorized_count: int = 0  # 실제 광고 집행 허가 건수 (현재 엄격히 0)
    synthetic_data_count: int = 0
    unverified_external_count: int = 0
    simulated_authorized_count: int = 0
    verified_real_data_count: int = 0  # 현실 세계 실제 검증 데이터 (현재 엄격히 0)
    real_ad_delegation_count: int = 0  # 현실 세계 실제 광고권한 확보 (현재 엄격히 0)
    real_settled_count: int = 0        # 현실 세계 실제 정산 완료 (현재 엄격히 0)
    actual_ad_spend_krw: int = 0       # 실제 집행된 광고비용 (현재 엄격히 0)
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
                "live_ad_authorized_count": self.live_ad_authorized_count,
                "synthetic_data_count": self.synthetic_data_count,
                "unverified_external_count": self.unverified_external_count,
                "simulated_authorized_count": self.simulated_authorized_count,
                "verified_real_data_count": self.verified_real_data_count,
                "real_ad_delegation_count": self.real_ad_delegation_count,
                "real_settled_count": self.real_settled_count,
                "actual_ad_spend_krw": self.actual_ad_spend_krw,
                "errors_by_field": self.errors_by_field,
            },
            "records": [asdict(r) for r in self.records],
            "error_count": len(self.errors),
        }


PERMITTED_HEADERS = [
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

FORBIDDEN_PII_KEYWORDS = [
    "plate", "vin", "owner", "ssn", "rrn", "phone", "tel", "mobile",
    "차량번호", "차대번호", "소유자", "주민", "연락처", "전화", "실명"
]

OFFICIAL_REAL_WORLD_TOKEN = "CHAFICIAL_DIRECTOR_2026_OFFICIAL_VERIFIED"


class PartnerListingIntakeValidator:
    """파트너 매물 인입값의 무결성·보안·권한 검증 및 ORM 정합성 변환 엔진."""

    def __init__(
        self,
        delegation_proofs: list[DelegationProof] | None = None,
        approval_proof: IntakeApprovalProof | None = None,
    ) -> None:
        self.delegation_proofs = {p.internal_listing_id: p for p in (delegation_proofs or [])}
        self.approval_proof = approval_proof

    def validate_csv(
        self,
        source: str | Path | io.StringIO,
        is_synthetic: bool = True,
    ) -> IntakeValidationReport:
        report = IntakeValidationReport()

        if isinstance(source, (str, Path)) and not isinstance(source, io.StringIO):
            source_path = Path(source)
            if not source_path.exists():
                report.errors.append(
                    ValidationError(0, "file", "FILE_NOT_FOUND", "파일을 찾을 수 없습니다.")
                )
                return report
            try:
                with open(source_path, encoding="utf-8-sig") as f:
                    content_str = f.read()
            except UnicodeDecodeError:
                report.errors.append(
                    ValidationError(0, "file", "ENCODING_ERROR", "UTF-8 인코딩 형식이 아닙니다.")
                )
                return report
        elif isinstance(source, io.StringIO):
            content_str = source.getvalue()
        else:
            content_str = str(source)

        # RFC 4180 호환 파싱:
        # 파일 최상단의 파일 레벨 주석(#)만 건너뛰고, 본문 내 인용부호 안의 '#'는 정상 보호
        cleaned_io = io.StringIO()
        in_header_search = True
        for line in content_str.splitlines(keepends=True):
            if in_header_search and line.strip().startswith("#"):
                continue  # 파일 최상단 주석 스킵
            in_header_search = False
            cleaned_io.write(line)
        cleaned_io.seek(0)

        try:
            reader = csv.reader(cleaned_io)
            rows = list(reader)
        except csv.Error:
            report.errors.append(
                ValidationError(0, "csv", "CSV_PARSING_ERROR", "CSV 문법이 유효하지 않습니다.")
            )
            return report

        if not rows:
            report.errors.append(ValidationError(0, "file", "EMPTY_FILE", "유효한 데이터 행이 없습니다."))
            return report

        raw_headers = rows[0]
        actual_headers = [h.strip() for h in raw_headers]

        # 1. 중복 헤더 검증
        if len(actual_headers) != len(set(actual_headers)):
            report.errors.append(
                ValidationError(0, "header", "DUPLICATE_HEADER", "중복된 헤더명이 존재합니다.")
            )
            return report

        # 2. 필수 헤더 누락 검증
        missing_headers = [h for h in PERMITTED_HEADERS if h not in actual_headers]
        if missing_headers:
            for mh in missing_headers:
                report.errors.append(
                    ValidationError(0, mh, "MISSING_REQUIRED_COLUMN", "필수 컬럼이 누락되었습니다.")
                )
                report.errors_by_field[mh] = report.errors_by_field.get(mh, 0) + 1
            return report

        # 3. 추가 컬럼 검사 (허용 목록 외 컬럼 차단 및 개인정보 컬럼 명시적 차단)
        extra_headers = [h for h in actual_headers if h not in PERMITTED_HEADERS]
        if extra_headers:
            for eh in extra_headers:
                eh_lower = eh.lower()
                if any(pii in eh_lower for pii in FORBIDDEN_PII_KEYWORDS):
                    report.errors.append(
                        ValidationError(0, eh, "PII_COLUMN_PROHIBITED", "개인정보 수집 금지 정책에 위배되는 컬럼입니다.")
                    )
                else:
                    report.errors.append(
                        ValidationError(0, eh, "FORBIDDEN_EXTRA_COLUMN", "허용되지 않은 임의 컬럼이 포함되어 있습니다.")
                    )
                report.errors_by_field[eh] = report.errors_by_field.get(eh, 0) + 1
            return report

        header_indices = {h: idx for idx, h in enumerate(actual_headers)}
        expected_col_count = len(actual_headers)
        seen_listing_ids: set[str] = set()

        for row_idx, row in enumerate(rows[1:], start=1):
            report.total_rows += 1

            if len(row) != expected_col_count:
                report.rejected_rows += 1
                err = ValidationError(
                    row_idx, "row", "COLUMN_COUNT_MISMATCH", f"열 개수가 헤더({expected_col_count})와 일치하지 않습니다({len(row)})."
                )
                report.errors.append(err)
                report.errors_by_field["row"] = report.errors_by_field.get("row", 0) + 1
                report.records.append(
                    IntakeRecordResult(
                        row_number=row_idx,
                        internal_listing_id="UNKNOWN",
                        is_valid=False,
                        is_marketing_eligible=False,
                        is_live_ad_authorized=False,
                        data_classification="SYNTHETIC" if is_synthetic else "UNVERIFIED_EXTERNAL",
                        rejection_reasons=[err.message],
                    )
                )
                continue

            row_dict = {h: row[header_indices[h]] for h in actual_headers}

            # 데이터 분류 판정 (단순 Boolean 의존 금지, 공식 토큰 및 현장 검증 확인)
            if is_synthetic:
                data_class = "SYNTHETIC"
                report.synthetic_data_count += 1
            elif self.approval_proof is not None:
                # 공식 검증 토큰과 실사 검증 플래그가 모두 충족된 경우에만 실제 데이터 인정
                if (
                    self.approval_proof.is_real_world_verified
                    and self.approval_proof.verification_token == OFFICIAL_REAL_WORLD_TOKEN
                ):
                    data_class = "VERIFIED_REAL"
                    report.verified_real_data_count += 1
                else:
                    data_class = "SIMULATED_AUTHORIZED"
                    report.simulated_authorized_count += 1
            else:
                data_class = "UNVERIFIED_EXTERNAL"
                report.unverified_external_count += 1

            row_errors: list[ValidationError] = []
            normalized: dict[str, Any] = {}

            # 1. internal_listing_id
            listing_id = (row_dict.get("internal_listing_id") or "").strip()
            if not listing_id:
                row_errors.append(
                    ValidationError(row_idx, "internal_listing_id", "MISSING_LISTING_ID", "내부 매물 ID가 누락되었습니다.")
                )
            elif listing_id in seen_listing_ids:
                row_errors.append(
                    ValidationError(row_idx, "internal_listing_id", "DUPLICATE_INTERNAL_ID", "중복된 매물 ID입니다.")
                )
            else:
                seen_listing_ids.add(listing_id)
            normalized["internal_listing_id"] = listing_id

            # 2. anonymous_vehicle_code
            anon_code = (row_dict.get("anonymous_vehicle_code") or "").strip()
            normalized["anonymous_vehicle_code"] = anon_code if anon_code else None

            # 3. manufacturer, model_name, sub_model, trim
            mfr = (row_dict.get("manufacturer") or "").strip()
            model = (row_dict.get("model_name") or "").strip()
            sub_model = (row_dict.get("sub_model") or "").strip()
            trim = (row_dict.get("trim") or "").strip()

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
            normalized["sub_model"] = sub_model or None
            # 세대 정보: 임의로 특정 세대로 확정짓지 않고 미확정 시 "UNKNOWN_GENERATION"
            normalized["generation"] = sub_model if sub_model else "UNKNOWN_GENERATION"
            normalized["trim"] = trim if trim else "UNKNOWN_TRIM"
            normalized["fuel_type"] = (row_dict.get("fuel_type") or "").strip() or "UNKNOWN_FUEL"
            normalized["transmission"] = (row_dict.get("transmission") or "").strip() or "UNKNOWN_TRANSMISSION"
            normalized["color_category"] = (row_dict.get("color_category") or "").strip() or "UNKNOWN_COLOR"

            # 4. model_year (연식 필수)
            year_str = (row_dict.get("model_year") or "").strip()
            if not year_str:
                row_errors.append(
                    ValidationError(row_idx, "model_year", "MISSING_MODEL_YEAR", "연식은 필수 항목입니다.")
                )
                normalized["model_year"] = None
            else:
                try:
                    year = int(year_str)
                    current_year = datetime.now(UTC).year
                    if year < 1990 or year > current_year + 1:
                        row_errors.append(
                            ValidationError(row_idx, "model_year", "INVALID_MODEL_YEAR", "연식 범위가 허용 기준을 벗어납니다.")
                        )
                    normalized["model_year"] = year
                except ValueError:
                    row_errors.append(
                        ValidationError(row_idx, "model_year", "INVALID_YEAR_TYPE", "연식은 정수형이어야 합니다.")
                    )
                    normalized["model_year"] = None

            # 5. mileage_km (주행거리 필수 및 음수 차단)
            mileage_str = (row_dict.get("mileage_km") or "").strip()
            if not mileage_str:
                row_errors.append(
                    ValidationError(row_idx, "mileage_km", "MISSING_MILEAGE", "주행거리는 필수 항목입니다.")
                )
                normalized["mileage_km"] = None
            else:
                try:
                    mileage = int(mileage_str)
                    if mileage < 0:
                        row_errors.append(
                            ValidationError(row_idx, "mileage_km", "NEGATIVE_MILEAGE", "주행거리는 음수일 수 없습니다.")
                        )
                    normalized["mileage_km"] = mileage
                except ValueError:
                    row_errors.append(
                        ValidationError(row_idx, "mileage_km", "INVALID_MILEAGE_TYPE", "주행거리는 정수형이어야 합니다.")
                    )
                    normalized["mileage_km"] = None

            # 6. first_observed_date (필수)
            obs_date_str = (row_dict.get("first_observed_date") or "").strip()
            if not obs_date_str:
                row_errors.append(
                    ValidationError(row_idx, "first_observed_date", "MISSING_OBSERVED_DATE", "최초 관측일은 필수입니다.")
                )
                normalized["first_observed_date"] = None
            else:
                try:
                    dt = datetime.strptime(obs_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                    normalized["first_observed_date"] = dt
                except ValueError:
                    row_errors.append(
                        ValidationError(row_idx, "first_observed_date", "INVALID_DATE_FORMAT", "날짜 포맷 오류입니다(YYYY-MM-DD).")
                    )
                    normalized["first_observed_date"] = None

            # 7. inspection_date (선택)
            insp_date_str = (row_dict.get("inspection_date") or "").strip()
            if insp_date_str:
                try:
                    dt_insp = datetime.strptime(insp_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                    normalized["inspection_date"] = dt_insp
                except ValueError:
                    row_errors.append(
                        ValidationError(row_idx, "inspection_date", "INVALID_DATE_FORMAT", "점검일 포맷 오류입니다.")
                    )
                    normalized["inspection_date"] = None
            else:
                normalized["inspection_date"] = None

            # 8. 가격 필드 (목표등록가 필수, 매입가/최저가 음수 차단)
            target_price_str = (row_dict.get("target_listing_price_krw") or "").strip()
            try:
                target_price = int(target_price_str)
                if target_price <= 0:
                    row_errors.append(
                        ValidationError(row_idx, "target_listing_price_krw", "NEGATIVE_OR_ZERO_PRICE", "목표가는 0보다 커야 합니다.")
                    )
                normalized["target_listing_price_krw"] = target_price
            except ValueError:
                row_errors.append(
                    ValidationError(row_idx, "target_listing_price_krw", "INVALID_PRICE_TYPE", "목표가는 정수여야 합니다.")
                )
                normalized["target_listing_price_krw"] = None

            for p_field in ["cost_price_krw", "min_acceptable_price_krw"]:
                p_val_str = (row_dict.get(p_field) or "").strip()
                if p_val_str:
                    try:
                        p_val = int(p_val_str)
                        if p_val < 0:
                            row_errors.append(
                                ValidationError(row_idx, p_field, "NEGATIVE_PRICE", "가격 항목은 음수일 수 없습니다.")
                            )
                        normalized[p_field] = p_val
                    except ValueError:
                        row_errors.append(
                            ValidationError(row_idx, p_field, "INVALID_PRICE_TYPE", "가격 항목은 정수여야 합니다.")
                        )
                        normalized[p_field] = None
                else:
                    normalized[p_field] = None

            # 9. 성능점검 및 차량 상태
            outer_damage = (row_dict.get("outer_panel_rank1_damage") or "").strip()
            struct_damage = (row_dict.get("structural_rank2_damage") or "").strip()
            flood_status = (row_dict.get("flood_damage_status") or "").strip()
            inspector = (row_dict.get("inspector_code") or "").strip()

            normalized["outer_panel_rank1_damage"] = outer_damage or "미확인"
            normalized["structural_rank2_damage"] = struct_damage or "미확인"
            normalized["flood_damage_status"] = flood_status or "미확인"
            normalized["inspector_code"] = inspector or None

            if not inspector and (struct_damage != "미확인" or outer_damage != "미확인"):
                row_errors.append(
                    ValidationError(row_idx, "inspector_code", "UNVERIFIED_INSPECTION_RECORD", "공인 점검자 식별코드 없이 상태를 단정할 수 없습니다.")
                )

            # 10. 광고 위임 상태 및 재고 유형
            ad_status = (row_dict.get("advertising_delegation_status") or "").strip()
            inv_type = (row_dict.get("inventory_type") or "").strip() or "DIRECT_PURCHASE"
            partner_firm = (row_dict.get("partner_firm_code") or "").strip()
            partner_dealer = (row_dict.get("partner_dealer_code") or "").strip()

            normalized["advertising_delegation_status"] = ad_status
            normalized["inventory_type"] = inv_type
            normalized["partner_firm_code"] = partner_firm or None
            normalized["partner_dealer_code"] = partner_dealer or None

            # 11. 계약 및 정산 검증
            closed_date_str = (row_dict.get("contract_closed_date") or "").strip()
            contract_price_str = (row_dict.get("actual_contract_price_krw") or "").strip()
            settlement_status = (row_dict.get("settlement_status") or "").strip() or "UNSETTLED"

            if closed_date_str:
                try:
                    dt_closed = datetime.strptime(closed_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                    normalized["contract_closed_date"] = dt_closed
                except ValueError:
                    row_errors.append(
                        ValidationError(row_idx, "contract_closed_date", "INVALID_DATE_FORMAT", "계약일자 포맷 오류입니다.")
                    )
                    normalized["contract_closed_date"] = None
                
                if contract_price_str:
                    try:
                        normalized["actual_contract_price_krw"] = int(contract_price_str)
                    except ValueError:
                        row_errors.append(
                            ValidationError(row_idx, "actual_contract_price_krw", "INVALID_PRICE_TYPE", "계약가는 정수형이어야 합니다.")
                        )
                        normalized["actual_contract_price_krw"] = None
                else:
                    normalized["actual_contract_price_krw"] = None
            else:
                normalized["contract_closed_date"] = None
                normalized["actual_contract_price_krw"] = None

            if not closed_date_str:
                if contract_price_str:
                    row_errors.append(
                        ValidationError(row_idx, "actual_contract_price_krw", "PREMATURE_CONTRACT_PRICE", "미계약 매물에 계약가를 임의 기재할 수 없습니다.")
                    )
                if (row_dict.get("net_profit_krw") or "").strip():
                    row_errors.append(
                        ValidationError(row_idx, "net_profit_krw", "PREMATURE_PROFIT_RECOGNITION", "미계약 매물의 수익을 확정값으로 기록할 수 없습니다.")
                    )

            if closed_date_str and settlement_status == "SETTLED":
                cost_fields = [
                    "gross_commission_revenue_krw",
                    "video_production_cost_krw",
                    "ad_spend_krw",
                    "other_operational_costs_krw",
                    "net_profit_krw",
                ]
                missing_cost_fields = [cf for cf in cost_fields if not (row_dict.get(cf) or "").strip()]
                if missing_cost_fields:
                    row_errors.append(
                        ValidationError(
                            row_idx, "settlement_status", "MISSING_SETTLED_AMOUNTS", f"정산 완료 상태에서는 필수 비용/수익 항목이 누락될 수 없습니다: {missing_cost_fields}"
                        )
                    )
                else:
                    try:
                        c_rev = int(row_dict["gross_commission_revenue_krw"].strip())
                        v_cost = int(row_dict["video_production_cost_krw"].strip())
                        a_cost = int(row_dict["ad_spend_krw"].strip())
                        o_cost = int(row_dict["other_operational_costs_krw"].strip())
                        net_profit = int(row_dict["net_profit_krw"].strip())

                        if c_rev < 0 or v_cost < 0 or a_cost < 0 or o_cost < 0:
                            row_errors.append(
                                ValidationError(row_idx, "settlement_amounts", "NEGATIVE_SETTLEMENT_AMOUNT", "수수료 및 비용 항목은 음수일 수 없습니다.")
                            )
                        elif net_profit != c_rev - (v_cost + a_cost + o_cost):
                            row_errors.append(
                                ValidationError(row_idx, "net_profit_krw", "NET_PROFIT_MISMATCH", "순수익과 (수수료 - 총비용) 계산값이 불일치합니다.")
                            )
                        normalized["settled_amounts"] = {
                            "gross_commission_revenue_krw": c_rev,
                            "video_production_cost_krw": v_cost,
                            "ad_spend_krw": a_cost,
                            "other_operational_costs_krw": o_cost,
                            "net_profit_krw": net_profit,
                        }
                    except ValueError:
                        row_errors.append(
                            ValidationError(row_idx, "settlement_status", "INVALID_COST_NUMBER", "정산 금액은 정수여야 합니다.")
                        )
            else:
                normalized["settled_amounts"] = None

            is_valid = len(row_errors) == 0

            # 서면 위임 객체 검증
            is_marketing_eligible = False
            if is_valid and ad_status == "DELEGATED":
                proof = self.delegation_proofs.get(listing_id)
                if proof and proof.has_signed_document and not proof.is_revoked:
                    today = datetime.now(UTC).date()
                    if proof.valid_until >= today:
                        if inv_type == "CONSIGNMENT":
                            if proof.third_party_firm_consent:
                                is_marketing_eligible = True
                        else:
                            is_marketing_eligible = True

            # 실제 게시 허가(Execution Permission): Phase 1에서는 무조건 False (광고비 집행 0원 동결 원칙)
            is_live_ad_authorized = False

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

            report.records.append(
                IntakeRecordResult(
                    row_number=row_idx,
                    internal_listing_id=listing_id,
                    is_valid=is_valid,
                    is_marketing_eligible=is_marketing_eligible,
                    is_live_ad_authorized=is_live_ad_authorized,
                    data_classification=data_class,
                    rejection_reasons=[e.message for e in row_errors],
                    normalized_data=normalized,
                )
            )

        return report

    @staticmethod
    def build_orm_entities(
        record: IntakeRecordResult,
        target_region_id: str | None = None,
        raw_location: str | None = None,
        system_ingested_at: datetime | None = None,
    ) -> tuple[VehicleCatalog, VehicleIdentity, Listing, list[ListingSnapshot]]:
        """
        검증 통과 레코드를 실제 SQLAlchemy ORM 객체로 인스턴스화합니다.
        
        [시계열 무결성 핵심 규칙 - 미래 정보 누출 원천 차단]:
        - 최초 관측 스냅샷(INIT)은 사후 계약 여부와 무관하게 무조건 'ACTIVE'로 기록합니다.
        - 계약이 나중에 체결된 경우(contract_closed_date 존재), 해당 계약 시점에 맞춰 
          두 번째 스냅샷(CLOSED)을 생성하여 과거 관측 이력의 불변성을 완벽히 보존합니다.
        - 배기량, 좌석수는 미확인 시 NULL(None)을 유지합니다.
        - 소재지는 확인된 근거가 없으면 LOCATION_UNCONFIRMED / None을 유지합니다.
        """
        if not record.is_valid:
            raise ValueError("검증 실패 레코드는 ORM 객체로 변환할 수 없습니다.")

        data = record.normalized_data
        listing_id = data["internal_listing_id"]
        anon_code = data["anonymous_vehicle_code"] or f"ANON_{listing_id}"
        ingest_time = system_ingested_at or datetime.now(UTC)

        # 1. VehicleCatalog:
        catalog = VehicleCatalog(
            manufacturer=data["manufacturer"],
            model_name=data["model_name"],
            generation=data["generation"],
            is_facelift=False,
            sub_model=data["sub_model"],
            trim=data["trim"],
            model_year=data["model_year"],
            fuel_type=data["fuel_type"],
            transmission=data["transmission"],
            displacement_cc=None,  # 미확인 시 NULL 유지
            seating_capacity=None, # 미확인 시 NULL 유지
        )

        # 2. VehicleIdentity:
        identity = VehicleIdentity(
            vehicle_id=anon_code,
            plate_number=None,
            vin=None,
            identity_status="UNCONFIRMED",
            identity_confidence=0.5,
            catalog=catalog,
        )

        # 3. Listing:
        resolved_raw_location = raw_location if raw_location else "LOCATION_UNCONFIRMED"
        resolved_region_id = target_region_id

        # 매물의 현재 상태 (사후 계약 완료 시 DELISTED, 미계약 시 ACTIVE)
        current_status = "DELISTED" if data["contract_closed_date"] else "ACTIVE"
        first_obs_at = data["first_observed_date"] or ingest_time

        listing = Listing(
            listing_id=listing_id,
            source_platform="PARTNER_DIRECT_INTAKE",
            source_listing_id=listing_id,
            vehicle=identity,
            seller_reference=data["partner_dealer_code"],
            first_observed_at=first_obs_at,
            raw_location=resolved_raw_location,
            normalized_region_id=resolved_region_id,
            current_status=current_status,
        )

        # 4. ListingSnapshot (시계열 불변 스냅샷 목록):
        snapshots: list[ListingSnapshot] = []

        # 스냅샷 1: 최초 관측 시점 (사후 계약이 있더라도 최초 등록 시점엔 반드시 'ACTIVE'였음!)
        init_snapshot = ListingSnapshot(
            snapshot_id=f"SNAP_{listing_id}_INIT",
            listing=listing,
            observed_at=first_obs_at,
            ingested_at=ingest_time,
            price_krw=data["target_listing_price_krw"] or 0,
            mileage_km=data["mileage_km"] or 0,
            listing_status="ACTIVE",  # 미래 정보 누출 차단: 최초 관측 당시 상태 강제
            normalized_region_id=resolved_region_id,
            raw_specs={
                "outer_damage": data["outer_panel_rank1_damage"],
                "structural_damage": data["structural_rank2_damage"],
                "flood": data["flood_damage_status"],
                "inspector": data["inspector_code"],
            },
        )
        snapshots.append(init_snapshot)

        # 스냅샷 2: 실제 계약 완료 시점 (과거 관측 기록을 덮어쓰지 않고 새로운 스냅샷 추가)
        if data["contract_closed_date"]:
            closed_at = data["contract_closed_date"]
            closed_snapshot = ListingSnapshot(
                snapshot_id=f"SNAP_{listing_id}_CLOSED",
                listing=listing,
                observed_at=closed_at,
                ingested_at=ingest_time,
                price_krw=data.get("actual_contract_price_krw") or data["target_listing_price_krw"] or 0,
                mileage_km=data["mileage_km"] or 0,
                listing_status="DELISTED",  # 계약 체결 시점의 상태
                normalized_region_id=resolved_region_id,
                raw_specs={"event": "CONTRACT_CLOSED"},
            )
            snapshots.append(closed_snapshot)

        return catalog, identity, listing, snapshots
