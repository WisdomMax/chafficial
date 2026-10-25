"""차마트 통합 운영 플랫폼 비즈니스 로직 및 서비스 레이어."""

from __future__ import annotations

import datetime
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from chaficial.platform.search import normalize_phone_number, parse_currency_amount
from chaficial.platform.db import (
    Branch,
    Consultation,
    Customer,
    Dealer,
    DocumentReview,
    MediaProject,
    Transaction,
    User,
    Vehicle,
    VehicleDefect,
    VehicleListing,
    VehiclePhoto,
    get_db,
)
from chaficial.platform.models import (
    ConsultationCreateRequest,
    CustomerCreateRequest,
    CustomerUpdateRequest,
    DocumentApprovalRequest,
    MediaProjectCreateRequest,
    PhotoOrderItem,
    PlatformRegisterIntentRequest,
    TransactionCreateRequest,
    VehicleCreateRequest,
    VehicleDefectCreateRequest,
    VehicleDefectUpdateRequest,
    VehicleMasterUpdateRequest,
    VehiclePhotoReorderRequest,
    VehicleStatusChangeRequest,
    VehicleUpdateRequest,
    VehicleVideoProjectCreateRequest,
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class PlatformService:
    """플랫폼 핵심 비즈니스 로직 서비스."""

    @staticmethod
    def get_overview_kpis(db: Session) -> dict[str, Any]:
        """대시보드 KPI 지표 요약 집계."""
        total_vehicles = db.query(Vehicle).count()
        for_sale_vehicles = db.query(Vehicle).filter(Vehicle.status == "FOR_SALE").count()
        detailing_vehicles = db.query(Vehicle).filter(Vehicle.status.in_(["IN_STOCK", "DETAILING"])).count()
        contracting_vehicles = db.query(Vehicle).filter(Vehicle.status == "CONTRACTING").count()

        total_customers = db.query(Customer).count()
        active_consultations = db.query(Customer).filter(Customer.status.in_(["NEW", "CONSULTING", "VEHICLE_MATCHED"])).count()

        total_projects = db.query(MediaProject).count()
        in_prod_projects = db.query(MediaProject).filter(MediaProject.status.in_(["REQUESTED", "IN_PRODUCTION", "REVIEW"])).count()

        pending_docs = db.query(DocumentReview).filter(DocumentReview.review_status == "PENDING").count()

        # 최근 거래 합계
        purchases = db.query(Transaction).filter(Transaction.transaction_type == "PURCHASE").all()
        sales = db.query(Transaction).filter(Transaction.transaction_type == "SALE").all()
        purchase_sum = sum(p.amount for p in purchases)
        sale_sum = sum(s.amount for s in sales)

        branches = db.query(Branch).all()

        return {
            "demo_badge": "CHAMART_DEMO_ENVIRONMENT",
            "kpis": {
                "total_vehicles": total_vehicles,
                "for_sale_vehicles": for_sale_vehicles,
                "detailing_vehicles": detailing_vehicles,
                "contracting_vehicles": contracting_vehicles,
                "total_customers": total_customers,
                "active_consultations": active_consultations,
                "total_projects": total_projects,
                "in_prod_projects": in_prod_projects,
                "pending_docs": pending_docs,
                "purchase_sum_million_krw": purchase_sum,
                "sale_sum_million_krw": sale_sum,
            },
            "branches": [
                {
                    "id": b.id,
                    "name": b.name,
                    "region": b.region,
                    "vehicle_count": len(b.vehicles),
                    "customer_count": len(b.customers),
                }
                for b in branches
            ],
        }

    # ==========================================
    # 1. 지점 및 조직
    # ==========================================
    @staticmethod
    def list_branches(db: Session) -> list[dict[str, Any]]:
        branches = db.query(Branch).all()
        return [
            {
                "id": b.id,
                "name": b.name,
                "region": b.region,
                "address": b.address,
                "is_headquarters": b.is_headquarters,
            }
            for b in branches
        ]

    # ==========================================
    # 2. 차량 관리 CRUD & 상태 전이
    # ==========================================
    @staticmethod
    def list_vehicles(
        db: Session,
        branch_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query = db.query(Vehicle)
        if branch_id:
            query = query.filter(Vehicle.branch_id == branch_id)
        if status:
            query = query.filter(Vehicle.status == status)
        query = query.order_by(desc(Vehicle.created_at))
        vehicles = query.all()

        results = []
        for v in vehicles:
            dealer_name = v.dealer.name if v.dealer else None
            dealership_name = v.dealer.dealership_name if v.dealer else "차마트 직영"
            results.append({
                "id": v.id,
                "branch_id": v.branch_id,
                "branch_name": v.branch.name if v.branch else "지점 미지정",
                "plate_number": v.plate_number,
                "model_name": v.model_name,
                "year": v.year,
                "mileage": v.mileage,
                "fuel_type": v.fuel_type,
                "transmission": v.transmission,
                "color": v.color,
                "purchase_price": v.purchase_price,
                "target_price": v.target_price,
                "status": v.status,
                "ownership_type": v.ownership_type or "CHAMART_OWNED",
                "dealer_id": v.dealer_id,
                "dealer_name": dealer_name,
                "dealership_name": dealership_name,
                "primary_photo_url": v.primary_photo_url,
                "video_status": v.video_status or "NONE",
                "has_partner_auth": (v.ownership_type in ["PARTNER_APPROVED", "CHAMART_OWNED"]),
                "created_at": v.created_at.strftime("%Y-%m-%d %H:%M"),
            })
        return results

    @staticmethod
    def get_vehicle(db: Session, vehicle_id: str) -> Optional[dict[str, Any]]:
        return PlatformService.get_vehicle_detail(db, vehicle_id)

    @staticmethod
    def get_vehicle_detail(db: Session, vehicle_id: str) -> Optional[dict[str, Any]]:
        """DIRECTIVE 046-D 차량 마스터 종합 상세 정보 조회 (기본정보, 사고/보험, 성능/하자, 사진, 매물이력, 영상 연계)."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            return None

        timeline = json.loads(v.timeline_json) if v.timeline_json else []
        options = json.loads(v.options_json) if v.options_json else []
        accident_history = json.loads(v.accident_history_json) if v.accident_history_json else {}
        inspection_summary = json.loads(v.inspection_summary_json) if v.inspection_summary_json else {}
        marketing_auth = json.loads(v.marketing_auth_json) if v.marketing_auth_json else {}

        # 딜러 정보
        dealer_info = None
        if v.dealer:
            dealer_info = {
                "id": v.dealer.id,
                "name": v.dealer.name,
                "dealership_name": v.dealer.dealership_name,
                "phone": v.dealer.phone,
                "partnership_status": v.dealer.partnership_status,
                "contract_date": v.dealer.contract_date,
            }

        # 부위별 하자 목록
        defects = [
            {
                "id": d.id,
                "part_name": d.part_name,
                "defect_type": d.defect_type,
                "severity": d.severity,
                "action_status": d.action_status,
                "estimated_repair_cost": d.estimated_repair_cost,
                "photo_url": d.photo_url,
                "notes": d.notes,
                "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for d in v.defects
        ]

        # 사진 자산 목록 (순서 정렬)
        photos = [
            {
                "id": p.id,
                "photo_url": p.photo_url,
                "thumb_url": p.thumb_url or p.photo_url,
                "category": p.category,
                "sort_order": p.sort_order,
                "is_primary": p.is_primary,
                "allow_video_use": p.allow_video_use,
                "caption": p.caption,
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for p in sorted(v.photos, key=lambda x: (not x.is_primary, x.sort_order))
        ]

        # 외부 매물 Listing 목록
        listings = [
            {
                "id": l.id,
                "platform": l.platform,
                "listing_id": l.listing_id,
                "listing_url": l.listing_url,
                "advertised_price": l.advertised_price,
                "listing_status": l.listing_status,
                "first_observed_at": l.first_observed_at.strftime("%Y-%m-%d"),
                "last_observed_at": l.last_observed_at.strftime("%Y-%m-%d"),
            }
            for l in v.listings
        ]

        # 연계된 AI 영상 프로젝트 목록
        media_projects = [
            {
                "id": m.id,
                "title": m.title,
                "content_format": m.content_format,
                "concept": m.concept,
                "status": m.status,
                "target_platform": m.target_platform,
                "created_at": m.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for m in v.media_projects
        ]

        return {
            "id": v.id,
            "branch_id": v.branch_id,
            "branch_name": v.branch.name if v.branch else "지점 미지정",
            "plate_number": v.plate_number,
            "model_name": v.model_name,
            "year": v.year,
            "mileage": v.mileage,
            "fuel_type": v.fuel_type,
            "transmission": v.transmission,
            "color": v.color,
            "purchase_price": v.purchase_price,
            "target_price": v.target_price,
            "status": v.status,
            "ownership_type": v.ownership_type or "CHAMART_OWNED",
            "dealer": dealer_info,
            "vin": v.vin or "미확인",
            "displacement_cc": v.displacement_cc,
            "first_registration_date": v.first_registration_date,
            "drive_type": v.drive_type,
            "interior_color": v.interior_color,
            "options": options,
            "accident_history": accident_history,
            "inspection_summary": inspection_summary,
            "marketing_auth": marketing_auth,
            "primary_photo_url": v.primary_photo_url,
            "video_status": v.video_status or "NONE",
            "defects": defects,
            "photos": photos,
            "listings": listings,
            "media_projects": media_projects,
            "timeline": timeline,
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": v.updated_at.strftime("%Y-%m-%d %H:%M"),
        }

    @staticmethod
    def update_vehicle_master(db: Session, vehicle_id: str, req: VehicleMasterUpdateRequest) -> Optional[dict[str, Any]]:
        """DIRECTIVE 046-D 차량 마스터 정보 일괄 수정."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            return None

        if req.plate_number:
            v.plate_number = req.plate_number.strip()
        if req.model_name:
            v.model_name = req.model_name.strip()
        if req.year is not None:
            v.year = req.year
        if req.mileage is not None:
            v.mileage = req.mileage
        if req.target_price is not None:
            v.target_price = parse_currency_amount(req.target_price)
        if req.purchase_price is not None:
            v.purchase_price = parse_currency_amount(req.purchase_price)
        if req.status:
            v.status = req.status
        if req.ownership_type:
            v.ownership_type = req.ownership_type
        if req.dealer_id is not None:
            v.dealer_id = req.dealer_id if req.dealer_id != "" else None
        if req.vin:
            v.vin = req.vin.strip().upper()
        if req.displacement_cc is not None:
            v.displacement_cc = req.displacement_cc
        if req.first_registration_date:
            v.first_registration_date = req.first_registration_date
        if req.drive_type:
            v.drive_type = req.drive_type
        if req.interior_color:
            v.interior_color = req.interior_color
        if req.options is not None:
            v.options_json = json.dumps(req.options, ensure_ascii=False)
        if req.accident_history is not None:
            v.accident_history_json = json.dumps(req.accident_history, ensure_ascii=False)
        if req.inspection_summary is not None:
            v.inspection_summary_json = json.dumps(req.inspection_summary, ensure_ascii=False)
        if req.marketing_auth is not None:
            v.marketing_auth_json = json.dumps(req.marketing_auth, ensure_ascii=False)
        if req.primary_photo_url:
            v.primary_photo_url = req.primary_photo_url

        v.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(v)
        return PlatformService.get_vehicle_detail(db, v.id)

    @staticmethod
    def add_vehicle_defect(db: Session, vehicle_id: str, req: VehicleDefectCreateRequest) -> dict[str, Any]:
        """부위별 하자 신규 등록."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        defect = VehicleDefect(
            vehicle_id=v.id,
            part_name=req.part_name.strip(),
            defect_type=req.defect_type.strip(),
            severity=req.severity,
            action_status=req.action_status,
            estimated_repair_cost=parse_currency_amount(req.estimated_repair_cost) or 0,
            notes=req.notes,
        )
        db.add(defect)
        db.commit()
        db.refresh(defect)
        return {
            "id": defect.id,
            "part_name": defect.part_name,
            "defect_type": defect.defect_type,
            "severity": defect.severity,
            "action_status": defect.action_status,
            "estimated_repair_cost": defect.estimated_repair_cost,
            "notes": defect.notes,
            "created_at": defect.created_at.strftime("%Y-%m-%d %H:%M"),
        }

    @staticmethod
    def update_vehicle_defect(db: Session, defect_id: str, req: VehicleDefectUpdateRequest) -> Optional[dict[str, Any]]:
        """부위별 하자 정보 수정 (조치상태, 수리비 등)."""
        defect = db.query(VehicleDefect).filter(VehicleDefect.id == defect_id).first()
        if not defect:
            return None
        if req.part_name:
            defect.part_name = req.part_name.strip()
        if req.defect_type:
            defect.defect_type = req.defect_type.strip()
        if req.severity:
            defect.severity = req.severity
        if req.action_status:
            defect.action_status = req.action_status
        if req.estimated_repair_cost is not None:
            defect.estimated_repair_cost = parse_currency_amount(req.estimated_repair_cost) or 0
        if req.notes is not None:
            defect.notes = req.notes
        db.commit()
        db.refresh(defect)
        return {
            "id": defect.id,
            "part_name": defect.part_name,
            "defect_type": defect.defect_type,
            "severity": defect.severity,
            "action_status": defect.action_status,
            "estimated_repair_cost": defect.estimated_repair_cost,
            "notes": defect.notes,
        }

    @staticmethod
    def delete_vehicle_defect(db: Session, defect_id: str) -> bool:
        defect = db.query(VehicleDefect).filter(VehicleDefect.id == defect_id).first()
        if not defect:
            return False
        db.delete(defect)
        db.commit()
        return True

    @staticmethod
    def add_vehicle_photo(
        db: Session,
        vehicle_id: str,
        photo_url: str,
        thumb_url: Optional[str] = None,
        category: str = "EXTERIOR",
        sort_order: int = 0,
        is_primary: bool = False,
        allow_video_use: bool = True,
        caption: Optional[str] = None,
    ) -> dict[str, Any]:
        """차량 사진 자산 등록."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        if is_primary:
            # 기존 사진들의 대표 플래그 해제
            db.query(VehiclePhoto).filter(VehiclePhoto.vehicle_id == vehicle_id).update({"is_primary": False})
            v.primary_photo_url = photo_url

        photo = VehiclePhoto(
            vehicle_id=vehicle_id,
            photo_url=photo_url,
            thumb_url=thumb_url or photo_url,
            category=category,
            sort_order=sort_order,
            is_primary=is_primary,
            allow_video_use=allow_video_use,
            caption=caption,
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
        return {
            "id": photo.id,
            "photo_url": photo.photo_url,
            "thumb_url": photo.thumb_url,
            "category": photo.category,
            "sort_order": photo.sort_order,
            "is_primary": photo.is_primary,
            "allow_video_use": photo.allow_video_use,
            "caption": photo.caption,
        }

    @staticmethod
    def reorder_vehicle_photos(db: Session, vehicle_id: str, req: VehiclePhotoReorderRequest) -> list[dict[str, Any]]:
        """사진 순서 변경, 대표사진 지정 및 영상 사용 여부 일괄 갱신."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        for item in req.photo_orders:
            p = db.query(VehiclePhoto).filter(VehiclePhoto.id == item.id, VehiclePhoto.vehicle_id == vehicle_id).first()
            if p:
                p.sort_order = item.sort_order
                p.is_primary = item.is_primary
                p.allow_video_use = item.allow_video_use
                if item.category:
                    p.category = item.category
                if item.is_primary:
                    v.primary_photo_url = p.photo_url

        db.commit()
        return PlatformService.get_vehicle_detail(db, vehicle_id)["photos"]

    @staticmethod
    def delete_vehicle_photo(db: Session, photo_id: str) -> bool:
        p = db.query(VehiclePhoto).filter(VehiclePhoto.id == photo_id).first()
        if not p:
            return False
        v_id = p.vehicle_id
        is_prim = p.is_primary
        db.delete(p)
        db.commit()

        # 만약 삭제된 사진이 대표 사진이었다면 남은 첫번째 사진을 대표로 지정
        if is_prim:
            next_photo = db.query(VehiclePhoto).filter(VehiclePhoto.vehicle_id == v_id).order_by(VehiclePhoto.sort_order).first()
            v = db.query(Vehicle).filter(Vehicle.id == v_id).first()
            if next_photo and v:
                next_photo.is_primary = True
                v.primary_photo_url = next_photo.photo_url
                db.commit()
            elif v:
                v.primary_photo_url = None
                db.commit()
        return True

    @staticmethod
    def create_video_project_from_vehicle(
        db: Session,
        vehicle_id: str,
        req: VehicleVideoProjectCreateRequest,
    ) -> dict[str, Any]:
        """DIRECTIVE 046-D 차량 -> AI 영상 프로젝트 연계 생성.
        
        [보안 및 비즈니스 가드 (TEST 8 & TEST 9)]:
        1. 광고 권한이 없는 시장 관측 매물(MARKET_OBSERVED)은 영상 제작 원천 차단!
        2. 제휴 딜러와의 권한 확인(marketing_auth.video_allowed == True)이 완료된 차량만 생성 허용.
        """
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        # 마케팅 권한 파싱 및 가드
        auth_data = json.loads(v.marketing_auth_json) if v.marketing_auth_json else {}
        is_market_observed = (v.ownership_type == "MARKET_OBSERVED")
        video_allowed = auth_data.get("video_allowed", False)

        if is_market_observed or not video_allowed:
            raise PermissionError(
                f"광고 및 영상 제작 권한 미승인 차단: 해당 매물({v.plate_number})은 시장 관측 또는 권한 미확인 매물입니다. "
                "원 소속 딜러와의 제휴 승인 및 영상 권한 확인 후 제작이 가능합니다."
            )

        # 차량 마스터 데이터를 기반으로 홍보 대본 초안 자동 구성
        title = req.custom_title or f"[{req.content_format}] {v.year}년식 {v.model_name} 실매물 검증"
        concept = req.concept or f"실차주 제휴 인증 매물 - {v.color}"
        
        script = (
            f"오늘 소개해드릴 실매물은 {v.year}년식 {v.model_name}입니다!\n"
            f"주행거리 {v.mileage:,}km, {v.transmission} 변속기에 깔끔한 {v.color} 바디입니다.\n"
            f"실제 광고가격 {v.target_price:,}만원에 입고되었으며, 차마트에서 성능점검과 사고이력을 직접 검증했습니다.\n"
            "지금 바로 문의주시면 빠른 시운전과 상담이 가능합니다!"
        )

        project = MediaProject(
            title=title,
            vehicle_id=v.id,
            content_format=req.content_format,
            concept=concept,
            target_platform=req.target_platform,
            status="REQUESTED",
            script_draft=script,
        )
        db.add(project)
        v.video_status = "REQUESTED"
        db.commit()
        db.refresh(project)

        return {
            "id": project.id,
            "vehicle_id": project.vehicle_id,
            "title": project.title,
            "content_format": project.content_format,
            "concept": project.concept,
            "target_platform": project.target_platform,
            "status": project.status,
            "script_draft": project.script_draft,
            "created_at": project.created_at.strftime("%Y-%m-%d %H:%M"),
        }

    @staticmethod
    def list_dealers(db: Session) -> list[dict[str, Any]]:
        """제휴 딜러 목록 조회."""
        dealers = db.query(Dealer).all()
        return [
            {
                "id": d.id,
                "name": d.name,
                "dealership_name": d.dealership_name,
                "phone": d.phone,
                "partnership_status": d.partnership_status,
                "contract_date": d.contract_date,
            }
            for d in dealers
        ]

    @staticmethod
    def register_platform_intent(db: Session, vehicle_id: str, req: PlatformRegisterIntentRequest) -> dict[str, Any]:
        """미래 다중 플랫폼 자동 등록 준비 및 검증 어댑터 (DIRECTIVE 046-D 제13항).
        
        [보안 제한]: 외부 실제 엔카/카매니저 자동 게시는 공식 계약/API 승인 전까지 차단하며,
        검증된 스키마 무결성 및 대기 상태(PENDING_PARTNERSHIP_API_AGREEMENT)만 안전하게 반환.
        """
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        results = {}
        for platform in req.platforms:
            results[platform] = {
                "platform": platform,
                "vehicle_plate": v.plate_number,
                "status": "BLOCKED_PENDING_OFFICIAL_API_AGREEMENT",
                "message": f"{platform} 공식 제휴 API 연동 전으로, 임의 자동 게시가 안전하게 차단되었습니다.",
                "readiness": {
                    "vin_valid": bool(v.vin and len(v.vin) == 17),
                    "options_count": len(json.loads(v.options_json)) if v.options_json else 0,
                    "photos_count": len(v.photos),
                    "has_primary_photo": bool(v.primary_photo_url),
                }
            }
        return {
            "vehicle_id": v.id,
            "platforms": results,
            "summary": "다중 플랫폼 광고 등록 준비 상태 검증 완료 (외부 실제 전송 차단됨)"
        }

    @staticmethod
    def create_vehicle(db: Session, req: VehicleCreateRequest) -> dict[str, Any]:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        initial_timeline = [
            {"timestamp": now_str, "event": f"신규 차량 등록 ({req.plate_number} / {req.model_name})"}
        ]
        v = Vehicle(
            branch_id=req.branch_id,
            plate_number=req.plate_number.strip(),
            model_name=req.model_name.strip(),
            year=req.year,
            mileage=req.mileage,
            fuel_type=req.fuel_type,
            transmission=req.transmission,
            color=req.color,
            purchase_price=parse_currency_amount(req.purchase_price) if req.purchase_price is not None else None,
            target_price=parse_currency_amount(req.target_price) if req.target_price is not None else None,
            status=req.status,
            timeline_json=json.dumps(initial_timeline, ensure_ascii=False),
        )
        db.add(v)
        db.commit()
        db.refresh(v)
        return PlatformService.get_vehicle(db, v.id)

    @staticmethod
    def update_vehicle(db: Session, vehicle_id: str, req: VehicleUpdateRequest) -> Optional[dict[str, Any]]:
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            return None

        update_data = req.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(v, key, val)

        v.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(v)
        return PlatformService.get_vehicle(db, v.id)

    @staticmethod
    def change_vehicle_status(db: Session, vehicle_id: str, new_status: str, reason: str = "") -> Optional[dict[str, Any]]:
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            return None

        prev_status = v.status
        v.status = new_status
        v.updated_at = datetime.datetime.utcnow()

        timeline = json.loads(v.timeline_json) if v.timeline_json else []
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        event_msg = f"상태 변경: {prev_status} -> {new_status}"
        if reason:
            event_msg += f" (사유: {reason})"
        timeline.append({"timestamp": now_str, "event": event_msg})
        v.timeline_json = json.dumps(timeline, ensure_ascii=False)

        db.commit()
        db.refresh(v)
        return PlatformService.get_vehicle(db, v.id)

    # ==========================================
    # 3. 고객 CRM & 상담 기록
    # ==========================================
    @staticmethod
    def list_customers(
        db: Session,
        branch_id: Optional[str] = None,
        status: Optional[str] = None,
        query_str: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        query = db.query(Customer)
        if branch_id:
            query = query.filter(Customer.branch_id == branch_id)
        if status:
            query = query.filter(Customer.status == status)
        if query_str:
            query = query.filter(
                (Customer.name.contains(query_str)) | (Customer.phone.contains(query_str))
            )
        customers = query.order_by(desc(Customer.created_at)).all()

        results = []
        for c in customers:
            results.append({
                "id": c.id,
                "branch_name": c.branch.name if c.branch else "지점 미지정",
                "name": c.name,
                "phone": c.phone,
                "status": c.status,
                "target_vehicle_model": c.target_vehicle_model or "-",
                "budget_max": c.budget_max or 0,
                "assigned_staff": c.assigned_staff,
                "consultation_count": len(c.consultations),
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
            })
        return results

    @staticmethod
    def get_customer(db: Session, customer_id: str) -> Optional[dict[str, Any]]:
        c = db.query(Customer).filter(Customer.id == customer_id).first()
        if not c:
            return None

        consultations = [
            {
                "id": cons.id,
                "channel": cons.channel,
                "content": cons.content,
                "staff_name": cons.staff_name,
                "next_action_date": cons.next_action_date or "-",
                "created_at": cons.created_at.strftime("%Y-%m-%d %H:%M"),
            }
            for cons in sorted(c.consultations, key=lambda x: x.created_at, reverse=True)
        ]

        return {
            "id": c.id,
            "branch_id": c.branch_id,
            "branch_name": c.branch.name if c.branch else "지점 미지정",
            "name": c.name,
            "phone": c.phone,
            "status": c.status,
            "target_vehicle_model": c.target_vehicle_model,
            "budget_max": c.budget_max,
            "assigned_staff": c.assigned_staff,
            "contact_consent": c.contact_consent,
            "notes": c.notes,
            "consultations": consultations,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
        }

    @staticmethod
    def create_customer(db: Session, req: CustomerCreateRequest) -> dict[str, Any]:
        # DIRECTIVE 046-C 전화번호 및 금액 표준화 적용
        clean_phone = normalize_phone_number(req.phone)
        clean_budget = parse_currency_amount(req.budget_max) if req.budget_max is not None else None

        c = Customer(
            branch_id=req.branch_id,
            name=req.name.strip(),
            phone=clean_phone,
            status=req.status,
            target_vehicle_model=req.target_vehicle_model,
            budget_max=clean_budget,
            assigned_staff=req.assigned_staff or "차마트 상담팀",
            contact_consent=req.contact_consent,
            notes=req.notes,
        )
        db.add(c)
        db.commit()
        db.refresh(c)
        return PlatformService.get_customer(db, c.id)

    @staticmethod
    def add_consultation(db: Session, customer_id: str, req: ConsultationCreateRequest) -> dict[str, Any]:
        c = db.query(Customer).filter(Customer.id == customer_id).first()
        if not c:
            raise ValueError(f"고객을 찾을 수 없습니다: {customer_id}")

        cons = Consultation(
            customer_id=customer_id,
            channel=req.channel,
            content=req.content,
            staff_name=req.staff_name,
            next_action_date=req.next_action_date,
        )
        db.add(cons)
        db.commit()
        return PlatformService.get_customer(db, customer_id)

    # ==========================================
    # 4. 거래·계약 관리
    # ==========================================
    @staticmethod
    def list_transactions(db: Session) -> list[dict[str, Any]]:
        txs = db.query(Transaction).order_by(desc(Transaction.transaction_date)).all()
        results = []
        for t in txs:
            results.append({
                "id": t.id,
                "vehicle_id": t.vehicle_id,
                "vehicle_plate": t.vehicle.plate_number if t.vehicle else "차량 미지정",
                "vehicle_model": t.vehicle.model_name if t.vehicle else "-",
                "transaction_type": t.transaction_type,
                "amount": t.amount,
                "party_name": t.party_name,
                "party_contact": t.party_contact or "-",
                "transaction_date": t.transaction_date,
                "settlement_status": t.settlement_status,
                "notes": t.notes or "",
            })
        return results

    @staticmethod
    def create_transaction(db: Session, req: TransactionCreateRequest) -> dict[str, Any]:
        v = db.query(Vehicle).filter(Vehicle.id == req.vehicle_id).first()
        if not v:
            raise ValueError(f"연결할 차량이 존재하지 않습니다: {req.vehicle_id}")

        tx = Transaction(
            vehicle_id=req.vehicle_id,
            transaction_type=req.transaction_type,
            amount=req.amount,
            party_name=req.party_name,
            party_contact=req.party_contact,
            transaction_date=req.transaction_date,
            settlement_status="SETTLED",
            notes=req.notes,
        )
        db.add(tx)

        # 차량 상태 및 타임라인 연동
        if req.transaction_type == "SALE":
            v.status = "CONTRACTING"
            timeline = json.loads(v.timeline_json) if v.timeline_json else []
            timeline.append({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "event": f"판매 거래 등록 ({req.party_name} / {req.amount}만원)",
            })
            v.timeline_json = json.dumps(timeline, ensure_ascii=False)

        db.commit()
        db.refresh(tx)
        return {
            "id": tx.id,
            "vehicle_plate": v.plate_number,
            "transaction_type": tx.transaction_type,
            "amount": tx.amount,
            "party_name": tx.party_name,
            "transaction_date": tx.transaction_date,
        }

    # ==========================================
    # 5. AI 서류 인식 검토 대기열
    # ==========================================
    @staticmethod
    def list_documents(db: Session) -> list[dict[str, Any]]:
        docs = db.query(DocumentReview).order_by(desc(DocumentReview.created_at)).all()
        results = []
        for d in docs:
            extracted = json.loads(d.extracted_data_json) if d.extracted_data_json else {}
            results.append({
                "id": d.id,
                "doc_type": d.doc_type,
                "filename": d.filename,
                "file_size_kb": round(d.file_size / 1024, 1),
                "file_sha256": d.file_sha256,
                "review_status": d.review_status,
                "approved_by": d.approved_by or "-",
                "extracted_data": extracted,
                "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"),
            })
        return results

    @staticmethod
    def save_and_register_document(
        db: Session,
        file_bytes: bytes,
        filename: str,
        doc_type: str,
    ) -> dict[str, Any]:
        """업로드된 서류 파일의 SHA-256 검증 및 분석 대기열 등록."""
        sha256_hash = hashlib.sha256(file_bytes).hexdigest()

        # 중복 파일 검사
        existing = db.query(DocumentReview).filter(DocumentReview.file_sha256 == sha256_hash).first()
        if existing:
            return {
                "status": "DUPLICATE_DETECTED",
                "message": "동일한 내용의 서류가 이미 등록되어 있습니다.",
                "doc_id": existing.id,
                "sha256": sha256_hash,
            }

        # 로컬 파일 저장
        save_path = UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}_{filename}"
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        # 서류 유형에 따른 AI 분석 시뮬레이션 메타데이터 추출
        extracted_mock = {
            "source_type": doc_type,
            "file_sha256": sha256_hash,
            "ocr_status": "READY_FOR_REVIEW",
            "extracted_fields": {
                "plate_number": "차량번호 자동 인식 대기",
                "date": datetime.date.today().isoformat(),
                "confidence_score": 0.94,
            },
        }

        doc = DocumentReview(
            doc_type=doc_type,
            filename=filename,
            file_path=str(save_path),
            file_sha256=sha256_hash,
            file_size=len(file_bytes),
            extracted_data_json=json.dumps(extracted_mock, ensure_ascii=False),
            review_status="PENDING",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        return {
            "status": "UPLOAD_SUCCESS",
            "doc_id": doc.id,
            "filename": filename,
            "sha256": sha256_hash,
            "review_status": "PENDING",
        }

    @staticmethod
    def approve_document(db: Session, doc_id: str, req: DocumentApprovalRequest) -> dict[str, Any]:
        doc = db.query(DocumentReview).filter(DocumentReview.id == doc_id).first()
        if not doc:
            raise ValueError("서류를 찾을 수 없습니다.")

        doc.review_status = "APPROVED" if req.approved else "REJECTED"
        doc.approved_by = req.reviewer_name
        db.commit()
        db.refresh(doc)
        return {
            "id": doc.id,
            "review_status": doc.review_status,
            "approved_by": doc.approved_by,
        }

    # ==========================================
    # 6. AI 영상 스튜디오
    # ==========================================
    @staticmethod
    def list_media_projects(db: Session) -> list[dict[str, Any]]:
        projects = db.query(MediaProject).order_by(desc(MediaProject.created_at)).all()
        results = []
        for p in projects:
            results.append({
                "id": p.id,
                "title": p.title,
                "vehicle_id": p.vehicle_id,
                "vehicle_plate": p.vehicle.plate_number if p.vehicle else "차량 미연결",
                "vehicle_model": p.vehicle.model_name if p.vehicle else "-",
                "content_format": p.content_format,
                "concept": p.concept,
                "status": p.status,
                "target_platform": p.target_platform,
                "script_draft": p.script_draft or "",
                "created_at": p.created_at.strftime("%Y-%m-%d %H:%M"),
            })
        return results

    @staticmethod
    def create_media_project(db: Session, req: MediaProjectCreateRequest) -> dict[str, Any]:
        script = req.script_draft
        if not script and req.vehicle_id:
            # 차량 정보 기반 자동 대본 초안 생성
            v = db.query(Vehicle).filter(Vehicle.id == req.vehicle_id).first()
            if v:
                script = (
                    f"[{req.content_format} 초안] "
                    f"“{v.year}년식 {v.model_name}! 주행거리 {v.mileage:,}km 무사고 차량. "
                    f"장한평 차마트 본사에서 {v.target_price}만원에 실매물 직접 확인하세요!”"
                )

        project = MediaProject(
            title=req.title,
            vehicle_id=req.vehicle_id,
            content_format=req.content_format,
            concept=req.concept,
            status="DRAFT",
            target_platform=req.target_platform,
            script_draft=script,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return {
            "id": project.id,
            "title": project.title,
            "status": project.status,
            "content_format": project.content_format,
            "script_draft": project.script_draft,
        }

    @staticmethod
    def update_media_project_status(db: Session, project_id: str, new_status: str) -> dict[str, Any]:
        p = db.query(MediaProject).filter(MediaProject.id == project_id).first()
        if not p:
            raise ValueError("프로젝트를 찾을 수 없습니다.")
        p.status = new_status
        db.commit()
        db.refresh(p)
        return {"id": p.id, "status": p.status}
