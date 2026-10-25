"""개편된 CHAMART OS 플랫폼 UI/UX 시각적 증빙 캡처 스크립트."""

import json
import os
import time
import urllib.request
from playwright.sync_api import sync_playwright

def load_env_password():
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

def capture_ui():
    admin_pw = load_env_password()
    assert admin_pw, "관리자 비밀번호를 로드할 수 없습니다."
    
    token = get_auth_token(admin_pw)
    assert token, "인증 토큰을 발급받을 수 없습니다."
    
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "screenshots_046")
    os.makedirs(out_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # 데스크톱 표준 1440x900 해상도
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        
        # 인증 쿠키 주입
        context.add_cookies([{
            "name": "chamart_auth",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])
        
        page = context.new_page()
        
        # 1. 메인 대시보드 접속
        page.goto("http://127.0.0.1:8501/#dashboard")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        dash_path = os.path.join(out_dir, "01_dashboard_enterprise.png")
        page.screenshot(path=dash_path, full_page=False)
        print(f"[CAPTURED] 대시보드 메인: {dash_path}")
        
        # 2. 전역 초성 검색 실행 ('ㅇㅂㄸ' 입력)
        search_input = page.locator("#globalSearchInput")
        search_input.click()
        search_input.fill("ㅇㅂㄸ")
        # 검색 드롭다운이 나타날 때까지 대기
        time.sleep(1.5)
        search_path = os.path.join(out_dir, "02_universal_search_chosung.png")
        page.screenshot(path=search_path, full_page=False)
        print(f"[CAPTURED] 초성 검색 드롭다운: {search_path}")
        
        # 검색창 초기화
        search_input.fill("")
        page.keyboard.press("Escape")
        time.sleep(0.5)
        
        # 3. 차량 관리 탭 전환
        page.click("#nav-vehicles")
        time.sleep(1.5)
        veh_path = os.path.join(out_dir, "03_vehicle_management.png")
        page.screenshot(path=veh_path, full_page=False)
        print(f"[CAPTURED] 차량 관리 테이블: {veh_path}")
        
        # 4. 고객 CRM 탭 전환
        page.click("#nav-customers")
        time.sleep(1.5)
        crm_path = os.path.join(out_dir, "04_customer_crm.png")
        page.screenshot(path=crm_path, full_page=False)
        print(f"[CAPTURED] 고객 CRM: {crm_path}")
        
        # 5. AI 영상 스튜디오 탭 전환
        page.click("#nav-media")
        time.sleep(1.5)
        media_path = os.path.join(out_dir, "05_media_studio.png")
        page.screenshot(path=media_path, full_page=False)
        print(f"[CAPTURED] 영상 스튜디오: {media_path}")
        
        browser.close()
        print("[SUCCESS] 전 화면 시각적 캡처 5종 완료.")

if __name__ == "__main__":
    capture_ui()
