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
    DealerRightsLedger,
    DocumentReview,
    MediaProject,
    RLDecisionLog,
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
    DealerRightsGrantRequest,
    DealerRightsRevokeRequest,
    DocumentApprovalRequest,
    MediaProjectCreateRequest,
    PhotoOrderItem,
    PlatformRegisterIntentRequest,
    RLDecisionEvaluateRequest,
    RLDecisionRewardUpdateRequest,
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

        # 마케팅 권한 파싱 및 가드 (DIRECTIVE 046-D / 047 정밀 권한 원장 감사)
        auth_data = json.loads(v.marketing_auth_json) if v.marketing_auth_json else {}
        is_market_observed = (v.ownership_type == "MARKET_OBSERVED")
        video_allowed = auth_data.get("video_allowed", False)

        # 1. 제휴 딜러 권한 원장(Rights Ledger) 정밀 감사 (철회, 유효기간, 채널 허용 검증 우선)
        latest_ledger = (
            db.query(DealerRightsLedger)
            .filter(DealerRightsLedger.vehicle_id == vehicle_id)
            .order_by(desc(DealerRightsLedger.created_at))
            .first()
        )
        if latest_ledger:
            if latest_ledger.is_revoked:
                raise PermissionError(
                    f"제휴 권한 철회 차단: 해당 차량({v.plate_number})의 제휴 마케팅 권한이 "
                    f"사유('{latest_ledger.revoked_reason or '딜러 요청'}')로 인해 철회되었습니다."
                )
            if not latest_ledger.video_allowed:
                raise PermissionError(
                    f"영상 제작 권한 제한: 해당 제휴 딜러 원장에서 AI 영상 변환 권한이 허용되지 않았습니다."
                )
            if latest_ledger.valid_until:
                today_str = datetime.date.today().isoformat()
                if latest_ledger.valid_until < today_str:
                    raise PermissionError(
                        f"제휴 권한 유효기간 만료 차단: 해당 제휴 계약은 {latest_ledger.valid_until}에 만료되었습니다."
                    )
            allowed_channels = json.loads(latest_ledger.allowed_channels_json or '["YOUTUBE"]')
            if req.target_platform and req.target_platform not in allowed_channels:
                raise PermissionError(
                    f"타겟 플랫폼 불일치 차단: 제휴 딜러가 허용한 채널은 {allowed_channels}입니다. "
                    f"요청된 플랫폼 '{req.target_platform}'은(는) 허용 범위 밖입니다."
                )

        # 2. 시장 관측 매물 및 기본 영상 권한 미승인 차단
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

    # ==========================================
    # 7. DIRECTIVE 047: 장한평 시장 분석 엔진
    # ==========================================
    @staticmethod
    def get_market_analysis_summary(db: Session) -> dict[str, Any]:
        """장한평 중심 시장 매물 관측 및 전국 시세 비교 지표 집계."""
        listings = db.query(VehicleListing).all()
        total_count = len(listings)
        
        jh_listings = [l for l in listings if getattr(l, "is_janghanpyeong", True)]
        other_listings = [l for l in listings if not getattr(l, "is_janghanpyeong", True)]
        
        encar_count = sum(1 for l in listings if l.platform == "ENCAR")
        kb_count = sum(1 for l in listings if l.platform == "KB_CHACHACHA")
        
        price_dropped = [l for l in listings if (getattr(l, "price_drop_amount", 0) or 0) > 0]
        high_opp = [l for l in listings if (getattr(l, "opportunity_score", 0.0) or 0.0) >= 80.0]
        
        avg_price = int(sum(l.advertised_price for l in listings) / total_count) if total_count > 0 else 0
        avg_confidence = round(
            sum(getattr(l, "data_confidence", 0.95) or 0.95 for l in listings) / total_count, 3
        ) if total_count > 0 else 0.95

        return {
            "demo_badge": "CHAMART_DEMO_ENVIRONMENT",
            "is_real_world_market": False,  # 실거래 0건 데모 격리 표기
            "total_listings": total_count,
            "janghanpyeong_count": len(jh_listings),
            "other_regions_count": len(other_listings),
            "encar_count": encar_count,
            "kb_count": kb_count,
            "price_dropped_count": len(price_dropped),
            "high_opportunity_count": len(high_opp),
            "market_avg_price_million_krw": avg_price,
            "avg_data_confidence": avg_confidence,
            "monitored_region_focus": "장한평 중고차 매매단지 (서울 동대문구)",
            "benchmark_region": "수원 도이치오토월드 및 전국 주요 거점",
        }

    @staticmethod
    def list_market_listings(
        db: Session,
        is_janghanpyeong: Optional[bool] = None,
        min_opportunity: float = 0.0,
        price_dropped_only: bool = False,
    ) -> list[dict[str, Any]]:
        """외부 플랫폼 관측 매물 및 가성비·기회 점수 목록 조회."""
        query = db.query(VehicleListing).order_by(desc(VehicleListing.opportunity_score))
        if is_janghanpyeong is not None:
            query = query.filter(VehicleListing.is_janghanpyeong == is_janghanpyeong)
        if min_opportunity > 0.0:
            query = query.filter(VehicleListing.opportunity_score >= min_opportunity)
        if price_dropped_only:
            query = query.filter(VehicleListing.price_drop_amount > 0)

        listings = query.all()
        results = []
        for l in listings:
            v = l.vehicle
            results.append({
                "listing_id": l.id,
                "platform": l.platform,
                "external_id": l.listing_id,
                "listing_url": l.listing_url,
                "advertised_price": l.advertised_price,
                "market_avg_price": getattr(l, "market_avg_price", 0) or 0,
                "price_drop_amount": getattr(l, "price_drop_amount", 0) or 0,
                "opportunity_score": getattr(l, "opportunity_score", 0.0) or 0.0,
                "region": getattr(l, "region", "장한평"),
                "is_janghanpyeong": getattr(l, "is_janghanpyeong", True),
                "data_confidence": getattr(l, "data_confidence", 0.95),
                "listing_status": l.listing_status,
                "vehicle": {
                    "id": v.id if v else None,
                    "plate_number": v.plate_number if v else "-",
                    "model_name": v.model_name if v else "-",
                    "year": v.year if v else 0,
                    "mileage": v.mileage if v else 0,
                    "ownership_type": v.ownership_type if v else "MARKET_OBSERVED",
                    "primary_photo_url": v.primary_photo_url if v else None,
                } if v else None,
            })
        return results

    # ==========================================
    # 8. DIRECTIVE 047: 제휴 딜러 권한 원장 (Rights Ledger)
    # ==========================================
    @staticmethod
    def get_vehicle_rights(db: Session, vehicle_id: str) -> dict[str, Any]:
        """차량의 제휴 권한 원장 및 상태 조회."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        ledger = (
            db.query(DealerRightsLedger)
            .filter(DealerRightsLedger.vehicle_id == vehicle_id)
            .order_by(desc(DealerRightsLedger.created_at))
            .first()
        )
        auth_data = json.loads(v.marketing_auth_json) if v.marketing_auth_json else {}

        return {
            "vehicle_id": v.id,
            "plate_number": v.plate_number,
            "ownership_type": v.ownership_type,
            "has_active_ledger": ledger is not None and not ledger.is_revoked,
            "sale_allowed": ledger.sale_allowed if ledger else auth_data.get("authorized", False),
            "photo_allowed": ledger.photo_allowed if ledger else auth_data.get("photo_allowed", False),
            "video_allowed": ledger.video_allowed if ledger else auth_data.get("video_allowed", False),
            "allowed_channels": json.loads(ledger.allowed_channels_json) if ledger else auth_data.get("allowed_platforms", []),
            "valid_until": ledger.valid_until if ledger else auth_data.get("expires_at"),
            "is_revoked": ledger.is_revoked if ledger else False,
            "revoked_at": ledger.revoked_at.isoformat() if ledger and ledger.revoked_at else None,
            "revoked_reason": ledger.revoked_reason if ledger else None,
            "approved_by": ledger.approved_by if ledger else auth_data.get("authorized_by", "미승인"),
            "dealer_commission_pct": ledger.dealer_commission_pct if ledger else 5.0,
            "chamart_share_pct": ledger.chamart_share_pct if ledger else 15.0,
        }

    @staticmethod
    def grant_vehicle_rights(
        db: Session,
        vehicle_id: str,
        req: DealerRightsGrantRequest,
    ) -> dict[str, Any]:
        """제휴 딜러 권한 부여 및 원장 등록."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        ledger = DealerRightsLedger(
            vehicle_id=v.id,
            dealer_id=v.dealer_id,
            sale_allowed=req.sale_allowed,
            photo_allowed=req.photo_allowed,
            video_allowed=req.video_allowed,
            allowed_channels_json=json.dumps(req.allowed_channels, ensure_ascii=False),
            valid_until=req.valid_until,
            is_revoked=False,
            approved_by=req.approved_by,
            dealer_commission_pct=req.dealer_commission_pct,
            chamart_share_pct=req.chamart_share_pct,
        )
        db.add(ledger)

        # Vehicle 마스터 동기화 및 승인 소유구분으로 격상
        if v.ownership_type in ["MARKET_OBSERVED", "PARTNER_CANDIDATE"]:
            v.ownership_type = "PARTNER_APPROVED"

        v.marketing_auth_json = json.dumps({
            "authorized": req.sale_allowed,
            "video_allowed": req.video_allowed,
            "photo_allowed": req.photo_allowed,
            "authorized_by": req.approved_by,
            "expires_at": req.valid_until,
            "allowed_platforms": req.allowed_channels,
            "is_revoked": False,
        }, ensure_ascii=False)

        db.commit()
        db.refresh(ledger)
        return PlatformService.get_vehicle_rights(db, vehicle_id)

    @staticmethod
    def revoke_vehicle_rights(
        db: Session,
        vehicle_id: str,
        req: DealerRightsRevokeRequest,
    ) -> dict[str, Any]:
        """제휴 권한 철회 및 즉시 차단 처리."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        ledger = (
            db.query(DealerRightsLedger)
            .filter(DealerRightsLedger.vehicle_id == vehicle_id)
            .order_by(desc(DealerRightsLedger.created_at))
            .first()
        )
        if not ledger:
            ledger = DealerRightsLedger(
                vehicle_id=v.id,
                dealer_id=v.dealer_id,
                sale_allowed=False,
                photo_allowed=False,
                video_allowed=False,
            )
            db.add(ledger)

        ledger.is_revoked = True
        ledger.revoked_at = datetime.datetime.utcnow()
        ledger.revoked_reason = req.reason
        ledger.video_allowed = False
        ledger.sale_allowed = False

        # 차량 마스터에도 권한 철회 즉시 반영
        auth_data = json.loads(v.marketing_auth_json) if v.marketing_auth_json else {}
        auth_data["video_allowed"] = False
        auth_data["authorized"] = False
        auth_data["is_revoked"] = True
        auth_data["revoked_reason"] = req.reason
        auth_data["revoked_by"] = req.revoked_by
        v.marketing_auth_json = json.dumps(auth_data, ensure_ascii=False)

        db.commit()
        return PlatformService.get_vehicle_rights(db, vehicle_id)

    # ==========================================
    # 9. DIRECTIVE 047: AI 영상 판매 성과 및 기여도 (Attribution)
    # ==========================================
    @staticmethod
    def get_attribution_summary(db: Session) -> dict[str, Any]:
        """AI 영상 콘텐츠 기여도, 자연 판매 구분 및 공헌이익 정산 분석."""
        sales = db.query(Transaction).filter(Transaction.transaction_type == "SALE").all()
        total_sales = len(sales)
        
        ai_sales = [s for s in sales if getattr(s, "attribution_type", "") == "AI_VIDEO"]
        organic_sales = [s for s in sales if getattr(s, "attribution_type", "") != "AI_VIDEO"]

        total_chamart_net = sum(getattr(s, "chamart_net_profit", 0) or 0 for s in sales)
        ai_chamart_net = sum(getattr(s, "chamart_net_profit", 0) or 0 for s in ai_sales)
        total_operating_cost = sum(getattr(s, "operating_cost", 0) or 0 for s in ai_sales)

        roi_pct = 0.0
        if total_operating_cost > 0:
            roi_pct = round(((ai_chamart_net - total_operating_cost) / total_operating_cost) * 100.0, 1)

        # 문의 채널 분석 (중복 문의 제외 유효 상담 수)
        consultations = db.query(Consultation).all()
        valid_consultations = [c for c in consultations if not getattr(c, "is_duplicate", False)]
        video_leads = [
            c for c in valid_consultations
            if getattr(c, "inquiry_source", "") in ["YOUTUBE_SHORTS", "INSTAGRAM_REELS", "TIKTOK"]
        ]

        return {
            "demo_badge": "CHAMART_DEMO_ENVIRONMENT",
            "total_sales_count": total_sales,
            "ai_video_attributed_sales": len(ai_sales),
            "organic_sales": len(organic_sales),
            "ai_video_share_pct": round((len(ai_sales) / total_sales * 100.0), 1) if total_sales > 0 else 0.0,
            "total_chamart_net_profit_million_krw": total_chamart_net,
            "ai_video_net_profit_million_krw": ai_chamart_net,
            "total_content_operating_cost_million_krw": total_operating_cost,
            "ai_video_roi_pct": roi_pct,
            "lead_metrics": {
                "total_valid_leads": len(valid_consultations),
                "ai_video_sourced_leads": len(video_leads),
                "duplicate_leads_quarantined": len(consultations) - len(valid_consultations),
            },
            "attribution_rule": "영상 시청 및 해당 링크/태그 문의 고객 중복 제거 후 실계약 매칭",
        }

    @staticmethod
    def get_vehicle_attribution_trail(db: Session, vehicle_id: str) -> dict[str, Any]:
        """차량 1대의 발굴 -> 승인 -> 영상제작 -> 문의 -> 계약 -> 정산 전 과정 추적."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        timeline = []
        # 1. 관측/등록
        timeline.append({
            "stage": "MARKET_DISCOVERY",
            "title": "매물 관측 및 마스터 등록",
            "timestamp": v.created_at.strftime("%Y-%m-%d %H:%M"),
            "details": f"{v.plate_number} ({v.model_name}) 매물 등록 (구분: {v.ownership_type})",
        })

        # 2. 제휴 권한
        ledger = (
            db.query(DealerRightsLedger)
            .filter(DealerRightsLedger.vehicle_id == vehicle_id)
            .order_by(desc(DealerRightsLedger.created_at))
            .first()
        )
        if ledger:
            timeline.append({
                "stage": "RIGHTS_AUTHORIZATION",
                "title": "제휴 딜러 권한 승인" if not ledger.is_revoked else "제휴 권한 철회",
                "timestamp": ledger.created_at.strftime("%Y-%m-%d %H:%M"),
                "details": f"승인자: {ledger.approved_by}, 영상허용: {ledger.video_allowed}, 철회: {ledger.is_revoked}",
            })

        # 3. 영상 프로젝트
        projects = db.query(MediaProject).filter(MediaProject.vehicle_id == vehicle_id).all()
        for p in projects:
            timeline.append({
                "stage": "AI_VIDEO_PRODUCTION",
                "title": f"AI 영상 프로젝트 ({p.content_format})",
                "timestamp": p.created_at.strftime("%Y-%m-%d %H:%M"),
                "details": f"상태: {p.status}, 타겟: {p.target_platform}, 제목: {p.title}",
            })

        # 4. 거래 및 정산
        transactions = db.query(Transaction).filter(Transaction.vehicle_id == vehicle_id).all()
        for t in transactions:
            timeline.append({
                "stage": "TRANSACTION_SETTLEMENT",
                "title": f"계약 및 정산 ({t.transaction_type})",
                "timestamp": t.transaction_date,
                "details": f"금액: {t.amount:,}만원, 기여유형: {getattr(t, 'attribution_type', 'ORGANIC')}, 순익: {getattr(t, 'chamart_net_profit', 0)}만원",
            })

        return {
            "vehicle_id": v.id,
            "plate_number": v.plate_number,
            "model_name": v.model_name,
            "ownership_type": v.ownership_type,
            "trail_count": len(timeline),
            "timeline": timeline,
        }

    # ==========================================
    # 10. DIRECTIVE 047: 강화학습(RL) 오프라인 데이터 파이프라인
    # ==========================================
    @staticmethod
    def evaluate_rl_decision(
        db: Session,
        vehicle_id: str,
        policy_version: str = "v1.0-rule_baseline",
    ) -> dict[str, Any]:
        """관측 시점 기준 State 구성 -> Baseline Action 결정 -> Offline RL Log 기록.
        
        [Data Leakage 방지]:
        미래의 거래/정산 결과나 삭제 여부를 State에 절대 포함하지 않으며,
        현재 차량 스펙, 시장 평균가, 권한 유무, 결함비용만으로 상태 벡터를 만듭니다.
        """
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        # Listing에서 시장 평균 시세 및 가격 인하액 조회
        listing = db.query(VehicleListing).filter(VehicleListing.vehicle_id == vehicle_id).first()
        market_avg = getattr(listing, "market_avg_price", 0) if listing else (v.target_price + 150)
        price_drop = getattr(listing, "price_drop_amount", 0) if listing else 0
        region = getattr(listing, "region", "장한평") if listing else "장한평"
        confidence = getattr(listing, "data_confidence", 0.95) if listing else 0.95

        # 권한 원장 확인
        ledger = (
            db.query(DealerRightsLedger)
            .filter(DealerRightsLedger.vehicle_id == vehicle_id)
            .order_by(desc(DealerRightsLedger.created_at))
            .first()
        )
        auth_data = json.loads(v.marketing_auth_json) if v.marketing_auth_json else {}
        rights_allowed = (ledger.video_allowed and not ledger.is_revoked) if ledger else auth_data.get("video_allowed", False)

        # 결함 및 수리비 집계
        defect_count = db.query(VehicleDefect).filter(VehicleDefect.vehicle_id == vehicle_id).count()
        defects = db.query(VehicleDefect).filter(VehicleDefect.vehicle_id == vehicle_id).all()
        repair_cost_sum = sum(d.estimated_repair_cost for d in defects)

        # 1. State Vector 구성 (과거/현재 관측치만 사용)
        discount_ratio = 0.0
        if market_avg > 0 and v.target_price > 0:
            discount_ratio = round((market_avg - v.target_price) / market_avg, 4)

        state = {
            "target_price": v.target_price,
            "market_avg_price": market_avg,
            "price_discount_ratio": discount_ratio,
            "price_drop_amount": price_drop,
            "year": v.year,
            "mileage": v.mileage,
            "defect_count": defect_count,
            "estimated_repair_cost": repair_cost_sum,
            "region": region,
            "data_confidence": confidence,
            "rights_video_allowed": rights_allowed,
            "ownership_type": v.ownership_type,
        }

        # 2. Rule Baseline Policy 결정
        # 가성비 및 권한 유무에 따른 기계적 규칙 기반 Action
        if not rights_allowed:
            if discount_ratio > 0.05 or price_drop > 100:
                action = "REQUEST_DEALER_REVIEW"  # 가성비가 높으나 권한이 없으므로 딜러 접촉 제휴 검토
                action_prob = 0.88
                action_details = {"priority": "HIGH", "reason": "시세 대비 저렴한 매물 제휴 시급"}
            else:
                action = "OBSERVE"  # 권한 없고 특이사항 없으므로 관망
                action_prob = 0.95
                action_details = {"priority": "LOW", "reason": "관측 유지"}
        else:
            if discount_ratio >= 0.05:
                action = "PROPOSE_VIDEO"  # 권한 있고 가성비 우수 -> 즉시 영상 제작 제안
                action_prob = 0.92
                action_details = {"channels": ["YOUTUBE", "INSTAGRAM"], "budget_won": 200000}
            else:
                action = "ADJUST_PRIORITY"  # 권한 있으나 시세와 유사 -> 우선순위 조정
                action_prob = 0.80
                action_details = {"priority": "MEDIUM", "reason": "영상 제작 대기열 보통 순위"}

        # 3. 시간순 데이터 분할 (Split)
        # 2026-10월 이전은 TRAIN, 이후는 VAL / TEST
        now = datetime.datetime.utcnow()
        split = "VAL" if now.month >= 10 else "TRAIN"

        decision = RLDecisionLog(
            timestamp=now,
            policy_version=policy_version,
            vehicle_id=v.id,
            state_json=json.dumps(state, ensure_ascii=False),
            action=action,
            action_prob=action_prob,
            action_details_json=json.dumps(action_details, ensure_ascii=False),
            reward=None,  # 의사결정 당시에는 미래 보상 미확정 (None)
            reward_details_json=json.dumps({"status": "OBSERVING"}, ensure_ascii=False),
            is_censored=True,
            split=split,
            is_demo=True,
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)

        return {
            "decision_id": decision.id,
            "vehicle_id": v.id,
            "policy_version": decision.policy_version,
            "action": decision.action,
            "action_prob": decision.action_prob,
            "action_details": action_details,
            "is_censored": decision.is_censored,
            "split": decision.split,
            "state_vector": state,
        }

    @staticmethod
    def list_rl_decisions(
        db: Session,
        split: Optional[str] = None,
        is_censored: Optional[bool] = None,
    ) -> list[dict[str, Any]]:
        """강화학습 오프라인 의사결정 로그 목록 조회."""
        query = db.query(RLDecisionLog).order_by(desc(RLDecisionLog.timestamp))
        if split:
            query = query.filter(RLDecisionLog.split == split)
        if is_censored is not None:
            query = query.filter(RLDecisionLog.is_censored == is_censored)

        logs = query.all()
        results = []
        for l in logs:
            results.append({
                "id": l.id,
                "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M"),
                "policy_version": l.policy_version,
                "vehicle_id": l.vehicle_id,
                "vehicle_plate": l.vehicle.plate_number if l.vehicle else "-",
                "action": l.action,
                "action_prob": l.action_prob,
                "action_details": json.loads(l.action_details_json or "{}"),
                "reward": l.reward,
                "reward_details": json.loads(l.reward_details_json or "{}"),
                "is_censored": l.is_censored,
                "split": l.split,
                "state": json.loads(l.state_json or "{}"),
            })
        return results

    @staticmethod
    def update_rl_reward(
        db: Session,
        decision_id: str,
        req: RLDecisionRewardUpdateRequest,
    ) -> dict[str, Any]:
        """실제 판매·정산 완결에 따른 강화학습 보상(Reward) 확정 및 검열 해제."""
        log = db.query(RLDecisionLog).filter(RLDecisionLog.id == decision_id).first()
        if not log:
            raise ValueError(f"RL 의사결정 로그 '{decision_id}'를 찾을 수 없습니다.")

        # 보상 계산: 확정수수료 - 운영비 + 검증계약기여도보너스 - (체류일수 페널티)
        time_penalty = req.days_to_sell * 0.5
        net_reward = round(
            req.fee_revenue - req.operating_cost + (50.0 if req.verified_contribution > 0.5 else 0.0) - time_penalty,
            2,
        )

        reward_details = {
            "fee_revenue": req.fee_revenue,
            "operating_cost": req.operating_cost,
            "days_to_sell": req.days_to_sell,
            "verified_contribution": req.verified_contribution,
            "time_penalty": time_penalty,
            "net_reward": net_reward,
            "notes": req.notes,
        }

        log.reward = net_reward
        log.reward_details_json = json.dumps(reward_details, ensure_ascii=False)
        log.is_censored = False  # 관측 종결 (Uncensored)
        db.commit()
        db.refresh(log)

        return {
            "decision_id": log.id,
            "reward": log.reward,
            "is_censored": log.is_censored,
            "reward_details": reward_details,
        }

    @staticmethod
    def get_rl_readiness_audit(db: Session) -> dict[str, Any]:
        """강화학습 실전 적용 적합성 및 데이터 규모 자동 진단."""
        total_logs = db.query(RLDecisionLog).count()
        uncensored_logs = db.query(RLDecisionLog).filter(RLDecisionLog.is_censored == False).count()
        censored_logs = total_logs - uncensored_logs

        # 권장 기준
        min_required_samples = 500
        is_ready_for_bandit = uncensored_logs >= 50
        is_ready_for_offline_rl = uncensored_logs >= min_required_samples

        status_text = "COLLECTING_INITIAL_BASELINE_DATA"
        recommendation = (
            "현재 실전 오프라인 데이터 수집 초기 단계입니다. "
            "PPO 등 대규모 강화학습 모델의 성급한 도입은 과적합과 치명적 비용 왜곡을 유발하므로 절대 금지하며, "
            "현재의 규칙 기반 추천과 성과 로깅을 유지하면서 비검열 데이터가 50건 이상 누적 시 Contextual Bandit, "
            "500건 이상 누적 시 Conservative Q-Learning(CQL) 평가 단계로 순차 전환해야 합니다."
        )

        return {
            "demo_badge": "CHAMART_DEMO_ENVIRONMENT",
            "total_decision_logs": total_logs,
            "uncensored_completed_logs": uncensored_logs,
            "censored_observing_logs": censored_logs,
            "min_required_samples": min_required_samples,
            "readiness_status": status_text,
            "can_train_contextual_bandit": is_ready_for_bandit,
            "can_train_offline_rl": is_ready_for_offline_rl,
            "guard_ppo_prohibited": True,  # 대규모 RL 조기 도입 차단 원칙
            "recommendation": recommendation,
        }
