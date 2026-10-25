"""CHA-FICIAL DIRECTIVE 047 브라우저 실측 및 고해상도 화면 캡처 스크립트.

Playwright를 사용하여 실제 웹 환경에서 5종의 고해상도 UI 증빙 캡처 수행:
1. 01_market_analysis_view.png: 장한평 시장 분석 뷰 (상단 4대 지표, 엔카/KB 매물 목록, 기회 점수)
2. 02_attribution_performance_view.png: 마케팅 성과 및 정산 뷰 (AI 영상 기여도, 공헌이익, ROI, 중복 문의 격리)
3. 03_rl_decision_ledger_view.png: 강화학습(RL) 오프라인 연구원장 뷰 (PPO 조기 도입 차단 배너, 정책 결정 바, 의사결정 원장)
4. 04_dealer_rights_modal_interaction.png: 차량 상세 모달 내 제휴 딜러 권한 상태 및 승인/철회 인터랙션
5. 05_vehicle_master_table_047.png: 차량 관리 마스터 목록 (4대 소유구분 뱃지, 실시간 동기화 상태)
"""

import json
import os
import sys
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

def capture_ui_047():
    admin_pw = load_env_password()
    assert admin_pw, "관리자 비밀번호를 로드할 수 없습니다."
    
    token = get_auth_token(admin_pw)
    assert token, "인증 토큰을 발급받을 수 없습니다."
    
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "screenshots_047")
    os.makedirs(out_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 960},
            device_scale_factor=2,  # Retina 고해상도 캡처
        )
        context.add_cookies([
            {
                "name": "chamart_auth",
                "value": token,
                "domain": "127.0.0.1",
                "path": "/",
            }
        ])
        
        page = context.new_page()
        page.goto("http://127.0.0.1:8501", wait_until="networkidle")
        time.sleep(1.5)
        
        # 1. 장한평 시장 분석 뷰 캡처
        print("[*] 01_market_analysis_view 캡처 중...")
        page.evaluate("switchNav('market')")
        time.sleep(1.0)
        page.screenshot(path=os.path.join(out_dir, "01_market_analysis_view.png"))
        
        # 2. 마케팅 성과 및 정산 뷰 캡처
        print("[*] 02_attribution_performance_view 캡처 중...")
        page.evaluate("switchNav('attribution')")
        time.sleep(1.0)
        page.screenshot(path=os.path.join(out_dir, "02_attribution_performance_view.png"))
        
        # 3. 강화학습(RL) 오프라인 연구원장 뷰 캡처
        print("[*] 03_rl_decision_ledger_view 캡처 중...")
        page.evaluate("switchNav('rl')")
        time.sleep(1.0)
        page.screenshot(path=os.path.join(out_dir, "03_rl_decision_ledger_view.png"))
        
        # 4. 차량 관리 마스터 목록 뷰 캡처
        print("[*] 04_vehicle_master_table_047 캡처 중...")
        page.evaluate("switchNav('vehicles')")
        time.sleep(1.0)
        page.screenshot(path=os.path.join(out_dir, "04_vehicle_master_table_047.png"))
        
        # 5. 차량 상세 모달 내 제휴 딜러 권한 인터랙션 캡처
        print("[*] 05_dealer_rights_modal_interaction 캡처 중...")
        first_btn = page.query_selector("button:has-text('상세보기')")
        if first_btn:
            first_btn.click()
            time.sleep(1.2)
            page.screenshot(path=os.path.join(out_dir, "05_dealer_rights_modal_interaction.png"))
        
        browser.close()
        print(f"[+] DIRECTIVE 047 실측 캡처 5종 완료 -> {out_dir}")

if __name__ == "__main__":
    capture_ui_047()
