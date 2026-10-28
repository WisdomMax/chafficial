#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 063: 실차 검증 강화, 견적서 실시간 수치 동기화, 실측 좌표 길찾기, 모바일 Sticky 비교표 E2E 종합 테스트."""

import json
import os
import sys
import time
from PIL import Image
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8501"
OUTPUT_DIR = "reports/screenshots_063"
os.makedirs(OUTPUT_DIR, exist_ok=True)

test_results = {}

def log_test(test_id, name, passed, detail=""):
    test_results[test_id] = {"name": name, "passed": passed, "detail": detail}
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_id}: {name} - {detail}")

def run_tests():
    print("=" * 80)
    print("[*] DIRECTIVE 063 E2E 종합 무결성 검증 시작...")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # TEST 1: P0 허위 공인 성능문서 완전 제거 & 정직한 전산 대기 배지 검증
        # -------------------------------------------------------------
        print("\n--- TEST 1: P0 허위 성능점검표 완전 제거 및 대기 배지 검증 ---")
        context_pc = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context_pc.new_page()
        page.goto(f"{BASE_URL}/chamart")
        page.wait_for_selector("#vehicleGrid")
        time.sleep(1)

        # 첫 번째 차량 상세로 이동
        page.click("#vehicleGrid > div:first-child")
        page.wait_for_selector("#vdrSpecTable")
        time.sleep(1)

        has_fake_modal = page.evaluate("() => Boolean(document.getElementById('vdrInspectionDocModal'))")
        badge_text = page.locator("#vdrInspectionPendingBadge").inner_text()
        t1_pass = (not has_fake_modal) and ("확인 중" in badge_text or "대기" in badge_text)
        log_test("T1_NO_FAKE_DOC", "허위 공인 성능문서 완전 제거 및 정직한 전산 대기 안내", t1_pass, f"FakeModalExist: {has_fake_modal}, BadgeText: '{badge_text}'")

        # -------------------------------------------------------------
        # TEST 2: P0 실차 사진 및 테스트/데모 차량 배제 가드 검증
        # -------------------------------------------------------------
        print("\n--- TEST 2: P0 실차 사진 및 데모 차량 격리 가드 검증 ---")
        page.click("#vdrBtnBack")
        page.wait_for_selector("#vehicleGrid")
        time.sleep(1)

        # 공개된 매물들의 모델명에 '테스트'나 'demo'가 없어야 함
        public_titles = page.evaluate("() => Array.from(document.querySelectorAll('#vehicleGrid h3')).map(el => el.innerText)")
        has_demo = any("테스트" in t.lower() or "demo" in t.lower() for t in public_titles)

        # 등록된 사진이 placeholder가 아니어야 함
        img_srcs = page.evaluate("() => Array.from(document.querySelectorAll('#vehicleGrid img')).map(el => el.src)")
        has_placeholder_img = any("placeholder" in s.lower() and "neutral" not in s.lower() for s in img_srcs)

        t2_pass = (not has_demo) and (not has_placeholder_img) and (len(public_titles) >= 2)
        log_test("T2_REAL_PHOTO_GUARD", "실차 사진 및 데모/테스트 차량 격리 가드", t2_pass, f"PublicVehicles: {len(public_titles)}, HasDemo: {has_demo}, HasPlaceholder: {has_placeholder_img}")

        # -------------------------------------------------------------
        # TEST 3: P1 관심 차량 찜(하트) 토글 및 새로고침 localStorage 복원 검증
        # -------------------------------------------------------------
        print("\n--- TEST 3: P1 찜(하트) 토글 및 localStorage 영속화 검증 ---")
        # 첫 번째 카드의 찜 버튼 클릭
        first_fav_btn = page.locator("[data-fav-btn]").first
        fav_vid = first_fav_btn.get_attribute("data-fav-btn")
        first_fav_btn.click()
        time.sleep(0.5)

        stored_favs = page.evaluate("() => JSON.parse(localStorage.getItem('chamart_favorites') || '[]')")
        is_stored = fav_vid in stored_favs

        page.reload()
        page.wait_for_selector("#vehicleGrid")
        time.sleep(1)

        reloaded_icon_class = page.locator(f'[data-fav-btn="{fav_vid}"] i, [data-fav-btn="{fav_vid}"] svg').get_attribute("class") or ""
        is_reloaded_filled = "text-rose-500" in reloaded_icon_class

        t3_pass = is_stored and is_reloaded_filled
        log_test("T3_FAVORITE_PERSISTENCE", "찜(하트) 토글 및 새로고침 localStorage 영속화", t3_pass, f"StoredIDs: {stored_favs}, ReloadedFilled: {is_reloaded_filled}")

        # -------------------------------------------------------------
        # TEST 4: P1 최대 3대 차량 비교함 (Sticky 열 & 실측 차액 정렬) 검증
        # -------------------------------------------------------------
        print("\n--- TEST 4: P1 최대 3대 차량 비교함 & Sticky 열 검증 ---")
        checkboxes = page.locator(".compare-checkbox")
        cb_count = checkboxes.count()

        # 2대 이상 선택
        checkboxes.nth(0).check()
        time.sleep(0.3)
        checkboxes.nth(1).check()
        time.sleep(0.3)
        if cb_count >= 3:
            checkboxes.nth(2).check()
            time.sleep(0.3)

        bar_count = page.locator("#compareCount").inner_text()
        btn_open = page.locator("#btnOpenCompareModal")
        btn_enabled = not btn_open.is_disabled()

        btn_open.click()
        page.wait_for_selector("#compareModal:not(.hidden)")
        time.sleep(1)

        # Sticky 클래스 적용 확인
        has_sticky_th = page.evaluate("() => Boolean(document.querySelector('#compareTableContainer th.sticky'))")
        has_sticky_td = page.evaluate("() => Boolean(document.querySelector('#compareTableContainer td.sticky'))")
        cols_count = page.locator("#compareTableContainer thead th").count()

        t4_pass = btn_enabled and (cols_count >= 3) and has_sticky_th and has_sticky_td
        log_test("T4_COMPARE_STICKY_TABLE", "최대 3대 비교함 & Sticky 열 가로스크롤 검증", t4_pass, f"BarCount: {bar_count}, ColsCount: {cols_count}, StickyTH: {has_sticky_th}, StickyTD: {has_sticky_td}")

        page.screenshot(path=f"{OUTPUT_DIR}/1440x900_compare_3cars_modal.png")
        page.locator("#compareModal button:has-text('확인 닫기')").click()
        time.sleep(0.5)

        # -------------------------------------------------------------
        # TEST 5: P2 견적서 모달 실시간 계산값 동기화 검산 검증 (DIRECTIVE 063 핵심)
        # -------------------------------------------------------------
        print("\n--- TEST 5: P2 견적서 모달 실시간 계산값 동기화 검산 검증 ---")
        page.click("#vehicleGrid > div:first-child")
        page.wait_for_selector("#vdrSpecTable")
        time.sleep(1)

        # 할부 계산기 옵션 변경 (선수금 20%, 36개월, 연 6.9%)
        page.select_option("#vdrCalcDownPayment", "20")
        page.select_option("#vdrCalcMonths", "36")
        page.select_option("#vdrCalcRate", "0.069")
        time.sleep(0.5)

        # 견적서 모달 열기
        page.click("#vdrBtnOpenEstimate")
        page.wait_for_selector("#vdrEstimatePrintModal:not(.hidden)")
        time.sleep(1)

        # 모달 내부 텍스트 검증
        down_text = page.locator("#vdrEstDownText").inner_text()
        months_text = page.locator("#vdrEstMonthsText").inner_text()
        rate_text = page.locator("#vdrEstRateText").inner_text()
        monthly_text = page.locator("#vdrEstMonthlyText").inner_text()
        has_disclaimer = page.evaluate("() => document.getElementById('vdrEstimatePrintModal').innerText.includes('실제 금융사 심사 결과')")

        t5_pass = ("20%" in down_text) and ("36개월" in months_text) and ("6.9%" in rate_text) and ("월 약" in monthly_text) and has_disclaimer
        log_test("T5_ESTIMATE_REALTIME_SYNC", "견적서 모달 실시간 계산값 동기화 및 법적 고지 검증", t5_pass, f"Down: '{down_text}', Months: '{months_text}', Rate: '{rate_text}', Monthly: '{monthly_text}', Disclaimer: {has_disclaimer}")

        page.screenshot(path=f"{OUTPUT_DIR}/1440x900_estimate_print_modal.png")
        page.locator("#vdrEstimatePrintModal button:has-text('닫기')").click()
        time.sleep(0.5)

        # -------------------------------------------------------------
        # TEST 6: P3 전시장 공식 도로명 주소 및 실측 WGS84 좌표 길찾기 검증
        # -------------------------------------------------------------
        print("\n--- TEST 6: P3 공식 도로명 주소 및 실측 WGS84 좌표 길찾기 검증 ---")
        page.click("#vdrBtnOpenWayfinding")
        page.wait_for_selector("#vdrWayfindingModal:not(.hidden)")
        time.sleep(1)

        modal_text = page.locator("#vdrWayfindingModal").inner_text()
        has_road_addr = "자동차시장1길 70" in modal_text
        has_coords = "37.56191" in modal_text and "127.06424" in modal_text

        kakao_href = page.locator('#vdrWayfindingModal a:has-text("카카오맵")').get_attribute("href") or ""
        naver_href = page.locator('#vdrWayfindingModal a:has-text("네이버지도")').get_attribute("href") or ""
        has_url_coords = ("37.56191" in kakao_href) and ("127.06424" in naver_href)

        t6_pass = has_road_addr and has_coords and has_url_coords
        log_test("T6_VERIFIED_SHOWROOM_WAYFINDING", "전시장 공식 도로명 주소 및 실측 WGS84 좌표 일치 검증", t6_pass, f"HasRoadAddr: {has_road_addr}, HasCoords: {has_coords}, UrlCoords: {has_url_coords}")

        page.screenshot(path=f"{OUTPUT_DIR}/1440x900_wayfinding_modal.png")
        page.locator("#vdrWayfindingModal button:has-text('확인 닫기')").click()
        time.sleep(0.5)

        # -------------------------------------------------------------
        # TEST 7: 멀티 뷰포트 스크린샷 캡처
        # -------------------------------------------------------------
        print("\n--- TEST 7: 멀티 뷰포트 규격 실측 스크린샷 캡처 ---")
        # 1440x900
        page.set_viewport_size({"width": 1440, "height": 900})
        page.screenshot(path=f"{OUTPUT_DIR}/1440x900_customer_detail.png")
        page.click("#vdrBtnBack")
        page.wait_for_selector("#vehicleGrid")
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/1440x900_chamart_home.png")

        # 1280x800
        page.set_viewport_size({"width": 1280, "height": 800})
        page.click("#vehicleGrid > div:first-child")
        page.wait_for_selector("#vdrSpecTable")
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/1280x800_customer_detail.png")

        # 768x1024
        page.set_viewport_size({"width": 768, "height": 1024})
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/768x1024_customer_detail_tablet.png")

        # 390x844 (Mobile iPhone 14)
        page.set_viewport_size({"width": 390, "height": 844})
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/390x844_customer_detail_mobile.png")
        page.click("#vdrBtnOpenWayfinding")
        page.wait_for_selector("#vdrWayfindingModal:not(.hidden)")
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/390x844_wayfinding_mobile.png")
        page.locator("#vdrWayfindingModal button:has-text('확인 닫기')").click()
        time.sleep(0.5)

        # 모바일 비교 모달 가로스크롤 화면 캡처
        page.click("#vdrBtnBack")
        page.wait_for_selector("#vehicleGrid")
        time.sleep(0.5)
        page.locator("#btnOpenCompareModal").click()
        page.wait_for_selector("#compareModal:not(.hidden)")
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/390x844_compare_modal_mobile.png")
        page.locator("#compareModal button:has-text('확인 닫기')").click()
        time.sleep(0.5)

        # 375x812 (Mobile iPhone SE)
        page.set_viewport_size({"width": 375, "height": 812})
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/375x812_chamart_mobile.png")

        context_pc.close()
        browser.close()

    # 사이드 바이 사이드 2x2 종합 비교 이미지 병합
    try:
        img_home = Image.open(f"{OUTPUT_DIR}/1440x900_chamart_home.png")
        img_compare = Image.open(f"{OUTPUT_DIR}/1440x900_compare_3cars_modal.png")
        img_est = Image.open(f"{OUTPUT_DIR}/1440x900_estimate_print_modal.png")
        img_way = Image.open(f"{OUTPUT_DIR}/1440x900_wayfinding_modal.png")

        w, h = 720, 450
        grid_img = Image.new("RGB", (w * 2, h * 2), (255, 255, 255))
        grid_img.paste(img_home.resize((w, h)), (0, 0))
        grid_img.paste(img_compare.resize((w, h)), (w, 0))
        grid_img.paste(img_est.resize((w, h)), (0, h))
        grid_img.paste(img_way.resize((w, h)), (w, h))

        grid_path = f"{OUTPUT_DIR}/side_by_side_comparison_063.png"
        grid_img.save(grid_path)
        print(f"[*] 2x2 종합 비교 이미지 생성 완료: {grid_path}")
    except Exception as e:
        print(f"[!] 이미지 결합 중 오류: {e}")

    print("\n" + "=" * 80)
    print("DIRECTIVE 063 최종 E2E 검증 결과 보고서")
    print("=" * 80)
    all_passed = True
    for tid, res in test_results.items():
        st = "PASS" if res["passed"] else "FAIL"
        if not res["passed"]:
            all_passed = False
        print(f"[{st}] {tid}: {res['name']} ({res['detail']})")

    print(f"\n전체 통과 여부: {'100% PASS SUCCESS' if all_passed else 'SOME TESTS FAILED'}")
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(run_tests())
