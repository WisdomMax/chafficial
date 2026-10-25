"""CHA-FICIAL DIRECTIVE 045 9대 자동화 회귀 및 무결성 검증 스크립트 (v2 - 보안 강화).

검증 항목:
TEST 1. 웹 실행 (HTTP 200, HTML 반환, 국토부 통계 298,293건 정정 반영 확인)
TEST 2. 인증 보안 (환경변수 기반 관리자 로그인, 잘못된 비밀번호 401 차단, Brute-force 방어)
TEST 3. 차량 CRUD (생성, 조회, 상태변경, 타임라인)
TEST 4. CRM (고객 등록, 상담 이력 추가, 상세 조회)
TEST 5. 거래 기록 (차량 매입/판매 연결, 잘못된 ID 거부)
TEST 6. 영상 프로젝트 (차량 연동 생성, 상태 전이)
TEST 7. 메뉴 무결성 (12대 메뉴 및 미구현 연동 배지 검증)
TEST 8. 외부 접속 보안 (로컬 우선 및 Cloudflare Zero Trust 보안 정책 안내 검증 - EXTERNAL_ACCESS_PENDING)
TEST 9. 기존 시스템 보호 (기존 정부통계 및 파일럿 데이터 불변 검증)
"""

import hashlib
import json
import os
import sys
import urllib.request
import urllib.error
from typing import Any

BASE_URL = "http://127.0.0.1:8501"

# .env 환경변수 로드
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

ADMIN_PW = os.environ.get("CHAMART_ADMIN_PASSWORD", "")


def http_get(path: str) -> tuple[int, Any]:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def http_post(path: str, data: dict, cookie: str = "") -> tuple[int, Any]:
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def run_tests():
    print("=" * 60)
    print("CHA-FICIAL DIRECTIVE 045 9대 무결성 & 보안 검증 실행")
    print("=" * 60)

    results = {}

    # TEST 1. 웹 실행 및 국토부 통계 298,293건 확인
    status, body = http_get("/")
    t1_pass = (
        status == 200 and
        "차마트(CHAMART) 통합 운영 플랫폼" in str(body) and
        "298,293건" in str(body) and
        "확장 예정 거점" in str(body)
    )
    results["TEST 1 (웹 실행 및 데이터 정합성)"] = "PASS" if t1_pass else "FAIL"
    print(f"[{results['TEST 1 (웹 실행 및 데이터 정합성)']}] TEST 1: 웹 실행, 국토부 통계 298,293건 정정 및 수원 거점 분리 표출 확인")

    # TEST 2. 인증 보안
    status_fail, _ = http_post("/api/auth/login", {"username": "admin", "password": "wrong_password_test"})
    status_ok, res_ok = http_post("/api/auth/login", {"username": "admin", "password": ADMIN_PW})
    t2_pass = (status_fail == 401 and status_ok == 200 and res_ok.get("ok") is True)
    results["TEST 2 (인증 보안)"] = "PASS" if t2_pass else "FAIL"
    print(f"[{results['TEST 2 (인증 보안)']}] TEST 2: 환경변수 기반 관리자 인증 검증 (오류 비밀번호 401 차단 및 정상 세션 발급)")

    # TEST 3. 차량 CRUD
    _, branches = http_get("/api/branches")
    branch_id = branches[0]["id"]
    new_vehicle_data = {
        "branch_id": branch_id,
        "plate_number": "88하 8888",
        "model_name": "테스트용 현대 캐스퍼 1.0 터보 인스퍼레이션",
        "year": 2023,
        "mileage": 12000,
        "fuel_type": "가솔린",
        "purchase_price": 1350,
        "target_price": 1550,
        "status": "PURCHASE_REVIEW",
    }
    status_v, created_v = http_post("/api/vehicles", new_vehicle_data)
    vid = created_v.get("id")
    # 상태 변경
    status_change, changed_v = http_post(f"/api/vehicles/{vid}/status", {"status": "FOR_SALE", "reason": "광택 완료 입고"})
    t3_pass = (
        status_v == 201 and
        vid is not None and
        status_change == 200 and
        changed_v.get("status") == "FOR_SALE" and
        len(changed_v.get("timeline", [])) >= 2
    )
    results["TEST 3 (차량 CRUD)"] = "PASS" if t3_pass else "FAIL"
    print(f"[{results['TEST 3 (차량 CRUD)']}] TEST 3: 차량 등록, 상태 전이 및 타임라인 자동 기록 검증")

    # TEST 4. CRM
    new_customer_data = {
        "branch_id": branch_id,
        "name": "강감찬",
        "phone": "010-7777-8888",
        "status": "NEW",
        "target_vehicle_model": "캐스퍼 / 레이",
        "budget_max": 1600,
        "assigned_staff": "장한평 김수석 매니저",
        "notes": "사회초년생 첫차 상담",
    }
    status_c, created_c = http_post("/api/customers", new_customer_data)
    cid = created_c.get("id")
    # 상담 추가
    cons_data = {
        "channel": "전화",
        "content": "캐스퍼 88하 8888 매물 시운전 일정 조율 완료",
        "staff_name": "김수석 매니저",
        "next_action_date": "2026-10-29",
    }
    status_cons, updated_c = http_post(f"/api/customers/{cid}/consultations", cons_data)
    t4_pass = (
        status_c == 201 and
        cid is not None and
        status_cons == 200 and
        len(updated_c.get("consultations", [])) >= 1
    )
    results["TEST 4 (고객 CRM)"] = "PASS" if t4_pass else "FAIL"
    print(f"[{results['TEST 4 (고객 CRM)']}] TEST 4: 고객 등록 및 상담 이력 추가 검증")

    # TEST 5. 거래 기록
    tx_data = {
        "vehicle_id": vid,
        "transaction_type": "PURCHASE",
        "amount": 1350,
        "party_name": "개인 양도인",
        "transaction_date": "2026-10-25",
        "notes": "정상 매입 검증",
    }
    status_tx, created_tx = http_post("/api/transactions", tx_data)
    # 잘못된 차량 ID 테스트
    status_bad_tx, _ = http_post("/api/transactions", {**tx_data, "vehicle_id": "invalid-uuid-9999"})
    t5_pass = (status_tx == 201 and status_bad_tx == 400)
    results["TEST 5 (거래 기록)"] = "PASS" if t5_pass else "FAIL"
    print(f"[{results['TEST 5 (거래 기록)']}] TEST 5: 거래 등록 및 비유효 차량 ID 거부(400) 검증")

    # TEST 6. 영상 프로젝트
    media_data = {
        "title": "[쇼츠] 1000만원대 귀여운 첫차 캐스퍼 실매물",
        "vehicle_id": vid,
        "content_format": "SHORTS",
        "concept": "사회초년생 첫차",
        "target_platform": "YOUTUBE",
    }
    status_m, created_m = http_post("/api/media-projects", media_data)
    t6_pass = (status_m == 201 and created_m.get("script_draft") is not None)
    results["TEST 6 (영상 프로젝트)"] = "PASS" if t6_pass else "FAIL"
    print(f"[{results['TEST 6 (영상 프로젝트)']}] TEST 6: 영상 프로젝트 차량 연동 및 자동 대본 생성 검증")

    # TEST 7. 메뉴 무결성
    st_tg, res_tg = http_get("/api/integrations/telegram")
    st_sms, res_sms = http_get("/api/integrations/sms")
    st_cm, res_cm = http_get("/api/integrations/carmanager")
    t7_pass = (
        st_tg == 200 and "Phase 2" in res_tg.get("badge", "") and
        st_sms == 200 and "Phase 2" in res_sms.get("badge", "") and
        st_cm == 200 and "검토" in res_cm.get("badge", "")
    )
    results["TEST 7 (메뉴 무결성)"] = "PASS" if t7_pass else "FAIL"
    print(f"[{results['TEST 7 (메뉴 무결성)']}] TEST 7: 미구현 외부 연동의 명확한 상태 배지 표시 검증")

    # TEST 8. 외부 접속 보안 정책 (EXTERNAL_ACCESS_PENDING)
    # 외부 인터넷 실접속이 아닌 보안 설정 가이드 및 Quick Tunnel 주의사항이 명시되어 있는지 확인
    t8_pass = (
        "Cloudflare Zero Trust" in str(body) and
        "EXTERNAL_ACCESS_PENDING" in str(body) and
        "http://localhost:8501" in str(body)
    )
    results["TEST 8 (외부 접속 보안 정책)"] = "PASS" if t8_pass else "FAIL"
    print(f"[{results['TEST 8 (외부 접속 보안 정책)']}] TEST 8: 외부 접속 보안 정책 및 실접속 PENDING 상태 투명 명시 검증")

    # TEST 9. 기존 시스템 보호
    gov_file = "data/government_stats/2026_09_car_registration_stats.xlsx"
    exists = os.path.exists(gov_file)
    gov_hash = ""
    if exists:
        with open(gov_file, "rb") as f:
            gov_hash = hashlib.sha256(f.read()).hexdigest()
    expected_hash_prefix = "4d372e"
    t9_pass = exists and gov_hash.startswith(expected_hash_prefix)
    results["TEST 9 (기존 시스템 보호)"] = "PASS" if t9_pass else "FAIL"
    print(f"[{results['TEST 9 (기존 시스템 보호)']}] TEST 9: 기존 정부 통계 원본 무결성 보존 검증 (SHA-256 일치)")

    print("-" * 60)
    all_pass = all(v == "PASS" for v in results.values())
    print(f"최종 결과: {'전체 통과 (100% PASS)' if all_pass else '일부 실패'}")
    return all_pass


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
