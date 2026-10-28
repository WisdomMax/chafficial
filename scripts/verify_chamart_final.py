import asyncio
from playwright.async_api import async_playwright

async def verify_final():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        
        # 1. Open /chamart (production showroom URL user is using)
        await page.goto('http://localhost:8501/chamart')
        await page.wait_for_selector('.cm-vehicle-row', timeout=6000)
        await page.wait_for_timeout(1000)
        
        rows = await page.query_selector_all('.cm-vehicle-row')
        print(f'/chamart loaded rows count: {len(rows)}')
        
        # Header closeup screenshot
        await page.screenshot(path='reports/chamart_header_perfect_align.png', clip={'x': 0, 'y': 0, 'width': 1440, 'height': 280})
        print('Saved: reports/chamart_header_perfect_align.png')
        
        # Full page screenshot
        await page.screenshot(path='reports/chamart_prod_with_100_cars.png', full_page=True)
        print('Saved: reports/chamart_prod_with_100_cars.png')
        
        # Test detail click on first row
        first_btn = await page.query_selector('.cm-vehicle-row__detail')
        if first_btn:
            await first_btn.click()
            await page.wait_for_timeout(1000)
            print(f'Detail URL: {page.url}')
            
            await page.screenshot(path='reports/chamart_detail_from_prod.png', full_page=False)
            print('Saved: reports/chamart_detail_from_prod.png')
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(verify_final())
