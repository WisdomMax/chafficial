import asyncio
import os
from playwright.async_api import async_playwright

async def capture_encar_showrooms():
    out_dir = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/reports"
    os.makedirs(out_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. PC 1440x900 - Staging Showroom Grid View
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://localhost:8501/staging/chamart", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=f"{out_dir}/encar_1440_staging_grid.png", full_page=False)
        print("Captured encar_1440_staging_grid.png")
        
        # 2. PC 1440x900 - Staging Showroom List View Switch
        await page.click("#btnViewList", force=True)
        await page.wait_for_timeout(600)
        await page.screenshot(path=f"{out_dir}/encar_1440_staging_list.png", full_page=False)
        print("Captured encar_1440_staging_list.png")
        
        # 3. PC 1280x800 - Standard Laptop View
        await page.click("#btnViewGrid", force=True)
        await page.set_viewport_size({"width": 1280, "height": 800})
        await page.wait_for_timeout(500)
        await page.screenshot(path=f"{out_dir}/encar_1280_staging.png", full_page=False)
        print("Captured encar_1280_staging.png")
        
        # 4. Detail View Test (Click first vehicle)
        card = page.locator('[onclick*="openVehicleDetail"]').first
        if await card.count() > 0:
            await card.click()
            await page.wait_for_timeout(1200)
            await page.screenshot(path=f"{out_dir}/encar_1440_detail_fixed.png", full_page=False)
            print("Captured encar_1440_detail_fixed.png")
        
        # 5. Tablet 1024x768 - Staging Showroom
        page_tablet = await browser.new_page(viewport={"width": 1024, "height": 768})
        await page_tablet.goto("http://localhost:8501/staging/chamart", wait_until="networkidle")
        await page_tablet.wait_for_timeout(1000)
        await page_tablet.screenshot(path=f"{out_dir}/encar_1024_staging.png", full_page=False)
        print("Captured encar_1024_staging.png")
        
        # 6. Mobile 390x844 - iPhone 12/13/14 size
        page_mobile = await browser.new_page(viewport={"width": 390, "height": 844})
        await page_mobile.goto("http://localhost:8501/staging/chamart", wait_until="networkidle")
        await page_mobile.wait_for_timeout(1000)
        await page_mobile.screenshot(path=f"{out_dir}/encar_390_staging_mobile.png", full_page=False)
        print("Captured encar_390_staging_mobile.png")
        
        # 7. Production Showroom 1440x900 (0 vehicles - Honesty verification banner)
        page_prod = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page_prod.goto("http://localhost:8501/chamart", wait_until="networkidle")
        await page_prod.wait_for_timeout(1000)
        await page_prod.screenshot(path=f"{out_dir}/encar_1440_production_clean.png", full_page=False)
        print("Captured encar_1440_production_clean.png")

        await browser.close()
        print("All screenshots captured successfully.")

if __name__ == "__main__":
    asyncio.run(capture_encar_showrooms())
