#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 049 엔카 실매물 소싱 UI 화면 캡처 스크립트."""

import json
import os
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright

def load_admin_password():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("CHAMART_ADMIN_PASSWORD="):
                    return line.split("=", 1)[1].strip()
    return os.getenv("CHAMART_ADMIN_PASSWORD", "")

def get_auth_token(password: str) -> str:
    url = "http://127.0.0.1:8501/api/auth/login"
    data = json.dumps({"username": "admin", "password": password}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req) as resp:
        cookie_header = resp.getheader("set-cookie", "")
        for part in cookie_header.split(";"):
            if "chamart_auth=" in part:
                return part.split("chamart_auth=")[1].strip()
    return ""

def main():
    pw = load_admin_password()
    assert pw, "관리자 비밀번호를 로드할 수 없습니다."
    token = get_auth_token(pw)
    assert token, "인증 토큰 발급 실패"

    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "screenshots_049")
    os.makedirs(out_dir, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        context.add_cookies([{
            "name": "chamart_auth",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])

        page = context.new_page()
        print("[*] 메인 페이지 접속...")
        page.goto("http://127.0.0.1:8501/")
        page.wait_for_load_state("networkidle")
        time.sleep(1)

        # 엔카 실매물 소싱 탭 클릭
        print("[*] 엔카 실매물 소싱 메뉴 이동...")
        page.click("#nav-sourcing")
        time.sleep(2)

        # 1. 소싱 센터 전체 화면 캡처
        shot1 = os.path.join(out_dir, "01_encar_sourcing_center.png")
        page.screenshot(path=shot1)
        print(f"[*] 스크린샷 1 저장: {shot1}")

        # 2. 실매물 테이블 영역 확대 캡처
        shot2 = os.path.join(out_dir, "02_encar_listings_table.png")
        table_el = page.query_selector("#view-sourcing .overflow-x-auto")
        if table_el:
            table_el.screenshot(path=shot2)
            print(f"[*] 스크린샷 2 저장: {shot2}")

        browser.close()
        print("[*] 모든 스크린샷 캡처 완료.")

if __name__ == "__main__":
    main()
