import asyncio
from playwright.async_api import async_playwright

async def test_header_sticky_and_spacing():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 1440x1000 PC 화면
        context = await browser.new_context(viewport={"width": 1440, "height": 1000})
        page = await context.new_page()

        # 1. 초기 로드 화면
        await page.goto("http://localhost:8501/chamart", wait_until="domcontentloaded")
        await asyncio.sleep(1.5)
        await page.screenshot(path="reports/chamart_compact_spacing.png")
        print("1. chamart_compact_spacing.png captured")

        # 2. 500px 아래로 스크롤 시 상단 메뉴바 고정 확인
        await page.evaluate("window.scrollTo(0, 500)")
        await asyncio.sleep(0.5)

        # 헤더의 bounding box 확인
        header_box = await page.locator("header").bounding_box()
        print(f"Header Y after 500px scroll: {header_box['y']} (Should be 0 for sticky)")

        await page.screenshot(path="reports/chamart_sticky_scrolled.png")
        print("2. chamart_sticky_scrolled.png captured")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_header_sticky_and_spacing())
