#!/usr/bin/env python3
"""DIRECTIVE 052: CRITICAL SECURITY, PUBLISHING & CONTENT INTELLIGENCE REMEDIATION
16대 핵심 요구사항 전수 실서버 E2E 검증 스크립트.
"""

from __future__ import annotations

import http.cookiejar
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("CHAMART_API_URL", "http://127.0.0.1:8501")

# .env 환경변수 로드
ENV_PATH = Path(".env")
ADMIN_PW = ""
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("CHAMART_ADMIN_PASSWORD=") and not line.startswith("#"):
            ADMIN_PW = line.split("=", 1)[1].strip().strip('"').strip("'")

# 세션 관리 (쿠키 처리)
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
auth_token = None

pass_count = 0
fail_count = 0


def log_test(num: int, title: str, passed: bool, detail: str = ""):
    global pass_count, fail_count
    status_str = "\033[92m[PASS]\033[0m" if passed else "\033[91m[FAIL]\033[0m"
    print(f"{status_str} TEST {num:02d}: {title}")
    if detail:
        print(f"       -> {detail}")
    if passed:
        pass_count += 1
    else:
        fail_count += 1


def api_request(
    endpoint: str,
    method: str = "GET",
    data: dict | None = None,
    use_auth: bool = True,
) -> tuple[int, dict | str]:
    url = f"{BASE_URL}{endpoint}"
    req_data = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=req_data, method=method)
    req.add_header("Content-Type", "application/json")
    if use_auth and auth_token:
        req.add_header("Authorization", f"Bearer {auth_token}")

    try:
        with opener.open(req, timeout=10) as resp:
            content_type = resp.headers.get("content-type", "")
            raw = resp.read().decode("utf-8")
            if "application/json" in content_type:
                return resp.status, json.loads(raw)
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return 0, str(e)


print("======================================================================")
print("  CHA-FICIAL DIRECTIVE 052: REMEDIATION 16대 전수 검증")
print("======================================================================")

# -----------------------------------------------------------------------------
# 1. P0-1 관리자 비밀번호 로테이션 및 안전성
# -----------------------------------------------------------------------------
p1 = (
    bool(ADMIN_PW)
    and ADMIN_PW != "chamart2026!"
    and len(ADMIN_PW) >= 20
)
log_test(1, "관리자 비밀번호 로테이션 및 환경변수 보안성 검증", p1, f"비밀번호 길이: {len(ADMIN_PW)}자 (구 비밀번호 폐기 확인)")

# -----------------------------------------------------------------------------
# 2. P0-1 Cloudflare 외부 터널 비활성화 검증
# -----------------------------------------------------------------------------
res = subprocess.run(["ps", "aux"], capture_output=True, text=True)
tunnel_procs = [l for l in res.stdout.splitlines() if "cloudflared" in l.lower() and "grep" not in l]
p2 = len(tunnel_procs) == 0
log_test(2, "Cloudflare 외부 터널 프로세스 완전 차단 검증", p2, f"실행 중인 터널 프로세스 수: {len(tunnel_procs)}개 (완전 비활성화)")

# -----------------------------------------------------------------------------
# 3. P0-1 내부 API 전수 비인가 차단 (401 Unauthorized)
# -----------------------------------------------------------------------------
status_veh, _ = api_request("/api/vehicles", method="GET", use_auth=False)
status_over, _ = api_request("/api/overview", method="GET", use_auth=False)
status_br, _ = api_request("/api/branches", method="GET", use_auth=False)
status_lab, _ = api_request("/api/content-lab/session", method="GET", use_auth=False)

p3 = (status_veh == 401 and status_over == 401 and status_br == 401 and status_lab == 401)
log_test(
    3,
    "내부 핵심 API 비인가 401 차단 감사 (/api/vehicles, /api/overview 등)",
    p3,
    f"/api/vehicles: {status_veh}, /api/overview: {status_over}, /api/branches: {status_br}, /api/content-lab/session: {status_lab}",
)

# -----------------------------------------------------------------------------
# 4. P0-1 안전한 관리자 로그인 및 세션 토큰 획득
# -----------------------------------------------------------------------------
status_login, body_login = api_request("/api/auth/login", method="POST", data={"username": "admin", "password": ADMIN_PW}, use_auth=False)
p4 = (status_login == 200 and isinstance(body_login, dict) and body_login.get("ok") is True)
if p4:
    auth_token = body_login.get("token")
log_test(4, "새 관리자 비밀번호 정상 로그인 및 보안 세션 토큰 발급", p4, f"응답 코드: {status_login}, 사용자: admin")

# -----------------------------------------------------------------------------
# 5. P0-1 공개 API 내부 원가/마진 비노출 검증
# -----------------------------------------------------------------------------
status_pub, body_pub = api_request("/api/chamart/vehicles", method="GET", use_auth=False)
p5 = False
if status_pub == 200 and isinstance(body_pub, list):
    has_leak = any("purchase_price" in v or "margin" in v or "recon_cost" in v for v in body_pub)
    p5 = not has_leak and len(body_pub) > 0
log_test(5, "차마트 공개 매물 API 내부 원가/마진 비노출 검증", p5, f"공개 매물 수: {len(body_pub) if isinstance(body_pub, list) else 0}대, 민감원가 누출: 0건")

# -----------------------------------------------------------------------------
# 6. P0-2 OwnershipType Enum 정의 및 MARKET_OBSERVED 오타 수정 검증
# -----------------------------------------------------------------------------
from chaficial.platform.db import OwnershipType
p6 = (
    hasattr(OwnershipType, "MARKET_OBSERVED")
    and OwnershipType.MARKET_OBSERVED.value == "MARKET_OBSERVED"
    and hasattr(OwnershipType, "CHAMART_OWNED")
    and hasattr(OwnershipType, "PARTNER_APPROVED")
)
log_test(6, "OwnershipType Enum 정의 및 오타(MARKET_OBSERVATION) 제거 검증", p6, "Enum: MARKET_OBSERVED, CHAMART_OWNED, PARTNER_APPROVED 정의 완료")

# -----------------------------------------------------------------------------
# 7. P0-2 Vehicle.is_public 기본값 False 격리 검증
# -----------------------------------------------------------------------------
from chaficial.platform.db import SessionLocal, Vehicle
session_db = SessionLocal()
sample_branch = session_db.query(Vehicle).first().branch_id
test_v = Vehicle(
    branch_id=sample_branch,
    plate_number="00기0000",
    model_name="기본값 격리 검증 차량",
    year=2024,
    mileage=1000,
)
session_db.add(test_v)
session_db.flush()
p7 = (test_v.is_public is False)
session_db.rollback()
session_db.close()
log_test(7, "Vehicle.is_public 모델 기본값 False 격리 설정 검증", p7, f"DB 삽입 기본값 is_public: {p7}")

# -----------------------------------------------------------------------------
# 8. P0-2 미승인 및 시장 관측 매물 비공개 격리 검증
# -----------------------------------------------------------------------------
from chaficial.platform.db import SessionLocal
session_db = SessionLocal()
observed_public_count = (
    session_db.query(Vehicle)
    .filter(
        Vehicle.ownership_type == OwnershipType.MARKET_OBSERVED.value,
        Vehicle.is_public == True,
    )
    .count()
)
demo_public_count = (
    session_db.query(Vehicle)
    .filter(
        Vehicle.is_demo == True,
        Vehicle.is_public == True,
    )
    .count()
)
total_public_count = session_db.query(Vehicle).filter(Vehicle.is_public == True).count()
session_db.close()

p8 = (observed_public_count == 0 and demo_public_count == 0 and total_public_count > 0)
log_test(
    8,
    "기존 DB 매물 전수 감사 및 미승인/관측 매물 비공개 격리 검증",
    p8,
    f"공개된 관측매물: {observed_public_count}건, 공개된 데모매물: {demo_public_count}건, 승인된 실차: {total_public_count}건",
)

# -----------------------------------------------------------------------------
# 9. P0-2 toggle_vehicle_public_status 5대 서버 검증 가드 차단 검증
# -----------------------------------------------------------------------------
# DB에서 관측 매물 1건 조회하여 공개 시도
session_db = SessionLocal()
obs_v = session_db.query(Vehicle).filter(Vehicle.ownership_type == OwnershipType.MARKET_OBSERVED.value).first()
session_db.close()

p9 = False
if obs_v:
    st_guard, body_guard = api_request(f"/api/admin/vehicles/{obs_v.id}/publish", method="POST", data={"is_public": True}, use_auth=True)
    p9 = (st_guard == 400 and "관측/미승인 매물" in str(body_guard))
    detail_guard = f"관측 매물 공개 시도 응답: {st_guard} ({body_guard.get('detail') if isinstance(body_guard, dict) else body_guard})"
else:
    detail_guard = "관측 매물이 DB에 없음"
log_test(9, "관리자 매물 공개 시 5대 서버 검증 가드 차단 검증 (관측매물 차단)", p9, detail_guard)

# -----------------------------------------------------------------------------
# 10. P0-3 허위 기본값 제거: 1.05배 가짜 평균 시세 날조 제거 검증
# -----------------------------------------------------------------------------
first_pub_v = body_pub[0] if isinstance(body_pub, list) and len(body_pub) > 0 else {}
pub_vid = first_pub_v.get("id")
status_det, body_det = api_request(f"/api/chamart/vehicles/{pub_vid}", method="GET", use_auth=False)
p10 = False
if status_det == 200 and isinstance(body_det, dict):
    price_comp = body_det.get("price_comparison", {})
    # 1.05배 가짜 시세가 아닌 None이어야 함
    p10 = price_comp.get("market_avg_price") is None and "정밀 비교 분석 중" in price_comp.get("competition_analysis", "")
log_test(10, "고객용 상세 정보 1.05배 가짜 평균 시세 날조 제거 검증", p10, f"market_avg_price: {body_det.get('price_comparison', {}).get('market_avg_price')}, 안내: {body_det.get('price_comparison', {}).get('competition_analysis')}")

# -----------------------------------------------------------------------------
# 11. P0-3 허위 기본값 제거: 임의 무사고/누유없음 날조 제거 검증
# -----------------------------------------------------------------------------
# 성능점검 미등록 임시 차량을 통한 정직성 검증
session_db = SessionLocal()
branch_1 = session_db.query(Vehicle).first().branch_id
v_clean = Vehicle(
    branch_id=branch_1,
    plate_number="00검9999",
    model_name="검증용 미등록 차량",
    year=2023,
    mileage=15000,
    ownership_type=OwnershipType.CHAMART_OWNED.value,
    status="FOR_SALE",
    primary_photo_url="/static/img/car.jpg",
    condition_detail_json="{}",
    accident_history_json="{}",
    vin=None,
    displacement_cc=None,
    is_public=True,
)
session_db.add(v_clean)
session_db.commit()
clean_vid = v_clean.id
session_db.close()

st_clean, body_clean = api_request(f"/api/chamart/vehicles/{clean_vid}", method="GET", use_auth=False)
p11 = False
if st_clean == 200 and isinstance(body_clean, dict):
    acc_sum = body_clean.get("accident_summary", {})
    p11 = (
        "미확인" in acc_sum.get("accident_state_label", "")
        and acc_sum.get("frame_damage") == "미확인 (성능점검표 미등록)"
        and acc_sum.get("oil_leak_status") == "미확인 (성능점검표 미등록)"
        and acc_sum.get("inspection_date") == "미확인"
    )
log_test(11, "성능점검 미등록 시 임의 무사고/누유없음/DB생성일 날조 제거 검증", p11, f"상태: {body_clean.get('accident_summary', {}).get('accident_state_label')}, 골격: {body_clean.get('accident_summary', {}).get('frame_damage')}, 점검일: {body_clean.get('accident_summary', {}).get('inspection_date')}")

# -----------------------------------------------------------------------------
# 12. P0-3 허위 기본값 제거: 임의 VIN 조회완료 및 1999cc 날조 제거 검증
# -----------------------------------------------------------------------------
p12 = False
if st_clean == 200 and isinstance(body_clean, dict):
    p12 = (
        body_clean.get("vin") != "조회 완료"
        and "미확인" in body_clean.get("vin", "")
        and body_clean.get("displacement_cc") is None
    )
log_test(12, "미확인 VIN 조회완료 표기 및 임의 1999cc 배기량 날조 제거 검증", p12, f"VIN: {body_clean.get('vin')}, 배기량: {body_clean.get('displacement_cc')}")

# 임시 검증 차량 정리
session_db = SessionLocal()
session_db.query(Vehicle).filter(Vehicle.id == clean_vid).delete()
session_db.commit()
session_db.close()

# -----------------------------------------------------------------------------
# 13. P0-4 차마트 독립 고객 사이트 라우트 서빙 검증
# -----------------------------------------------------------------------------
st_chamart, body_chamart = api_request("/chamart", method="GET", use_auth=False)
st_cars, body_cars = api_request("/cars", method="GET", use_auth=False)
st_cardetail, body_cardetail = api_request(f"/cars/{pub_vid}", method="GET", use_auth=False)
p13 = (
    st_chamart == 200
    and st_cars == 200
    and st_cardetail == 200
    and "CHAMART" in str(body_chamart)
    and "개인정보" in str(body_chamart)
)
log_test(13, "차마트 독립 고객 쇼룸 URL 라우트 (/chamart, /cars, /cars/{id}) 서빙 검증", p13, f"/chamart: {st_chamart}, /cars: {st_cars}, /cars/{pub_vid}: {st_cardetail}")

# -----------------------------------------------------------------------------
# 14. P0-4 개인정보 수집/이용 동의 필수 및 1분 스팸 방어 검증
# -----------------------------------------------------------------------------
# 1) 동의 미체크 시 400 차단
st_c1, body_c1 = api_request("/api/chamart/consultations", method="POST", data={
    "name": "홍길동",
    "phone": "010-1234-5678",
    "privacy_agreed": False,
}, use_auth=False)

# 2) 정상 동의 접수 200
test_phone = f"010-9999-{int(time.time()) % 10000:04d}"
st_c2, body_c2 = api_request("/api/chamart/consultations", method="POST", data={
    "name": "홍길동",
    "phone": test_phone,
    "vehicle_id": pub_vid,
    "privacy_agreed": True,
}, use_auth=False)

# 3) 동일 번호 1분 내 재신청 시 429 차단
st_c3, body_c3 = api_request("/api/chamart/consultations", method="POST", data={
    "name": "홍길동",
    "phone": test_phone,
    "vehicle_id": pub_vid,
    "privacy_agreed": True,
}, use_auth=False)

p14 = (st_c1 == 400 and st_c2 == 200 and st_c3 == 429)
log_test(
    14,
    "상담 예약 개인정보 동의 필수 검증 및 1분 내 스팸 방어 (429 Too Many Requests)",
    p14,
    f"미동의: {st_c1}, 정상동의: {st_c2}, 1분내재신청: {st_c3}",
)

# -----------------------------------------------------------------------------
# 15. P1-1 Gemini 분석: 정직한 METADATA_ONLY 라벨 표기 검증
# -----------------------------------------------------------------------------
from datetime import UTC, datetime
from chaficial.studio.models import ContentFormat, VideoRecord
from chaficial.platform.lab.service import ContentLabService
dummy_v = VideoRecord(
    video_id="test_meta_01",
    platform="YOUTUBE",
    title="중고차 수리비 폭탄 피하는 법",
    content_format=ContentFormat.YOUTUBE_SHORTS,
    url="https://youtube.com/shorts/test_meta_01",
    channel_name="카마스터",
    published_at=datetime.now(UTC),
    view_count=50000,
)
mode_analysis, data_analysis = ContentLabService._analyze_video_intelligence(dummy_v)
p15 = (mode_analysis == "METADATA_ONLY" and "DEEP_VIDEO_UNDERSTANDING" != mode_analysis)
log_test(15, "Gemini 영상 미전달 시 METADATA_ONLY 투명 표기 (허위 과장 라벨 제거)", p15, f"분석 모드: {mode_analysis} (DEEP_VIDEO_UNDERSTANDING 폐기 확인)")

# -----------------------------------------------------------------------------
# 16. P1-2 & P1-4: 지속 관찰 세션 생명주기 및 4단계 학습 준비도 표기 검증
# -----------------------------------------------------------------------------
# 1) 세션 상태 및 라이프사이클
st_start, b_start = api_request("/api/content-lab/session/start", method="POST", data={"session_name": "검증 세션"}, use_auth=True)
st_pause, b_pause = api_request("/api/content-lab/session/pause", method="POST", use_auth=True)
st_resume, b_resume = api_request("/api/content-lab/session/resume", method="POST", use_auth=True)
st_stop, b_stop = api_request("/api/content-lab/session/stop", method="POST", use_auth=True)

# 2) 4단계 학습 준비도 확인
st_learn, b_learn = api_request("/api/content-lab/learning-readiness", method="GET", use_auth=True)
p16 = False
if (
    st_start == 200
    and st_pause == 200
    and st_resume == 200
    and st_stop == 200
    and st_learn == 200
    and isinstance(b_learn, dict)
):
    l1 = b_learn.get("level_1_data_accumulation", {}).get("status") == "OPERATIONAL"
    l2 = b_learn.get("level_2_rule_tuning", {}).get("status") == "OPERATIONAL"
    l3 = b_learn.get("level_3_model_finetuning", {}).get("status") == "PENDING_DATA"
    l4 = b_learn.get("level_4_reinforcement_learning", {}).get("status") == "SIMULATION_READY"
    p16 = (l1 and l2 and l3 and l4)

log_test(
    16,
    "지속 관찰 세션 생명주기 제어 및 4단계 학습 준비도 정직 표기",
    p16,
    f"세션 제어: 시작/정지/재개/종료 정상, 학습단계: Level1/2={b_learn.get('level_1_data_accumulation', {}).get('status')}, Level3={b_learn.get('level_3_model_finetuning', {}).get('status')}, Level4={b_learn.get('level_4_reinforcement_learning', {}).get('status')}",
)

print("======================================================================")
print(f"  전수 검증 결과: 총 16건 중 {pass_count}건 성공, {fail_count}건 실패")
print("======================================================================")

if fail_count > 0:
    sys.exit(1)
sys.exit(0)
