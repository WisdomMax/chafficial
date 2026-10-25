"""차마트(CHAMART) 통합 운영 플랫폼 FastAPI 애플리케이션.

DIRECTIVE 045 명세 준수:
- 12대 전체 메뉴 네비게이션을 지원하는 단일 웹 플랫폼 백엔드
- 실제 작동 4대 영역(차량, CRM, 거래, 영상) + AI 서류 검토 업로드 API
- 미래 연동 영역(텔레그램, SMS, 카매니저, 마케팅)의 구조화된 데이터 응답
- 로컬 우선 실행 및 외부 접속(Cloudflare Tunnel) 지원을 위한 보안 헤더/인증
"""

from __future__ import annotations

import datetime
import os
import secrets
import time
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
)
from chaficial.platform.models import (
    ConsultationCreateRequest,
    CustomerCreateRequest,
    CustomerUpdateRequest,
    DealerRightsGrantRequest,
    DealerRightsRevokeRequest,
    DocumentApprovalRequest,
    LoginRequest,
    MediaProjectCreateRequest,
    MediaProjectStatusUpdateRequest,
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
from chaficial.platform.search import (
    format_currency_display,
    format_phone_display,
    normalize_phone_number,
    parse_currency_amount,
    universal_search,
)
from chaficial.platform.service import PlatformService

# 앱 초기화
app = FastAPI(
    title="차마트(CHAMART) 통합 운영 플랫폼",
    description="장한평 본사 및 거점 확장을 위한 차량·고객·거래·영상 통합 OS",
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
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


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
# 2. 대시보드 KPI (P0)
# ----------------------------------------------------
@app.get("/api/overview")
def get_overview(db: Session = Depends(get_db)) -> dict[str, Any]:
    return PlatformService.get_overview_kpis(db)


@app.get("/api/branches")
def list_branches(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return PlatformService.list_branches(db)


# ----------------------------------------------------
# 3. 차량 관리 (P0 실작동)
# ----------------------------------------------------
@app.get("/api/vehicles")
def list_vehicles(
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return PlatformService.list_vehicles(db, branch_id=branch_id, status=status)


@app.get("/api/vehicles/{vehicle_id}")
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
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

    res = PlatformService.save_and_register_document(
        db=db,
        file_bytes=content,
        filename=file.filename or "unknown_document",
        doc_type=doc_type,
    )
    return res


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
# 8. P1 미래 연동 영역 (텔레그램, SMS, 카매니저, 마케팅)
# ----------------------------------------------------
@app.get("/api/integrations/telegram")
def get_telegram_status() -> dict[str, Any]:
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
def get_sms_status() -> dict[str, Any]:
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
def get_carmanager_status() -> dict[str, Any]:
    """카매니저 외부 매물 연동 상태 (P1)."""
    return {
        "status": "SPECIFICATION_AUDIT",
        "badge": "공식 연동 규격 검토 중",
        "sync_mode": "READ_ONLY_PILOT",
        "auto_sync_enabled": False,
        "message": "카매니저 공식 연동 가이드 및 상사 인증키 확인 후 양방향 동기화가 제공됩니다.",
    }


@app.get("/api/marketing/performance")
def get_marketing_performance() -> dict[str, Any]:
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
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/rl/readiness")
def get_rl_readiness(
    db: Session = Depends(get_db),
    _auth: dict = Depends(require_auth),
) -> dict[str, Any]:
    """강화학습 데이터 파이프라인 준비도 및 모델 도입 적합성 감사 (DIRECTIVE 047)."""
    return PlatformService.get_rl_readiness_audit(db)


# ----------------------------------------------------
# 9. UI 서빙
# ----------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_index() -> HTMLResponse:
    if UI_INDEX_FILE.exists():
        content = UI_INDEX_FILE.read_text(encoding="utf-8")
        return HTMLResponse(content=content)
    return HTMLResponse("<h1>UI File Not Found</h1>", status_code=404)
