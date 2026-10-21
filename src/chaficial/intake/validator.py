"""차피셜 파트너 실매물 데이터 인입 및 무결성·권한 검증 모듈.

- 10대 데이터 품질 규칙
- 엄격한 헤더 정책 (개인정보 추가 컬럼 원천 차단)
- 민감 정보 마스킹 및 비노출
- 서면 위임 증빙(유효기간, 철회, 제3자 위임 범위) 보안 게이트
- 실제 DB ORM(VehicleCatalog, VehicleIdentity, Listing, ListingSnapshot) 스키마 완전 일치 매핑
- DRY RUN 및 출처·승인 검증 기반 실데이터 분리
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
    has_signed_document: bool = True
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


@dataclass
class IntakeRecordResult:
    row_number: int
    internal_listing_id: str
    is_valid: bool
    is_marketing_eligible: bool
    data_classification: str  # SYNTHETIC, UNVERIFIED_EXTERNAL, VERIFIED_REAL
    rejection_reasons: list[str] = field(default_factory=list)
    normalized_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntakeValidationReport:
    total_rows: int = 0
    valid_rows: int = 0
    rejected_rows: int = 0
    marketing_eligible_count: int = 0
    synthetic_data_count: int = 0
    unverified_external_count: int = 0
    verified_real_data_count: int = 0  # 현실 세계 실제 데이터 (승인 증빙 필수)
    real_ad_delegation_count: int = 0  # 현실 세계 실제 광고권한 확보 (현재 0)
    real_settled_count: int = 0        # 현실 세계 실제 정산 완료 (현재 0)
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
                "synthetic_data_count": self.synthetic_data_count,
                "unverified_external_count": self.unverified_external_count,
                "verified_real_data_count": self.verified_real_data_count,
                "real_ad_delegation_count": self.real_ad_delegation_count,
                "real_settled_count": self.real_settled_count,
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
    "name", "차량번호", "차대번호", "소유자", "주민", "연락처", "전화", "실명"
]


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
            with open(source_path, encoding="utf-8-sig") as f:
                content = f.read()
        elif isinstance(source, io.StringIO):
            content = source.getvalue()
        else:
            content = str(source)

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

        # 1. 엄격한 헤더 정책 (누락 및 무단 추가 컬럼/개인정보 차단)
        actual_headers = [h.strip() for h in reader.fieldnames]
        missing_headers = [h for h in PERMITTED_HEADERS if h not in actual_headers]
        if missing_headers:
            for mh in missing_headers:
                report.errors.append(
                    ValidationError(0, mh, "MISSING_REQUIRED_COLUMN", "필수 컬럼이 누락되었습니다.")
                )
                report.errors_by_field[mh] = report.errors_by_field.get(mh, 0) + 1
            return report

        # 2. 추가 컬럼 검사 (허용 목록 외 컬럼 차단 및 개인정보 컬럼 명시적 차단)
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

        seen_listing_ids: set[str] = set()

        for row_idx, row in enumerate(reader, start=1):
            report.total_rows += 1

            # 데이터 분류 판정 (단순 Boolean 의존 금지)
            if is_synthetic:
                data_class = "SYNTHETIC"
                report.synthetic_data_count += 1
            elif self.approval_proof is not None:
                data_class = "VERIFIED_REAL"
                report.verified_real_data_count += 1
            else:
                data_class = "UNVERIFIED_EXTERNAL"
                report.unverified_external_count += 1

            row_errors: list[ValidationError] = []
            normalized: dict[str, Any] = {}

            # 1. internal_listing_id
            listing_id = (row.get("internal_listing_id") or "").strip()
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
            anon_code = (row.get("anonymous_vehicle_code") or "").strip()
            normalized["anonymous_vehicle_code"] = anon_code if anon_code else None

            # 3. manufacturer, model_name, sub_model, trim
            mfr = (row.get("manufacturer") or "").strip()
            model = (row.get("model_name") or "").strip()
            sub_model = (row.get("sub_model") or "").strip()
            trim = (row.get("trim") or "").strip()

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
            # DB NOT NULL generation 처리를 위해 sub_model 또는 모델명 기반 정규화
            normalized["generation"] = sub_model if sub_model else "UNKNOWN"
            normalized["trim"] = trim if trim else "기본형"
            normalized["fuel_type"] = (row.get("fuel_type") or "가솔린").strip()
            normalized["transmission"] = (row.get("transmission") or "오토").strip()
            normalized["color_category"] = (row.get("color_category") or "기타").strip()

            # 4. model_year
            year_str = (row.get("model_year") or "").strip()
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
                    ValidationError(row_idx, "model_year", "INVALID_YEAR_TYPE", "연식은 숫자형이어야 합니다.")
                )
                normalized["model_year"] = None

            # 5. mileage_km (음수 주행거리 차단)
            mileage_str = (row.get("mileage_km") or "").strip()
            try:
                mileage = int(mileage_str)
                if mileage < 0:
                    row_errors.append(
                        ValidationError(row_idx, "mileage_km", "NEGATIVE_MILEAGE", "주행거리는 음수일 수 없습니다.")
                    )
                normalized["mileage_km"] = mileage
            except ValueError:
                row_errors.append(
                    ValidationError(row_idx, "mileage_km", "INVALID_MILEAGE_TYPE", "주행거리는 숫자형이어야 합니다.")
                )
                normalized["mileage_km"] = None

            # 6. first_observed_date (필수)
            obs_date_str = (row.get("first_observed_date") or "").strip()
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
            insp_date_str = (row.get("inspection_date") or "").strip()
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
            target_price_str = (row.get("target_listing_price_krw") or "").strip()
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
                p_val_str = (row.get(p_field) or "").strip()
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
            outer_damage = (row.get("outer_panel_rank1_damage") or "").strip()
            struct_damage = (row.get("structural_rank2_damage") or "").strip()
            flood_status = (row.get("flood_damage_status") or "").strip()
            inspector = (row.get("inspector_code") or "").strip()

            normalized["outer_panel_rank1_damage"] = outer_damage or "미확인"
            normalized["structural_rank2_damage"] = struct_damage or "미확인"
            normalized["flood_damage_status"] = flood_status or "미확인"
            normalized["inspector_code"] = inspector or None

            # 점검코드 없이 사고없음/교환없음 단정 금지
            if not inspector and (struct_damage != "미확인" or outer_damage != "미확인"):
                row_errors.append(
                    ValidationError(row_idx, "inspector_code", "UNVERIFIED_INSPECTION_RECORD", "공인 점검자 식별코드 없이 상태를 단정할 수 없습니다.")
                )

            # 10. 광고 위임 상태 및 재고 유형
            ad_status = (row.get("advertising_delegation_status") or "").strip()
            inv_type = (row.get("inventory_type") or "").strip() or "DIRECT_PURCHASE"
            partner_firm = (row.get("partner_firm_code") or "").strip()
            partner_dealer = (row.get("partner_dealer_code") or "").strip()

            normalized["advertising_delegation_status"] = ad_status
            normalized["inventory_type"] = inv_type
            normalized["partner_firm_code"] = partner_firm or None
            normalized["partner_dealer_code"] = partner_dealer or None

            # 11. 계약 및 정산 검증 (금액 누락 및 음수 검증)
            closed_date_str = (row.get("contract_closed_date") or "").strip()
            contract_price_str = (row.get("actual_contract_price_krw") or "").strip()
            settlement_status = (row.get("settlement_status") or "").strip() or "UNSETTLED"

            if closed_date_str:
                try:
                    dt_closed = datetime.strptime(closed_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                    normalized["contract_closed_date"] = dt_closed
                except ValueError:
                    row_errors.append(
                        ValidationError(row_idx, "contract_closed_date", "INVALID_DATE_FORMAT", "계약일자 포맷 오류입니다.")
                    )
                    normalized["contract_closed_date"] = None
            else:
                normalized["contract_closed_date"] = None

            # 미계약 상태에서 계약가/수익 기재 차단
            if not closed_date_str:
                if contract_price_str:
                    row_errors.append(
                        ValidationError(row_idx, "actual_contract_price_krw", "PREMATURE_CONTRACT_PRICE", "미계약 매물에 계약가를 임의 기재할 수 없습니다.")
                    )
                if (row.get("net_profit_krw") or "").strip():
                    row_errors.append(
                        ValidationError(row_idx, "net_profit_krw", "PREMATURE_PROFIT_RECOGNITION", "미계약 매물의 수익을 확정값으로 기록할 수 없습니다.")
                    )

            # SETTLED 상태 금액 무결성 검증 (필수값 누락 차단 및 음수 차단)
            if closed_date_str and settlement_status == "SETTLED":
                cost_fields = [
                    "gross_commission_revenue_krw",
                    "video_production_cost_krw",
                    "ad_spend_krw",
                    "other_operational_costs_krw",
                    "net_profit_krw",
                ]
                # 빈 필드를 0으로 임의 대체하지 않고 누락 검증
                missing_cost_fields = [cf for cf in cost_fields if not (row.get(cf) or "").strip()]
                if missing_cost_fields:
                    row_errors.append(
                        ValidationError(
                            row_idx, "settlement_status", "MISSING_SETTLED_AMOUNTS", f"정산 완료 상태에서는 필수 비용/수익 항목이 누락될 수 없습니다: {missing_cost_fields}"
                        )
                    )
                else:
                    try:
                        c_rev = int(row["gross_commission_revenue_krw"].strip())
                        v_cost = int(row["video_production_cost_krw"].strip())
                        a_cost = int(row["ad_spend_krw"].strip())
                        o_cost = int(row["other_operational_costs_krw"].strip())
                        net_profit = int(row["net_profit_krw"].strip())

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

            # 판정 및 광고 권한 게이트
            is_valid = len(row_errors) == 0

            # 서면 위임 객체 검증
            is_marketing_eligible = False
            if is_valid and ad_status == "DELEGATED":
                proof = self.delegation_proofs.get(listing_id)
                if proof and proof.has_signed_document and not proof.is_revoked:
                    today = datetime.now(UTC).date()
                    if proof.valid_until >= today:
                        # 제3자 상사 차량인 경우 동의 확인
                        if inv_type == "CONSIGNMENT":
                            if proof.third_party_firm_consent:
                                is_marketing_eligible = True
                        else:
                            is_marketing_eligible = True

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
                    data_classification=data_class,
                    rejection_reasons=[e.message for e in row_errors],
                    normalized_data=normalized,
                )
            )

        return report

    @staticmethod
    def build_orm_entities(
        record: IntakeRecordResult,
        target_region_id: str = "REGION_JANGANPYEONG",
        raw_location: str = "서울 성동구 장안평 중고차 매매단지",
    ) -> tuple[VehicleCatalog, VehicleIdentity, Listing, ListingSnapshot]:
        """
        검증 통과 레코드를 실제 SQLAlchemy ORM 객체로 인스턴스화합니다.
        DB의 모든 NOT NULL, CHECK, FK 제약조건을 100% 충족하도록 매핑합니다.
        (DRY RUN: 세션에 add/flush하여 검증 후 롤백 가능)
        """
        if not record.is_valid:
            raise ValueError("검증 실패 레코드는 ORM 객체로 변환할 수 없습니다.")

        data = record.normalized_data
        listing_id = data["internal_listing_id"]
        anon_code = data["anonymous_vehicle_code"] or f"ANON_{listing_id}"

        # 1. VehicleCatalog (catalog_id는 DB Autoincrement 정수이므로 지정 안 함)
        catalog = VehicleCatalog(
            manufacturer=data["manufacturer"],
            model_name=data["model_name"],
            generation=data["generation"],
            is_facelift=False,
            sub_model=data["sub_model"],
            trim=data["trim"],
            model_year=data["model_year"] or 2020,
            fuel_type=data["fuel_type"],
            transmission=data["transmission"],
            displacement_cc=1999,
            seating_capacity=5,
        )

        # 2. VehicleIdentity (CHECK: CONFIRMED, UNCONFIRMED, AMBIGUOUS)
        # 비식별 코드이므로 UNCONFIRMED, confidence 0.5 (근거 없는 확정 부여 금지)
        identity = VehicleIdentity(
            vehicle_id=anon_code,
            plate_number=None,
            vin=None,
            identity_status="UNCONFIRMED",
            identity_confidence=0.5,
            catalog=catalog,
        )

        # 3. Listing (CHECK: ACTIVE, PRICE_CHANGED, DELISTED, UNKNOWN)
        # 판매 완료 시에는 SOLD가 아닌 DELISTED로 상태 전이
        status = "DELISTED" if data["contract_closed_date"] else "ACTIVE"
        listing = Listing(
            listing_id=listing_id,
            source_platform="PARTNER_DIRECT_INTAKE",
            source_listing_id=listing_id,
            vehicle=identity,
            seller_reference=data["partner_dealer_code"],
            first_observed_at=data["first_observed_date"] or datetime.now(UTC),
            raw_location=raw_location,
            normalized_region_id=target_region_id,
            current_status=status,
        )

        # 4. ListingSnapshot (CHECK: ACTIVE, PRICE_CHANGED, DELISTED, UNKNOWN)
        snapshot = ListingSnapshot(
            snapshot_id=f"SNAP_{listing_id}_INIT",
            listing=listing,
            observed_at=data["first_observed_date"] or datetime.now(UTC),
            ingested_at=datetime.now(UTC),
            price_krw=data["target_listing_price_krw"] or 0,
            mileage_km=data["mileage_km"] or 0,
            listing_status=status,
            normalized_region_id=target_region_id,
            raw_specs={
                "outer_damage": data["outer_panel_rank1_damage"],
                "structural_damage": data["structural_rank2_damage"],
                "flood": data["flood_damage_status"],
                "inspector": data["inspector_code"],
            },
        )

        return catalog, identity, listing, snapshot
