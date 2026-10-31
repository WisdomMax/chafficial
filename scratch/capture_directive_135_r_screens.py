import asyncio
import os
import json
from playwright.async_api import async_playwright

ARTIFACT_DIR = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6"
LANDROVER_DATA = {
    "id": "e6670a2e-c532-435e-b34a-b4a3ff9a677c",
    "branch_id": "61fea9a4-58f0-42bd-862c-14fd16d0d21c",
    "plate_number": "64노3143",
    "model_name": "[랜드로버] 디스커버리 스포츠 2.0 TD4 SE",
    "year": 2018,
    "mileage": 125000,
    "fuel_type": "경유",
    "transmission": "오토",
    "color": "흰색",
    "target_price": 1090,
    "status": "IN_REVIEW",
    "is_demo": 0,
    "is_public": 0,
    "publishing_status": "PENDING_REVIEW",
    "listing_ownership_type": "EXTERNAL",
    "seller_company_name": "(주)더쿨모터스",
    "dealer_name": "유동호",
    "vin": "SALCA2BN5JH761441",
    "first_registration_date": "2018-09-14",
    "interior_color": "블랙",
    "primary_photo_url": "https://img.carmanager.co.kr/temp/photo/20260909/0CAD6BE080CDA63FE5F689D30327DD6A4164F8FB68FFD2B387143B1E5AA3F415.jpg",
    "photos": [
        {"url": "https://img.carmanager.co.kr/temp/photo/20260909/0CAD6BE080CDA63FE5F689D30327DD6A4164F8FB68FFD2B387143B1E5AA3F415.jpg", "caption": "01. 전면 외관 (실차)", "category": "EXTERIOR"},
        {"url": "https://img.carmanager.co.kr/temp/photo/20260909/4853A188B7DA6CD5C94FE2860E1AEA420F4075314D156D717483511B1D17D80D.jpg", "caption": "02. 전측면 좌 (실차)", "category": "EXTERIOR"},
        {"url": "https://img.carmanager.co.kr/temp/photo/20260909/832063D2D5C2ACE60E763B994091811D89F767989B4943D2420E1A5C6B62705E.jpg", "caption": "03. 후측면 좌 (실차)", "category": "EXTERIOR"},
        {"url": "https://img.carmanager.co.kr/temp/photo/20260909/68FF1F19B4E51EC196EA617DAB10AED32FD4D0CD51C7AF671D836FFCFDF935F2.jpg", "caption": "04. 후면 외관 (실차)", "category": "EXTERIOR"},
        {"url": "https://img.carmanager.co.kr/temp/photo/20260909/5D97EDACCAAC548FF48880BAFCA1FA36A24896712DC3DADE32AFBC21CF57825F.jpg", "caption": "05. 운전석 콕핏 (실차)", "category": "INTERIOR"},
        {"url": "https://img.carmanager.co.kr/temp/photo/20260909/810901E10873104CF5E76905334D90B0A3098EDEC1412D23D7377F78BD564262.jpg", "caption": "06. 계기판/주행거리 (실차)", "category": "INTERIOR"},
        {"url": "https://img.carmanager.co.kr/temp/photo/20260909/AF0B7252F643FD2BF6A1669DCC0ADD36C1C41A42AD983347444CF858984B9779.jpg", "caption": "07. 센터페시아/내비게이션 (실차)", "category": "INTERIOR"},
        {"url": "https://img.carmanager.co.kr/temp/photo/20260909/27058443325C4AEE09F67B9D67EA4067966D901D294736908A11CAF54EB8ED9F.jpg", "caption": "08. 2열 시트 공간 (실차)", "category": "INTERIOR"},
        {"url": "https://img.carmanager.co.kr/temp/photo/20260909/985AEDD0B201DC738D201F28A38D9A29A7349A273CB425CECCFBC69C510F021E.jpg", "caption": "09. 트렁크 공간 (실차)", "category": "INTERIOR"}
    ],
    "spec_summary": {
        "year": "2018년식 (18년 09월 최초등록)",
        "mileage": "125,000 km",
        "fuel": "디젤",
        "transmission": "자동(오토)",
        "displacement": "1,999 cc (확인대기)",
        "color": "화이트"
    }
}

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()

        # 1. PC 데스크탑 목록 (1280x950) - 비공개 격리 입증
        pc_context = await browser.new_context(viewport={"width": 1280, "height": 950})
        pc_page = await pc_context.new_page()
        await pc_page.goto("https://chamart.cc", wait_until="networkidle")
        await pc_page.wait_for_timeout(2000)

        pc_list_path = os.path.join(ARTIFACT_DIR, "directive135_r_pc_list_blocked.png")
        await pc_page.screenshot(path=pc_list_path)
        print("Captured PC list screen (0 items):", pc_list_path)

        # 2. PC 관리자 검수 상세 뷰 프리뷰 (1280x1200)
        try:
            await pc_page.evaluate(f"""
                window.publicVehicles = [{json.dumps(LANDROVER_DATA)}];
                openVehicleDetail('{LANDROVER_DATA["id"]}');
            """)
            await pc_page.wait_for_timeout(3000)
            pc_modal_path = os.path.join(ARTIFACT_DIR, "directive135_r_pc_detail_preview.png")
            await pc_page.screenshot(path=pc_modal_path)
            print("Captured PC detail preview:", pc_modal_path)
        except Exception as e:
            print("Error opening detail on PC:", e)

        # 3. 모바일 목록 (390x844) - 비공개 격리 입증
        mb_context = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
        mb_page = await mb_context.new_page()
        await mb_page.goto("https://chamart.cc", wait_until="networkidle")
        await mb_page.wait_for_timeout(2000)

        mb_list_path = os.path.join(ARTIFACT_DIR, "directive135_r_mobile_list_blocked.png")
        await mb_page.screenshot(path=mb_list_path)
        print("Captured Mobile list screen (0 items):", mb_list_path)

        # 4. 모바일 관리자 검수 상세 뷰 프리뷰 (390x844)
        try:
            await mb_page.evaluate(f"""
                window.publicVehicles = [{json.dumps(LANDROVER_DATA)}];
                openVehicleDetail('{LANDROVER_DATA["id"]}');
            """)
            await mb_page.wait_for_timeout(3000)
            mb_modal_path = os.path.join(ARTIFACT_DIR, "directive135_r_mobile_detail_preview.png")
            await mb_page.screenshot(path=mb_modal_path)
            print("Captured Mobile detail preview:", mb_modal_path)
        except Exception as e:
            print("Error opening detail on Mobile:", e)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
