import asyncio
from playwright.async_api import async_playwright

async def verify_clean_and_frame_scroll():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 960})
        page = await context.new_page()

        await page.goto("http://localhost:8501/chamart", wait_until="domcontentloaded")
        await asyncio.sleep(1.5)

        # 1. '엔카' 텍스트 존재 여부 전수 검증
        body_text = await page.inner_text("body")
        has_encar = "엔카" in body_text
        print(f"Has '엔카' in visible body: {has_encar} (Must be False!)")

        # 좌측 필터 헤더 텍스트 확인
        filter_header = await page.locator(".cm-filter-panel__header strong").inner_text()
        print(f"Filter panel header title: '{filter_header.strip()}' (Should be '차마트 정밀 상세 검색')")

        # 2. window 스크롤 차단 확인 (window.scrollTo 시도)
        await page.evaluate("window.scrollTo(0, 500)")
        await asyncio.sleep(0.3)
        window_scroll_y = await page.evaluate("window.scrollY")
        print(f"Window scrollY after attempt: {window_scroll_y} (Must be 0!)")

        # 3. 우측 프레임 독립 스크롤 동작 확인
        await page.evaluate("""
            const rf = document.querySelector('.cm-listing-results');
            if (rf) rf.scrollTop = 500;
        """)
        await asyncio.sleep(0.5)
        rf_scroll_top = await page.evaluate("document.querySelector('.cm-listing-results').scrollTop")
        header_y = await page.locator("header").bounding_box()
        filter_y = await page.locator(".cm-filter-panel").bounding_box()

        print(f"Right Frame scrollTop: {rf_scroll_top} (Should be 500)")
        print(f"Header Y: {header_y['y']} (Must be 0)")
        print(f"Filter Panel Y: {filter_y['y']} (Must not move)")

        # 4. 스크린샷 캡처
        await page.screenshot(path="reports/chamart_perfect_split_frame.png")
        print("Captured reports/chamart_perfect_split_frame.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_clean_and_frame_scroll())
