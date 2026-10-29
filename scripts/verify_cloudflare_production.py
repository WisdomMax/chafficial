"""
Cloudflare 프로덕션 실서버 엔드투엔드 검증 스크립트 (https://chamart.pages.dev)
"""

import asyncio
import os
from playwright.async_api import async_playwright

async def verify_prod():
    out_dir = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        target_url = "https://88e66f64.chamart.pages.dev"
        print(f"[1] 프로덕션 접속: {target_url}...")
        await page.goto(target_url, wait_until="networkidle")
        await asyncio.sleep(2)

        # 1. 메인 홈 스크린샷
        home_shot = os.path.join(out_dir, "prod_home_1920.png")
        await page.screenshot(path=home_shot, full_page=False)
        print(f"메인 홈 캡처: {home_shot}")

        # 2. 첫 번째 매물 클릭하여 상세 뷰 진입
        print("[2] 첫 번째 차량 상세 뷰 진입...")
        first_card = page.locator(".cm-vehicle-row, .cm-album-card").first
        await first_card.click()
        await page.wait_for_selector("#vdrSpecsContainer", timeout=8000)
        await asyncio.sleep(1)

        # 3. 제원 표 캡처
        specs_sec = page.locator("#vdrSpecsContainer")
        await specs_sec.scroll_into_view_if_needed()
        await page.evaluate("() => window.scrollBy(0, -180)")
        await asyncio.sleep(0.5)
        specs_shot = os.path.join(out_dir, "prod_detail_specs.png")
        await page.screenshot(path=specs_shot, full_page=False)
        print(f"제원 표 캡처: {specs_shot}")

        # 4. 진단 맵 캡처 (보닛 클릭)
        diag_sec = page.locator("#vdrCarSvgDiagram")
        await diag_sec.scroll_into_view_if_needed()
        await page.evaluate("() => window.scrollBy(0, -180)")
        await asyncio.sleep(0.5)

        # 보닛 클릭
        await page.locator("#part-hood").click(force=True)
        await asyncio.sleep(0.3)
        diag_shot = os.path.join(out_dir, "prod_detail_diag_map.png")
        await page.screenshot(path=diag_shot, full_page=False)
        print(f"진단 맵 캡처: {diag_shot}")

        # 5. 상하 스크롤 검증
        print("[3] 상하 스크롤 테스트...")
        await page.evaluate("() => window.scrollTo(0, 2000)")
        await asyncio.sleep(0.5)
        scrolled_y = await page.evaluate("() => window.scrollY")
        print(f"스크롤 위치: {scrolled_y}px")
        assert scrolled_y > 1500, "상세 뷰 스크롤 불가 오류"

        # 6. 모바일 해상도 (390px) 캡처
        await page.set_viewport_size({"width": 390, "height": 844})
        await asyncio.sleep(0.5)
        await page.evaluate("() => window.scrollTo(0, 0)")
        await asyncio.sleep(0.5)
        mobile_shot = os.path.join(out_dir, "prod_detail_mobile_390.png")
        await page.screenshot(path=mobile_shot, full_page=False)
        print(f"모바일 상세 캡처: {mobile_shot}")

        print(f"콘솔 에러 수: {len(console_errors)}")
        if console_errors:
            print("콘솔 에러:", console_errors)

        await browser.close()
    print("프로덕션 검증 완료!")

if __name__ == "__main__":
    asyncio.run(verify_prod())
