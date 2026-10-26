"""KB차차차(KB_CHACHACHA) 전용 필드 매핑 및 등록 준비도 검사 어댑터 (DIRECTIVE 050)."""

from __future__ import annotations
import json
from typing import Any
from chaficial.platform.publishing.base import BasePlatformMapper, ReadinessReport
from chaficial.platform.catalog.options import StandardOptionCatalog


class KbPlatformMapper(BasePlatformMapper):
    """KB차차차 규격 매퍼 (사진 8장, KB안심매물 진단 요건, 딜러 권한 확인)."""

    def __init__(self):
        super().__init__("KB_CHACHACHA")

    def validate_readiness(self, vehicle: Any, context: dict[str, Any] | None = None) -> ReadinessReport:
        missing = []
        warnings = []
        errors = []

        # 1. 필수 제원 검증
        if not getattr(vehicle, "plate_number", None):
            missing.append("차량번호(plate_number)")
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

        # 2. 사진 수량 검증
        photos = getattr(vehicle, "photos", []) or []
        if len(photos) < 8:
            missing.append(f"KB차차차 필수 사진 수량 부족 (최소 8장 필요, 현재: {len(photos)}장)")

        # 3. 성능점검 검증
        acc_json = getattr(vehicle, "accident_history_json", "{}") or "{}"
        try:
            acc_data = json.loads(acc_json) if isinstance(acc_json, str) else acc_json
        except Exception:
            acc_data = {}

        if acc_data.get("accident_state") == "UNCHECKED":
            errors.append("KB 안심매물 등록 차단: 성능점검 미검증(UNCHECKED) 차량은 등록할 수 없습니다.")

        # 4. 권한 검증
        ownership = getattr(vehicle, "ownership_type", "CHAMART_OWNED")
        if ownership == "MARKET_OBSERVED":
            errors.append("시장 관측 매물(MARKET_OBSERVED)은 외부 KB차차차 재등록이 금지됩니다.")

        is_ready = len(missing) == 0 and len(errors) == 0
        summary = "KB차차차 등록 준비 완료" if is_ready else f"KB차차차 등록 미비 ({len(missing)}건 필수값 누락, {len(errors)}건 차단 오류)"

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
        """KB차차차 API/전산 규격 등록 페이로드 생성."""
        raw_opts = getattr(vehicle, "options_structured_json", "[]") or "[]"
        try:
            opt_list = json.loads(raw_opts) if isinstance(raw_opts, str) else raw_opts
        except Exception:
            opt_list = []

        kb_option_codes = []
        for opt in opt_list:
            code = opt.get("code")
            s_opt = StandardOptionCatalog.get_by_code(code)
            if s_opt and s_opt.kb_code and opt.get("is_installed", True):
                kb_option_codes.append(s_opt.kb_code)

        photos = getattr(vehicle, "photos", []) or []

        return {
            "platform": "KB_CHACHACHA",
            "car_reg_no": vehicle.plate_number,
            "car_name": vehicle.model_name,
            "car_year": vehicle.year,
            "car_mileage": vehicle.mileage,
            "sell_price_man": vehicle.target_price,
            "fuel_kind": vehicle.fuel_type,
            "transmission_kind": vehicle.transmission,
            "option_codes": kb_option_codes,
            "photo_urls": [p.photo_url for p in photos],
            "intro_text": getattr(vehicle, "ad_description", "") or "",
            "export_version": "v1.0-kb_standard",
        }
