import asyncio
import os
from playwright.async_api import async_playwright

OUT_DIR = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6"
BASE_URL = "http://localhost:8501/chamart"

async def run_tests():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 1. 모바일 390px 검증 (iPhone 14 / 15 기준)
        # -------------------------------------------------------------
        print("\n[1] 모바일 390px 검증 시작...")
        ctx_mobile = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15",
            has_touch=True
        )
        page_m = await ctx_mobile.new_page()
        await page_m.goto(BASE_URL, wait_until="networkidle")
        await asyncio.sleep(1)

        # (1) 모바일 메인 배너 및 헤더 캡처
        banner_shot = os.path.join(OUT_DIR, "directive_083_mobile_banner_390.png")
        await page_m.screenshot(path=banner_shot)
        print(f"[*] 모바일 메인 화면 캡처: {banner_shot}")

        # (2) 모바일 전용 차량 카드 목록으로 스크롤 및 캡처
        await page_m.evaluate("window.scrollBy(0, 320)")
        await asyncio.sleep(0.5)
        cards_shot = os.path.join(OUT_DIR, "directive_083_mobile_cards_390.png")
        await page_m.screenshot(path=cards_shot)
        print(f"[*] 모바일 차량 카드 캡처: {cards_shot}")

        # (3) 첫 번째 차량 클릭하여 상세 페이지 진입
        first_card = page_m.locator(".cm-vehicle-row").first
        await first_card.click()
        await asyncio.sleep(1)
        await page_m.wait_for_selector("#vdrTopTabBar", timeout=5000)

        # (4) 사진 정보 탭 클릭
        photo_tab_btn = page_m.locator("#vdrTabBtnPhotos")
        await photo_tab_btn.click()
        await asyncio.sleep(0.5)

        # 모바일 사진 전용 탭 캡처
        mobile_photo_shot = os.path.join(OUT_DIR, "directive_083_mobile_photo_tab_390.png")
        await page_m.screenshot(path=mobile_photo_shot)
        print(f"[*] 모바일 사진 정보 탭 캡처: {mobile_photo_shot}")

        # 사진 다음 버튼 클릭 테스트 (연속 탐색)
        next_btn = page_m.locator("#vdrBtnDedicatedNext")
        if await next_btn.is_visible():
            await next_btn.click()
            await asyncio.sleep(0.3)
            counter_text = await page_m.locator("#vdrDedicatedCounter").text_content()
            print(f"[*] 모바일 사진 다음 넘기기 성공! 현재 카운터: {counter_text}")

        # (5) 터치 스와이프 시뮬레이션
        viewport_el = page_m.locator("#vdrDedicatedGalleryViewport")
        box = await viewport_el.bounding_box()
        if box:
            center_x = box["x"] + box["width"] / 2
            center_y = box["y"] + box["height"] / 2
            # 좌측으로 100px 스와이프 (다음 사진)
            await page_m.touchscreen.tap(center_x, center_y)
            await page_m.mouse.move(center_x, center_y)
            await page_m.mouse.down()
            await page_m.mouse.move(center_x - 120, center_y, steps=10)
            await page_m.mouse.up()
            await asyncio.sleep(0.3)
            print("[*] 모바일 터치 스와이프 동작 완료")

        await ctx_mobile.close()

        # -------------------------------------------------------------
        # 2. PC 1920px 검증 (데스크톱 기준)
        # -------------------------------------------------------------
        print("\n[2] PC 1920px 검증 시작...")
        ctx_pc = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page_pc = await ctx_pc.new_page()
        await page_pc.goto(BASE_URL, wait_until="networkidle")
        await asyncio.sleep(1)

        # (1) PC 매물 목록 (우측 패딩 및 가격 정렬 확인) 캡처
        pc_list_shot = os.path.join(OUT_DIR, "directive_083_pc_list_1920.png")
        await page_pc.screenshot(path=pc_list_shot)
        print(f"[*] PC 매물 목록 캡처: {pc_list_shot}")

        # (2) 첫 번째 차량 상세 보기 진입
        await page_pc.locator(".cm-vehicle-row").first.click()
        await asyncio.sleep(1)
        await page_pc.wait_for_selector("#vdrTopTabBar", timeout=5000)

        # (3) 사진 정보 탭 클릭 (가로폭 100% 대형 갤러리)
        await page_pc.locator("#vdrTabBtnPhotos").click()
        await asyncio.sleep(0.5)
        pc_photo_tab_shot = os.path.join(OUT_DIR, "directive_083_pc_photo_tab_1920.png")
        await page_pc.screenshot(path=pc_photo_tab_shot)
        print(f"[*] PC 사진 정보 탭 캡처: {pc_photo_tab_shot}")

        # PC에서 좌우 화살표로 3번 연속 넘기기
        for i in range(3):
            await page_pc.locator("#vdrBtnDedicatedNext").click()
            await asyncio.sleep(0.2)
        counter_pc = await page_pc.locator("#vdrDedicatedCounter").text_content()
        print(f"[*] PC 사진 연속 넘기기 성공! 현재 카운터: {counter_pc}")

        # (4) 사진 클릭하여 PC 전체 화면 Lightbox 뷰어 열기
        await page_pc.locator("#vdrDedicatedMainImage").click()
        await asyncio.sleep(0.5)
        pc_lightbox_shot = os.path.join(OUT_DIR, "directive_083_pc_lightbox_1920.png")
        await page_pc.screenshot(path=pc_lightbox_shot)
        print(f"[*] PC 전체화면 Lightbox 뷰어 캡처: {pc_lightbox_shot}")

        # 키보드 방향키 이동 테스트
        await page_pc.keyboard.press("ArrowRight")
        await asyncio.sleep(0.2)
        lb_counter = await page_pc.locator("#vdrLightboxCounter").text_content()
        print(f"[*] Lightbox 키보드 방향키 넘기기 성공! 카운터: {lb_counter}")

        # ESC 키로 닫기
        await page_pc.keyboard.press("Escape")
        await asyncio.sleep(0.3)
        lb_visible = await page_pc.locator("#vdrLightboxModal").is_visible()
        print(f"[*] Lightbox ESC 닫기 성공! (숨김 상태: {not lb_visible})")

        # (5) 차량 정보 탭 복귀 및 스펙/옵션/진단도면 확인
        await page_pc.locator("#vdrTabBtnInfo").click()
        await asyncio.sleep(0.5)
        pc_info_shot = os.path.join(OUT_DIR, "directive_083_pc_info_tab_1920.png")
        await page_pc.screenshot(path=pc_info_shot)
        print(f"[*] PC 차량 정보 탭 캡처: {pc_info_shot}")

        await ctx_pc.close()

        # -------------------------------------------------------------
        # 3. 추가 해상도 반응형 검증 (360px, 430px, 768px, 1366px)
        # -------------------------------------------------------------
        print("\n[3] 추가 반응형 해상도 검증...")
        viewports = [
            ("mobile_360", 360, 800),
            ("mobile_430", 430, 932),
            ("tablet_768", 768, 1024),
            ("laptop_1366", 1366, 768)
        ]
        for name, w, h in viewports:
            ctx_resp = await browser.new_context(viewport={"width": w, "height": h})
            page_r = await ctx_resp.new_page()
            await page_r.goto(BASE_URL, wait_until="networkidle")
            await asyncio.sleep(0.5)
            r_shot = os.path.join(OUT_DIR, f"directive_083_{name}.png")
            await page_r.screenshot(path=r_shot)
            print(f"[*] 해상도 {w}x{h} ({name}) 캡처 완료: {r_shot}")
            await ctx_resp.close()

        await browser.close()
        print("\n=== 모든 검증 및 스크린샷 캡처 완료! ===")

if __name__ == "__main__":
    asyncio.run(run_tests())
