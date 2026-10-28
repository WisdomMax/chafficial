#!/usr/bin/env python3
"""DIRECTIVE 064 6대 무결성 E2E 자동화 검증 테스트 스크립트."""

import os
import sys
import time
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("reports/screenshots_064")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = Path("reports/estimate_A4_directive_064.pdf")

BASE_URL = "http://127.0.0.1:8501"

def run_tests():
    print("=" * 70)
    print("CHA-FICIAL DIRECTIVE 064 E2E 무결성 검증 테스트 시작")
    print("=" * 70)

    results = {}
    screenshots = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # T1: 운영 실차 검증 가드 및 정직한 0건 빈 상태 (Zero-Inventory)
        # -------------------------------------------------------------
        print("\n[*] T1: 운영 모드 실차 사진 원장 검증 및 정직한 0건 안내 상태 검사...")
        ctx_pc = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx_pc.new_page()

        page.goto(f"{BASE_URL}/chamart?mode=prod", wait_until="networkidle")
        time.sleep(1)

        # 0대 배지 확인
        count_badge = page.text_content("#vehicleCountBadge")
        print(f"    - 현재 판매 중인 실차 재고 배지: {count_badge}")

        # 정직한 0건 안내 텍스트 확인
        body_text = page.inner_text("body")
        has_honest_empty = "현재 실차 검증 기준을 통과한 매물을 등록 준비 중입니다" in body_text
        has_no_fake = "가짜 사진이나 합성 카드를 실차로 둔갑시켜 등록하지 않습니다" in body_text
        has_demo_switch_btn = page.is_visible("button:has-text('데모 모드')") or "데모 모드" in body_text

        t1_pass = (count_badge == "0대") and has_honest_empty and has_no_fake and has_demo_switch_btn
        results["T1_HONEST_ZERO_INVENTORY_EMPTY_STATE"] = t1_pass
        print(f"    - T1 결과: {'PASS' if t1_pass else 'FAIL'} (0대: {count_badge == '0대'}, 정직고지: {has_honest_empty}, 가짜배제: {has_no_fake})")

        p_t1 = OUTPUT_DIR / "1440x900_chamart_prod_honest_empty.png"
        page.screenshot(path=str(p_t1))
        screenshots["prod_empty"] = p_t1

        # -------------------------------------------------------------
        # T2: 데모 쇼룸 모드 전환 및 격리 안내 배너 & 매물 카드 검사
        # -------------------------------------------------------------
        print("\n[*] T2: 데모 쇼룸 모드 전환 및 격리 안내 검사...")
        page.click("#btnModeToggle")
        time.sleep(1)

        demo_banner_visible = page.is_visible("#demoModeBanner")
        demo_banner_text = page.inner_text("#demoModeBanner") if demo_banner_visible else ""
        print(f"    - 데모 안내 배너 노출: {demo_banner_visible} (텍스트: {demo_banner_text[:40]}...)")

        demo_count_badge = page.text_content("#vehicleCountBadge")
        print(f"    - 데모 모드 매물 수 배지: {demo_count_badge}")

        # 매물 카드에 'UI 검수용' 배지 확인
        card_badges = page.locator(".aspect-\\[5\\/3\\] span").all_text_contents()
        print(f"    - 매물 카드 배지들: {card_badges}")
        has_ui_demo_badge = any("UI 검수용" in b for b in card_badges)

        t2_pass = demo_banner_visible and (demo_count_badge == "3대") and has_ui_demo_badge
        results["T2_DEMO_SHOWROOM_MODE_AND_ISOLATION"] = t2_pass
        print(f"    - T2 결과: {'PASS' if t2_pass else 'FAIL'} (배너: {demo_banner_visible}, 3대: {demo_count_badge == '3대'}, 검수용배지: {has_ui_demo_badge})")

        p_t2 = OUTPUT_DIR / "1440x900_chamart_demo_home.png"
        page.screenshot(path=str(p_t2))
        screenshots["demo_home"] = p_t2

        # -------------------------------------------------------------
        # T3: 단일 순수 할부 계산 함수 수학 일치 및 상세 계산기 연동
        # -------------------------------------------------------------
        print("\n[*] T3: 단일 순수 계산 함수 수학 검증 및 상세 계산기 수치 일치 검사...")
        calc_test = page.evaluate("""() => {
            const res = window.calculateVehicleLoanPure({
                priceWon: 42000000,
                downRate: 20,
                annualRate: 6.9,
                months: 36
            });
            // 경계조건 테스트
            const resZero = window.calculateVehicleLoanPure({
                priceWon: 42000000,
                downRate: 100,
                annualRate: 6.9,
                months: 36
            });
            const resZeroRate = window.calculateVehicleLoanPure({
                priceWon: 36000000,
                downRate: 0,
                annualRate: 0,
                months: 36
            });
            return {
                base: res,
                zeroDown: resZero,
                zeroRate: resZeroRate
            };
        }""")

        b = calc_test["base"]
        print(f"    - 4,200만원/20%/36개월/6.9% -> 선수금: {b['downTenThousand']}만원, 원금: {b['principalTenThousand']}만원, 월: {b['monthlyWon']}원({b['monthlyTenThousand']}만원), 이자: {b['totalInterestWon']}원({b['totalInterestTenThousand']}만원)")
        math_correct = (
            b["downTenThousand"] == 840
            and b["principalTenThousand"] == 3360
            and b["monthlyTenThousand"] == 104  # 1,035,934원 반올림
            and b["totalInterestTenThousand"] == 369  # 3,693,624원 반올림
            and calc_test["zeroDown"]["principalWon"] == 0
            and calc_test["zeroDown"]["monthlyWon"] == 0
            and calc_test["zeroRate"]["monthlyWon"] == 1000000
        )

        # 상세 페이지 열어서 계산기 셀렉트 조작 후 일치 확인
        page.click("#vehicleGrid > div:first-child")
        time.sleep(1.5)

        # 상세 화면 스크린샷
        p_t3_detail = OUTPUT_DIR / "1440x900_vehicle_detail_pc.png"
        page.screenshot(path=str(p_t3_detail))
        screenshots["detail_pc"] = p_t3_detail

        # 선수금 20%, 36개월, 6.9% 설정
        page.select_option("#vdrCalcDownPayment", "20")
        page.select_option("#vdrCalcMonths", "36")
        page.select_option("#vdrCalcRate", "0.069")
        time.sleep(0.5)

        monthly_res_text = page.text_content("#vdrCalcMonthlyResult")
        total_res_text = page.text_content("#vdrCalcTotalInterestResult")
        print(f"    - 상세 계산기 결과: '{monthly_res_text}', '{total_res_text}'")

        calc_dom_match = ("104만원" in monthly_res_text) and ("369만원" in total_res_text)

        t3_pass = math_correct and calc_dom_match
        results["T3_PURE_LOAN_CALC_EXACT_MATH_AND_BOUNDARY"] = t3_pass
        print(f"    - T3 결과: {'PASS' if t3_pass else 'FAIL'} (수학: {math_correct}, DOM일치: {calc_dom_match})")

        # -------------------------------------------------------------
        # T4: 견적서 모달 동기화 및 실제 Chromium A4 PDF 출력 검증
        # -------------------------------------------------------------
        print("\n[*] T4: 견적서 모달 동기화 및 실제 Chromium A4 PDF 출력 검사...")
        page.click("#vdrBtnOpenEstimate")
        time.sleep(1)

        est_down = page.text_content("#vdrEstDownText")
        est_principal = page.text_content("#vdrEstPrincipalText")
        est_months = page.text_content("#vdrEstMonthsText")
        est_rate = page.text_content("#vdrEstRateText")
        est_monthly = page.text_content("#vdrEstMonthlyText")
        est_interest = page.text_content("#vdrEstInterestText")

        print(f"    - 견적서 모달 수치: 선수금={est_down}, 원금={est_principal}, 기간={est_months}, 금리={est_rate}, 월납={est_monthly}, 이자={est_interest}")

        modal_sync_match = (
            "20%" in est_down and "840만원" in est_down
            and "3,360만원" in est_principal
            and "36개월" in est_months
            and "6.9%" in est_rate
            and "104만원" in est_monthly
            and "369만원" in est_interest
        )

        p_t4_modal = OUTPUT_DIR / "1440x900_estimate_modal.png"
        page.screenshot(path=str(p_t4_modal))
        screenshots["estimate_modal"] = p_t4_modal

        # 실제 Chromium PDF 출력 수행
        page.pdf(
            path=str(PDF_PATH),
            format="A4",
            print_background=True,
            margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"}
        )
        pdf_exists = PDF_PATH.exists() and PDF_PATH.stat().st_size > 5000
        print(f"    - 실제 A4 PDF 생성: {pdf_exists} (크기: {PDF_PATH.stat().st_size if PDF_PATH.exists() else 0} bytes)")

        t4_pass = modal_sync_match and pdf_exists
        results["T4_CHROMIUM_PDF_EXPORT_A4_QUALITY"] = t4_pass
        print(f"    - T4 결과: {'PASS' if t4_pass else 'FAIL'} (모달동기화: {modal_sync_match}, PDF유효: {pdf_exists})")

        page.click("button:has-text('닫기')")
        time.sleep(0.5)

        # -------------------------------------------------------------
        # T5: 1544 임시번호 및 확인되지 않은 안내문구 전수 제거 검증
        # -------------------------------------------------------------
        print("\n[*] T5: 1544 임시번호 및 확인되지 않은 과장문구 전수 제거 검사...")
        # 길찾기 모달 열기
        page.click("#vdrBtnOpenWayfinding")
        time.sleep(0.5)

        p_t5_map = OUTPUT_DIR / "1440x900_wayfinding_modal.png"
        page.screenshot(path=str(p_t5_map))
        screenshots["wayfinding"] = p_t5_map

        wayfinding_text = page.inner_text("#vdrWayfindingModal")
        has_official_measure_badge = "공식 실측" in wayfinding_text
        has_free_parking = "고객 전용 무료 주차장" in wayfinding_text
        has_correct_partner_addr = "서울특별시 성동구 자동차시장1길 70 (용답동)" in wayfinding_text
        has_partner_name = "차마트 제휴 전시장 (장한평)" in wayfinding_text

        page.click("#vdrWayfindingModal button:has-text('확인 닫기')")
        time.sleep(0.5)

        # 전체 렌더링된 텍스트 및 속성에서 1544-0000 스캔
        rendered_body_text = page.inner_text("body")
        has_1544_in_rendered_dom = "1544-0000" in rendered_body_text or "15440000" in rendered_body_text

        t5_pass = (
            (not has_1544_in_rendered_dom)
            and (not has_official_measure_badge)
            and (not has_free_parking)
            and has_correct_partner_addr
            and has_partner_name
        )
        results["T5_NO_TEMP_PHONE_AND_VERIFIED_SHOWROOM"] = t5_pass
        print(f"    - T5 결과: {'PASS' if t5_pass else 'FAIL'} (1544제거: {not has_1544_in_rendered_dom}, 공식실측제거: {not has_official_measure_badge}, 무료주차제거: {not has_free_parking}, 제휴주소일치: {has_correct_partner_addr})")

        ctx_pc.close()

        # -------------------------------------------------------------
        # T6: 모바일 390px Sticky 비교표 & 가로스크롤 안내 인디케이터
        # -------------------------------------------------------------
        print("\n[*] T6: 모바일 390px Sticky 비교표 & 가로스크롤 안내 인디케이터 검사...")
        ctx_mb = browser.new_context(viewport={"width": 390, "height": 844})
        p_mb = ctx_mb.new_page()

        p_mb.goto(f"{BASE_URL}/chamart?mode=demo", wait_until="networkidle")
        time.sleep(1)

        p_t6_home = OUTPUT_DIR / "390x844_chamart_demo_home.png"
        p_mb.screenshot(path=str(p_t6_home))
        screenshots["mb_home"] = p_t6_home

        # 3대 차량 모두 비교함 체크박스 클릭
        checkboxes = p_mb.locator("input[type='checkbox']").all()
        print(f"    - 발견된 비교 체크박스 수: {len(checkboxes)}")
        for cb in checkboxes[:3]:
            cb.check()
            time.sleep(0.3)

        floating_bar_text = p_mb.inner_text("#compareFloatingBar")
        print(f"    - 플로팅 비교바 텍스트: '{floating_bar_text.strip()}'")

        # 비교하기 모달 열기
        p_mb.click("#btnOpenCompareModal")
        time.sleep(1)

        p_t6_modal = OUTPUT_DIR / "390x844_compare_modal_3cars.png"
        p_mb.screenshot(path=str(p_t6_modal))
        screenshots["mb_compare"] = p_t6_modal

        # 1) 가로스크롤 안내 인디케이터 노출 검증
        scroll_hint_visible = p_mb.is_visible("text=좌우로 밀어서 3대 차량 상세 비교")
        print(f"    - 모바일 가로스크롤 안내 바 노출: {scroll_hint_visible}")

        # 2) 첫 열 Sticky 속성 검증
        sticky_eval = p_mb.evaluate("""() => {
            const th = document.querySelector('#compareTableContainer th:first-child');
            if (!th) return false;
            const style = window.getComputedStyle(th);
            return style.position === 'sticky' && parseInt(style.left, 10) === 0;
        }""")
        print(f"    - 1열(비교 항목) Sticky 고정: {sticky_eval}")

        # 3) 차량 상세 모바일 뷰
        p_mb.click("#compareModal button:has-text('확인 닫기')")
        time.sleep(0.5)
        p_mb.click("#vehicleGrid > div:first-child")
        time.sleep(1.5)

        p_t6_detail = OUTPUT_DIR / "390x844_customer_detail_mobile.png"
        p_mb.screenshot(path=str(p_t6_detail))
        screenshots["mb_detail"] = p_t6_detail

        # 태블릿 뷰포트 (768x1024)
        ctx_tab = browser.new_context(viewport={"width": 768, "height": 1024})
        p_tab = ctx_tab.new_page()
        p_tab.goto(f"{BASE_URL}/chamart?mode=demo", wait_until="networkidle")
        time.sleep(1)
        p_tab.click("#vehicleGrid > div:first-child")
        time.sleep(1.5)
        p_t6_tab = OUTPUT_DIR / "768x1024_customer_detail_tablet.png"
        p_tab.screenshot(path=str(p_t6_tab))
        screenshots["tab_detail"] = p_t6_tab
        ctx_tab.close()

        t6_pass = scroll_hint_visible and sticky_eval
        results["T6_MOBILE_390PX_STICKY_COMPARE_AND_HORIZONTAL_SCROLL_HINT"] = t6_pass
        print(f"    - T6 결과: {'PASS' if t6_pass else 'FAIL'} (스크롤힌트: {scroll_hint_visible}, Sticky고정: {sticky_eval})")

        ctx_mb.close()
        browser.close()

    # -------------------------------------------------------------
    # 2x2 종합 비교 이미지 생성
    # -------------------------------------------------------------
    print("\n[*] 종합 2x2 side-by-side 비교 이미지 생성 중...")
    try:
        im1 = Image.open(screenshots["prod_empty"]).resize((720, 450))
        im2 = Image.open(screenshots["demo_home"]).resize((720, 450))
        im3 = Image.open(screenshots["estimate_modal"]).resize((720, 450))
        im4 = Image.open(screenshots["mb_compare"]).resize((720, 450))

        grid = Image.new("RGB", (1440, 900))
        grid.paste(im1, (0, 0))
        grid.paste(im2, (720, 0))
        grid.paste(im3, (0, 450))
        grid.paste(im4, (720, 450))

        grid_path = OUTPUT_DIR / "side_by_side_comparison_064.png"
        grid.save(grid_path)
        print(f"    - 종합 비교 이미지 저장 완료: {grid_path}")
    except Exception as e:
        print(f"    - 종합 비교 이미지 생성 실패: {e}")

    print("\n" + "=" * 70)
    print("CHA-FICIAL DIRECTIVE 064 테스트 최종 결과 요약")
    print("=" * 70)
    all_pass = True
    for name, ok in results.items():
        status_str = "PASS SUCCESS" if ok else "FAIL FAILED"
        print(f"  - [{status_str}] {name}")
        if not ok:
            all_pass = False

    print("=" * 70)
    if all_pass:
        print(">>> 6대 전수 무결성 테스트 100% PASS SUCCESS <<<")
        return 0
    else:
        print(">>> 일부 테스트 실패 <<<")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
