"""CHA-FICIAL DIRECTIVE 046-D 브라우저 실측 및 화면 캡처 스크립트.

Playwright를 사용하여 실제 웹 환경에서 6종의 고해상도 UI 증빙 캡처 수행:
1. 01_vehicles_master_table.png: 차량 마스터 목록 (4대 소유구분 뱃지, 대표사진 썸네일, 영상상태)
2. 02_vehicle_detail_basic.png: 차량 상세 모달 [기본정보 & 딜러]
3. 03_vehicle_detail_accident.png: 차량 상세 모달 [사고·보험이력] (미확인 격리 및 정밀 이력)
4. 04_vehicle_detail_defects.png: 차량 상세 모달 [성능점검 & 하자] (부위별 하자 및 예상 수리비)
5. 05_vehicle_detail_photos.png: 차량 상세 모달 [사진 자산 관리] (카테고리 갤러리 및 대표사진 설정)
6. 06_vehicle_detail_listings_video.png: 차량 상세 모달 [외부 매물 & 영상 연계] (엔카/KB 및 제작 연동)
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

def capture_ui_046d():
    admin_pw = load_env_password()
    assert admin_pw, "관리자 비밀번호를 로드할 수 없습니다."
    
    token = get_auth_token(admin_pw)
    assert token, "인증 토큰을 발급받을 수 없습니다."
    
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "screenshots_046d")
    os.makedirs(out_dir, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 960})
        
        # 인증 쿠키 주입
        context.add_cookies([{
            "name": "chamart_auth",
            "value": token,
            "domain": "127.0.0.1",
            "path": "/"
        }])
        
        page = context.new_page()
        
        # 1. 메인 접속 후 차량 관리 탭 클릭
        print("[*] 플랫폼 메인 접속 및 차량 관리 탭 진입...")
        page.goto("http://127.0.0.1:8501/")
        page.wait_for_load_state("networkidle")
        time.sleep(1.5)
        
        page.click("#nav-vehicles")
        time.sleep(1.5)
        
        shot1 = os.path.join(out_dir, "01_vehicles_master_table.png")
        page.screenshot(path=shot1, full_page=False)
        print(f"[CAPTURED] 1. 차량 마스터 테이블: {shot1}")
        
        # 2. 첫 번째 차량 '상세보기' 버튼 클릭하여 모달 열기
        print("[*] 첫 번째 차량 '상세보기' 버튼 클릭하여 상세 모달 호출...")
        detail_btns = page.locator("button:has-text('상세보기')")
        assert detail_btns.count() > 0, "차량 목록에 상세보기 버튼이 없습니다."
        detail_btns.first.click()
        time.sleep(1.5)
        
        modal = page.locator("#vehicleDetailModal")
        assert modal.is_visible(), "차량 상세 모달이 열리지 않았습니다."
        
        # 2. [기본정보 & 딜러] 탭 캡처
        shot2 = os.path.join(out_dir, "02_vehicle_detail_basic.png")
        page.screenshot(path=shot2, full_page=False)
        print(f"[CAPTURED] 2. 차량 상세 [기본정보 & 딜러]: {shot2}")
        
        # 3. [사고·보험이력] 탭 전환 및 캡처
        page.click("#tab-btn-v-accident")
        time.sleep(0.8)
        shot3 = os.path.join(out_dir, "03_vehicle_detail_accident.png")
        page.screenshot(path=shot3, full_page=False)
        print(f"[CAPTURED] 3. 차량 상세 [사고·보험이력]: {shot3}")
        
        # 4. [성능점검 & 하자] 탭 전환 및 캡처
        page.click("#tab-btn-v-inspection")
        time.sleep(0.8)
        shot4 = os.path.join(out_dir, "04_vehicle_detail_defects.png")
        page.screenshot(path=shot4, full_page=False)
        print(f"[CAPTURED] 4. 차량 상세 [성능점검 & 하자]: {shot4}")
        
        # 5. [사진 자산 관리] 탭 전환 및 캡처
        page.click("#tab-btn-v-photos")
        time.sleep(0.8)
        shot5 = os.path.join(out_dir, "05_vehicle_detail_photos.png")
        page.screenshot(path=shot5, full_page=False)
        print(f"[CAPTURED] 5. 차량 상세 [사진 자산 관리]: {shot5}")
        
        # 6. [외부 매물 (Listing)] 탭 전환 및 캡처
        page.click("#tab-btn-v-listings")
        time.sleep(0.8)
        shot6 = os.path.join(out_dir, "06_vehicle_detail_listings_video.png")
        page.screenshot(path=shot6, full_page=False)
        print(f"[CAPTURED] 6. 차량 상세 [외부 매물 & 영상]: {shot6}")
        
        browser.close()
        print("[*] 6종 UI 화면 실측 캡처 완료!")

if __name__ == "__main__":
    capture_ui_046d()
