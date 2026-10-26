"""Playwright 헤드리스 브라우저를 통한 DIRECTIVE 050 UI 실측 스크린샷 캡처."""

from __future__ import annotations
import os
import sys
import time
from playwright.sync_api import sync_playwright

def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

BASE_URL = os.environ.get("CHAMART_BASE_URL", "http://127.0.0.1:8501")
PASSWORD = os.environ.get("CHAMART_ADMIN_PASSWORD", "")
SCREENSHOT_DIR = "reports/screenshots_050"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def main():
    print(f"[*] DIRECTIVE 050 UI 실측 캡처 시작: {BASE_URL}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. 로그인
        page.goto(BASE_URL)
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # 로그인 모달 확인
        if page.locator("#loginModal").is_visible():
            page.fill("#login_password", PASSWORD)
            page.click("button[type='submit']")
            page.wait_for_timeout(1000)

        # 2. 차량 관리 뷰 진입
        page.click("#nav-vehicles")
        page.wait_for_timeout(800)

        # 3. 전문 차량 마스터 등록 모달 열기
        page.evaluate("openVehicleModal()")
        page.wait_for_timeout(800)

        # 샷 1: 마스터 등록 모달 기본 제원 탭
        path1 = os.path.join(SCREENSHOT_DIR, "01_master_vehicle_modal_basic.png")
        page.screenshot(path=path1)
        print(f"  -> 캡처 완료: {path1} ({os.path.getsize(path1):,} bytes)")

        # 샷 2: 옵션 체크리스트 탭
        page.evaluate("switchMasterTab('options')")
        page.wait_for_timeout(600)
        path2 = os.path.join(SCREENSHOT_DIR, "02_master_vehicle_modal_options.png")
        page.screenshot(path=path2)
        print(f"  -> 캡처 완료: {path2} ({os.path.getsize(path2):,} bytes)")

        # 샷 3: 다중 플랫폼 연동 & 등록 준비도 탭
        page.evaluate("switchMasterTab('publishing')")
        page.wait_for_timeout(600)
        path3 = os.path.join(SCREENSHOT_DIR, "03_master_vehicle_modal_publishing.png")
        page.screenshot(path=path3)
        print(f"  -> 캡처 완료: {path3} ({os.path.getsize(path3):,} bytes)")

        browser.close()
        print("[*] 모든 DIRECTIVE 050 실측 스크린샷 캡처 완료")

if __name__ == "__main__":
    main()
