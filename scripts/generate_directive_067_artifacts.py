#!/usr/bin/env python3
"""DIRECTIVE 067 산출물 생성 및 종합 검증 스크립트.

- 표준 및 긴 차명 견적서 실제 Chromium A4 단일 1페이지 PDF 생성
- macOS sips 1:1 고해상도 전체 페이지 렌더 PNG 생성
- 360px~1440px 반응형 시각 검수 스크린샷 5종 및 종합 대시보드 생성
- 모든 산출물을 reports/directive_067/ 디렉토리에 정돈 보관
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "reports" / "directive_067"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_all_artifacts():
    print("=======================================================")
    print("  DIRECTIVE 067 산출물 생성 및 시각 검증 시작")
    print("=======================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 1. 표준 견적서 생성 (PDF + sips PNG)
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:8501/staging/chamart", wait_until="networkidle")
        time.sleep(1)

        # 첫 번째 시연 차량 상세 열기
        page.evaluate("openVehicleDetail(publicVehicles[0].id)")
        page.wait_for_selector("#vdrEstimatePrintModal", state="attached", timeout=5000)
        page.evaluate("window.__vdrInstance.openEstimateModal()")
        time.sleep(0.5)

        # Print 에뮬레이션 및 표준 PDF 생성
        page.emulate_media(media="print")
        pdf_bytes_std = page.pdf(prefer_css_page_size=True)
        pdf_path_std = OUTPUT_DIR / "estimate_standard.pdf"
        with open(pdf_path_std, "wb") as f:
            f.write(pdf_bytes_std)

        pages_count_std = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes_std))
        print(f"[*] 표준 견적서 PDF 생성: {len(pdf_bytes_std):,} 바이트, 페이지 수: {pages_count_std}")
        assert pages_count_std == 1, f"표준 견적서 페이지 수 오류: {pages_count_std}"

        png_path_std = OUTPUT_DIR / "estimate_standard_page1.png"
        subprocess.run(["sips", "-s", "format", "png", str(pdf_path_std), "--out", str(png_path_std)], check=True)
        print(f"[*] 표준 견적서 sips 고해상도 렌더 완료: {png_path_std.name}")

        page.emulate_media(media="screen")
        page.evaluate("window.__vdrInstance.closeEstimateModal()")

        # 2. 긴 차명 견적서 생성 (PDF + sips PNG)
        page.evaluate("openVehicleDetail(publicVehicles[0].id)")
        page.wait_for_selector("#vdrEstimatePrintModal", state="attached", timeout=5000)
        long_title = "더 뉴 제네시스 G80 3.5T 가솔린 AWD 스포츠 패키지 캘리그래피 풀옵션 (다이나믹 패키지 III 탑재)"
        page.evaluate(f"""
            const titleEl = document.querySelector('#vdrPrintableEstimateSheet h2');
            if (titleEl) titleEl.textContent = {json.dumps(long_title)};
        """)
        page.evaluate("window.__vdrInstance.openEstimateModal()")
        time.sleep(0.5)

        page.emulate_media(media="print")
        pdf_bytes_long = page.pdf(prefer_css_page_size=True)
        pdf_path_long = OUTPUT_DIR / "estimate_long_title.pdf"
        with open(pdf_path_long, "wb") as f:
            f.write(pdf_bytes_long)

        pages_count_long = len(re.findall(rb"/Type\s*/Page\b", pdf_bytes_long))
        print(f"[*] 긴 차명 견적서 PDF 생성: {len(pdf_bytes_long):,} 바이트, 페이지 수: {pages_count_long}")
        assert pages_count_long == 1, f"긴 차명 견적서 페이지 수 오류: {pages_count_long}"

        png_path_long = OUTPUT_DIR / "estimate_long_title_page1.png"
        subprocess.run(["sips", "-s", "format", "png", str(pdf_path_long), "--out", str(png_path_long)], check=True)
        print(f"[*] 긴 차명 견적서 sips 고해상도 렌더 완료: {png_path_long.name}")

        page.emulate_media(media="screen")
        page.evaluate("window.__vdrInstance.closeEstimateModal()")

        # 3. 반응형 시각 검수 스크린샷 5종
        viewports = [
            ("360x800_prod_mobile_small", 360, 800, "http://127.0.0.1:8501/chamart", False),
            ("390x844_prod_mobile_standard", 390, 844, "http://127.0.0.1:8501/chamart", False),
            ("768x1024_staging_tablet", 768, 1024, "http://127.0.0.1:8501/staging/chamart", False),
            ("1440x900_staging_desktop", 1440, 900, "http://127.0.0.1:8501/staging/chamart", False),
            ("390x844_staging_compare_modal", 390, 844, "http://127.0.0.1:8501/staging/chamart", True),
        ]

        for name, w, h, url, open_compare in viewports:
            page.set_viewport_size({"width": w, "height": h})
            page.goto(url, wait_until="networkidle")
            time.sleep(1)

            if open_compare:
                page.wait_for_function("() => Boolean(window.publicVehicles && window.publicVehicles.length >= 3)")
                page.evaluate("""
                    window.compareVehicleIds = publicVehicles.map(v => v.id);
                    updateCompareFloatingBar();
                    openCompareModal();
                """)
                time.sleep(1)
                hint = page.locator("#compareScrollHintBar")
                assert hint.is_visible(), "모바일 가로스크롤 안내 바 미노출"

            shot_file = OUTPUT_DIR / f"{name}.png"
            page.screenshot(path=str(shot_file))
            print(f"[*] 화면 캡처 완료: {shot_file.name}")

        # 4. 종합 4분할 비교 대시보드 생성
        create_side_by_side_dashboard_067()

        browser.close()

    print("\n=======================================================")
    print("  DIRECTIVE 067 산출물 생성 및 시각 검증 ALL SUCCESS!")
    print("=======================================================")
    return 0

def create_side_by_side_dashboard_067():
    try:
        from PIL import Image
        img_prod = Image.open(OUTPUT_DIR / "390x844_prod_mobile_standard.png")
        img_staging = Image.open(OUTPUT_DIR / "1440x900_staging_desktop.png")
        img_compare = Image.open(OUTPUT_DIR / "390x844_staging_compare_modal.png")
        img_pdf = Image.open(OUTPUT_DIR / "estimate_standard_page1.png")

        target_w, target_h = 720, 450

        # 데스크톱 리사이즈
        cell_desktop = img_staging.resize((target_w, target_h), Image.Resampling.LANCZOS)

        # 모바일 표준 비율 맞춤
        m_ratio = img_prod.width / img_prod.height
        m_w = int(target_h * m_ratio)
        cell_prod = Image.new("RGB", (target_w, target_h), (245, 246, 244))
        cell_prod.paste(img_prod.resize((m_w, target_h), Image.Resampling.LANCZOS), ((target_w - m_w)//2, 0))

        # 모바일 비교표 비율 맞춤
        c_ratio = img_compare.width / img_compare.height
        c_w = int(target_h * c_ratio)
        cell_compare = Image.new("RGB", (target_w, target_h), (245, 246, 244))
        cell_compare.paste(img_compare.resize((c_w, target_h), Image.Resampling.LANCZOS), ((target_w - c_w)//2, 0))

        # PDF 렌더 비율 맞춤
        p_ratio = img_pdf.width / img_pdf.height
        p_w = int(target_h * p_ratio)
        cell_pdf = Image.new("RGB", (target_w, target_h), (245, 246, 244))
        cell_pdf.paste(img_pdf.resize((p_w, target_h), Image.Resampling.LANCZOS), ((target_w - p_w)//2, 0))

        dash = Image.new("RGB", (target_w * 2, target_h * 2), (255, 255, 255))
        dash.paste(cell_prod, (0, 0))
        dash.paste(cell_desktop, (target_w, 0))
        dash.paste(cell_compare, (0, target_h))
        dash.paste(cell_pdf, (target_w, target_h))

        dash_path = OUTPUT_DIR / "side_by_side_comparison_067.png"
        dash.save(dash_path)
        print(f"[*] 종합 4분할 대시보드 저장 완료: {dash_path.name}")
    except Exception as e:
        print(f"[!] 대시보드 생성 스킵 (PIL: {e})")

if __name__ == "__main__":
    sys.exit(generate_all_artifacts())
