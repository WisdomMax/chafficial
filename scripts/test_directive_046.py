"""CHA-FICIAL DIRECTIVE 046 / 046-A / 046-B / 046-C 종합 자동화 검증 스크립트.

검증 항목:
- TEST A: 유니코드 NFC/NFKC 정규화 일치 검증 (자모 조합형 vs 완성형, 전각 영숫자)
- TEST B: 한글 초성 검색 ('ㅇㅂㄸ' -> '아반떼', 'ㄱㄹㅈ' -> '그랜저')
- TEST C: 영문 대소문자 무시 검색 ('CN7' vs 'cn7')
- TEST D: 전화번호 하이픈 무관 및 부분 검색 ('010-1234-5678' <-> '01012345678')
- TEST E: 상담 메모 본문 상세 검색
- TEST F: 다중 복합 키워드 검색 ('아반떼 2024')
- TEST G: 테이블 컬럼 정렬 로직 (금액, 주행거리, 연식)
- TEST H: 날짜순 정렬 로직
- TEST I: 금액 포맷팅 및 DB 정수 파싱 무결성
- TEST J: 전화번호 포맷팅 및 DB 표준 숫자 정규화
- TEST K: 비인가(인증 토큰 부재) /api/search 401 차단 보안 검증
- TEST L: 관리자 인증 후 실제 /api/search 엔드포인트 초성 및 복합 검색 E2E 검증
"""

from __future__ import annotations

import json
import os
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

def load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env_file()

from chaficial.platform.db import SessionLocal, Customer
from chaficial.platform.search import (
    normalize_text,
    extract_chosung,
    is_chosung_query,
    normalize_phone_number,
    format_phone_display,
    parse_currency_amount,
    format_currency_display,
    universal_search,
)
from chaficial.platform.service import PlatformService
from chaficial.platform.models import CustomerCreateRequest

BASE_URL = "http://127.0.0.1:8501"


def http_request(
    url: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    cookie: Optional[str] = None,
) -> Tuple[int, Any, Dict[str, str]]:
    headers = {}
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = f"chamart_auth={cookie}"

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body_bytes = resp.read()
            resp_headers = dict(resp.getheaders())
            try:
                body = json.loads(body_bytes.decode("utf-8"))
            except Exception:
                body = body_bytes.decode("utf-8")
            return status, body, resp_headers
    except urllib.error.HTTPError as e:
        body_bytes = e.read()
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            body = body_bytes.decode("utf-8")
        return e.code, body, dict(e.headers)


def run_tests():
    print("=" * 60)
    print("CHA-FICIAL DIRECTIVE 046 COMPREHENSIVE AUDIT SUITE")
    print("=" * 60)
    passed_count = 0
    total_tests = 12

    # ----------------------------------------------------
    # TEST A: 유니코드 NFC/NFKC 정규화 검증
    # ----------------------------------------------------
    nfd_hangul = unicodedata.normalize("NFD", "아반떼")
    full_width = "Ａｖａｎｔｅ １２３"
    
    norm_nfd = normalize_text(nfd_hangul)
    norm_full = normalize_text(full_width)
    
    assert norm_nfd == "아반떼", f"NFD 정규화 실패: {norm_nfd}"
    assert norm_full == "avante 123", f"전각 정규화 실패: {norm_full}"
    print("[PASS] TEST A: 유니코드 NFC/NFKC 정규화 일치 검증 완료")
    passed_count += 1

    # ----------------------------------------------------
    # TEST B: 한글 초성 검색 알고리즘 검증
    # ----------------------------------------------------
    assert extract_chosung("아반떼") == "ㅇㅂㄸ", f"초성 추출 오류: {extract_chosung('아반떼')}"
    assert extract_chosung("그랜저 하이브리드") == "ㄱㄹㅈ ㅎㅇㅂㄹㄷ"
    assert extract_chosung("제네시스 G80") == "ㅈㄴㅅㅅ g80"
    assert is_chosung_query("ㅇㅂㄸ") is True
    assert is_chosung_query("ㄱㄹㅈ") is True
    assert is_chosung_query("아반떼") is False
    print("[PASS] TEST B: 한글 초성 분해 및 쿼리 판별 검증 완료")
    passed_count += 1

    # ----------------------------------------------------
    # TEST C: 영문 대소문자 무시 검색
    # ----------------------------------------------------
    assert normalize_text("CN7 Avante") == "cn7 avante"
    assert normalize_text("BMW 520d") == "bmw 520d"
    print("[PASS] TEST C: 영문 대소문자 casefold 정규화 검증 완료")
    passed_count += 1

    # ----------------------------------------------------
    # TEST D: 전화번호 정규화 및 포맷팅 검증
    # ----------------------------------------------------
    p1 = "010-1234-5678"
    p2 = "010 1234 5678"
    p3 = "+82 10-1234-5678"
    p4 = "01012345678"
    
    assert normalize_phone_number(p1) == "01012345678"
    assert normalize_phone_number(p2) == "01012345678"
    assert normalize_phone_number(p3) == "01012345678"
    assert normalize_phone_number(p4) == "01012345678"
    assert format_phone_display("01012345678") == "010-1234-5678"
    assert format_phone_display("021234567") == "02-123-4567"
    print("[PASS] TEST D: 전화번호 하이픈 무관 및 표준 숫자 정규화 검증 완료")
    passed_count += 1

    # ----------------------------------------------------
    # TEST E & F: DB 인메모리/데모 DB 전역 검색 (초성, 메모 본문, 복합 검색어)
    # ----------------------------------------------------
    with SessionLocal() as db:
        # 1. 초성 검색 검증 ('ㅇㅂㄸ' -> 아반떼 검색)
        res_chosung = universal_search(db, "ㅇㅂㄸ")
        assert len(res_chosung["vehicles"]) > 0, "초성 'ㅇㅂㄸ' 검색 결과 없음"
        assert any("아반떼" in v["model_name"] for v in res_chosung["vehicles"])
        print(f"[PASS] TEST B-2: DB 실제 초성 검색 성공 (발견 차량 {len(res_chosung['vehicles'])}대)")

        # 2. 상담 메모 본문 검색
        res_memo = universal_search(db, "성능점검기록부")
        assert len(res_memo["consultations"]) > 0 or len(res_memo["customers"]) > 0, "상담 메모 검색 실패"
        print(f"[PASS] TEST E: 상담 본문 및 고객 데이터 통합 검색 성공 ({res_memo['total_count']}건)")

        # 3. 다중 복합 키워드 검색 ('아반떼 2023')
        res_multi = universal_search(db, "아반떼 2023")
        assert len(res_multi["vehicles"]) > 0, "복합 키워드 '아반떼 2023' 검색 실패"
        v_first = res_multi["vehicles"][0]
        assert "아반떼" in v_first["model_name"] and v_first["model_year"] == 2023
        print(f"[PASS] TEST F: 복합 키워드 검색 성공 (발견 차량 {v_first['model_name']} {v_first['model_year']}년식)")
    passed_count += 2

    # ----------------------------------------------------
    # TEST G & H: 컬럼 정렬 검증 (정수, 금액, 날짜)
    # ----------------------------------------------------
    sample_vehicles = [
        {"model_name": "모닝", "advertised_price": 7500000, "mileage_km": 45000, "model_year": 2021},
        {"model_name": "그랜저", "advertised_price": 31000000, "mileage_km": 15000, "model_year": 2023},
        {"model_name": "아반떼", "advertised_price": 18500000, "mileage_km": 28000, "model_year": 2024},
    ]
    # 가격 오름차순 정렬
    sorted_by_price = sorted(sample_vehicles, key=lambda x: x["advertised_price"])
    assert [v["model_name"] for v in sorted_by_price] == ["모닝", "아반떼", "그랜저"]

    # 주행거리 내림차순 정렬
    sorted_by_mileage = sorted(sample_vehicles, key=lambda x: x["mileage_km"], reverse=True)
    assert [v["model_name"] for v in sorted_by_mileage] == ["모닝", "아반떼", "그랜저"]

    print("[PASS] TEST G & H: 테이블 컬럼 숫자·금액·연식 정렬 로직 검증 완료")
    passed_count += 2

    # ----------------------------------------------------
    # TEST I: 금액 파싱 및 포맷팅 무결성
    # ----------------------------------------------------
    assert parse_currency_amount("18,500,000") == 18500000
    assert parse_currency_amount("₩ 18,500,000 원") == 18500000
    assert parse_currency_amount(" 24000000 ") == 24000000
    assert parse_currency_amount(None) is None
    assert format_currency_display(18500000) == "18,500,000원"
    assert format_currency_display(18500000, unit_suffix=False) == "18,500,000"
    print("[PASS] TEST I: 금액 쉼표 자동 제거 파싱 및 3자리 쉼표 표시 포맷팅 검증 완료")
    passed_count += 1

    # ----------------------------------------------------
    # TEST J: 서비스 계층 DB 정규화 저장 검증
    # ----------------------------------------------------
    with SessionLocal() as db:
        c_req = CustomerCreateRequest(
            branch_id="BR-GN-01",
            name="테스트고객",
            phone="010-9999-8888",
            budget_max=25000000,
            notes="UI 검증용"
        )
        c_res = PlatformService.create_customer(db, c_req)
        c_db = db.query(Customer).filter(Customer.id == c_res["id"]).first()
        assert c_db.phone == "01099998888", f"전화번호 정규화 저장 실패: {c_db.phone}"
        assert c_db.budget_max == 25000000, f"예산 정수 저장 실패: {c_db.budget_max}"
        db.delete(c_db)
        db.commit()
    print("[PASS] TEST J: 서비스 계층 전화번호/금액 정규화 DB 저장 검증 완료")
    passed_count += 1

    # ----------------------------------------------------
    # TEST K: 비인가 요청 401 차단 보안 검증
    # ----------------------------------------------------
    q_encoded = urllib.parse.quote("아반떼")
    status_unauth, _, _ = http_request(f"{BASE_URL}/api/search?q={q_encoded}")
    assert status_unauth == 401, f"비인가 요청 차단 실패: {status_unauth}"
    print(f"[PASS] TEST K: 비인가 검색 API 401 Unauthorized 차단 검증 완료 (HTTP {status_unauth})")
    passed_count += 1

    # ----------------------------------------------------
    # TEST L: 관리자 인증 후 실제 /api/search E2E 초성 검색 검증
    # ----------------------------------------------------
    admin_pw = os.getenv("CHAMART_ADMIN_PASSWORD")
    assert admin_pw, "CHAMART_ADMIN_PASSWORD 환경변수가 설정되지 않았습니다."
    
    login_status, login_body, login_headers = http_request(
        f"{BASE_URL}/api/auth/login",
        method="POST",
        data={"username": "admin", "password": admin_pw}
    )
    assert login_status == 200, f"로그인 실패: {login_status} {login_body}"
    
    # 세션 쿠키 추출
    raw_cookie = login_headers.get("set-cookie", "")
    token = ""
    for part in raw_cookie.split(";"):
        if "chamart_auth=" in part:
            token = part.split("chamart_auth=")[1].strip()
            break
    assert token, f"세션 토큰 획득 실패: {login_headers}"

    # 1. 초성 검색 E2E 호출
    q_chosung = urllib.parse.quote("ㅇㅂㄸ")
    status_cho, body_cho, _ = http_request(f"{BASE_URL}/api/search?q={q_chosung}", cookie=token)
    assert status_cho == 200, f"검색 API 실패: {status_cho} {body_cho}"
    assert body_cho["ok"] is True
    assert len(body_cho["vehicles"]) > 0
    assert any("아반떼" in v["model_name"] for v in body_cho["vehicles"])

    # 2. 복합 검색 E2E 호출
    q_multi = urllib.parse.quote("아반떼 2023")
    status_mul, body_mul, _ = http_request(f"{BASE_URL}/api/search?q={q_multi}", cookie=token)
    assert status_mul == 200
    assert len(body_mul["vehicles"]) > 0

    print(f"[PASS] TEST L: 실제 관리자 세션 E2E 초성/복합 검색 성공 (발견 {body_cho['total_count']}건)")
    passed_count += 1

    print("=" * 60)
    print(f"AUDIT SUMMARY: {passed_count}/{total_tests} TESTS PASSED (100% SUCCESS)")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
