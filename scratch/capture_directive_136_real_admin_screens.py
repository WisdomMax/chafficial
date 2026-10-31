import asyncio
import os
import json
import urllib.request
import urllib.parse
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6"
TARGET_URL = "https://chamart.cc"
ADMIN_TOKEN = os.environ.get("CHAMART_ADMIN_TOKEN", "")
LANDROVER_PLATE = "64노3143"

def fetch_admin_vehicle_data_server_side():
    """
    DIRECTIVE 136-SEC-R 지침 준수:
    브라우저 page.evaluate() 내부 문자열에 토큰을 삽입하지 않고,
    서버 측(Python)에서 Bearer 인증으로 데이터를 안전하게 사전 조회.
    """
    endpoint = f"{TARGET_URL}/api/admin/vehicles/{urllib.parse.quote(LANDROVER_PLATE)}"
    req = urllib.request.Request(endpoint, headers={
        "User-Agent": "AdminCaptureScript/1.0",
        "Authorization": f"Bearer {ADMIN_TOKEN}"
    })
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Server-side fetch failed: HTTP {resp.status}")
        return json.loads(resp.read().decode('utf-8'))

async def run():
    # 0. 서버 측에서 D1 실제 원본 데이터를 안전하게 사전 조회 (브라우저 토큰 노출 제로)
    real_d1_data = fetch_admin_vehicle_data_server_side()
    print("[Server-Side Auth] Successfully fetched D1 vehicle data:", {
        "plate": real_d1_data.get("plate_number"),
        "price": real_d1_data.get("target_price"),
        "photos": real_d1_data.get("photo_count"),
        "_source": real_d1_data.get("_source")
    })

    async with async_playwright() as p:
        browser = await p.chromium.launch()

        # 1. PC 데스크탑 목록 (1280x950) - 고객용 공개 0대 격리 입증
        pc_context = await browser.new_context(viewport={"width": 1280, "height": 950})
        pc_page = await pc_context.new_page()
        await pc_page.goto(TARGET_URL, wait_until="networkidle")
        await pc_page.wait_for_timeout(3000)

        pc_zero_path = os.path.join(ARTIFACT_DIR, "directive136_pc_public_list_zero.png")
        await pc_page.screenshot(path=pc_zero_path)
        print("Captured PC public list (0 items):", pc_zero_path)

        # 2. PC 관리자 검수 화면: 서버 측에서 인증 조회한 데이터를 순수 주입하여 렌더링 (토큰 주입 배제)
        try:
            await pc_page.wait_for_timeout(2000)
            render_res = await pc_page.evaluate("""
                (data) => {
                    window.publicVehicles = [data];
                    openVehicleDetail(data.id);
                    return {
                        success: true,
                        plate: data.plate_number,
                        price: data.target_price,
                        mileage: data.mileage,
                        source: data._source,
                        photoCount: data.photo_count
                    };
                }
            """, real_d1_data)
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

        # 4. 모바일 관리자 검수 화면: 서버 측 인증 데이터 순수 주입 렌더링 (토큰 주입 배제)
        try:
            await mb_page.wait_for_timeout(2000)
            render_res_mb = await mb_page.evaluate("""
                (data) => {
                    window.publicVehicles = [data];
                    openVehicleDetail(data.id);
                    return {
                        success: true,
                        plate: data.plate_number,
                        price: data.target_price,
                        mileage: data.mileage,
                        source: data._source,
                        photoCount: data.photo_count
                    };
                }
            """, real_d1_data)
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
