import asyncio
from playwright.async_api import async_playwright

async def capture_new_layout():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # PC 1440px
        context = await browser.new_context(viewport={"width": 1440, "height": 1050})
        page = await context.new_page()
        await page.goto("http://localhost:8501/chamart", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await page.screenshot(path="reports/chamart_new_layout_pc.png")
        print("Captured reports/chamart_new_layout_pc.png")

        # Staging도 캡처
        await page.goto("http://localhost:8501/staging/chamart", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await page.screenshot(path="reports/chamart_new_layout_staging.png")
        print("Captured reports/chamart_new_layout_staging.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_new_layout())
