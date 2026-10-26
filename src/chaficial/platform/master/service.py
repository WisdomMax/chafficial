"""차량 마스터 통합 입력, 수정 및 다중 플랫폼 게시 서비스 (DIRECTIVE 050)."""

from __future__ import annotations
import datetime
import json
import uuid
from typing import Any
from sqlalchemy.orm import Session
from chaficial.platform.db import (
    Vehicle,
    Dealer,
    Branch,
    DealerRightsLedger,
    VehiclePhoto,
    VehicleDefect,
    PlatformPublishingRecord,
)
from chaficial.platform.catalog.hierarchy import VehicleCatalogService
from chaficial.platform.catalog.options import StandardOptionCatalog
from chaficial.platform.publishing.validator import PublishingReadinessValidator


class MasterVehicleService:
    """차마트 통합 차량 마스터 입력·수정·조회 및 플랫폼 연동 관리자."""

    validator = PublishingReadinessValidator()

    @classmethod
    def create_vehicle_master(cls, db: Session, data: dict[str, Any]) -> dict[str, Any]:
        """8대 영역을 포괄하는 신규 차량 마스터 등록 (DIRECTIVE 050 1항)."""
        plate_number = (data.get("plate_number") or "").strip()
        if not plate_number:
            raise ValueError("차량번호는 필수 입력 항목입니다.")

        # 중복 등록 검증
        existing = db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()
        if existing:
            raise ValueError(f"차량번호 '{plate_number}'는 이미 등록되어 있습니다. (기존 차량 ID: {existing.id})")

        # 지점 확보
        branch_id = data.get("branch_id")
        if not branch_id:
            branch = db.query(Branch).first()
            branch_id = branch.id if branch else str(uuid.uuid4())

        # 트림 기반 기본값 자동 보정 (있는 경우에만 채움, 미확인은 None 유지)
        manufacturer = data.get("manufacturer")
        model_name = data.get("model_name") or "미상 모델"
        generation = data.get("generation")
        trim = data.get("trim")

        displacement_cc = data.get("displacement_cc")
        fuel_type = data.get("fuel_type") or "가솔린"
        transmission = data.get("transmission") or "오토"
        drive_type = data.get("drive_type") or "2WD"
        body_type = data.get("body_type") or "세단"

        if manufacturer and model_name and generation and trim and not displacement_cc:
            defaults = VehicleCatalogService.get_spec_defaults(manufacturer, model_name, generation, trim)
            displacement_cc = defaults.get("displacement_cc")
            body_type = defaults.get("body_type") or body_type

        # 구조화된 옵션 JSON 처리
        options_structured = data.get("options_structured") or []
        options_json_str = json.dumps(options_structured, ensure_ascii=False)

        # 사고/점검 JSON 처리
        condition_detail = data.get("condition_detail") or {}
        accident_history = data.get("accident_history") or {
            "accident_state": condition_detail.get("accident_state", "UNCHECKED"),
            "frame_damage": condition_detail.get("frame_damage", "미확인 (성능점검표 미등록)"),
            "outer_damage": condition_detail.get("outer_damage", "미확인"),
            "outer_panel_exchange": condition_detail.get("outer_panel_exchange", "미확인 (성능점검표 미등록)"),
            "insurance_accident_count": condition_detail.get("insurance_accident_count", "전산 조회 대기"),
            "special_accident": condition_detail.get("special_accident", "미확인"),
        }

        vehicle = Vehicle(
            branch_id=branch_id,
            plate_number=plate_number,
            vin=data.get("vin"),
            manufacturer=manufacturer,
            model_name=model_name,
            trim=trim,
            year=int(data.get("year") or 2022),
            first_registration_date=data.get("first_registration_date"),
            mileage=int(data.get("mileage") or 0),
            displacement_cc=displacement_cc,
            fuel_type=fuel_type,
            transmission=transmission,
            drive_type=drive_type,
            body_type=body_type,
            color=data.get("color") or "화이트",
            interior_color=data.get("interior_color") or "블랙",
            target_price=int(data.get("target_price") or 0),
            purchase_price=int(data.get("purchase_price") or 0),
            recon_cost=int(data.get("recon_cost") or 0),
            sales_conditions=data.get("sales_conditions") or "현금/할부/리스 가능",
            ownership_type=data.get("ownership_type") or "CHAMART_OWNED",
            dealer_id=data.get("dealer_id"),
            status=data.get("status") or "FOR_SALE",
            ad_description=data.get("ad_description"),
            ad_highlights=data.get("ad_highlights"),
            ad_notices=data.get("ad_notices"),
            platform_ad_copies_json=json.dumps(data.get("platform_ad_copies") or {}, ensure_ascii=False),
            options_structured_json=options_json_str,
            options_json=json.dumps([opt.get("name") for opt in options_structured if opt.get("name")], ensure_ascii=False),
            condition_detail_json=json.dumps(condition_detail, ensure_ascii=False),
            accident_history_json=json.dumps(accident_history, ensure_ascii=False),
            publishing_status="DRAFT",
            is_demo=False,
            created_at=datetime.datetime.utcnow(),
            updated_at=datetime.datetime.utcnow(),
        )
        db.add(vehicle)
        db.flush()

        # 사진 등록이 전달된 경우 처리
        photos = data.get("photos") or []
        for idx, p in enumerate(photos):
            photo_url = p.get("photo_url") or p.get("url")
            if photo_url:
                v_photo = VehiclePhoto(
                    vehicle_id=vehicle.id,
                    photo_url=photo_url,
                    category=p.get("category", "EXTERIOR"),
                    sort_order=p.get("sort_order", idx),
                    is_primary=bool(p.get("is_primary", idx == 0)),
                    caption=p.get("caption"),
                )
                db.add(v_photo)
                if v_photo.is_primary and not vehicle.primary_photo_url:
                    vehicle.primary_photo_url = photo_url

        # 제휴 딜러 권한이 전달된 경우 등록
        marketing_auth = data.get("marketing_auth")
        if marketing_auth and isinstance(marketing_auth, dict):
            ledger = DealerRightsLedger(
                vehicle_id=vehicle.id,
                dealer_id=vehicle.dealer_id,
                approved_by=marketing_auth.get("approved_by", "장한평 제휴 딜러"),
                sale_allowed=True,
                video_allowed=marketing_auth.get("video_allowed", True),
                photo_allowed=marketing_auth.get("photo_allowed", True),
                allowed_channels_json=json.dumps(["YOUTUBE", "INSTAGRAM", "ENCAR", "KB"], ensure_ascii=False),
                is_revoked=False,
            )
            db.add(ledger)

        db.commit()
        db.refresh(vehicle)

        # 다중 플랫폼 등록 준비도 자동 평가
        readiness = cls.validator.evaluate_vehicle_readiness(db, vehicle, sync_db=True)

        return cls.get_vehicle_master(db, vehicle.id)

    @classmethod
    def update_vehicle_master(cls, db: Session, vehicle_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """차량 마스터 정보 수정 및 플랫폼 게시 준비 데이터 자동 동기화 (DIRECTIVE 050 6항)."""
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        # 기본 제원 필드 갱신
        updatable_fields = [
            "plate_number", "vin", "manufacturer", "model_name", "trim",
            "year", "first_registration_date", "mileage", "displacement_cc",
            "fuel_type", "transmission", "drive_type", "body_type",
            "color", "interior_color", "target_price", "purchase_price",
            "recon_cost", "sales_conditions", "ownership_type", "dealer_id",
            "status", "ad_description", "ad_highlights", "ad_notices"
        ]
        for field in updatable_fields:
            if field in data and data[field] is not None:
                setattr(vehicle, field, data[field])

        # 플랫폼별 문구 갱신
        if "platform_ad_copies" in data:
            vehicle.platform_ad_copies_json = json.dumps(data["platform_ad_copies"], ensure_ascii=False)

        # 구조화 옵션 갱신
        if "options_structured" in data:
            vehicle.options_structured_json = json.dumps(data["options_structured"], ensure_ascii=False)
            vehicle.options_json = json.dumps(
                [opt.get("name") for opt in data["options_structured"] if opt.get("name")],
                ensure_ascii=False,
            )

        # 점검/사고 상세 갱신
        if "condition_detail" in data:
            vehicle.condition_detail_json = json.dumps(data["condition_detail"], ensure_ascii=False)
        if "accident_history" in data:
            vehicle.accident_history_json = json.dumps(data["accident_history"], ensure_ascii=False)

        # 사진 갱신 (전달된 경우)
        if "photos" in data and isinstance(data["photos"], list):
            # 기존 사진 정리 및 재등록 (또는 추가)
            db.query(VehiclePhoto).filter(VehiclePhoto.vehicle_id == vehicle.id).delete()
            for idx, p in enumerate(data["photos"]):
                photo_url = p.get("photo_url") or p.get("url")
                if photo_url:
                    v_photo = VehiclePhoto(
                        vehicle_id=vehicle.id,
                        photo_url=photo_url,
                        category=p.get("category", "EXTERIOR"),
                        sort_order=p.get("sort_order", idx),
                        is_primary=bool(p.get("is_primary", idx == 0)),
                        caption=p.get("caption"),
                    )
                    db.add(v_photo)
                    if v_photo.is_primary:
                        vehicle.primary_photo_url = photo_url

        vehicle.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(vehicle)

        # 수정 반영 후 플랫폼 등록 준비도 자동 재평가
        cls.validator.evaluate_vehicle_readiness(db, vehicle, sync_db=True)

        return cls.get_vehicle_master(db, vehicle.id)

    @classmethod
    def get_vehicle_master(cls, db: Session, vehicle_id: str) -> dict[str, Any]:
        """8대 영역 표준 구조로 차량 마스터 데이터 통합 조회 (DIRECTIVE 050 1항)."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        # 1. 기본 제원
        basic_specs = {
            "vehicle_id": v.id,
            "plate_number": v.plate_number,
            "vin": v.vin,
            "manufacturer": v.manufacturer,
            "model_name": v.model_name,
            "trim": v.trim,
            "year": v.year,
            "first_registration_date": v.first_registration_date,
            "mileage": v.mileage,
            "displacement_cc": v.displacement_cc,
            "fuel_type": v.fuel_type,
            "transmission": v.transmission,
            "drive_type": v.drive_type,
            "body_type": v.body_type,
            "color": v.color,
            "interior_color": v.interior_color,
        }

        # 2. 구조화 옵션
        try:
            options_structured = json.loads(v.options_structured_json or "[]")
        except Exception:
            options_structured = []

        # 3. 사고 및 성능 상태
        try:
            condition_detail = json.loads(v.condition_detail_json or "{}")
        except Exception:
            condition_detail = {}
        try:
            accident_history = json.loads(v.accident_history_json or "{}")
        except Exception:
            accident_history = {}

        # 4. 사진 자산
        photos = [
            {
                "id": p.id,
                "photo_url": p.photo_url,
                "category": p.category,
                "sort_order": p.sort_order,
                "is_primary": p.is_primary,
                "caption": p.caption,
            }
            for p in (v.photos or [])
        ]

        # 5. 가격 및 판매 프로필
        dealer_info = None
        if v.dealer:
            dealer_info = {
                "dealer_id": v.dealer.id,
                "name": v.dealer.name,
                "dealership_name": v.dealer.dealership_name,
                "phone": v.dealer.phone,
            }
        sales_profile = {
            "target_price": v.target_price,
            "purchase_price": v.purchase_price,
            "recon_cost": getattr(v, "recon_cost", 0),
            "status": v.status,
            "ownership_type": v.ownership_type,
            "sales_conditions": getattr(v, "sales_conditions", "현금/할부 가능"),
            "dealer": dealer_info,
            "branch_id": v.branch_id,
        }

        # 6. 광고 상세 설명
        try:
            platform_ad_copies = json.loads(v.platform_ad_copies_json or "{}")
        except Exception:
            platform_ad_copies = {}
        ad_content = {
            "ad_description": v.ad_description,
            "ad_highlights": v.ad_highlights,
            "ad_notices": v.ad_notices,
            "platform_ad_copies": platform_ad_copies,
        }

        # 7. 권한 및 승인
        rights_records = [
            {
                "id": r.id,
                "approved_by": r.approved_by,
                "sale_allowed": r.sale_allowed,
                "video_allowed": r.video_allowed,
                "photo_allowed": r.photo_allowed,
                "is_revoked": r.is_revoked,
                "valid_until": r.valid_until,
            }
            for r in (v.rights_ledgers or [])
        ]

        # 8. 플랫폼 연동 및 등록 준비도
        try:
            platform_readiness = json.loads(v.platform_readiness_json or "{}")
        except Exception:
            platform_readiness = {}

        return {
            "vehicle_id": v.id,
            "publishing_status": getattr(v, "publishing_status", "DRAFT"),
            "basic_specs": basic_specs,
            "options": options_structured,
            "condition": {
                "accident_history": accident_history,
                "condition_detail": condition_detail,
                "defects_count": len(v.defects or []),
            },
            "media": {
                "primary_photo_url": v.primary_photo_url,
                "photos_count": len(photos),
                "photos": photos,
            },
            "sales_profile": sales_profile,
            "ad_content": ad_content,
            "rights": {
                "has_rights": any(not r.is_revoked for r in (v.rights_ledgers or [])),
                "ledgers": rights_records,
            },
            "platform_publishing": platform_readiness,
            "updated_at": v.updated_at.isoformat() if v.updated_at else None,
        }
