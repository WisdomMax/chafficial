import asyncio
from playwright.async_api import async_playwright

async def check_errors():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda exc: print(f"[PAGE ERROR] {exc}"))
        await page.goto("http://localhost:8501/chamart", wait_until="domcontentloaded")
        await asyncio.sleep(2)
        content = await page.content()
        print("Page loaded, length:", len(content))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(check_errors())
