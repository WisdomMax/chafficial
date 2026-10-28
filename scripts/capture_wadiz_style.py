import asyncio
from playwright.async_api import async_playwright

async def capture_wadiz_style():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. Production showroom (/chamart)
        page_prod = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page_prod.goto('http://localhost:8501/chamart')
        await page_prod.wait_for_timeout(1500)
        await page_prod.screenshot(path='reports/chamart_wadiz_prod_1440.png', full_page=True)
        print('Saved: reports/chamart_wadiz_prod_1440.png')
        
        # 2. Staging showroom (/staging/chamart)
        page_stg = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await page_stg.goto('http://localhost:8501/staging/chamart')
        await page_stg.wait_for_selector('.cm-vehicle-row', timeout=5000)
        await page_stg.wait_for_timeout(1000)
        await page_stg.screenshot(path='reports/chamart_wadiz_staging_1440.png', full_page=True)
        print('Saved: reports/chamart_wadiz_staging_1440.png')
        
        # 3. Header & Banner closeup
        await page_prod.screenshot(path='reports/chamart_wadiz_banner_closeup.png', clip={'x': 0, 'y': 0, 'width': 1440, 'height': 480})
        print('Saved: reports/chamart_wadiz_banner_closeup.png')
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(capture_wadiz_style())
