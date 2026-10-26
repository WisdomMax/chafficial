"""CHA-FICIAL DIRECTIVE 050 자동화 검증 스위트.
MASTER VEHICLE REGISTRATION & MULTI-PLATFORM PUBLISHING READINESS.

검증 항목:
- TEST 00: 관리자 보안 인증 로그인
- TEST 01: [3항] 카탈로그 계층형 트리 및 트림별 사양 기본값 매칭 검증
- TEST 02: [1-2항] 표준 옵션 카탈로그 및 3대 플랫폼(엔카/KB/카매니저) 코드 매핑 검증
- TEST 03: [1항] 8대 필수 영역 포괄 신규 차량 마스터 통합 등록 검증 (POST /api/vehicles/master/create)
- TEST 04: [2항] 미확인 사양(UNKNOWN/미기재)의 가상 임의 변환 원천 차단 검증 (NULL 보존)
- TEST 05: [1항] 8대 필수 영역 표준 구조 통합 마스터 조회 검증 (GET /api/vehicles/{id}/master)
- TEST 06: [4항] 3대 플랫폼(ENCAR, KB, CAR_MANAGER) 등록 준비도 종합 검사 (Readiness)
- TEST 07: [4항] 시장 관측 매물(MARKET_OBSERVED)의 외부 다중 플랫폼 무단 등록 차단 가드
- TEST 08: [4항] 플랫폼별(엔카/KB/카매니저) 내보내기 규격 페이로드 생성 검증
- TEST 09: [5항] 게시 라이프사이클(DRAFT -> DATA_VERIFIED -> READY_TO_PUBLISH -> APPROVED) 전이 검증
- TEST 10: [5항] 공식 연동 미승인 시 임의 PUBLISHED 상태 설정 원천 차단 가드 (거짓 게시 금지)
- TEST 11: [6항] 장한평 파트너 허가 차량 1대 실전 딜러 E2E 등록 시나리오 검증
- TEST 12: [6항] 정보 수정 시 원본 마스터와 플랫폼별 게시 준비 데이터 실시간 동기화 검증
"""

from __future__ import annotations
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

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

BASE_URL = os.environ.get("CHAMART_BASE_URL", "http://127.0.0.1:8501")
SESSION_COOKIE: str | None = None


def print_step(title: str):
    print("\n" + "=" * 75)
    print(f"[TEST] {title}")
    print("=" * 75)


def http_request(
    path: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers_extra: dict[str, str] | None = None,
) -> tuple[int, Any]:
    global SESSION_COOKIE
    url = f"{BASE_URL}{path}"
    headers = {}
    req_data = None

    if SESSION_COOKIE:
        headers["Cookie"] = SESSION_COOKIE

    if headers_extra:
        headers.update(headers_extra)

    if data is not None:
        headers["Content-Type"] = "application/json"
        req_data = json.dumps(data, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            status = resp.status
            set_cookie = resp.headers.get("Set-Cookie")
            if set_cookie and not SESSION_COOKIE:
                SESSION_COOKIE = set_cookie.split(";")[0]

            resp_content_type = resp.headers.get("Content-Type", "")
            resp_bytes = resp.read()
            if "application/json" in resp_content_type:
                return status, json.loads(resp_bytes.decode("utf-8"))
            try:
                return status, resp_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return status, resp_bytes
    except urllib.error.HTTPError as e:
        resp_bytes = e.read()
        try:
            parsed = json.loads(resp_bytes.decode("utf-8"))
        except Exception:
            try:
                parsed = resp_bytes.decode("utf-8")
            except Exception:
                parsed = resp_bytes
        return e.code, parsed


# ============================================================================
# 13대 검증 케이스
# ============================================================================

def test_00_auth_login():
    print_step("00. 관리자 보안 인증 로그인")
    password = os.environ.get("CHAMART_ADMIN_PASSWORD", "")
    assert password, "CHAMART_ADMIN_PASSWORD 환경변수가 필요합니다."
    status, res = http_request("/api/auth/login", method="POST", data={"username": "admin", "password": password})
    assert status == 200, f"로그인 실패: {res}"
    print("  -> PASS: 관리자 로그인 및 세션 쿠키 확보 완료")


def test_01_catalog_hierarchy_and_trim_selection():
    print_step("01. [3항] 카탈로그 계층형 트리 및 트림별 사양 기본값 매칭 검증")
    status, tree = http_request("/api/vehicles/catalog/hierarchy")
    assert status == 200, f"카탈로그 조회 실패: {tree}"
    assert "현대" in tree and "기아" in tree and "제네시스" in tree, "주요 국산 제조사 누락"
    
    hyundai_gn7 = tree["현대"]["그랜저"]["generations"]["디 올 뉴 그랜저 (GN7)"]
    assert 2024 in hyundai_gn7["years"], "그랜저 GN7 연식 누락"
    assert "2.5 가솔린 캘리그래피" in hyundai_gn7["trims"], "그랜저 캘리그래피 트림 누락"

    from chaficial.platform.catalog.hierarchy import VehicleCatalogService
    spec = VehicleCatalogService.get_spec_defaults("현대", "그랜저", "디 올 뉴 그랜저 (GN7)", "2.5 가솔린 캘리그래피")
    assert spec["displacement_cc"] == 2497, f"배기량 매칭 실패: {spec}"
    assert spec["fuel_type"] == "가솔린", f"연료 매칭 실패: {spec}"
    assert spec["body_type"] == "대형 세단", f"차체 매칭 실패: {spec}"
    print(f"  -> PASS: 카탈로그 트리 및 그랜저 2.5 캘리그래피 사양 매칭 검증 성공 ({spec['displacement_cc']}cc, {spec['body_type']})")


def test_02_standard_options_catalog_and_mapping():
    print_step("02. [1-2항] 표준 옵션 카탈로그 및 3대 플랫폼(엔카/KB/카매니저) 코드 매핑 검증")
    status, options = http_request("/api/vehicles/catalog/options")
    assert status == 200, f"표준 옵션 조회 실패: {options}"
    assert len(options) >= 20, f"표준 옵션 수량 부족 (현재: {len(options)})"

    scc_opt = next((o for o in options if o["code"] == "OPT_SMART_CRUISE"), None)
    assert scc_opt is not None, "스마트 크루즈 옵션 누락"
    assert scc_opt["encar_code"] == "SMART_CRUISE", "엔카 매핑 코드 누락"
    assert scc_opt["kb_code"] == "KB_ADAS_01", "KB 매핑 코드 누락"
    assert scc_opt["carmanager_code"] == "CM_SCC", "카매니저 매핑 코드 누락"
    print(f"  -> PASS: 스마트 크루즈 옵션 3대 플랫폼 전산 코드 매핑 확인 (ENCAR: {scc_opt['encar_code']}, KB: {scc_opt['kb_code']}, CM: {scc_opt['carmanager_code']})")


def test_03_master_vehicle_full_registration():
    print_step("03. [1항] 8대 필수 영역 포괄 신규 차량 마스터 통합 등록 검증 (POST /api/vehicles/master/create)")
    unique_no = int(time.time() * 10) % 9000 + 1000
    test_plate = f"88오 {unique_no}"
    test_vin = f"KMHEC41UBKA{unique_no:06d}"

    payload = {
        "plate_number": test_plate,
        "vin": test_vin,
        "manufacturer": "현대",
        "model_name": "현대 디 올 뉴 그랜저 (GN7)",
        "trim": "2.5 가솔린 캘리그래피",
        "year": 2024,
        "first_registration_date": "2024-03-15",
        "mileage": 15000,
        "displacement_cc": 2497,
        "fuel_type": "가솔린",
        "transmission": "오토",
        "drive_type": "2WD",
        "body_type": "대형 세단",
        "color": "블랙",
        "interior_color": "브라운",
        "target_price": 4200,
        "purchase_price": 3800,
        "recon_cost": 50,
        "sales_conditions": "현금/할부 가능, 세금계산서 100% 발행",
        "ownership_type": "CHAMART_OWNED",
        "status": "FOR_SALE",
        "ad_highlights": "1인신조, 완전무사고, 캘리그래피 풀옵션",
        "ad_notices": "비흡연, 휠 기스 없음, 신차급 상태",
        "ad_description": "장한평 차마트 본사에서 직접 보유 관리하는 특선 매물입니다.",
        "options_structured": [
            {"code": "OPT_AIRBAG_FRONT", "name": "운전석/동승석 에어백", "is_installed": True, "is_factory": True},
            {"code": "OPT_SMART_CRUISE", "name": "스마트 크루즈 컨트롤 (SCC)", "is_installed": True, "is_factory": True},
            {"code": "OPT_SURROUND_VIEW", "name": "서라운드 뷰 모니터 (SVM)", "is_installed": True, "is_factory": True},
            {"code": "OPT_VENTILATED_SEAT", "name": "통풍 시트 (앞좌석)", "is_installed": True, "is_factory": True},
            {"code": "OPT_GENUINE_NAVI", "name": "순정 내비게이션", "is_installed": True, "is_factory": True},
            {"code": "OPT_SUNROOF", "name": "파노라마 선루프", "is_installed": True, "is_factory": True},
        ],
        "condition_detail": {
            "accident_state": "NO_ACCIDENT",
            "frame_damage": "이상 없음",
            "outer_damage": "무교환",
            "flood_history": "NONE",
            "leak_state": "NONE",
        },
        "accident_history": {
            "accident_state": "NO_ACCIDENT",
            "frame_damage": "이상 없음",
            "outer_damage": "무교환",
        },
        "photos": [
            {"photo_url": "https://images.unsplash.com/photo-1549399542-7e3f8b79c341?w=800&q=80", "category": "EXTERIOR", "is_primary": True},
            {"photo_url": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=800&q=80", "category": "EXTERIOR", "is_primary": False},
            {"photo_url": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=800&q=80", "category": "EXTERIOR", "is_primary": False},
            {"photo_url": "https://images.unsplash.com/photo-1542282088-72c9c27ed0cd?w=800&q=80", "category": "EXTERIOR", "is_primary": False},
            {"photo_url": "https://images.unsplash.com/photo-1583121274602-3e2820c69888?w=800&q=80", "category": "INTERIOR", "is_primary": False},
            {"photo_url": "https://images.unsplash.com/photo-1617814076367-b759c7d7e738?w=800&q=80", "category": "INTERIOR", "is_primary": False},
            {"photo_url": "https://images.unsplash.com/photo-1502877338535-766e1452684a?w=800&q=80", "category": "ENGINE", "is_primary": False},
            {"photo_url": "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?w=800&q=80", "category": "EXTERIOR", "is_primary": False},
            {"photo_url": "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=800&q=80", "category": "EXTERIOR", "is_primary": False},
            {"photo_url": "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?w=800&q=80", "category": "EXTERIOR", "is_primary": False},
        ],
    }

    status, res = http_request("/api/vehicles/master/create", method="POST", data=payload)
    assert status == 200, f"차량 마스터 등록 실패: {res}"
    v_id = res.get("vehicle_id")
    assert v_id, "생성된 차량 ID 누락"
    assert res["basic_specs"]["plate_number"] == test_plate, "차량번호 불일치"
    assert len(res["options"]) == 6, "옵션 수량 불일치"
    assert res["media"]["photos_count"] == 10, "사진 10장 누락"
    print(f"  -> PASS: 8대 영역 포괄 신규 차량 마스터 등록 성공 (Vehicle ID: {v_id})")
    return v_id


def test_04_unconfirmed_specs_preserved_as_null():
    print_step("04. [2항] 미확인 사양(UNKNOWN/미기재)의 가상 임의 변환 원천 차단 검증 (NULL 보존)")
    from chaficial.platform.db import SessionLocal, Vehicle
    db = SessionLocal()
    try:
        v = db.query(Vehicle).first()
        assert v is not None, "기준 차량이 존재해야 합니다."
        # 최초등록일이 미기재된 차량 등록 시 가상 날짜 주입 방지
        raw_v = Vehicle(
            branch_id=v.branch_id,
            plate_number="99우 5002",
            model_name="테스트 미확인 차량",
            year=2021,
            mileage=40000,
            vin=None,
            first_registration_date=None,
            displacement_cc=None,
        )
        db.add(raw_v)
        db.commit()
        db.refresh(raw_v)

        assert raw_v.vin is None, "미확인 차대번호가 가상으로 생성됨"
        assert raw_v.first_registration_date is None, "미확인 등록일자가 가상으로 채워짐"
        assert raw_v.displacement_cc is None, "미확인 배기량이 가상으로 채워짐"
        print("  -> PASS: 미확인 값의 가상 자동 생성 차단 및 NULL 보존 확인")

        db.delete(raw_v)
        db.commit()
    finally:
        db.close()


def test_05_master_vehicle_structured_retrieval(v_id: str):
    print_step("05. [1항] 8대 필수 영역 표준 구조 통합 마스터 조회 검증 (GET /api/vehicles/{id}/master)")
    status, m = http_request(f"/api/vehicles/{v_id}/master")
    assert status == 200, f"마스터 조회 실패: {m}"

    # 8대 필수 영역 존재 검증
    assert "basic_specs" in m, "1. 기본제원 영역 누락"
    assert "options" in m, "2. 옵션 영역 누락"
    assert "condition" in m, "3. 사고·성능 영역 누락"
    assert "media" in m, "4. 사진 자산 영역 누락"
    assert "sales_profile" in m, "5. 가격·판매 영역 누락"
    assert "ad_content" in m, "6. 광고설명 영역 누락"
    assert "rights" in m, "7. 권한·승인 영역 누락"
    assert "platform_publishing" in m, "8. 플랫폼 연동 영역 누락"

    assert len(m["basic_specs"]["vin"]) == 17
    assert m["condition"]["accident_history"]["accident_state"] == "NO_ACCIDENT"
    assert m["sales_profile"]["target_price"] == 4200
    print(f"  -> PASS: 8대 핵심 영역 표준 데이터 모델 구조화 응답 확인 완료")


def test_06_publishing_readiness_evaluation(v_id: str):
    print_step("06. [4항] 3대 플랫폼(ENCAR, KB, CAR_MANAGER) 등록 준비도 종합 검사 (Readiness)")
    status, rep = http_request(f"/api/vehicles/{v_id}/publishing-readiness")
    assert status == 200, f"준비도 검사 실패: {rep}"

    platforms = rep.get("platforms", {})
    assert "ENCAR" in platforms, "엔카 검사 결과 누락"
    assert "KB_CHACHACHA" in platforms, "KB차차차 검사 결과 누락"
    assert "CAR_MANAGER" in platforms, "카매니저 검사 결과 누락"

    # 88오 5001은 사진 10장, 차대번호 17자리, 무사고, 가격 모두 완비되어 준비 완료여야 함
    encar = platforms["ENCAR"]
    kb = platforms["KB_CHACHACHA"]
    cm = platforms["CAR_MANAGER"]

    assert encar["is_ready"] is True, f"엔카 준비 완료 실패: {encar['missing_fields']}"
    assert kb["is_ready"] is True, f"KB차차차 준비 완료 실패: {kb['missing_fields']}"
    assert cm["is_ready"] is True, f"카매니저 준비 완료 실패: {cm['missing_fields']}"
    assert rep["ready_platform_count"] == 3, f"3대 플랫폼 준비 카운트 불일치: {rep['ready_platform_count']}"
    print(f"  -> PASS: 3대 플랫폼(ENCAR, KB, CAR_MANAGER) 등록 준비도 100% 충족 확인 (Ready: 3/3)")


def test_07_unauthorized_market_observed_publishing_blocked():
    print_step("07. [4항] 시장 관측 매물(MARKET_OBSERVED)의 외부 다중 플랫폼 무단 등록 차단 가드")
    status, v_list = http_request("/api/vehicles")
    observed_v = next((v for v in v_list if v.get("ownership_type") == "MARKET_OBSERVED"), None)
    if not observed_v:
        print("  -> SKIP: 관측 매물 없음")
        return

    status, rep = http_request(f"/api/vehicles/{observed_v['id']}/publishing-readiness")
    assert status == 200
    encar_rep = rep["platforms"]["ENCAR"]
    assert encar_rep["is_ready"] is False, "시장 관측 매물이 엔카 등록 준비 완료 상태로 잘못 판정됨"
    assert any("시장 관측 매물" in err for err in encar_rep["errors"]), "시장 관측 매물 차단 오류 누락"
    print(f"  -> PASS: 시장 관측 매물의 무단 다중 플랫폼 등록 차단 가드 정상 확인: {encar_rep['errors'][0]}")


def test_08_platform_export_payload_generation(v_id: str):
    print_step("08. [4항] 플랫폼별(엔카/KB/카매니저) 내보내기 규격 페이로드 생성 검증")
    for plat in ["ENCAR", "KB_CHACHACHA", "CAR_MANAGER"]:
        status, preview = http_request(f"/api/vehicles/{v_id}/publishing/preview/{plat}", method="POST")
        assert status == 200, f"{plat} 페이로드 생성 실패: {preview}"
        assert preview["is_ready"] is True, f"{plat} 준비 미비"
        payload = preview["mapped_payload"]
        assert payload["platform"] == plat, "플랫폼 식별자 불일치"
        opt_key = "option_codes" if plat == "KB_CHACHACHA" else "options"
        assert len(payload[opt_key]) > 0, f"{plat} 매핑 옵션 누락"
        print(f"  -> PASS: [{plat}] 전산 규격 페이로드 생성 성공 (옵션 {len(payload[opt_key])}개 매핑됨)")


def test_09_publishing_status_lifecycle_transitions(v_id: str):
    print_step("09. [5항] 게시 라이프사이클(DRAFT -> DATA_VERIFIED -> READY_TO_PUBLISH -> APPROVED) 전이 검증")
    # 1. DATA_VERIFIED 전이
    status, res1 = http_request(
        f"/api/vehicles/{v_id}/publishing/transition",
        method="POST",
        data={"target_status": "DATA_VERIFIED", "notes": "데이터 팩트 검증 완료"},
    )
    assert status == 200, f"DATA_VERIFIED 전이 실패: {res1}"
    assert res1["current_status"] == "DATA_VERIFIED"

    # 2. READY_TO_PUBLISH 전이
    status, res2 = http_request(
        f"/api/vehicles/{v_id}/publishing/transition",
        method="POST",
        data={"target_status": "READY_TO_PUBLISH", "notes": "3대 플랫폼 준비 완료"},
    )
    assert status == 200, f"READY_TO_PUBLISH 전이 실패: {res2}"
    assert res2["current_status"] == "READY_TO_PUBLISH"

    # 3. APPROVED 전이
    status, res3 = http_request(
        f"/api/vehicles/{v_id}/publishing/transition",
        method="POST",
        data={"target_status": "APPROVED", "notes": "관리자 다중 플랫폼 게시 승인"},
    )
    assert status == 200, f"APPROVED 전이 실패: {res3}"
    assert res3["current_status"] == "APPROVED"
    print("  -> PASS: 라이프사이클 단계별 전이 정상 성공 (DRAFT -> DATA_VERIFIED -> READY_TO_PUBLISH -> APPROVED)")


def test_10_block_fake_published_status(v_id: str):
    print_step("10. [5항] 공식 연동 미승인 시 임의 PUBLISHED 상태 설정 원천 차단 가드 (거짓 게시 금지)")
    status, res = http_request(
        f"/api/vehicles/{v_id}/publishing/transition",
        method="POST",
        data={"target_status": "PUBLISHED", "notes": "임의 게시 시도"},
    )
    assert status == 400, f"공식 API 부재 시 PUBLISHED 전이는 차단되어야 하지만 {status} 응답됨"
    assert "실제 게시 차단" in str(res.get("detail", "")), f"예상 차단 사유 불일치: {res}"
    print(f"  -> PASS: 가짜 게시 보고 차단 가드 정상 작동: {res.get('detail')}")


def test_11_partner_dealer_e2e_scenario():
    print_step("11. [6항] 장한평 파트너 허가 차량 1대 실전 딜러 E2E 등록 시나리오 검증")
    from chaficial.platform.db import SessionLocal, Dealer
    db = SessionLocal()
    dealer = db.query(Dealer).first()
    dealer_id = dealer.id if dealer else None
    db.close()

    unique_p_no = int(time.time() * 10 + 7) % 9000 + 1000
    p_plate = f"77조 {unique_p_no}"
    p_vin = f"KNAGE41ABPA{unique_p_no:06d}"

    partner_payload = {
        "plate_number": p_plate,
        "vin": p_vin,
        "manufacturer": "기아",
        "model_name": "기아 K8 2.5 가솔린 노블레스",
        "trim": "2.5 가솔린 노블레스",
        "year": 2023,
        "first_registration_date": "2023-08-20",
        "mileage": 28000,
        "displacement_cc": 2497,
        "fuel_type": "가솔린",
        "target_price": 3150,
        "purchase_price": 2850,
        "ownership_type": "PARTNER_APPROVED",
        "dealer_id": dealer_id,
        "ad_highlights": "장한평 가온모터스 제휴 실매물, 1인신조, 통풍시트/HUD",
        "ad_description": "장한평 제휴 딜러의 실차량으로 차마트 인증 검사를 마쳤습니다.",
        "options_structured": [
            {"code": "OPT_SMART_CRUISE", "name": "스마트 크루즈 컨트롤 (SCC)", "is_installed": True, "is_factory": True},
            {"code": "OPT_HUD", "name": "헤드업 디스플레이 (HUD)", "is_installed": True, "is_factory": True},
        ],
        "condition_detail": {
            "accident_state": "SIMPLE_REPAIR",
            "frame_damage": "이상 없음",
            "outer_damage": "프론트휀더 1개 단순교환",
        },
        "photos": [
            {"photo_url": f"https://example.com/k8_{i}.jpg", "category": "EXTERIOR"}
            for i in range(10)
        ],
        "marketing_auth": {
            "approved_by": "장한평 가온모터스 김민우 대표",
            "rights_scope": "FULL_MARKETING",
            "video_allowed": True,
            "photo_allowed": True,
            "external_ad_allowed": True,
        }
    }

    status, res = http_request("/api/vehicles/master/create", method="POST", data=partner_payload)
    assert status == 200, f"제휴 차량 등록 실패: {res}"
    partner_v_id = res["vehicle_id"]
    assert res["rights"]["has_rights"] is True, "제휴 권한 승인 누락"
    assert res["basic_specs"]["trim"] == "2.5 가솔린 노블레스", "트림 누락"
    print(f"  -> PASS: 장한평 제휴 파트너 차량 E2E 마스터 등록 성공 (Vehicle ID: {partner_v_id})")
    return partner_v_id


def test_12_master_data_sync_on_update(partner_v_id: str):
    print_step("12. [6항] 정보 수정 시 원본 마스터와 플랫폼별 게시 준비 데이터 실시간 동기화 검증")
    # 가격 인하 (3,150만원 -> 3,050만원) 및 추가 옵션 장착
    update_payload = {
        "target_price": 3050,
        "ad_highlights": "[가격인하 100만원] 장한평 가온모터스 제휴 실매물, 급매",
        "options_structured": [
            {"code": "OPT_SMART_CRUISE", "name": "스마트 크루즈 컨트롤 (SCC)", "is_installed": True, "is_factory": True},
            {"code": "OPT_HUD", "name": "헤드업 디스플레이 (HUD)", "is_installed": True, "is_factory": True},
            {"code": "OPT_SURROUND_VIEW", "name": "서라운드 뷰 모니터 (SVM)", "is_installed": True, "is_factory": True},
        ]
    }

    status, updated = http_request(f"/api/vehicles/{partner_v_id}/master", method="PUT", data=update_payload)
    assert status == 200, f"마스터 수정 실패: {updated}"
    assert updated["sales_profile"]["target_price"] == 3050, "수정된 가격 미반영"
    assert len(updated["options"]) == 3, "추가된 옵션 미반영"

    # 플랫폼 페이로드에 수정된 가격이 즉시 동기화되었는지 확인
    status, preview = http_request(f"/api/vehicles/{partner_v_id}/publishing/preview/ENCAR", method="POST")
    assert status == 200
    encar_payload = preview["mapped_payload"]
    assert encar_payload["advertised_price_krw"] == 30500000, f"엔카 페이로드 가격 미동기화: {encar_payload['advertised_price_krw']}"
    assert "AROUND_VIEW" in encar_payload["options"], f"엔카 페이로드 신규 옵션 미동기화: {encar_payload['options']}"
    print(f"  -> PASS: 마스터 수정 사항이 엔카 전산 페이로드에 실시간 즉시 동기화됨 확인 (3,050만원, 옵션 3개)")


def test_13_playwright_screenshots_integrity():
    print_step("13. [실측 UI] Playwright 실측 스크린샷 3종 존재 및 유효 크기 검증")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shot_dir = os.path.join(base_dir, "reports", "screenshots_050")
    expected = [
        "01_master_vehicle_modal_basic.png",
        "02_master_vehicle_modal_options.png",
        "03_master_vehicle_modal_publishing.png",
    ]
    for filename in expected:
        f_path = os.path.join(shot_dir, filename)
        assert os.path.exists(f_path), f"스크린샷 파일 누락: {f_path}"
        f_size = os.path.getsize(f_path)
        assert f_size > 50000, f"스크린샷 파일 크기 비정상 ({f_size} bytes): {filename}"
        print(f"  -> PASS: {filename} 실측 이미지 검증 완료 ({f_size:,} bytes)")


def main():
    print("\n" + "=" * 75)
    print("CHAMART OS - DIRECTIVE 050 종합 자동화 검증 스위트 시작")
    print("=" * 75)

    start_time = time.time()
    tests = [
        ("00. 관리자 보안 인증 로그인", test_00_auth_login),
        ("01. 카탈로그 계층 트리 및 트림 매칭", test_01_catalog_hierarchy_and_trim_selection),
        ("02. 표준 옵션 및 3대 플랫폼 매핑", test_02_standard_options_catalog_and_mapping),
        ("03. 8대 영역 포괄 신규 차량 마스터 등록", test_03_master_vehicle_full_registration),
        ("04. 미확인 사양 NULL 보존", test_04_unconfirmed_specs_preserved_as_null),
        ("05. 통합 마스터 표준 구조 조회", None),
        ("06. 3대 플랫폼 등록 준비도 검사", None),
        ("07. 시장 관측 매물 무단 등록 차단", test_07_unauthorized_market_observed_publishing_blocked),
        ("08. 플랫폼별 규격 페이로드 생성", None),
        ("09. 게시 라이프사이클 상태 전이", None),
        ("10. 가짜 게시 보고 차단 가드", None),
        ("11. 장한평 파트너 E2E 시나리오", test_11_partner_dealer_e2e_scenario),
        ("12. 마스터 수정 시 플랫폼 데이터 실시간 동기화", None),
        ("13. Playwright 실측 스크린샷 검증", test_13_playwright_screenshots_integrity),
    ]

    passed = 0
    failed = 0
    failures = []
    v_id = None
    partner_v_id = None

    for name, func in tests:
        try:
            if name.startswith("03."):
                v_id = test_03_master_vehicle_full_registration()
            elif name.startswith("05."):
                test_05_master_vehicle_structured_retrieval(v_id)
            elif name.startswith("06."):
                test_06_publishing_readiness_evaluation(v_id)
            elif name.startswith("08."):
                test_08_platform_export_payload_generation(v_id)
            elif name.startswith("09."):
                test_09_publishing_status_lifecycle_transitions(v_id)
            elif name.startswith("10."):
                test_10_block_fake_published_status(v_id)
            elif name.startswith("11."):
                partner_v_id = test_11_partner_dealer_e2e_scenario()
            elif name.startswith("12."):
                test_12_master_data_sync_on_update(partner_v_id)
            else:
                func()
            passed += 1
        except Exception as e:
            failed += 1
            failures.append((name, str(e)))
            print(f"\n[FAIL] {name} 실패: {e}")
            import traceback
            traceback.print_exc()

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 75)
    print("DIRECTIVE 050 검증 결과 보고서")
    print("=" * 75)
    print(f"총 검증 항목: {len(tests)}개")
    print(f"통과 (PASS): {passed}개")
    print(f"실패 (FAIL): {failed}개")
    print(f"소요 시간: {elapsed}초")

    if failures:
        print("\n실패 목록:")
        for name, err in failures:
            print(f"- {name}: {err}")
        sys.exit(1)
    else:
        print("\n>>> 모든 DIRECTIVE 050 차량 마스터 및 다중 플랫폼 연동 검증 100% 통과 (PASS) <<<")
        sys.exit(0)


if __name__ == "__main__":
    main()
