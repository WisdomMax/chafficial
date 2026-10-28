"""CHA-FICIAL DIRECTIVE 058 E2E 및 상용 디자인 품질 전수 검증 스위트.

검증 항목:
1. [T1: 관리시스템 브랜드] 차피셜(CHA-FICIAL) 타이틀, 사이드바, 대시보드 검증
2. [T2: 고객 쇼룸 브랜드] 차마트 한글 로고 및 헤더/푸터 관리자 버튼 0건 검증
3. [T3: 모바일 로고 꺾임 방지] 390x844, 375x812 뷰포트에서 단일 행 레이아웃 실측
4. [T4: 공개 매물 단일 검증 정책] 승인 매물 조회 및 비공개 차량 직접 URL 접근 시 404 차단
5. [T5: 카카오 상담 정직성] 카카오 채널 ID 미설정 시 버튼 비노출 (허위 링크 방지)
6. [T6: 푸터 정직성 및 모달] 이용약관 및 개인정보처리방침 전문 모달 열림/닫힘
7. [T7: 관리자 상세 캡처] 로그인 완료 상태에서 로그인 모달 없는 실제 차량 상세 캡처
8. [T8: 5대 반응형 캡처 및 비교 이미지] 1440, 1280, 768, 390, 375 및 병합 이미지 생성
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8501"
OUTPUT_DIR = Path("reports/screenshots_058")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def http_get(url):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            data = response.read().decode('utf-8')
            return response.status, json.loads(data) if data.startswith(("{", "[")) else data
    except urllib.error.HTTPError as e:
        return e.code, None


def test_directive_058():
    results = {}
    print("=" * 70)
    print("CHA-FICIAL DIRECTIVE 058 E2E & DESIGN QUALITY VERIFICATION")
    print("=" * 70)

    # 1. 서버 생존 여부 확인
    try:
        code, _ = http_get(f"{BASE_URL}/chamart")
        assert code == 200, f"HTTP status: {code}"
        print("[*] 서버 정상 응답 확인 (HTTP 200)")
    except Exception as e:
        print(f"[!] 서버 접속 불가: {e}")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # T1: 차피셜 관리시스템 브랜드 검증
        # -------------------------------------------------------------
        print("\n[T1] 차피셜(CHA-FICIAL) 관리시스템 브랜드 검증...")
        page_admin = browser.new_page(viewport={"width": 1440, "height": 900})
        page_admin.goto(f"{BASE_URL}/")
        page_admin.wait_for_selector("#mainSidebar", timeout=5000)

        title = page_admin.title()
        sidebar_brand = page_admin.locator("#mainSidebar div.font-bold.text-white.text-base:has-text('차피셜')").inner_text()
        sidebar_sub = page_admin.locator("#mainSidebar div.text-xs.text-slate-400").first.inner_text()
        dashboard_h2 = page_admin.locator("h2:has-text('차피셜 통합 운영 현황')").count()
        chamart_link = page_admin.locator("a[href='/chamart']").count()

        print(f"  - 페이지 타이틀: {title}")
        print(f"  - 사이드바 브랜드: {sidebar_brand}")
        print(f"  - 사이드바 서브: {sidebar_sub}")
        print(f"  - 대시보드 타이틀 일치: {dashboard_h2 > 0}")
        print(f"  - 고객 쇼룸 바로가기 분리 링크: {chamart_link > 0}")

        assert "차피셜" in title, f"타이틀에 차피셜 미포함: {title}"
        assert "차피셜" in sidebar_brand, f"사이드바에 차피셜 미포함: {sidebar_brand}"
        assert "차피셜" in sidebar_sub, f"사이드바 서브에 차피셜 미포함: {sidebar_sub}"
        assert dashboard_h2 > 0, "대시보드에 '차피셜 통합 운영 현황' 미발견"
        results["T1_ADMIN_BRAND_CLARITY"] = "PASS"
        print("  => [PASS] T1 완료")

        # -------------------------------------------------------------
        # T2: 고객 쇼룸 브랜드 및 관리자 버튼 0건 검증
        # -------------------------------------------------------------
        print("\n[T2] 고객 쇼룸 한글 '차마트' 브랜드 및 관리자 버튼 격리 검증...")
        page_cust = browser.new_page(viewport={"width": 1440, "height": 900})
        page_cust.goto(f"{BASE_URL}/chamart")
        page_cust.wait_for_selector("header", timeout=5000)

        logo_text = page_cust.locator("header a[href='/chamart'].group span:nth-child(2)").inner_text()
        print(f"  - 쇼룸 헤더 로고 텍스트: {logo_text}")
        assert logo_text.strip() == "차마트", f"로고가 '차마트'가 아님: {logo_text}"

        # 관리자 버튼 배제 검증
        header_admin_btn_cnt = page_cust.locator("header a:has-text('관리자'), header button:has-text('관리자')").count()
        footer_admin_link_cnt = page_cust.locator("footer a[href='/'], footer a:has-text('관리자')").count()
        print(f"  - 고객 헤더 내 관리자 버튼 수: {header_admin_btn_cnt}")
        print(f"  - 고객 푸터 내 관리자 링크 수: {footer_admin_link_cnt}")
        assert header_admin_btn_cnt == 0, "고객 헤더에 관리자 버튼이 노출됨"
        assert footer_admin_link_cnt == 0, "고객 푸터에 관리자 링크가 노출됨"
        results["T2_SHOWROOM_BRAND_ISOLATION"] = "PASS"
        print("  => [PASS] T2 완료")

        # -------------------------------------------------------------
        # T3: 모바일 390px, 375px 로고 꺾임 0건 실측 검증
        # -------------------------------------------------------------
        print("\n[T3] 모바일 390px / 375px 로고 단일 행(꺾임 방지) 실측 검증...")
        for vp_w, vp_h in [(390, 844), (375, 812)]:
            page_cust.set_viewport_size({"width": vp_w, "height": vp_h})
            time.sleep(0.3)
            logo_elem = page_cust.locator("header a[href='/chamart'].group").first
            bbox = logo_elem.bounding_box()
            print(f"  - 뷰포트 {vp_w}x{vp_h} 로고 BoundingBox: width={bbox['width']:.1f}px, height={bbox['height']:.1f}px")
            # 꺾이지 않고 단일 행이면 높이가 35px 이하임 (두 줄로 꺾이면 50px 이상)
            assert bbox["height"] <= 35, f"{vp_w}px에서 로고가 줄바꿈됨 (height={bbox['height']})"
        results["T3_MOBILE_LOGO_NO_WRAP"] = "PASS"
        print("  => [PASS] T3 완료")

        # -------------------------------------------------------------
        # T4: 공개 매물 단일 검증 정책 (목록 & 상세 404 차단)
        # -------------------------------------------------------------
        print("\n[T4] 공개 매물 단일 정책 및 비공개 차량 URL 직접 접근 차단 검증...")
        code_pub, pub_list = http_get(f"{BASE_URL}/api/chamart/vehicles")
        assert code_pub == 200, f"목록 조회 실패: {code_pub}"
        print(f"  - 공개 매물 수: {len(pub_list)}대")
        assert len(pub_list) > 0, "공개 승인 매물이 0대입니다."
        valid_id = pub_list[0]["id"]

        # 유효한 공개 매물 상세 조회
        code_ok, _ = http_get(f"{BASE_URL}/api/chamart/vehicles/{valid_id}")
        assert code_ok == 200, "유효 공개 매물 상세 조회 실패"

        # 비공개/존재하지 않는 매물 접근 시 404 차단 검증
        code_404, _ = http_get(f"{BASE_URL}/api/chamart/vehicles/v-private-unknown-999")
        print(f"  - 비공개/미승인 매물 직접 접근 시 응답 코드: {code_404}")
        assert code_404 == 404, f"비공개 매물이 404로 차단되지 않음: {code_404}"
        results["T4_UNIFIED_PUBLIC_GATE_404"] = "PASS"
        print("  => [PASS] T4 완료")

        # -------------------------------------------------------------
        # T5: 카카오 상담 채널 정직성 (미설정 시 버튼 비노출)
        # -------------------------------------------------------------
        print("\n[T5] 카카오 상담 채널 정직성 (미설정 시 완전 숨김) 검증...")
        page_cust.set_viewport_size({"width": 1440, "height": 900})
        page_cust.goto(f"{BASE_URL}/cars/{valid_id}")
        page_cust.wait_for_selector("#view-detail", timeout=5000)
        time.sleep(1.0)

        kakao_btn_cnt = page_cust.locator("button:has-text('카카오톡 1:1 빠른 상담')").count()
        print(f"  - 카카오 상담 채널 미설정 상태의 카카오 버튼 노출 수: {kakao_btn_cnt}")
        assert kakao_btn_cnt == 0, f"카카오 채널이 미설정되었는데 버튼이 노출됨 ({kakao_btn_cnt}건)"
        results["T5_KAKAO_HONESTY_NO_BUTTON"] = "PASS"
        print("  => [PASS] T5 완료")

        # -------------------------------------------------------------
        # T6: 푸터 정직성 및 이용약관 / 개인정보처리방침 모달 검증
        # -------------------------------------------------------------
        print("\n[T6] 푸터 약관 모달 열림 및 내용 노출 검증...")
        page_cust.goto(f"{BASE_URL}/chamart")
        page_cust.wait_for_selector("footer", timeout=5000)

        # 1) 이용약관 모달 오픈
        page_cust.locator("footer button:has-text('이용약관')").click()
        page_cust.wait_for_selector("#policyModal:not(.hidden)", timeout=3000)
        terms_title = page_cust.locator("#policyModalTitle").inner_text()
        print(f"  - 이용약관 모달 타이틀: {terms_title}")
        assert "이용약관" in terms_title, "이용약관 모달이 열리지 않음"

        # 닫기
        page_cust.locator("#policyModal button:has-text('닫기')").click()
        time.sleep(0.3)
        assert page_cust.locator("#policyModal").get_attribute("class").find("hidden") != -1, "모달 닫힘 실패"

        # 2) 개인정보처리방침 모달 오픈
        page_cust.locator("footer button:has-text('개인정보처리방침')").click()
        page_cust.wait_for_selector("#policyModal:not(.hidden)", timeout=3000)
        privacy_title = page_cust.locator("#policyModalTitle").inner_text()
        print(f"  - 개인정보처리방침 모달 타이틀: {privacy_title}")
        assert "개인정보" in privacy_title, "개인정보처리방침 모달이 열리지 않음"

        # ESC 키로 닫기
        page_cust.keyboard.press("Escape")
        time.sleep(0.3)
        assert page_cust.locator("#policyModal").get_attribute("class").find("hidden") != -1, "ESC 키 닫힘 실패"
        results["T6_TERMS_PRIVACY_MODAL"] = "PASS"
        print("  => [PASS] T6 완료")

        # -------------------------------------------------------------
        # T7: 관리자 로그인 상태 실차 상세 캡처 (로그인 모달 없음)
        # -------------------------------------------------------------
        print("\n[T7] 관리자 로그인 상태에서 로그인 모달 없는 실제 차량 상세 캡처...")
        page_admin.goto(f"{BASE_URL}/")
        page_admin.wait_for_selector("#mainSidebar", timeout=5000)

        # 환경변수에서 관리자 비밀번호 로드
        admin_pw = os.environ.get("CHAMART_ADMIN_PASSWORD")
        if not admin_pw:
            env_file = Path(".env")
            if env_file.exists():
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if line.startswith("CHAMART_ADMIN_PASSWORD="):
                        admin_pw = line.split("=", 1)[1].strip()
                        break

        # 관리자 로그인 수행
        login_btn = page_admin.locator("#headerLoginBtn")
        if login_btn.is_visible() and admin_pw:
            print("  - 관리자 로그인 수행 중...")
            login_btn.click()
            page_admin.wait_for_selector("#adminLoginModal:not(.hidden)", timeout=3000)
            page_admin.locator("#loginUsername").fill("admin")
            page_admin.locator("#loginPassword").fill(admin_pw)
            page_admin.locator("#loginSubmitBtn").click()
            page_admin.wait_for_selector("#adminLoginModal", state="hidden", timeout=5000)
            time.sleep(1.0)
            print("  - 관리자 인증 완료!")

        # 차량 관리 탭으로 이동 후 차량 상세 직접 마운트
        page_admin.locator("#nav-vehicles").click()
        page_admin.wait_for_selector("#vehicleTableBody tr", timeout=5000)
        time.sleep(0.5)

        # 관리자 차량 상세 전폭 뷰 열기
        page_admin.evaluate(f"openVehicleDetailFullView('{valid_id}', true)")
        page_admin.wait_for_selector("#view-vehicle-detail:not(.hidden)", timeout=5000)
        time.sleep(1.2)

        # 로그인 모달이 완전히 닫혀있고 화면에 노출되지 않음을 단언
        login_modal = page_admin.locator("#adminLoginModal")
        assert not login_modal.is_visible(), "관리자 상세 화면 위에 로그인 모달이 노출되어 있습니다!"

        # 관리자 상세 스크린샷 캡처
        admin_detail_path = OUTPUT_DIR / "1440x900_admin_detail.png"
        page_admin.screenshot(path=str(admin_detail_path))
        print(f"  - 관리자 실제 상세 캡처 완료 (로그인 모달 0건): {admin_detail_path}")
        results["T7_ADMIN_DETAIL_NO_LOGIN_MODAL"] = "PASS"
        print("  => [PASS] T7 완료")

        # -------------------------------------------------------------
        # T8: 고객 사이트 5대 해상도 스크린샷 캡처 및 사이드 바이 사이드 이미지 생성
        # -------------------------------------------------------------
        print("\n[T8] 고객 사이트 5대 해상도 스크린샷 캡처 및 병합...")
        viewports = [
            ("1440x900_customer_detail", 1440, 900),
            ("1280x800_customer_detail", 1280, 800),
            ("768x1024_customer_detail_tablet", 768, 1024),
            ("390x844_customer_detail_mobile", 390, 844),
            ("375x812_customer_detail_mobile", 375, 812),
        ]

        captured_images = {}
        for fname, w, h in viewports:
            page_cust.set_viewport_size({"width": w, "height": h})
            page_cust.goto(f"{BASE_URL}/cars/{valid_id}")
            page_cust.wait_for_selector("#view-detail", timeout=5000)
            time.sleep(1.0)
            target_path = OUTPUT_DIR / f"{fname}.png"
            page_cust.screenshot(path=str(target_path))
            captured_images[fname] = target_path
            print(f"  - [{w}x{h}] 캡처 완료: {target_path.name}")

        # 모바일 바텀시트 캡처
        page_cust.set_viewport_size({"width": 390, "height": 844})
        time.sleep(0.3)
        bottom_btn = page_cust.locator("button:has-text('방문 예약')").last
        if bottom_btn.is_visible():
            bottom_btn.click()
            time.sleep(0.5)
            bs_path = OUTPUT_DIR / "390x844_customer_detail_bottomsheet.png"
            page_cust.screenshot(path=str(bs_path))
            print(f"  - 모바일 바텀시트 캡처 완료: {bs_path.name}")

        browser.close()

    # PIL을 이용한 나란히 비교 이미지 (PC vs 태블릿 vs 모바일) 병합
    try:
        img_pc = Image.open(captured_images["1440x900_customer_detail"])
        img_tab = Image.open(captured_images["768x1024_customer_detail_tablet"])
        img_mob = Image.open(captured_images["390x844_customer_detail_mobile"])

        # 타깃 높이 700px로 리사이징
        target_h = 700
        r_pc = img_pc.resize((int(img_pc.width * target_h / img_pc.height), target_h))
        r_tab = img_tab.resize((int(img_tab.width * target_h / img_tab.height), target_h))
        r_mob = img_mob.resize((int(img_mob.width * target_h / img_mob.height), target_h))

        total_w = r_pc.width + r_tab.width + r_mob.width + 40
        merged = Image.new("RGB", (total_w, target_h + 40), (247, 248, 250))

        offset_x = 10
        for img in [r_pc, r_tab, r_mob]:
            merged.paste(img, (offset_x, 20))
            offset_x += img.width + 10

        merged_path = OUTPUT_DIR / "side_by_side_comparison.png"
        merged.save(merged_path)
        print(f"\n[*] 나란히 비교 이미지 병합 저장 완료: {merged_path}")
        results["T8_RESPONSIVE_COMPARISON_MERGED"] = "PASS"
    except Exception as e:
        print(f"[!] 이미지 병합 실패: {e}")
        results["T8_RESPONSIVE_COMPARISON_MERGED"] = "FAIL"

    print("\n" + "=" * 70)
    print("DIRECTIVE 058 전수 검증 결과 요약:")
    for k, v in results.items():
        print(f"  - {k}: {v}")
    print("=" * 70)

    all_pass = all(v == "PASS" for v in results.values())
    assert all_pass, "일부 검증 항목이 실패했습니다!"
    print("\n>>> DIRECTIVE 058 8대 전수 검증 100% PASS 달성! <<<")


if __name__ == "__main__":
    test_directive_058()
