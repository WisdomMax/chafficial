"""차마트 통합 운영 플랫폼 API 스키마 모델."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class VehicleCreateRequest(BaseModel):
    branch_id: str
    plate_number: str
    model_name: str
    year: int
    mileage: int
    fuel_type: str = "가솔린"
    transmission: str = "오토"
    color: str = "화이트"
    purchase_price: int = 0
    target_price: int = 0
    status: str = "PURCHASE_REVIEW"


class VehicleUpdateRequest(BaseModel):
    plate_number: Optional[str] = None
    model_name: Optional[str] = None
    year: Optional[int] = None
    mileage: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    color: Optional[str] = None
    purchase_price: Optional[int] = None
    target_price: Optional[int] = None
    status: Optional[str] = None


class VehicleStatusChangeRequest(BaseModel):
    status: str
    reason: Optional[str] = "상태 수동 변경"


class CustomerCreateRequest(BaseModel):
    branch_id: str
    name: str
    phone: str
    status: str = "NEW"
    target_vehicle_model: Optional[str] = None
    budget_max: Optional[int] = None
    assigned_staff: Optional[str] = "차마트 상담팀"
    contact_consent: bool = True
    notes: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = "DIRECT"
    source_image_url: Optional[str] = None
    ai_confidence: Optional[float] = None


class CustomerUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    target_vehicle_model: Optional[str] = None
    budget_max: Optional[int] = None
    assigned_staff: Optional[str] = None
    contact_consent: Optional[bool] = None
    notes: Optional[str] = None
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    email: Optional[str] = None
    source: Optional[str] = None
    source_image_url: Optional[str] = None
    ai_confidence: Optional[float] = None


class ConsultationCreateRequest(BaseModel):
    channel: str = "전화"
    content: str
    staff_name: str = "담당 매니저"
    next_action_date: Optional[str] = None


class TransactionCreateRequest(BaseModel):
    vehicle_id: str
    transaction_type: str  # PURCHASE, SALE
    amount: int
    party_name: str
    party_contact: Optional[str] = None
    transaction_date: str
    notes: Optional[str] = None


class MediaProjectCreateRequest(BaseModel):
    title: str
    vehicle_id: Optional[str] = None
    content_format: str = "SHORTS"
    concept: str = "가성비 패밀리 세단"
    target_platform: str = "YOUTUBE"
    script_draft: Optional[str] = None


class MediaProjectStatusUpdateRequest(BaseModel):
    status: str


class DocumentApprovalRequest(BaseModel):
    approved: bool
    reviewer_name: str = "차마트 관리자"


# ----------------------------------------------------
# DIRECTIVE 046-D 차량 마스터 및 상세 관리 스키마
# ----------------------------------------------------
class VehicleMasterUpdateRequest(BaseModel):
    plate_number: Optional[str] = None
    model_name: Optional[str] = None
    year: Optional[int] = None
    mileage: Optional[int] = None
    target_price: Optional[int] = None
    purchase_price: Optional[int] = None
    status: Optional[str] = None
    ownership_type: Optional[str] = None
    dealer_id: Optional[str] = None
    vin: Optional[str] = None
    displacement_cc: Optional[int] = None
    first_registration_date: Optional[str] = None
    drive_type: Optional[str] = None
    interior_color: Optional[str] = None
    options: Optional[list[str]] = None
    accident_history: Optional[dict[str, Any]] = None
    inspection_summary: Optional[dict[str, Any]] = None
    marketing_auth: Optional[dict[str, Any]] = None
    primary_photo_url: Optional[str] = None


class VehicleDefectCreateRequest(BaseModel):
    part_name: str
    defect_type: str
    severity: str = "경미"
    action_status: str = "OBSERVED"
    estimated_repair_cost: int = 0
    notes: Optional[str] = None


class VehicleDefectUpdateRequest(BaseModel):
    part_name: Optional[str] = None
    defect_type: Optional[str] = None
    severity: Optional[str] = None
    action_status: Optional[str] = None
    estimated_repair_cost: Optional[int] = None
    notes: Optional[str] = None


class PhotoOrderItem(BaseModel):
    id: str
    sort_order: int
    is_primary: bool = False
    allow_video_use: bool = True
    category: Optional[str] = None


class VehiclePhotoReorderRequest(BaseModel):
    photo_orders: list[PhotoOrderItem]


class VehicleVideoProjectCreateRequest(BaseModel):
    content_format: str = "SHORTS"  # SHORTS, REELS, LONGFORM
    target_platform: str = "YOUTUBE"  # YOUTUBE, INSTAGRAM, TIKTOK, TELEGRAM
    custom_title: Optional[str] = None
    concept: Optional[str] = None


class PlatformRegisterIntentRequest(BaseModel):
    platforms: list[str] = ["ENCAR", "KB_CHACHACHA", "CAR_MANAGER"]


# ----------------------------------------------------
# DIRECTIVE 047 시장 분석, 권한 원장, 기여도 및 RL 스키마
# ----------------------------------------------------
class DealerRightsGrantRequest(BaseModel):
    sale_allowed: bool = True
    photo_allowed: bool = True
    video_allowed: bool = True
    allowed_channels: list[str] = ["YOUTUBE", "INSTAGRAM", "TIKTOK"]
    valid_until: Optional[str] = None  # YYYY-MM-DD
    approved_by: str = "차마트 장한평 본부"
    dealer_commission_pct: float = 4.5
    chamart_share_pct: float = 15.0


class DealerRightsRevokeRequest(BaseModel):
    reason: str
    revoked_by: str = "차마트 관리자"


class RLDecisionEvaluateRequest(BaseModel):
    vehicle_id: str
    policy_version: str = "v1.0-rule_baseline"


class RLDecisionRewardUpdateRequest(BaseModel):
    transaction_id: str  # 실제 판매 계약 및 정산 원장 ID (Ground Truth 강제)
    notes: Optional[str] = None


# ----------------------------------------------------
# DIRECTIVE 050-C AI 명함 및 거래서류 인식 스키마
# ----------------------------------------------------
class CustomerCandidate(BaseModel):
    """명함 이미지 분석 결과 고객 후보 모델."""
    name: str
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    phone: str
    company_phone: Optional[str] = None
    email: Optional[str] = None
    company_address: Optional[str] = None
    notes: Optional[str] = None
    confidence: float = 0.95


class CustomerFromCardRequest(BaseModel):
    """명함 확인 후 CRM 정식 고객 등록 요청."""
    branch_id: Optional[str] = None
    name: str
    phone: str
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    email: Optional[str] = None
    target_vehicle_model: Optional[str] = None
    budget_max: Optional[int] = None
    notes: Optional[str] = None
    source_image_url: Optional[str] = None
    ai_confidence: Optional[float] = 0.95
    status: str = "NEW"


class TransactionDocumentExtract(BaseModel):
    """거래서류(매매계약서, 정산서, 입출금내역 등) 분석 결과 모델."""
    document_type: str = "CONTRACT"  # CONTRACT, SETTLEMENT, EXPENSE, BANK_TRANSFER
    transaction_type: str = "SALE"  # PURCHASE, SALE, EXPENSE, DEPOSIT
    transaction_date: str = ""      # YYYY-MM-DD
    vehicle_plate_number: Optional[str] = None
    vin: Optional[str] = None
    party_name: str = ""
    party_contact: Optional[str] = None
    dealership_name: Optional[str] = None
    total_amount: int = 0           # 만원 단위
    supply_amount: Optional[int] = 0
    vat_amount: Optional[int] = 0
    registration_fee: Optional[int] = 0
    brokerage_fee: Optional[int] = 0
    refurbishment_cost: Optional[int] = 0
    has_official_seal: bool = False
    confidence: float = 0.90
    summary: Optional[str] = None


class TransactionDraftConfirmRequest(BaseModel):
    """거래 초안 확인 및 관리자 승인 요청 (무결성 보장)."""
    document_review_id: Optional[str] = None
    vehicle_id: str
    transaction_type: str = "SALE"  # PURCHASE, SALE, EXPENSE, DEPOSIT
    amount: int  # 만원
    party_name: str
    party_contact: Optional[str] = None
    transaction_date: str
    settlement_status: str = "PENDING"  # 기본값 PENDING
    dealer_commission_amount: int = 0
    chamart_net_profit: int = 0
    operating_cost: int = 0
    attribution_type: str = "AI_VIDEO"
    is_verified_sale: bool = False      # 실제 증빙 승인 전까지 False 유지
    is_test_record: bool = False
    notes: Optional[str] = None


class GeminiKeySaveRequest(BaseModel):
    """관리자 화면 Gemini API 키 등록 및 모델 설정."""
    api_key: str
    model: Optional[str] = "gemini-flash-latest"
    fallback_model: Optional[str] = "gemini-flash-lite"
