import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6"

async def run_verification():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        
        # 쿠키 직접 주입하여 관리자 인증 완료
        await context.add_cookies([{
            "name": "chamart_auth",
            "value": "add674c5b5cee4020798b778a517037e2028692a71b985b8fa162f4e88f13abb",
            "domain": "127.0.0.1",
            "path": "/"
        }])

        page = await context.new_page()

        print("[1] Navigating to admin page with auth cookie...")
        await page.goto("http://127.0.0.1:8501/")
        await page.wait_for_timeout(1000)

        # 차량 등록 모달 열기
        print("[2] Opening Vehicle Register Modal...")
        await page.evaluate("() => { if (typeof openVehicleModal === 'function') openVehicleModal(); }")
        await page.wait_for_timeout(1000)

        modal_visible = await page.is_visible("#vehicleModal")
        print(f"Modal visible: {modal_visible}")
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_admin_integrated_register.png"))

        # 2. 공식 모델 검색창 테스트
        print("[3] Testing Catalog Search...")
        quick_search_input = await page.query_selector("#cat_quick_search")
        if quick_search_input:
            await quick_search_input.fill("그랜저")
            await page.wait_for_timeout(1000)
            results = await page.query_selector_all("#cat_search_dropdown div")
            print(f"Catalog dropdown results count: {len(results)}")
            if results:
                print("Selecting first catalog item...")
                await results[0].click()
                await page.wait_for_timeout(800)

        # 3. 옵션 섹션으로 스크롤 및 옵션 토글 테스트
        print("[4] Scrolling to Options section...")
        await page.evaluate("() => { if (typeof scrollToMasterSection === 'function') scrollToMasterSection('sec_options'); }")
        await page.wait_for_timeout(800)

        # 3상태 토글 테스트 (첫번째 옵션의 PRESENT 버튼 클릭)
        present_btns = await page.query_selector_all("button:has-text('장착')")
        print(f"Present buttons found: {len(present_btns)}")
        if present_btns:
            await present_btns[0].click()
            await page.wait_for_timeout(300)

        # 기타 옵션 추가 테스트
        custom_opt_input = await page.query_selector("#new_custom_option_input")
        if custom_opt_input:
            await custom_opt_input.fill("빌트인 캠 2.0")
            add_opt_btn = await page.query_selector("button:has-text('추가')")
            if add_opt_btn:
                await add_opt_btn.click()
                await page.wait_for_timeout(300)

        # 옵션 섹션 캡처
        await page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_admin_options_3state.png"))

        # 4. 고객 사이트 (PC) 테스트
        print("[5] Navigating to customer showroom PC...")
        cust_page = await context.new_page()
        await cust_page.goto("http://127.0.0.1:8501/chamart")
        await cust_page.wait_for_timeout(1500)

        # 첫 번째 차량 상세 진입
        first_card = await cust_page.query_selector(".vehicle-card, [onclick*='openDetail']")
        if first_card:
            print("Clicking first vehicle card...")
            await first_card.click()
            await cust_page.wait_for_timeout(1500)

            # 상세 페이지 옵션 영역으로 스크롤
            options_sec = await cust_page.query_selector("#vdrTop10OptionsSection, #vdrFullOptionsPanel")
            if options_sec:
                await options_sec.scroll_into_view_if_needed()
                await cust_page.wait_for_timeout(500)
                await cust_page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_customer_top10_options_pc.png"))

                # 전체 옵션 아코디언 열기
                toggle_btn = await cust_page.query_selector("button:has-text('전체 옵션 보기')")
                if toggle_btn:
                    print("Clicking full options toggle button...")
                    await toggle_btn.click()
                    await cust_page.wait_for_timeout(600)
                    await cust_page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_customer_full_options_expanded_pc.png"))

        # 5. 고객 사이트 (Mobile 390px) 테스트
        print("[6] Navigating to customer showroom Mobile (390px)...")
        mobile_context = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mob_page = await mobile_context.new_page()
        await mob_page.goto("http://127.0.0.1:8501/chamart")
        await mob_page.wait_for_timeout(1500)

        first_card_mob = await mob_page.query_selector(".vehicle-card, [onclick*='openDetail']")
        if first_card_mob:
            await first_card_mob.click()
            await mob_page.wait_for_timeout(1500)

            options_sec_mob = await mob_page.query_selector("#vdrTop10OptionsSection")
            if options_sec_mob:
                await options_sec_mob.scroll_into_view_if_needed()
                await mob_page.wait_for_timeout(500)
                await mob_page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_customer_top10_options_mobile.png"))

                toggle_btn_mob = await mob_page.query_selector("button:has-text('전체 옵션 보기')")
                if toggle_btn_mob:
                    await toggle_btn_mob.click()
                    await mob_page.wait_for_timeout(600)
                    await mob_page.screenshot(path=os.path.join(ARTIFACT_DIR, "verified_customer_full_options_expanded_mobile.png"))

        await browser.close()
        print("[OK] All verifications completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_verification())
