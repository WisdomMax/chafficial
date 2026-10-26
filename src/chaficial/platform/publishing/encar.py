"""엔카(ENCAR) 전용 필드 매핑 및 등록 준비도 검사 어댑터 (DIRECTIVE 050)."""

from __future__ import annotations
import json
from typing import Any
from chaficial.platform.publishing.base import BasePlatformMapper, ReadinessReport
from chaficial.platform.catalog.options import StandardOptionCatalog


class EncarPlatformMapper(BasePlatformMapper):
    """엔카 규격 매퍼 (사진 10장, 차대번호 17자리, 성능기록부, 딜러 권한 필수)."""

    def __init__(self):
        super().__init__("ENCAR")

    def validate_readiness(self, vehicle: Any, context: dict[str, Any] | None = None) -> ReadinessReport:
        missing = []
        warnings = []
        errors = []

        # 1. 필수 제원 검증
        if not getattr(vehicle, "plate_number", None):
            missing.append("차량번호(plate_number)")
        if not getattr(vehicle, "vin", None):
            missing.append("차대번호(vin)")
        elif len(str(vehicle.vin).strip()) != 17:
            warnings.append(f"차대번호 규격 비표준 (17자리 권장, 현재: {len(str(vehicle.vin).strip())}자리)")

        if not getattr(vehicle, "manufacturer", None):
            missing.append("제조사(manufacturer)")
        if not getattr(vehicle, "model_name", None):
            missing.append("모델명(model_name)")
        if not getattr(vehicle, "year", None) or vehicle.year < 1990:
            missing.append("연식(year)")
        if not getattr(vehicle, "mileage", None) or vehicle.mileage <= 0:
            missing.append("주행거리(mileage)")
        if not getattr(vehicle, "target_price", None) or vehicle.target_price <= 0:
            missing.append("광고가격(target_price)")
        if not getattr(vehicle, "fuel_type", None):
            missing.append("연료구분(fuel_type)")
        if not getattr(vehicle, "transmission", None):
            missing.append("변속기(transmission)")

        # 2. 사진 수량 및 카테고리 검증
        photos = getattr(vehicle, "photos", []) or []
        if len(photos) < 10:
            missing.append(f"엔카 필수 사진 수량 부족 (최소 10장 필요, 현재: {len(photos)}장)")

        categories = {getattr(p, "category", "EXTERIOR") for p in photos}
        if "EXTERIOR" not in categories:
            warnings.append("외관(EXTERIOR) 사진 컷 누락")
        if "INTERIOR" not in categories:
            warnings.append("실내(INTERIOR) 사진 컷 누락")

        # 3. 사고 및 성능점검 검증
        acc_json = getattr(vehicle, "accident_history_json", "{}") or "{}"
        try:
            acc_data = json.loads(acc_json) if isinstance(acc_json, str) else acc_json
        except Exception:
            acc_data = {}

        if acc_data.get("accident_state") == "UNCHECKED":
            errors.append("엔카 광고 등록 차단: 성능점검 미검증(UNCHECKED) 차량은 등록할 수 없습니다.")

        # 4. 딜러 판매/광고 권한 검증
        rights = getattr(vehicle, "rights_ledgers", []) or []
        has_valid_rights = any(
            getattr(r, "video_allowed", False) or getattr(r, "photo_allowed", False)
            for r in rights
            if not getattr(r, "is_revoked", False)
        )
        ownership = getattr(vehicle, "ownership_type", "CHAMART_OWNED")
        if ownership in ["PARTNER_APPROVED", "PARTNER_CANDIDATE"] and not has_valid_rights:
            errors.append("제휴 매물 엔카 등록 차단: 유효한 제휴 딜러 광고 권한 원장(Rights Ledger)이 없습니다.")
        elif ownership == "MARKET_OBSERVED":
            errors.append("시장 관측 매물(MARKET_OBSERVED)은 외부 엔카 재등록이 금지됩니다 (무단 광고 차단).")

        is_ready = len(missing) == 0 and len(errors) == 0
        summary = "엔카 등록 준비 완료" if is_ready else f"엔카 등록 미비 ({len(missing)}건 필수값 누락, {len(errors)}건 차단 오류)"

        payload = self.build_export_payload(vehicle, context) if is_ready else {}

        return ReadinessReport(
            platform=self.platform_name,
            is_ready=is_ready,
            missing_fields=missing,
            warnings=warnings,
            errors=errors,
            mapped_payload=payload,
            summary_message=summary,
        )

    def build_export_payload(self, vehicle: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """엔카 API/전산 규격 등록 페이로드 생성."""
        # 옵션 매핑
        structured_opts = []
        raw_opts = getattr(vehicle, "options_structured_json", "[]") or "[]"
        try:
            opt_list = json.loads(raw_opts) if isinstance(raw_opts, str) else raw_opts
        except Exception:
            opt_list = []

        encar_option_codes = []
        for opt in opt_list:
            code = opt.get("code")
            s_opt = StandardOptionCatalog.get_by_code(code)
            if s_opt and s_opt.encar_code and opt.get("is_installed", True):
                encar_option_codes.append(s_opt.encar_code)

        photos = getattr(vehicle, "photos", []) or []
        photo_urls = [p.photo_url for p in photos]

        return {
            "platform": "ENCAR",
            "vehicle_no": vehicle.plate_number,
            "vin": getattr(vehicle, "vin", ""),
            "manufacturer": getattr(vehicle, "manufacturer", ""),
            "model_name": vehicle.model_name,
            "grade_trim": getattr(vehicle, "trim", "") or "",
            "model_year": vehicle.year,
            "first_reg_date": getattr(vehicle, "first_registration_date", ""),
            "mileage_km": vehicle.mileage,
            "advertised_price_krw": vehicle.target_price * 10000,
            "fuel_type": vehicle.fuel_type,
            "transmission": vehicle.transmission,
            "color": vehicle.color,
            "options": encar_option_codes,
            "photos": photo_urls,
            "sales_note": getattr(vehicle, "ad_description", "") or f"{vehicle.model_name} 실매물 판매합니다.",
            "export_version": "v1.0-encar_standard",
        }
