import asyncio
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # 1. Mobile 390x844 (iPhone 12/13/14)
        print("--- [1] Testing Mobile 390px ---")
        context_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page_m = await context_mobile.new_page()
        
        await page_m.goto("https://chamart.cc", wait_until="networkidle")
        await page_m.wait_for_timeout(1000)

        # 배너 캡처
        await page_m.screenshot(
            path="/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/verified_prod_mobile_banner.png"
        )
        print("Captured verified_prod_mobile_banner.png")

        # 햄버거 메뉴 열기
        drawer_btn = page_m.locator("#mobileMenuOpenBtn")
        if await drawer_btn.is_visible():
            await drawer_btn.click()
            await page_m.wait_for_timeout(600)
            await page_m.screenshot(
                path="/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/verified_prod_mobile_drawer.png"
            )
            print("Captured verified_prod_mobile_drawer.png")
            # 드로어 닫기
            await page_m.evaluate("toggleMobileNavDrawer(false)")
            await page_m.wait_for_timeout(400)

        # 차량 카드 확인 및 캡처
        await page_m.wait_for_selector(".cm-album-card", timeout=10000)
        first_card = page_m.locator(".cm-album-card").first
        await first_card.scroll_into_view_if_needed()
        await page_m.wait_for_timeout(500)
        await page_m.screenshot(
            path="/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/verified_prod_mobile_cards.png"
        )
        print("Captured verified_prod_mobile_cards.png")

        # 첫 번째 차량 상세 진입
        print("Clicking first vehicle card...")
        await first_card.click()
        await page_m.wait_for_selector("#vdrGalleryViewport", timeout=10000)
        await page_m.wait_for_timeout(1000)

        await page_m.screenshot(
            path="/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/verified_prod_mobile_detail_top.png"
        )
        print("Captured verified_prod_mobile_detail_top.png")

        # 세로 스크롤 모달 오픈
        print("Opening vertical photo feed modal...")
        await page_m.click("#vdrGalleryViewport")
        await page_m.wait_for_selector("#vdrVerticalFeedModal:not(.hidden)", timeout=5000)
        await page_m.wait_for_timeout(800)

        await page_m.screenshot(
            path="/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/verified_prod_mobile_vertical_feed_top.png"
        )
        print("Captured verified_prod_mobile_vertical_feed_top.png")

        # 아래로 슥슥 스크롤
        await page_m.evaluate("document.getElementById('vdrVerticalFeedScrollContainer').scrollTop = 1600")
        await page_m.wait_for_timeout(800)
        await page_m.screenshot(
            path="/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/verified_prod_mobile_vertical_feed_scrolled.png"
        )
        print("Captured verified_prod_mobile_vertical_feed_scrolled.png")

        await context_mobile.close()

        # 2. PC 1920x1080
        print("\n--- [2] Testing PC 1920px ---")
        context_pc = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page_pc = await context_pc.new_page()
        await page_pc.goto("https://chamart.cc", wait_until="networkidle")
        await page_pc.wait_for_timeout(1000)

        # PC 홈 화면 캡처 (검은색 플레이스홀더 완전 퇴출 확인)
        await page_pc.wait_for_selector(".cm-album-card", timeout=10000)
        await page_pc.screenshot(
            path="/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/verified_prod_pc_cards.png"
        )
        print("Captured verified_prod_pc_cards.png")

        # PC 상세 진입
        first_card_pc = page_pc.locator(".cm-album-card").first
        await first_card_pc.click()
        await page_pc.wait_for_selector("#vdrGalleryViewport", timeout=10000)
        await page_pc.wait_for_timeout(1000)

        await page_pc.screenshot(
            path="/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/verified_prod_pc_detail.png"
        )
        print("Captured verified_prod_pc_detail.png")

        # PC 세로 스크롤 모달 오픈
        await page_pc.click("#vdrGalleryViewport")
        await page_pc.wait_for_selector("#vdrVerticalFeedModal:not(.hidden)", timeout=5000)
        await page_pc.wait_for_timeout(800)

        await page_pc.screenshot(
            path="/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/verified_prod_pc_vertical_feed.png"
        )
        print("Captured verified_prod_pc_vertical_feed.png")

        await context_pc.close()
        await browser.close()
        print("\nAll verifications completed successfully!")

asyncio.run(verify())
