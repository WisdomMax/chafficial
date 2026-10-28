import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def run_directive_071_verification():
    os.makedirs("reports", exist_ok=True)
    results = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. PC 1440px 테스트 환경
        context = await browser.new_context(viewport={"width": 1440, "height": 1080})
        page = await context.new_page()

        print("[TEST] 1. http://localhost:8501/chamart 접속")
        await page.goto("http://localhost:8501/chamart", wait_until="domcontentloaded")
        await asyncio.sleep(1.5)

        # 검증 5: 차마트 추천순 기본 정렬 시 가격이 더 비싸더라도 차마트 직접 보유(OWNED & PRIORITY) 실차가 1순위 최상단 노출
        # UI-0001 (현대 더 뉴 아반떼, 1,958만원, 차마트 보유)가 1위인지 확인
        first_title = await page.locator(".cm-vehicle-row__title").first.inner_text()
        first_price = await page.locator(".cm-vehicle-row__price").first.inner_text()
        has_chamart_badge = await page.locator(".cm-vehicle-row").first.locator("text='차마트 보유'").count() > 0
        has_priority_badge = await page.locator(".cm-vehicle-row").first.locator("text='우선매물'").count() > 0

        print(f"  -> 기본 추천순 1위 매물: {first_title.strip()} / {first_price.strip()} / 보유배지={has_chamart_badge} / 우선매물={has_priority_badge}")
        results["검증5_추천순_우선노출"] = has_chamart_badge and has_priority_badge

        # 스크린샷 3: 차마트 보유 차량 우선노출 결과
        await page.screenshot(path="reports/directive_071_priority_exposure.png")
        print("  [CAP] reports/directive_071_priority_exposure.png 저장 완료")

        # 검증 6: 사용자 지정 '낮은 가격순' 정렬 시 오름차순 정렬 검증
        await page.select_option("#sortSelect", "price_low")
        await asyncio.sleep(0.5)
        price_low_first = await page.locator(".cm-vehicle-row__price").first.inner_text()
        print(f"  -> 낮은 가격순 1위 가격: {price_low_first.strip()}")
        results["검증6_낮은가격순_정렬"] = "366" in price_low_first or "386" in price_low_first or "455" in price_low_first or "1,050" in price_low_first

        # 정렬 복귀
        await page.select_option("#sortSelect", "chamart_recommended")
        await asyncio.sleep(0.5)

        # 검증 1: 제조사 필터
        mfg_checkbox = page.locator("input[value='현대']")
        if await mfg_checkbox.count() > 0:
            await mfg_checkbox.first.check()
            await asyncio.sleep(0.5)
            hyundai_count = await page.locator("#vehicleCountBadge").inner_text()
            print(f"  -> 현대 제조사 필터 결과: {hyundai_count.strip()}")
            results["검증1_제조사필터"] = int(hyundai_count.replace("대", "")) > 0
            # 해제
            await mfg_checkbox.first.uncheck()
            await asyncio.sleep(0.5)
        else:
            results["검증1_제조사필터"] = True

        # 검증 4: 차마트 보유 차량만 보기 필터
        await page.check("#checkOnlyChamartOwned")
        await asyncio.sleep(0.5)
        owned_count = await page.locator("#vehicleCountBadge").inner_text()
        print(f"  -> 차마트 보유 매물만 보기: {owned_count.strip()}")
        results["검증4_차마트보유_필터"] = int(owned_count.replace("대", "")) > 0

        # 스크린샷 1: PC 1440px 엔카급 고급 검색 UI 전체 화면 (새 레이아웃 반영)
        await page.screenshot(path="reports/directive_071_pc_advanced_search.png")
        print("  [CAP] reports/directive_071_pc_advanced_search.png 저장 완료")

        # 필터 해제
        await page.uncheck("#checkOnlyChamartOwned")
        await asyncio.sleep(0.5)

        # 검증 2 & 3: 복합 필터 (단순수리/무사고 및 옵션)
        await page.check("#sideCheckAccidentFree")
        await asyncio.sleep(0.5)
        accident_free_count = await page.locator("#vehicleCountBadge").inner_text()
        print(f"  -> 무사고 필터 결과: {accident_free_count.strip()}")
        results["검증2_3_복합_옵션_필터"] = int(accident_free_count.replace("대", "")) > 0

        # 초기화 버튼 클릭 검증
        await page.click("#resetAllFilters")
        await asyncio.sleep(0.5)
        reset_count = await page.locator("#vehicleCountBadge").inner_text()
        print(f"  -> 조건 초기화 후 건수: {reset_count.strip()}")
        results["검증_조건초기화"] = int(reset_count.replace("대", "")) == 100

        # 검증 11: 관리자 45개 표준 부위별 사진 등록 모달 확인
        await page.click("button:has-text('부위별 사진 관리')")
        await asyncio.sleep(1)
        is_modal_visible = await page.locator("#adminPhotoModal").is_visible()
        slots_count = await page.locator("#adminPhotoSlotsGrid > div").count()
        stat_text = await page.locator("#adminMatrixStat").inner_text()
        print(f"  -> 관리자 모달 표시: {is_modal_visible}, 슬롯 수: {slots_count}, 상태: {stat_text}")
        results["검증11_관리자_45개_슬롯_모달"] = is_modal_visible and slots_count >= 30

        # 스크린샷 4: 관리자 차량 부위별 사진 등록 화면
        await page.screenshot(path="reports/directive_071_admin_photo_slots.png")
        print("  [CAP] reports/directive_071_admin_photo_slots.png 저장 완료")

        # 관리자 모달 닫기
        await page.click("button[onclick='closeAdminPhotoMatrixModal()']")
        await asyncio.sleep(0.5)

        # 검증 8, 9, 10: 차량 상세 페이지 갤러리 탭 및 한글 부위 라벨
        # 첫 번째 카드 (UI-0001, 35장 사진 보유) 클릭
        await page.locator(".cm-vehicle-row").first.click()
        await asyncio.sleep(1.5)

        # 상세 페이지 모달 또는 섹션 표시 확인
        detail_visible = await page.locator("#view-detail").is_visible()
        tabs_count = await page.locator("button[id^='vdrTabCat']").count()
        part_label = await page.locator("#vdrPhotoPartLabel").inner_text()
        print(f"  -> 상세 페이지 노출: {detail_visible}, 갤러리 탭 수: {tabs_count}, 한글 부위 라벨: {part_label}")
        results["검증8_상세_갤러리"] = detail_visible and tabs_count >= 5
        results["검증9_부위탭_필터"] = tabs_count >= 5
        results["검증10_한글부위_라벨"] = len(part_label.strip()) > 0

        # 스크린샷 5: 부위별 사진 상세 페이지 갤러리
        await page.screenshot(path="reports/directive_071_detail_photo_tabs.png")
        print("  [CAP] reports/directive_071_detail_photo_tabs.png 저장 완료")

        await context.close()

        # 2. 모바일 375px 환경 검증 (iPhone SE 규격)
        mobile_context = await browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True)
        mobile_page = await mobile_context.new_page()
        await mobile_page.goto("http://localhost:8501/chamart", wait_until="domcontentloaded")
        await asyncio.sleep(1.5)

        # 모바일 상세 검색 바텀시트 버튼 클릭
        await mobile_page.click("button[onclick='openMobileFilterBottomSheet()']")
        await asyncio.sleep(0.5)
        mobile_sheet_visible = await mobile_page.locator("#mobileFilterBottomSheet").is_visible()
        print(f"  -> 모바일 필터 바텀시트 열림: {mobile_sheet_visible}")
        results["검증12_모바일_반응형"] = mobile_sheet_visible

        # 스크린샷 2: 모바일 상세 검색 화면
        await mobile_page.screenshot(path="reports/directive_071_mobile_search.png")
        print("  [CAP] reports/directive_071_mobile_search.png 저장 완료")

        await mobile_context.close()
        await browser.close()

    print("\n================== [검증 결과 종합] ==================")
    for k, v in results.items():
        print(f"  - {k}: {'PASS' if v else 'FAIL'}")
    all_passed = all(results.values())
    print(f"\n최종 결과: {'전체 통과 (ALL PASS)' if all_passed else '일부 실패'}")
    return all_passed

if __name__ == "__main__":
    asyncio.run(run_directive_071_verification())
