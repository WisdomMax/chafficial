#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 062: 엔카·K Car급 상용 쇼핑 UX (찜·비교·견적·길찾기) E2E 검증 및 실측 스크린샷 캡처 스크립트."""

import json
import os
import sys
import time
from PIL import Image
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8501"
OUTPUT_DIR = "reports/screenshots_062"
os.makedirs(OUTPUT_DIR, exist_ok=True)

test_results = {}

def log_test(test_id, name, passed, detail=""):
    test_results[test_id] = {"name": name, "passed": passed, "detail": detail}
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {test_id}: {name} - {detail}")

def run_tests():
    print("=" * 80)
    print("[*] DIRECTIVE 062 상용 쇼핑 UX E2E 종합 검증 시작...")
    print("=" * 80)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # TEST 1: P0 허위 공인 문서 완전 제거 & 정직한 전산 대기 배지 검증
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

        # 가짜 공인 성능기록부 원본 보기 모달(#vdrInspectionDocModal)이 DOM에 완전히 존재하지 않아야 함
        has_fake_modal = page.evaluate("() => Boolean(document.getElementById('vdrInspectionDocModal'))")
        
        # 정직한 대기 배지(#vdrInspectionPendingBadge)가 화면에 보이는지 확인
        badge_text = page.locator("#vdrInspectionPendingBadge").inner_text()
        t1_pass = (not has_fake_modal) and ("확인 중" in badge_text or "대기" in badge_text)
        log_test("T1_NO_FAKE_DOC", "허위 공인 성능문서 완전 제거 및 정직한 전산 대기 안내", t1_pass, f"FakeModalExist: {has_fake_modal}, BadgeText: '{badge_text}'")

        # -------------------------------------------------------------
        # TEST 2: P1 관심 차량 찜(하트) 토글 및 localStorage 복원 검증
        # -------------------------------------------------------------
        print("\n--- TEST 2: P1 찜(하트) 토글 및 localStorage 영속화 검증 ---")
        # 상세페이지 상단 하트 버튼 클릭
        fav_btn = page.locator("#vdrBtnFavorite")
        fav_btn.click()
        time.sleep(0.5)

        # localStorage에 저장되었는지 확인
        stored_favs = page.evaluate("() => JSON.parse(localStorage.getItem('chamart_favorites') || '[]')")
        has_stored = len(stored_favs) > 0
        fav_id = stored_favs[0] if has_stored else None

        # 목록으로 돌아가서 동일 차량 카드의 하트가 채워져 있는지 확인
        page.click("#vdrBtnBack")
        page.wait_for_selector("#vehicleGrid")
        time.sleep(1)

        card_fav_icon_class = page.locator(f'[data-fav-btn="{fav_id}"] i, [data-fav-btn="{fav_id}"] svg').get_attribute("class") or ""
        is_card_filled = "text-rose-500" in card_fav_icon_class or "fill-rose-500" in card_fav_icon_class

        # 새로고침 후에도 유지되는지 검증
        page.reload()
        page.wait_for_selector("#vehicleGrid")
        time.sleep(1)

        card_fav_reloaded_class = page.locator(f'[data-fav-btn="{fav_id}"] i, [data-fav-btn="{fav_id}"] svg').get_attribute("class") or ""
        is_reloaded_filled = "text-rose-500" in card_fav_reloaded_class or "fill-rose-500" in card_fav_reloaded_class

        t2_pass = has_stored and is_card_filled and is_reloaded_filled
        log_test("T2_FAVORITE_STORAGE", "찜(하트) 토글 및 localStorage 새로고침 영속화", t2_pass, f"StoredIDs: {stored_favs}, CardFilled: {is_card_filled}, ReloadedFilled: {is_reloaded_filled}")

        # -------------------------------------------------------------
        # TEST 3: P1 최대 3대 차량 비교함 (플로팅 바 및 비교 모달) 검증
        # -------------------------------------------------------------
        print("\n--- TEST 3: P1 최대 3대 차량 비교함 플로팅 바 & 모달 검증 ---")
        # 전체 3대 차량의 ID 수집
        cards = page.locator("#vehicleGrid > div")
        card_count = cards.count()

        # 1번째 차량 체크
        page.locator(".compare-checkbox").nth(0).check()
        time.sleep(0.5)
        bar_count_1 = page.locator("#compareCount").inner_text()
        btn_open_disabled = page.locator("#btnOpenCompareModal").is_disabled()

        # 2번째 차량 체크
        page.locator(".compare-checkbox").nth(1).check()
        time.sleep(0.5)
        bar_count_2 = page.locator("#compareCount").inner_text()
        btn_open_enabled = not page.locator("#btnOpenCompareModal").is_disabled()

        # 3번째 차량 체크 (있는 경우)
        if card_count >= 3:
            page.locator(".compare-checkbox").nth(2).check()
            time.sleep(0.5)
        bar_count_3 = page.locator("#compareCount").inner_text()

        # 비교하기 모달 오픈
        page.locator("#btnOpenCompareModal").click()
        page.wait_for_selector("#compareModal:not(.hidden)")
        time.sleep(1)

        # 비교 테이블 렌더링 확인 (th 개수 = 1(항목) + N(차량))
        col_count = page.locator("#compareTableContainer thead th").count()
        t3_pass = (bar_count_2 == "2") and btn_open_enabled and (col_count >= 3)
        log_test("T3_COMPARE_BAR_MODAL", "최대 3대 차량 비교함 플로팅 바 및 비교 모달 렌더링", t3_pass, f"BarCount2: {bar_count_2}, BtnEnabled: {btn_open_enabled}, ModalCols: {col_count}")

        # 3대 비교 모달 스크린샷 캡처
        page.screenshot(path=f"{OUTPUT_DIR}/1440x900_compare_3cars_modal.png")

        # 1대 제외 후 2대 비교 스크린샷 캡처
        if col_count > 3:
            page.locator("#compareTableContainer thead th button").nth(0).click()
            time.sleep(0.5)
            page.screenshot(path=f"{OUTPUT_DIR}/1440x900_compare_2cars_modal.png")

        # 비교 모달 닫기
        page.locator("#compareModal button:has-text('확인 닫기')").click()
        time.sleep(0.5)

        # -------------------------------------------------------------
        # TEST 4: P2 실차 예상 구매비용 안내서 (견적서) 인쇄/저장 모달 검증
        # -------------------------------------------------------------
        print("\n--- TEST 4: P2 실차 예상 구매비용 안내서(견적서) 인쇄 모달 검증 ---")
        # 차량 상세로 이동
        page.click("#vehicleGrid > div:first-child")
        page.wait_for_selector("#vdrSpecTable")
        time.sleep(1)

        # 견적서 모달 열기 버튼 클릭
        page.click("#vdrBtnOpenEstimate")
        page.wait_for_selector("#vdrEstimatePrintModal:not(.hidden)")
        time.sleep(1)

        # 견적서 내 필수 텍스트 검증
        estimate_title = page.locator("#vdrEstimatePrintModal h3").inner_text()
        has_disclaimer = page.evaluate("() => document.getElementById('vdrEstimatePrintModal').innerText.includes('실제 금융사 심사 결과')")
        has_tax_info = page.evaluate("() => document.getElementById('vdrEstimatePrintModal').innerText.includes('예상 취득세')")

        t4_pass = ("예상 구매비용 안내서" in estimate_title) and has_disclaimer and has_tax_info
        log_test("T4_ESTIMATE_PRINT_MODAL", "예상 구매비용 안내서(견적서) 모달 및 검산 안내 검증", t4_pass, f"Title: '{estimate_title}', HasDisclaimer: {has_disclaimer}, HasTax: {has_tax_info}")

        # 견적서 모달 스크린샷 캡처
        page.screenshot(path=f"{OUTPUT_DIR}/1440x900_estimate_print_modal.png")

        # 견적서 모달 닫기
        page.locator("#vdrEstimatePrintModal button:has-text('닫기')").click()
        time.sleep(0.5)

        # -------------------------------------------------------------
        # TEST 5: P3 공식 지도 길찾기 모달 및 클립보드 주소 복사 검증
        # -------------------------------------------------------------
        print("\n--- TEST 5: P3 공식 지도 길찾기 모달 및 주소 복사 검증 ---")
        page.click("#vdrBtnOpenWayfinding")
        page.wait_for_selector("#vdrWayfindingModal:not(.hidden)")
        time.sleep(1)

        # 공식 지도 URL Scheme 검증
        kakao_href = page.locator('#vdrWayfindingModal a:has-text("카카오맵")').get_attribute("href") or ""
        naver_href = page.locator('#vdrWayfindingModal a:has-text("네이버지도")').get_attribute("href") or ""

        t5_pass = ("map.kakao.com/link/to" in kakao_href) and ("map.naver.com/v5/directions" in naver_href)
        log_test("T5_WAYFINDING_MAPS", "카카오맵/네이버지도 공식 길찾기 딥링크 검증", t5_pass, f"Kakao: {kakao_href[:40]}..., Naver: {naver_href[:40]}...")

        # 길찾기 모달 스크린샷 캡처
        page.screenshot(path=f"{OUTPUT_DIR}/1440x900_wayfinding_modal.png")

        # 길찾기 모달 닫기
        page.locator("#vdrWayfindingModal button:has-text('확인 닫기')").click()
        time.sleep(0.5)

        # -------------------------------------------------------------
        # TEST 6: 멀티 뷰포트 규격 실측 스크린샷 캡처 (1440, 1280, 768, 390, 375)
        # -------------------------------------------------------------
        print("\n--- TEST 6: 멀티 뷰포트 규격 실측 스크린샷 캡처 ---")

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

        # 768x1024 (Tablet)
        page.set_viewport_size({"width": 768, "height": 1024})
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/768x1024_customer_detail_tablet.png")

        # 390x844 (Mobile iPhone 12/13/14)
        page.set_viewport_size({"width": 390, "height": 844})
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/390x844_customer_detail_mobile.png")

        # 모바일에서 길찾기 모달 열기
        page.click("#vdrBtnOpenWayfinding")
        page.wait_for_selector("#vdrWayfindingModal:not(.hidden)")
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/390x844_wayfinding_mobile.png")
        page.locator("#vdrWayfindingModal button:has-text('확인 닫기')").click()
        time.sleep(0.5)

        # 모바일 홈 및 비교 바
        page.click("#vdrBtnBack")
        page.wait_for_selector("#vehicleGrid")
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/390x844_chamart_home_with_compare_bar.png")

        # 375x812 (Mobile iPhone SE/X)
        page.set_viewport_size({"width": 375, "height": 812})
        time.sleep(0.5)
        page.screenshot(path=f"{OUTPUT_DIR}/375x812_chamart_mobile.png")

        context_pc.close()
        browser.close()

    # -------------------------------------------------------------
    # 7. 사이드 바이 사이드 비교 이미지 병합 생성
    # -------------------------------------------------------------
    try:
        img_home = Image.open(f"{OUTPUT_DIR}/1440x900_chamart_home.png")
        img_compare = Image.open(f"{OUTPUT_DIR}/1440x900_compare_3cars_modal.png")
        img_est = Image.open(f"{OUTPUT_DIR}/1440x900_estimate_print_modal.png")
        img_way = Image.open(f"{OUTPUT_DIR}/1440x900_wayfinding_modal.png")

        # 2x2 그리드 결합
        w, h = 720, 450
        grid_img = Image.new("RGB", (w * 2, h * 2), (255, 255, 255))
        grid_img.paste(img_home.resize((w, h)), (0, 0))
        grid_img.paste(img_compare.resize((w, h)), (w, 0))
        grid_img.paste(img_est.resize((w, h)), (0, h))
        grid_img.paste(img_way.resize((w, h)), (w, h))

        grid_path = f"{OUTPUT_DIR}/side_by_side_comparison_062.png"
        grid_img.save(grid_path)
        print(f"[*] 2x2 종합 비교 이미지 생성 완료: {grid_path}")
    except Exception as e:
        print(f"[!] 이미지 결합 중 오류: {e}")

    # 최종 결과 요약
    print("\n" + "=" * 80)
    print("DIRECTIVE 062 최종 E2E 검증 결과 보고서")
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
