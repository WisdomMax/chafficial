import asyncio
import os
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6"
LANDROVER_ID = "e6670a2e-c532-435e-b34a-b4a3ff9a677c"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        # 1. PC 데스크탑 목록 (1280x950)
        pc_context = await browser.new_context(viewport={"width": 1280, "height": 950})
        pc_page = await pc_context.new_page()
        await pc_page.goto("https://chamart.cc", wait_until="networkidle")
        await pc_page.wait_for_timeout(2000)

        pc_list_path = os.path.join(ARTIFACT_DIR, "directive133_pc_list.png")
        await pc_page.screenshot(path=pc_list_path)
        print("Captured PC list screen:", pc_list_path)

        # 2. PC 상세 모달 (openVehicleDetail 호출)
        try:
            await pc_page.evaluate(f"openVehicleDetail('{LANDROVER_ID}')")
            await pc_page.wait_for_timeout(2500)
            pc_modal_path = os.path.join(ARTIFACT_DIR, "directive133_pc_detail_modal.png")
            await pc_page.screenshot(path=pc_modal_path)
            print("Captured PC detail modal:", pc_modal_path)
        except Exception as e:
            print("Error opening detail on PC:", e)

        # 3. 모바일 목록 (390x844)
        mb_context = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mb_page = await mb_context.new_page()
        await mb_page.goto("https://chamart.cc", wait_until="networkidle")
        await mb_page.wait_for_timeout(2000)

        mb_list_path = os.path.join(ARTIFACT_DIR, "directive133_mobile_list.png")
        await mb_page.screenshot(path=mb_list_path)
        print("Captured Mobile list screen:", mb_list_path)

        # 4. 모바일 상세 모달
        try:
            await mb_page.evaluate(f"openVehicleDetail('{LANDROVER_ID}')")
            await mb_page.wait_for_timeout(2500)
            mb_modal_path = os.path.join(ARTIFACT_DIR, "directive133_mobile_detail.png")
            await mb_page.screenshot(path=mb_modal_path)
            print("Captured Mobile detail modal:", mb_modal_path)
        except Exception as e:
            print("Error opening detail on Mobile:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
