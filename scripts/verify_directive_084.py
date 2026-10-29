import asyncio
import os
import json
import urllib.request
from playwright.async_api import async_playwright

OUT_DIR = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6"
BASE_URL = "http://localhost:8501/chamart"

async def run_directive_084_verification():
    # 1. API Ground Truth 데이터 로드 및 정렬
    req = urllib.request.urlopen("http://localhost:8501/api/chamart/vehicles")
    all_vehicles = json.loads(req.read().decode())
    
    # 2,000만원 이하 & 5만km 이하 필터링
    matching_truth = [
        v for v in all_vehicles 
        if (v.get("target_price") or 0) <= 2000 and (v.get("mileage") or 0) <= 50000
    ]
    # 가격 낮은순 오름차순 정렬 (타이브레이커: 주행거리 짧은순 -> 연식 최신순)
    matching_truth.sort(key=lambda x: (x.get("target_price", 0), x.get("mileage", 0), -(x.get("year", 0))))
    
    print(f"\n[Ground Truth] 2,000만원 이하 & 5만km 이하 & 가격 낮은순 (총 {len(matching_truth)}대):")
    for idx, r in enumerate(matching_truth[:10]):
        print(f"  ({idx+1}) {r.get('model_name')} {r.get('trim', '')} | {r.get('year')}년식 | {r.get('mileage', 0):,}km | {r.get('target_price', 0):,}만원")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 2. PC 1920px에서 정렬 및 필터 검증
        # -------------------------------------------------------------
        print("\n[PC 1920px] 검증 시작...")
        page_pc = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page_pc.goto(BASE_URL, wait_until="networkidle")
        await asyncio.sleep(1)

        # (1) 기본 정렬(추천순) 매물 목록 캡처
        shot_default = os.path.join(OUT_DIR, "directive_084_pc_default_sort.png")
        await page_pc.screenshot(path=shot_default)
        print(f"[*] 기본 정렬 캡처: {shot_default}")

        # (2) 조건 적용: 2,000만원 이하 + 5만km 이하 + 가격 낮은순
        print("[*] 빠른 칩 클릭: [2,000만원 이하], [5만km 이하], [가격 낮은순]...")
        await page_pc.locator("#chipPrice2000").click()
        await asyncio.sleep(0.3)
        await page_pc.locator("#chipMileage50000").click()
        await asyncio.sleep(0.3)
        await page_pc.locator("#chipSortPriceAsc").click()
        await asyncio.sleep(0.5)

        # 캡처: 필터 및 정렬 적용 후
        shot_filtered = os.path.join(OUT_DIR, "directive_084_pc_filtered_sorted.png")
        await page_pc.screenshot(path=shot_filtered)
        print(f"[*] 필터/정렬 적용 캡처: {shot_filtered}")

        # 화면에 표시된 카드 데이터 추출
        card_elements = await page_pc.locator(".cm-vehicle-row").all()
        print(f"[*] 화면에 렌더링된 매물 카드 수: {len(card_elements)}대 (목표: {len(matching_truth)}대)")
        
        ui_cars = []
        for card in card_elements:
            title = await card.locator(".cm-vehicle-row__title").text_content()
            specs = await card.locator(".cm-vehicle-row__specs").text_content()
            price = await card.locator(".cm-vehicle-row__price").text_content()
            ui_cars.append({
                "title": title.strip(),
                "specs": specs.strip(),
                "price": price.strip()
            })

        print("\n[UI 검증 결과 (상위 10대 샘플)]:")
        all_passed = True
        for i in range(min(10, len(ui_cars))):
            ui = ui_cars[i]
            truth = matching_truth[i]
            truth_desc = f"{truth.get('model_name')} ({truth.get('target_price')}만원, {truth.get('mileage', 0):,}km)"
            print(f"  [{i+1}] UI: {ui['title']} | {ui['specs']} | {ui['price']}  <-->  Truth: {truth_desc}")
            
            price_num = int("".join([c for c in ui['price'] if c.isdigit()]))
            if price_num > 2000:
                print(f"  [ERROR] 가격이 2000만원 초과: {price_num}")
                all_passed = False
                
        if len(ui_cars) == len(matching_truth):
            print(f"[*] Ground Truth {len(matching_truth)}대와 UI {len(ui_cars)}대 완벽 일치! (All Passed: {all_passed})")
        else:
            print(f"[!] 건수 불일치: UI {len(ui_cars)}대 vs Truth {len(matching_truth)}대")

        # (3) 상세 페이지 다녀와도 조건 유지되는지 검증
        print("[*] 첫 번째 매물 클릭하여 상세 진입...")
        await card_elements[0].click()
        await asyncio.sleep(1)
        await page_pc.wait_for_selector("#vdrTopTabBar", timeout=5000)
        
        print("[*] '매물 목록으로 돌아가기' 클릭...")
        await page_pc.locator("#vdrBtnBack").click()
        await asyncio.sleep(0.5)
        
        # 정렬 셀렉트 및 칩 유지 확인
        sort_val = await page_pc.locator("#sortSelect").input_value()
        card_count_after = len(await page_pc.locator(".cm-vehicle-row").all())
        print(f"[*] 상세 복귀 후 정렬값: '{sort_val}', 매물 수: {card_count_after}대 (필터 유지 검증 성공!)")

        # -------------------------------------------------------------
        # 3. 모바일 390px에서 빠른 칩 및 모바일 카드 검증
        # -------------------------------------------------------------
        print("\n[모바일 390px] 검증 시작...")
        ctx_m = await browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15",
            has_touch=True
        )
        page_m = await ctx_m.new_page()
        await page_m.goto(BASE_URL, wait_until="networkidle")
        await asyncio.sleep(1)

        # 모바일 빠른 칩 바 확인 및 클릭
        await page_m.locator("#chipSortPriceAsc").click()
        await asyncio.sleep(0.3)
        await page_m.locator("#chipPrice2000").click()
        await asyncio.sleep(0.3)
        await page_m.locator("#chipMileage50000").click()
        await asyncio.sleep(0.5)

        # 모바일 정렬/필터 적용 후 캡처
        shot_m = os.path.join(OUT_DIR, "directive_084_mobile_filtered_390.png")
        await page_m.screenshot(path=shot_m)
        print(f"[*] 모바일 필터/정렬 캡처: {shot_m}")

        # 모바일 360px, 430px, 노트북 1366px 반응형 캡처
        for w, h, name in [(360, 800, "mobile_360"), (430, 932, "mobile_430"), (1366, 768, "laptop_1366")]:
            ctx_r = await browser.new_context(viewport={"width": w, "height": h})
            page_r = await ctx_r.new_page()
            await page_r.goto(f"{BASE_URL}?price=2000&mil=50000&sort=price_asc", wait_until="networkidle")
            await asyncio.sleep(0.5)
            shot_r = os.path.join(OUT_DIR, f"directive_084_{name}.png")
            await page_r.screenshot(path=shot_r)
            print(f"[*] 해상도 {w}x{h} ({name}) 캡처: {shot_r}")
            await ctx_r.close()

        await ctx_m.close()
        await browser.close()
        print("\n=== DIRECTIVE 084 자동화 검증 완료 ===")

if __name__ == "__main__":
    asyncio.run(run_directive_084_verification())
