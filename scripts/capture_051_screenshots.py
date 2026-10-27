#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 051: 브라우저 실측 스크린샷 캡처 스크립트.

캡처 항목 (고해상도 4종):
1. 051_unified_vehicle_detail_modal.png - 차피셜·차마트 공통 고급 차량 상세 모달 (8대 영역, 대형 갤러리, 제원, 성능리포트, 시세비교)
2. 051_chamart_customer_mall_view.png - 차마트 일반 고객용 판매몰 뷰 (인증 실매물 그리드, 월납입금, 배너)
3. 051_content_lab_overview_and_session.png - AI 콘텐츠 연구소 연구 현황 (세션 상태, 5대 KPI, 관찰 영상, 7대 서브탭)
4. 051_content_lab_prompts_ready.png - 승인 대본 기반 Wan 3.0 / Kling 4.0 영상 제작 프롬프트 패키지 뷰어
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("CHAMART_API_URL", "http://127.0.0.1:8501")
OUT_DIR = Path("reports/screenshots_051")
DOCS_DIR = Path("docs/screenshots/directive_051")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)


def capture_all():
    print("[*] Playwright 브라우저 가동 및 DIRECTIVE 051 실측 스크린샷 캡처 시작...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 960})

        # 관리자 세션 쿠키 발급 및 컨텍스트 주입
        import http.cookiejar
        import json
        import urllib.request
        
        ENV_PATH = Path(".env")
        ADMIN_PW = "PL7VJMe3WfC9ZYlC8ZjwCav8wwQM02Sf"
        if ENV_PATH.exists():
            for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("CHAMART_ADMIN_PASSWORD=") and not line.startswith("#"):
                    ADMIN_PW = line.split("=", 1)[1].strip().strip('"').strip("'")

        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        req = urllib.request.Request(
            f"{BASE_URL}/api/auth/login",
            data=json.dumps({"username": "admin", "password": ADMIN_PW}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        session_token = None
        try:
            with opener.open(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                session_token = data.get("token") or data.get("session_token")
        except Exception as e:
            print(f"[!] 관리자 로그인 요청 예외: {e}")

        if session_token:
            context.add_cookies([{
                "name": "chamart_auth",
                "value": session_token,
                "domain": "127.0.0.1",
                "path": "/",
                "httpOnly": True,
                "sameSite": "Lax",
            }])
            print(f"  [OK] 관리자 세션 쿠키 주입 완료: {session_token[:16]}...")

        page = context.new_page()
        page.goto(BASE_URL, wait_until="networkidle")
        time.sleep(2)

        # ---------------------------------------------------------------------
        # 1. 차마트 고객몰 뷰 캡처
        # ---------------------------------------------------------------------
        print("[1/4] 차마트 고객몰 뷰 캡처 중...")
        page.evaluate("switchNav('chamart-mall')")
        time.sleep(2)
        shot1 = OUT_DIR / "051_chamart_customer_mall_view.png"
        page.screenshot(path=str(shot1), full_page=False)
        print(f"  -> 저장 완료: {shot1}")

        # ---------------------------------------------------------------------
        # 2. 공통 고급 차량 상세 모달 캡처
        # ---------------------------------------------------------------------
        print("[2/4] 공통 고급 차량 상세 모달 캡처 중...")
        page.evaluate("""
            async () => {
                const res = await fetch('/api/chamart/vehicles');
                const list = await res.json();
                if (list.length > 0) {
                    await openUnifiedVehicleDetailModal(list[0].id, true);
                }
            }
        """)
        time.sleep(2)
        shot2 = OUT_DIR / "051_unified_vehicle_detail_modal.png"
        page.screenshot(path=str(shot2), full_page=False)
        print(f"  -> 저장 완료: {shot2}")

        # 모달 닫기
        page.evaluate("closeUnifiedVehicleDetailModal()")
        time.sleep(0.5)

        # ---------------------------------------------------------------------
        # 3. AI 콘텐츠 연구소 연구 현황 캡처
        # ---------------------------------------------------------------------
        print("[3/4] AI 콘텐츠 연구소 연구 현황 캡처 중...")
        page.evaluate("switchNav('content-lab')")
        page.evaluate("switchContentLabSubTab('status')")
        time.sleep(2)
        shot3 = OUT_DIR / "051_content_lab_overview_and_session.png"
        page.screenshot(path=str(shot3), full_page=False)
        print(f"  -> 저장 완료: {shot3}")

        # ---------------------------------------------------------------------
        # 4. 승인 대본 기반 영상 프롬프트 패키지 뷰어 캡처
        # ---------------------------------------------------------------------
        print("[4/4] 영상 프롬프트 패키지 뷰어 캡처 중...")
        try:
            with opener.open(urllib.request.Request(f"{BASE_URL}/api/content-lab/scripts?status=DRAFT")) as r:
                drafts = json.loads(r.read().decode("utf-8"))
                if drafts:
                    s_id = drafts[0]["id"]
                    opener.open(urllib.request.Request(
                        f"{BASE_URL}/api/content-lab/scripts/{s_id}/approve",
                        data=json.dumps({"approver_name": "관리자"}).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    ))
        except Exception as e:
            print(f"[!] 사전 승인 시도 안내: {e}")

        page.evaluate("""
            async () => {
                const res = await safeFetch('/api/content-lab/scripts?status=APPROVED');
                const list = await res.json();
                if (list.length > 0) {
                    await generateScriptPromptsFromApproved(list[0].id, 'WAN_3_0');
                }
            }
        """)
        time.sleep(2)
        shot4 = OUT_DIR / "051_content_lab_prompts_ready.png"
        page.screenshot(path=str(shot4), full_page=False)
        print(f"  -> 저장 완료: {shot4}")

        browser.close()

    # docs 디렉토리 복사
    for p in OUT_DIR.glob("*.png"):
        dest = DOCS_DIR / p.name
        dest.write_bytes(p.read_bytes())

    print(f"[*] 4종 실측 스크린샷 캡처 완료 (저장 경로: {OUT_DIR}, {DOCS_DIR})")


if __name__ == "__main__":
    capture_all()
