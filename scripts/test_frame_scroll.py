import asyncio
from playwright.async_api import async_playwright

async def test_independent_frame_scroll():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 960})
        page = await context.new_page()

        await page.goto("http://localhost:8501/chamart", wait_until="domcontentloaded")
        await asyncio.sleep(1.5)

        # 초기 상태 캡처
        await page.screenshot(path="reports/chamart_frame_scroll_initial.png")
        print("Captured reports/chamart_frame_scroll_initial.png")

        # 우측 독립 프레임(.cm-listing-results) 내부 스크롤 수행 (600px)
        await page.evaluate("""
            const rightFrame = document.querySelector('.cm-listing-results');
            if (rightFrame) {
                rightFrame.scrollTop = 600;
            }
        """)
        await asyncio.sleep(0.8)

        # 상태 점검
        header_y = await page.locator("header").bounding_box()
        filter_y = await page.locator(".cm-filter-panel").bounding_box()
        right_scroll_top = await page.evaluate("document.querySelector('.cm-listing-results').scrollTop")

        print(f"Header Y: {header_y['y']} (Must be 0)")
        print(f"Filter Panel Y: {filter_y['y']} (Must not move)")
        print(f"Right Frame ScrollTop: {right_scroll_top} (Should be 600)")

        # 우측 프레임 스크롤 상태 캡처
        await page.screenshot(path="reports/chamart_frame_scrolled_right_only.png")
        print("Captured reports/chamart_frame_scrolled_right_only.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_independent_frame_scroll())
