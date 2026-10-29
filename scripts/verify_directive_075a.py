import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def verify_075a():
    results = {
        "passed": 0,
        "failed": 0,
        "specs_checked": False,
        "vin_copied": False,
        "parts_tested": [],
        "tabs_tested": [],
        "screenshots": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        print("[1] 로컬 쇼룸 접속...")
        await page.goto("http://localhost:8501/chamart", wait_until="networkidle")
        await asyncio.sleep(1)

        print("[2] 첫 번째 차량 상세 보기 진입...")
        card = page.locator(".cm-vehicle-row, .cm-album-card").first
        await card.click()
        await page.wait_for_selector("#view-detail:not(.hidden)", timeout=5000)
        await asyncio.sleep(1)

        # 1. 제원 표 검증
        print("[3] 차량 기본 제원 표 검증...")
        specs_container = page.locator("#vdrSpecsContainer")
        assert await specs_container.count() > 0, "제원 표 컨테이너 누락"
        specs_text = await specs_container.inner_text()
        print(f"제원 텍스트 샘플:\n{specs_text[:200]}...")
        assert "차량번호" in specs_text
        assert "연식" in specs_text
        assert "최초등록일" in specs_text
        assert "차대번호 (VIN)" in specs_text
        results["specs_checked"] = True
        results["passed"] += 1

        # VIN 복사 버튼 클릭 테스트
        vin_btn = page.locator("#vdrBtnCopyVin")
        if await vin_btn.count() > 0:
            await vin_btn.first.click()
            await asyncio.sleep(0.3)
            # label 메시지 확인
            lbl = page.locator("#vdrVinCopyLabel")
            if await lbl.count() > 0:
                txt = await lbl.inner_text()
                print(f"VIN 복사 피드백 라벨: '{txt}'")
                assert "복사" in txt, "VIN 복사 피드백 실패"
                results["vin_copied"] = True
                results["passed"] += 1

        # 2. 탭 필터링 테스트 (전체 / 외판 / 골격)
        print("[4] 진단 맵 탭 전환 테스트...")
        tab_all = page.locator("#vdrDiagTabAll")
        tab_outer = page.locator("#vdrDiagTabOuter")
        tab_frame = page.locator("#vdrDiagTabFrame")

        await tab_outer.click()
        await asyncio.sleep(0.3)
        outer_opacity = await page.locator("#part-hood").evaluate("el => getComputedStyle(el).opacity")
        frame_opacity = await page.locator("#part-pillar-a").evaluate("el => getComputedStyle(el).opacity")
        print(f"외판 탭: hood opacity={outer_opacity}, pillar-a opacity={frame_opacity}")
        assert float(outer_opacity) > 0.8 and float(frame_opacity) < 0.3, "외판 탭 필터링 실패"
        results["tabs_tested"].append("outer")
        results["passed"] += 1

        await tab_frame.click()
        await asyncio.sleep(0.3)
        outer_opacity2 = await page.locator("#part-hood").evaluate("el => getComputedStyle(el).opacity")
        frame_opacity2 = await page.locator("#part-pillar-a").evaluate("el => getComputedStyle(el).opacity")
        print(f"골격 탭: hood opacity={outer_opacity2}, pillar-a opacity={frame_opacity2}")
        assert float(outer_opacity2) < 0.3 and float(frame_opacity2) > 0.8, "골격 탭 필터링 실패"
        results["tabs_tested"].append("frame")
        results["passed"] += 1

        await tab_all.click()
        await asyncio.sleep(0.3)
        results["tabs_tested"].append("all")
        results["passed"] += 1

        # 3. 24개 부위 전수 클릭 테스트
        print("[5] 24개 부위 전수 클릭 테스트...")
        all_parts = [
            'hood', 'front-bumper', 'rear-bumper', 'fender-fl', 'fender-fr',
            'door-fl', 'door-fr', 'door-rl', 'door-rr', 'roof', 'trunk',
            'quarter-l', 'quarter-r', 'frame-rad-support', 'frame-member-l',
            'frame-member-r', 'frame-member-rl', 'frame-member-rr', 'pillar-a',
            'pillar-a-r', 'pillar-b', 'pillar-b-r', 'pillar-c', 'pillar-c-r'
        ]

        for p_key in all_parts:
            locator = page.locator(f"#part-{p_key}")
            if await locator.count() == 0:
                print(f"부위 누락: {p_key}")
                results["failed"] += 1
                continue
            
            # 부위 요소가 화면에 보이도록 스크롤 및 클릭
            await locator.scroll_into_view_if_needed()
            await page.evaluate("() => window.scrollBy(0, -160)") # 상단 고정 헤더(150px) 회피
            await asyncio.sleep(0.05)
            await locator.click(force=True)
            await asyncio.sleep(0.1)

            part_name = await page.locator("#vdrSelectedPartName").inner_text()
            part_badge = await page.locator("#vdrSelectedPartBadge").inner_text()
            part_state = await page.locator("#vdrSelectedPartState").inner_text()
            
            # 영문 내부 코드가 노출되지 않고 한국어가 잘 뜨는지 검증
            assert p_key not in part_name, f"영문 코드 노출 오류: {p_key} in {part_name}"
            assert len(part_name.strip()) > 0, f"부위 한글명 누락: {p_key}"
            
            results["parts_tested"].append({
                "key": p_key,
                "name": part_name,
                "badge": part_badge,
                "state": part_state
            })
            results["passed"] += 1

        print(f"24개 부위 전수 클릭 완료! 검증 성공: {len(results['parts_tested'])}개")

        # 4. 스크롤 테스트
        print("[6] 상세 뷰 상하 스크롤 테스트...")
        initial_scroll = await page.evaluate("() => window.scrollY")
        await page.evaluate("() => window.scrollTo(0, 1500)")
        await asyncio.sleep(0.5)
        scrolled_y = await page.evaluate("() => window.scrollY")
        print(f"스크롤 이동: {initial_scroll} -> {scrolled_y}")
        assert scrolled_y > 1000, "상세 뷰 스크롤 불가 오류"
        results["passed"] += 1

        # 5. 해상도별 스크린샷 캡처
        resolutions = [
            (1920, 1080, "pc_1920"),
            (1366, 768, "pc_1366"),
            (768, 1024, "tablet_768"),
            (390, 844, "mobile_390")
        ]

        out_dir = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6"
        for w, h, name in resolutions:
            await page.set_viewport_size({"width": w, "height": h})
            await asyncio.sleep(0.5)
            # 최상단 이동
            await page.evaluate("() => window.scrollTo(0, 0)")
            await asyncio.sleep(0.3)
            shot_path = os.path.join(out_dir, f"directive_075a_{name}.png")
            await page.screenshot(path=shot_path, full_page=False)
            results["screenshots"].append(shot_path)
            print(f"캡처 완료: {shot_path}")

        print(f"콘솔 에러 수: {len(console_errors)}")
        if console_errors:
            print("콘솔 에러 목록:", console_errors[:5])

        await browser.close()

    print("\n=== 최종 결과 ===")
    print(f"통과: {results['passed']}, 실패: {results['failed']}")
    return results

if __name__ == "__main__":
    asyncio.run(verify_075a())
