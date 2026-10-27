#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 052: 브라우저 실측 스크린샷 캡처 스크립트.

캡처 항목 (고해상도 4종):
1. 052_chamart_independent_showroom.png - 차마트 독립 고객 쇼룸 (/chamart: 허위매물 0%, 실차 100% 검증 매물 그리드)
2. 052_chamart_honest_vehicle_detail.png - 차마트 고객 독립 상세 (/cars/{id}: 1.05배 가짜시세 제거, 정직한 실거래 시세 분석, 8대 영역)
3. 052_content_lab_honest_readiness.png - AI 콘텐츠 연구소 (4단계 학습 준비도 정직 표기, 지속 관찰 세션 제어)
4. 052_admin_quarantine_and_guards.png - 차피셜 관리자 차량 관리 (관측/미승인 매물 146대 비공개 격리 및 5대 가드)
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("CHAMART_API_URL", "http://127.0.0.1:8501")
OUT_DIR = Path("reports/screenshots_052")
DOCS_DIR = Path("docs/screenshots/directive_052")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def capture_all():
    print("[*] Playwright 브라우저 가동 및 DIRECTIVE 052 실측 스크린샷 캡처 시작...")

    # .env 관리자 비밀번호 로드
    ENV_PATH = Path(".env")
    ADMIN_PW = ""
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("CHAMART_ADMIN_PASSWORD=") and not line.startswith("#"):
                ADMIN_PW = line.split("=", 1)[1].strip().strip('"').strip("'")

    # 공개 차량 ID 확보
    req = urllib.request.Request(f"{BASE_URL}/api/chamart/vehicles")
    with urllib.request.urlopen(req) as resp:
        pub_cars = json.loads(resp.read().decode("utf-8"))
    assert len(pub_cars) > 0, "공개 실차 매물이 최소 1대 존재해야 함"
    sample_car_id = pub_cars[0]["id"]
    print(f"[*] 대표 실차 ID 확보: {sample_car_id} ({pub_cars[0]['model_name']})")

    # 관리자 세션 토큰 확보
    login_req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=json.dumps({"username": "admin", "password": ADMIN_PW}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(login_req) as resp:
        login_data = json.loads(resp.read().decode("utf-8"))
        session_token = login_data["token"]
    print(f"[*] 관리자 세션 토큰 획득 완료: {session_token[:12]}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ---------------------------------------------------------------------
        # 1. 052_chamart_independent_showroom.png (일반 고객 전용 독립 쇼룸)
        # ---------------------------------------------------------------------
        print("[1/4] 차마트 독립 고객 쇼룸 화면 캡처 중...")
        context_guest = browser.new_context(viewport={"width": 1440, "height": 960})
        page_guest = context_guest.new_page()
        page_guest.goto(f"{BASE_URL}/chamart")
        page_guest.wait_for_selector("#vehicleGrid")
        time.sleep(2)

        p1_path = OUT_DIR / "052_chamart_independent_showroom.png"
        page_guest.screenshot(path=str(p1_path))
        p1_docs = DOCS_DIR / "052_chamart_independent_showroom.png"
        p1_docs.write_bytes(p1_path.read_bytes())
        print(f"      -> 캡처 완료: {p1_path} ({p1_path.stat().st_size:,} bytes)")

        # ---------------------------------------------------------------------
        # 2. 052_chamart_honest_vehicle_detail.png (고객 전용 정직한 실차 상세 페이지)
        # ---------------------------------------------------------------------
        print("[2/4] 차마트 고객 독립 차량 상세 화면 캡처 중...")
        page_guest.goto(f"{BASE_URL}/cars/{sample_car_id}")
        page_guest.wait_for_selector("#detailModelName")
        time.sleep(2)

        p2_path = OUT_DIR / "052_chamart_honest_vehicle_detail.png"
        page_guest.screenshot(path=str(p2_path))
        p2_docs = DOCS_DIR / "052_chamart_honest_vehicle_detail.png"
        p2_docs.write_bytes(p2_path.read_bytes())
        print(f"      -> 캡처 완료: {p2_path} ({p2_path.stat().st_size:,} bytes)")
        context_guest.close()

        # ---------------------------------------------------------------------
        # 3. 052_content_lab_honest_readiness.png (차피셜 관리자 AI 콘텐츠 연구소)
        # ---------------------------------------------------------------------
        print("[3/4] 차피셜 관리자 AI 콘텐츠 연구소 화면 캡처 중...")
        context_admin = browser.new_context(viewport={"width": 1440, "height": 960})
        context_admin.add_cookies([{
            "name": "chamart_auth",
            "value": session_token,
            "domain": "127.0.0.1",
            "path": "/",
        }])
        page_admin = context_admin.new_page()
        page_admin.goto(f"{BASE_URL}/")
        page_admin.wait_for_load_state("networkidle")
        time.sleep(1)

        # 연구소 탭 전환
        page_admin.evaluate("switchNav('content-lab')")
        time.sleep(2)

        p3_path = OUT_DIR / "052_content_lab_honest_readiness.png"
        page_admin.screenshot(path=str(p3_path))
        p3_docs = DOCS_DIR / "052_content_lab_honest_readiness.png"
        p3_docs.write_bytes(p3_path.read_bytes())
        print(f"      -> 캡처 완료: {p3_path} ({p3_path.stat().st_size:,} bytes)")

        # ---------------------------------------------------------------------
        # 4. 052_admin_quarantine_and_guards.png (차피셜 관리자 차량 관리 & 격리 현황)
        # ---------------------------------------------------------------------
        print("[4/4] 차피셜 관리자 차량 관리 & 미승인 매물 격리 현황 화면 캡처 중...")
        page_admin.evaluate("switchNav('vehicles')")
        time.sleep(2)

        p4_path = OUT_DIR / "052_admin_quarantine_and_guards.png"
        page_admin.screenshot(path=str(p4_path))
        p4_docs = DOCS_DIR / "052_admin_quarantine_and_guards.png"
        p4_docs.write_bytes(p4_path.read_bytes())
        print(f"      -> 캡처 완료: {p4_path} ({p4_path.stat().st_size:,} bytes)")
        context_admin.close()

        browser.close()

    print("[*] DIRECTIVE 052 실측 스크린샷 4종 캡처 완료!")


if __name__ == "__main__":
    capture_all()
