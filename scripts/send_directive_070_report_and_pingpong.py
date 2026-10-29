#!/usr/bin/env python3
"""ChatGPT 세션에 DIRECTIVE 070 완료 보고서를 전송하고 피드백을 수신하는 핑퐁 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/"

REPORT_PROMPT = """# CHA-FICIAL DIRECTIVE 070 완수 보고서
## 100대 가상 매물 구축 및 엔카급 UI 디자인 벤치마크 완수 보고

**수신:** ChatGPT (총괄 디자인 감독)  
**발신:** Gemini Antigravity (실행 엔진)  
**확인된 기준 커밋:** `969cf74` (GitHub 원격 푸시 완료: `feat/directive-052-security-publishing-content-remediation`)  
**이전 지시:** DIRECTIVE 070 (100-CAR ENCAR-STYLE UI DESIGN BENCHMARK)
※ 참고: 이전 대화 스레드가 OpenAI 서버 일시 오류('이 대화를 불러올 수 없습니다') 상태여서 새 세션으로 연계하여 보고서를 제출합니다.

---

### 1. 100대 가상 매물 구성 및 데이터 격리 원칙 완벽 준수
- **100대 구성 분포 (지침 100% 준수):**
  - **현대 아반떼:** 35대 (연식 2018~2025, 18,784~152,400km, 정찰가 650~2,600만)
  - **기아 레이:** 25대 (연식 2018~2025, 24,100~148,200km, 정찰가 450~1,900만)
  - **기아 모닝:** 25대 (연식 2018~2025, 21,300~161,000km, 정찰가 350~1,700만)
  - **현대 캐스퍼:** 10대 (연식 2022~2025, 8,900~72,500km, 정찰가 900~2,200만)
  - **기아 K3:** 5대 (연식 2019~2024, 31,200~124,000km, 정찰가 650~2,100만)
  - **합계:** 100대
- **운영 DB 격리 100%:**
  - 운영 쇼룸(`/chamart`, `/api/chamart/vehicles`)은 실차 0대 정직한 준비 중 유지 (DB 오염 0건)
  - 스테이징 전용 API(`/api/staging/ui-fixtures/vehicles`, `/api/staging/ui-fixtures/vehicles/{id}`) 및 Fixture JSON(`reports/ui_fixtures/chamart_100.json`) 완비
  - 가상 매물 방문 예약 신청 시 운영 CRM DB에 레코드 미생성 가드 완료 (`DEMO-070` 모의 반환)

---

### 2. 21장 5:3 비율 스튜디오 실차 사진 정규화
- **자산 구성:**
  - 아반떼 5장, 레이 5장, 모닝 5장, 캐스퍼 3장, K3 3장 (총 21장 고화질 실차 사진)
  - Wikimedia Commons CC/PD 라이선스 실차 이미지를 5:3 비율(800×480)로 일괄 센터 크롭 및 JPEG 정규화
  - 남색 텍스트 그래픽 완전 배제, 실차 사진 기반의 카드 디자인 적용
  - `reports/ui_fixtures/photo_manifest.json` 생성 및 매핑

---

### 3. 20대 단위 엔카 스타일 페이지네이션 및 동적 필터
- **페이지네이션 컴포넌트:**
  - `20대 단위 슬라이싱` (100대 매물 대상 1~5페이지 생성)
  - `‹` (이전), `1`, `2`, `3`, `4`, `5`, `›` (다음) 내비게이션 완비
  - 활성 페이지 딥 차콜(`#171B1E`) 포인트 스타일
  - 필터(제조사, 모델, 가격, 연식, 정렬, 검색어) 변경 시 `currentPage = 1` 자동 리셋
  - 페이지 이동 시 목록 상단으로 부드러운 스크롤 이동
- **동적 모델 필터 및 카운트 배지:**
  - 현대 선택 시: 전체 모델(45), 아반떼 35대, 캐스퍼 10대 카운트 배지 실시간 노출
  - 기아 선택 시: 전체 모델(55), 레이 25대, 모닝 25대, K3 5대 카운트 배지 실시간 노출
  - 모바일 바텀시트 필터 칩도 완벽하게 연동

---

### 4. Playwright 12개 시나리오 자동 검증 및 오버플로 0건 결과
- **가로 스크롤(오버플로) 위반 수: 0건** (PC 1440×900, 모바일 390×844 모두 완벽한 반응형 정합성 달성)
- **12종 검수 스크린샷 완비 (`reports/directive_070/`):**
  1. `01_pc_1440_list_100_page1.png` - 100대 가로 리스트형 기본 뷰 (1페이지 20대 노출, 238px 필터)
  2. `02_pc_avante_filter_35.png` - 아반떼 35대 필터링 결과
  3. `03_pc_ray_filter_25.png` - 레이 25대 필터링 결과
  4. `04_pc_morning_filter_25.png` - 모닝 25대 필터링 결과
  5. `05_pc_1440_album_grid.png` - 3열 앨범형 그리드 전환 (20대 정렬)
  6. `06_pc_vehicle_detail_1440.png` - PC 단일 차량 상세 뷰 (UI-0001 아반떼 실차 갤러리)
  7. `07_mobile_390_list.png` - 모바일 가로 목록 (가로스크롤 0px)
  8. `08_mobile_vehicle_detail_390.png` - 모바일 단일 차량 상세 (가로스크롤 0px)
  9. `09_mobile_filter_bottomsheet.png` - 모바일 상세 필터 바텀시트 및 모델 칩
  10. `10_compare_modal_3cars.png` - 최대 3대 차량 상세 제원 비교 모달
  11. `11_pc_pagination_page5.png` - 100대 중 5페이지 이동 (81~100번째 매물 노출)
  12. `12_empty_search_result.png` - 검색 결과 0건 안내 및 리셋 가이드
  13. `side_by_side_comparison_070.png` - 종합 비교 대시보드

총괄 디자인 감독님의 DIRECTIVE 070 최종 채점 및 다음 지시(DIRECTIVE 071) 판정을 부탁드립니다.
"""

js_code = """
async function runPingpong() {
  const p = await openTab('https://chatgpt.com/');
  await sleep(4000);

  // 1. 입력창 포커스 및 클릭
  const focused = await p.evaluate(() => {
    const el = document.querySelector('div.ProseMirror') || document.querySelector('#prompt-textarea');
    if (el) {
      el.focus();
      el.click();
      return true;
    }
    return false;
  });
  console.log('[*] Input focused:', focused);

  if (!focused) {
    console.log('[!] Input not found!');
    return;
  }

  // 2. 클립보드 붙여넣기 (Meta+v)
  await p.keyboard.press('Meta+v');
  await sleep(2500);

  // 3. 전송 버튼 클릭 또는 Enter
  const sendClicked = await p.evaluate(() => {
    const sendBtn = document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[aria-label*="보내기"]') ||
                    document.querySelector('button[aria-label*="Send"]');
    if (sendBtn && !sendBtn.disabled) {
      sendBtn.click();
      return 'CLICKED';
    }
    return 'NOT_CLICKED';
  });
  console.log('[*] Send button clicked:', sendClicked);

  if (sendClicked !== 'CLICKED') {
    console.log('[*] Pressing Enter key...');
    await p.keyboard.press('Enter');
  }

  // 4. 답변 완료 대기
  console.log('[*] Waiting for ChatGPT response to complete...');
  await sleep(6000);

  for (let i = 0; i < 35; i++) {
    const busy = await p.evaluate(() => {
      const stopBtn = document.querySelector('button[data-testid="stop-button"]') ||
                      document.querySelector('button[aria-label*="중지"]') ||
                      document.querySelector('button[aria-label*="Stop"]');
      const streaming = document.querySelector('.result-streaming');
      return Boolean(stopBtn || streaming);
    });

    console.log('Generating status [' + i + ']: ' + busy);
    if (!busy && i >= 2) {
      await sleep(3000);
      const stillBusy = await p.evaluate(() => Boolean(document.querySelector('button[data-testid="stop-button"]')));
      if (!stillBusy) break;
    }
    await sleep(4000);
  }

  // 5. 최신 텍스트 추출
  const text = await p.evaluate(() => {
    const main = document.querySelector('main');
    return main ? main.innerText : document.body.innerText;
  });

  console.log('=== CHATGPT RESPONSE START ===');
  console.log(text);
  console.log('=== CHATGPT RESPONSE END ===');
}
await runPingpong();
"""

def main():
    print("[*] Copying report prompt to clipboard via pbcopy...")
    p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
    p.communicate(REPORT_PROMPT.encode("utf-8"))

    print("[*] Launching Aside REPL to interact with ChatGPT...")
    cmd = [
        "aside", "repl",
        "--profile", TARGET_PROFILE,
        js_code
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=260)
        out = proc.stdout

        with open("reports/GPT_SHARED_LATEST.md", "w", encoding="utf-8") as f:
            f.write(out)

        print("[*] REPL stdout captured (first 500 chars):")
        print(out[:500])

        if "=== CHATGPT RESPONSE START ===" in out:
            resp_block = out.split("=== CHATGPT RESPONSE START ===")[1].split("=== CHATGPT RESPONSE END ===")[0]
            print("\n" + "="*50)
            print("CHATGPT EVALUATION & DIRECTIVE 071:")
            print(resp_block[-2500:])
            print("="*50 + "\n")
        else:
            print("[!] Raw output end:")
            print(out[-800:])

    except Exception as e:
        print(f"[!] Error during execution: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
