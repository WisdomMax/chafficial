"""차마트(CHAMART) 통합 운영 플랫폼 데이터베이스 모델 및 세션 관리.

DIRECTIVE 045 명세 준수:
- 차마트 본사(장한평) 및 지점(수원) 다중 거점 모델 지원
- 실제 작동 4대 영역: 차량 관리, 고객 CRM, 거래/정산, 영상 스튜디오
- AI 서류 인식 검토 대기열 및 미래 연동(텔레그램, SMS, 카매니저) 모델
- 데모 데이터 분리: data/chamart/chamart_platform_demo.db 에 격리 보존
"""

from __future__ import annotations

import datetime
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

# 데이터 저장 디렉토리
DB_DIR = Path("data/chamart")
DB_DIR.mkdir(parents=True, exist_ok=True)
DEMO_DB_PATH = DB_DIR / "chamart_platform_demo.db"
DEMO_DB_URL = f"sqlite:///{DEMO_DB_PATH.absolute()}"


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

    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    timeline_json: Mapped[str] = mapped_column(Text, default="[]")  # 상태 변경 이력 리스트 JSON
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    branch = relationship("Branch", back_populates="vehicles")
    dealer = relationship("Dealer", back_populates="vehicles")
    listings = relationship("VehicleListing", back_populates="vehicle", cascade="all, delete-orphan")
    defects = relationship("VehicleDefect", back_populates="vehicle", cascade="all, delete-orphan")
    photos = relationship("VehiclePhoto", back_populates="vehicle", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="vehicle")
    media_projects = relationship("MediaProject", back_populates="vehicle")


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
    """엔카, KB차차차 등 외부 플랫폼 광고 매물 연동 모델 (DIRECTIVE 046-D)."""
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

    vehicle = relationship("Vehicle", back_populates="listings")


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
    """고객 CRM 모델."""
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
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    customer = relationship("Customer", back_populates="consultations")


class Transaction(Base):
    """거래·계약 관리 모델."""
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
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="transactions")


class DocumentReview(Base):
    """AI 서류 인식 대기열 모델."""
    __tablename__ = "document_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)  # TRANSFER_CERTIFICATE, SALE_CONTRACT, INSPECTION_RECORD, SETTLEMENT_SHEET
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_data_json: Mapped[str] = mapped_column(Text, default="{}")
    review_status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED
    approved_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
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


# 엔진 및 세션 팩토리
engine = create_engine(DEMO_DB_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def migrate_db_schema() -> None:
    """기존 SQLite DB 테이블에 DIRECTIVE 046-D 확장 컬럼 및 신규 테이블을 안전하게 마이그레이션."""
    import sqlite3
    db_file = DEMO_DB_URL.replace("sqlite:///", "")
    if not os.path.exists(db_file):
        return

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    try:
        # vehicles 테이블 컬럼 목록 확인
        cursor.execute("PRAGMA table_info(vehicles)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        new_columns = [
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
        ]

        for col_name, col_type in new_columns:
            if col_name not in existing_cols:
                cursor.execute(f"ALTER TABLE vehicles ADD COLUMN {col_name} {col_type}")

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

        # 3. 기존 차량들 마스터 데이터 보강 및 4대 구분 지정
        vehicles = session.query(Vehicle).all()
        for v in vehicles:
            if not v.ownership_type:
                v.ownership_type = "CHAMART_OWNED"
            if not v.vin:
                v.vin = f"KNAGE41BBP{abs(hash(v.plate_number)) % 1000000:07d}"
            if not v.displacement_cc:
                v.displacement_cc = 1999
            if not v.drive_type:
                v.drive_type = "2WD"
            if not v.options_json or v.options_json == "[]":
                v.options_json = json.dumps(["스마트 크루즈 컨트롤", "통풍시트", "열선 스티어링 휠", "어라운드 뷰", "헤드업 디스플레이"], ensure_ascii=False)
            if not v.accident_history_json or v.accident_history_json == "{}":
                v.accident_history_json = json.dumps({
                    "accident_state": "CLEAN",
                    "frame_damage": "NONE",
                    "outer_panel_exchange": "NONE",
                    "flood_damage": "NONE",
                    "total_loss": "NONE",
                    "theft_history": "NONE",
                    "insurance_my_damage_count": 0,
                    "insurance_my_damage_amount": 0,
                    "insurance_other_damage_count": 0,
                    "insurance_other_damage_amount": 0,
                    "verified_source": "카히스토리(보험개발원) 전산 검증",
                    "verified_at": "2026-10-25"
                }, ensure_ascii=False)
            if not v.inspection_summary_json or v.inspection_summary_json == "{}":
                v.inspection_summary_json = json.dumps({
                    "inspector": "한국교통안전공단 공인성능장",
                    "inspection_date": "2026-10-24",
                    "leak_status": "양호(누유없음)",
                    "brake_system": "양호",
                    "suspension": "양호",
                    "overall_grade": "A+"
                }, ensure_ascii=False)
            if not v.marketing_auth_json or v.marketing_auth_json == "{}":
                v.marketing_auth_json = json.dumps({
                    "authorized": True,
                    "video_allowed": True,
                    "photo_allowed": True,
                    "authorized_by": "차마트 본사 직영관리",
                    "authorized_at": "2026-10-20",
                    "expires_at": "2026-12-31",
                    "allowed_platforms": ["YOUTUBE", "SHORTS", "REELS", "TELEGRAM"]
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
            )
            # 동일 차량 KB차차차 매물도 연계 (다중 플랫폼 관측)
            listing2 = VehicleListing(
                vehicle_id=v_obs.id,
                platform="KB_CHACHACHA",
                listing_id="kb_88291039",
                listing_url="https://www.kbchachacha.com/public/car/detail.kbc?carSeq=88291039",
                advertised_price=2980,
                listing_status="ACTIVE",
            )
            session.add_all([listing1, listing2])

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

        session.commit()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 의존성 주입용 세션 제너레이터."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
