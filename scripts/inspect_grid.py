import asyncio
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda m: print(f"[LOG] {m.text}"))
        page.on("pageerror", lambda e: print(f"[PAGE ERR] {e}"))
        await page.goto("http://localhost:8501/chamart", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        grid_html = await page.locator("#vehicleGrid").inner_html()
        badge_text = await page.locator("#vehicleCountBadge").inner_text()
        print("Count badge:", badge_text)
        print("Grid HTML snippet:", grid_html[:400])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
