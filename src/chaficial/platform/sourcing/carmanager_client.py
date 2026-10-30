"""
CarManager Live Client (DIRECTIVE 096)
- Authenticates with real CarManager credentials from .env.
- Fetches live vehicle listings from MyPageCar / CarData.
- Returns structured real-time snapshot for CarManagerSyncService.
"""

import os
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional

def load_env():
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

class CarManagerLiveClient:
    def __init__(self):
        load_env()
        self.username = os.getenv("CAR_MANAGER_ID") or os.getenv("CARMANAGER_ID")
        self.password = os.getenv("CAR_MANAGER_PW") or os.getenv("CARMANAGER_PW")

    def fetch_live_my_cars(self, timeout_sec: int = 25) -> List[Dict[str, Any]]:
        """카매니저 실계정에 로그인하여 현재 내 차량 실시간 스냅샷을 파싱하여 반환."""
        if not self.username or not self.password:
            raise ValueError("CAR_MANAGER_ID or CAR_MANAGER_PW environment variable not configured.")

        try:
            return asyncio.run(self._async_fetch_my_cars(timeout_sec=timeout_sec))
        except Exception as e:
            # DIRECTIVE 097: 과거 JSON 조용한 폴백 금지. 실패를 명시적으로 로깅하고 예외를 전파한다.
            print(f"[!] CarManagerLiveClient live fetch failed: {e}")
            raise RuntimeError(f"CarManager real-time session fetch failed: {e}") from e

    async def _async_fetch_my_cars(self, timeout_sec: int = 25) -> List[Dict[str, Any]]:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            page.on("dialog", lambda d: asyncio.create_task(d.accept()))

            # 1. 로그인
            await page.goto("https://www.carmanager.co.kr/User/Login", wait_until="networkidle", timeout=timeout_sec*1000)
            await page.fill("#userid", self.username)
            await page.fill("#userpwd", self.password)
            btn = await page.query_selector("button[onclick*='commitLogin']")
            if btn:
                async with page.expect_navigation(wait_until="networkidle", timeout=15000):
                    await btn.click()

            # 팝업 닫기
            try:
                popups = await page.query_selector_all("button:has-text('닫기'), a:has-text('닫기')")
                for popup in popups:
                    await popup.click()
            except Exception:
                pass

            # 2. 내차관리 페이지 이동
            await page.goto("https://www.carmanager.co.kr/MyPageCar/index", wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(2000)

            # 3. 실시간 매물 테이블 파싱
            cars = await page.evaluate(r'''() => {
                const rows = Array.from(document.querySelectorAll('table tbody tr'));
                const list = [];
                for (const tr of rows) {
                    const text = tr.innerText;
                    if (!text || text.includes('등록된 차량이 없습니다')) continue;
                    
                    const plateMatch = text.match(/(\d{2,3}[가-힣]\s*\d{4})/);
                    const plate = plateMatch ? plateMatch[1].replace(/\s+/g, '') : '';
                    if (!plate) continue;

                    const suggestMatch = text.match(/제시번호\s*:\s*\[?\s*(\d+)\s*\]?/);
                    const suggestNo = suggestMatch ? suggestMatch[1] : '';

                    const yearMatch = text.match(/(20\d{2})\s*년/);
                    const year = yearMatch ? yearMatch[1] : '0';

                    const mileageMatch = text.match(/([\d,]+)\s*Km/i);
                    const mileage = mileageMatch ? mileageMatch[1] : '0';

                    const priceMatch = text.match(/([\d,]+)\s*만원/);
                    const price = priceMatch ? priceMatch[1] : '0';

                    const links = Array.from(tr.querySelectorAll('a'));
                    let carSeq = '';
                    for (const a of links) {
                        const href = a.getAttribute('href') || '';
                        const onclick = a.getAttribute('onclick') || '';
                        const m = (href + onclick).match(/(\d{7,10})/);
                        if (m) {
                            carSeq = m[1];
                            break;
                        }
                    }

                    list.push({
                        plate: plate,
                        suggestNo: suggestNo,
                        year: year,
                        mileage: mileage,
                        price: price,
                        carSeq: carSeq,
                        title: text.slice(0, 100).replace(/\n/g, ' '),
                        status: text.includes('정상 광고중') ? '정상 광고중' : '매물정보부족'
                    });
                }
                return list;
            }''')

            await browser.close()
            return cars
