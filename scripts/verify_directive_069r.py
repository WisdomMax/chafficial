import asyncio
from playwright.async_api import async_playwright

async def verify_directive_069_r():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # 1. PC 1440x900 - Staging Viewport
        page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        
        console_logs = []
        dialog_logs = []
        page.on('console', lambda m: console_logs.append(f'[{m.type}] {m.text}') if m.type in ['error', 'warning'] else None)
        page.on('pageerror', lambda e: console_logs.append(f'[PAGEERROR] {e}'))
        page.on('dialog', lambda d: dialog_logs.append(d.message) or d.dismiss())
        
        print('=== 1. Testing Staging Environment (100 cars UI Fixture) ===')
        await page.goto('http://localhost:8501/staging/chamart')
        await page.wait_for_selector('.cm-vehicle-row', timeout=6000)
        
        # Check banner
        banner_visible = await page.evaluate('''() => {
            return Boolean(document.querySelector('img[src*="chamart_hero_banner"]'));
        }''')
        print(f'Banner visible: {banner_visible}')
        
        # Check filter panel width
        filter_box = await page.evaluate('''() => {
            const el = document.querySelector('.cm-filter-panel');
            return el ? el.getBoundingClientRect().width : null;
        }''')
        print(f'Filter panel width: {filter_box}px (Target: 240~270px)')
        
        # Check layout width
        layout_box = await page.evaluate('''() => {
            const el = document.querySelector('.cm-listing-layout');
            return el ? el.getBoundingClientRect().width : null;
        }''')
        print(f'Layout width: {layout_box}px (Target: 1280~1400px)')

        # Check vehicle rows
        rows = await page.query_selector_all('.cm-vehicle-row')
        print(f'Loaded vehicle rows: {len(rows)}')
        
        # Horizontal overflow check
        overflow = await page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        print(f'Staging Horizontal overflow: {overflow}')
        
        await page.screenshot(path='reports/encar_1440_staging_directive_069r.png', full_page=True)
        print('Saved: reports/encar_1440_staging_directive_069r.png')
        
        # Test Detail Click
        print('\n=== 2. Testing 상세보기 Click Navigation ===')
        first_detail_btn = await page.query_selector('.cm-vehicle-row__detail')
        await first_detail_btn.click()
        await page.wait_for_timeout(1500)
        
        current_url = page.url
        print(f'URL after detail click: {current_url}')
        
        detail_hidden = await page.evaluate('document.getElementById("view-detail").classList.contains("hidden")')
        home_hidden = await page.evaluate('document.getElementById("view-home").classList.contains("hidden")')
        print(f'Detail view hidden: {detail_hidden}, Home view hidden: {home_hidden}')
        
        # Check photos in detail view
        photos_count = await page.evaluate('document.querySelectorAll("#vdrGalleryThumbStrip img").length')
        main_photo_src = await page.evaluate('''() => {
            const el = document.getElementById("vdrMainImg");
            return el ? el.src : null;
        }''')
        print(f'Detail Gallery photos count: {photos_count}')
        print(f'Detail Main photo src: {main_photo_src}')
        
        await page.screenshot(path='reports/encar_1440_detail_fixed_069r.png', full_page=False)
        print('Saved: reports/encar_1440_detail_fixed_069r.png')
        
        # Test Detail Reload (F5 resilience)
        print('\n=== 3. Testing Reload on Detail URL ===')
        await page.reload()
        await page.wait_for_timeout(1500)
        print(f'URL after reload: {page.url}')
        print(f'Dialogs triggered during reload: {dialog_logs}')
        detail_hidden_reload = await page.evaluate('document.getElementById("view-detail").classList.contains("hidden")')
        print(f'Detail view hidden after reload: {detail_hidden_reload} (Expected: False)')
        
        # Test Back to list
        print('\n=== 4. Testing Back to List ===')
        back_btn = await page.query_selector('#vdrBtnBack')
        if back_btn:
            await back_btn.click()
            await page.wait_for_timeout(1000)
            print(f'URL after back button: {page.url}')
            home_hidden_back = await page.evaluate('document.getElementById("view-home").classList.contains("hidden")')
            print(f'Home view hidden after back: {home_hidden_back} (Expected: False)')
            
        # Test 5. Production Showroom (chamart.html)
        print('\n=== 5. Testing Production Showroom (/chamart) ===')
        prod_page = await browser.new_page(viewport={'width': 1440, 'height': 900})
        await prod_page.goto('http://localhost:8501/chamart')
        await prod_page.wait_for_timeout(1500)
        
        prod_banner = await prod_page.evaluate('''() => {
            return Boolean(document.querySelector('img[src*="chamart_hero_banner"]'));
        }''')
        print(f'Production Banner visible: {prod_banner}')
        
        # Check forbidden staging strings
        page_text = await prod_page.evaluate('document.body.innerText')
        has_staging_text = ('스테이징 환경' in page_text) or ('기능 시연용' in page_text)
        print(f'Production contains forbidden staging text: {has_staging_text} (Expected: False)')
        
        prod_overflow = await prod_page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
        print(f'Production Horizontal overflow: {prod_overflow}')
        
        await prod_page.screenshot(path='reports/encar_1440_prod_directive_069r.png', full_page=True)
        print('Saved: reports/encar_1440_prod_directive_069r.png')
        
        clean_logs = [l for l in console_logs if 'Tailwind' not in l]
        print('\nConsole Errors/Warnings:', clean_logs)
        print('Dialog Logs:', dialog_logs)
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(verify_directive_069_r())
