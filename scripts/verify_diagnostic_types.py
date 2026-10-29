import asyncio
import os
import sqlite3
from playwright.async_api import async_playwright

async def verify_types():
    conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
    cur = conn.cursor()

    # 5개 유형의 차량 ID 샘플 추출
    cur.execute("SELECT id, model_name, accident_history_json FROM vehicles WHERE is_demo = 1;")
    rows = cur.fetchall()
    conn.close()

    samples = {
        "CLEAN": None,
        "OUTER_REPLACED": None,
        "OUTER_REPAIRED": None,
        "FRAME_DAMAGED": None,
        "UNKNOWN": None
    }

    import json
    for r in rows:
        v_id, model, acc_json = r
        if acc_json:
            acc = json.loads(acc_json)
            st = acc.get("accident_state")
            if st in samples and samples[st] is None:
                samples[st] = {"id": v_id, "model": model, "state": st}

    print("샘플 차량:", samples)

    out_dir = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        # 먼저 쇼룸 페이지 로드
        await page.goto("http://localhost:8501/chamart", wait_until="networkidle")
        await asyncio.sleep(1)

        for st_type, info in samples.items():
            if not info:
                continue
            v_id = info["id"]
            print(f"[{st_type}] {info['model']} ({v_id}) 상세 진입...")
            await page.evaluate(f"openVehicleDetail('{v_id}')")
            await page.wait_for_selector("#vdrSpecsContainer", timeout=5000)
            await asyncio.sleep(0.5)

            # 진단 맵 섹션으로 스크롤
            diag_sec = page.locator("#vdrCarSvgDiagram")
            await diag_sec.scroll_into_view_if_needed()
            await page.evaluate("() => window.scrollBy(0, -180)")
            await asyncio.sleep(0.3)

            shot_path = os.path.join(out_dir, f"diag_sample_{st_type.lower()}.png")
            await page.screenshot(path=shot_path, full_page=False)
            print(f"캡처 완료: {shot_path}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_types())
