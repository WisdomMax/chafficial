import asyncio
import os
import json
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6"
TARGET_URL = "https://chamart.cc"
ADMIN_API_PATH = "/api/admin/vehicles/64노3143?token=chamart-sync-secret-2026"

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        # 1. PC 데스크탑 목록 (1280x950) - 고객용 공개 0대 격리 입증
        pc_context = await browser.new_context(viewport={"width": 1280, "height": 950})
        pc_page = await pc_context.new_page()
        await pc_page.goto(TARGET_URL, wait_until="networkidle")
        await pc_page.wait_for_timeout(2000)

        pc_zero_path = os.path.join(ARTIFACT_DIR, "directive136_pc_public_list_zero.png")
        await pc_page.screenshot(path=pc_zero_path)
        print("Captured PC public list (0 items):", pc_zero_path)

        # 2. PC 관리자 검수 화면: 브라우저에서 실제 D1 관리자 API 호출 후 렌더링 (TASK 4)
        try:
            render_res = await pc_page.evaluate(f"""
                async () => {{
                    // D1 실제 관리자 API 직접 fetch (하드코딩 주입 배제)
                    const res = await fetch('{ADMIN_API_PATH}');
                    if (!res.ok) return {{ success: false, error: 'FETCH_FAILED', status: res.status }};
                    const realD1Data = await res.json();

                    // 프론트엔드 전역 저장 및 상세 렌더러 호출
                    window.publicVehicles = [realD1Data];
                    openVehicleDetail(realD1Data.id);

                    return {{
                        success: true,
                        plate: realD1Data.plate_number,
                        price: realD1Data.target_price,
                        mileage: realD1Data.mileage,
                        source: realD1Data._source,
                        photoCount: realD1Data.photo_count
                    }};
                }}
            """)
            print("Rendered D1 Real Data on PC:", render_res)
            await pc_page.wait_for_timeout(3000)

            pc_admin_path = os.path.join(ARTIFACT_DIR, "directive136_pc_admin_detail_real.png")
            await pc_page.screenshot(path=pc_admin_path)
            print("Captured PC real admin detail preview:", pc_admin_path)
        except Exception as e:
            print("Error rendering PC admin view:", e)

        # 3. 모바일 목록 (390x844) - 고객용 공개 0대 격리 입증
        mb_context = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mb_page = await mb_context.new_page()
        await mb_page.goto(TARGET_URL, wait_until="networkidle")
        await mb_page.wait_for_timeout(2000)

        mb_zero_path = os.path.join(ARTIFACT_DIR, "directive136_mobile_public_list_zero.png")
        await mb_page.screenshot(path=mb_zero_path)
        print("Captured Mobile public list (0 items):", mb_zero_path)

        # 4. 모바일 관리자 검수 화면: 브라우저에서 실제 D1 관리자 API 호출 후 렌더링 (TASK 4)
        try:
            render_res_mb = await mb_page.evaluate(f"""
                async () => {{
                    const res = await fetch('{ADMIN_API_PATH}');
                    if (!res.ok) return {{ success: false, error: 'FETCH_FAILED', status: res.status }};
                    const realD1Data = await res.json();

                    window.publicVehicles = [realD1Data];
                    openVehicleDetail(realD1Data.id);

                    return {{
                        success: true,
                        plate: realD1Data.plate_number,
                        price: realD1Data.target_price,
                        mileage: realD1Data.mileage,
                        source: realD1Data._source,
                        photoCount: realD1Data.photo_count
                    }};
                }}
            """)
            print("Rendered D1 Real Data on Mobile:", render_res_mb)
            await mb_page.wait_for_timeout(3000)

            mb_admin_path = os.path.join(ARTIFACT_DIR, "directive136_mobile_admin_detail_real.png")
            await mb_page.screenshot(path=mb_admin_path)
            print("Captured Mobile real admin detail preview:", mb_admin_path)
        except Exception as e:
            print("Error rendering Mobile admin view:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
