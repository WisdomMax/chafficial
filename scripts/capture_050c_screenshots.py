#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 050-C Playwright 실측 스크린샷 4종 캡처 스크립트."""

import json
import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("docs/screenshots/directive_050c")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://127.0.0.1:8501"

# .env에서 관리자 패스워드 로드
ENV_PATH = Path(".env")
ADMIN_PW = None
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("CHAMART_ADMIN_PASSWORD=") and not line.startswith("#"):
            ADMIN_PW = line.split("=", 1)[1].strip().strip('"').strip("'")

if not ADMIN_PW:
    ADMIN_PW = os.environ.get("CHAMART_ADMIN_PASSWORD", "ephemeral_demo_password")


def get_auth_token():
    import urllib.request
    req = urllib.request.Request(
        f"{BASE_URL}/api/auth/login",
        data=json.dumps({"username": "admin", "password": ADMIN_PW}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        d = json.loads(resp.read().decode("utf-8"))
        return d.get("token")


def capture():
    print("[*] Playwright 브라우저 가동 및 DIRECTIVE 050-C 실측 스크린샷 캡처 시작...")
    token = get_auth_token()
    print(f"  [*] 관리자 인증 토큰 발급 완료: {token[:16]}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        # 세션 쿠키 주입
        context.add_cookies([
            {
                "name": "chamart_auth",
                "value": token,
                "domain": "127.0.0.1",
                "path": "/",
                "httpOnly": True,
                "sameSite": "Lax",
            }
        ])
        page = context.new_page()

        # 1. 페이지 접속
        print("  [1/4] 인증 세션 주입 후 대시보드 진입...")
        page.goto(BASE_URL)
        page.wait_for_timeout(1500)

        # 1번 스크린샷: 차량 상세 모달 정상 동작 (050c_vehicle_detail_authenticated.png)
        print("  [2/4] 차량 상세 모달 캡처 중...")
        page.evaluate("openVehicleDetailModal(allVehicles[0].id)")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUTPUT_DIR / "050c_vehicle_detail_authenticated.png"))
        print(f"    -> 저장: {OUTPUT_DIR}/050c_vehicle_detail_authenticated.png")
        page.evaluate("closeVehicleDetailModal()")
        page.wait_for_timeout(500)

        # 2번 스크린샷: AI 명함 스캔 및 고객 CRM 모달 (050c_business_card_crm_modal.png)
        print("  [3/4] AI 명함 스캔 모달 캡처 중...")
        page.evaluate("switchNav('customers')")
        page.wait_for_timeout(500)
        page.evaluate("openBusinessCardModal()")
        page.wait_for_timeout(500)
        # 더미 샘플 데이터 채우기 (시각화)
        page.evaluate("""() => {
            document.getElementById('bc_name').value = '김철수';
            document.getElementById('bc_job_title').value = '대표이사';
            document.getElementById('bc_company_name').value = '(주)카마스터즈 서울';
            document.getElementById('bc_phone').value = '010-8888-9999';
            document.getElementById('bc_company_phone').value = '02-2244-1122';
            document.getElementById('bc_email').value = 'chulsoo.kim@carmasters.kr';
            document.getElementById('bc_company_address').value = '서울특별시 동대문구 장한로 120';
            document.getElementById('bc_target_model').value = '쏘렌토 4세대';
            document.getElementById('bc_budget_max').value = '3500';
            document.getElementById('bc_notes').value = '장한평 매매단지 제휴 상사 미팅 시 명함 자동 인식 완료';
            document.getElementById('bcDuplicateWarning').classList.remove('hidden');
            document.getElementById('bcDuplicateText').innerText = '동일 고객 감지: 김철수 (010-8888-9999) / (주)카마스터즈 서울';
        }""")
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUTPUT_DIR / "050c_business_card_crm_modal.png"))
        print(f"    -> 저장: {OUTPUT_DIR}/050c_business_card_crm_modal.png")
        page.evaluate("closeBusinessCardModal()")
        page.wait_for_timeout(500)

        # 3번 스크린샷: AI 거래서류 분석 및 원장 매칭 초안 모달 (050c_transaction_document_modal.png)
        print("  [4/4] AI 거래서류 초안 모달 캡처 중...")
        page.evaluate("switchNav('transactions')")
        page.wait_for_timeout(500)
        page.evaluate("openTransactionDocModal()")
        page.wait_for_timeout(500)
        page.evaluate("""() => {
            document.getElementById('txDocResultContainer').classList.remove('hidden');
            document.getElementById('txd_doc_type').value = 'CONTRACT (양도증명서)';
            document.getElementById('txd_tx_type').value = 'SALE';
            document.getElementById('txd_date').value = '2026-10-26';
            document.getElementById('txd_amount').value = '2450';
            document.getElementById('txd_plate').value = '99다 3881';
            document.getElementById('txd_vin').value = 'KMH050C123456';
            document.getElementById('txd_party_name').value = '차은우';
            document.getElementById('txd_party_contact').value = '010-7777-1234';
            const vBox = document.getElementById('txMatchedVehicleBox');
            vBox.className = 'p-3 rounded-xl border bg-emerald-50 border-emerald-200 text-xs';
            document.getElementById('txMatchedVehicleText').innerText = '[매칭 성공] 99다 3881 (기아 쏘렌토 4세대)';
            const pBox = document.getElementById('txMatchedPartyBox');
            pBox.className = 'p-3 rounded-xl border bg-emerald-50 border-emerald-200 text-xs';
            document.getElementById('txMatchedPartyText').innerText = '[고객 매칭] 차은우 (010-7777-1234)';
        }""")
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUTPUT_DIR / "050c_transaction_document_modal.png"))
        print(f"    -> 저장: {OUTPUT_DIR}/050c_transaction_document_modal.png")
        page.evaluate("closeTransactionDocModal()")
        page.wait_for_timeout(500)

        # 4번 스크린샷: Gemini Vision 운영 설정 모달 (050c_gemini_vision_settings.png)
        print("  [5/5] Gemini Vision 설정 모달 캡처 중...")
        page.evaluate("openGeminiSettingsModal()")
        page.wait_for_timeout(800)
        page.screenshot(path=str(OUTPUT_DIR / "050c_gemini_vision_settings.png"))
        print(f"    -> 저장: {OUTPUT_DIR}/050c_gemini_vision_settings.png")
        page.evaluate("closeGeminiSettingsModal()")

        browser.close()
        print("[*] 실측 스크린샷 4종 캡처 완료!")


if __name__ == "__main__":
    capture()
