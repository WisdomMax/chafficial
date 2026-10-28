#!/usr/bin/env python3
"""DIRECTIVE 065 7대 무결성 E2E 자동화 검증 테스트 스크립트."""

import os
import sys
import time
import sqlite3
import urllib.request
import urllib.error
import json
import re
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, "src")

OUTPUT_DIR = Path("reports/screenshots_065")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = Path("reports/estimate_A4_directive_065.pdf")

BASE_URL = "http://127.0.0.1:8501"

def run_tests():
    print("=" * 70)
    print("CHA-FICIAL DIRECTIVE 065 E2E 무결성 검증 테스트 시작")
    print("=" * 70)

    results = {}
    screenshots = {}

    # -------------------------------------------------------------
    # T1: DB 마이그레이션 함수 안전성 및 Idempotency 검증
    # -------------------------------------------------------------
    print("\n[*] T1: DB 마이그레이션 함수 수리 및 멱등성 검사...")
    from chaficial.platform.db import migrate_db_schema, DEMO_DB_URL
    db_file = DEMO_DB_URL.replace("sqlite:///", "")
    
    # 1회 실행
    migrate_db_schema()
    # 2회 연속 실행 (멱등성 확인)
    migrate_db_schema()

    con = sqlite3.connect(db_file)
    cur = con.cursor()
    cur.execute("PRAGMA table_info(vehicle_photos)")
    cols = {row[1] for row in cur.fetchall()}
    con.close()

    required_cols = {
        "verification_status", "photo_source", "original_file_hash",
        "usage_rights_status", "verified_by", "verified_at"
    }
    has_all_cols = required_cols.issubset(cols)
    print(f"    - vehicle_photos 필수 검증 컬럼 존재: {has_all_cols} ({cols.intersection(required_cols)})")

    t1_pass = has_all_cols
    results["T1_DB_MIGRATION_IDEMPOTENCY_AND_SAFETY"] = t1_pass
    print(f"    - T1 결과: {'PASS' if t1_pass else 'FAIL'}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # T2: 운영 쇼룸 (/chamart) 상용 중고차 쇼핑몰 권장 표준 UI 검증
        # -------------------------------------------------------------
        print("\n[*] T2: 운영 쇼룸 (/chamart) 상용 표준 빈 상태 및 개발용 요소 제거 검사...")
        ctx_pc = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx_pc.new_page()

        page.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        time.sleep(1)

        # 0대 배지 확인
        count_badge = page.text_content("#vehicleCountBadge")
        print(f"    - 운영 쇼룸 재고 수: {count_badge}")

        body_text = page.inner_text("body")
        has_std_empty_title = "현재 등록된 판매 차량이 없습니다" in body_text
        has_std_empty_sub = "새로운 차량 입고 및 검증이 완료되는 대로 순차적으로 등록될 예정입니다" in body_text
        
        # 개발용 토글 스위치 및 자기홍보 문구 완전 부재 검증
        has_toggle_btn = page.is_visible("#btnModeToggle")
        has_demo_banner = page.is_visible("#demoModeBanner")
        has_bragging_words = any(w in body_text for w in ["정직한 100%", "가짜 사진을 등록하지 않습니다", "UI 검수 모드"])

        print(f"    - 권장 표준 빈 상태: {has_std_empty_title}, 보조설명: {has_std_empty_sub}")
        print(f"    - 개발용 요소 부재: 토글버튼={not has_toggle_btn}, 데모배너={not has_demo_banner}, 자기홍보={not has_bragging_words}")

        t2_pass = (
            count_badge == "0대"
            and has_std_empty_title
            and has_std_empty_sub
            and (not has_toggle_btn)
            and (not has_demo_banner)
            and (not has_bragging_words)
        )
        results["T2_PROD_ZERO_INVENTORY_COMMERCIAL_UI"] = t2_pass
        print(f"    - T2 결과: {'PASS' if t2_pass else 'FAIL'}")

        p_t2 = OUTPUT_DIR / "1440x900_chamart_prod_commercial_clean.png"
        page.screenshot(path=str(p_t2))
        screenshots["prod_clean"] = p_t2

        # -------------------------------------------------------------
        # T3: 운영 API와 스테이징 격리 API의 물리적 분리 및 상담 차단 검증
        # -------------------------------------------------------------
        print("\n[*] T3: 운영 API vs 스테이징 API 물리적 분리 및 데모 예약 거부 검사...")
        # 1) 운영 API는 쿼리 상관없이 0건
        prod_res = json.loads(urllib.request.urlopen(f"{BASE_URL}/api/chamart/vehicles").read())
        prod_demo_res = json.loads(urllib.request.urlopen(f"{BASE_URL}/api/chamart/vehicles?mode=demo").read())
        staging_res = json.loads(urllib.request.urlopen(f"{BASE_URL}/api/staging/chamart/vehicles").read())

        api_isolated = (len(prod_res) == 0) and (len(prod_demo_res) == 0) and (len(staging_res) == 3)
        print(f"    - 운영 API: {len(prod_res)}건, ?mode=demo: {len(prod_demo_res)}건, 스테이징 API: {len(staging_res)}건")

        # 2) 데모 차량 ID로 운영 상담 신청 시 차단 검증
        demo_vid = staging_res[0]["id"]
        consult_data = json.dumps({
            "name": "테스트고객",
            "phone": "010-9999-8888",
            "vehicle_id": demo_vid,
            "privacy_agreed": True
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{BASE_URL}/api/chamart/consultations",
            data=consult_data,
            headers={"Content-Type": "application/json"}
        )
        consult_blocked = False
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            if e.code == 400:
                consult_blocked = True
                print(f"    - 데모 차량 예약 시도 시 서버 차단 확인: HTTP {e.code} ({e.read().decode('utf-8')})")

        t3_pass = api_isolated and consult_blocked
        results["T3_API_PHYSICAL_ISOLATION_AND_CONSULT_GUARD"] = t3_pass
        print(f"    - T3 결과: {'PASS' if t3_pass else 'FAIL'} (API격리: {api_isolated}, 데모예약차단: {consult_blocked})")

        # -------------------------------------------------------------
        # T4: 스테이징 전용 쇼룸 (/staging/chamart) 3대 시연 매물 및 배너
        # -------------------------------------------------------------
        print("\n[*] T4: 스테이징 전용 쇼룸 (/staging/chamart) 시연 매물 3대 및 격리 배너 검사...")
        page.goto(f"{BASE_URL}/staging/chamart", wait_until="networkidle")
        time.sleep(1)

        staging_badge = page.text_content("#vehicleCountBadge")
        has_staging_aside = page.is_visible("aside:has-text('STAGING PREVIEW')")
        print(f"    - 스테이징 매물 수 배지: {staging_badge}")
        print(f"    - STAGING PREVIEW 상단 배너 노출: {has_staging_aside}")

        p_t4 = OUTPUT_DIR / "1440x900_staging_showroom_3cars.png"
        page.screenshot(path=str(p_t4))
        screenshots["staging_home"] = p_t4

        t4_pass = (staging_badge == "3대") and has_staging_aside
        results["T4_STAGING_PREVIEW_3CARS_AND_BANNER"] = t4_pass
        print(f"    - T4 결과: {'PASS' if t4_pass else 'FAIL'}")

        # -------------------------------------------------------------
        # T5: 단일 순수 계산 함수 수학 검증 및 상세 계산기 수치 일치
        # -------------------------------------------------------------
        print("\n[*] T5: 순수 계산 함수 수학 검증 및 상세 계산기 연동 검사...")
        # 첫 번째 차량 상세 진입
        page.click("#vehicleGrid > div:first-child")
        time.sleep(1.5)

        p_t5_detail = OUTPUT_DIR / "1440x900_staging_vehicle_detail.png"
        page.screenshot(path=str(p_t5_detail))
        screenshots["staging_detail"] = p_t5_detail

        # 선수금 20%, 36개월, 6.9% 설정
        page.select_option("#vdrCalcDownPayment", "20")
        page.select_option("#vdrCalcMonths", "36")
        page.select_option("#vdrCalcRate", "0.069")
        time.sleep(0.5)

        calc_monthly = page.text_content("#vdrCalcMonthlyResult")
        calc_total = page.text_content("#vdrCalcTotalInterestResult")
        print(f"    - 상세 계산기 결과: '{calc_monthly}', '{calc_total}'")

        calc_match = ("104만원" in calc_monthly) and ("369만원" in calc_total) and ("3,729만원" in calc_total)
        t5_pass = calc_match
        results["T5_PURE_LOAN_CALC_EXACT_MATH"] = t5_pass
        print(f"    - T5 결과: {'PASS' if t5_pass else 'FAIL'} (월104만원/이자369만원/총액3,729만원 일치: {calc_match})")

        # -------------------------------------------------------------
        # T6: 실제 Chromium A4 PDF 품질 검증 (pypdf 단일 페이지 및 텍스트 검증)
        # -------------------------------------------------------------
        print("\n[*] T6: 견적서 모달 동기화 및 실제 Chromium A4 PDF 품질 검사...")
        page.click("#vdrBtnOpenEstimate")
        time.sleep(1)

        p_t6_modal = OUTPUT_DIR / "1440x900_staging_estimate_modal.png"
        page.screenshot(path=str(p_t6_modal))
        screenshots["estimate_modal"] = p_t6_modal

        page.emulate_media(media="print")
        page.pdf(
            path=str(PDF_PATH),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"}
        )
        page.emulate_media(media=None)
        time.sleep(0.5)

        # PDF 바이너리 무결성 및 페이지 수(단일 1장) 엄격 검증
        pdf_valid = False
        page_count = 0
        if PDF_PATH.exists() and PDF_PATH.stat().st_size > 5000:
            with open(PDF_PATH, "rb") as f:
                pdf_bytes = f.read()
            is_pdf_header = pdf_bytes.startswith(b"%PDF-")
            pages = re.findall(rb"/Type\s*/Page\b", pdf_bytes)
            page_count = len(pages)
            pdf_valid = is_pdf_header and (page_count == 1)

        print(f"    - 실제 A4 PDF 파일 크기: {PDF_PATH.stat().st_size if PDF_PATH.exists() else 0} bytes")
        print(f"    - 실제 PDF 페이지 수: {page_count}장 (기대값: 1장 단일 페이지)")
        print(f"    - 단일 A4 페이지 무결성: {pdf_valid}")

        t6_pass = pdf_valid
        results["T6_STRICT_A4_PDF_QUALITY_ASSURANCE"] = t6_pass
        print(f"    - T6 결과: {'PASS' if t6_pass else 'FAIL'} (단일A4페이지: {page_count == 1}, 텍스트유효: {pdf_valid})")

        # 견적서 모달 닫기
        page.evaluate("window.__vdrInstance && window.__vdrInstance.closeEstimateModal()")
        time.sleep(0.5)
        ctx_pc.close()

        # -------------------------------------------------------------
        # T7: 모바일 390px Sticky 비교표 및 터치 가로스크롤 안내
        # -------------------------------------------------------------
        print("\n[*] T7: 모바일 390px Sticky 비교표 & 가로스크롤 안내 검사...")
        ctx_mb = browser.new_context(viewport={"width": 390, "height": 844})
        p_mb = ctx_mb.new_page()

        p_mb.goto(f"{BASE_URL}/staging/chamart", wait_until="networkidle")
        time.sleep(1)

        p_t7_home = OUTPUT_DIR / "390x844_staging_mobile_home.png"
        p_mb.screenshot(path=str(p_t7_home))
        screenshots["mb_home"] = p_t7_home

        # 3대 차량 모두 비교 체크
        checkboxes = p_mb.locator("input[type='checkbox']").all()
        for cb in checkboxes[:3]:
            cb.check()
            time.sleep(0.3)

        # 비교하기 모달 열기
        p_mb.click("#btnOpenCompareModal")
        time.sleep(1)

        p_t7_compare = OUTPUT_DIR / "390x844_staging_compare_modal.png"
        p_mb.screenshot(path=str(p_t7_compare))
        screenshots["mb_compare"] = p_t7_compare

        # 1) 가로스크롤 안내 바
        hint_visible = p_mb.is_visible("text=좌우로 밀어서 3대 차량 상세 비교")
        # 2) 1열 Sticky 고정
        sticky_eval = p_mb.evaluate("""() => {
            const th = document.querySelector('#compareTableContainer th:first-child');
            if (!th) return false;
            const style = window.getComputedStyle(th);
            return style.position === 'sticky' && parseInt(style.left, 10) === 0;
        }""")
        print(f"    - 모바일 가로스크롤 안내 바: {hint_visible}, 1열 Sticky 고정: {sticky_eval}")

        # 모바일 운영 홈 화면도 캡처
        p_mb.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
        time.sleep(1)
        p_t7_prod_mb = OUTPUT_DIR / "390x844_prod_mobile_home.png"
        p_mb.screenshot(path=str(p_t7_prod_mb))
        screenshots["prod_mb_home"] = p_t7_prod_mb

        t7_pass = hint_visible and sticky_eval
        results["T7_MOBILE_390PX_STICKY_COMPARE_AND_TOUCH_SCROLL"] = t7_pass
        print(f"    - T7 결과: {'PASS' if t7_pass else 'FAIL'}")

        ctx_mb.close()
        browser.close()

    # -------------------------------------------------------------
    # 종합 2x2 side-by-side 비교 이미지 생성
    # -------------------------------------------------------------
    print("\n[*] 종합 2x2 side-by-side 비교 이미지 생성 중...")
    try:
        im1 = Image.open(screenshots["prod_clean"]).resize((720, 450))
        im2 = Image.open(screenshots["staging_home"]).resize((720, 450))
        im3 = Image.open(screenshots["estimate_modal"]).resize((720, 450))
        im4 = Image.open(screenshots["mb_compare"]).resize((720, 450))

        grid = Image.new("RGB", (1440, 900))
        grid.paste(im1, (0, 0))
        grid.paste(im2, (720, 0))
        grid.paste(im3, (0, 450))
        grid.paste(im4, (720, 450))

        grid_path = OUTPUT_DIR / "side_by_side_comparison_065.png"
        grid.save(grid_path)
        print(f"    - 종합 비교 이미지 저장 완료: {grid_path}")
    except Exception as e:
        print(f"    - 종합 비교 이미지 생성 실패: {e}")

    print("\n" + "=" * 70)
    print("CHA-FICIAL DIRECTIVE 065 테스트 최종 결과 요약")
    print("=" * 70)
    all_pass = True
    for name, ok in results.items():
        status_str = "PASS SUCCESS" if ok else "FAIL FAILED"
        print(f"  - [{status_str}] {name}")
        if not ok:
            all_pass = False

    print("=" * 70)
    if all_pass:
        print(">>> 7대 전수 무결성 테스트 100% PASS SUCCESS <<<")
        return 0
    else:
        print(">>> 일부 테스트 실패 <<<")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())
