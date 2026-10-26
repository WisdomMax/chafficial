"""카매니저(CAR_MANAGER) 전용 필드 매핑 및 등록 준비도 검사 어댑터 (DIRECTIVE 050)."""

from __future__ import annotations
import json
from typing import Any
from chaficial.platform.publishing.base import BasePlatformMapper, ReadinessReport
from chaficial.platform.catalog.options import StandardOptionCatalog


class CarManagerPlatformMapper(BasePlatformMapper):
    """카매니저 전산 규격 매퍼 (상사/딜러 소속, 매입가/판매가, 사진 6장)."""

    def __init__(self):
        super().__init__("CAR_MANAGER")

    def validate_readiness(self, vehicle: Any, context: dict[str, Any] | None = None) -> ReadinessReport:
        missing = []
        warnings = []
        errors = []

        # 1. 필수 제원 및 상사/딜러 검증
        if not getattr(vehicle, "plate_number", None):
            missing.append("차량번호(plate_number)")
        if not getattr(vehicle, "model_name", None):
            missing.append("모델명(model_name)")
        if not getattr(vehicle, "target_price", None) or vehicle.target_price <= 0:
            missing.append("소비자 광고가격(target_price)")

        dealer_id = getattr(vehicle, "dealer_id", None)
        ownership = getattr(vehicle, "ownership_type", "CHAMART_OWNED")
        if not dealer_id and ownership != "CHAMART_OWNED":
            missing.append("소속 상사/딜러(dealer_id)")

        # 2. 사진 수량 검증
        photos = getattr(vehicle, "photos", []) or []
        if len(photos) < 6:
            missing.append(f"카매니저 최소 사진 수량 부족 (최소 6장 필요, 현재: {len(photos)}장)")

        # 3. 권한 검증
        if ownership == "MARKET_OBSERVED":
            errors.append("시장 관측 매물(MARKET_OBSERVED)은 딜러 전산망 카매니저 등록이 금지됩니다.")

        is_ready = len(missing) == 0 and len(errors) == 0
        summary = "카매니저 등록 준비 완료" if is_ready else f"카매니저 등록 미비 ({len(missing)}건 필수값 누락, {len(errors)}건 차단 오류)"

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
        """카매니저 전산 등록 페이로드 생성."""
        raw_opts = getattr(vehicle, "options_structured_json", "[]") or "[]"
        try:
            opt_list = json.loads(raw_opts) if isinstance(raw_opts, str) else raw_opts
        except Exception:
            opt_list = []

        cm_option_codes = []
        for opt in opt_list:
            code = opt.get("code")
            s_opt = StandardOptionCatalog.get_by_code(code)
            if s_opt and s_opt.carmanager_code and opt.get("is_installed", True):
                cm_option_codes.append(s_opt.carmanager_code)

        photos = getattr(vehicle, "photos", []) or []

        return {
            "platform": "CAR_MANAGER",
            "car_no": vehicle.plate_number,
            "car_name": vehicle.model_name,
            "trim_name": getattr(vehicle, "trim", "") or "",
            "model_year": vehicle.year,
            "mileage": vehicle.mileage,
            "sale_price": vehicle.target_price,
            "wholesale_price": getattr(vehicle, "purchase_price", 0),
            "dealer_id": getattr(vehicle, "dealer_id", "CHAMART_HQ"),
            "options": cm_option_codes,
            "photos": [p.photo_url for p in photos],
            "condition_notes": getattr(vehicle, "ad_notices", "") or "",
            "export_version": "v1.0-carmanager_standard",
        }
