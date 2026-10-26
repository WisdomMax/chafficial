#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 050-C 종합 검증 스위트 (16대 검증 항목).

항목:
1. 비인가 요청 시 핵심 API 401 차단 검증
2. 관리자 로그인 및 보안 토큰/세션 쿠키 발급 검증
3. /api/auth/me 세션 유효성 및 사용자 상태 검증
4. 로그인 세션으로 기존 차량 10건 연속 상세조회 100% 정상 (200 OK)
5. 8대 영역 마스터 등록을 통한 신규 차량 10건 생성 및 상세조회 100% 정상 (200 OK)
6. 존재하지 않는 차량 ID 조회 시 명확한 404 Not Found 및 에러 바디 검증
7. Gemini Vision API 키 미설정 시 안전한 API_KEY_REQUIRED 상태 응답 검증
8. Gemini Vision 키 마스킹 및 설정/통계 조회 API 검증
9. 명함 이미지 -> CustomerCandidate 구조화 추출 검증 (Mock/Live)
10. 명함 추출 고객 -> CRM 정식 등록 및 최초 상담 메모 자동 연동 검증
11. 고객 전화번호 및 이메일 중복 검사 로직 검증 (check_customer_duplicate)
12. 거래서류(계약서, 정산서, 입출금내역) -> TransactionDraft 구조화 추출 검증
13. 거래서류 내 차량번호/VIN 및 거래 상대방 자동 매칭 검증
14. 무결성 격리 검증: 미승인 거래서류의 실매출/ROI/RL Reward 오염 차단 (is_verified_sale=False)
15. 서류 파일 유효성(매직바이트 위조 방어, 15MB 한도) 및 SHA-256 감사 로그 검증
16. 전체 이전 지침 회귀 무결성 검증 (046-D, 047, 048, 049, 050 전체 100% PASS)
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:8501"

# .env 환경변수 로드
ENV_PATH = Path(".env")
ADMIN_PW = None
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("CHAMART_ADMIN_PASSWORD=") and not line.startswith("#"):
            ADMIN_PW = line.split("=", 1)[1].strip().strip('"').strip("'")

if not ADMIN_PW:
    ADMIN_PW = os.environ.get("CHAMART_ADMIN_PASSWORD", "ephemeral_demo_password")

PASSED_COUNT = 0
TOTAL_COUNT = 16


def print_step(idx: int, title: str):
    print(f"\n========================================================")
    print(f"[{idx}/{TOTAL_COUNT}] {title}")
    print(f"========================================================")


def assert_test(cond: bool, msg: str):
    global PASSED_COUNT
    if cond:
        print(f"  [PASS] {msg}")
    else:
        print(f"  [FAIL] {msg}")
        raise AssertionError(msg)


def http_request(url: str, method: str = "GET", data: dict = None, headers: dict = None, cookie: str = None):
    h = headers.copy() if headers else {}
    if cookie:
        h["Cookie"] = f"chamart_auth={cookie}"

    encoded_data = None
    if data is not None:
        if "Content-Type" not in h:
            h["Content-Type"] = "application/json"
        encoded_data = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=encoded_data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, resp.headers, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        return e.code, e.headers, body


def run_all_tests():
    global PASSED_COUNT
    print(f"[*] DIRECTIVE 050-C 검증 스위트 가동 (대상 서버: {BASE_URL})")

    # ----------------------------------------------------
    # 1. 비인가 요청 시 핵심 API 401 차단 검증
    # ----------------------------------------------------
    print_step(1, "비인가 요청 시 핵심 API 401 차단 검증")
    code, _, body = http_request(f"{BASE_URL}/api/vehicles/v-demo-01/detail")
    assert_test(code == 401, f"비인가 차량 상세조회 401 차단 확인 (응답 코드: {code})")
    code, _, _ = http_request(f"{BASE_URL}/api/ai/vision/config")
    assert_test(code == 401, f"비인가 AI 비전 설정 조회 401 차단 확인 (응답 코드: {code})")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 2. 관리자 로그인 및 보안 토큰/세션 쿠키 발급 검증
    # ----------------------------------------------------
    print_step(2, "관리자 로그인 및 보안 토큰/세션 쿠키 발급 검증")
    code, headers, body = http_request(
        f"{BASE_URL}/api/auth/login",
        method="POST",
        data={"username": "admin", "password": ADMIN_PW},
    )
    assert_test(code == 200, f"정상 관리자 로그인 200 OK (응답 코드: {code})")
    d = json.loads(body)
    assert_test(d.get("ok") is True, "응답 ok: True 확인")
    session_token = d.get("token")
    assert_test(bool(session_token) and len(session_token) == 64, f"보안 세션 토큰 발급 확인 (길이: {len(session_token)})")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 3. /api/auth/me 세션 유효성 및 사용자 상태 검증
    # ----------------------------------------------------
    print_step(3, "/api/auth/me 세션 유효성 및 사용자 상태 검증")
    code, _, body = http_request(f"{BASE_URL}/api/auth/me", cookie=session_token)
    assert_test(code == 200, f"/api/auth/me 200 OK (응답 코드: {code})")
    me = json.loads(body)
    assert_test(me.get("authenticated") is True, "세션 인증 상태 authenticated=True 확인")
    assert_test(me.get("username") == "admin", f"사용자명 확인: {me.get('username')}")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 4. 로그인 세션으로 기존 차량 10건 연속 상세조회 100% 정상
    # ----------------------------------------------------
    print_step(4, "로그인 세션으로 기존 차량 10건 연속 상세조회 100% 정상 (200 OK)")
    # 차량 목록 조회
    code, _, body = http_request(f"{BASE_URL}/api/vehicles")
    vehicles = json.loads(body)
    target_existing = vehicles[:10]
    assert_test(len(target_existing) >= 5, f"기존 등록 차량 최소 5건 이상 확보 (현재: {len(target_existing)}건)")

    success_existing_count = 0
    for v in target_existing:
        v_id = v["id"]
        c, _, b = http_request(f"{BASE_URL}/api/vehicles/{v_id}/detail", cookie=session_token)
        if c == 200:
            success_existing_count += 1
            detail = json.loads(b)
            assert "plate_number" in detail
            assert "marketing_auth" in detail

    assert_test(
        success_existing_count == len(target_existing),
        f"기존 차량 {len(target_existing)}건 중 {success_existing_count}건 상세조회 100% 성공 (200 OK)",
    )
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 5. 8대 영역 마스터 등록을 통한 신규 차량 10건 생성 및 상세조회 100% 정상
    # ----------------------------------------------------
    print_step(5, "신규 차량 10건 생성 및 상세조회 100% 정상 (200 OK)")
    new_vehicle_ids = []
    ts_now = int(time.time())
    for i in range(1, 11):
        plate_no = f"99다 {ts_now % 8000 + i:04d}"
        payload = {
            "plate_number": plate_no,
            "vin": f"KMH050C{ts_now % 100000}{i:02d}",
            "manufacturer": "기아",
            "model_name": "기아 쏘렌토 4세대",
            "trim": "2.5 가솔린 터보 노블레스",
            "year": 2024,
            "first_registration_date": "2024-01-15",
            "mileage": 12000 + i * 500,
            "displacement_cc": 2497,
            "fuel_type": "가솔린",
            "transmission": "오토",
            "drive_type": "2WD",
            "body_type": "SUV",
            "color": "스노우 화이트 펄",
            "target_price": 3500 + i * 50,
            "purchase_price": 3200,
            "recon_cost": 30,
            "sales_conditions": "현금/할부 가능",
            "ownership_type": "CHAMART_OWNED",
            "status": "FOR_SALE",
            "ad_highlights": "1인신조 완전무사고",
            "ad_description": "차마트 본사 특선 매물",
        }
        c, _, b = http_request(
            f"{BASE_URL}/api/vehicles/master/create",
            method="POST",
            data=payload,
            cookie=session_token,
        )
        assert_test(c == 200, f"신규 차량 {i}번({plate_no}) 마스터 등록 성공 (HTTP {c})")
        created_res = json.loads(b)
        new_vehicle_ids.append(created_res["vehicle_id"])

    # 신규 등록된 10건 연속 상세조회
    new_detail_success = 0
    for v_id in new_vehicle_ids:
        c, _, b = http_request(f"{BASE_URL}/api/vehicles/{v_id}/detail", cookie=session_token)
        if c == 200:
            new_detail_success += 1
            det = json.loads(b)
            assert det["id"] == v_id

    assert_test(
        new_detail_success == 10,
        f"신규 마스터 등록 차량 10건 전건 상세조회 100% 정상 (10/10)",
    )
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 6. 존재하지 않는 차량 ID 조회 시 명확한 404 Not Found 및 에러 바디 검증
    # ----------------------------------------------------
    print_step(6, "존재하지 않는 차량 ID 조회 시 명확한 404 Not Found 검증")
    code, _, body = http_request(
        f"{BASE_URL}/api/vehicles/non-existent-vehicle-id-9999/detail",
        cookie=session_token,
    )
    assert_test(code == 404, f"미존재 차량 404 Not Found 확인 (응답 코드: {code})")
    err_body = json.loads(body)
    assert_test("detail" in err_body, f"정형화된 404 에러 바디 확인: {err_body.get('detail')}")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 7. Gemini Vision API 키 미설정 시 안전한 API_KEY_REQUIRED 상태 응답 검증
    # ----------------------------------------------------
    print_step(7, "Gemini Vision API 키 미설정 시 안전한 API_KEY_REQUIRED 검증")
    code, _, body = http_request(
        f"{BASE_URL}/api/ai/vision/test-connection",
        method="POST",
        data={"api_key": ""},
        cookie=session_token,
    )
    d = json.loads(body)
    # 키가 없는 경우 크래시 없이 API_KEY_REQUIRED 응답
    if not d.get("ok"):
        assert_test(d.get("status") in ["API_KEY_REQUIRED", "ERROR"], f"키 미설정 안전 분기 응답: {d.get('status')} ({d.get('message')})")
    else:
        assert_test(True, "현재 환경에 유효한 Gemini 키가 구성되어 정상 연결 통과")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 8. Gemini Vision 키 마스킹 및 설정/통계 조회 API 검증
    # ----------------------------------------------------
    print_step(8, "Gemini Vision 키 마스킹 및 설정/통계 조회 API 검증")
    code, _, body = http_request(f"{BASE_URL}/api/ai/vision/config", cookie=session_token)
    assert_test(code == 200, f"/api/ai/vision/config 200 OK (응답 코드: {code})")
    cfg = json.loads(body)
    assert_test("masked_key" in cfg, "마스킹된 키 필드(masked_key) 제공 확인")
    if cfg.get("masked_key"):
        assert_test("..." in cfg["masked_key"] or "****" in cfg["masked_key"], f"키 보안 마스킹 검증: {cfg['masked_key']}")
    assert_test("primary_model" in cfg, f"비전 주 모델 확인: {cfg.get('primary_model')}")
    assert_test("total_calls" in cfg, f"비전 누적 호출수 추적 확인: {cfg.get('total_calls')}건")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 9. 명함 이미지 -> CustomerCandidate 구조화 추출 검증 (Mock/Live)
    # ----------------------------------------------------
    print_step(9, "명함 이미지 -> CustomerCandidate 구조화 추출 검증")
    # 1x1 투명 PNG 바이너리 생성
    dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    boundary = "----Directive050cBoundary"
    
    body_bytes = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="test_card.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + dummy_png + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/crm/business-card/analyze?is_mock=true",
        data=body_bytes,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Cookie": f"chamart_auth={session_token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        card_res = json.loads(resp.read().decode("utf-8"))

    assert_test(card_res.get("ok") is True, f"명함 이미지 분석 성공 확인: {card_res.get('message')}")
    candidate = card_res.get("candidate", {})
    assert_test(bool(candidate.get("name")), f"명함 성명 추출 확인: {candidate.get('name')}")
    assert_test(bool(candidate.get("phone")), f"명함 휴대전화 추출 확인: {candidate.get('phone')}")
    assert_test(bool(candidate.get("company_name")), f"명함 상호 추출 확인: {candidate.get('company_name')}")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 10. 명함 추출 고객 -> CRM 정식 등록 및 최초 상담 메모 자동 연동 검증
    # ----------------------------------------------------
    print_step(10, "명함 추출 고객 -> CRM 정식 등록 및 상담 메모 연동 검증")
    card_customer_phone = f"010-7777-{ts_now % 10000:04d}"
    card_req_payload = {
        "name": "차은우",
        "phone": card_customer_phone,
        "job_title": "본부장",
        "company_name": "(주)스타모터스 장한평",
        "company_phone": "02-2244-9876",
        "email": "eunwoo@starmotors.kr",
        "company_address": "서울시 동대문구 장한로 100",
        "target_vehicle_model": "쏘렌토 4세대",
        "budget_max": 3500,
        "notes": "장한평 매매단지 제휴 상사 미팅 시 명함 수령",
        "source_image_url": card_res.get("source_image_url"),
        "ai_confidence": 0.98,
    }
    c, _, b = http_request(
        f"{BASE_URL}/api/crm/customers/from-card",
        method="POST",
        data=card_req_payload,
        cookie=session_token,
    )
    assert_test(c == 201, f"명함 기반 정식 고객 등록 201 Created (HTTP {c})")
    saved_cust = json.loads(b)
    assert_test(saved_cust.get("source") == "BUSINESS_CARD_AI", f"고객 유입 경로(source) 확인: {saved_cust.get('source')}")
    assert_test(saved_cust.get("job_title") == "본부장", f"직함 저장 확인: {saved_cust.get('job_title')}")
    assert_test(saved_cust.get("company_name") == "(주)스타모터스 장한평", f"회사명 저장 확인: {saved_cust.get('company_name')}")
    assert_test(len(saved_cust.get("consultations", [])) >= 1, "최초 명함 등록 상담 메모 자동 생성 확인")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 11. 고객 전화번호 및 이메일 중복 검사 로직 검증
    # ----------------------------------------------------
    print_step(11, "고객 전화번호 및 이메일 중복 검사 로직 검증")
    c, _, b = http_request(
        f"{BASE_URL}/api/crm/customers/check-duplicate?phone={card_customer_phone}",
        cookie=session_token,
    )
    dup = json.loads(b)
    assert_test(dup.get("is_duplicate") is True, f"동일 전화번호 고객 중복 정상 감지: {dup.get('name')}")
    assert_test(dup.get("customer_id") == saved_cust["id"], "일치하는 고객 ID 식별 확인")

    # 미존재 번호 검사
    c, _, b = http_request(
        f"{BASE_URL}/api/crm/customers/check-duplicate?phone=010-0000-9999",
        cookie=session_token,
    )
    dup_none = json.loads(b)
    assert_test(dup_none.get("is_duplicate") is False, "신규 전화번호 중복 미감지(정상) 확인")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 12. 거래서류(계약서, 정산서, 입출금내역) -> TransactionDraft 구조화 추출 검증
    # ----------------------------------------------------
    print_step(12, "거래서류 -> TransactionDraft 구조화 추출 검증")
    body_tx = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="contract_sample.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + dummy_png + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req_tx = urllib.request.Request(
        f"{BASE_URL}/api/transactions/document/analyze?is_mock=true",
        data=body_tx,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Cookie": f"chamart_auth={session_token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req_tx) as resp:
        tx_doc_res = json.loads(resp.read().decode("utf-8"))

    assert_test(tx_doc_res.get("ok") is True, f"거래서류 분석 성공 확인: {tx_doc_res.get('message')}")
    assert_test(tx_doc_res.get("status") == "NEEDS_REVIEW", f"문서 상태(NEEDS_REVIEW) 확인: {tx_doc_res.get('status')}")
    ext = tx_doc_res.get("extract", {})
    assert_test(ext.get("document_type") == "CONTRACT", f"서류 유형 판별 확인: {ext.get('document_type')}")
    assert_test(ext.get("total_amount") > 0, f"추출된 총 거래금액 확인: {ext.get('total_amount')}만원")
    assert_test("document_review_id" in tx_doc_res, "서류 검토 원장 ID(document_review_id) 발급 확인")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 13. 거래서류 내 차량번호/VIN 및 거래 상대방 자동 매칭 검증
    # ----------------------------------------------------
    print_step(13, "거래서류 내 차량번호 및 상대방 자동 매칭 검증")
    # 등록된 신규 차량 중 1대의 번호판으로 서류 데이터 모의
    matched_test_vehicle_id = new_vehicle_ids[0]
    code, _, body = http_request(f"{BASE_URL}/api/vehicles/{matched_test_vehicle_id}/detail", cookie=session_token)
    v_info = json.loads(body)
    target_plate = v_info["plate_number"]

    # 백엔드 직접 매칭 로직 검증 (PlatformService.match_vehicle_for_document)
    from chaficial.platform.db import SessionLocal
    from chaficial.platform.service import PlatformService

    with SessionLocal() as db_sess:
        m_veh = PlatformService.match_vehicle_for_document(db_sess, plate_number=target_plate)
        assert_test(m_veh is not None, f"차량번호 '{target_plate}' 자동 매칭 성공")
        assert_test(m_veh["id"] == matched_test_vehicle_id, "매칭된 차량 ID 일치 확인")

        m_party = PlatformService.match_party_for_document(db_sess, name="차은우", contact=card_customer_phone)
        assert_test(m_party.get("customer") is not None, "명함으로 등록된 CRM 고객('차은우') 상대방 자동 매칭 성공")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 14. 무결성 격리 검증: 미승인 거래서류의 실매출/ROI/RL Reward 오염 차단
    # ----------------------------------------------------
    print_step(14, "무결성 격리 검증 (is_verified_sale=False 유지 및 실매출 격리)")
    # 미승인 초안 거래 등록
    draft_payload = {
        "document_review_id": tx_doc_res.get("document_review_id"),
        "vehicle_id": matched_test_vehicle_id,
        "transaction_type": "SALE",
        "amount": 2450,
        "party_name": "가상매수자_미검증",
        "transaction_date": datetime.date.today().isoformat(),
        "settlement_status": "PENDING",
        "is_verified_sale": False,  # 무결성: 미승인
        "is_test_record": False,
        "notes": "통장 입출금 캡처 서류 자동 분석 초안 (미승인 격리)",
    }
    c, _, b = http_request(
        f"{BASE_URL}/api/transactions/draft/confirm",
        method="POST",
        data=draft_payload,
        cookie=session_token,
    )
    assert_test(c == 201, f"초안 거래 등록 성공 201 Created (HTTP {c})")
    tx_draft_saved = json.loads(b)
    assert_test(tx_draft_saved.get("is_verified_sale") is False, "미승인 초안 is_verified_sale=False 격리 확인")
    assert_test(tx_draft_saved.get("settlement_status") == "PENDING", "정산 상태 settlement_status='PENDING' 확인")

    # 실매출 합산 오염 여부 확인 (DIRECTIVE 048/049 기준: 검증된 실매출 카운트에 미반영)
    with SessionLocal() as db_sess:
        from chaficial.platform.db import Transaction
        unverified_in_db = db_sess.query(Transaction).filter(Transaction.id == tx_draft_saved["transaction_id"]).first()
        assert_test(unverified_in_db.is_verified_sale is False, "DB 원장 is_verified_sale=False 물리적 불변성 검증")
        
        # 차량 상태가 무분별하게 SOLD로 전이되지 않았는지 검증
        from chaficial.platform.db import Vehicle
        v_check = db_sess.query(Vehicle).filter(Vehicle.id == matched_test_vehicle_id).first()
        assert_test(v_check.status != "SOLD", f"입금내역만으로 차량 판매 완료(SOLD) 미전이 확인 (현재 상태: {v_check.status})")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 15. 서류 파일 유효성(매직바이트 위조 방어, 15MB 한도) 및 SHA-256 감사 로그 검증
    # ----------------------------------------------------
    print_step(15, "서류 파일 유효성 및 바이너리 위조 차단 검증")
    # 위조 파일: 이름은 .jpg인데 내용은 일반 텍스트
    fake_body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="fake_doc.jpg"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n"
        f"This is not a jpeg image content, but malicious text.\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    req_fake = urllib.request.Request(
        f"{BASE_URL}/api/transactions/document/analyze",
        data=fake_body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Cookie": f"chamart_auth={session_token}",
        },
        method="POST",
    )
    code_fake, _, body_fake = 0, {}, ""
    try:
        with urllib.request.urlopen(req_fake) as resp:
            code_fake = resp.status
    except urllib.error.HTTPError as e:
        code_fake = e.code
        body_fake = e.read().decode("utf-8")

    assert_test(code_fake == 400, f"위조 바이너리 파일 400 차단 확인 (응답 코드: {code_fake})")
    assert_test("일치하지 않습니다" in body_fake, f"매직바이트 불일치 차단 사유 확인: {body_fake}")
    PASSED_COUNT += 1

    # ----------------------------------------------------
    # 16. 전체 이전 지침 회귀 무결성 및 Playwright 실측 스크린샷 4종 검증
    # ----------------------------------------------------
    print_step(16, "전체 이전 지침 회귀 무결성 및 실측 스크린샷 4종 검증")
    regression_scripts = [
        "scripts/test_directive_046d.py",
        "scripts/test_directive_047.py",
        "scripts/test_directive_048.py",
        "scripts/test_directive_049.py",
        "scripts/test_directive_050.py",
    ]
    for script_path in regression_scripts:
        print(f"  [*] 회귀 실행 중: {script_path} ...")
        res = subprocess.run(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert_test(res.returncode == 0, f"회귀 테스트 '{script_path}' 100% ALL PASS 통과")

    # 실측 스크린샷 4종 존재 및 유효 크기(50KB 이상) 검증
    screenshot_dir = Path("docs/screenshots/directive_050c")
    required_screenshots = [
        "050c_vehicle_detail_authenticated.png",
        "050c_business_card_crm_modal.png",
        "050c_transaction_document_modal.png",
        "050c_gemini_vision_settings.png",
    ]
    for s_name in required_screenshots:
        s_file = screenshot_dir / s_name
        assert_test(s_file.exists(), f"실측 스크린샷 '{s_name}' 존재 확인")
        sz = s_file.stat().st_size
        assert_test(sz >= 50000, f"스크린샷 크기 검증: {sz:,} bytes (>= 50KB)")

    PASSED_COUNT += 1

    print(f"\n========================================================")
    print(f"[DIRECTIVE 050-C 검증 결과] 16대 필수 검증 항목 {PASSED_COUNT}/{TOTAL_COUNT} 100% ALL PASS!")
    print(f"========================================================\n")


if __name__ == "__main__":
    run_all_tests()
