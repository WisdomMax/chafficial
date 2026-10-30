import asyncio
from playwright.async_api import async_playwright
import os
import sqlite3
import re
from chaficial.platform.sourcing.carmanager_client import load_env

load_env()
user = os.getenv("CAR_MANAGER_ID")
pw = os.getenv("CAR_MANAGER_PW")

async def test_reality():
    conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
    c = conn.cursor()
    
    # 1. 사진이 있는 매물 (가격 확정 173대 중 3대)
    c.execute("""
        SELECT l.listing_id, v.model_name, v.target_price
        FROM vehicles v
        JOIN vehicle_listings l ON v.id = l.vehicle_id
        WHERE v.id IN (SELECT DISTINCT vehicle_id FROM vehicle_photos WHERE photo_source = 'CARMANAGER')
        LIMIT 3
    """)
    with_photos_sample = c.fetchall()

    # 2. 사진이 없는 매물 (상담 1,591대 중 3대)
    c.execute("""
        SELECT l.listing_id, v.model_name, v.target_price
        FROM vehicles v
        JOIN vehicle_listings l ON v.id = l.vehicle_id
        WHERE v.id NOT IN (SELECT DISTINCT vehicle_id FROM vehicle_photos)
        LIMIT 3
    """)
    without_photos_sample = c.fetchall()
    conn.close()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.carmanager.co.kr/User/Login", wait_until="networkidle")
        await page.fill("#userid", user)
        await page.fill("#userpwd", pw)
        btn = await page.query_selector("button[onclick*='commitLogin']")
        if btn:
            async with page.expect_navigation(wait_until="networkidle"):
                await btn.click()
        await page.wait_for_timeout(2000)

        await page.goto("https://www.carmanager.co.kr/Car/Data", wait_until="networkidle")
        enc_check = await page.evaluate(r"() => document.querySelector('#EncCheck')?.value || ''")
        req = context.request

        print("=== 1. 차량 사진 완비 매물 (확정 가격군) 원본 실측 ===")
        for enc, model, price in with_photos_sample:
            resp = await req.post("https://www.carmanager.co.kr/PopupFrame/CarDetailEnc/", form={"encarno": enc, "EncCheck": enc_check})
            html = await resp.text()
            matches = re.findall(r'https?://img\.carmanager\.co\.kr/temp/photo/\d+/[A-Fa-f0-9]+', html)
            print(f"[WITH PHOTO] {model} ({price}만원): 실사진 {len(matches)}장 확인")

        print("\n=== 2. 차량 사진 미등록 매물 (상담/미공개군) 원본 실측 ===")
        for enc, model, price in without_photos_sample:
            resp = await req.post("https://www.carmanager.co.kr/PopupFrame/CarDetailEnc/", form={"encarno": enc, "EncCheck": enc_check})
            html = await resp.text()
            matches = re.findall(r'https?://img\.carmanager\.co\.kr/temp/photo/\d+/[A-Fa-f0-9]+', html)
            has_noimage = "car_noimage" in html
            print(f"[NO PHOTO] {model} ({price}): 실사진 {len(matches)}장 확인, 'noimage' 태그 존재 여부: {has_noimage}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_reality())
