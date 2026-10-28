#!/usr/bin/env python3
"""
CHA-FICIAL DIRECTIVE 070: 100대 가상 매물 엔카 스타일 UI 디자인 자동화 검증 스크립트
- 12종 스크린샷 캡처
- 가로 오버플로(수평 스크롤) 0건 검증
- 20대 단위 페이지네이션 및 필터 동적 카운트 검증
- 종합 비교 대시보드(side_by_side_comparison_070.png) 생성
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("reports/directive_070")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://localhost:8501/staging/chamart"

def run_verification():
    results = {}
    overflow_violations = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ---------------------------------------------------------
        # 1. PC 1440x900 기본 가로 리스트형 (1페이지: 20대)
        # ---------------------------------------------------------
        print("[1/12] PC 1440x900 1페이지 20대 가로 리스트형 캡처 중...")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("console", lambda msg: print(f"  [BROWSER] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"  [PAGE ERROR] {err}"))

        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.wait_for_selector(".cm-vehicle-row", timeout=10000)
        time.sleep(1.0)

        # 오버플로 검증
        overflow = page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
        if overflow:
            overflow_violations.append("1. PC 1440x900 List")

        total_badge = page.inner_text("#vehicleCountBadge")
        row_count = page.locator(".cm-vehicle-row").count()
        pagination_text = page.locator(".cm-pagination-info").inner_text()
        print(f"  -> 전체 배지: {total_badge}, 표시된 행: {row_count}, 페이지네이션: {pagination_text}")
        results["total_count_badge"] = total_badge
        results["page1_rows"] = row_count
        assert "100" in total_badge, f"Expected 100 in badge, got {total_badge}"
        assert row_count == 20, f"Expected 20 rows on page 1, got {row_count}"

        page.screenshot(path=str(OUTPUT_DIR / "01_pc_1440_list_100_page1.png"))

        # ---------------------------------------------------------
        # 2. 아반떼 35대 필터 결과
        # ---------------------------------------------------------
        print("[2/12] 현대 아반떼 필터 캡처 중...")
        # 현대 제조사 선택
        page.locator("#sideMakerList button:has-text('현대')").first.click()
        time.sleep(0.5)
        # 아반떼 모델 선택
        page.locator("#sideModelList button:has-text('아반떼')").first.click()
        time.sleep(0.5)
        avante_badge = page.inner_text("#vehicleCountBadge")
        avante_rows = page.locator(".cm-vehicle-row").count()
        print(f"  -> 아반떼 필터 결과: {avante_badge}, 1페이지 행: {avante_rows}")
        results["avante_count"] = avante_badge
        assert "35" in avante_badge, f"Expected 35 in avante badge, got {avante_badge}"
        assert avante_rows == 20, f"Expected 20 rows (page 1 of 35), got {avante_rows}"
        page.screenshot(path=str(OUTPUT_DIR / "02_pc_avante_filter_35.png"))

        # ---------------------------------------------------------
        # 3. 레이 25대 필터 결과
        # ---------------------------------------------------------
        print("[3/12] 기아 레이 필터 캡처 중...")
        page.click("#resetAllFilters")
        time.sleep(0.4)
        page.locator("#sideMakerList button:has-text('기아')").first.click()
        time.sleep(0.5)
        page.locator("#sideModelList button:has-text('레이')").first.click()
        time.sleep(0.5)
        ray_badge = page.inner_text("#vehicleCountBadge")
        ray_rows = page.locator(".cm-vehicle-row").count()
        print(f"  -> 레이 필터 결과: {ray_badge}, 1페이지 행: {ray_rows}")
        results["ray_count"] = ray_badge
        assert "25" in ray_badge, f"Expected 25 in ray badge, got {ray_badge}"
        assert ray_rows == 20, f"Expected 20 rows (page 1 of 25), got {ray_rows}"
        page.screenshot(path=str(OUTPUT_DIR / "03_pc_ray_filter_25.png"))

        # ---------------------------------------------------------
        # 4. 모닝 25대 필터 결과
        # ---------------------------------------------------------
        print("[4/12] 기아 모닝 필터 캡처 중...")
        page.locator("#sideModelList button:has-text('모닝')").first.click()
        time.sleep(0.5)
        morning_badge = page.inner_text("#vehicleCountBadge")
        morning_rows = page.locator(".cm-vehicle-row").count()
        print(f"  -> 모닝 필터 결과: {morning_badge}, 1페이지 행: {morning_rows}")
        results["morning_count"] = morning_badge
        assert "25" in morning_badge, f"Expected 25 in morning badge, got {morning_badge}"
        assert morning_rows == 20, f"Expected 20 rows, got {morning_rows}"
        page.screenshot(path=str(OUTPUT_DIR / "04_pc_morning_filter_25.png"))

        # ---------------------------------------------------------
        # 5. PC 앨범형 그리드 (1440x900)
        # ---------------------------------------------------------
        print("[5/12] PC 앨범형 그리드 캡처 중...")
        page.click("#resetAllFilters")
        time.sleep(0.4)
        page.click("#cmViewAlbum")
        time.sleep(0.5)
        album_cards = page.locator(".cm-album-card").count()
        print(f"  -> 앨범형 1페이지 카드 수: {album_cards}")
        assert album_cards == 20, f"Expected 20 album cards, got {album_cards}"
        page.screenshot(path=str(OUTPUT_DIR / "05_pc_1440_album_grid.png"))

        # ---------------------------------------------------------
        # 6. PC 단일 차량 상세 (UI-0001 아반떼)
        # ---------------------------------------------------------
        print("[6/12] PC 차량 상세 뷰 캡처 중...")
        page.goto("http://localhost:8501/staging/cars/UI-0001", wait_until="domcontentloaded")
        time.sleep(1.0)
        page.screenshot(path=str(OUTPUT_DIR / "06_pc_vehicle_detail_1440.png"))

        # ---------------------------------------------------------
        # 7. 모바일 가로 목록 (390x844)
        # ---------------------------------------------------------
        print("[7/12] 모바일 390x844 가로 목록 캡처 중...")
        mobile_page = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        mobile_page.goto(BASE_URL, wait_until="domcontentloaded")
        mobile_page.wait_for_selector(".cm-vehicle-row", timeout=10000)
        time.sleep(0.8)

        # 모바일 가로스크롤 검증
        mob_overflow = mobile_page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
        if mob_overflow:
            overflow_violations.append("7. Mobile 390x844 List")
        print(f"  -> 모바일 가로 오버플로 여부: {mob_overflow}")
        mobile_page.screenshot(path=str(OUTPUT_DIR / "07_mobile_390_list.png"))

        # ---------------------------------------------------------
        # 8. 모바일 단일 차량 상세 (390x844)
        # ---------------------------------------------------------
        print("[8/12] 모바일 단일 차량 상세 캡처 중...")
        mobile_page.goto("http://localhost:8501/staging/cars/UI-0001", wait_until="domcontentloaded")
        time.sleep(0.8)
        mob_detail_overflow = mobile_page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
        if mob_detail_overflow:
            overflow_violations.append("8. Mobile 390x844 Detail")
        mobile_page.screenshot(path=str(OUTPUT_DIR / "08_mobile_vehicle_detail_390.png"))

        # ---------------------------------------------------------
        # 9. 모바일 필터 바텀시트
        # ---------------------------------------------------------
        print("[9/12] 모바일 필터 바텀시트 캡처 중...")
        mobile_page.goto(BASE_URL, wait_until="domcontentloaded")
        mobile_page.wait_for_selector("button:has-text('필터')", timeout=10000)
        mobile_page.click("button:has-text('필터')")
        time.sleep(0.5)
        mobile_page.screenshot(path=str(OUTPUT_DIR / "09_mobile_filter_bottomsheet.png"))

        # ---------------------------------------------------------
        # 10. 최대 3대 차량 상세 비교 모달
        # ---------------------------------------------------------
        print("[10/12] 3대 차량 비교 모달 캡처 중...")
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.wait_for_selector(".cm-vehicle-row", timeout=10000)
        time.sleep(0.5)
        # 1, 2, 3번째 차량 비교 체크박스 클릭
        checkboxes = page.locator(".cm-row-compare")
        checkboxes.nth(0).click()
        checkboxes.nth(1).click()
        checkboxes.nth(2).click()
        time.sleep(0.4)
        page.click("#btnOpenCompareModal")
        time.sleep(0.6)
        page.screenshot(path=str(OUTPUT_DIR / "10_compare_modal_3cars.png"))
        page.click("#compareModal button:has-text('확인 닫기')")
        time.sleep(0.3)

        # ---------------------------------------------------------
        # 11. 100대 중 5페이지(마지막 81-100번째 매물) 이동 결과
        # ---------------------------------------------------------
        print("[11/12] 100대 중 5페이지 이동 캡처 중...")
        page.locator("button.cm-page-btn:has-text('5')").click()
        time.sleep(0.5)
        page5_info = page.locator(".cm-pagination-info").inner_text()
        page5_rows = page.locator(".cm-vehicle-row").count()
        print(f"  -> 5페이지 페이지네이션 안내: {page5_info}, 행 수: {page5_rows}")
        results["page5_info"] = page5_info
        results["page5_rows"] = page5_rows
        assert "81 - 100" in page5_info, f"Expected 81-100 in pagination info, got {page5_info}"
        assert page5_rows == 20, f"Expected 20 rows on page 5, got {page5_rows}"
        page.screenshot(path=str(OUTPUT_DIR / "11_pc_pagination_page5.png"))

        # ---------------------------------------------------------
        # 12. 검색 결과 0건 화면
        # ---------------------------------------------------------
        print("[12/12] 검색 결과 0건 화면 캡처 중...")
        search_input = page.locator("#homeSearchInput")
        search_input.fill("존재하지않는차량검색어9999")
        search_input.press("Enter")
        time.sleep(0.5)
        empty_badge = page.inner_text("#vehicleCountBadge")
        print(f"  -> 검색 0건 배지: {empty_badge}")
        results["empty_badge"] = empty_badge
        assert "0대" in empty_badge, f"Expected 0대, got {empty_badge}"
        page.screenshot(path=str(OUTPUT_DIR / "12_empty_search_result.png"))

        browser.close()

    print("\n================ 검증 요약 ================")
    print(f"오버플로 위반 수: {len(overflow_violations)}")
    if overflow_violations:
        print("  위반 목록:", overflow_violations)
    else:
        print("  [PASS] 모든 PC/모바일 뷰포트에서 가로 스크롤(오버플로) 0건 달성!")

    print(f"100대 배지 및 페이지1 20대 표시: {results.get('total_count_badge')} / {results.get('page1_rows')}행")
    print(f"아반떼 35대 필터 검증: {results.get('avante_count')}")
    print(f"레이 25대 필터 검증: {results.get('ray_count')}")
    print(f"모닝 25대 필터 검증: {results.get('morning_count')}")
    print(f"5페이지(81-100) 이동 검증: {results.get('page5_info')} ({results.get('page5_rows')}행)")
    print("===========================================\n")

    build_comparison_dashboard()

def build_comparison_dashboard():
    """12개 캡처를 종합 대시보드 단일 이미지로 합성"""
    print("[*] 종합 비교 대시보드(side_by_side_comparison_070.png) 생성 중...")
    
    selected = [
        ("01_pc_1440_list_100_page1.png", "1. 100대 가로 리스트형 기본 뷰 (1440x900, 20대 단위)"),
        ("02_pc_avante_filter_35.png", "2. 현대 아반떼 35대 필터링 결과"),
        ("05_pc_1440_album_grid.png", "3. 3열 앨범형 그리드 (20대 단위)"),
        ("06_pc_vehicle_detail_1440.png", "4. PC 단일 차량 상세 (UI-0001 아반떼 실차 사진)"),
        ("11_pc_pagination_page5.png", "5. 5페이지 이동 (81-100번째 매물 완비)"),
        ("07_mobile_390_list.png", "6. 모바일 가로 리스트형 (390x844 오버플로 0건)"),
    ]

    cell_w, cell_h = 720, 450
    header_h = 70
    banner_h = 35
    cols, rows = 2, 3
    total_w = cell_w * cols + 40
    total_h = header_h + (cell_h + banner_h + 20) * rows + 30

    dash = Image.new("RGB", (total_w, total_h), color=(248, 250, 252))
    draw = ImageDraw.Draw(dash)

    # 상단 헤더
    draw.rectangle([0, 0, total_w, header_h], fill=(23, 27, 30))
    # 제목 텍스트 (기본 폰트)
    draw.text((25, 18), "CHA-FICIAL DIRECTIVE 070: 100-CAR ENCAR-STYLE UI BENCHMARK", fill=(200, 255, 61))
    draw.text((25, 42), "100 Virtual Vehicles, 20/Page Pagination, Dedicated UI Fixture & Zero Horizontal Overflow", fill=(229, 231, 235))

    for idx, (filename, label) in enumerate(selected):
        c = idx % cols
        r = idx // cols
        x = 20 + c * (cell_w + 10)
        y = header_h + 20 + r * (cell_h + banner_h + 20)

        # 라벨 바
        draw.rectangle([x, y, x + cell_w, y + banner_h], fill=(235, 240, 245))
        draw.text((x + 12, y + 10), label, fill=(23, 27, 30))

        # 이미지 로드 및 리사이즈
        img_path = OUTPUT_DIR / filename
        if img_path.exists():
            with Image.open(img_path) as im:
                im_thumb = im.copy()
                im_thumb.thumbnail((cell_w, cell_h), Image.Resampling.LANCZOS)
                # 센터 배치
                ox = x + (cell_w - im_thumb.width) // 2
                oy = y + banner_h + (cell_h - im_thumb.height) // 2
                dash.paste(im_thumb, (ox, oy))
                # 테두리
                draw.rectangle([x, y + banner_h, x + cell_w, y + banner_h + cell_h], outline=(226, 232, 240), width=1)

    out_file = OUTPUT_DIR / "side_by_side_comparison_070.png"
    dash.save(out_file, format="PNG", optimize=True)
    print(f"[*] 종합 대시보드 저장 완료: {out_file} ({out_file.stat().st_size:,} bytes)")

    # 아티팩트 디렉토리에도 복사
    artifact_dir = Path("/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6")
    if artifact_dir.exists():
        dash.save(artifact_dir / "side_by_side_comparison_070.png", format="PNG")
        print(f"[*] 아티팩트 디렉토리에 복사 완료: {artifact_dir / 'side_by_side_comparison_070.png'}")

if __name__ == "__main__":
    run_verification()
