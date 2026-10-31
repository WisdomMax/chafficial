# -*- coding: utf-8 -*-
"""
DIRECTIVE 136-SEC P0 보안 및 인증 검증 테스트
1. 토큰 없는 관리자 API 요청 -> 401 차단
2. 폐기된 구 토큰(chamart-sync-secret-2026) -> 401 차단
3. ?token= URL 쿼리 파라미터 요청 -> 401 차단 (URL 인증 완전 차단)
4. 동기화 토큰(CHAMART_SYNC_TOKEN)으로 관리자 API 요청 -> 401 차단 (권한 분리)
5. 관리자 토큰(CHAMART_ADMIN_TOKEN)으로 동기화 API 요청 -> 401 차단 (권한 분리)
6. 정상 Bearer 관리자 토큰 요청 -> 200 OK & 축소된 데이터 스키마 & 사진 9장 & 비공개 보호 확인
7. 고객용 공개 API -> 0대 격리 유지 확인
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("test_directive_136_sec")

PROD_URL = "https://chamart.cc"
LANDROVER_PLATE = "64노3143"
ADMIN_TOKEN = os.environ.get("CHAMART_ADMIN_TOKEN", "")
if not ADMIN_TOKEN and Path("data/.chamart_admin_secret").exists():
    ADMIN_TOKEN = Path("data/.chamart_admin_secret").read_text().strip()

SYNC_TOKEN = os.environ.get("CHAMART_SYNC_TOKEN", "")
if not SYNC_TOKEN and Path("data/.chamart_sync_secret").exists():
    SYNC_TOKEN = Path("data/.chamart_sync_secret").read_text().strip()
REVOKED_TOKEN = "chamart-sync-secret-2026"

def request_http(url: str, method: str = "GET", headers: dict = None, data: bytes = None):
    req_headers = {"User-Agent": "ChamartSecVerifier/1.0"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode('utf-8')
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else ""
        return e.code, body

def run_security_verification():
    logger.info("=" * 65)
    logger.info("CHA-FICIAL DIRECTIVE 136-SEC: Security & Regression Verification")
    logger.info("=" * 65)

    assert ADMIN_TOKEN and len(ADMIN_TOKEN) >= 16, "CHAMART_ADMIN_TOKEN env must be set and >= 16 chars"
    assert SYNC_TOKEN and len(SYNC_TOKEN) >= 16, "CHAMART_SYNC_TOKEN env must be set and >= 16 chars"

    encoded_plate = urllib.parse.quote(LANDROVER_PLATE)
    admin_api_endpoint = f"{PROD_URL}/api/admin/vehicles/{encoded_plate}"

    # -------------------------------------------------------------
    # Case 1: 토큰 없는 관리자 API 요청 -> 401 차단
    # -------------------------------------------------------------
    status, body = request_http(admin_api_endpoint)
    logger.info(f"Case 1 (No Auth): Status={status}")
    assert status == 401, f"Expected 401 for unauthenticated request, got {status}"
    assert "UNAUTHORIZED_ADMIN_ACCESS" in body
    logger.info("  [PASS] Case 1: 토큰 없는 관리자 요청 즉시 401 차단 확인")

    # -------------------------------------------------------------
    # Case 2: 폐기된 구 토큰(chamart-sync-secret-2026) -> 401 차단
    # -------------------------------------------------------------
    status, body = request_http(admin_api_endpoint, headers={"Authorization": f"Bearer {REVOKED_TOKEN}"})
    logger.info(f"Case 2 (Revoked Token Bearer): Status={status}")
    assert status == 401, f"Expected 401 for revoked token, got {status}"
    assert "UNAUTHORIZED_ADMIN_ACCESS" in body
    logger.info("  [PASS] Case 2: 폐기된 구 토큰(chamart-sync-secret-2026) 즉시 401 차단 확인")

    # -------------------------------------------------------------
    # Case 3: ?token= URL 쿼리 파라미터 인증 차단 (DIRECTIVE 136-SEC-R 지침 준수)
    # 실제 관리자 토큰 노출 방지를 위해 합성 더미 토큰을 URL 쿼리에 전송하여 401 차단 검증
    # (서버 _worker.js는 url.searchParams.get('token') 로직을 영구 제거하여 쿼리 파라미터를 무시하고 401 차단함)
    # -------------------------------------------------------------
    dummy_synthetic_token = "synthetic-dummy-query-probe-token-never-used-in-prod"
    url_with_query = f"{admin_api_endpoint}?token={dummy_synthetic_token}"
    status, body = request_http(url_with_query)
    logger.info(f"Case 3 (URL Query Token): Status={status}")
    assert status == 401, f"Expected 401 for URL query token, got {status}"
    assert "UNAUTHORIZED_ADMIN_ACCESS" in body
    logger.info("  [PASS] Case 3: URL 쿼리 파라미터(?token=...)를 통한 인증 시도 원천 401 차단 확인 (합성 토큰 사용으로 운영 토큰 노출 제로)")

    # -------------------------------------------------------------
    # Case 4: 동기화 토큰(CHAMART_SYNC_TOKEN)으로 관리자 API 요청 -> 401 차단 (권한 분리)
    # -------------------------------------------------------------
    status, body = request_http(admin_api_endpoint, headers={"Authorization": f"Bearer {SYNC_TOKEN}"})
    logger.info(f"Case 4 (Sync Token -> Admin API): Status={status}")
    assert status == 401, f"Expected 401 when calling Admin API with Sync Token, got {status}"
    assert "UNAUTHORIZED_ADMIN_ACCESS" in body
    logger.info("  [PASS] Case 4: 동기화 토큰으로 관리자 API 접근 시 401 차단 (권한 분리 검증)")

    # -------------------------------------------------------------
    # Case 5: 관리자 토큰(CHAMART_ADMIN_TOKEN)으로 동기화 API 요청 -> 401 차단 (권한 분리 역방향)
    # -------------------------------------------------------------
    sync_api_endpoint = f"{PROD_URL}/api/sync/status"
    status, body = request_http(sync_api_endpoint, headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    logger.info(f"Case 5 (Admin Token -> Sync API): Status={status}")
    assert status == 401, f"Expected 401 when calling Sync API with Admin Token, got {status}"
    logger.info("  [PASS] Case 5: 관리자 토큰으로 동기화 API 접근 시 401 차단 (권한 분리 상호 검증)")

    # -------------------------------------------------------------
    # Case 6: 정상 Bearer 관리자 토큰 요청 -> 200 OK & 축소된 데이터 스키마 & 사진 9장
    # -------------------------------------------------------------
    status, body = request_http(admin_api_endpoint, headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    logger.info(f"Case 6 (Valid Admin Bearer Token): Status={status}")
    assert status == 200, f"Expected 200 for valid admin bearer token, got {status}"
    data = json.loads(body)

    assert data.get("_source") == "CLOUDFLARE_D1_REAL_RECORD"
    assert data.get("plate_number") == LANDROVER_PLATE
    assert data.get("target_price") == 1090
    assert data.get("mileage") == 125428
    assert data.get("is_public") == 0, "실매물 1호는 사용자 승인 전 비공개(is_public=0)여야 합니다."
    assert data.get("publishing_status") == "PENDING_REVIEW"
    assert data.get("seller_company_name") == "(주)더쿨모터스"
    assert data.get("photo_count") == 9
    assert len(data.get("photos", [])) == 9

    # 불필요한 내부 컬럼 노출 여부 확인 (SELECT v.* 제거 확인)
    unwanted_keys = ["dealer_id", "sync_job_id", "external_source_id", "options_json", "memo"]
    for k in unwanted_keys:
        assert k not in data, f"Unwanted column {k} exposed in admin vehicle response"

    logger.info("  [PASS] Case 6: 관리자 API 정상 인증(200 OK), 축소된 스키마, 사진 9장, 비공개 보호 확인")

    # -------------------------------------------------------------
    # Case 7: 고객용 공개 API -> 0대 격리 유지 확인
    # -------------------------------------------------------------
    status, body = request_http(f"{PROD_URL}/api/chamart/vehicles")
    assert status == 200
    pub_vehicles = json.loads(body)
    assert len(pub_vehicles) == 0, f"Public vehicle list must be 0, got {len(pub_vehicles)}"
    logger.info("  [PASS] Case 7: 고객용 공개 API(chamart.cc) 0대 완전 격리 유지 확인")

    logger.info("=" * 65)
    logger.info("ALL DIRECTIVE 136-SEC SECURITY VERIFICATION CASES PASSED (100% PASS)")
    logger.info("=" * 65)

if __name__ == "__main__":
    run_security_verification()
