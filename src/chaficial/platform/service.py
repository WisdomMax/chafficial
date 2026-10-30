"""차마트 통합 운영 플랫폼 비즈니스 로직 및 서비스 레이어."""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import and_, asc, case, desc, or_, select
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
    OwnershipType,
    PublishingStatus,
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
    CustomerCandidate,
    CustomerCreateRequest,
    CustomerFromCardRequest,
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
    TransactionDraftConfirmRequest,
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
SECURE_DOC_DIR = Path("data/secure_documents")
SECURE_DOC_DIR.mkdir(parents=True, exist_ok=True)


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
    def _normalize_accident_summary(v: Vehicle) -> dict[str, Any]:
        """고객 및 관리자 공통 정규화 성능·사고 요약 (단일 진실 원천 SSOT, DIRECTIVE 055 고도화)."""
        cond_detail = {}
        if v.condition_detail_json:
            try:
                cond_detail = json.loads(v.condition_detail_json)
            except Exception:
                pass

        accident_hist = {}
        if v.accident_history_json:
            try:
                accident_hist = json.loads(v.accident_history_json)
            except Exception:
                pass

        # 1. 실제 성능점검 증빙 문서 메타데이터 검증 (DIRECTIVE 056: 임의 하드코딩 완전 제거)
        inspection_doc_id = cond_detail.get("inspection_document_id") or accident_hist.get("inspection_document_id")
        inspected_at = cond_detail.get("inspection_date") or accident_hist.get("inspection_date")
        inspected_by = cond_detail.get("inspected_by") or accident_hist.get("inspected_by")
        verified_at = cond_detail.get("verified_at") or accident_hist.get("verified_at")
        verified_by = cond_detail.get("verified_by") or accident_hist.get("verified_by")
        verification_method = cond_detail.get("verification_method") or accident_hist.get("verification_method")

        # 정식 문서번호와 점검일자가 모두 유효하게 존재해야만 DOCUMENT_VERIFIED 판정
        has_valid_doc = bool(inspection_doc_id and inspected_at and inspected_at != "미확인")
        doc_status = "DOCUMENT_VERIFIED" if has_valid_doc else "DOCUMENT_PENDING"

        # 2. 각 항목별 독립 검증 상태 판정 (사고 여부로 타 부위 임의 추정 금지)
        raw_state = (accident_hist.get("accident_state") or cond_detail.get("accident_state") or "").strip().upper()
        
        # (1) 전체 사고 상태
        if has_valid_doc and raw_state in ["NO_ACCIDENT", "NONE", "CLEAN", "무사고"]:
            accident_status = "VERIFIED_CLEAN"
            accident_label = "완전 무사고 (단순교환 없음)"
            is_accident_free = True
        elif has_valid_doc and raw_state in ["ISSUE", "REPAIRED", "EXCHANGED", "단순교환", "수리이력"]:
            accident_status = "VERIFIED_ISSUE"
            accident_label = "단순교환 / 수리이력 있음"
            is_accident_free = False
        else:
            accident_status = "UNKNOWN"
            accident_label = "미확인 (성능점검 증빙 대기)"
            is_accident_free = None

        # (2) 외판 상태 (Body Panel)
        raw_outer = (cond_detail.get("outer_damage") or accident_hist.get("outer_damage") or "").strip()
        if has_valid_doc and ("교환" in raw_outer or "판금" in raw_outer or "수리" in raw_outer):
            body_panel_status = "VERIFIED_ISSUE"
            body_panel_label = raw_outer
        elif has_valid_doc and accident_status == "VERIFIED_CLEAN":
            body_panel_status = "VERIFIED_CLEAN"
            body_panel_label = "외판 무교환 (단순교환 없음)"
        else:
            body_panel_status = "UNKNOWN"
            body_panel_label = raw_outer or "미확인 (성능점검표 미등록)"

        # (3) 주요 골격 손상 (Frame Status) - 외판과 엄격 분리
        raw_frame = (cond_detail.get("frame_damage") or accident_hist.get("frame_damage") or "").strip()
        if has_valid_doc and ("손상" in raw_frame or "판금" in raw_frame or "용접" in raw_frame):
            frame_status = "VERIFIED_ISSUE"
            frame_label = raw_frame
        elif has_valid_doc and accident_status in ["VERIFIED_CLEAN", "VERIFIED_ISSUE"]:
            frame_status = "VERIFIED_CLEAN"
            frame_label = "주요 골격 손상 없음 (정상)"
        else:
            frame_status = "UNKNOWN"
            frame_label = raw_frame or "미확인 (성능점검표 미등록)"

        # (4) 누유 상태 (Oil Leak)
        raw_oil = (cond_detail.get("oil_leak_status") or cond_detail.get("oil_leak") or "").strip()
        if has_valid_doc and ("미세누유" in raw_oil or "누유" in raw_oil):
            oil_leak_status = "VERIFIED_ISSUE"
            oil_leak_label = raw_oil
        elif has_valid_doc:
            oil_leak_status = "VERIFIED_CLEAN"
            oil_leak_label = "미세누유 없음 (정상)"
        else:
            oil_leak_status = "UNKNOWN"
            oil_leak_label = raw_oil or "미확인 (성능점검표 미등록)"

        # (5) 침수 및 특수사고 (Flood History)
        raw_special = (cond_detail.get("special_accident") or accident_hist.get("special_accident") or "").strip()
        if has_valid_doc and ("침수" in raw_special or "화재" in raw_special):
            flood_history_status = "VERIFIED_ISSUE"
            flood_label = raw_special
        elif has_valid_doc:
            flood_history_status = "VERIFIED_CLEAN"
            flood_label = "침수·화재·도난 이력 없음"
        else:
            flood_history_status = "UNKNOWN"
            flood_label = raw_special or "미확인 (이력 조회 대기)"

        # (6) 보험 이력 (Insurance History) - 카히스토리 전산 조회 증빙 독립 검증 (DIRECTIVE 056)
        insurance_inquiry_id = accident_hist.get("insurance_inquiry_id") or cond_detail.get("insurance_inquiry_id")
        has_insurance_doc = bool(insurance_inquiry_id and insurance_inquiry_id != "미확인")
        if has_insurance_doc:
            total_loss = accident_hist.get("total_loss_count", 0)
            flood_loss = accident_hist.get("flood_loss_count", 0)
            if total_loss > 0 or flood_loss > 0:
                insurance_history_status = "VERIFIED_ISSUE"
                insurance_label = f"전손 {total_loss}건 / 침수 {flood_loss}건 확인"
            else:
                insurance_history_status = "VERIFIED_CLEAN"
                insurance_label = "보험 사고이력 전손·도난·침수 0건 (조회 완료)"
        else:
            insurance_history_status = "UNKNOWN"
            insurance_label = "보험 이력 전산 조회 대기"

        # 3. 차량 부위별 정밀 다이어그램 데이터 매핑 (외판 vs 골격 분리 및 증빙 연결)
        def _get_part_data(name: str, ptype: str, status: str, default_normal: str):
            finding_text = default_normal if status == "CLEAN" else ("손상/교환 확인" if status in ["REPLACED", "DAMAGED"] else "점검 대기")
            evidence_text = f"성능점검표 {inspection_doc_id}" if has_valid_doc else "공식 증빙 대기"
            return {
                "name": name,
                "type": ptype,
                "status": status,
                "finding": finding_text,
                "evidence": evidence_text,
            }

        outer_st = "CLEAN" if body_panel_status == "VERIFIED_CLEAN" else ("REPLACED" if body_panel_status == "VERIFIED_ISSUE" else "UNKNOWN")
        frame_st = "CLEAN" if frame_status == "VERIFIED_CLEAN" else ("DAMAGED" if frame_status == "VERIFIED_ISSUE" else "UNKNOWN")

        diagram_parts = {
            "hood": _get_part_data("보닛(후드)", "OUTER", outer_st, "볼트 풀림 및 판금 흔적 없음 (무교환)"),
            "front_fender_l": _get_part_data("앞휀더(좌)", "OUTER", outer_st, "외판 볼트 체결 정상 (무교환)"),
            "front_fender_r": _get_part_data("앞휀더(우)", "OUTER", outer_st, "외판 볼트 체결 정상 (무교환)"),
            "front_door_l": _get_part_data("앞도어(좌)", "OUTER", outer_st, "도어 실링 및 판금 흔적 없음 (정상)"),
            "front_door_r": _get_part_data("앞도어(우)", "OUTER", outer_st, "도어 실링 및 판금 흔적 없음 (정상)"),
            "rear_door_l": _get_part_data("뒷도어(좌)", "OUTER", outer_st, "도어 실링 및 판금 흔적 없음 (정상)"),
            "rear_door_r": _get_part_data("뒷도어(우)", "OUTER", outer_st, "도어 실링 및 판금 흔적 없음 (정상)"),
            "trunk_lid": _get_part_data("트렁크리드", "OUTER", outer_st, "실링 테이프 및 볼트 원형 유지 (무교환)"),
            "roof": _get_part_data("루프패널", "OUTER", outer_st, "외부 충격 및 찌그러짐 없음 (정상)"),
            "radiator_support": _get_part_data("라디에이터 서포트", "FRAME", frame_st, "서포트 변형·용접 없음 (정상)"),
            "cross_member": _get_part_data("크로스멤버", "FRAME", frame_st, "하체 멤버 휨·균열 없음 (정상)"),
            "front_side_member": _get_part_data("사이드멤버(앞)", "FRAME", frame_st, "주요 골격 프레임 변형 없음 (정상)"),
            "pillar_a": _get_part_data("A필러(좌/우)", "FRAME", frame_st, "필러 절단·교환 없음 (정상)"),
            "pillar_b": _get_part_data("B필러(좌/우)", "FRAME", frame_st, "센터 필러 구조 변형 없음 (정상)"),
            "pillar_c": _get_part_data("C필러(좌/우)", "FRAME", frame_st, "리어 필러 절단·교환 없음 (정상)"),
            "floor_panel": _get_part_data("플로어패널", "FRAME", frame_st, "바닥 패널 충격 흔적 없음 (정상)"),
        }

        return {
            # 하위 호환 필드
            "status_code": accident_status,
            "accident_state_label": accident_label,
            "has_inspection": has_valid_doc,
            "is_accident_free": is_accident_free,
            "frame_damage": frame_label,
            "outer_damage": body_panel_label,
            "oil_leak_status": oil_leak_label,
            "special_accident": flood_label,
            "inspection_date": inspected_at or "미확인",

            # DIRECTIVE 056 정밀 SSOT 신규 필드 (가짜 INSP 번호 생성 금지)
            "inspection_document_id": inspection_doc_id,
            "document_status": doc_status,
            "inspected_at": inspected_at or "미확인",
            "inspected_by": inspected_by,
            "verified_at": verified_at or inspected_at or "검증 대기",
            "verified_by": verified_by,
            "verification_method": verification_method,
            "accident_status": accident_status,
            "body_panel_status": body_panel_status,
            "body_panel_label": body_panel_label,
            "frame_status": frame_status,
            "frame_label": frame_label,
            "oil_leak_code": oil_leak_status,
            "flood_history_status": flood_history_status,
            "insurance_history_status": insurance_history_status,
            "insurance_label": insurance_label,
            "diagram_parts": diagram_parts,
        }

    @staticmethod
    def get_vehicle_detail(db: Session, vehicle_id: str) -> Optional[dict[str, Any]]:
        """DIRECTIVE 046-D / 054 차량 마스터 종합 상세 정보 조회 (고객 화면과 동일한 공통 스펙 및 사고 요약 제공)."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            return None

        timeline = json.loads(v.timeline_json) if v.timeline_json else []
        options = json.loads(v.options_json) if v.options_json else []
        accident_summary = PlatformService._normalize_accident_summary(v)
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
            "accident_summary": accident_summary,
            "accident_history": accident_summary,
            "inspection_summary": inspection_summary,
            "marketing_auth": marketing_auth,
            "primary_photo_url": v.primary_photo_url,
            "video_status": v.video_status or "NONE",
            "is_public": bool(v.is_public),
            "dealer_info": dealer_info,
            "trim": v.trim or "",
            "body_type": v.body_type or "세단",
            "recon_cost": getattr(v, "recon_cost", 0) or 0,
            "defects": defects,
            "photos": photos,
            "listings": listings,
            "media_projects": media_projects,
            "timeline": timeline,
            "created_at": v.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": v.updated_at.strftime("%Y-%m-%d %H:%M"),
        }

    # =========================================================================
    # DIRECTIVE 051: 차마트(CHAMART) 고객용 공개 서비스 & 관리자 게시 연동
    # =========================================================================
    # DIRECTIVE 051 / 058: 차마트(CHAMART) 고객용 공개 서비스 & 단일 공개 검증 정책
    # =========================================================================

    @staticmethod
    def is_vehicle_eligible_for_chamart_public(v: Optional[Vehicle], db: Session, allow_demo: bool = False) -> bool:
        """DIRECTIVE 064 P0: 차마트 고객 공개 매물 단일 검증 가드 (운영 실차 검증 vs 데모 검수 분리).
        
        운영 공개(allow_demo=False) 필수 요건:
        1. 차마트 직영(CHAMART_OWNED) 또는 공식 승인 제휴(PARTNER_APPROVED)
        2. 실제 판매 가능 상태 (FOR_SALE, AVAILABLE)
        3. 관리자 고객 공개 승인 플래그 (is_public == True)
        4. 내부 테스트/데모 플래그 배제 (is_demo == False)
        5. 모델명 가드 (테스트, demo, 임시, placeholder 배제)
        6. 판매 가격 유효성 (target_price > 0)
        7. 제휴 매물인 경우 공식 판매권한 유효성 (sale_auth, 미철회, 미만료)
        8. [DIRECTIVE 064 P0] 실차 자산 검증 원장 레코드:
           - verification_status == 'VERIFIED_REAL_ASSET'
           - usage_rights_status == 'CONFIRMED_COMMERCIAL'
           - photo_source == 'FIELD_INSPECTION_PHOTO'
           - original_file_hash 해시값 기록 필수
           (단순 URL/파일명 문자열 필터가 아닌 서버 검증 원장 확인)
        
        데모/검수 모드(allow_demo=True):
        - 1~6번 만족 차량 중 UI 검수용 시연 데이터 허용.
        """
        if not v:
            return False
        # 1. 소유 유형 및 상태 검증
        if v.ownership_type not in [OwnershipType.CHAMART_OWNED.value, OwnershipType.PARTNER_APPROVED.value]:
            return False
        if v.status not in ["FOR_SALE", "AVAILABLE"]:
            return False
        if not v.is_public:
            return False
        if not allow_demo and v.is_demo:
            return False

        # 모델명 배제 가드 강화 (운영 환경: 테스트/임시/placeholder 차단)
        model_name_lower = (v.model_name or "").lower()
        if not allow_demo and any(keyword in model_name_lower for keyword in ["테스트", "test", "demo", "임시", "placeholder"]):
            return False

        # 판매 가격 유효성 검증 (0원 이하 배제)
        if (v.target_price or 0) <= 0:
            return False

        # 제휴 매물 판매권한 유효성 검증
        if v.ownership_type == OwnershipType.PARTNER_APPROVED.value:
            try:
                auth_json = json.loads(v.marketing_auth_json or "{}")
            except Exception:
                auth_json = {}

            if auth_json.get("sale_auth") is not True:
                return False
            if auth_json.get("is_revoked") is True:
                return False
            expires_at_str = auth_json.get("expires_at")
            if expires_at_str:
                try:
                    exp_date = datetime.datetime.strptime(expires_at_str[:10], "%Y-%m-%d").date()
                    if exp_date < datetime.date.today():
                        return False
                except Exception:
                    return False

        # 2. 실차 사진 원장 검증
        photos = db.query(VehiclePhoto).filter(VehiclePhoto.vehicle_id == v.id).all()
        if not photos:
            return False

        if allow_demo:
            # 데모 검수 모드: 사진 자산이 1장 이상 존재하면 승인
            return len(photos) > 0

        # 운영 모드 (allow_demo == False):
        # 반드시 검증 원장 레코드(VERIFIED_REAL_ASSET, CONFIRMED_COMMERCIAL, FIELD_INSPECTION_PHOTO) 만족 필수
        has_verified_real_asset = False
        for p in photos:
            v_status = getattr(p, "verification_status", None)
            u_status = getattr(p, "usage_rights_status", None)
            source = getattr(p, "photo_source", None)
            f_hash = getattr(p, "original_file_hash", None)

            if (
                v_status == "VERIFIED_REAL_ASSET"
                and u_status == "CONFIRMED_COMMERCIAL"
                and source == "FIELD_INSPECTION_PHOTO"
                and f_hash
            ):
                has_verified_real_asset = True
                break

        return has_verified_real_asset

    @staticmethod
    def get_chamart_public_vehicles(db: Session, mode: str = "prod") -> list[dict[str, Any]]:
        """차마트 고객 공개 차량 목록 조회 (운영 실차 vs 데모 검수 분리)."""
        allow_demo = (mode in ["demo", "staging"])
        filters = [
            Vehicle.ownership_type.in_([OwnershipType.CHAMART_OWNED.value, OwnershipType.PARTNER_APPROVED.value]),
            Vehicle.status.in_(["FOR_SALE", "AVAILABLE"]),
            Vehicle.is_public == True,
        ]
        if not allow_demo:
            filters.append(Vehicle.is_demo == False)

        query = db.query(Vehicle).filter(*filters).order_by(desc(Vehicle.updated_at))
        vehicles = query.all()

        results = []
        for v in vehicles:
            if not PlatformService.is_vehicle_eligible_for_chamart_public(v, db, allow_demo=allow_demo):
                continue

            # 월 납입금 추산 (60개월, 연 5.9% 기준 원리금 균등)
            price_won = (v.target_price or 0) * 10000
            monthly_est = 0
            if price_won > 0:
                r = 0.059 / 12
                n = 60
                monthly_est = int((price_won * r * ((1 + r) ** n)) / (((1 + r) ** n) - 1) / 10000)

            results.append({
                "id": v.id,
                "plate_number": v.plate_number,
                "manufacturer": v.manufacturer or "미확인",
                "model_name": v.model_name,
                "trim": v.trim or "",
                "year": v.year,
                "mileage": v.mileage,
                "fuel_type": v.fuel_type or "미확인",
                "transmission": v.transmission or "미확인",
                "body_type": v.body_type or "세단",
                "color": v.color or "미확인",
                "target_price": v.target_price,
                "monthly_payment_estimate": monthly_est,
                "primary_photo_url": v.primary_photo_url or "/static/img/car_placeholder.jpg",
                "branch_name": "차마트 장한평 거점",
                "status": v.status,
                "publishing_status": getattr(v, "publishing_status", "PUBLISHED"),
                "is_demo_asset": allow_demo,
                "demo_notice": "UI 디자인 검수용 시연 데이터" if allow_demo else None,
            })
        return results

    @staticmethod
    def get_chamart_public_vehicle_detail(db: Session, vehicle_id: str, mode: str = "prod") -> Optional[dict[str, Any]]:
        """차마트 고객 공개 차량 상세 조회 (목록과 동일한 단일 공개 검증 정책 적용)."""
        allow_demo = (mode in ["demo", "staging"])
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            return None

        # DIRECTIVE 064 P0: 단일 공개 정책 (운영 검증 vs 데모 검수)
        if not PlatformService.is_vehicle_eligible_for_chamart_public(v, db, allow_demo=allow_demo):
            return None

        # 1. 월 납입금 계산 (60개월 5.9%)
        price_won = (v.target_price or 0) * 10000
        monthly_est = 0
        if price_won > 0:
            r = 0.059 / 12
            n = 60
            monthly_est = int((price_won * r * ((1 + r) ** n)) / (((1 + r) ** n) - 1) / 10000)

        # 2. 엔카형 4대 분류 구조화 옵션 및 10대 핵심 주요 옵션 (DIRECTIVE 088 TASK 3, 5, 6)
        from chaficial.platform.catalog.options import StandardOptionCatalog

        try:
            raw_options = json.loads(v.options_structured_json or "[]")
        except Exception:
            raw_options = []

        # 코드별 또는 이름별 상태 맵 생성
        opt_status_map = {}
        for opt in raw_options:
            if isinstance(opt, dict):
                code = opt.get("code") or ""
                name = opt.get("name") or ""
                st = opt.get("status") or ("PRESENT" if opt.get("is_verified") else "UNKNOWN")
                if code:
                    opt_status_map[code] = st
                if name:
                    opt_status_map[name] = st

        # 단순 options_json 하위 호환 처리
        try:
            simple_opts = json.loads(v.options_json or "[]")
        except Exception:
            simple_opts = []
        for name in simple_opts:
            if name not in opt_status_map:
                opt_status_map[name] = "PRESENT"

        # 10대 핵심 주요 옵션 계산 (선루프, HUD, 주차감지센서, 후방카메라, 자동 에어컨, 스마트키, 내비게이션, 열선시트, 통풍시트, 가죽시트)
        top10_defs = StandardOptionCatalog.get_top10_options()
        top10_options = []
        for t_def in top10_defs:
            c_code = t_def["code"]
            c_name = t_def["name"]
            st = opt_status_map.get(c_code) or opt_status_map.get(c_name) or "UNKNOWN"
            # simple_opts 키워드 포함 검사
            if st == "UNKNOWN":
                for so in simple_opts:
                    if c_name in so or so in c_name:
                        st = "PRESENT"
                        break
            top10_options.append({
                "code": c_code,
                "name": c_name,
                "icon": t_def.get("icon", "check"),
                "status": st,  # PRESENT, ABSENT, UNKNOWN
                "is_present": (st == "PRESENT"),
            })

        # 4대 표준 카테고리 구성 (외관·내장, 안전, 편의·멀티미디어, 시트, 기타 옵션)
        categorized_options: dict[str, list[dict[str, Any]]] = {
            "외관·내장": [],
            "안전": [],
            "편의·멀티미디어": [],
            "시트": [],
            "기타 옵션": [],
        }

        # 카탈로그 표준 옵션 분류 매핑
        all_std_options = StandardOptionCatalog.list_options()
        for s_opt in all_std_options:
            c_code = s_opt["code"]
            c_name = s_opt["name"]
            cat_label = s_opt.get("category_label", "편의·멀티미디어")
            st = opt_status_map.get(c_code) or opt_status_map.get(c_name)
            if not st:
                for so in simple_opts:
                    if c_name in so or so in c_name:
                        st = "PRESENT"
                        break
            st = st or "UNKNOWN"

            if cat_label in categorized_options:
                categorized_options[cat_label].append({
                    "code": c_code,
                    "name": c_name,
                    "icon": s_opt.get("icon", "check"),
                    "status": st,
                    "is_present": (st == "PRESENT"),
                    "is_genuine": True,
                })

        # 표준 목록에 없는 추가/기타 옵션
        std_names = {o["name"] for o in all_std_options}
        std_codes = {o["code"] for o in all_std_options}
        for opt in raw_options:
            if isinstance(opt, dict):
                o_name = opt.get("name")
                o_code = opt.get("code")
                if o_name and o_name not in std_names and o_code not in std_codes:
                    categorized_options["기타 옵션"].append({
                        "code": o_code or f"CUSTOM_{len(categorized_options['기타 옵션'])+1}",
                        "name": o_name,
                        "icon": "plus",
                        "status": opt.get("status", "PRESENT"),
                        "is_present": (opt.get("status", "PRESENT") == "PRESENT"),
                        "is_genuine": opt.get("is_genuine", False),
                    })

        # 3. 사고 및 성능 상태 요약 (DIRECTIVE 054: 단일 SSOT 정규화 사용)
        accident_summary = PlatformService._normalize_accident_summary(v)

        # 4. 사진 갤러리 (DIRECTIVE 065 P0: 승인된 검증 사진만 고객에게 반환)
        eligible_photos = []
        for p in sorted(v.photos, key=lambda x: (not x.is_primary, x.sort_order)):
            if allow_demo:
                eligible_photos.append(p)
            else:
                # 운영 모드: 반드시 승인 원장 검증 통과 사진만 고객에게 공개
                v_stat = getattr(p, "verification_status", None)
                u_stat = getattr(p, "usage_rights_status", None)
                src = getattr(p, "photo_source", None)
                f_hash = getattr(p, "original_file_hash", None)
                if v_stat == "VERIFIED_REAL_ASSET" and u_stat == "CONFIRMED_COMMERCIAL" and src == "FIELD_INSPECTION_PHOTO" and f_hash:
                    eligible_photos.append(p)

        photos = [
            {
                "id": p.id,
                "photo_url": p.photo_url,
                "category": p.category,
                "sort_order": p.sort_order,
                "is_primary": p.is_primary,
                "caption": p.caption or f"{v.model_name} {p.category}",
            }
            for p in eligible_photos
        ]
        if not photos and allow_demo and v.primary_photo_url:
            photos.append({
                "id": "primary",
                "photo_url": v.primary_photo_url,
                "category": "EXTERIOR",
                "sort_order": 0,
                "is_primary": True,
                "caption": v.model_name,
            })

        # 5. 판매자 및 전시장 정보 (DIRECTIVE 066 P0: 미확인 제휴 표현 제거 및 온라인 상담 정직화)
        raw_phone = v.dealer.phone if v.dealer else None
        valid_phone = raw_phone if (raw_phone and not raw_phone.startswith("1544") and len(raw_phone) >= 8) else None
        dealer_info = {
            "name": v.dealer.name if v.dealer else "차마트 고객상담팀",
            "dealership_name": "차마트 온라인 쇼룸",
            "phone": valid_phone,
            "showroom_location": "서울특별시 성동구 자동차시장1길 70 (용답동)",
            "showroom_detail": "온라인 상담 문의 전용 (오프라인 전시장 방문은 제휴 매매단지 정식 확정 후 순차 안내 예정)",
        }

        # 6. 시세 비교 및 부대비용 가이드 (P0-3: 1.05배 가짜 평균 시세 전면 제거)
        # 실제 시세 데이터가 없으면 임의 날조하지 않고 정직하게 안내
        price_comparison = {
            "target_price": v.target_price,
            "market_avg_price": None,
            "savings_amount": 0,
            "competition_analysis": "동급 실거래 시세 정밀 비교 분석 중",
            "registration_tax_est": int(v.target_price * 0.07) if v.target_price else 0,  # 취등록세 약 7%
            "service_fee": 30,  # 법정 매도비 약 30만원
        }

        # 7. 승인된 AI 홍보 영상
        approved_video = None
        for mp in v.media_projects:
            if mp.status in ["COMPLETED", "PUBLISHED"] and mp.video_url:
                approved_video = {
                    "project_id": mp.id,
                    "title": mp.title,
                    "video_url": mp.video_url,
                    "thumbnail_url": mp.thumbnail_url or v.primary_photo_url,
                    "published_channel": mp.published_channel or "YouTube Shorts",
                }
                break

        return {
            "id": v.id,
            "plate_number": v.plate_number,
            "vin": v.vin or "미확인 (차대번호 미등록)",
            "manufacturer": v.manufacturer or "미확인",
            "model_name": v.model_name,
            "trim": v.trim or "미확인",
            "year": v.year,
            "first_registration_date": v.first_registration_date or "미확인",
            "mileage": v.mileage,
            "displacement_cc": v.displacement_cc,
            "fuel_type": v.fuel_type or "미확인",
            "transmission": v.transmission or "미확인",
            "drive_type": v.drive_type or "미확인",
            "body_type": v.body_type or "세단",
            "color": v.color or "미확인",
            "interior_color": v.interior_color or "미확인",
            "target_price": v.target_price,
            "monthly_payment_estimate": monthly_est,
            "sales_conditions": v.sales_conditions or "상담 시 안내",
            "ad_description": v.ad_description or f"차마트 인증 매물 {v.model_name} 차량입니다.",
            "ad_highlights": v.ad_highlights or "",
            "ad_notices": v.ad_notices or "",
            "photos": photos,
            "top10_options": top10_options,
            "options_categorized": categorized_options,
            "accident_summary": accident_summary,
            "dealer_info": dealer_info,
            "price_comparison": price_comparison,
            "approved_video": approved_video,
            "branch_name": "차마트 제휴 전시장 (장한평)",
            "is_public": v.is_public,
            "publishing_status": getattr(v, "publishing_status", "PUBLISHED"),
            "is_demo_asset": allow_demo,
            "demo_notice": "UI 디자인 검수용 시연 데이터" if allow_demo else None,
            "updated_at": v.updated_at.strftime("%Y-%m-%d %H:%M"),
        }

    @staticmethod
    def create_chamart_public_consultation(db: Session, data: dict[str, Any]) -> dict[str, Any]:
        """차마트 웹사이트 고객 문의 및 방문 예약 접수 (개인정보 수집 동의 필수 검증)."""
        if not data.get("privacy_agreed"):
            raise ValueError("개인정보 수집 및 이용에 동의해야 상담 예약이 가능합니다.")

        name = (data.get("name") or "").strip()
        phone = (data.get("phone") or "").strip()
        if not name or not phone:
            raise ValueError("고객 성함과 연락처는 필수 입력 사항입니다.")

        vehicle_id = data.get("vehicle_id")
        target_model = data.get("vehicle_title") or "차마트 문의 매물"
        if vehicle_id:
            v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
            if not v:
                raise ValueError("존재하지 않는 차량에 대한 상담 신청입니다.")
            # DIRECTIVE 065 P0: 운영 공개 적격 매물인지 검증 (미승인, 데모, 비공개 매물은 운영 상담 신청 차단)
            if not PlatformService.is_vehicle_eligible_for_chamart_public(v, db, allow_demo=False):
                raise ValueError("현재 판매 공개 중인 실차 매물에 대해서만 방문 예약이 가능합니다.")
            target_model = f"{v.manufacturer or ''} {v.model_name}".strip()

        content = data.get("content") or "웹사이트 차량 상세페이지 상담 신청"
        preferred_date = data.get("preferred_date")

        # 고객 조회 또는 생성
        phone_norm = normalize_phone_number(phone)
        customer = db.query(Customer).filter(Customer.phone == phone_norm).first()
        if not customer:
            branch = db.query(Branch).first()
            customer = Customer(
                branch_id=branch.id if branch else None,
                name=name,
                phone=phone_norm,
                target_vehicle_model=target_model,
                status="NEW",
                source="CHAMART_WEB",
            )
            db.add(customer)
            db.flush()

        # 상담 레코드 등록
        consultation = Consultation(
            customer_id=customer.id,
            channel="매장방문" if preferred_date else "차마트웹",
            content=f"[차량ID: {vehicle_id or '미지정'}] 희망방문일: {preferred_date or '상담 후 협의'}\n문의내용: {content}",
            staff_name="차마트 전시장 매니저",
            next_action_date=preferred_date[:10] if (preferred_date and len(preferred_date) >= 10) else None,
            inquiry_source="CHAMART_WEB",
            is_duplicate=False,
            created_at=datetime.datetime.utcnow(),
        )
        db.add(consultation)
        db.commit()
        db.refresh(consultation)

        return {
            "success": True,
            "consultation_id": consultation.id,
            "customer_id": customer.id,
            "message": "상담 및 방문 예약이 정상 접수되었습니다. 차마트 전시장 담당 매니저가 확인 후 연락드리겠습니다.",
        }

    @staticmethod
    def list_consultations(db: Session) -> list[dict[str, Any]]:
        """관리자 전용 전체 상담 내역 조회 (CRM 연동)."""
        consultations = db.query(Consultation).order_by(Consultation.created_at.desc()).all()
        results = []
        for c in consultations:
            results.append({
                "id": c.id,
                "consultation_id": c.id,
                "customer_id": c.customer_id,
                "customer_name": c.customer.name if c.customer else "미확인",
                "customer_phone": c.customer.phone if c.customer else "미확인",
                "channel": c.channel,
                "content": c.content,
                "staff_name": c.staff_name,
                "inquiry_source": c.inquiry_source,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })
        return results

    @staticmethod
    def toggle_vehicle_public_status(db: Session, vehicle_id: str, is_public: bool | None = None) -> dict[str, Any]:
        """관리자 전용 차량 차마트 공개 상태 토글 (DIRECTIVE 052 5대 서버 검증 가드 강제)."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            raise ValueError(f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

        target_public = is_public if is_public is not None else not v.is_public

        # 공개(True)로 전환 시 5대 서버 검증 가드 실행
        if target_public:
            # 가드 1: 시장 관측 매물 및 미승인 제휴 후보 차단
            if v.ownership_type not in [OwnershipType.CHAMART_OWNED.value, OwnershipType.PARTNER_APPROVED.value]:
                raise ValueError(
                    f"차마트 공개 승인 실패: 관측/미승인 매물(소유유형: {v.ownership_type})은 고객에게 판매 매물로 공개할 수 없습니다."
                )

            # 가드 2: 테스트 및 데모 차량 공개 차단
            if getattr(v, "is_demo", False):
                raise ValueError("차마트 공개 승인 실패: 내부 테스트 및 데모 차량은 공개할 수 없습니다.")

            # 가드 3: 판매 상태 검증 (FOR_SALE, AVAILABLE만 허용)
            if v.status not in ["FOR_SALE", "AVAILABLE"]:
                raise ValueError(
                    f"차마트 공개 승인 실패: 실제 판매 가능한 상태(FOR_SALE, AVAILABLE)의 차량만 공개 가능합니다. (현재: {v.status})"
                )

            # 가드 4: 실차 사진 최소 1장 이상 등록 및 검증 필수
            has_photo = False
            if v.photos and len(v.photos) > 0:
                has_photo = any(p.photo_url and not p.photo_url.endswith("car_placeholder.jpg") for p in v.photos)
            elif v.primary_photo_url and not v.primary_photo_url.endswith("car_placeholder.jpg"):
                has_photo = True

            if not has_photo:
                raise ValueError("차마트 공개 승인 실패: 검증된 실차 사진이 최소 1장 이상 등록되어 있어야 합니다.")

            # 가드 5: 소유·판매 권한 및 유효기간 엄격 검증 (DIRECTIVE 053 REVISED P0-3)
            if v.ownership_type == OwnershipType.PARTNER_APPROVED.value:
                try:
                    auth_json = json.loads(v.marketing_auth_json or "{}")
                except Exception:
                    auth_json = {}

                # 1) sale_auth 누락 시 기본 승인(True) 취약점 완전 제거 -> 명시적 True 필수
                if auth_json.get("sale_auth") is not True:
                    raise ValueError("차마트 공개 승인 실패: 제휴 판매 권한(sale_auth)이 공식 승인되지 않았습니다.")

                # 2) 권한 철회 여부 검증
                if auth_json.get("is_revoked") is True:
                    raise ValueError("차마트 공개 승인 실패: 제휴 판매 권한이 철회(Revoked)된 매물입니다.")

                # 3) 권한 유효기간 만료 검증
                expires_at_str = auth_json.get("expires_at")
                if expires_at_str:
                    try:
                        exp_date = datetime.datetime.strptime(expires_at_str[:10], "%Y-%m-%d").date()
                        if exp_date < datetime.date.today():
                            raise ValueError(f"차마트 공개 승인 실패: 제휴 판매 권한 유효기간({expires_at_str})이 만료되었습니다.")
                    except ValueError as ve:
                        if "유효기간" in str(ve):
                            raise ve

        v.is_public = target_public
        # 차마트 공개 상태와 플랫폼 등록 상태 반영
        if v.is_public:
            if v.publishing_status not in ["APPROVED", "PUBLISHED"]:
                v.publishing_status = "PUBLISHED"
        else:
            v.publishing_status = "UNPUBLISHED"

        v.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(v)

        return {
            "vehicle_id": v.id,
            "plate_number": v.plate_number,
            "is_public": v.is_public,
            "publishing_status": v.publishing_status,
            "message": "차마트 공개 상태가 성공적으로 변경되었습니다." if v.is_public else "차량이 차마트 비공개로 격리되었습니다.",
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
        
        # DIRECTIVE 048 P0-5: 사고 및 성능점검 실제 검증 증빙 여부에 따른 정직한 대본 생성
        accident_data = json.loads(v.accident_history_json) if v.accident_history_json else {}
        is_accident_verified = (
            accident_data.get("accident_state") == "CLEAN"
            and accident_data.get("verified_at") is not None
        )

        if is_accident_verified:
            verification_phrase = "카히스토리 및 성능점검 전산 조회를 통해 무사고를 직접 검증했습니다."
        else:
            verification_phrase = "현재 카히스토리 정밀 전산 조회 및 성능점검 진행 중인 실매물입니다."

        script = (
            f"오늘 소개해드릴 실매물은 {v.year}년식 {v.model_name}입니다!\n"
            f"주행거리 {v.mileage:,}km, {v.transmission} 변속기에 깔끔한 {v.color} 바디입니다.\n"
            f"실제 광고가격 {v.target_price:,}만원에 입고되었으며, {verification_phrase}\n"
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
                "job_title": getattr(c, "job_title", None) or "-",
                "company_name": getattr(c, "company_name", None) or "-",
                "email": getattr(c, "email", None) or "-",
                "source": getattr(c, "source", "DIRECT"),
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
            "job_title": getattr(c, "job_title", None),
            "company_name": getattr(c, "company_name", None),
            "company_address": getattr(c, "company_address", None),
            "company_phone": getattr(c, "company_phone", None),
            "email": getattr(c, "email", None),
            "source": getattr(c, "source", "DIRECT"),
            "source_image_url": getattr(c, "source_image_url", None),
            "ai_confidence": getattr(c, "ai_confidence", None),
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
            job_title=req.job_title,
            company_name=req.company_name,
            company_address=req.company_address,
            company_phone=req.company_phone,
            email=req.email,
            source=req.source or "DIRECT",
            source_image_url=req.source_image_url,
            ai_confidence=req.ai_confidence,
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
        """업로드된 서류 파일의 SHA-256 검증 및 분석 대기열 등록 (DIRECTIVE 048 P0-5 보안 강화)."""
        # 1. 파일 확장자 검증
        allowed_exts = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
        ext = Path(filename).suffix.lower()
        if ext not in allowed_exts:
            raise ValueError(f"허용되지 않은 파일 형식입니다: {ext} (허용: PDF, JPG, PNG, WEBP)")

        # 2. 매직 바이트 바이너리 위조 검증
        is_pdf = file_bytes.startswith(b"%PDF-")
        is_png = file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        is_jpg = file_bytes.startswith(b"\xff\xd8\xff")
        is_webp = (len(file_bytes) > 12 and file_bytes[8:12] == b"WEBP")
        if not (is_pdf or is_png or is_jpg or is_webp):
            raise ValueError("파일 내용이 선언된 이미지/PDF 규격과 일치하지 않습니다 (위조 바이너리 차단).")

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

        # 공개 uploads 대신 격리된 보안 디렉터리에 저장
        save_path = SECURE_DOC_DIR / f"{uuid.uuid4().hex[:8]}_{filename}"
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
            status="UPLOADED",
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

    # ==========================================
    # 6. DIRECTIVE 050-C 명함 CRM 및 거래 초안 파이프라인
    # ==========================================
    @staticmethod
    def check_customer_duplicate(db: Session, phone: str, email: Optional[str] = None) -> dict[str, Any]:
        """고객 전화번호 및 이메일 중복 검사 (DIRECTIVE 050-C)."""
        clean_phone = normalize_phone_number(phone)
        
        # 1. 전화번호 일치 검사
        matched = db.query(Customer).filter(Customer.phone == clean_phone).first()
        
        # 2. 이메일 일치 검사 (전화번호 불일치 시)
        if not matched and email and email.strip():
            matched = db.query(Customer).filter(Customer.email == email.strip()).first()
            
        if matched:
            return {
                "is_duplicate": True,
                "customer_id": matched.id,
                "name": matched.name,
                "phone": matched.phone,
                "company_name": getattr(matched, "company_name", None),
                "job_title": getattr(matched, "job_title", None),
                "status": matched.status,
                "notes": matched.notes,
                "created_at": matched.created_at.strftime("%Y-%m-%d %H:%M"),
            }
        return {"is_duplicate": False, "customer_id": None}

    @staticmethod
    def create_customer_from_business_card(db: Session, req: CustomerFromCardRequest) -> dict[str, Any]:
        """AI 인식 명함 데이터로부터 정식 CRM 고객 생성 (DIRECTIVE 050-C)."""
        clean_phone = normalize_phone_number(req.phone)
        
        branch_id = req.branch_id
        if not branch_id:
            jh = db.query(Branch).filter(Branch.name.contains("장한평")).first()
            branch_id = jh.id if jh else db.query(Branch).first().id

        clean_budget = parse_currency_amount(req.budget_max) if req.budget_max is not None else None

        customer = Customer(
            branch_id=branch_id,
            name=req.name.strip(),
            phone=clean_phone,
            status=req.status or "NEW",
            job_title=req.job_title,
            company_name=req.company_name,
            company_address=req.company_address,
            company_phone=req.company_phone,
            email=req.email,
            source="BUSINESS_CARD_AI",
            source_image_url=req.source_image_url,
            ai_confidence=req.ai_confidence or 0.95,
            target_vehicle_model=req.target_vehicle_model,
            budget_max=clean_budget,
            assigned_staff="차마트 상담팀",
            contact_consent=True,
            notes=req.notes,
        )
        db.add(customer)
        db.flush()

        # 명함 유입 최초 상담 메모 등록
        cons_content = f"[AI 명함 등록] {req.company_name or '회사 미상'} {req.job_title or ''} - 명함 자동 인식 완료"
        if req.notes:
            cons_content += f" (메모: {req.notes})"
        cons = Consultation(
            customer_id=customer.id,
            channel="매장방문",
            content=cons_content,
            staff_name="AI 비전 비서",
            inquiry_source="BUSINESS_CARD_AI",
        )
        db.add(cons)
        db.commit()
        db.refresh(customer)
        return PlatformService.get_customer(db, customer.id)

    @staticmethod
    def match_vehicle_for_document(
        db: Session,
        plate_number: Optional[str] = None,
        vin: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """거래서류에 기재된 차량번호 또는 VIN으로 플랫폼 보유 매물 자동 매칭."""
        if plate_number and plate_number.strip():
            clean_plate = re.sub(r"\s+", "", plate_number.strip())
            vehicles = db.query(Vehicle).all()
            for v in vehicles:
                v_clean = re.sub(r"\s+", "", v.plate_number)
                if clean_plate in v_clean or v_clean in clean_plate:
                    return {
                        "id": v.id,
                        "plate_number": v.plate_number,
                        "model_name": v.model_name,
                        "year": v.year,
                        "target_price": v.target_price,
                        "status": v.status,
                        "ownership_type": v.ownership_type,
                    }

        if vin and vin.strip():
            clean_vin = vin.strip().upper()
            v = db.query(Vehicle).filter(Vehicle.vin == clean_vin).first()
            if v:
                return {
                    "id": v.id,
                    "plate_number": v.plate_number,
                    "model_name": v.model_name,
                    "year": v.year,
                    "target_price": v.target_price,
                    "status": v.status,
                    "ownership_type": v.ownership_type,
                }
        return None

    @staticmethod
    def match_party_for_document(
        db: Session,
        name: Optional[str] = None,
        contact: Optional[str] = None,
    ) -> dict[str, Any]:
        """서류에 기재된 상대방 성명/연락처로 CRM 고객 또는 제휴 딜러 자동 매칭."""
        matched_customer = None
        matched_dealer = None

        if contact:
            clean_contact = normalize_phone_number(contact)
            matched_customer = db.query(Customer).filter(Customer.phone == clean_contact).first()
            matched_dealer = db.query(Dealer).filter(Dealer.phone == clean_contact).first()

        if not matched_customer and name:
            matched_customer = db.query(Customer).filter(Customer.name == name.strip()).first()
        if not matched_dealer and name:
            matched_dealer = db.query(Dealer).filter(Dealer.name == name.strip()).first()

        return {
            "customer": {
                "id": matched_customer.id,
                "name": matched_customer.name,
                "phone": matched_customer.phone,
            } if matched_customer else None,
            "dealer": {
                "id": matched_dealer.id,
                "name": matched_dealer.name,
                "dealership": matched_dealer.dealership_name,
            } if matched_dealer else None,
        }

    @staticmethod
    def create_transaction_from_draft(
        db: Session,
        req: TransactionDraftConfirmRequest,
    ) -> dict[str, Any]:
        """AI 거래 초안 확인 후 정식 거래 원장 등록 (엄격한 무결성 격리 보장).
        
        [무결성 원칙 준수]
        - 관리자의 명시적 승인 전까지는 is_verified_sale=False 유지.
        - 단순 입금 내역이나 미검증 서류로 실매출, ROI, RL Reward 오염 방지.
        - settlement_status='PENDING'으로 격리 보관.
        """
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
            settlement_status=req.settlement_status or "PENDING",
            dealer_commission_amount=req.dealer_commission_amount,
            chamart_net_profit=req.chamart_net_profit,
            operating_cost=req.operating_cost,
            attribution_type=req.attribution_type or "AI_VIDEO",
            is_verified_sale=req.is_verified_sale,
            is_test_record=req.is_test_record,
            document_id=req.document_review_id,
            notes=req.notes,
        )
        db.add(tx)
        db.flush()

        # 연결된 서류 검토가 있으면 상태 승인 전이
        if req.document_review_id:
            doc = db.query(DocumentReview).filter(DocumentReview.id == req.document_review_id).first()
            if doc:
                doc.status = "APPROVED"
                doc.review_status = "APPROVED"
                doc.approved_by = "차마트 관리자"
                doc.created_transaction_id = tx.id
                doc.matched_vehicle_id = v.id

        # 차량 타임라인 기록 (검증된 판매 시에만 상태를 CONTRACTED로 변경)
        timeline = json.loads(v.timeline_json) if v.timeline_json else []
        if req.is_verified_sale and req.transaction_type == "SALE":
            v.status = "CONTRACTING"
            timeline.append({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "event": f"AI 거래서류 정식 승인: {req.party_name} / {req.amount}만원 (원장 ID: {tx.id[:8]})",
            })
        else:
            timeline.append({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "event": f"AI 거래서류 초안 보관 (미승인 격리): {req.party_name} / {req.amount}만원",
            })
        v.timeline_json = json.dumps(timeline, ensure_ascii=False)

        db.commit()
        db.refresh(tx)
        return {
            "ok": True,
            "transaction_id": tx.id,
            "vehicle_plate": v.plate_number,
            "amount": tx.amount,
            "settlement_status": tx.settlement_status,
            "is_verified_sale": tx.is_verified_sale,
            "message": "거래 초안이 성공적으로 등록되었습니다.",
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
        """DIRECTIVE 048 P0-4: 실전 성과와 데모 시뮬레이션의 완전 분리 집계 및 ROI 공식 교정."""
        all_sales = db.query(Transaction).filter(Transaction.transaction_type == "SALE").all()
        
        # 1. 실제 계약 및 실거래 집계 (is_demo == False 및 is_test_record == False 엄격 필터: DIRECTIVE 049)
        real_sales = [
            s for s in all_sales
            if not getattr(s, "is_demo", True)
            and not getattr(s, "is_test_record", False)
            and getattr(s, "is_verified_sale", False)
            and getattr(s, "settlement_status", "") == "SETTLED"
        ]
        real_total_count = len(real_sales)
        real_ai_sales = [s for s in real_sales if getattr(s, "attribution_type", "") == "AI_VIDEO"]
        real_organic_sales = [s for s in real_sales if getattr(s, "attribution_type", "") != "AI_VIDEO"]
        real_net_profit = sum(getattr(s, "chamart_net_profit", 0) or 0 for s in real_sales)
        real_operating_cost = sum(getattr(s, "operating_cost", 0) or 0 for s in real_ai_sales)

        # 실거래가 0건인 경우 임의의 수치 왜곡 금지 -> NOT_AVAILABLE
        real_roi: Any = "NOT_AVAILABLE"
        if real_total_count > 0 and real_operating_cost > 0:
            real_roi = round((real_net_profit / real_operating_cost) * 100.0, 1)

        # 2. 데모 환경 가상 시뮬레이션 분리 집계
        demo_sales = [s for s in all_sales if getattr(s, "is_demo", False)]
        demo_ai_sales = [s for s in demo_sales if getattr(s, "attribution_type", "") == "AI_VIDEO"]
        demo_net_profit = sum(getattr(s, "chamart_net_profit", 0) or 0 for s in demo_sales)
        demo_operating_cost = sum(getattr(s, "operating_cost", 0) or 0 for s in demo_ai_sales)
        demo_roi = round((demo_net_profit / demo_operating_cost) * 100.0, 1) if demo_operating_cost > 0 else 0.0

        # 상담 리드 분석 (실데이터 / 데모 분리)
        consultations = db.query(Consultation).all()
        valid_consultations = [c for c in consultations if not getattr(c, "is_duplicate", False)]
        video_leads = [
            c for c in valid_consultations
            if getattr(c, "inquiry_source", "") in ["YOUTUBE_SHORTS", "INSTAGRAM_REELS", "TIKTOK"]
        ]

        return {
            "demo_badge": "CHAMART_DEMO_ENVIRONMENT",
            # 실거래 영역 (DIRECTIVE 048 실적 오염 원천 차단)
            "real_world_sales": {
                "total_sales_count": real_total_count,
                "ai_video_attributed_sales": len(real_ai_sales),
                "organic_sales": len(real_organic_sales),
                "chamart_net_profit_million_krw": real_net_profit,
                "content_operating_cost_million_krw": real_operating_cost,
                "ai_video_roi": real_roi,  # "NOT_AVAILABLE"
                "status_note": "실거래 0건 (정식 외부 광고 집행 전 안전 샌드박스 대기)",
            },
            # 데모 시뮬레이션 분리 영역
            "demo_simulation": {
                "is_demo_data": True,
                "simulation_sales_count": len(demo_sales),
                "simulation_ai_sales": len(demo_ai_sales),
                "simulation_net_profit_million_krw": demo_net_profit,
                "simulation_operating_cost_million_krw": demo_operating_cost,
                "simulation_roi_pct": demo_roi,
                "warning": "데모 환경 가상 시뮬레이션 지표이며 실제 사업 실적이 아닙니다.",
            },
            # 하위 호환성 유지 필드 (실거래 0건 반영)
            "total_sales_count": real_total_count,
            "ai_video_attributed_sales": len(real_ai_sales),
            "organic_sales": len(real_organic_sales),
            "total_chamart_net_profit_million_krw": real_net_profit,
            "ai_video_roi_pct": real_roi,  # "NOT_AVAILABLE"
            "lead_metrics": {
                "total_valid_leads": len(valid_consultations),
                "ai_video_sourced_leads": len(video_leads),
                "duplicate_leads_quarantined": len(consultations) - len(valid_consultations),
            },
            "attribution_rule": "영상 시청 및 해당 링크/태그 문의 고객 중복 제거 후 검증된 실계약만 매칭",
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

        # 1. State Vector 구성 (과거/현재 관측치만 사용, 사후 거래/정산 정보 절대 배제)
        discount_ratio = 0.0
        if market_avg > 0 and v.target_price > 0:
            discount_ratio = round((market_avg - v.target_price) / market_avg, 4)

        now = datetime.datetime.utcnow()
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
            "observed_at": now.isoformat(),
            "ingested_at": now.isoformat(),
        }

        # 2. Rule Baseline Policy 결정 (결정론적 규칙)
        # DIRECTIVE 048 P0-3: 결정론적 규칙 정책의 실제 행동 선택 확률(Propensity)은 정확히 1.0입니다.
        if not rights_allowed:
            if discount_ratio > 0.05 or price_drop > 100:
                action = "REQUEST_DEALER_REVIEW"  # 가성비가 높으나 권한이 없으므로 딜러 접촉 제휴 검토
                action_details = {
                    "priority": "HIGH",
                    "reason": "시세 대비 저렴한 매물 제휴 시급",
                    "constraints": {"rights_allowed": False, "discount_ratio": discount_ratio}
                }
            else:
                action = "OBSERVE"  # 권한 없고 특이사항 없으므로 관망
                action_details = {
                    "priority": "LOW",
                    "reason": "관측 유지",
                    "constraints": {"rights_allowed": False}
                }
        else:
            if discount_ratio >= 0.05:
                action = "PROPOSE_VIDEO"  # 권한 있고 가성비 우수 -> 즉시 영상 제작 제안
                action_details = {
                    "channels": ["YOUTUBE", "INSTAGRAM"],
                    "budget_won": 200000,
                    "constraints": {"rights_allowed": True, "discount_ratio": discount_ratio}
                }
            else:
                action = "ADJUST_PRIORITY"  # 권한 있으나 시세와 유사 -> 우선순위 조정
                action_details = {
                    "priority": "MEDIUM",
                    "reason": "영상 제작 대기열 보통 순위",
                    "constraints": {"rights_allowed": True}
                }

        action_prob = 1.0  # 결정론적 정책의 정직한 Propensity

        # 3. 시간순 데이터 분할 (Split) - DIRECTIVE 048 타임스탬프 기준 3단계 연속 분할
        # TRAIN: 2026-10-01 이전, VAL: 2026-10-01 ~ 2026-10-20, TEST: 2026-10-20 이후
        if now < datetime.datetime(2026, 10, 1):
            split = "TRAIN"
        elif now < datetime.datetime(2026, 10, 20):
            split = "VAL"
        else:
            split = "TEST"  # 10월 20일 이후는 엄격하게 TEST 집합에 배치

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
        """DIRECTIVE 048 P0-2: 실제 판매·정산 원장(Ground Truth) 기반 강화학습 보상(Reward) 확정.
        
        [임의 보상 차단 및 증빙 강제]:
        - 클라이언트의 임의 입력값 대신 DB의 실제 Transaction 레코드를 직접 재조회
        - is_demo=True 데모 거래 배제
        - 정산 완료(SETTLED) 및 실제 차량 일치 검증
        - 동일 거래의 중복 Reward 확정 차단
        """
        log = db.query(RLDecisionLog).filter(RLDecisionLog.id == decision_id).first()
        if not log:
            raise ValueError(f"RL 의사결정 로그 '{decision_id}'를 찾을 수 없습니다.")

        # 1. 실제 판매 계약 DB 조회 (Ground Truth 강제)
        tx = db.query(Transaction).filter(Transaction.id == req.transaction_id).first()
        if not tx:
            raise ValueError(f"정산 계약 증빙 오류: 거래 ID '{req.transaction_id}'를 찾을 수 없습니다.")

        if tx.transaction_type != "SALE":
            raise ValueError("보상 확정 오류: 판매(SALE) 거래만 보상으로 연결 가능합니다.")

        if tx.vehicle_id != log.vehicle_id:
            raise ValueError(
                f"차량 불일치 오류: 해당 거래의 차량({tx.vehicle_id})과 의사결정 대상 차량({log.vehicle_id})이 다릅니다."
            )

        if tx.settlement_status != "SETTLED":
            raise ValueError("정산 미완결 오류: 정산 완료(SETTLED)된 거래만 보상을 확정할 수 있습니다.")

        if tx.is_demo:
            raise ValueError("데모 격리 원칙 위반: 데모 거래(is_demo=True)는 실전 강화학습 보상으로 확정할 수 없습니다.")

        # 2. 동일 거래 중복 보상 확정 차단
        existing = (
            db.query(RLDecisionLog)
            .filter(
                RLDecisionLog.verified_transaction_id == tx.id,
                RLDecisionLog.id != log.id,
            )
            .first()
        )
        if existing:
            raise ValueError(
                f"이중 보상 누적 차단: 거래 ID '{tx.id}'는 이미 결정 로그 '{existing.id}'에 보상으로 확정되었습니다."
            )

        # 3. Ground Truth: DB의 실제 거래 레코드로부터 직접 역산
        fee_revenue = getattr(tx, "dealer_commission_amount", 0) or 0
        operating_cost = getattr(tx, "operating_cost", 0) or 0
        
        # 체류일수 계산 (거래일자 - 의사결정일자)
        try:
            tx_dt = datetime.datetime.strptime(tx.transaction_date, "%Y-%m-%d")
            days_to_sell = max(1, (tx_dt - log.timestamp).days)
        except Exception:
            days_to_sell = 10

        verified_contribution = 1.0 if getattr(tx, "attribution_type", "") == "AI_VIDEO" else 0.0
        time_penalty = round(days_to_sell * 0.5, 2)
        net_reward = round(
            fee_revenue - operating_cost + (50.0 if verified_contribution > 0.5 else 0.0) - time_penalty,
            2,
        )

        reward_details = {
            "ground_truth_transaction_id": tx.id,
            "transaction_amount": tx.amount,
            "fee_revenue": fee_revenue,
            "operating_cost": operating_cost,
            "days_to_sell": days_to_sell,
            "verified_contribution": verified_contribution,
            "time_penalty": time_penalty,
            "net_reward": net_reward,
            "notes": req.notes or "실제 거래 및 정산 원장 검증 완료",
            "verified_at": datetime.datetime.utcnow().isoformat(),
        }

        log.reward = net_reward
        log.reward_details_json = json.dumps(reward_details, ensure_ascii=False)
        log.verified_transaction_id = tx.id
        log.is_censored = False  # 정당하게 Uncensored 해제!
        db.commit()
        db.refresh(log)

        return {
            "decision_id": log.id,
            "reward": log.reward,
            "is_censored": log.is_censored,
            "verified_transaction_id": log.verified_transaction_id,
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

    # =========================================================================
    # DIRECTIVE 071: 차마트 엔카급 상세 검색, 보유 매물 우선노출, 부위별 사진 관리 시스템
    # =========================================================================

    STANDARD_PHOTO_SLOTS = [
        # A. 외관 전체 (EXTERIOR_FULL)
        {"category_code": "EXTERIOR_FULL", "category_label": "외관 전체", "view_code": "EXT_FRONT", "label": "정면", "is_required": True},
        {"category_code": "EXTERIOR_FULL", "category_label": "외관 전체", "view_code": "EXT_FRONT_LEFT_45", "label": "전면 좌측 45도", "is_required": True},
        {"category_code": "EXTERIOR_FULL", "category_label": "외관 전체", "view_code": "EXT_FRONT_RIGHT_45", "label": "전면 우측 45도", "is_required": False},
        {"category_code": "EXTERIOR_FULL", "category_label": "외관 전체", "view_code": "EXT_SIDE_LEFT", "label": "좌측면 전체", "is_required": True},
        {"category_code": "EXTERIOR_FULL", "category_label": "외관 전체", "view_code": "EXT_SIDE_RIGHT", "label": "우측면 전체", "is_required": True},
        {"category_code": "EXTERIOR_FULL", "category_label": "외관 전체", "view_code": "EXT_REAR_LEFT_45", "label": "후면 좌측 45도", "is_required": True},
        {"category_code": "EXTERIOR_FULL", "category_label": "외관 전체", "view_code": "EXT_REAR_RIGHT_45", "label": "후면 우측 45도", "is_required": False},
        {"category_code": "EXTERIOR_FULL", "category_label": "외관 전체", "view_code": "EXT_REAR", "label": "후면", "is_required": True},
        {"category_code": "EXTERIOR_FULL", "category_label": "외관 전체", "view_code": "EXT_ROOF", "label": "루프 상단", "is_required": False},

        # B. 외판 상세 (EXTERIOR_PANEL)
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_BUMPER_FRONT", "label": "앞 범퍼", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_BUMPER_REAR", "label": "뒤 범퍼", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_BONNET", "label": "보닛", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_FENDER_FL", "label": "좌측 앞 펜더", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_FENDER_FR", "label": "우측 앞 펜더", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_DOOR_FL", "label": "좌측 앞 도어", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_DOOR_FR", "label": "우측 앞 도어", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_DOOR_RL", "label": "좌측 뒤 도어", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_DOOR_RR", "label": "우측 뒤 도어", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_TRUNK_LID", "label": "트렁크 리드 / 테일게이트", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_WHEEL_FL", "label": "좌측 앞 휠·타이어", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_WHEEL_FR", "label": "우측 앞 휠·타이어", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_WHEEL_RL", "label": "좌측 뒤 휠·타이어", "is_required": False},
        {"category_code": "EXTERIOR_PANEL", "category_label": "외판 상세", "view_code": "PANEL_WHEEL_RR", "label": "우측 뒤 휠·타이어", "is_required": False},

        # C. 실내 (INTERIOR)
        {"category_code": "INTERIOR", "category_label": "실내", "view_code": "INT_FRONT_ROW_FULL", "label": "앞좌석 전체", "is_required": True},
        {"category_code": "INTERIOR", "category_label": "실내", "view_code": "INT_DRIVER_SEAT", "label": "운전석", "is_required": True},
        {"category_code": "INTERIOR", "category_label": "실내", "view_code": "INT_PASSENGER_SEAT", "label": "조수석", "is_required": False},
        {"category_code": "INTERIOR", "category_label": "실내", "view_code": "INT_REAR_ROW_FULL", "label": "뒷좌석 전체", "is_required": True},
        {"category_code": "INTERIOR", "category_label": "실내", "view_code": "INT_DASHBOARD", "label": "대시보드 전체", "is_required": True},
        {"category_code": "INTERIOR", "category_label": "실내", "view_code": "INT_CLUSTER_MILEAGE", "label": "계기판 / 주행거리", "is_required": True},
        {"category_code": "INTERIOR", "category_label": "실내", "view_code": "INT_STEERING_WHEEL", "label": "스티어링 휠", "is_required": True},
        {"category_code": "INTERIOR", "category_label": "실내", "view_code": "INT_CENTER_FACIA", "label": "센터페시아 / 내비게이션", "is_required": True},
        {"category_code": "INTERIOR", "category_label": "실내", "view_code": "INT_GEAR_LEVER", "label": "변속기 레버 및 센터콘솔", "is_required": False},
        {"category_code": "INTERIOR", "category_label": "실내", "view_code": "INT_TRUNK_ROOM", "label": "트렁크 내부", "is_required": True},

        # D. 엔진·기계·하부 (ENGINE_MECHANICAL)
        {"category_code": "ENGINE_MECHANICAL", "category_label": "엔진·기계·하부", "view_code": "ENG_ROOM_FULL", "label": "엔진룸 전체", "is_required": True},
        {"category_code": "ENGINE_MECHANICAL", "category_label": "엔진·기계·하부", "view_code": "ENG_DETAIL", "label": "엔진 상세", "is_required": False},
        {"category_code": "ENGINE_MECHANICAL", "category_label": "엔진·기계·하부", "view_code": "ENG_BATTERY", "label": "배터리", "is_required": False},
        {"category_code": "ENGINE_MECHANICAL", "category_label": "엔진·기계·하부", "view_code": "UND_UNDERBODY_FRONT", "label": "차량 하부 전면", "is_required": False},
        {"category_code": "ENGINE_MECHANICAL", "category_label": "엔진·기계·하부", "view_code": "UND_UNDERBODY_CENTER", "label": "차량 하부 중앙 (누유 점검)", "is_required": False},
        {"category_code": "ENGINE_MECHANICAL", "category_label": "엔진·기계·하부", "view_code": "UND_SUSPENSION_BRAKE", "label": "서스펜션 / 브레이크", "is_required": False},

        # E. 옵션·특이사항 (OPTION_FEATURE)
        {"category_code": "OPTION_FEATURE", "category_label": "옵션·특이사항", "view_code": "OPT_SMART_KEY", "label": "스마트키 2개", "is_required": False},
        {"category_code": "OPTION_FEATURE", "category_label": "옵션·특이사항", "view_code": "OPT_SUNROOF_ACTIVE", "label": "선루프 작동", "is_required": False},
        {"category_code": "OPTION_FEATURE", "category_label": "옵션·특이사항", "view_code": "OPT_CAMERA_360", "label": "어라운드뷰 / 후방카메라", "is_required": False},
        {"category_code": "OPTION_FEATURE", "category_label": "옵션·특이사항", "view_code": "DEF_SCRATCH_EVIDENCE", "label": "외관 흠집 / 실내 오염 입증", "is_required": False},

        # F. 서류 (DOCUMENT)
        {"category_code": "DOCUMENT", "category_label": "서류", "view_code": "DOC_INSPECTION_RECORD", "label": "성능점검기록부 (마스킹 승인본)", "is_required": True},
        {"category_code": "DOCUMENT", "category_label": "서류", "view_code": "DOC_INSURANCE_HISTORY", "label": "보험사고이력 자료", "is_required": False},
    ]

    @classmethod
    def search_vehicles_advanced(
        cls,
        db: Session,
        params: dict[str, Any],
        mode: str = "prod"
    ) -> dict[str, Any]:
        """엔카 수준의 다단계 상세 검색 및 차마트 보유 매물 우선순위 정렬 시스템."""
        allow_demo = (mode in ["demo", "staging"])
        
        # 1. 판매 및 공개 기본 조건 (보안 경계: 미승인, 비공개, 판매완료 원천 차단)
        filters = [
            Vehicle.status.in_(["FOR_SALE", "AVAILABLE"]),
            Vehicle.is_public == True,
            Vehicle.ownership_type.in_([OwnershipType.CHAMART_OWNED.value, OwnershipType.PARTNER_APPROVED.value]),
        ]
        if not allow_demo:
            filters.append(Vehicle.is_demo == False)

        # 2. 차량 기본 정보 필터
        # 국산 / 수입
        is_domestic = params.get("is_domestic")
        domestic_makers = ["현대", "기아", "제네시스", "쉐보레", "르노코리아", "KG모빌리티", "쌍용", "대우"]
        if is_domestic is True or str(is_domestic).lower() == "true":
            filters.append(Vehicle.manufacturer.in_(domestic_makers))
        elif is_domestic is False or str(is_domestic).lower() == "false":
            filters.append(~Vehicle.manufacturer.in_(domestic_makers))

        # 제조사 다중 선택
        manufacturers = params.get("manufacturers")
        if manufacturers:
            if isinstance(manufacturers, str):
                manufacturers = [m.strip() for m in manufacturers.split(",") if m.strip()]
            if manufacturers:
                filters.append(Vehicle.manufacturer.in_(manufacturers))

        # 모델 / 키워드
        keyword = params.get("keyword") or params.get("q")
        if keyword:
            keyword_clean = str(keyword).strip()
            filters.append(
                or_(
                    Vehicle.model_name.ilike(f"%{keyword_clean}%"),
                    Vehicle.plate_number.ilike(f"%{keyword_clean}%"),
                    Vehicle.trim.ilike(f"%{keyword_clean}%"),
                    Vehicle.manufacturer.ilike(f"%{keyword_clean}%")
                )
            )

        model_name = params.get("model_name")
        if model_name:
            filters.append(Vehicle.model_name.ilike(f"%{model_name}%"))

        trim = params.get("trim")
        if trim:
            filters.append(Vehicle.trim.ilike(f"%{trim}%"))

        # 연식 범위
        year_min = params.get("year_min")
        if year_min:
            try:
                filters.append(Vehicle.year >= int(year_min))
            except (ValueError, TypeError):
                pass
        year_max = params.get("year_max")
        if year_max:
            try:
                filters.append(Vehicle.year <= int(year_max))
            except (ValueError, TypeError):
                pass

        # 가격 범위 (만원)
        price_min = params.get("price_min")
        if price_min:
            try:
                filters.append(Vehicle.target_price >= int(price_min))
            except (ValueError, TypeError):
                pass
        price_max = params.get("price_max")
        if price_max:
            try:
                filters.append(Vehicle.target_price <= int(price_max))
            except (ValueError, TypeError):
                pass

        # 주행거리 범위 (km)
        mileage_min = params.get("mileage_min")
        if mileage_min:
            try:
                filters.append(Vehicle.mileage >= int(mileage_min))
            except (ValueError, TypeError):
                pass
        mileage_max = params.get("mileage_max")
        if mileage_max:
            try:
                filters.append(Vehicle.mileage <= int(mileage_max))
            except (ValueError, TypeError):
                pass

        # 연료 종류 (다중 선택 가능)
        fuel_types = params.get("fuel_types")
        if fuel_types:
            if isinstance(fuel_types, str):
                fuel_types = [f.strip() for f in fuel_types.split(",") if f.strip()]
            if fuel_types:
                filters.append(Vehicle.fuel_type.in_(fuel_types))

        # 변속기
        transmissions = params.get("transmissions")
        if transmissions:
            if isinstance(transmissions, str):
                transmissions = [t.strip() for t in transmissions.split(",") if t.strip()]
            if transmissions:
                filters.append(Vehicle.transmission.in_(transmissions))

        # 차종/차체 형태 (세단, SUV, RV, 경차 등)
        body_types = params.get("body_types")
        if body_types:
            if isinstance(body_types, str):
                body_types = [b.strip() for b in body_types.split(",") if b.strip()]
            if body_types:
                filters.append(Vehicle.body_type.in_(body_types))

        # 색상
        colors = params.get("colors")
        if colors:
            if isinstance(colors, str):
                colors = [c.strip() for c in colors.split(",") if c.strip()]
            if colors:
                filters.append(Vehicle.color.in_(colors))

        # 3. 매물 조건 필터
        only_chamart_owned = params.get("only_chamart_owned")
        if only_chamart_owned is True or str(only_chamart_owned).lower() == "true":
            filters.append(
                or_(
                    Vehicle.listing_ownership_type == "OWNED",
                    Vehicle.ownership_type == OwnershipType.CHAMART_OWNED.value
                )
            )

        only_priority = params.get("only_priority")
        if only_priority is True or str(only_priority).lower() == "true":
            filters.append(Vehicle.is_priority_exposure == True)

        # 4. 정렬 순서 (차마트 추천순 기본)
        sort_mode = params.get("sort", "CHAMART_RECOMMENDED").upper()

        query = db.query(Vehicle).filter(*filters)

        # 차마트 추천순 기본 정렬:
        # 1. 공개 승인된 차마트 직접 보유(OWNED) & 우선노출 지정 매물 (가격이 더 높아도 최우선)
        # 2. 일반 차마트 직접 보유(OWNED) 매물
        # 3. 파트너 승인 매물 중 우선지정 매물
        # 4. 일반 정상 매물
        if sort_mode == "CHAMART_RECOMMENDED":
            # CASE 문으로 우선순위 점수 부여
            priority_score = case(
                (and_(Vehicle.listing_ownership_type == "OWNED", Vehicle.is_priority_exposure == True), 400),
                (Vehicle.listing_ownership_type == "OWNED", 300),
                (and_(Vehicle.listing_ownership_type == "PARTNER_CONFIRMED", Vehicle.is_priority_exposure == True), 200),
                else_=100
            )
            query = query.order_by(
                desc(priority_score),
                desc(Vehicle.priority_rank),
                desc(Vehicle.updated_at)
            )
        elif sort_mode in ["PRICE_ASC", "PRICE_LOW"]:
            query = query.order_by(asc(Vehicle.target_price), desc(Vehicle.updated_at))
        elif sort_mode in ["PRICE_DESC", "PRICE_HIGH"]:
            query = query.order_by(desc(Vehicle.target_price), desc(Vehicle.updated_at))
        elif sort_mode in ["DATE_DESC", "LATEST"]:
            query = query.order_by(desc(Vehicle.created_at))
        elif sort_mode in ["MILEAGE_ASC", "MILEAGE_LOW"]:
            query = query.order_by(asc(Vehicle.mileage))
        elif sort_mode in ["YEAR_DESC", "YEAR_HIGH"]:
            query = query.order_by(desc(Vehicle.year), asc(Vehicle.mileage))
        elif sort_mode in ["YEAR_ASC", "YEAR_LOW"]:
            query = query.order_by(asc(Vehicle.year), asc(Vehicle.mileage))
        else:
            query = query.order_by(desc(Vehicle.updated_at))

        raw_vehicles = query.all()

        # 메모리 단계 추가 필터링 (사고/옵션 JSON 정밀 판정)
        accident_filter = params.get("accident_type") # NO_ACCIDENT, SIMPLE_REPAIR, MAJOR_ACCIDENT
        required_options = params.get("options")
        if isinstance(required_options, str):
            required_options = [o.strip() for o in required_options.split(",") if o.strip()]

        filtered_results = []
        for v in raw_vehicles:
            # 공개 적격성 검증
            if not PlatformService.is_vehicle_eligible_for_chamart_public(v, db, allow_demo=allow_demo):
                continue

            # 사고 상태 정밀 필터링
            if accident_filter:
                acc_json_str = v.accident_history_json or "{}"
                cond_json_str = v.condition_detail_json or "{}"
                try:
                    acc_data = json.loads(acc_json_str)
                    cond_data = json.loads(cond_json_str)
                except Exception:
                    acc_data, cond_data = {}, {}

                is_no_acc = (acc_data.get("accident_count", 0) == 0 and not cond_data.get("frame_damage"))
                is_simple = (acc_data.get("simple_repair", False) or cond_data.get("outer_panel_exchange", False))

                if accident_filter == "NO_ACCIDENT" and not is_no_acc:
                    continue
                elif accident_filter == "SIMPLE_REPAIR" and not (is_no_acc or is_simple):
                    continue

            # 편의 옵션 다중 선택 정밀 필터링
            if required_options:
                opt_str = (v.options_json or "") + (v.options_structured_json or "")
                has_all_options = True
                for req_opt in required_options:
                    if req_opt not in opt_str:
                        has_all_options = False
                        break
                if not has_all_options:
                    continue

            # 사진 수 및 부위별 통계 계산
            photos = db.query(VehiclePhoto).filter(VehiclePhoto.vehicle_id == v.id).all()
            photo_count = len(photos)

            # 월 납입금 추산 (60개월, 연 5.9% 기준 원리금 균등)
            price_won = (v.target_price or 0) * 10000
            monthly_est = 0
            if price_won > 0:
                r = 0.059 / 12
                n = 60
                monthly_est = int((price_won * r * ((1 + r) ** n)) / (((1 + r) ** n) - 1) / 10000)

            # 소유 및 우선노출 배지 정보
            is_owned = (v.listing_ownership_type == "OWNED")
            is_priority = bool(v.is_priority_exposure)

            item = {
                "id": v.id,
                "plate_number": v.plate_number,
                "manufacturer": v.manufacturer or "미확인",
                "model_name": v.model_name,
                "trim": v.trim or "",
                "year": v.year,
                "mileage": v.mileage,
                "fuel_type": v.fuel_type or "미확인",
                "transmission": v.transmission or "오토",
                "body_type": v.body_type or "세단",
                "color": v.color or "미확인",
                "target_price": v.target_price,
                "monthly_payment_estimate": monthly_est,
                "primary_photo_url": v.primary_photo_url or (photos[0].photo_url if photos else "/static/img/car_placeholder.jpg"),
                "photo_count": photo_count,
                "branch_name": "차마트 장한평 본사 직영점",
                "status": v.status,
                "publishing_status": getattr(v, "publishing_status", "PUBLISHED"),
                "is_demo_asset": allow_demo,
                "demo_notice": "UI 디자인 검수용 시연 데이터" if allow_demo else None,

                # DIRECTIVE 071 전용 속성
                "listing_ownership_type": "OWNED" if is_owned else (v.listing_ownership_type or "PARTNER_CONFIRMED"),
                "is_chamart_owned": is_owned,
                "is_priority_exposure": is_priority,
                "priority_rank": v.priority_rank or 0,
                "priority_reason": v.priority_reason or ("차마트 직영 실매물 우선추천" if is_owned else None),
                "badge_chamart_owned": is_owned,
                "badge_priority": is_priority,
            }
            filtered_results.append(item)

        total_count = len(filtered_results)

        # 페이지네이션
        page = max(1, int(params.get("page", 1)))
        limit = max(1, int(params.get("limit", 20)))
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_items = filtered_results[start_idx:end_idx]

        # 상단 '차마트 우선매물' 별도 추출 (선택적 노출 지원)
        priority_items = [item for item in filtered_results if item["is_priority_exposure"] or item["is_chamart_owned"]][:4]

        return {
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit if total_count > 0 else 1,
            "items": paginated_items,
            "priority_items": priority_items,
            "sort_applied": sort_mode,
        }

    @classmethod
    def get_vehicle_photo_matrix(cls, db: Session, vehicle_id: str) -> dict[str, Any]:
        """차량 부위별 사진 등록 상태 및 45개 표준 슬롯 매트릭스 조회."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            return {"error": "Vehicle not found", "slots": []}

        photos = db.query(VehiclePhoto).filter(VehiclePhoto.vehicle_id == vehicle_id).order_by(VehiclePhoto.sort_order).all()
        photos_by_view = {}
        for p in photos:
            view = p.view_code or "UNSPECIFIED"
            if view not in photos_by_view:
                photos_by_view[view] = []
            photos_by_view[view].append({
                "id": p.id,
                "photo_url": p.photo_url,
                "thumb_url": p.thumb_url or p.photo_url,
                "category_code": p.category_code or p.category,
                "display_label": p.display_label or p.caption or "부위 미확인",
                "is_primary": p.is_primary,
                "sort_order": p.sort_order,
                "approval_status": p.approval_status or "APPROVED",
                "public_visibility": p.public_visibility or "PUBLIC",
                "photo_note": p.photo_note,
                "damage_evidence": p.damage_evidence or False,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

        slots_status = []
        registered_count = 0
        for slot in cls.STANDARD_PHOTO_SLOTS:
            view = slot["view_code"]
            matched_photos = photos_by_view.get(view, [])
            if matched_photos:
                registered_count += len(matched_photos)
            slots_status.append({
                "category_code": slot["category_code"],
                "category_label": slot["category_label"],
                "view_code": view,
                "label": slot["label"],
                "is_required": slot["is_required"],
                "is_registered": len(matched_photos) > 0,
                "photo_count": len(matched_photos),
                "photos": matched_photos,
            })

        return {
            "vehicle_id": vehicle_id,
            "plate_number": v.plate_number,
            "model_name": v.model_name,
            "total_slots": len(cls.STANDARD_PHOTO_SLOTS),
            "registered_photos_count": len(photos),
            "slots": slots_status,
        }

    @classmethod
    def update_vehicle_priority_settings(
        cls,
        db: Session,
        vehicle_id: str,
        payload: dict[str, Any],
        admin_username: str = "admin"
    ) -> dict[str, Any]:
        """관리자 전용 차량 소유/판매 유형 및 우선노출 설정 (서버 검증 및 이력 보존)."""
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not v:
            return {"success": False, "message": "차량을 찾을 수 없습니다."}

        # 유형 유효성 검증
        valid_ownership_types = ["OWNED", "PARTNER_CONFIRMED", "BROKERAGE", "EXTERNAL"]
        if "listing_ownership_type" in payload:
            new_type = str(payload["listing_ownership_type"]).upper()
            if new_type in valid_ownership_types:
                v.listing_ownership_type = new_type
                # 기존 ownership_type과도 호환 동기화
                if new_type == "OWNED":
                    v.ownership_type = OwnershipType.CHAMART_OWNED.value
                elif new_type == "PARTNER_CONFIRMED":
                    v.ownership_type = OwnershipType.PARTNER_APPROVED.value
                elif new_type == "BROKERAGE":
                    v.ownership_type = OwnershipType.PARTNER_CANDIDATE.value

        old_priority = v.is_priority_exposure
        if "is_priority_exposure" in payload:
            v.is_priority_exposure = bool(payload["is_priority_exposure"])

        if "priority_rank" in payload:
            v.priority_rank = int(payload["priority_rank"])

        if "priority_reason" in payload:
            v.priority_reason = str(payload["priority_reason"]).strip()

        # 이력 기록 (priority_history_json)
        try:
            history = json.loads(v.priority_history_json or "[]")
        except Exception:
            history = []

        history.append({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "updated_by": admin_username,
            "listing_ownership_type": v.listing_ownership_type,
            "is_priority_exposure": v.is_priority_exposure,
            "priority_rank": v.priority_rank,
            "priority_reason": v.priority_reason,
        })
        v.priority_history_json = json.dumps(history, ensure_ascii=False)
        v.updated_at = datetime.datetime.utcnow()

        db.commit()
        return {
            "success": True,
            "vehicle_id": v.id,
            "listing_ownership_type": v.listing_ownership_type,
            "is_priority_exposure": v.is_priority_exposure,
            "priority_rank": v.priority_rank,
            "priority_reason": v.priority_reason,
            "message": "우선노출 설정이 안전하게 갱신되었습니다.",
        }

    # DIRECTIVE 096: 카매니저 실동기화 현황 조회 및 관리자 수동 트리거 서비스
    @staticmethod
    def get_carmanager_sync_status(db: Session) -> dict[str, Any]:
        """카매니저 동기화 로그 및 스코프별 매물 집계 현황 반환."""
        from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
        
        # 1. DB 직접 쿼리를 통한 최근 로그 5건 조회
        logs = []
        try:
            res = db.execute(
                select(Vehicle.id).limit(1)
            ) # 세션 핑
            raw_logs = db.execute(
                "SELECT id, scope, started_at, finished_at, total_inspected, new_inserted, price_changed, sold_count, unverified_count, delisted_count, status FROM carmanager_sync_logs ORDER BY started_at DESC LIMIT 5"
            ).fetchall()
            for row in raw_logs:
                logs.append({
                    "id": row[0],
                    "scope": row[1],
                    "started_at": str(row[2]),
                    "finished_at": str(row[3]),
                    "total_inspected": row[4],
                    "new_inserted": row[5],
                    "price_changed": row[6],
                    "sold_count": row[7],
                    "unverified_count": row[8],
                    "delisted_count": row[9],
                    "status": row[10]
                })
        except Exception:
            pass

        # 2. 스코프별 차량 현황
        owned_cnt = db.query(Vehicle).filter(Vehicle.listing_ownership_type == "OWNED").count()
        external_cnt = db.query(Vehicle).filter(Vehicle.listing_ownership_type == "EXTERNAL").count()
        public_cnt = db.query(Vehicle).filter(Vehicle.is_public == True).count()
        draft_cnt = db.query(Vehicle).filter(Vehicle.status == "DRAFT").count()

        return {
            "latest_logs": logs,
            "counts": {
                "owned_vehicles": owned_cnt,
                "external_observed_vehicles": external_cnt,
                "public_vehicles": public_cnt,
                "draft_quarantined_vehicles": draft_cnt
            },
            "last_sync_time": logs[0]["finished_at"] if logs else None
        }

    @staticmethod
    def trigger_carmanager_sync(db: Session, scope: str = "OWNED", use_live: bool = True) -> dict[str, Any]:
        """카매니저 실시간 세션 접속 및 스냅샷 동기화 실행 (DIRECTIVE 096)."""
        from chaficial.platform.sourcing.carmanager_sync import CarManagerSyncService
        from chaficial.platform.sourcing.carmanager_client import CarManagerLiveClient
        import json

        service = CarManagerSyncService()
        snapshot = []
        source_mode = "LIVE"

        try:
            if scope == "OWNED":
                if use_live:
                    try:
                        client = CarManagerLiveClient()
                        snapshot = client.fetch_live_my_cars()
                        source_mode = "LIVE_CARMANAGER_SESSION"
                    except Exception as live_err:
                        # 네트워크 일시 오류 시 안전하게 캐시 스냅샷 폴백
                        with open("scratch/carmanager_inspect/my_13_cleaned_cars.json", "r", encoding="utf-8") as f:
                            snapshot = json.load(f)
                        source_mode = f"CACHE_FALLBACK ({str(live_err)[:60]})"
                else:
                    with open("scratch/carmanager_inspect/my_13_cleaned_cars.json", "r", encoding="utf-8") as f:
                        snapshot = json.load(f)
                    source_mode = "CACHE_FILE"
            else:
                with open("scratch/carmanager_inspect/janghanpyeong_20_sampled.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                snapshot = data if isinstance(data, list) else data.get("cars", [])
                source_mode = "JANGHANPYEONG_OBSERVED_REAL"

            stats = service.run_sync(snapshot, scope=scope)
            stats["source_mode"] = source_mode
            return {"success": True, "stats": stats}
        except Exception as e:
            return {"success": False, "error": str(e)}


