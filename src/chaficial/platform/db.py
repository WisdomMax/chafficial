"""차마트(CHAMART) 통합 운영 플랫폼 데이터베이스 모델 및 세션 관리.

DIRECTIVE 045 명세 준수:
- 차마트 본사(장한평) 및 지점(수원) 다중 거점 모델 지원
- 실제 작동 4대 영역: 차량 관리, 고객 CRM, 거래/정산, 영상 스튜디오
- AI 서류 인식 검토 대기열 및 미래 연동(텔레그램, SMS, 카매니저) 모델
- 데모 데이터 분리: data/chamart/chamart_platform_demo.db 에 격리 보존
"""

from __future__ import annotations

import datetime
import enum
import json
import os
import uuid
from pathlib import Path
from typing import Any, Generator
from contextlib import contextmanager

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session

# 데이터 저장 디렉토리 및 DB 경로 (환경변수 CHAMART_DB_PATH 지원: DIRECTIVE 049 테스트 격리)
DB_DIR = Path("data/chamart")
DB_DIR.mkdir(parents=True, exist_ok=True)
_CUSTOM_DB_PATH = os.environ.get("CHAMART_DB_PATH")
if _CUSTOM_DB_PATH:
    DEMO_DB_PATH = Path(_CUSTOM_DB_PATH)
    if not DEMO_DB_PATH.parent.exists():
        DEMO_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
else:
    DEMO_DB_PATH = DB_DIR / "chamart_platform_demo.db"

DEMO_DB_URL = f"sqlite:///{DEMO_DB_PATH.absolute()}"


class OwnershipType(str, enum.Enum):
    """차량 소유 및 관리 권한 유형 (DIRECTIVE 046-D / 052)."""
    CHAMART_OWNED = "CHAMART_OWNED"        # 차마트 직영 차량 (완전 소유 및 판매 권한 보유)
    PARTNER_APPROVED = "PARTNER_APPROVED"  # 제휴 승인 매물 (서류/사진/광고권한 확인 완료)
    PARTNER_CANDIDATE = "PARTNER_CANDIDATE" # 제휴 후보 매물 (미승인, 광고 금지)
    MARKET_OBSERVED = "MARKET_OBSERVED"    # 시장 관측 매물 (엔카/KB 등 모니터링용, 공개 절대 금지)


class PublishingStatus(str, enum.Enum):
    """차량 플랫폼 게시 준비 및 승인 상태 (DIRECTIVE 050 / 052)."""
    DRAFT = "DRAFT"
    DATA_VERIFIED = "DATA_VERIFIED"
    READY_TO_PUBLISH = "READY_TO_PUBLISH"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    UPDATED = "UPDATED"
    SOLD = "SOLD"
    UNPUBLISHED = "UNPUBLISHED"


class Base(DeclarativeBase):
    """플랫폼 공통 베이스 모델."""
    pass


class Branch(Base):
    """지점/거점 모델 (장한평 본사, 수원 지점)."""
    __tablename__ = "branches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    region: Mapped[str] = mapped_column(String(50), nullable=False)  # 서울 동대문구, 경기 수원시 등
    address: Mapped[str] = mapped_column(String(200), nullable=True)
    is_headquarters: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    vehicles = relationship("Vehicle", back_populates="branch")
    customers = relationship("Customer", back_populates="branch")


class User(Base):
    """직원/관리자 계정 모델."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="DEALER")  # ADMIN, DEALER, MARKETER, AUDITOR
    branch_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("branches.id"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class Vehicle(Base):
    """차량 관리 마스터 모델 (차마트 직영 및 장한평 제휴·시장 매물).
    
    DIRECTIVE 046-D 규격:
    - ownership_type: MARKET_OBSERVED, PARTNER_CANDIDATE, PARTNER_APPROVED, CHAMART_OWNED
    - 사고/보험, 성능점검, 부위별 하자, 사진 자산, 딜러/광고권한, 외부 Listing 연계
    """
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    branch_id: Mapped[str] = mapped_column(String(36), ForeignKey("branches.id"), nullable=False)
    plate_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    mileage: Mapped[int] = mapped_column(Integer, nullable=False)
    fuel_type: Mapped[str] = mapped_column(String(20), default="가솔린")
    transmission: Mapped[str] = mapped_column(String(20), default="오토")
    color: Mapped[str] = mapped_column(String(30), default="화이트")
    purchase_price: Mapped[int] = mapped_column(Integer, default=0)  # 단위: 만원
    target_price: Mapped[int] = mapped_column(Integer, default=0)    # 단위: 만원
    status: Mapped[str] = mapped_column(String(30), default="PURCHASE_REVIEW")
    # 상태: PURCHASE_REVIEW, IN_STOCK, DETAILING, FOR_SALE, CONTRACTING, SOLD, CANCELLED
    
    # DIRECTIVE 046-D 확장 필드
    ownership_type: Mapped[str] = mapped_column(String(30), default="CHAMART_OWNED")
    # 4대 구분: MARKET_OBSERVED, PARTNER_CANDIDATE, PARTNER_APPROVED, CHAMART_OWNED
    dealer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("dealers.id"), nullable=True)
    vin: Mapped[str | None] = mapped_column(String(30), nullable=True)
    displacement_cc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_registration_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    drive_type: Mapped[str] = mapped_column(String(20), default="2WD")
    interior_color: Mapped[str] = mapped_column(String(30), default="블랙")
    options_json: Mapped[str] = mapped_column(Text, default="[]")
    accident_history_json: Mapped[str] = mapped_column(Text, default="{}")
    inspection_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    marketing_auth_json: Mapped[str] = mapped_column(Text, default="{}")
    primary_photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    video_status: Mapped[str] = mapped_column(String(30), default="NONE")
    # 영상 상태: NONE, REQUESTED, IN_PRODUCTION, COMPLETED, PUBLISHED
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    timeline_json: Mapped[str] = mapped_column(Text, default="[]")  # 상태 변경 이력 리스트 JSON

    # DIRECTIVE 050 확장 필드: 마스터 상세 제원 및 다중 플랫폼 연동
    manufacturer: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 제조사 (현대, 기아 등)
    trim: Mapped[str | None] = mapped_column(String(100), nullable=True)          # 세부 등급/트림
    body_type: Mapped[str | None] = mapped_column(String(30), default="세단")     # 차체 유형 (세단, SUV 등)
    recon_cost: Mapped[int] = mapped_column(Integer, default=0)                   # 상품화 비용 (만원)
    sales_conditions: Mapped[str | None] = mapped_column(String(255), nullable=True) # 판매 조건
    ad_description: Mapped[str | None] = mapped_column(Text, nullable=True)      # 광고 상세 설명
    ad_highlights: Mapped[str | None] = mapped_column(Text, nullable=True)       # 특장점 요약
    ad_notices: Mapped[str | None] = mapped_column(Text, nullable=True)          # 고지사항
    platform_ad_copies_json: Mapped[str] = mapped_column(Text, default="{}")     # 플랫폼별 광고 문구 JSON
    options_structured_json: Mapped[str] = mapped_column(Text, default="[]")     # 표준 옵션 코드/순정/확인상태
    condition_detail_json: Mapped[str] = mapped_column(Text, default="{}")       # 프레임/외판/누유/침수 상세
    publishing_status: Mapped[str] = mapped_column(String(30), default="DRAFT") # DRAFT, DATA_VERIFIED, READY_TO_PUBLISH, APPROVED, PUBLISHED, UPDATED, SOLD, UNPUBLISHED
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)              # 차마트 고객 공개 여부 (DIRECTIVE 052: 기본값 False 격리)
    platform_readiness_json: Mapped[str] = mapped_column(Text, default="{}")    # 플랫폼별 등록 준비도 검사 결과
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    branch = relationship("Branch", back_populates="vehicles")
    dealer = relationship("Dealer", back_populates="vehicles")
    listings = relationship("VehicleListing", back_populates="vehicle", cascade="all, delete-orphan")
    defects = relationship("VehicleDefect", back_populates="vehicle", cascade="all, delete-orphan")
    photos = relationship("VehiclePhoto", back_populates="vehicle", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="vehicle")
    media_projects = relationship("MediaProject", back_populates="vehicle")
    rights_ledgers = relationship("DealerRightsLedger", back_populates="vehicle", cascade="all, delete-orphan")
    rl_decisions = relationship("RLDecisionLog", back_populates="vehicle")
    publishing_records = relationship("PlatformPublishingRecord", back_populates="vehicle", cascade="all, delete-orphan")


class Dealer(Base):
    """장한평 및 외부 제휴 딜러/상사 정보 모델 (DIRECTIVE 046-D)."""
    __tablename__ = "dealers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    branch_id: Mapped[str] = mapped_column(String(36), ForeignKey("branches.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    dealership_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 상사명 (예: 장한평 가온모터스)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    partnership_status: Mapped[str] = mapped_column(String(30), default="ACTIVE")  # ACTIVE, IN_REVIEW, INACTIVE
    contract_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    branch = relationship("Branch")
    vehicles = relationship("Vehicle", back_populates="dealer")


class VehicleListing(Base):
    """엔카, KB차차차 등 외부 플랫폼 광고 매물 연동 모델 (DIRECTIVE 046-D / 047 확장)."""
    __tablename__ = "vehicle_listings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)  # ENCAR, KB_CHACHACHA, CAR_MANAGER
    listing_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # 플랫폼 고유 매물 ID
    listing_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    advertised_price: Mapped[int] = mapped_column(Integer, default=0)
    listing_status: Mapped[str] = mapped_column(String(30), default="ACTIVE")  # ACTIVE, DELISTED, PRICE_CHANGED
    first_observed_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_observed_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    # DIRECTIVE 047 장한평 시장 분석 및 가성비 점수 필드
    region: Mapped[str] = mapped_column(String(50), default="장한평")
    is_janghanpyeong: Mapped[bool] = mapped_column(Boolean, default=True)
    data_confidence: Mapped[float] = mapped_column(Float, default=0.95)
    price_drop_amount: Mapped[int] = mapped_column(Integer, default=0)  # 직전 대비 가격 인하 (만원)
    market_avg_price: Mapped[int] = mapped_column(Integer, default=0)   # 동일 스펙 시장 평균가 (만원)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0) # 0.0 ~ 100.0 기회·가성비 점수
    observation_notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # DIRECTIVE 049 엔카 실매물 자동 소싱 및 가격 추적 필드
    initial_price: Mapped[int] = mapped_column(Integer, default=0)       # 최초 관측 가격 (만원)
    price_history_json: Mapped[str] = mapped_column(Text, default="[]")  # 가격 변경 이력 스냅샷 ([{"observed_at": "...", "price": 2500}, ...])
    location_category: Mapped[str] = mapped_column(String(50), default="LOCATION_UNKNOWN") # JANGANPYEONG_CONFIRMED, JANGANPYEONG_CANDIDATE, SEOUL_OTHER, SEOUL_UNSPECIFIED, LOCATION_UNKNOWN
    identification_reason: Mapped[str | None] = mapped_column(String(255), nullable=True) # 판정 근거
    raw_seller_location: Mapped[str | None] = mapped_column(String(255), nullable=True)   # 원본 판매자/단지 위치
    raw_seller_name: Mapped[str | None] = mapped_column(String(100), nullable=True)       # 원본 판매자/상사명
    source_confidence: Mapped[float] = mapped_column(Float, default=0.90)                 # 신뢰도 점수 (0.0~1.0)
    ingested_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow) # 최초 DB 적재 시각
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)                         # 데모 매물 여부 (실제 소싱 매물은 False)

    vehicle = relationship("Vehicle", back_populates="listings")


class PlatformPublishingRecord(Base):
    """외부 중고차 플랫폼 다중 등록 및 검증 원장 모델 (DIRECTIVE 050)."""
    __tablename__ = "platform_publishing_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False, index=True)  # ENCAR, KB_CHACHACHA, CAR_MANAGER
    publishing_status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    # 상태: DRAFT, DATA_VERIFIED, READY_TO_PUBLISH, APPROVED, EXPORTED, PUBLISHED, ERROR, UNPUBLISHED
    is_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    missing_fields_json: Mapped[str] = mapped_column(Text, default="[]")
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    mapped_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    external_listing_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_validated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_exported_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="publishing_records")


class VehicleDefect(Base):
    """차량 부위별 하자 및 수리 이력 관리 모델 (DIRECTIVE 046-D)."""
    __tablename__ = "vehicle_defects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    part_name: Mapped[str] = mapped_column(String(100), nullable=False)  # 좌측 앞범퍼, 우측 뒤휀더, 엔진룸 등
    defect_type: Mapped[str] = mapped_column(String(100), nullable=False)  # 긁힘, 미세누유, 판금, 단순교환 등
    severity: Mapped[str] = mapped_column(String(30), default="경미")  # 경미, 보통, 심각
    action_status: Mapped[str] = mapped_column(String(30), default="OBSERVED")  # OBSERVED, REPAIR_SCHEDULED, REPAIRED, KEEP_AS_IS
    estimated_repair_cost: Mapped[int] = mapped_column(Integer, default=0)  # 단위: 만원
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="defects")


class VehiclePhoto(Base):
    """차량 사진 자산 관리 모델 (외관, 실내, 엔진, 하자, 문서) (DIRECTIVE 046-D)."""
    __tablename__ = "vehicle_photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    photo_url: Mapped[str] = mapped_column(String(255), nullable=False)  # 이미지 파일 URL/경로
    thumb_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(30), default="EXTERIOR")  # EXTERIOR, INTERIOR, ENGINE, DEFECT, DOCUMENT
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_video_use: Mapped[bool] = mapped_column(Boolean, default=True)
    caption: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="photos")


class Customer(Base):
    """고객 CRM 모델 (DIRECTIVE 050-C 명함 인식 확장)."""
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    branch_id: Mapped[str] = mapped_column(String(36), ForeignKey("branches.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="NEW")
    # 상태: NEW, CONSULTING, VEHICLE_MATCHED, VISIT_SCHEDULED, CONTRACTED, COMPLETED
    target_vehicle_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    budget_max: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 단위: 만원
    assigned_staff: Mapped[str] = mapped_column(String(50), default="차마트 상담팀")
    contact_consent: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    # DIRECTIVE 050-C 명함 OCR 및 추가 정보 필드
    job_title: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    company_address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="DIRECT")  # DIRECT, BUSINESS_CARD_AI, WEB_INQUIRY, TELEGRAM
    source_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    branch = relationship("Branch", back_populates="customers")
    consultations = relationship("Consultation", back_populates="customer", cascade="all, delete-orphan")


class Consultation(Base):
    """고객별 상담 기록 모델."""
    __tablename__ = "consultations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id: Mapped[str] = mapped_column(String(36), ForeignKey("customers.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), default="전화")  # 전화, 매장방문, 카카오톡, 텔레그램, 유튜브댓글
    content: Mapped[str] = mapped_column(Text, nullable=False)
    staff_name: Mapped[str] = mapped_column(String(50), default="담당 매니저")
    next_action_date: Mapped[str | None] = mapped_column(String(20), nullable=True)  # YYYY-MM-DD
    
    # DIRECTIVE 047 유입 경로 및 중복 문의 식별
    inquiry_source: Mapped[str] = mapped_column(String(50), default="DIRECT_CALL")  # YOUTUBE_SHORTS, INSTAGRAM_REELS, TELEGRAM, DIRECT_CALL, PORTAL_ENCAR
    media_project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)  # 동일 고객 중복 문의 플래그
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="consultations")


class Transaction(Base):
    """거래·계약 관리 모델 (DIRECTIVE 047 정산 및 공헌이익 확장)."""
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)  # PURCHASE(매입), SALE(판매)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)  # 단위: 만원
    party_name: Mapped[str] = mapped_column(String(50), nullable=False)
    party_contact: Mapped[str | None] = mapped_column(String(30), nullable=True)
    transaction_date: Mapped[str] = mapped_column(String(20), nullable=False)  # YYYY-MM-DD
    settlement_status: Mapped[str] = mapped_column(String(20), default="SETTLED")  # PENDING, SETTLED, DISPUTED
    document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    # DIRECTIVE 047 정산 수익, 운영비용 및 AI 기여도 추적 필드
    dealer_commission_amount: Mapped[int] = mapped_column(Integer, default=0) # 딜러 정산 수수료 (만원)
    chamart_net_profit: Mapped[int] = mapped_column(Integer, default=0)       # 차마트 공헌이익/순수익 (만원)
    operating_cost: Mapped[int] = mapped_column(Integer, default=0)           # 콘텐츠 제작/운영비 (만원)
    attribution_type: Mapped[str] = mapped_column(String(30), default="ORGANIC_WALKIN") # AI_VIDEO, ORGANIC_WALKIN, DEALER_DIRECT
    media_project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    is_verified_sale: Mapped[bool] = mapped_column(Boolean, default=False)    # DIRECTIVE 049: 검증된 실제 계약 여부 (기본값 False)
    is_test_record: Mapped[bool] = mapped_column(Boolean, default=False)      # DIRECTIVE 049: 테스트 가상 거래 격리 플래그
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="transactions")


class DocumentReview(Base):
    """AI 서류 인식 대기열 및 거래서류 검토 모델 (DIRECTIVE 050-C 확장)."""
    __tablename__ = "document_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)  # TRANSFER_CERTIFICATE, SALE_CONTRACT, INSPECTION_RECORD, SETTLEMENT_SHEET, BANK_TRANSFER, EXPENSE_REPORT
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_data_json: Mapped[str] = mapped_column(Text, default="{}")
    review_status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED
    approved_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)

    # DIRECTIVE 050-C 7대 라이프사이클 및 거래 초안 연결
    # 상태: UPLOADED -> PROCESSING -> EXTRACTED -> NEEDS_REVIEW -> APPROVED / REJECTED / FAILED
    status: Mapped[str] = mapped_column(String(30), default="NEEDS_REVIEW")
    document_type: Mapped[str] = mapped_column(String(50), default="CONTRACT")  # CONTRACT, SETTLEMENT, EXPENSE, BANK_TRANSFER
    matched_vehicle_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    matched_customer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    extracted_amount: Mapped[int] = mapped_column(Integer, default=0)
    has_official_seal: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class GeminiUsageLog(Base):
    """Gemini Vision AI 호출 감사 및 비용/통계 추적 모델 (DIRECTIVE 050-C)."""
    __tablename__ = "gemini_usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_type: Mapped[str] = mapped_column(String(50))  # BUSINESS_CARD, TRANSACTION_DOC, TEST_CONNECTION, GENERAL
    model_used: Mapped[str] = mapped_column(String(50))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    candidate_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


class MediaProject(Base):
    """AI 영상 스튜디오 프로젝트 모델."""
    __tablename__ = "media_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=True)
    content_format: Mapped[str] = mapped_column(String(20), default="SHORTS")  # SHORTS, REELS, LONGFORM
    concept: Mapped[str] = mapped_column(String(100), default="가성비 패밀리 세단")
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")
    # 상태: DRAFT, REQUESTED, IN_PRODUCTION, REVIEW, APPROVED, DELIVERED
    script_draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_platform: Mapped[str] = mapped_column(String(30), default="YOUTUBE")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="media_projects")


class DealerRightsLedger(Base):
    """제휴 딜러 권한 원장 모델 (DIRECTIVE 047 권한 세분화 및 철회 감사)."""
    __tablename__ = "dealer_rights_ledgers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    dealer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("dealers.id"), nullable=True)
    sale_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    video_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    allowed_channels_json: Mapped[str] = mapped_column(Text, default='["YOUTUBE", "INSTAGRAM"]')
    valid_until: Mapped[str | None] = mapped_column(String(20), nullable=True)  # YYYY-MM-DD
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_by: Mapped[str] = mapped_column(String(50), default="차마트 본부")
    dealer_commission_pct: Mapped[float] = mapped_column(Float, default=5.0)  # 딜러 정산율 (%)
    chamart_share_pct: Mapped[float] = mapped_column(Float, default=15.0)     # 차마트 배분율 (%)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="rights_ledgers")


class RLDecisionLog(Base):
    """강화학습(RL) 오프라인 의사결정 원장 모델 (DIRECTIVE 047).
    
    미래 정보 누출(Data Leakage) 원천 차단:
    - 결정 시점의 State, Action, Policy Version, Propensity(선택 확률) 엄격 보존
    - 사후 거래 종결/정산 시점의 Reward 분리 연결
    - Right Censored(미판매 관측 진행 중) 상태 및 시간순 데이터셋 분할(Train/Val/Test)
    """
    __tablename__ = "rl_decision_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)
    policy_version: Mapped[str] = mapped_column(String(50), default="v1.0-rule_baseline")
    vehicle_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=True)
    
    # State Vector: 결정 당시 관측 가능한 특징만 포함 (미래 정보 금지)
    state_json: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Action: OBSERVE, REQUEST_DEALER_REVIEW, ADJUST_PRIORITY, PROPOSE_VIDEO, PROPOSE_CHANNELS
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    action_prob: Mapped[float] = mapped_column(Float, default=1.0)  # Propensity Score
    action_details_json: Mapped[str] = mapped_column(Text, default="{}")
    
    # Reward: 실제 계약 및 정산 확정 시 산정 (미종결 시 None)
    reward: Mapped[float | None] = mapped_column(Float, nullable=True)
    reward_details_json: Mapped[str] = mapped_column(Text, default="{}")
    verified_transaction_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # DIRECTIVE 048 실제 거래 증빙 ID
    
    is_censored: Mapped[bool] = mapped_column(Boolean, default=True)  # 판매 미종결 관측 중 플래그
    split: Mapped[str] = mapped_column(String(20), default="TRAIN")   # TRAIN, VAL, TEST (시간순 엄격 분리)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)      # 실제 RL 훈련 시 데모 격리
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="rl_decisions")


# =============================================================================
# DIRECTIVE 051: AI 콘텐츠 연구소 (Autonomous Content Intelligence Lab) 모델
# =============================================================================

class ContentLabSession(Base):
    """지속 관찰 및 콘텐츠 연구 세션 모델 (DIRECTIVE 051)."""
    __tablename__ = "content_lab_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_name: Mapped[str] = mapped_column(String(100), default="중고차 트렌드 연구 세션")
    status: Mapped[str] = mapped_column(String(20), default="IDLE")  # IDLE, RUNNING, PAUSED, STOPPED
    target_keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    processed_video_count: Mapped[int] = mapped_column(Integer, default=0)
    discovered_topic_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_quota_used: Mapped[int] = mapped_column(Integer, default=0)
    daily_quota_limit: Mapped[int] = mapped_column(Integer, default=10000)
    last_checkpoint_json: Mapped[str] = mapped_column(Text, default="{}")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    observed_videos = relationship("ObservedVideo", back_populates="session", cascade="all, delete-orphan")
    topics = relationship("ContentTopicCandidate", back_populates="session", cascade="all, delete-orphan")


class ObservedVideo(Base):
    """관찰된 중고차 경쟁 콘텐츠 메타데이터 (저작권 보호: 원문 대본/영상 보관 금지)."""
    __tablename__ = "observed_videos"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)  # YouTube Video ID
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("content_lab_sessions.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    channel_name: Mapped[str] = mapped_column(String(100), nullable=False)
    published_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    is_shorts: Mapped[bool] = mapped_column(Boolean, default=False)
    matched_keywords_json: Mapped[str] = mapped_column(Text, default="[]")
    analysis_mode: Mapped[str] = mapped_column(String(30), default="METADATA_ONLY")  # METADATA_ONLY, DEEP_VIDEO_UNDERSTANDING
    analysis_result_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("ContentLabSession", back_populates="observed_videos")


class ContentTopicCandidate(Base):
    """독창적 중고차 기획 주제 후보 모델 (차마트 25년 전문성 기반 독립 기획)."""
    __tablename__ = "content_topic_candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("content_lab_sessions.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="수리비/유지비")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    core_question: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_basis: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.85)
    source_reference: Mapped[str] = mapped_column(String(255), default="트렌드 관찰 분석")
    chamart_fit_score: Mapped[float] = mapped_column(Float, default=0.90)  # 차마트 제작 적합도
    fact_check_items_json: Mapped[str] = mapped_column(Text, default="[]")
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    recommendation_reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="DISCOVERED")  # DISCOVERED, RECOMMENDED, SCRIPTED, ARCHIVED
    user_feedback: Mapped[str | None] = mapped_column(String(30), nullable=True)  # LIKE, DISLIKE, ALREADY_COVERED, FACT_ERROR, PRODUCED, LATER
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("ContentLabSession", back_populates="topics")
    scripts = relationship("ContentScriptDraft", back_populates="topic", cascade="all, delete-orphan")


class ContentScriptDraft(Base):
    """독자적인 차마트 숏폼 대본 초안 및 스토리보드 모델 (자동 승인 금지, 승인 해시 보존)."""
    __tablename__ = "content_script_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("content_topic_candidates.id"), nullable=False)
    titles_json: Mapped[str] = mapped_column(Text, default="[]")  # 제목 후보 3종
    target_audience: Mapped[str] = mapped_column(String(100), default="중고차 실구매자")
    planning_intent: Mapped[str] = mapped_column(Text, default="")
    hook_sentence: Mapped[str] = mapped_column(Text, default="")
    full_script: Mapped[str] = mapped_column(Text, default="")
    storyboard_json: Mapped[str] = mapped_column(Text, default="[]")
    fact_check_checklist_json: Mapped[str] = mapped_column(Text, default="[]")
    dealer_questions_json: Mapped[str] = mapped_column(Text, default="[]")
    dealer_answers_json: Mapped[str] = mapped_column(Text, default="{}")
    estimated_duration_sec: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT")  # DRAFT, REVIEWING, APPROVED, REJECTED
    version: Mapped[int] = mapped_column(Integer, default=1)
    approved_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256
    approved_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    approved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    expert_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompts_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # 비디오 생성 프롬프트 패키지
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    topic = relationship("ContentTopicCandidate", back_populates="scripts")


class ContentTopicFeedback(Base):
    """사용자 피드백 감사 모델 (지속적 추천 개선 및 성과 지표 로깅)."""
    __tablename__ = "content_topic_feedbacks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    topic_id: Mapped[str] = mapped_column(String(36), ForeignKey("content_topic_candidates.id"), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(30), nullable=False)
    feedback_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    view_count_recorded: Mapped[int] = mapped_column(Integer, default=0)
    inquiry_count_recorded: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)


# 엔진 및 세션 팩토리
engine = create_engine(DEMO_DB_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def migrate_db_schema() -> None:
    """기존 SQLite DB 테이블에 DIRECTIVE 046-D / 047 확장 컬럼 및 신규 테이블을 안전하게 마이그레이션."""
    import sqlite3
    db_file = DEMO_DB_URL.replace("sqlite:///", "")
    if not os.path.exists(db_file):
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        # 1. vehicles 테이블 마이그레이션
        cursor.execute("PRAGMA table_info(vehicles)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        vehicle_columns = [
            ("ownership_type", "VARCHAR(30) DEFAULT 'CHAMART_OWNED'"),
            ("dealer_id", "VARCHAR(36)"),
            ("vin", "VARCHAR(30)"),
            ("displacement_cc", "INTEGER"),
            ("first_registration_date", "VARCHAR(20)"),
            ("drive_type", "VARCHAR(20) DEFAULT '2WD'"),
            ("interior_color", "VARCHAR(30) DEFAULT '블랙'"),
            ("options_json", "TEXT DEFAULT '[]'"),
            ("accident_history_json", "TEXT DEFAULT '{}'"),
            ("inspection_summary_json", "TEXT DEFAULT '{}'"),
            ("marketing_auth_json", "TEXT DEFAULT '{}'"),
            ("primary_photo_url", "VARCHAR(255)"),
            ("video_status", "VARCHAR(30) DEFAULT 'NONE'"),
            ("is_public", "BOOLEAN DEFAULT 0"),
        ]
        for col_name, col_type in vehicle_columns:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {col_name} {col_type}")

        # 2. vehicle_listings 테이블 마이그레이션 (DIRECTIVE 047 / DIRECTIVE 049 엔카 소싱)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vehicle_listings'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(vehicle_listings)")
            listing_cols = {row[1] for row in cursor.fetchall()}
            listing_columns = [
                ("region", "VARCHAR(50) DEFAULT '장한평'"),
                ("is_janghanpyeong", "BOOLEAN DEFAULT 1"),
                ("data_confidence", "FLOAT DEFAULT 0.95"),
                ("price_drop_amount", "INTEGER DEFAULT 0"),
                ("market_avg_price", "INTEGER DEFAULT 0"),
                ("opportunity_score", "FLOAT DEFAULT 0.0"),
                ("observation_notes", "VARCHAR(255)"),
                ("initial_price", "INTEGER DEFAULT 0"),
                ("price_history_json", "TEXT DEFAULT '[]'"),
                ("location_category", "VARCHAR(50) DEFAULT 'LOCATION_UNKNOWN'"),
                ("identification_reason", "VARCHAR(255)"),
                ("raw_seller_location", "VARCHAR(255)"),
                ("raw_seller_name", "VARCHAR(100)"),
                ("source_confidence", "FLOAT DEFAULT 0.90"),
                ("ingested_at", "DATETIME"),
                ("is_demo", "BOOLEAN DEFAULT 0"),
            ]
            for col_name, col_type in listing_columns:
                if col_name not in listing_cols:
                    cursor.execute(f"ALTER TABLE vehicle_listings ADD COLUMN {col_name} {col_type}")

        # 3. transactions 테이블 마이그레이션 (DIRECTIVE 047 정산 및 DIRECTIVE 049 테스트 격리)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transactions'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(transactions)")
            tx_cols = {row[1] for row in cursor.fetchall()}
            tx_columns = [
                ("dealer_commission_amount", "INTEGER DEFAULT 0"),
                ("chamart_net_profit", "INTEGER DEFAULT 0"),
                ("operating_cost", "INTEGER DEFAULT 0"),
                ("attribution_type", "VARCHAR(30) DEFAULT 'ORGANIC_WALKIN'"),
                ("media_project_id", "VARCHAR(36)"),
                ("is_verified_sale", "BOOLEAN DEFAULT 0"),
                ("is_test_record", "BOOLEAN DEFAULT 0"),
            ]
            for col_name, col_type in tx_columns:
                if col_name not in tx_cols:
                    cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_type}")

        # 4. vehicles 테이블 마이그레이션 (DIRECTIVE 049 is_demo)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vehicles'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(vehicles)")
            v_cols = {row[1] for row in cursor.fetchall()}
            if "is_demo" not in v_cols:
                cursor.execute("ALTER TABLE vehicles ADD COLUMN is_demo BOOLEAN DEFAULT 0")

        # 4. consultations 테이블 마이그레이션 (DIRECTIVE 047 유입 경로 및 중복 문의 식별)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='consultations'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(consultations)")
            cons_cols = {row[1] for row in cursor.fetchall()}
            cons_columns = [
                ("inquiry_source", "VARCHAR(50) DEFAULT 'DIRECT_CALL'"),
                ("media_project_id", "VARCHAR(36)"),
                ("is_duplicate", "BOOLEAN DEFAULT 0"),
            ]
            for col_name, col_type in cons_columns:
                if col_name not in cons_cols:
                    cursor.execute(f"ALTER TABLE consultations ADD COLUMN {col_name} {col_type}")

        # 5. rl_decision_logs 테이블 마이그레이션 (DIRECTIVE 048 실거래 증빙 ID)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rl_decision_logs'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(rl_decision_logs)")
            rl_cols = {row[1] for row in cursor.fetchall()}
            if "verified_transaction_id" not in rl_cols:
                cursor.execute("ALTER TABLE rl_decision_logs ADD COLUMN verified_transaction_id VARCHAR(36)")

        # 6. vehicles 테이블 마이그레이션 (DIRECTIVE 050 마스터 제원 및 다중 플랫폼 연동)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='vehicles'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(vehicles)")
            v_cols = {row[1] for row in cursor.fetchall()}
            v_columns = [
                ("manufacturer", "VARCHAR(50)"),
                ("trim", "VARCHAR(100)"),
                ("body_type", "VARCHAR(30) DEFAULT '세단'"),
                ("recon_cost", "INTEGER DEFAULT 0"),
                ("sales_conditions", "VARCHAR(255)"),
                ("ad_description", "TEXT"),
                ("ad_highlights", "TEXT"),
                ("ad_notices", "TEXT"),
                ("platform_ad_copies_json", "TEXT DEFAULT '{}'"),
                ("options_structured_json", "TEXT DEFAULT '[]'"),
                ("condition_detail_json", "TEXT DEFAULT '{}'"),
                ("publishing_status", "VARCHAR(30) DEFAULT 'DRAFT'"),
                ("platform_readiness_json", "TEXT DEFAULT '{}'"),
            ]
            for col_name, col_type in v_columns:
                if col_name not in v_cols:
                    cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {col_name} {col_type}")

        # 7. platform_publishing_records 테이블 생성 (DIRECTIVE 050)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS platform_publishing_records (
                id VARCHAR(36) PRIMARY KEY,
                vehicle_id VARCHAR(36) NOT NULL,
                platform VARCHAR(30) NOT NULL,
                publishing_status VARCHAR(30) DEFAULT 'DRAFT',
                is_ready BOOLEAN DEFAULT 0,
                missing_fields_json TEXT DEFAULT '[]',
                warnings_json TEXT DEFAULT '[]',
                mapped_payload_json TEXT DEFAULT '{}',
                external_listing_id VARCHAR(50),
                last_validated_at DATETIME,
                last_exported_at DATETIME,
                error_message TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                FOREIGN KEY (vehicle_id) REFERENCES vehicles(id) ON DELETE CASCADE
            )
        """)

        # 8. customers 테이블 마이그레이션 (DIRECTIVE 050-C 명함 OCR 및 추가 정보)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(customers)")
            c_cols = {row[1] for row in cursor.fetchall()}
            c_columns = [
                ("job_title", "VARCHAR(50)"),
                ("company_name", "VARCHAR(100)"),
                ("company_address", "VARCHAR(255)"),
                ("company_phone", "VARCHAR(30)"),
                ("email", "VARCHAR(100)"),
                ("source", "VARCHAR(50) DEFAULT 'DIRECT'"),
                ("source_image_url", "VARCHAR(500)"),
                ("ai_confidence", "FLOAT"),
            ]
            for col_name, col_type in c_columns:
                if col_name not in c_cols:
                    cursor.execute(f"ALTER TABLE customers ADD COLUMN {col_name} {col_type}")

        # 9. document_reviews 테이블 마이그레이션 (DIRECTIVE 050-C 거래서류 검토 및 7대 라이프사이클)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='document_reviews'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(document_reviews)")
            doc_cols = {row[1] for row in cursor.fetchall()}
            doc_columns = [
                ("status", "VARCHAR(30) DEFAULT 'NEEDS_REVIEW'"),
                ("document_type", "VARCHAR(50) DEFAULT 'CONTRACT'"),
                ("matched_vehicle_id", "VARCHAR(36)"),
                ("matched_customer_id", "VARCHAR(36)"),
                ("extracted_amount", "INTEGER DEFAULT 0"),
                ("has_official_seal", "BOOLEAN DEFAULT 0"),
                ("ai_confidence", "FLOAT DEFAULT 0.0"),
                ("processing_error", "TEXT"),
                ("created_transaction_id", "VARCHAR(36)"),
            ]
            for col_name, col_type in doc_columns:
                if col_name not in doc_cols:
                    cursor.execute(f"ALTER TABLE document_reviews ADD COLUMN {col_name} {col_type}")

        # 10. gemini_usage_logs 테이블 생성 (DIRECTIVE 050-C 사용량 및 비용 감사)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gemini_usage_logs (
                id VARCHAR(36) PRIMARY KEY,
                task_type VARCHAR(50) NOT NULL,
                model_used VARCHAR(50) NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                candidate_tokens INTEGER DEFAULT 0,
                estimated_cost_usd FLOAT DEFAULT 0.0,
                success BOOLEAN DEFAULT 1,
                error_message TEXT,
                execution_time_ms INTEGER DEFAULT 0,
                created_at DATETIME
            )
        """)

        # 11. DIRECTIVE 051 AI 콘텐츠 연구소 테이블들 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_lab_sessions (
                id VARCHAR(36) PRIMARY KEY,
                session_name VARCHAR(100),
                status VARCHAR(20) DEFAULT 'IDLE',
                target_keywords_json TEXT DEFAULT '[]',
                processed_video_count INTEGER DEFAULT 0,
                discovered_topic_count INTEGER DEFAULT 0,
                daily_quota_used INTEGER DEFAULT 0,
                daily_quota_limit INTEGER DEFAULT 10000,
                last_checkpoint_json TEXT DEFAULT '{}',
                last_error TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS observed_videos (
                id VARCHAR(100) PRIMARY KEY,
                session_id VARCHAR(36),
                title VARCHAR(255) NOT NULL,
                channel_name VARCHAR(100) NOT NULL,
                published_at VARCHAR(50),
                view_count INTEGER DEFAULT 0,
                duration_seconds INTEGER DEFAULT 0,
                is_shorts BOOLEAN DEFAULT 0,
                matched_keywords_json TEXT DEFAULT '[]',
                analysis_mode VARCHAR(30) DEFAULT 'METADATA_ONLY',
                analysis_result_json TEXT DEFAULT '{}',
                created_at DATETIME
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_topic_candidates (
                id VARCHAR(36) PRIMARY KEY,
                session_id VARCHAR(36),
                category VARCHAR(50) DEFAULT '수리비/유지비',
                title VARCHAR(200) NOT NULL,
                core_question TEXT NOT NULL,
                evidence_basis TEXT NOT NULL,
                confidence FLOAT DEFAULT 0.85,
                source_reference VARCHAR(255),
                chamart_fit_score FLOAT DEFAULT 0.90,
                fact_check_items_json TEXT DEFAULT '[]',
                is_duplicate BOOLEAN DEFAULT 0,
                recommendation_reason TEXT,
                status VARCHAR(30) DEFAULT 'DISCOVERED',
                user_feedback VARCHAR(30),
                created_at DATETIME
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_script_drafts (
                id VARCHAR(36) PRIMARY KEY,
                topic_id VARCHAR(36) NOT NULL,
                titles_json TEXT DEFAULT '[]',
                target_audience VARCHAR(100),
                planning_intent TEXT,
                hook_sentence TEXT,
                full_script TEXT,
                storyboard_json TEXT DEFAULT '[]',
                fact_check_checklist_json TEXT DEFAULT '[]',
                dealer_questions_json TEXT DEFAULT '[]',
                dealer_answers_json TEXT DEFAULT '{}',
                estimated_duration_sec INTEGER DEFAULT 30,
                status VARCHAR(30) DEFAULT 'DRAFT',
                version INTEGER DEFAULT 1,
                approved_hash VARCHAR(64),
                approved_by VARCHAR(50),
                approved_at DATETIME,
                expert_feedback TEXT,
                prompts_json TEXT,
                created_at DATETIME,
                updated_at DATETIME
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS content_topic_feedbacks (
                id VARCHAR(36) PRIMARY KEY,
                topic_id VARCHAR(36) NOT NULL,
                feedback_type VARCHAR(30) NOT NULL,
                feedback_reason TEXT,
                view_count_recorded INTEGER DEFAULT 0,
                inquiry_count_recorded INTEGER DEFAULT 0,
                created_at DATETIME
            )
        """)

        conn.commit()
    finally:
        conn.close()


def init_demo_db() -> None:
    """데모 데이터베이스 테이블 생성, 마이그레이션 및 DIRECTIVE 046-D 매물 시딩."""
    migrate_db_schema()
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        # 1. 지점 생성 확인 및 확보
        jh_branch = session.query(Branch).filter(Branch.name.contains("장한평")).first()
        if not jh_branch:
            jh_branch = Branch(
                name="차마트 장한평 본사",
                region="서울 동대문구",
                address="서울특별시 동대문구 천호대로 329",
                is_headquarters=True,
            )
            sw_branch = Branch(
                name="차마트 수원 지점 (확장 예정 거점)",
                region="경기 수원시",
                address="경기도 수원시 권선구 평동로 79 (확장 계획 시연용 가상 주소)",
                is_headquarters=False,
            )
            session.add_all([jh_branch, sw_branch])
            session.flush()
        else:
            sw_branch = session.query(Branch).filter(Branch.name.contains("수원")).first()
            if not sw_branch:
                sw_branch = Branch(
                    name="차마트 수원 지점 (확장 예정 거점)",
                    region="경기 수원시",
                    address="경기도 수원시 권선구 평동로 79 (확장 계획 시연용 가상 주소)",
                    is_headquarters=False,
                )
                session.add(sw_branch)
                session.flush()

        # 2. 제휴 딜러 시딩 (DIRECTIVE 046-D)
        dealer_gaon = session.query(Dealer).filter(Dealer.dealership_name.contains("가온")).first()
        if not dealer_gaon:
            dealer_gaon = Dealer(
                branch_id=jh_branch.id,
                name="김민우",
                dealership_name="장한평 가온모터스",
                phone="010-3344-5566",
                partnership_status="ACTIVE",
                contract_date="2026-09-01",
            )
            dealer_woori = Dealer(
                branch_id=jh_branch.id,
                name="박진우",
                dealership_name="장한평 우리상사",
                phone="010-8877-6655",
                partnership_status="ACTIVE",
                contract_date="2026-08-15",
            )
            dealer_independent = Dealer(
                branch_id=jh_branch.id,
                name="최동현",
                dealership_name="장한평 제일오토",
                phone="010-4455-6677",
                partnership_status="IN_REVIEW",
                contract_date=None,
            )
            session.add_all([dealer_gaon, dealer_woori, dealer_independent])
            session.flush()
        else:
            dealer_woori = session.query(Dealer).filter(Dealer.dealership_name.contains("우리")).first()
            dealer_independent = session.query(Dealer).filter(Dealer.dealership_name.contains("제일")).first()

        # 3. 기존 차량들 마스터 데이터 보강 (미확인 정보 자동 주입 차단: DIRECTIVE 049)
        vehicles = session.query(Vehicle).all()
        for v in vehicles:
            if not v.ownership_type:
                v.ownership_type = "CHAMART_OWNED"
            # DIRECTIVE 049: 미확인 VIN, 배기량, 구동방식, 옵션 등을 가상으로 자동 생성하지 않음 (NULL / 빈값 엄격 보존)
            if not v.accident_history_json or v.accident_history_json == "{}":
                # DIRECTIVE 048 P0-1: 증빙 없는 차량의 임의 무사고 위조 원천 방지
                v.accident_history_json = json.dumps({
                    "accident_state": "UNCHECKED",
                    "frame_damage": "미확인",
                    "outer_panel_exchange": "미확인",
                    "flood_damage": "미확인",
                    "total_loss": "미확인",
                    "theft_history": "미확인",
                    "insurance_my_damage_count": 0,
                    "insurance_my_damage_amount": 0,
                    "insurance_other_damage_count": 0,
                    "insurance_other_damage_amount": 0,
                    "verified_source": "카히스토리 미조회 (성능점검 대기)",
                    "verified_at": None
                }, ensure_ascii=False)
            if not v.inspection_summary_json or v.inspection_summary_json == "{}":
                v.inspection_summary_json = json.dumps({
                    "inspector": "미지정 (점검 대기)",
                    "inspection_date": None,
                    "leak_status": "미확인",
                    "brake_system": "미확인",
                    "suspension": "미확인",
                    "overall_grade": "미조회"
                }, ensure_ascii=False)
            if not v.marketing_auth_json or v.marketing_auth_json == "{}":
                v.marketing_auth_json = json.dumps({
                    "authorized": False,
                    "video_allowed": False,
                    "photo_allowed": False,
                    "authorized_by": None,
                    "expires_at": None,
                    "allowed_platforms": [],
                    "note": "제휴 계약 및 마케팅 권한 미확인 상태"
                }, ensure_ascii=False)
            if not v.primary_photo_url:
                v.primary_photo_url = "/uploads/vehicles/demo_car_front.jpg"

        # 특정 차량 소유구분 및 딜러 연결 설정
        # v1 (그랜저): 차마트 직영 (CHAMART_OWNED)
        v_grn = session.query(Vehicle).filter(Vehicle.model_name.contains("그랜저")).first()
        if v_grn:
            v_grn.ownership_type = "CHAMART_OWNED"
            v_grn.video_status = "IN_PRODUCTION"

        # v2 (스포티지): 제휴 딜러 승인 매물 (PARTNER_APPROVED)
        v_spt = session.query(Vehicle).filter(Vehicle.model_name.contains("스포티지")).first()
        if v_spt:
            v_spt.ownership_type = "PARTNER_APPROVED"
            v_spt.dealer_id = dealer_gaon.id
            v_spt.marketing_auth_json = json.dumps({
                "authorized": True,
                "video_allowed": True,
                "photo_allowed": True,
                "authorized_by": "가온모터스 김민우 딜러 협약",
                "authorized_at": "2026-10-22",
                "expires_at": "2026-11-30",
                "allowed_platforms": ["YOUTUBE", "SHORTS", "REELS"]
            }, ensure_ascii=False)
            v_spt.video_status = "REQUESTED"

        # v4 (아반떼): 제휴 딜러 승인 매물 (PARTNER_APPROVED)
        v_avn = session.query(Vehicle).filter(Vehicle.model_name.contains("아반떼")).first()
        if v_avn:
            v_avn.ownership_type = "PARTNER_APPROVED"
            v_avn.dealer_id = dealer_woori.id
            v_avn.video_status = "IN_PRODUCTION"

        # 4. 신규 관측 매물 및 후보 매물 추가 (MARKET_OBSERVED, PARTNER_CANDIDATE)
        v_obs = session.query(Vehicle).filter(Vehicle.ownership_type == "MARKET_OBSERVED").first()
        if not v_obs:
            v_obs = Vehicle(
                branch_id=jh_branch.id,
                plate_number="33오 9988",
                model_name="기아 K8 2.5 가솔린 노블레스 라이트",
                year=2023,
                mileage=24000,
                fuel_type="가솔린",
                transmission="오토",
                color="오로라 블랙 펄",
                purchase_price=0,
                target_price=2950,
                status="FOR_SALE",
                ownership_type="MARKET_OBSERVED",  # 시장 관측 매물 (권한 없음)
                dealer_id=None,
                vin="KNAFE41BDP9988123",
                displacement_cc=2497,
                drive_type="2WD",
                interior_color="브라운",
                options_json=json.dumps(["내비게이션", "후방카메라", "열선시트"], ensure_ascii=False),
                accident_history_json=json.dumps({"accident_state": "UNKNOWN", "verified_source": "미확인(엔카 관측 매물)"}, ensure_ascii=False),
                inspection_summary_json=json.dumps({"inspector": "미확인", "overall_grade": "미조회"}, ensure_ascii=False),
                marketing_auth_json=json.dumps({
                    "authorized": False,
                    "video_allowed": False,
                    "photo_allowed": False,
                    "authorized_by": None,
                    "note": "장한평 엔카 등록 매물 관측 데이터 (차마트 광고권한 미확인)"
                }, ensure_ascii=False),
                primary_photo_url="/uploads/vehicles/demo_k8_front.jpg",
                video_status="NONE",
            )
            session.add(v_obs)
            session.flush()

            # 외부 Listing 추가 (엔카 매물 연계)
            listing1 = VehicleListing(
                vehicle_id=v_obs.id,
                platform="ENCAR",
                listing_id="encar_39821092",
                listing_url="https://www.encar.com/dc/dc_cardetailview.do?carid=39821092",
                advertised_price=2950,
                listing_status="ACTIVE",
                is_demo=True,
            )
            # 동일 차량 KB차차차 매물도 연계 (다중 플랫폼 관측)
            listing2 = VehicleListing(
                vehicle_id=v_obs.id,
                platform="KB_CHACHACHA",
                listing_id="kb_88291039",
                listing_url="https://www.kbchachacha.com/public/car/detail.kbc?carSeq=88291039",
                advertised_price=2980,
                listing_status="ACTIVE",
                region="장한평",
                is_janghanpyeong=True,
                data_confidence=0.96,
                price_drop_amount=170,
                market_avg_price=3150,
                opportunity_score=87.5,
                observation_notes="장한평 단지 내 KB차차차 실매물 확인",
                is_demo=True,
            )
            session.add_all([listing1, listing2])

        # 4-1. 전국 시세 비교용 외부 관측 매물 (장한평 외 지역)
        v_sw_obs = session.query(Vehicle).filter(Vehicle.plate_number == "77라 4455").first()
        if not v_sw_obs:
            v_sw_obs = Vehicle(
                branch_id=sw_branch.id,
                plate_number="77라 4455",
                model_name="기아 K8 2.5 가솔린 노블레스",
                year=2023,
                mileage=31000,
                fuel_type="가솔린",
                transmission="오토",
                color="스노우 화이트 펄",
                purchase_price=0,
                target_price=3080,
                status="FOR_SALE",
                ownership_type="MARKET_OBSERVED",
                dealer_id=None,
                vin="KNAFE41BDP7744551",
                displacement_cc=2497,
                drive_type="2WD",
                interior_color="블랙",
                marketing_auth_json=json.dumps({"authorized": False, "video_allowed": False}, ensure_ascii=False),
                video_status="NONE",
            )
            session.add(v_sw_obs)
            session.flush()

            listing_sw = VehicleListing(
                vehicle_id=v_sw_obs.id,
                platform="ENCAR",
                listing_id="encar_sw_102938",
                listing_url="https://www.encar.com/dc/dc_cardetailview.do?carid=102938",
                advertised_price=3080,
                listing_status="ACTIVE",
                region="경기 수원",
                is_janghanpyeong=False,  # 전국 시세 참고용 (장한평 외 매물)
                data_confidence=0.92,
                price_drop_amount=50,
                market_avg_price=3150,
                opportunity_score=74.0,
                observation_notes="수원 도이치오토월드 매물 (전국 시세 기준점)",
                is_demo=True,
            )
            session.add(listing_sw)

        # 기존 데모 리스팅에 is_demo=True 보정
        demo_listing_ids = ["encar_39821092", "kb_88291039", "encar_sw_102938"]
        for dl in session.query(VehicleListing).filter(VehicleListing.listing_id.in_(demo_listing_ids)).all():
            dl.is_demo = True

        # 4-2. 기존 관측 리스팅의 DIRECTIVE 047 기회 점수 및 시세 보정 (Backfill)
        existing_listings = session.query(VehicleListing).all()
        for l in existing_listings:
            if getattr(l, "opportunity_score", 0.0) == 0.0:
                if l.platform == "KB_CHACHACHA":
                    l.opportunity_score = 88.5
                    l.price_drop_amount = 170
                    l.market_avg_price = 3150
                    l.region = "장한평"
                    l.is_janghanpyeong = True
                    l.data_confidence = 0.96
                elif "sw" in l.listing_id:
                    l.opportunity_score = 74.0
                    l.price_drop_amount = 50
                    l.market_avg_price = 3150
                    l.region = "경기 수원"
                    l.is_janghanpyeong = False
                    l.data_confidence = 0.92
                else:
                    l.opportunity_score = 82.0
                    l.price_drop_amount = 200
                    l.market_avg_price = 3150
                    l.region = "장한평"
                    l.is_janghanpyeong = True
                    l.data_confidence = 0.98

        v_cand = session.query(Vehicle).filter(Vehicle.ownership_type == "PARTNER_CANDIDATE").first()
        if not v_cand:
            v_cand = Vehicle(
                branch_id=jh_branch.id,
                plate_number="55누 1122",
                model_name="현대 쏘나타 디 엣지 1.6 터보 익스클루시브",
                year=2024,
                mileage=9500,
                fuel_type="가솔린",
                transmission="오토",
                color="세레니티 화이트",
                purchase_price=0,
                target_price=2680,
                status="FOR_SALE",
                ownership_type="PARTNER_CANDIDATE",  # 협력 검토 대상 타 딜러 매물
                dealer_id=dealer_independent.id,
                vin="KMHE41BDP1122345",
                displacement_cc=1598,
                drive_type="2WD",
                interior_color="다크 그레이",
                options_json=json.dumps(["현대스마트센스", "파노라마 선루프", "12.3인치 내비"], ensure_ascii=False),
                accident_history_json=json.dumps({"accident_state": "CLEAN", "verified_source": "딜러 고지 사항"}, ensure_ascii=False),
                inspection_summary_json=json.dumps({"inspector": "공인성능장", "overall_grade": "A"}, ensure_ascii=False),
                marketing_auth_json=json.dumps({
                    "authorized": False,
                    "video_allowed": False,
                    "photo_allowed": False,
                    "authorized_by": None,
                    "note": "제일오토 딜러 협의 진행 중 (아직 광고 권한 미승인)"
                }, ensure_ascii=False),
                primary_photo_url="/uploads/vehicles/demo_sonata_front.jpg",
                video_status="NONE",
            )
            session.add(v_cand)

        # 5. 부위별 하자 시딩 (VehicleDefect)
        if session.query(VehicleDefect).count() == 0 and v_spt:
            defect1 = VehicleDefect(
                vehicle_id=v_spt.id,
                part_name="우측 뒤휀더",
                defect_type="스크래치 / 도장 손상",
                severity="경미",
                action_status="REPAIR_SCHEDULED",
                estimated_repair_cost=15,
                notes="고객 고지 및 출고 전 부분 도색 예정",
            )
            session.add(defect1)

        # 6. 차량 사진 자산 시딩 (VehiclePhoto)
        if session.query(VehiclePhoto).count() == 0 and v_grn:
            p1 = VehiclePhoto(
                vehicle_id=v_grn.id,
                photo_url="/uploads/vehicles/granger_front.jpg",
                thumb_url="/uploads/vehicles/granger_front_thumb.jpg",
                category="EXTERIOR",
                sort_order=1,
                is_primary=True,
                allow_video_use=True,
                caption="전면 정면 45도 외관",
            )
            p2 = VehiclePhoto(
                vehicle_id=v_grn.id,
                photo_url="/uploads/vehicles/granger_interior.jpg",
                thumb_url="/uploads/vehicles/granger_interior_thumb.jpg",
                category="INTERIOR",
                sort_order=2,
                is_primary=False,
                allow_video_use=True,
                caption="운전석 및 대시보드 실내",
            )
            p3 = VehiclePhoto(
                vehicle_id=v_grn.id,
                photo_url="/uploads/vehicles/granger_engine.jpg",
                thumb_url="/uploads/vehicles/granger_engine_thumb.jpg",
                category="ENGINE",
                sort_order=3,
                is_primary=False,
                allow_video_use=True,
                caption="엔진룸 및 주요 장치",
            )
            session.add_all([p1, p2, p3])

        # 7. 제휴 딜러 권한 원장 시딩 (DealerRightsLedger - DIRECTIVE 047)
        if session.query(DealerRightsLedger).count() == 0 and v_spt and dealer_gaon:
            rights_spt = DealerRightsLedger(
                vehicle_id=v_spt.id,
                dealer_id=dealer_gaon.id,
                sale_allowed=True,
                photo_allowed=True,
                video_allowed=True,
                allowed_channels_json=json.dumps(["YOUTUBE", "INSTAGRAM", "TIKTOK"], ensure_ascii=False),
                valid_until="2026-12-31",
                is_revoked=False,
                approved_by="가온모터스 김민우 딜러 정식 계약",
                dealer_commission_pct=4.5,
                chamart_share_pct=15.0,
            )
            session.add(rights_spt)

        # 8. 거래 기여도 및 상담 유입 경로 보강 (DIRECTIVE 047 / DIRECTIVE 048 / DIRECTIVE 049)
        # 모든 기존 데모 거래에 is_demo=True 명시 및 테스트 가상 거래 격리
        all_txs = session.query(Transaction).all()
        for t in all_txs:
            if t.is_demo is None:
                t.is_demo = True
            # DIRECTIVE 049: 테스트에서 생성된 가상 거래 격리 (실제 매출 오염 방지)
            if t.party_name in ["실구매자", "계약진행고객", "실거래고객", "데모고객"]:
                t.is_test_record = True
                t.is_verified_sale = False

        tx_sample = session.query(Transaction).filter(Transaction.transaction_type == "SALE").first()
        if tx_sample:
            tx_sample.attribution_type = "AI_VIDEO"
            tx_sample.dealer_commission_amount = 85
            tx_sample.chamart_net_profit = 125
            tx_sample.operating_cost = 20
            tx_sample.settlement_status = "SETTLED"
            tx_sample.is_verified_sale = True
            tx_sample.is_demo = True

        consultation_sample = session.query(Consultation).first()
        if consultation_sample and consultation_sample.inquiry_source == "DIRECT_CALL":
            consultation_sample.inquiry_source = "YOUTUBE_SHORTS"
            consultation_sample.is_duplicate = False

        # 9. 강화학습(RL) 오프라인 의사결정 로그 시딩 (RLDecisionLog - DIRECTIVE 047)
        if session.query(RLDecisionLog).count() == 0:
            # 의사결정 로그 1: 스포티지 - 영상 제작 제안 Action -> 판매 완결 -> 양의 보상 확정 (Train Split)
            rl_log1 = RLDecisionLog(
                timestamp=datetime.datetime(2026, 9, 10, 14, 30),
                policy_version="v1.0-rule_baseline",
                vehicle_id=v_spt.id if v_spt else None,
                state_json=json.dumps({
                    "target_price": 2450,
                    "market_avg_price": 2600,
                    "price_discount_ratio": 0.0577,
                    "year": 2022,
                    "mileage": 35000,
                    "accident_count": 0,
                    "defect_count": 1,
                    "estimated_repair_cost": 15,
                    "region": "장한평",
                    "data_confidence": 0.98,
                    "rights_video_allowed": True
                }, ensure_ascii=False),
                action="PROPOSE_VIDEO",
                action_prob=0.92,
                action_details_json=json.dumps({"channels": ["YOUTUBE", "INSTAGRAM"], "budget_won": 200000}, ensure_ascii=False),
                reward=105.0,  # 순공헌이익 기반 Reward (125만 순익 - 20만 제작비)
                reward_details_json=json.dumps({
                    "fee_revenue": 85,
                    "operating_cost": 20,
                    "days_to_sell": 14,
                    "verified_contribution": 1.0,
                    "net_reward": 105.0
                }, ensure_ascii=False),
                is_censored=False,
                split="TRAIN",
                is_demo=True,
            )

            # 의사결정 로그 2: K8 관측 매물 - 권한 없음으로 관망/딜러검토 Action -> 관측 진행 중 (Right Censored)
            rl_log2 = RLDecisionLog(
                timestamp=datetime.datetime(2026, 10, 20, 11, 15),
                policy_version="v1.0-rule_baseline",
                vehicle_id=v_obs.id if v_obs else None,
                state_json=json.dumps({
                    "target_price": 2950,
                    "market_avg_price": 3150,
                    "price_discount_ratio": 0.0635,
                    "year": 2023,
                    "mileage": 24000,
                    "accident_count": 0,
                    "defect_count": 0,
                    "estimated_repair_cost": 0,
                    "region": "장한평",
                    "data_confidence": 0.96,
                    "rights_video_allowed": False
                }, ensure_ascii=False),
                action="REQUEST_DEALER_REVIEW",
                action_prob=0.88,
                action_details_json=json.dumps({"target_dealership": "장한평 엔카 등록 상사", "priority": "HIGH"}, ensure_ascii=False),
                reward=None,  # 아직 판매/계약 미체결 (Censored)
                reward_details_json=json.dumps({"status": "OBSERVING", "days_observed": 5}, ensure_ascii=False),
                is_censored=True,
                split="VAL",
                is_demo=True,
            )
            session.add_all([rl_log1, rl_log2])

        session.commit()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 의존성 주입용 세션 제너레이터."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
