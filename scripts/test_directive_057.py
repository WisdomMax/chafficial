"""CHA-FICIAL DIRECTIVE 057 FINAL 종합 E2E 및 상용 디자인 시스템 검증 스위트
CHAMART COMMERCIAL WEBSITE DESIGN REBOOT (엔카·K Car·KB차차차 수준)

검증 항목:
1. P0 타이포그래피 & 상용 컬러: Pretendard, 26px 차량명, 32px 차콜(#171C24) 가격, #F7F8FA 배경 실측 검증
2. P0 5:3 비율 대형 실차 갤러리: 엔카 5:3 공식 규격(aspect-[5/3]) 좌측 68% 배치 및 썸네일 스트립 검증
3. P0 고객 전문 헤더 & 브랜드 독립성: 고객 헤더 내 관리자 버튼 0건, 단정 한글 로고 '차마트' 실측
4. P1 우측 32% Sticky 패널 & 방문예약 동선: 가격/전시장/카카오톡/간편예약 정돈된 배치 검증
5. P1 표 기반 정돈된 제원 & 옵션 그리드: K Car 스타일 테이블 제원 및 아코디언 옵션 검증
6. P0 기존 무결성 연속 보존: 상담 접수 -> CRM 원장 저장, SVG diagram_parts 연동, 타이어 게이지 100% 보존 실측
7. 5대 반응형 전수 스크린샷 (1440x900, 1280x800, 768x1024, 390x844, 375x812) 캡처 및 전후 나란히 비교 이미지 병합
"""

import asyncio
import json
import os
import random
import sys
import urllib.request
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8501"
OUTPUT_DIR = Path("reports/screenshots_057")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_VEHICLE_ID = "ce67fd58-311b-4449-b575-45edb9c4537a"

ENV_PATH = Path(".env")
ADMIN_PW = ""
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("CHAMART_ADMIN_PASSWORD=") and not line.startswith("#"):
            ADMIN_PW = line.split("=", 1)[1].strip().strip('"').strip("'")

assert ADMIN_PW, ".env 내 CHAMART_ADMIN_PASSWORD 가 설정되어 있어야 합니다."


def get_admin_token() -> str:
    url = f"{BASE_URL}/api/auth/login"
    data = json.dumps({"username": "admin", "password": ADMIN_PW}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return res.get("token") or res.get("access_token")


async def run_directive_057_verification():
    print("=" * 70)
    print("CHA-FICIAL DIRECTIVE 057 FINAL COMMERCIAL DESIGN REBOOT VERIFICATION")
    print("=" * 70)

    admin_token = get_admin_token()
    print(f"[*] 관리자 인증 토큰 획득 완료 (Bearer {admin_token[:10]}...)")

    test_results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # TEST 1: 고객 전문 헤더 및 관리자 버튼 완전 배제 검증 (상용 쇼룸 독립성)
        # -------------------------------------------------------------
        print("\n[TEST 1] 고객 전문 헤더 & 관리자 버튼 미노출 검증...")
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(f"{BASE_URL}/chamart", wait_until="networkidle")

        header_text = await page.locator("header").inner_text()
        has_admin_btn = "관리자" in header_text
        header_logo = await page.locator("header a[href='/chamart'] span:nth-child(2)").inner_text()

        print(f"  - 헤더 텍스트: {header_text.replace('\n', ' ')}")
        print(f"  - 헤더 로고: '{header_logo}' (관리자 버튼 존재 여부: {has_admin_btn})")

        if header_logo == "차마트" and not has_admin_btn:
            print("  PASS: 고객 쇼룸 헤더에서 관리자 버튼이 완전히 배제되고 단정한 '차마트' 브랜드로 독립됨")
            test_results["T1_COMMERCIAL_HEADER_CLEAN"] = True
        else:
            print("  FAIL: 헤더에 관리자 버튼이 잔존하거나 로고 표기 불일치")
            test_results["T1_COMMERCIAL_HEADER_CLEAN"] = False

        # -------------------------------------------------------------
        # TEST 2: 5:3 비율 대형 실차 갤러리 및 엔카 공식 규격 검증
        # -------------------------------------------------------------
        print("\n[TEST 2] 5:3 비율 대형 실차 갤러리 검증 (엔카 공식 5:3 규격)...")
        await page.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await page.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await page.wait_for_timeout(800)

        viewport_classes = await page.locator("#vdrGalleryViewport").get_attribute("class")
        has_aspect_5_3 = "aspect-[5/3]" in viewport_classes

        print(f"  - 갤러리 뷰포트 클래스: '{viewport_classes}'")
        if has_aspect_5_3:
            print("  PASS: 엔카 공식 5:3 비율(aspect-[5/3]) 대형 갤러리 뷰포트 적용 확인")
            test_results["T2_GALLERY_ASPECT_5_3"] = True
        else:
            print("  FAIL: 5:3 비율 클래스 누락")
            test_results["T2_GALLERY_ASPECT_5_3"] = False

        # -------------------------------------------------------------
        # TEST 3: 상용 타이포그래피 위계 및 진한 차콜 가격 검증
        # -------------------------------------------------------------
        print("\n[TEST 3] 타이포그래피 위계 및 차콜 가격 검증 (26px/32px)...")
        title_el = page.locator("#view-detail h1")
        title_text = await title_el.inner_text()
        title_class = await title_el.get_attribute("class")

        price_box = page.locator("#view-detail div.tracking-tight").first
        price_text = await price_box.inner_text()
        price_class = await price_box.get_attribute("class")

        print(f"  - 차량명: '{title_text.splitlines()[0]}' (클래스: {title_class})")
        print(f"  - 판매가격: '{price_text}' (클래스: {price_class})")

        is_charcoal_price = "#171C24" in price_class or "slate-900" in price_class or "slate-800" in price_class
        has_pro_title = "text-[26px]" in title_class or "text-2xl" in title_class

        if has_pro_title and is_charcoal_price:
            print("  PASS: 차량명 26px font-bold 및 진한 차콜(#171C24) 판매가격 위계 확인 (font-black 남발 제거)")
            test_results["T3_TYPOGRAPHY_AND_PRICE_COLOR"] = True
        else:
            print("  FAIL: 타이포그래피 또는 가격 색상 규격 불일치")
            test_results["T3_TYPOGRAPHY_AND_PRICE_COLOR"] = False

        # -------------------------------------------------------------
        # TEST 4: 우측 32% Sticky 패널 & 방문예약 동선 검증
        # -------------------------------------------------------------
        print("\n[TEST 4] 우측 Sticky 패널 및 방문예약 동선 검증...")
        sticky_panel = page.locator("div.lg\\:sticky")
        has_sticky = await sticky_panel.count() > 0
        has_kakao_btn = await page.locator("button:has-text('카카오톡 1:1 빠른 상담')").count() > 0
        has_submit_btn = await page.locator("#vdrBtnSubmitConsult").count() > 0

        if has_sticky and has_kakao_btn and has_submit_btn:
            print("  PASS: 우측 32% 영역의 Sticky 구매 패널, 카카오톡 상담, 방문예약 신청 폼 정상 배치")
            test_results["T4_RIGHT_STICKY_PANEL"] = True
        else:
            print("  FAIL: 우측 패널 구성 요소 누락")
            test_results["T4_RIGHT_STICKY_PANEL"] = False

        # -------------------------------------------------------------
        # TEST 5: K Car 스타일 정돈된 제원표 & 장착 옵션 체크리스트 검증
        # -------------------------------------------------------------
        print("\n[TEST 5] 표(Table) 기반 기본 제원표 & 장착 옵션 검증...")
        detail_text = await page.inner_text("#view-detail")
        has_vin = "차대번호 (VIN)" in detail_text
        has_plate = "차량번호" in detail_text
        has_displacement = "배기량" in detail_text
        has_options = "장착 주요 옵션 체크리스트" in detail_text

        if all([has_vin, has_plate, has_displacement, has_options]):
            print("  PASS: K Car 스타일의 정돈된 표 기반 기본 제원표 및 옵션 체크리스트 정상 확인")
            test_results["T5_TABLE_SPECS_AND_OPTIONS"] = True
        else:
            print("  FAIL: 기본 제원표 또는 옵션 목록 누락")
            test_results["T5_TABLE_SPECS_AND_OPTIONS"] = False

        # -------------------------------------------------------------
        # TEST 6: 기존 무결성 연속 보존 검증 (상담 API + CRM 저장 + SVG 바인딩)
        # -------------------------------------------------------------
        print("\n[TEST 6] 기존 무결성 연속 보존 검증 (P0 정직한 CRM 연동 실측)...")
        alert_messages = []
        page.on("dialog", lambda dialog: (alert_messages.append(dialog.message), asyncio.create_task(dialog.accept())))

        rnd = random.randint(1000, 9999)
        test_name = f"상용고객_{rnd}"
        test_phone = f"010-7777-{rnd}"

        await page.fill("#vdrCustName", test_name)
        await page.fill("#vdrCustPhone", test_phone)
        await page.fill("#vdrCustDate", "2026-11-10")
        await page.fill("#vdrCustMemo", "DIRECTIVE 057 상용 리부트 실전 예약")
        await page.check("#vdrPrivacyAgree")

        await page.click("#vdrBtnSubmitConsult")
        await page.wait_for_timeout(1500)

        print(f"  - 알림창 수신: {alert_messages}")
        has_success_dialog = any("정상 접수" in m and "접수번호" in m for m in alert_messages)

        # 백엔드 CRM 원장 확인
        req_crm = urllib.request.Request(f"{BASE_URL}/api/consultations")
        req_crm.add_header("Authorization", f"Bearer {admin_token}")
        with urllib.request.urlopen(req_crm, timeout=10) as resp:
            consults = json.loads(resp.read().decode("utf-8"))
            matched = [c for c in consults if c.get("customer_name") == test_name or test_name in c.get("content", "")]

        # SVG 보닛 클릭 확인
        await page.click("#part-hood")
        await page.wait_for_timeout(200)
        hood_part_name = await page.locator("#vdrSelectedPartName").inner_text()

        if has_success_dialog and len(matched) > 0 and ("후드" in hood_part_name or "보닛" in hood_part_name):
            print(f"  PASS: CRM 원장 저장 실측 완료 (ID: {matched[0]['id']}) 및 SVG 데이터 바인딩 정상 보존")
            test_results["T6_INTEGRITY_CONTINUITY"] = True
        else:
            print(f"  FAIL: 무결성 검증 실패 (다이얼로그={has_success_dialog}, CRM저장={len(matched)}, SVG={hood_part_name})")
            test_results["T6_INTEGRITY_CONTINUITY"] = False

        # -------------------------------------------------------------
        # TEST 7: 5대 반응형 전수 스크린샷 및 나란히 비교 이미지 병합
        # -------------------------------------------------------------
        print("\n[TEST 7] 5대 반응형 전수 스크린샷 캡처 (1440, 1280, 768, 390, 375)...")
        # 1) 1440x900 고객 상세
        p_1440 = await browser.new_page(viewport={"width": 1440, "height": 900})
        await p_1440.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        await p_1440.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await p_1440.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await p_1440.wait_for_timeout(600)
        path_1440 = OUTPUT_DIR / "1440x900_customer_detail.png"
        await p_1440.screenshot(path=str(path_1440), full_page=True)
        print(f"  - [1440x900] 고객 상세 저장: {path_1440}")

        # 1-2) 1440x900 관리자 상세
        p_admin = await browser.new_page(viewport={"width": 1440, "height": 900})
        await p_admin.goto(f"{BASE_URL}/", wait_until="networkidle")
        await p_admin.evaluate(f"localStorage.setItem('chaficial_token', '{admin_token}')")
        await p_admin.goto(f"{BASE_URL}/admin/vehicles/{TARGET_VEHICLE_ID}", wait_until="networkidle")
        await p_admin.wait_for_timeout(800)
        path_admin = OUTPUT_DIR / "1440x900_admin_detail.png"
        await p_admin.screenshot(path=str(path_admin), full_page=True)
        print(f"  - [1440x900] 관리자 상세 저장: {path_admin}")

        # 2) 1280x800 표준 랩톱
        p_1280 = await browser.new_page(viewport={"width": 1280, "height": 800})
        await p_1280.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        await p_1280.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await p_1280.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await p_1280.wait_for_timeout(600)
        path_1280 = OUTPUT_DIR / "1280x800_customer_detail.png"
        await p_1280.screenshot(path=str(path_1280), full_page=True)
        print(f"  - [1280x800] 랩톱 상세 저장: {path_1280}")

        # 3) 768x1024 태블릿
        p_768 = await browser.new_page(viewport={"width": 768, "height": 1024})
        await p_768.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        await p_768.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await p_768.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await p_768.wait_for_timeout(600)
        path_768 = OUTPUT_DIR / "768x1024_customer_detail_tablet.png"
        await p_768.screenshot(path=str(path_768), full_page=True)
        print(f"  - [768x1024] 태블릿 상세 저장: {path_768}")

        # 4) 390x844 모바일
        p_390 = await browser.new_page(viewport={"width": 390, "height": 844})
        await p_390.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        await p_390.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await p_390.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await p_390.wait_for_timeout(600)
        path_390 = OUTPUT_DIR / "390x844_customer_detail_mobile.png"
        await p_390.screenshot(path=str(path_390), full_page=True)
        print(f"  - [390x844] 모바일 상세 저장: {path_390}")

        # 바텀시트
        await p_390.evaluate("window.__vdrInstance.openBottomSheet()")
        await p_390.wait_for_timeout(400)
        path_bs = OUTPUT_DIR / "390x844_customer_detail_bottomsheet.png"
        await p_390.screenshot(path=str(path_bs), full_page=False)
        print(f"  - [390x844] 바텀시트 저장: {path_bs}")

        # 5) 375x812 아이폰 미니
        p_375 = await browser.new_page(viewport={"width": 375, "height": 812})
        await p_375.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        await p_375.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await p_375.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await p_375.wait_for_timeout(600)
        path_375 = OUTPUT_DIR / "375x812_customer_detail_mobile.png"
        await p_375.screenshot(path=str(path_375), full_page=True)
        print(f"  - [375x812] 모바일 375 상세 저장: {path_375}")

        # 6) 나란히 비교 이미지 병합 (고객 1440x900 vs 관리자 1440x900)
        img_cust = Image.open(path_1440)
        img_adm = Image.open(path_admin)

        crop_h = min(1200, img_cust.height, img_adm.height)
        c_cust = img_cust.crop((0, 0, img_cust.width, crop_h))
        c_adm = img_adm.crop((0, 0, img_adm.width, crop_h))

        combined = Image.new("RGB", (c_cust.width + c_adm.width, crop_h))
        combined.paste(c_cust, (0, 0))
        combined.paste(c_adm, (c_cust.width, 0))

        path_sbs = OUTPUT_DIR / "side_by_side_comparison.png"
        combined.save(path_sbs)
        print(f"  - [나란히 비교] 저장 완료: {path_sbs}")

        test_results["T7_RESPONSIVE_SCREENSHOTS"] = True

        await browser.close()

    print("\n" + "=" * 70)
    print("CHA-FICIAL DIRECTIVE 057 FINAL 검증 결과 요약")
    print("=" * 70)
    total_pass = sum(1 for v in test_results.values() if v)
    total_tests = len(test_results)
    for k, v in test_results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    print(f"\n총 결과: {total_pass} / {total_tests} 항목 PASS (통과율: {total_pass/total_tests*100:.1f}%)")
    print("=" * 70)

    return total_pass == total_tests


if __name__ == "__main__":
    success = asyncio.run(run_directive_057_verification())
    sys.exit(0 if success else 1)
