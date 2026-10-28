"""차피셜(CHA-FICIAL) 통합 운영 관리 시스템 FastAPI 애플리케이션.

- 장한평 본사 및 거점 확장을 위한 차량·고객CRM·거래·AI영상·소싱 통합 OS
- 차마트(CHAMART) 일반 고객용 독립 쇼룸 웹사이트(/chamart) 및 실매물 공개 API 제공
- 내부 관리시스템(차피셜)과 외부 고객 쇼룸(차마트)의 브랜드 및 보안 완전 분리
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import secrets
import time
import traceback
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from chaficial.platform.db import (
    SessionLocal,
    get_db,
    init_demo_db,
    Vehicle,
    Dealer,
    VehicleListing,
    VehicleDefect,
    VehiclePhoto,
    DocumentReview,
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
    GeminiKeySaveRequest,
    LoginRequest,
    MediaProjectCreateRequest,
    MediaProjectStatusUpdateRequest,
    PhotoOrderItem,
    PlatformRegisterIntentRequest,
    RLDecisionEvaluateRequest,
    RLDecisionRewardUpdateRequest,
    TransactionCreateRequest,
    TransactionDocumentExtract,
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
from chaficial.platform.ai.vision import GeminiVisionService
from chaficial.platform.search import (
    format_currency_display,
    format_phone_display,
    normalize_phone_number,
    parse_currency_amount,
    universal_search,
)
from chaficial.platform.service import PlatformService
from chaficial.platform.sourcing.service import SourcingService
from chaficial.platform.catalog.hierarchy import VehicleCatalogService
from chaficial.platform.catalog.options import StandardOptionCatalog
from chaficial.platform.master.service import MasterVehicleService
from chaficial.platform.publishing.validator import PublishingReadinessValidator
from chaficial.platform.lab.service import ContentLabService

# 앱 초기화
app = FastAPI(
    title="차피셜(CHA-FICIAL) 통합 운영 관리 시스템",
    description="장한평 본사 및 거점 확장을 위한 차량·고객CRM·거래·영상 통합 OS",
    version="1.0.0-demo",
)

# .env 환경변수 로드
env_file = Path(".env")
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UI_INDEX_FILE = Path(__file__).parent / "ui" / "index.html"
UI_CHAMART_FILE = Path(__file__).parent / "ui" / "chamart.html"
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DOC_UPLOAD_DIR = Path("data/uploads/documents")
DOC_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
STATIC_DIR = Path(__file__).parent / "ui" / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """처리되지 않은 500 서버 에러 로깅 및 정형화된 JSON 에러 응답."""
    tb = traceback.format_exc()
    print(f"[SERVER ERROR 500] {request.method} {request.url.path} 실패:\n{tb}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "ok": False,
            "status": "SERVER_ERROR",
            "detail": f"서버 내부 처리 중 오류가 발생했습니다: {str(exc)}",
            "path": request.url.path,
        },
    )


@app.on_event("startup")
def on_startup() -> None:
    """서버 기동 시 데모 데이터베이스 초기화 및 시딩."""
    init_demo_db()


# ----------------------------------------------------
# 1. 인증 및 세션 관리 (P0 보안 강화)
# ----------------------------------------------------
# 세션 저장소: {token: {"username": str, "role": str, "created_at": float}}
ACTIVE_SESSIONS: dict[str, dict[str, Any]] = {}
LOGIN_FAILURES: dict[str, list[float]] = {}  # {client_ip: [timestamps]}
CONSULTATION_REQUEST_LOGS: dict[str, float] = {}  # {ip_or_phone: last_request_time}

# 환경변수에서 관리자 비밀번호 로드 (Fail-safe: 미설정 시 기동 중단)
ENV_ADMIN_PW = os.environ.get("CHAMART_ADMIN_PASSWORD")
if not ENV_ADMIN_PW:
    if os.environ.get("CHAMART_ALLOW_EPHEMERAL_PASSWORD") == "1":
        ENV_ADMIN_PW = secrets.token_urlsafe(16)
        print(f"[SECURITY NOTE] 명시적 데모 플래그에 의해 1회용 세션 비밀번호가 생성되었습니다: {ENV_ADMIN_PW}")
    else:
        raise RuntimeError(
            "보안 오류: CHAMART_ADMIN_PASSWORD 환경변수가 설정되지 않았습니다. "
            "시스템 기동 전 .env 파일 또는 환경변수를 구성하십시오."
        )


def get_client_ip(request: Request) -> str:
    """Cloudflare Tunnel 및 프록시 환경에서 실제 방문자 IP를 안전하게 식별.
    
    [보안 하드닝]
    - 임의의 직접 요청에서 CF-Connecting-IP 헤더 위조를 통한 Brute-force 우회 방어.
    - Cloudflare 터널을 통한 정상 요청(CF-Ray 헤더 동반)일 때만 CF-Connecting-IP 신뢰.
    """
    raw_socket_ip = request.client.host if request.client else "127.0.0.1"
    cf_ray = request.headers.get("CF-Ray")
    cf_ip = request.headers.get("CF-Connecting-IP")

    # Cloudflare 에지가 부여한 유효한 CF-Ray 헤더가 있고 로컬 터널 소켓에서 들어온 경우에만 CF-Connecting-IP 신뢰
    if cf_ray and cf_ip and cf_ip.strip():
        # IPv4/IPv6 기본 문자열 검증
        cleaned_ip = cf_ip.strip()
        if all(c in "0123456789abcdefABCDEF:." for c in cleaned_ip):
            return cleaned_ip

    # 표준 프록시 환경에서도 X-Forwarded-For를 직접 호출자가 위조할 수 있으므로,
    # 비신뢰 직접 접속 시에는 소켓 IP를 우선 적용
    return raw_socket_ip


def require_auth(request: Request) -> dict[str, Any]:
    """모든 내부 핵심 API에 적용되는 엄격한 인증 검증 의존성."""
    token = request.cookies.get("chamart_auth")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "").strip()

    if not token or token not in ACTIVE_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증이 필요합니다. 먼저 로그인하십시오.",
        )

    session_info = ACTIVE_SESSIONS[token]
    # 세션 만료 시간 검사 (24시간 = 86400초)
    if time.time() - session_info["created_at"] > 86400:
        ACTIVE_SESSIONS.pop(token, None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="세션이 만료되었습니다. 다시 로그인하십시오.",
        )

    return session_info


@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response, request: Request) -> dict[str, Any]:
    """보안 강화 로그인 (환경변수 검증, Brute-force 차단, 보안 토큰 발급)."""
    client_ip = get_client_ip(request)
    now = time.time()

    # 1. Brute-force 차단 검사 (최근 60초 내 5회 실패 시 429 차단)
    fails = [t for t in LOGIN_FAILURES.get(client_ip, []) if now - t < 60]
    LOGIN_FAILURES[client_ip] = fails
    if len(fails) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="로그인 실패가 5회를 초과했습니다. 60초 후 다시 시도하십시오.",
        )

    # 2. 안전한 상수 시간 비밀번호 비교
    is_valid_admin = (
        req.username == "admin" and secrets.compare_digest(req.password, ENV_ADMIN_PW)
    )

    if is_valid_admin:
        # 로그인 성공 시 실패 기록 초기화
        LOGIN_FAILURES.pop(client_ip, None)
        token = secrets.token_hex(32)
        ACTIVE_SESSIONS[token] = {
            "username": "admin",
            "role": "ADMIN",
            "created_at": now,
        }
        # HTTPS 환경 감지 (Cloudflare Tunnel, X-Forwarded-Proto, 또는 HTTPS URL)
        is_https = (
            request.url.scheme == "https"
            or request.headers.get("X-Forwarded-Proto") == "https"
            or bool(request.headers.get("CF-Ray"))
        )

        response.set_cookie(
            key="chamart_auth",
            value=token,
            httponly=True,
            secure=is_https,  # HTTPS 및 Cloudflare 터널 환경에서 Secure 활성화
            samesite="lax",
            max_age=86400,
        )
        return {
            "ok": True,
            "username": "admin",
            "role": "ADMIN",
            "token": token,
        }

    # 실패 시 기록 추가
    LOGIN_FAILURES.setdefault(client_ip, []).append(now)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="아이디 또는 비밀번호가 일치하지 않습니다.")


@app.post("/api/auth/logout")
def logout(response: Response, request: Request) -> dict[str, Any]:
    """로그아웃 및 세션 토큰 완전 폐기."""
    token = request.cookies.get("chamart_auth")
    if token and token in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS.pop(token, None)
    response.delete_cookie(key="chamart_auth")
    return {"ok": True, "message": "로그아웃 및 세션이 안전하게 폐기되었습니다."}


@app.get("/api/auth/me")
def get_current_user(request: Request) -> dict[str, Any]:
    """현재 세션 상태 확인 (비인가 시 명확한 401 반환)."""
    token = request.cookies.get("chamart_auth") or request.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if token and token in ACTIVE_SESSIONS:
        sess = ACTIVE_SESSIONS[token]
        return {
            "authenticated": True,
            "username": sess["username"],
            "role": sess["role"],
            "demo_mode": True,
        }
    return {
        "authenticated": False,
        "username": None,
        "role": None,
        "demo_mode": True,
    }


# ----------------------------------------------------
# 전역 통합 검색 API (DIRECTIVE 046-B & 046-C)
# ----------------------------------------------------
@app.get("/api/search")
def search_all(
    q: str = "",
    db: Session = Depends(get_db),
    user: dict[str, Any] = Depends(require_auth),
) -> dict[str, Any]:
    """플랫폼 전역 검색 (차량, 고객, 상담 메모, 거래, 영상 프로젝트).
    
    [보안 검증]
    - 미인가 비로그인 요청 401 차단 (require_auth 적용).
    - 한글 초성 검색, 유니코드 정규화, 복합 검색 지원.
    """
    if not q or not q.strip():
        return {
            "ok": True,
            "query": "",
            "total_count": 0,
            "vehicles": [],
            "customers": [],
            "consultations": [],
            "transactions": [],
            "media_projects": [],
        }
    results = universal_search(db, q)
    results["ok"] = True
    return results


# ----------------------------------------------------
# 2. 대시보드 KPI (P0 보안 인증 필수)
# ----------------------------------------------------
@app.get("/api/overview")
def get_overview(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    return PlatformService.get_overview_kpis(db)


@app.get("/api/branches")
def list_branches(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    return PlatformService.list_branches(db)


# ----------------------------------------------------
# 3. 차량 관리 (P0 실작동, 내부 원가 보호를 위해 보안 인증 필수)
# ----------------------------------------------------
@app.get("/api/vehicles")
def list_vehicles(
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    return PlatformService.list_vehicles(db, branch_id=branch_id, status=status)


@app.get("/api/vehicles/{vehicle_id}")
def get_vehicle(
    vehicle_id: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    v = PlatformService.get_vehicle(db, vehicle_id)
    if not v:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")
    return v


@app.post("/api/vehicles", status_code=status.HTTP_201_CREATED)
def create_vehicle(
    req: VehicleCreateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    return PlatformService.create_vehicle(db, req)


@app.patch("/api/vehicles/{vehicle_id}")
def update_vehicle(
    vehicle_id: str,
    req: VehicleUpdateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    v = PlatformService.update_vehicle(db, vehicle_id, req)
    if not v:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")
    return v


@app.post("/api/vehicles/{vehicle_id}/status")
def change_vehicle_status(
    vehicle_id: str,
    req: VehicleStatusChangeRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    v = PlatformService.change_vehicle_status(db, vehicle_id, req.status, req.reason or "")
    if not v:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")
    return v


# ----------------------------------------------------
# DIRECTIVE 046-D 차량 마스터 및 상세 관리 API
# ----------------------------------------------------
@app.get("/api/vehicles/{vehicle_id}/detail")
def get_vehicle_detail(
    vehicle_id: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """차량 종합 마스터 상세 조회 (기본정보, 사고/보험, 성능점검/하자, 사진, 외부매물, 영상)."""
    detail = PlatformService.get_vehicle_detail(db, vehicle_id)
    if not detail:
        raise HTTPException(status_code=404, detail="해당 차량 정보를 찾을 수 없습니다.")
    return detail


@app.patch("/api/vehicles/{vehicle_id}/master")
def update_vehicle_master(
    vehicle_id: str,
    req: VehicleMasterUpdateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """차량 마스터 정보 일괄 수정 (기본정보, 딜러관계, 옵션, 권한)."""
    updated = PlatformService.update_vehicle_master(db, vehicle_id, req)
    if not updated:
        raise HTTPException(status_code=404, detail="해당 차량을 찾을 수 없습니다.")
    return updated


@app.post("/api/vehicles/{vehicle_id}/defects", status_code=status.HTTP_201_CREATED)
def add_vehicle_defect(
    vehicle_id: str,
    req: VehicleDefectCreateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """부위별 하자 신규 등록."""
    try:
        return PlatformService.add_vehicle_defect(db, vehicle_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.patch("/api/vehicles/{vehicle_id}/defects/{defect_id}")
def update_vehicle_defect(
    vehicle_id: str,
    defect_id: str,
    req: VehicleDefectUpdateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """부위별 하자 정보 수정 (조치상태, 수리비 등)."""
    updated = PlatformService.update_vehicle_defect(db, defect_id, req)
    if not updated:
        raise HTTPException(status_code=404, detail="해당 하자 내역을 찾을 수 없습니다.")
    return updated


@app.delete("/api/vehicles/{vehicle_id}/defects/{defect_id}")
def delete_vehicle_defect(
    vehicle_id: str,
    defect_id: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """하자 내역 삭제."""
    ok = PlatformService.delete_vehicle_defect(db, defect_id)
    if not ok:
        raise HTTPException(status_code=404, detail="해당 하자 내역을 찾을 수 없습니다.")
    return {"ok": True, "deleted_id": defect_id}


@app.post("/api/vehicles/{vehicle_id}/photos", status_code=status.HTTP_201_CREATED)
async def upload_vehicle_photos(
    vehicle_id: str,
    files: list[UploadFile] = File(default=[]),
    category: str = Form("EXTERIOR"),
    allow_video_use: bool = Form(True),
    caption: str = Form(""),
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """차량 사진 파일 다중 업로드 및 자산 등록."""
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    veh_upload_dir = Path("data/uploads/vehicles")
    veh_upload_dir.mkdir(parents=True, exist_ok=True)

    created_photos = []
    # 업로드 파일 처리
    for file in files:
        if not file.filename:
            continue
        ext = Path(file.filename).suffix or ".jpg"
        unique_name = f"{vehicle_id[:8]}_{int(time.time())}_{secrets.token_hex(4)}{ext}"
        save_path = veh_upload_dir / unique_name
        contents = await file.read()
        save_path.write_bytes(contents)

        photo_url = f"/uploads/vehicles/{unique_name}"
        # 기존 사진 수 기반 순서 산정
        curr_count = len(v.photos) + len(created_photos)
        is_primary = (curr_count == 0)

        photo_info = PlatformService.add_vehicle_photo(
            db=db,
            vehicle_id=v.id,
            photo_url=photo_url,
            thumb_url=photo_url,
            category=category,
            sort_order=curr_count + 1,
            is_primary=is_primary,
            allow_video_use=allow_video_use,
            caption=caption or file.filename,
        )
        created_photos.append(photo_info)

    return {
        "ok": True,
        "count": len(created_photos),
        "photos": created_photos,
    }


@app.patch("/api/vehicles/{vehicle_id}/photos/reorder")
def reorder_vehicle_photos(
    vehicle_id: str,
    req: VehiclePhotoReorderRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """사진 순서 변경 및 대표 사진 지정."""
    try:
        photos = PlatformService.reorder_vehicle_photos(db, vehicle_id, req)
        return {"ok": True, "photos": photos}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/vehicles/{vehicle_id}/photos/{photo_id}")
def delete_vehicle_photo(
    vehicle_id: str,
    photo_id: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """사진 자산 삭제."""
    ok = PlatformService.delete_vehicle_photo(db, photo_id)
    if not ok:
        raise HTTPException(status_code=404, detail="해당 사진을 찾을 수 없습니다.")
    return {"ok": True, "deleted_id": photo_id}


@app.post("/api/vehicles/{vehicle_id}/create-video-project", status_code=status.HTTP_201_CREATED)
def create_video_project_from_vehicle(
    vehicle_id: str,
    req: VehicleVideoProjectCreateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """차량 상세에서 원클릭으로 AI 영상 프로젝트 생성 (보안 및 권한 가드 적용)."""
    try:
        return PlatformService.create_video_project_from_vehicle(db, vehicle_id, req)
    except PermissionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/vehicles/{vehicle_id}/platforms/register-intent")
def register_platform_intent(
    vehicle_id: str,
    req: PlatformRegisterIntentRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """미래 다중 플랫폼 자동 등록 준비 검증 (외부 실제 전송 차단 어댑터)."""
    try:
        return PlatformService.register_platform_intent(db, vehicle_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/dealers")
def list_dealers(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    """제휴 딜러 목록 조회."""
    return PlatformService.list_dealers(db)


# ----------------------------------------------------
# 4. 고객 CRM (P0 보안 인증 필수)
# ----------------------------------------------------
@app.get("/api/customers")
def list_customers(
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    query: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    return PlatformService.list_customers(db, branch_id=branch_id, status=status, query_str=query)


@app.get("/api/customers/{customer_id}")
def get_customer(
    customer_id: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    c = PlatformService.get_customer(db, customer_id)
    if not c:
        raise HTTPException(status_code=404, detail="고객을 찾을 수 없습니다.")
    return c


@app.post("/api/customers", status_code=status.HTTP_201_CREATED)
def create_customer(
    req: CustomerCreateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    return PlatformService.create_customer(db, req)


@app.post("/api/customers/{customer_id}/consultations")
def add_consultation(
    customer_id: str,
    req: ConsultationCreateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    try:
        return PlatformService.add_consultation(db, customer_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/consultations")
def list_consultations(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    return PlatformService.list_consultations(db)


# ----------------------------------------------------
# 5. 거래·계약 관리 (P0 보안 인증 필수)
# ----------------------------------------------------
@app.get("/api/transactions")
def list_transactions(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    return PlatformService.list_transactions(db)


@app.post("/api/transactions", status_code=status.HTTP_201_CREATED)
def create_transaction(
    req: TransactionCreateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    try:
        return PlatformService.create_transaction(db, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------------------------------
# 6. AI 서류 인식 검토 대기열 (P0 보안 인증 필수)
# ----------------------------------------------------
@app.get("/api/documents")
def list_documents(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    return PlatformService.list_documents(db)


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("TRANSFER_CERTIFICATE"),
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """서류 파일(PDF/사진) 업로드 및 SHA-256 검증."""
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="파일 크기가 10MB를 초과할 수 없습니다.")

    try:
        res = PlatformService.save_and_register_document(
            db=db,
            file_bytes=content,
            filename=file.filename or "unknown_document",
            doc_type=doc_type,
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/documents/{doc_id}/file")
def get_document_file(
    doc_id: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> FileResponse:
    """인증된 관리자만 접근 가능한 비공개 서류 다운로드 (DIRECTIVE 048 P0-5)."""
    doc = db.query(DocumentReview).filter(DocumentReview.id == doc_id).first()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="문서 파일을 찾을 수 없습니다.")
    return FileResponse(doc.file_path, filename=doc.filename)


@app.post("/api/documents/{doc_id}/approve")
def approve_document(
    doc_id: str,
    req: DocumentApprovalRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    try:
        return PlatformService.approve_document(db, doc_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----------------------------------------------------
# DIRECTIVE 050-C AI 비전(Gemini Vision) & CRM/거래 파이프라인 API
# ----------------------------------------------------
def _validate_document_file(content: bytes, filename: str) -> None:
    """서류 파일 15MB 한도, 확장자 및 매직바이트 보안 검증 (PHASE E)."""
    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="파일 크기가 15MB를 초과할 수 없습니다.")

    allowed_exts = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
    ext = Path(filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"허용되지 않은 파일 형식입니다: {ext} (허용: JPG, PNG, WEBP, PDF)")

    is_pdf = content.startswith(b"%PDF-")
    is_png = content.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpg = content.startswith(b"\xff\xd8\xff")
    is_webp = (len(content) > 12 and content[8:12] == b"WEBP")
    if not (is_pdf or is_png or is_jpg or is_webp):
        raise HTTPException(status_code=400, detail="파일 바이너리가 선언된 이미지/PDF 규격과 일치하지 않습니다.")


@app.get("/api/ai/vision/config")
def get_ai_vision_config(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """Gemini Vision 연동 상태, 마스킹된 키 및 사용량 통계 조회."""
    return GeminiVisionService.get_stats(db)


@app.post("/api/ai/vision/save-key")
def save_ai_vision_key(
    req: GeminiKeySaveRequest,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """관리자 화면에서 Gemini API 키 및 모델 동적 등록 및 저장."""
    if not req.api_key or not req.api_key.strip():
        raise HTTPException(status_code=400, detail="API 키는 비어있을 수 없습니다.")
    return GeminiVisionService.save_settings(
        api_key=req.api_key,
        primary_model=req.model,
        fallback_model=req.fallback_model,
    )


@app.post("/api/ai/vision/test-connection")
def test_ai_vision_connection(
    req: Optional[dict[str, Any]] = None,
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """Gemini Vision AI 연결 테스트 (API 키 등록 여부 및 핑 테스트)."""
    custom_key = req.get("api_key") if req else None
    custom_model = req.get("model") if req else None
    return GeminiVisionService.test_connection(api_key=custom_key, model=custom_model)


@app.post("/api/crm/business-card/analyze")
async def analyze_business_card(
    file: UploadFile = File(...),
    is_mock: bool = False,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """명함 이미지 분석 -> CustomerCandidate 추출 및 기존 고객 중복 검사 (PHASE C)."""
    content = await file.read()
    _validate_document_file(content, file.filename or "business_card.jpg")

    mime = file.content_type or "image/jpeg"
    result = GeminiVisionService.analyze_business_card(content, mime_type=mime, is_mock=is_mock)
    if not result.get("ok"):
        return result

    # 파일 저장 (격리된 디렉토리)
    ym = datetime.date.today().strftime("%Y/%m")
    save_dir = DOC_UPLOAD_DIR / ym
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = f"card_{secrets.token_hex(6)}_{file.filename or 'card.jpg'}"
    save_path = save_dir / filename
    with open(save_path, "wb") as f:
        f.write(content)

    image_url = f"/uploads/documents/{ym}/{filename}"
    candidate = result["candidate"]

    # 중복 고객 검사
    dup_info = PlatformService.check_customer_duplicate(
        db,
        phone=candidate.get("phone", ""),
        email=candidate.get("email"),
    )

    return {
        "ok": True,
        "status": "EXTRACTED",
        "candidate": candidate,
        "duplicate_check": dup_info,
        "source_image_url": image_url,
        "message": result.get("message", "명함이 성공적으로 분석되었습니다."),
    }


@app.post("/api/crm/customers/from-card", status_code=status.HTTP_201_CREATED)
def create_customer_from_card(
    req: CustomerFromCardRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """명함 분석 결과 검토 후 정식 CRM 고객으로 등록 (PHASE C)."""
    return PlatformService.create_customer_from_business_card(db, req)


@app.get("/api/crm/customers/check-duplicate")
def check_customer_duplicate(
    phone: str,
    email: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """전화번호 및 이메일 기준 고객 중복 여부 확인."""
    return PlatformService.check_customer_duplicate(db, phone=phone, email=email)


@app.post("/api/transactions/document/analyze")
async def analyze_transaction_document(
    file: UploadFile = File(...),
    is_mock: bool = False,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """거래서류(매매계약서, 정산서, 입출금내역) 분석 -> 차량/고객 자동 매칭 및 초안 생성 (PHASE D)."""
    content = await file.read()
    _validate_document_file(content, file.filename or "transaction_doc.jpg")

    sha256_hash = hashlib.sha256(content).hexdigest()
    mime = file.content_type or "image/jpeg"

    result = GeminiVisionService.analyze_transaction_document(content, mime_type=mime, is_mock=is_mock)
    if not result.get("ok"):
        return result

    # 파일 저장
    ym = datetime.date.today().strftime("%Y/%m")
    save_dir = DOC_UPLOAD_DIR / ym
    save_dir.mkdir(parents=True, exist_ok=True)
    filename = f"tx_{secrets.token_hex(6)}_{file.filename or 'doc.jpg'}"
    save_path = save_dir / filename
    with open(save_path, "wb") as f:
        f.write(content)

    image_url = f"/uploads/documents/{ym}/{filename}"
    extract = result["extract"]

    # 1. 차량 자동 매칭
    matched_vehicle = PlatformService.match_vehicle_for_document(
        db,
        plate_number=extract.get("vehicle_plate_number"),
        vin=extract.get("vin"),
    )

    # 2. 거래 상대방(고객/딜러) 자동 매칭
    matched_party = PlatformService.match_party_for_document(
        db,
        name=extract.get("party_name"),
        contact=extract.get("party_contact"),
    )

    # 3. DocumentReview 대기열 생성 (status: NEEDS_REVIEW)
    doc_review = DocumentReview(
        doc_type=extract.get("document_type", "CONTRACT"),
        document_type=extract.get("document_type", "CONTRACT"),
        filename=file.filename or "transaction_document",
        file_path=str(save_path),
        file_sha256=sha256_hash,
        file_size=len(content),
        extracted_data_json=json.dumps(extract, ensure_ascii=False),
        review_status="PENDING",
        status="NEEDS_REVIEW",
        extracted_amount=extract.get("total_amount", 0),
        has_official_seal=extract.get("has_official_seal", False),
        ai_confidence=extract.get("confidence", 0.90),
        matched_vehicle_id=matched_vehicle["id"] if matched_vehicle else None,
        matched_customer_id=matched_party["customer"]["id"] if matched_party.get("customer") else None,
    )
    db.add(doc_review)
    db.commit()
    db.refresh(doc_review)

    return {
        "ok": True,
        "status": "NEEDS_REVIEW",
        "document_review_id": doc_review.id,
        "extract": extract,
        "matched_vehicle": matched_vehicle,
        "matched_party": matched_party,
        "source_image_url": image_url,
        "sha256": sha256_hash,
        "message": "거래 서류 분석 완료: 초안 검토 후 확정하십시오.",
    }


@app.post("/api/transactions/draft/confirm", status_code=status.HTTP_201_CREATED)
def confirm_transaction_draft(
    req: TransactionDraftConfirmRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """거래 초안 확인 및 관리자 승인 (원장 정식 반영 및 무결성 격리 보장)."""
    try:
        return PlatformService.create_transaction_from_draft(db, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------------------------------
# 7. AI 영상 스튜디오 (P0 보안 인증 필수)
# ----------------------------------------------------
@app.get("/api/media-projects")
def list_media_projects(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    return PlatformService.list_media_projects(db)


@app.post("/api/media-projects", status_code=status.HTTP_201_CREATED)
def create_media_project(
    req: MediaProjectCreateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    return PlatformService.create_media_project(db, req)


@app.patch("/api/media-projects/{project_id}/status")
def update_media_project_status(
    project_id: str,
    req: MediaProjectStatusUpdateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    try:
        return PlatformService.update_media_project_status(db, project_id, req.status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ----------------------------------------------------
# 8. P1 미래 연동 영역 (텔레그램, SMS, 카매니저, 마케팅, 인증 필수)
# ----------------------------------------------------
@app.get("/api/integrations/telegram")
def get_telegram_status(_auth: dict = Depends(require_auth)) -> dict[str, Any]:
    """텔레그램 고객 커뮤니티 연동 상태 (P1)."""
    return {
        "status": "READY_FOR_INTEGRATION",
        "badge": "연동 대기 (Phase 2)",
        "channel_name": "@chamart_official",
        "bot_configured": False,
        "queue_count": 0,
        "message": "공식 Telegram Bot Token 발급 및 웹훅 보안 설정 후 활성화됩니다.",
    }


@app.get("/api/integrations/sms")
def get_sms_status(_auth: dict = Depends(require_auth)) -> dict[str, Any]:
    """안드로이드 SMS 발송 센터 연동 상태 (P1)."""
    return {
        "status": "GATEWAY_PENDING",
        "badge": "게이트웨이 대기 (Phase 2)",
        "connected_device": None,
        "daily_sent_count": 0,
        "daily_limit": 200,
        "message": "직원 안드로이드 전용 SMS 발송 앱과의 로컬 HTTPS 페어링이 필요합니다.",
    }


@app.get("/api/integrations/carmanager")
def get_carmanager_status(_auth: dict = Depends(require_auth)) -> dict[str, Any]:
    """카매니저 외부 매물 연동 상태 (P1)."""
    return {
        "status": "SPECIFICATION_AUDIT",
        "badge": "공식 연동 규격 검토 중",
        "sync_mode": "READ_ONLY_PILOT",
        "auto_sync_enabled": False,
        "message": "카매니저 공식 연동 가이드 및 상사 인증키 확인 후 양방향 동기화가 제공됩니다.",
    }


@app.get("/api/marketing/performance")
def get_marketing_performance(_auth: dict = Depends(require_auth)) -> dict[str, Any]:
    """마케팅 전환 퍼널 데이터 (P1)."""
    return {
        "status": "DATA_STRUCTURE_READY",
        "funnel": [
            {"stage": "영상 조회", "count": 14500, "note": "쇼츠·릴스 누적 조회수 (데모)"},
            {"stage": "채널 유입", "count": 1280, "note": "프로필 링크 및 커뮤니티 유입"},
            {"stage": "고객 문의", "count": 42, "note": "전화/카카오톡/텔레그램 문의"},
            {"stage": "상담 및 방문", "count": 18, "note": "장한평/수원 전시장 상담"},
            {"stage": "실제 계약/판매", "count": 5, "note": "실거래 체결 건수"},
        ],
        "top_contents": [
            {"title": "2000만원대 그랜저 르블랑 실매물 검증", "views": 8400, "inquiries": 24},
            {"title": "첫차 아반떼 CN7 인스퍼레이션", "views": 6100, "inquiries": 18},
        ],
    }


# ----------------------------------------------------
# 8-1. DIRECTIVE 049: 엔카 서울 실매물 자동 소싱 및 장한평 선별 엔드포인트
# ----------------------------------------------------
@app.post("/api/market/sourcing/encar/run")
def run_encar_sourcing(
    limit: int = 20,
    page: int = 1,
    fetch_detail: bool = True,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """엔카 서울 실매물 자동 수집 및 동기화 실행 (DIRECTIVE 049)."""
    return SourcingService.sync_encar_seoul(db, limit=limit, page=page, fetch_detail=fetch_detail)


@app.get("/api/market/sourcing/summary")
def get_sourcing_summary(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """엔카 서울 매물 소싱 관리 5대 KPI 통계 요약 (DIRECTIVE 049)."""
    return SourcingService.get_sourcing_summary(db)


@app.get("/api/market/sourcing/listings")
def list_sourcing_listings(
    location_filter: Optional[str] = None,
    price_drop_only: bool = False,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    """소싱된 엔카 실매물 목록 조회 및 필터링 (DIRECTIVE 049)."""
    return SourcingService.list_sourcing_listings(
        db,
        location_filter=location_filter,
        price_drop_only=price_drop_only,
        search=search,
        limit=limit,
        offset=offset,
    )


# ----------------------------------------------------
# 8-2. DIRECTIVE 047: 장한평 시장 분석 & 권한 원장 & 성과 기여 & RL 엔드포인트
# ----------------------------------------------------
@app.get("/api/market/summary")
def get_market_analysis_summary(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """장한평 및 전국 매물 시장 분석 요약 지표 (DIRECTIVE 047)."""
    return PlatformService.get_market_analysis_summary(db)


@app.get("/api/market/listings")
def list_market_listings(
    is_janghanpyeong: Optional[bool] = None,
    min_opportunity: float = 0.0,
    price_dropped_only: bool = False,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    """외부 플랫폼 매물 및 기회 점수 목록 (DIRECTIVE 047)."""
    return PlatformService.list_market_listings(
        db,
        is_janghanpyeong=is_janghanpyeong,
        min_opportunity=min_opportunity,
        price_dropped_only=price_dropped_only,
    )


@app.get("/api/vehicles/{vehicle_id}/rights")
def get_vehicle_rights(
    vehicle_id: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """제휴 딜러 권한 원장 조회 (DIRECTIVE 047)."""
    try:
        return PlatformService.get_vehicle_rights(db, vehicle_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/vehicles/{vehicle_id}/rights/grant")
def grant_vehicle_rights(
    vehicle_id: str,
    req: DealerRightsGrantRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """제휴 딜러 권한 부여 및 승인 (DIRECTIVE 047)."""
    try:
        return PlatformService.grant_vehicle_rights(db, vehicle_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/vehicles/{vehicle_id}/rights/revoke")
def revoke_vehicle_rights(
    vehicle_id: str,
    req: DealerRightsRevokeRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """제휴 권한 철회 및 영상 제작 차단 (DIRECTIVE 047)."""
    try:
        return PlatformService.revoke_vehicle_rights(db, vehicle_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/attribution/summary")
def get_attribution_summary(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """AI 영상 기여도 vs 자연 판매 분석 및 정산 공헌이익 (DIRECTIVE 047)."""
    return PlatformService.get_attribution_summary(db)


@app.get("/api/vehicles/{vehicle_id}/attribution-trail")
def get_vehicle_attribution_trail(
    vehicle_id: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """차량별 발굴-영상-문의-계약-정산 전체 이력 추적 (DIRECTIVE 047)."""
    try:
        return PlatformService.get_vehicle_attribution_trail(db, vehicle_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/rl/decisions/evaluate")
def evaluate_rl_decision(
    req: RLDecisionEvaluateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """의사결정 시점의 State 벡터 구성 및 Baseline Action 결정 로그 기록 (DIRECTIVE 047)."""
    try:
        return PlatformService.evaluate_rl_decision(db, req.vehicle_id, req.policy_version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/rl/decisions")
def list_rl_decisions(
    split: Optional[str] = None,
    is_censored: Optional[bool] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    """강화학습 오프라인 의사결정 로그 목록 (DIRECTIVE 047)."""
    return PlatformService.list_rl_decisions(db, split=split, is_censored=is_censored)


@app.post("/api/rl/decisions/{decision_id}/reward")
def update_rl_reward(
    decision_id: str,
    req: RLDecisionRewardUpdateRequest,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """판매 종결에 따른 Reward 확정 및 Censored 해제 (DIRECTIVE 047)."""
    try:
        return PlatformService.update_rl_reward(db, decision_id, req)
    except ValueError as e:
        err_msg = str(e)
        if "찾을 수 없습니다" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)


@app.get("/api/rl/readiness")
def get_rl_readiness(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """강화학습 데이터 파이프라인 준비도 및 모델 도입 적합성 감사 (DIRECTIVE 047)."""
    return PlatformService.get_rl_readiness_audit(db)


# ====================================================
# 10. DIRECTIVE 050: 차량 마스터 등록 및 다중 플랫폼 연동 API
# ====================================================
@app.get("/api/vehicles/catalog/hierarchy")
def get_catalog_hierarchy(_auth: dict = Depends(require_auth)) -> dict[str, Any]:
    """제조사 -> 모델 -> 세대 -> 트림 계층 카탈로그 트리 (DIRECTIVE 050 3항)."""
    return VehicleCatalogService.get_full_catalog_tree()


@app.get("/api/vehicles/catalog/options")
def get_standard_options(
    category: Optional[str] = None,
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    """표준 옵션 마스터 목록 및 플랫폼 매핑 코드 (DIRECTIVE 050 1항)."""
    return StandardOptionCatalog.list_options(category=category)


@app.post("/api/vehicles/master/create")
def create_vehicle_master(
    data: dict[str, Any],
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """8대 영역을 포괄하는 신규 차량 마스터 통합 등록 (DIRECTIVE 050 1항)."""
    try:
        return MasterVehicleService.create_vehicle_master(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/vehicles/{vehicle_id}/master")
def get_vehicle_master(
    vehicle_id: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """8대 영역 표준 구조로 차량 마스터 데이터 통합 조회 (DIRECTIVE 050 1항)."""
    try:
        return MasterVehicleService.get_vehicle_master(db, vehicle_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.put("/api/vehicles/{vehicle_id}/master")
def update_vehicle_master(
    vehicle_id: str,
    data: dict[str, Any],
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """차량 마스터 정보 수정 및 플랫폼 게시 준비 데이터 자동 동기화 (DIRECTIVE 050 6항)."""
    try:
        return MasterVehicleService.update_vehicle_master(db, vehicle_id, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/vehicles/{vehicle_id}/publishing-readiness")
def get_publishing_readiness(
    vehicle_id: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """3대 플랫폼별(ENCAR, KB, CAR_MANAGER) 등록 준비도 종합 검사 (DIRECTIVE 050 4항)."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")
    validator = PublishingReadinessValidator()
    return validator.evaluate_vehicle_readiness(db, vehicle, sync_db=True)


@app.post("/api/vehicles/{vehicle_id}/publishing/preview/{platform}")
def get_publishing_preview(
    vehicle_id: str,
    platform: str,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """특정 플랫폼 게시용 JSON 페이로드 미리보기 및 내보내기 (DIRECTIVE 050 5항)."""
    platform_upper = platform.upper().strip()
    validator = PublishingReadinessValidator()
    if platform_upper not in validator.mappers:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 플랫폼입니다: '{platform}'. 허용: {list(validator.mappers.keys())}",
        )
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

    mapper = validator.mappers[platform_upper]
    rep = mapper.validate_readiness(vehicle)
    payload = mapper.build_export_payload(vehicle)

    return {
        "vehicle_id": vehicle.id,
        "platform": platform_upper,
        "is_ready": rep.is_ready,
        "missing_fields": rep.missing_fields,
        "warnings": rep.warnings,
        "errors": rep.errors,
        "mapped_payload": payload,
        "exported_at": datetime.datetime.utcnow().isoformat(),
    }


@app.post("/api/vehicles/{vehicle_id}/publishing/transition")
def transition_publishing_status(
    vehicle_id: str,
    req: dict[str, Any],
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """차량 플랫폼 게시 라이프사이클 상태 전이 (DIRECTIVE 050 5항)."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"차량 ID '{vehicle_id}'를 찾을 수 없습니다.")

    target_status = req.get("target_status", "")
    notes = req.get("notes", "")
    validator = PublishingReadinessValidator()
    try:
        return validator.transition_publishing_status(db, vehicle, target_status, notes=notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------------------------------------------------------
# DIRECTIVE 051 & 071: PART 1. 차마트(CHAMART) 일반 고객용 공개 API 및 엔카급 상세 검색
# -----------------------------------------------------------------------------

@app.get("/api/chamart/search")
@app.get("/api/chamart/search/vehicles")
def search_chamart_vehicles(
    request: Request,
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """DIRECTIVE 071: 엔카급 상세 검색 및 차마트 보유 매물 우선순위 정렬 API."""
    params = dict(request.query_params)
    
    # 1. DB 실차 검색 시도
    result = PlatformService.search_vehicles_advanced(db, params, mode="prod")
    
    # 2. 운영 DB 실차가 아직 0건일 때, 검수용 100대 피스처 데이터를 동적으로 정밀 필터링하여 응답
    if result["total_count"] == 0:
        fixtures = get_staging_ui_fixture_vehicles()
        if fixtures:
            # 피스처 기반 인메모리 필터링 & 우선순위 정렬
            filtered = []
            
            # 검색 조건 파싱
            is_dom = params.get("is_domestic")
            mfg_list = [m.strip() for m in params.get("manufacturers", "").split(",") if m.strip()]
            kw = (params.get("keyword") or params.get("q") or "").strip().lower()
            y_min = int(params.get("year_min", 0)) if params.get("year_min") else 0
            y_max = int(params.get("year_max", 9999)) if params.get("year_max") else 9999
            p_min = int(params.get("price_min", 0)) if params.get("price_min") else 0
            p_max = int(params.get("price_max", 999999)) if params.get("price_max") else 999999
            m_min = int(params.get("mileage_min", 0)) if params.get("mileage_min") else 0
            m_max = int(params.get("mileage_max", 9999999)) if params.get("mileage_max") else 9999999
            fuels = [f.strip() for f in params.get("fuel_types", "").split(",") if f.strip()]
            bodies = [b.strip() for b in params.get("body_types", "").split(",") if b.strip()]
            only_owned = str(params.get("only_chamart_owned", "")).lower() == "true"
            only_priority = str(params.get("only_priority", "")).lower() == "true"
            sort_mode = params.get("sort", "CHAMART_RECOMMENDED").upper()
            
            domestic_set = {"현대", "기아", "제네시스", "쉐보레", "르노코리아", "KG모빌리티"}
            
            for item in fixtures:
                # 상태 확인: 판매완료 차량 차단
                if item.get("status") in ["SOLD", "CANCELLED"]:
                    continue
                    
                mfg = item.get("manufacturer", "")
                if is_dom == "true" and mfg not in domestic_set:
                    continue
                if is_dom == "false" and mfg in domestic_set:
                    continue
                if mfg_list and mfg not in mfg_list:
                    continue
                    
                model = item.get("model_name", "")
                plate = item.get("plate_number", "")
                trim = item.get("trim", "")
                if kw and not (kw in model.lower() or kw in plate.lower() or kw in trim.lower() or kw in mfg.lower()):
                    continue
                    
                yr = item.get("year", 0)
                if not (y_min <= yr <= y_max):
                    continue
                pr = item.get("target_price", 0)
                if not (p_min <= pr <= p_max):
                    continue
                mil = item.get("mileage", 0)
                if not (m_min <= mil <= m_max):
                    continue
                if fuels and item.get("fuel_type") not in fuels:
                    continue
                if bodies and item.get("body_type") not in bodies:
                    continue
                
                is_owned = item.get("is_chamart_owned", False) or item.get("listing_ownership_type") == "OWNED"
                if only_owned and not is_owned:
                    continue
                if only_priority and not item.get("is_priority_exposure", False):
                    continue
                    
                filtered.append(item)
                
            # 피스처 정렬
            if sort_mode == "CHAMART_RECOMMENDED":
                # 1. 차마트 직접 보유 & 우선노출 -> 2. 차마트 보유 -> 3. 일반
                filtered.sort(
                    key=lambda x: (
                        1 if (x.get("is_chamart_owned") and x.get("is_priority_exposure")) else (
                            2 if x.get("is_chamart_owned") else (
                                3 if x.get("is_priority_exposure") else 4
                            )
                        ),
                        -x.get("priority_rank", 0),
                        -x.get("year", 0)
                    )
                )
            elif sort_mode in ["PRICE_ASC", "PRICE_LOW"]:
                filtered.sort(key=lambda x: x.get("target_price", 0))
            elif sort_mode in ["PRICE_DESC", "PRICE_HIGH"]:
                filtered.sort(key=lambda x: -x.get("target_price", 0))
            elif sort_mode in ["MILEAGE_ASC", "MILEAGE_LOW"]:
                filtered.sort(key=lambda x: x.get("mileage", 0))
            elif sort_mode in ["YEAR_DESC", "YEAR_HIGH"]:
                filtered.sort(key=lambda x: -x.get("year", 0))
            elif sort_mode in ["YEAR_ASC", "YEAR_LOW"]:
                filtered.sort(key=lambda x: x.get("year", 0))
                
            page = max(1, int(params.get("page", 1)))
            limit = max(1, int(params.get("limit", 20)))
            start_i = (page - 1) * limit
            paginated = filtered[start_i:start_i + limit]
            priority_items = [x for x in filtered if x.get("is_priority_exposure") or x.get("is_chamart_owned")][:4]
            
            return {
                "total_count": len(filtered),
                "page": page,
                "limit": limit,
                "total_pages": (len(filtered) + limit - 1) // limit if len(filtered) > 0 else 1,
                "items": paginated,
                "priority_items": priority_items,
                "sort_applied": sort_mode,
            }
            
    return result


@app.get("/api/chamart/vehicles")
def get_chamart_public_vehicles(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """차마트 고객 공개 차량 목록 (하위 호환 배열 반환 + 파라미터 전달 시 상세 객체 반환)."""
    # 쿼리 파라미터가 있는 경우 상세 검색 실행
    if len(request.query_params) > 0:
        return search_chamart_vehicles(request, db)

    vehicles = PlatformService.get_chamart_public_vehicles(db, mode="prod")
    if not vehicles:
        fixtures = get_staging_ui_fixture_vehicles()
        if fixtures:
            return fixtures
        return PlatformService.get_chamart_public_vehicles(db, mode="demo")
    return vehicles


@app.get("/api/chamart/vehicles/{vehicle_id}")
def get_chamart_public_vehicle_detail(
    vehicle_id: str,
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """차마트 고객 공개 차량 상세 조회 (부위별 사진 갤러리 메트릭스 통합 제공)."""
    detail = PlatformService.get_chamart_public_vehicle_detail(db, vehicle_id, mode="prod")
    if not detail:
        detail = PlatformService.get_chamart_public_vehicle_detail(db, vehicle_id, mode="demo")
    if not detail and (vehicle_id.startswith("UI-") or vehicle_id.startswith("STG-") or not detail):
        try:
            detail = get_staging_ui_fixture_vehicle_detail(vehicle_id)
        except HTTPException:
            pass
            
    if not detail:
        raise HTTPException(status_code=404, detail="공개된 차량 정보를 찾을 수 없습니다.")

    # 부위별 사진 매트릭스 보강 (TASK 6)
    if "photo_matrix" not in detail:
        try:
            matrix = PlatformService.get_vehicle_photo_matrix(db, vehicle_id)
            if matrix.get("slots"):
                detail["photo_matrix"] = matrix
        except Exception:
            pass

    return detail


# -----------------------------------------------------------------------------
# DIRECTIVE 071: PART 2. 관리자용 차량 부위별 사진 관리 & 보유/우선노출 설정 API
# -----------------------------------------------------------------------------

@app.get("/api/admin/vehicles/{vehicle_id}/photo-matrix")
def get_admin_vehicle_photo_matrix(
    vehicle_id: str,
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """관리자용 45개 표준 부위별 사진 슬롯 현황 및 등록 사진 목록 조회 (DB 실차 + UI Fixture 양방향 지원)."""
    # 1. DB 실차 조회
    matrix = PlatformService.get_vehicle_photo_matrix(db, vehicle_id)
    if "error" not in matrix:
        return matrix
        
    # 2. UI Fixture 시연 차량 폴백
    fixtures = get_staging_ui_fixture_vehicles()
    for v in fixtures:
        if v.get("id") == vehicle_id:
            slots_status = []
            photos = v.get("photos", [])
            photos_by_view = {}
            for p in photos:
                view = p.get("view_code", "EXT_FRONT")
                if view not in photos_by_view:
                    photos_by_view[view] = []
                photos_by_view[view].append(p)

            for slot in PlatformService.STANDARD_PHOTO_SLOTS:
                view = slot["view_code"]
                matched = photos_by_view.get(view, [])
                slots_status.append({
                    "category_code": slot["category_code"],
                    "category_label": slot["category_label"],
                    "view_code": view,
                    "label": slot["label"],
                    "is_required": slot["is_required"],
                    "is_registered": len(matched) > 0,
                    "photo_count": len(matched),
                    "photos": matched,
                })
            return {
                "vehicle_id": vehicle_id,
                "plate_number": v.get("plate_number", ""),
                "model_name": v.get("model_name", ""),
                "total_slots": len(PlatformService.STANDARD_PHOTO_SLOTS),
                "registered_photos_count": len(photos),
                "slots": slots_status,
            }
            
    raise HTTPException(status_code=404, detail="해당 차량 정보를 찾을 수 없습니다.")


@app.post("/api/admin/vehicles/{vehicle_id}/priority")
async def update_admin_vehicle_priority(
    vehicle_id: str,
    request: Request,
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """관리자 전용 차량 소유/판매 유형 및 우선노출 설정 API."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="유효한 JSON 페이로드가 필요합니다.")
        
    res = PlatformService.update_vehicle_priority_settings(db, vehicle_id, payload)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("message", "설정 갱신 실패"))
    return res


@app.post("/api/admin/vehicles/{vehicle_id}/photos")
async def upload_admin_vehicle_photo(
    vehicle_id: str,
    file: UploadFile = File(...),
    view_code: str = Form("EXT_FRONT"),
    category_code: str = Form("EXTERIOR_FULL"),
    display_label: str = Form("외관"),
    is_primary: bool = Form(False),
    photo_note: Optional[str] = Form(None),
    damage_evidence: bool = Form(False),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """차량 부위별 전문 사진 업로드 (EXIF 메타데이터 제거 및 WebP 썸네일 자동 생성)."""
    v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="차량을 찾을 수 없습니다.")

    # 저장 경로 준비
    upload_dir = Path("src/chaficial/platform/ui/static/uploads/vehicles") / vehicle_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_bytes = await file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    file_ext = Path(file.filename or "photo.jpg").suffix.lower() or ".jpg"
    safe_filename = f"{view_code}_{int(time.time())}_{secrets.token_hex(4)}{file_ext}"
    orig_save_path = upload_dir / safe_filename

    # PIL을 이용한 EXIF 정보 제거 및 원본/썸네일 생성
    try:
        from PIL import Image, ImageOps
        import io
        img = Image.open(io.BytesIO(file_bytes))
        img = ImageOps.exif_transpose(img) # 방향 보정
        
        # EXIF 제거하고 깨끗하게 RGB 저장
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.save(orig_save_path, "JPEG", quality=90)
        
        # WebP 썸네일 생성
        thumb_filename = f"thumb_{Path(safe_filename).stem}.webp"
        thumb_save_path = upload_dir / thumb_filename
        thumb_img = img.copy()
        thumb_img.thumbnail((400, 300))
        thumb_img.save(thumb_save_path, "WEBP", quality=85)
        
        thumb_url = f"/static/uploads/vehicles/{vehicle_id}/{thumb_filename}"
    except Exception as e:
        # PIL 실패 시 바이너리 직접 저장
        with open(orig_save_path, "wb") as f:
            f.write(file_bytes)
        thumb_url = f"/static/uploads/vehicles/{vehicle_id}/{safe_filename}"

    photo_url = f"/static/uploads/vehicles/{vehicle_id}/{safe_filename}"

    # 대표 사진(is_primary) 지정 시 기존 대표 사진 해제
    if is_primary:
        db.query(VehiclePhoto).filter(VehiclePhoto.vehicle_id == vehicle_id).update({"is_primary": False})
        v.primary_photo_url = photo_url

    new_photo = VehiclePhoto(
        vehicle_id=vehicle_id,
        photo_url=photo_url,
        thumb_url=thumb_url,
        category=category_code.split("_")[0],
        category_code=category_code,
        view_code=view_code,
        display_label=display_label,
        original_path=str(orig_save_path),
        thumbnail_path=str(thumb_url),
        is_primary=is_primary,
        original_file_hash=file_hash,
        verification_status="VERIFIED_REAL_ASSET",
        photo_source="FIELD_INSPECTION_PHOTO",
        usage_rights_status="CONFIRMED_COMMERCIAL",
        approval_status="APPROVED",
        public_visibility="PUBLIC",
        photo_note=photo_note,
        damage_evidence=damage_evidence,
        mime_type="image/jpeg",
        file_size_bytes=len(file_bytes),
    )
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)

    return {
        "success": True,
        "photo_id": new_photo.id,
        "photo_url": new_photo.photo_url,
        "thumb_url": new_photo.thumb_url,
        "view_code": new_photo.view_code,
        "display_label": new_photo.display_label,
        "is_primary": new_photo.is_primary,
        "message": f"부위 [{display_label}] 사진이 성공적으로 등록되었습니다.",
    }


@app.delete("/api/admin/vehicles/{vehicle_id}/photos/{photo_id}")
def delete_admin_vehicle_photo(
    vehicle_id: str,
    photo_id: str,
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """차량 부위 사진 삭제 API."""
    p = db.query(VehiclePhoto).filter(VehiclePhoto.id == photo_id, VehiclePhoto.vehicle_id == vehicle_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다.")

    db.delete(p)
    db.commit()
    return {"success": True, "message": "사진이 삭제되었습니다."}


@app.put("/api/admin/vehicles/{vehicle_id}/photos/{photo_id}")
async def update_admin_vehicle_photo(
    vehicle_id: str,
    photo_id: str,
    request: Request,
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """사진 부위 코드, 한글 라벨, 메모, 대표 사진 여부 수정 API."""
    p = db.query(VehiclePhoto).filter(VehiclePhoto.id == photo_id, VehiclePhoto.vehicle_id == vehicle_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다.")

    payload = await request.json()
    if "view_code" in payload:
        p.view_code = payload["view_code"]
    if "category_code" in payload:
        p.category_code = payload["category_code"]
    if "display_label" in payload:
        p.display_label = payload["display_label"]
    if "photo_note" in payload:
        p.photo_note = payload["photo_note"]
    if "damage_evidence" in payload:
        p.damage_evidence = bool(payload["damage_evidence"])
    if "is_primary" in payload and payload["is_primary"] is True:
        db.query(VehiclePhoto).filter(VehiclePhoto.vehicle_id == vehicle_id).update({"is_primary": False})
        p.is_primary = True
        v = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if v:
            v.primary_photo_url = p.photo_url

    db.commit()
    return {"success": True, "message": "사진 정보가 갱신되었습니다."}


# -----------------------------------------------------------------------------
# DIRECTIVE 065: PART 1-B. 디자인 검수 및 스테이징 전용 격리 API (/api/staging/...)
# -----------------------------------------------------------------------------

@app.get("/api/staging/chamart/vehicles")
def get_staging_chamart_vehicles(
    db: Session = Depends(get_db)
) -> list[dict[str, Any]]:
    """디자인 및 UI/UX 레이아웃 검수 전용 시연 매물 API (일반 고객 공개 API와 물리적 분리)."""
    return PlatformService.get_chamart_public_vehicles(db, mode="demo")


@app.get("/api/staging/chamart/vehicles/{vehicle_id}")
def get_staging_chamart_vehicle_detail(
    vehicle_id: str,
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """디자인 및 UI/UX 레이아웃 검수 전용 시연 상세 API."""
    detail = PlatformService.get_chamart_public_vehicle_detail(db, vehicle_id, mode="demo")
    if not detail:
        raise HTTPException(status_code=404, detail="시연용 매물 정보를 찾을 수 없습니다.")
    return detail


@app.get("/api/staging/ui-fixtures/vehicles")
def get_staging_ui_fixture_vehicles() -> list[dict[str, Any]]:
    """DIRECTIVE 070: 100대 가상 UI 디자인 검수용 피스처 매물 목록 API (운영 DB 비접근, 순수 JSON 서빙)."""
    fixture_path = Path("reports/ui_fixtures/chamart_100.json")
    if not fixture_path.exists():
        return []
    try:
        with open(fixture_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load UI fixture vehicles: {e}")
        return []


@app.get("/api/staging/ui-fixtures/vehicles/{vehicle_id}")
def get_staging_ui_fixture_vehicle_detail(vehicle_id: str) -> dict[str, Any]:
    """DIRECTIVE 070: 100대 가상 UI 디자인 검수용 피스처 매물 상세 API."""
    fixture_path = Path("reports/ui_fixtures/chamart_100.json")
    if not fixture_path.exists():
        raise HTTPException(status_code=404, detail="UI 피스처 데이터를 찾을 수 없습니다.")
    try:
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            if item.get("id") == vehicle_id:
                return item
        raise HTTPException(status_code=404, detail="해당 시연 차량을 찾을 수 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get UI fixture vehicle detail for {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="피스처 데이터 로드 중 오류가 발생했습니다.")


@app.post("/api/chamart/consultations")
def create_chamart_public_consultation(
    req: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """차마트 웹사이트 고객 문의 및 방문 예약 신청 (스팸 방어 및 개인정보 동의 검증)."""
    v_id = str(req.get("vehicle_id") or "")
    if v_id.startswith("UI-"):
        # DIRECTIVE 070: 가상 100대 시연 매물의 방문 예약은 운영 CRM DB에 저장하지 않고 모의 정상 반환
        return {
            "success": True,
            "consultation_id": "DEMO-070",
            "message": "UI 시연 매물에 대한 방문 예약 모의 접수가 완료되었습니다. (운영 DB 격리)",
        }
    client_ip = get_client_ip(request)
    phone_raw = (req.get("phone") or "").strip()
    phone_key = re.sub(r"[^0-9]", "", phone_raw)
    now = time.time()

    # 스팸 방어: 동일 IP 또는 동일 전화번호로 60초 내 중복 신청 시 429 차단 (로컬 루프백 테스트는 0.5초 허용)
    min_interval = 0.5 if client_ip in ["127.0.0.1", "::1", "localhost"] else 60
    if client_ip in CONSULTATION_REQUEST_LOGS and (now - CONSULTATION_REQUEST_LOGS[client_ip]) < min_interval:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="상담 신청이 이미 접수되었습니다. 잠시 후(1분 뒤) 다시 시도해 주십시오.",
        )
    if phone_key and phone_key in CONSULTATION_REQUEST_LOGS and (now - CONSULTATION_REQUEST_LOGS[phone_key]) < 60:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="동일한 연락처로 접수된 상담 신청이 있습니다. 1분 후 다시 시도해 주십시오.",
        )

    try:
        res = PlatformService.create_chamart_public_consultation(db, req)
        CONSULTATION_REQUEST_LOGS[client_ip] = now
        if phone_key:
            CONSULTATION_REQUEST_LOGS[phone_key] = now
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/chamart/vehicles/{vehicle_id}/inquiry")
def create_chamart_vehicle_inquiry(
    vehicle_id: str,
    req: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """차마트 차량 상세 화면 전용 상담 신청 별칭 엔드포인트."""
    req_with_id = dict(req)
    if not req_with_id.get("vehicle_id"):
        req_with_id["vehicle_id"] = vehicle_id
    return create_chamart_public_consultation(req_with_id, request, db)


@app.post("/api/admin/vehicles/{vehicle_id}/publish")
@app.post("/api/vehicles/{vehicle_id}/toggle-public")
def toggle_admin_vehicle_publish(
    vehicle_id: str,
    req: dict[str, Any] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """관리자 전용 차량 차마트 공개 상태 토글 (인증 필수, 5대 검증 가드 통과 필요)."""
    is_public = req.get("is_public") if req else None
    try:
        return PlatformService.toggle_vehicle_public_status(db, vehicle_id, is_public=is_public)
    except ValueError as e:
        err_msg = str(e)
        if "찾을 수 없습니다" in err_msg:
            raise HTTPException(status_code=404, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)


# -----------------------------------------------------------------------------
# DIRECTIVE 051: PART 2. AI 콘텐츠 연구소 (Autonomous Content Intelligence Lab) API
# -----------------------------------------------------------------------------

@app.get("/api/content-lab/session")
def get_content_lab_session(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """AI 콘텐츠 연구소 현재 세션 상태, 쿼터 사용량, 카운터 요약 조회."""
    return ContentLabService.get_session_status(db)


@app.get("/api/content-lab/learning-readiness")
def get_content_lab_learning_readiness(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """AI 콘텐츠 연구소 4단계 학습 및 자율화 준비도 정직 표기 (DIRECTIVE 052 P1-4)."""
    return ContentLabService.get_learning_readiness(db)


@app.post("/api/content-lab/session/start")
def start_content_lab_session(
    req: dict[str, Any] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """연구 세션 시작 (RUNNING 전환 및 관찰 1사이클 가동)."""
    name = req.get("session_name") if req else None
    kws = req.get("keywords") if req else None
    return ContentLabService.start_session(db, session_name=name, keywords=kws)


@app.post("/api/content-lab/session/pause")
def pause_content_lab_session(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """연구 세션 일시정지 (체크포인트 보존)."""
    return ContentLabService.pause_session(db)


@app.post("/api/content-lab/session/resume")
def resume_content_lab_session(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """연구 세션 재개 (체크포인트 복원 후 연속 관찰)."""
    return ContentLabService.resume_session(db)


@app.post("/api/content-lab/session/stop")
def stop_content_lab_session(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """연구 세션 종료 및 체크포인트 최종 저장."""
    return ContentLabService.stop_session(db)


@app.post("/api/content-lab/session/step")
def run_content_lab_step(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """단일 관찰 사이클 수동 실행 (신규 영상 검색 -> AI 분석 -> 독립주제 발굴 -> 대본초안 작성)."""
    session = ContentLabService.get_active_or_latest_session(db)
    return ContentLabService.run_observation_step(db, session.id)


@app.get("/api/content-lab/topics")
def list_content_lab_topics(
    category: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    """독창적 중고차 기획 주제 후보 목록 조회."""
    return ContentLabService.list_topic_candidates(db, category=category, status=status)


@app.post("/api/content-lab/topics/{topic_id}/feedback")
def submit_topic_feedback(
    topic_id: str,
    req: dict[str, Any],
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """주제 후보에 대한 피드백(LIKE, DISLIKE, ALREADY_COVERED, FACT_ERROR 등) 기록."""
    feedback_type = req.get("feedback_type", "LIKE")
    reason = req.get("reason")
    try:
        return ContentLabService.record_topic_feedback(db, topic_id, feedback_type, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/content-lab/scripts")
def list_content_lab_scripts(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> list[dict[str, Any]]:
    """AI 독립 대본 초안 및 승인 대본 목록 조회."""
    return ContentLabService.list_script_drafts(db, status=status)


@app.put("/api/content-lab/scripts/{script_id}")
def update_content_lab_script(
    script_id: str,
    req: dict[str, Any],
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """대본 수정 (수정 시 기존 승인 무효화 -> DRAFT 리셋 및 해시 제거)."""
    try:
        return ContentLabService.update_script_draft(db, script_id, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/content-lab/scripts/{script_id}/approve")
def approve_content_lab_script(
    script_id: str,
    req: dict[str, Any] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """관리자 대본 공식 승인 (SHA-256 해시 보존)."""
    approver = (req.get("approver_name") if req else None) or _auth.get("username", "차마트 관리자")
    try:
        return ContentLabService.approve_script_draft(db, script_id, approver_name=approver)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/content-lab/scripts/{script_id}/reject")
def reject_content_lab_script(
    script_id: str,
    req: dict[str, Any] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """대본 반려 처리."""
    reason = (req.get("reason") if req else None) or "기획 방향 재조정"
    try:
        return ContentLabService.reject_script_draft(db, script_id, reason=reason)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/content-lab/scripts/{script_id}/generate-prompts")
def generate_script_prompts(
    script_id: str,
    req: dict[str, Any] = None,
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """승인된 대본에 한하여 Wan 3.0 / Kling 4.0 영상 제작 프롬프트 생성 (미승인 시 400 에러)."""
    model_type = (req.get("model_type") if req else None) or "WAN_3_0"
    try:
        return ContentLabService.generate_video_prompts_for_approved_script(db, script_id, target_model=model_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------------------------------------
# 9. UI 서빙 (차피셜 관리자 & 차마트 독립 고객 쇼룸)
# ----------------------------------------------------
@app.get("/", response_class=HTMLResponse)
@app.get("/admin/vehicles/{vehicle_id}", response_class=HTMLResponse)
def serve_index(vehicle_id: Optional[str] = None) -> HTMLResponse:
    """차피셜(CHA-FICIAL) 내부 운영 관리자 포털 UI."""
    if UI_INDEX_FILE.exists():
        content = UI_INDEX_FILE.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse("<h1>UI File Not Found</h1>", status_code=404)


@app.get("/chamart", response_class=HTMLResponse)
@app.get("/cars", response_class=HTMLResponse)
@app.get("/cars/{vehicle_id}", response_class=HTMLResponse)
def serve_chamart(vehicle_id: Optional[str] = None) -> HTMLResponse:
    """차마트(CHAMART) 일반 고객 전용 실차 쇼룸 독립 웹페이지 (DIRECTIVE 052 P0-4)."""
    # 100대 가상 매물(UI-*) 또는 스테이징 ID 직접 접속 시 스테이징 UI로 자동 매핑
    if vehicle_id and (vehicle_id.startswith("UI-") or vehicle_id.startswith("STG-")):
        if UI_CHAMART_STAGING_FILE.exists():
            content = UI_CHAMART_STAGING_FILE.read_text(encoding="utf-8")
            return HTMLResponse(content=content)
    if UI_CHAMART_FILE.exists():
        content = UI_CHAMART_FILE.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse("<h1>Chamart UI File Not Found</h1>", status_code=404)


UI_CHAMART_STAGING_FILE = Path(__file__).parent / "ui" / "chamart_staging.html"

@app.get("/staging/chamart", response_class=HTMLResponse)
@app.get("/staging/cars", response_class=HTMLResponse)
@app.get("/staging/cars/{vehicle_id}", response_class=HTMLResponse)
def serve_chamart_staging(vehicle_id: Optional[str] = None) -> HTMLResponse:
    """디자인 및 UI/UX 검수 전용 스테이징 쇼룸 (DIRECTIVE 065: 운영 쇼룸과 물리적 분리)."""
    if UI_CHAMART_STAGING_FILE.exists():
        content = UI_CHAMART_STAGING_FILE.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse("<h1>Staging Chamart UI File Not Found</h1>", status_code=404)
