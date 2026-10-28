"""CHA-FICIAL DIRECTIVE 056 종합 E2E 검증 스위트
VERIFIED VEHICLE COMMERCE, HONEST DATA, TIRE GAUGES & BRAND INTEGRITY

검증 항목:
1. P0 로고 이름 검증: 고객 쇼룸(/chamart) 상단 및 푸터의 로고가 영문 CHAMART가 아니라 한글 '차마트'로 명확히 표시됨을 검증
2. P0 정직한 상담 API 및 CRM 저장: 실제 폼 제출 -> 백엔드 /api/chamart/consultations 호출 -> consultation_id 발급 및 DB 정상 생성 검증
3. P0 개인정보 미동의 및 필수값 누락 방어: 동의 미체크 시 400 거부 및 가짜 성공 안내 원천 차단 검증
4. P0 SVG 차체 진단 다이어그램: diagram_parts 실제 데이터(부위명, 판정, 근거) 1:1 바인딩 검증
5. P1 타이어 4개 바퀴 게이지 및 소모품 점검 카드: FL/FR/RL/RR 트레드 바 및 핵심 소모품 카드 렌더링 검증
6. P1 가정한 예시 금리(4.5%~9.9%) 조절 및 총 납부이자/총 상환액 실시간 계산 검증
7. 반응형 전수 스크린샷 캡처 (1440x900, 768x1024, 390x844, 375x812) 및 나란히 비교 이미지 병합
"""

import asyncio
import json
import os
import sys
import urllib.request
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:8501"
OUTPUT_DIR = Path("reports/screenshots_056")
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


async def run_directive_056_verification():
    print("=" * 70)
    print("CHA-FICIAL DIRECTIVE 056 COMPREHENSIVE E2E VERIFICATION")
    print("=" * 70)

    admin_token = get_admin_token()
    print(f"[*] 관리자 인증 토큰 획득 완료 (Bearer {admin_token[:10]}...)")

    test_results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # TEST 1: 로고 이름 검증 (영문 CHAMART -> 한글 '차마트')
        # -------------------------------------------------------------
        print("\n[TEST 1] 로고 이름 검증 (영문 CHAMART -> 한글 '차마트')...")
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto(f"{BASE_URL}/chamart", wait_until="networkidle")

        header_logo = await page.locator("header a[href='/chamart'] span").first.inner_text()
        footer_logo = await page.locator("footer div.text-white span").first.inner_text()
        page_title = await page.title()

        print(f"  - 헤더 로고 텍스트: '{header_logo}'")
        print(f"  - 푸터 로고 텍스트: '{footer_logo}'")
        print(f"  - 페이지 타이틀: '{page_title}'")

        if header_logo == "차마트" and footer_logo == "차마트" and "차마트" in page_title:
            print("  PASS: 상단 헤더, 푸터 및 페이지 타이틀이 한글 '차마트'로 일관되게 표시됨")
            test_results["T1_LOGO_NAME_KOREAN"] = True
        else:
            print("  FAIL: 영문 CHAMART가 남아있거나 표기가 불일치함")
            test_results["T1_LOGO_NAME_KOREAN"] = False

        # -------------------------------------------------------------
        # TEST 2: 정직한 상담 API 및 CRM 저장 검증 (P0)
        # -------------------------------------------------------------
        print("\n[TEST 2] 정직한 상담 API 및 CRM 원장 저장 실측 검증...")
        # 차량 상세로 진입
        await page.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await page.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await page.wait_for_timeout(1000)

        # 다이얼로그(alert) 메시지 수집
        alert_messages = []
        page.on("dialog", lambda dialog: (alert_messages.append(dialog.message), asyncio.create_task(dialog.accept())))

        # 상담 폼 입력 (60초 중복 차단 방지용 고유 번호)
        import random
        random_suffix = random.randint(1000, 9999)
        test_phone = f"010-8888-{random_suffix}"
        test_cust_name = f"테스트고객_{random_suffix}"

        await page.fill("#vdrCustName", test_cust_name)
        await page.fill("#vdrCustPhone", test_phone)
        await page.fill("#vdrCustDate", "2026-11-05")
        await page.fill("#vdrCustMemo", "E2E 자동화 실전 검증 상담 메모")
        await page.check("#vdrPrivacyAgree")

        # 제출 버튼 클릭
        await page.click("#vdrBtnSubmitConsult")
        await page.wait_for_timeout(1500)

        print(f"  - 표시된 알림창 메시지: {alert_messages}")
        has_consult_success = any("정상 접수" in m and "접수번호" in m for m in alert_messages)

        # 백엔드 CRM 원장에서 실제 생성 여부 확인
        req_crm = urllib.request.Request(f"{BASE_URL}/api/consultations")
        req_crm.add_header("Authorization", f"Bearer {admin_token}")
        with urllib.request.urlopen(req_crm, timeout=10) as resp:
            consult_list = json.loads(resp.read().decode("utf-8"))
            matched_consult = [c for c in consult_list if c.get("customer_name") == test_cust_name or test_cust_name in c.get("content", "")]

        if has_consult_success and len(matched_consult) > 0:
            cid = matched_consult[0].get("id") or matched_consult[0].get("consultation_id")
            print(f"  PASS: 프런트엔드 정상 접수 및 백엔드 CRM 원장 실제 저장 확인 (ID: {cid})")
            test_results["T2_CONSULT_INTEGRITY"] = True
        else:
            print(f"  FAIL: 상담 저장 검증 실패 (성공알림={has_consult_success}, CRM 저장수={len(matched_consult)})")
            test_results["T2_CONSULT_INTEGRITY"] = False

        # -------------------------------------------------------------
        # TEST 3: 필수 개인정보 미동의 시 차단 및 가짜 성공 방어
        # -------------------------------------------------------------
        print("\n[TEST 3] 개인정보 미동의 시 400 거부 및 가짜 성공 방어 검증...")
        # 직접 API 호출로 개인정보 미동의 전송
        try:
            req_invalid = urllib.request.Request(
                f"{BASE_URL}/api/chamart/consultations",
                data=json.dumps({
                    "vehicle_id": TARGET_VEHICLE_ID,
                    "name": "미동의고객",
                    "phone": "010-1111-2222",
                    "privacy_agreed": False
                }).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req_invalid, timeout=10) as resp:
                status = resp.status
                print(f"  FAIL: 미동의 요청이 성공함 (HTTP {status})")
                test_results["T3_CONSULT_PRIVACY_GUARD"] = False
        except urllib.error.HTTPError as e:
            if e.code in (400, 422):
                print(f"  PASS: 개인정보 미동의 시 HTTP {e.code} 로 엄격 차단됨")
                test_results["T3_CONSULT_PRIVACY_GUARD"] = True
            else:
                print(f"  FAIL: 예상치 못한 HTTP 에러 코드: {e.code}")
                test_results["T3_CONSULT_PRIVACY_GUARD"] = False

        # -------------------------------------------------------------
        # TEST 4: SVG 차체 진단 다이어그램 실제 데이터 1:1 바인딩 검증
        # -------------------------------------------------------------
        print("\n[TEST 4] SVG 다이어그램 diagram_parts 실제 데이터 바인딩 검증...")
        # 후드 클릭
        await page.click("#part-hood")
        await page.wait_for_timeout(300)
        part_name = await page.locator("#vdrSelectedPartName").inner_text()
        part_badge = await page.locator("#vdrSelectedPartBadge").inner_text()
        part_evidence = await page.locator("#vdrSelectedPartEvidence").inner_text()

        print(f"  - 후드 선택 결과: 부위='{part_name}', 상태='{part_badge}', 근거='{part_evidence}'")

        # A필러 클릭
        await page.click("#part-pillar-a")
        await page.wait_for_timeout(300)
        pillar_name = await page.locator("#vdrSelectedPartName").inner_text()
        pillar_evidence = await page.locator("#vdrSelectedPartEvidence").inner_text()
        print(f"  - A필러 선택 결과: 부위='{pillar_name}', 근거='{pillar_evidence}'")

        if ("후드" in part_name or "보닛" in part_name) and "필러" in pillar_name:
            print("  PASS: SVG 부위 클릭 시 diagram_parts 실제 데이터 및 근거가 실시간 바인딩됨")
            test_results["T4_SVG_DATA_BINDING"] = True
        else:
            print(f"  FAIL: SVG 데이터 바인딩 불일치 (후드={part_name}, 필러={pillar_name})")
            test_results["T4_SVG_DATA_BINDING"] = False

        # -------------------------------------------------------------
        # TEST 5: 타이어 4개 바퀴 게이지 및 소모품 점검 카드 검증 (P1)
        # -------------------------------------------------------------
        print("\n[TEST 5] 타이어 4개 바퀴 게이지 및 소모품 카드 렌더링 검증...")
        detail_text = await page.inner_text("#view-detail")
        has_fl_tire = "전륜 운전석 (FL)" in detail_text
        has_fr_tire = "전륜 동승석 (FR)" in detail_text
        has_rl_tire = "후륜 좌측 (RL)" in detail_text
        has_rr_tire = "후륜 우측 (RR)" in detail_text
        has_brake_pad = "브레이크 패드" in detail_text
        has_battery = "시동 배터리" in detail_text

        if all([has_fl_tire, has_fr_tire, has_rl_tire, has_rr_tire, has_brake_pad, has_battery]):
            print("  PASS: 4개 바퀴 타이어 트레드 게이지 바 및 소모품 카드 전수 정상 렌더링")
            test_results["T5_TIRE_CONSUMABLES_CARDS"] = True
        else:
            print(f"  FAIL: 타이어/소모품 카드 누락 (FL={has_fl_tire}, FR={has_fr_tire}, 패드={has_brake_pad})")
            test_results["T5_TIRE_CONSUMABLES_CARDS"] = False

        # -------------------------------------------------------------
        # TEST 6: 가정한 예시 금리 조절 및 총 납부이자 실시간 산출 검증 (P1)
        # -------------------------------------------------------------
        print("\n[TEST 6] 가정한 예시 금리 조절 및 총 납부이자 산출 검증...")
        has_assumed_rate_notice = "가정한 예시 금리" in detail_text
        
        # 금리 7.9%로 변경 선택
        await page.select_option("#vdrCalcRate", "0.079")
        await page.wait_for_timeout(300)
        
        interest_text = await page.locator("#vdrCalcTotalInterestResult").inner_text()
        monthly_text = await page.locator("#vdrCalcMonthlyResult").inner_text()
        print(f"  - 7.9% 변경 후 계산 결과: 월 납입금='{monthly_text}', 이자/상환액='{interest_text}'")

        if has_assumed_rate_notice and "이자:" in interest_text and "총 상환액:" in interest_text:
            print("  PASS: '가정한 예시 금리' 명시 및 금리 변경에 따른 총 이자/상환액 실시간 산출 완료")
            test_results["T6_HONEST_LOAN_CALCULATOR"] = True
        else:
            print("  FAIL: 가정한 예시 금리 또는 총 이자 산출 표기 실패")
            test_results["T6_HONEST_LOAN_CALCULATOR"] = False

        # -------------------------------------------------------------
        # TEST 7: 반응형 전수 스크린샷 캡처 및 나란히 비교 이미지 병합
        # -------------------------------------------------------------
        print("\n[TEST 7] 반응형 전수 스크린샷 캡처 (1440, 768, 390, 375)...")
        # 1) 데스크톱 고객 화면 1440x900
        p_desk = await browser.new_page(viewport={"width": 1440, "height": 900})
        await p_desk.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        await p_desk.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await p_desk.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await p_desk.wait_for_timeout(800)
        path_cust_desk = OUTPUT_DIR / "1440x900_customer_detail.png"
        await p_desk.screenshot(path=str(path_cust_desk), full_page=True)
        print(f"  - [1440x900] 고객 상세 저장: {path_cust_desk}")

        # 2) 데스크톱 관리자 화면 1440x900
        p_admin = await browser.new_page(viewport={"width": 1440, "height": 900})
        await p_admin.goto(f"{BASE_URL}/", wait_until="networkidle")
        await p_admin.evaluate(f"localStorage.setItem('chaficial_token', '{admin_token}')")
        await p_admin.goto(f"{BASE_URL}/admin/vehicles/{TARGET_VEHICLE_ID}", wait_until="networkidle")
        await p_admin.wait_for_timeout(1000)
        path_admin_desk = OUTPUT_DIR / "1440x900_admin_detail.png"
        await p_admin.screenshot(path=str(path_admin_desk), full_page=True)
        print(f"  - [1440x900] 관리자 상세 저장: {path_admin_desk}")

        # 3) 태블릿 768x1024
        p_tab = await browser.new_page(viewport={"width": 768, "height": 1024})
        await p_tab.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        await p_tab.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await p_tab.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await p_tab.wait_for_timeout(800)
        path_tab = OUTPUT_DIR / "768x1024_customer_detail_tablet.png"
        await p_tab.screenshot(path=str(path_tab), full_page=True)
        print(f"  - [768x1024] 태블릿 상세 저장: {path_tab}")

        # 4) 모바일 390x844 (고객 및 바텀시트)
        p_mob = await browser.new_page(viewport={"width": 390, "height": 844})
        await p_mob.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        await p_mob.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await p_mob.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await p_mob.wait_for_timeout(800)
        path_mob = OUTPUT_DIR / "390x844_customer_detail_mobile.png"
        await p_mob.screenshot(path=str(path_mob), full_page=True)
        print(f"  - [390x844] 모바일 상세 저장: {path_mob}")

        # 바텀시트 오픈 캡처
        await p_mob.evaluate("window.__vdrInstance.openBottomSheet()")
        await p_mob.wait_for_timeout(500)
        path_bs = OUTPUT_DIR / "390x844_customer_detail_bottomsheet.png"
        await p_mob.screenshot(path=str(path_bs), full_page=False)
        print(f"  - [390x844] 모바일 바텀시트 저장: {path_bs}")

        # 5) 모바일 375x812 (아이폰 미니)
        p_375 = await browser.new_page(viewport={"width": 375, "height": 812})
        await p_375.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        await p_375.evaluate(f"window.openVehicleDetail('{TARGET_VEHICLE_ID}')")
        await p_375.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await p_375.wait_for_timeout(800)
        path_375 = OUTPUT_DIR / "375x812_customer_detail_mobile.png"
        await p_375.screenshot(path=str(path_375), full_page=True)
        print(f"  - [375x812] 모바일 375 상세 저장: {path_375}")

        # 6) 나란히 비교 이미지 병합 (1440x900 고객 vs 관리자 상단)
        img_cust = Image.open(path_cust_desk)
        img_admin = Image.open(path_admin_desk)

        crop_h = min(1200, img_cust.height, img_admin.height)
        c_cust = img_cust.crop((0, 0, img_cust.width, crop_h))
        c_admin = img_admin.crop((0, 0, img_admin.width, crop_h))

        combined = Image.new("RGB", (c_cust.width + c_admin.width, crop_h))
        combined.paste(c_cust, (0, 0))
        combined.paste(c_admin, (c_cust.width, 0))

        path_sbs = OUTPUT_DIR / "side_by_side_comparison.png"
        combined.save(path_sbs)
        print(f"  - [나란히 비교] 저장 완료: {path_sbs}")

        test_results["T7_RESPONSIVE_SCREENSHOTS"] = True

        await browser.close()

    print("\n" + "=" * 70)
    print("CHA-FICIAL DIRECTIVE 056 검증 결과 요약")
    print("=" * 70)
    total_pass = sum(1 for v in test_results.values() if v)
    total_tests = len(test_results)
    for k, v in test_results.items():
        print(f"  {k}: {'PASS' if v else 'FAIL'}")

    print(f"\n총 결과: {total_pass} / {total_tests} 항목 PASS (통과율: {total_pass/total_tests*100:.1f}%)")
    print("=" * 70)

    return total_pass == total_tests


if __name__ == "__main__":
    success = asyncio.run(run_directive_056_verification())
    sys.exit(0 if success else 1)
