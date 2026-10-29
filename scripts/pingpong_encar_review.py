#!/usr/bin/env python3
"""ChatGPT 세션에 엔카 기준 개편 완수 보고서를 전송하고 검사 및 다음 지침을 수신하는 핑퐁 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/"

REPORT_PROMPT = """# CHA-FICIAL DIRECTIVE 068 완수 및 엔카(Encar) 표준 UI/UX 2단 레이아웃 전면 개편 종합 검사 보고서

**수신:** ChatGPT (총괄 디자인 감독)  
**발신:** Gemini Antigravity (실행 엔진)  
**기준 브랜치:** `feat/directive-052-security-publishing-content-remediation`  
**현재 로컬 서버:** `http://localhost:8501` (정상 가동 중)  

---

### 1. 사용자 핵심 요청 및 개편 배경
- 사용자 지침:
  > "우리는 엔카랑 지금은 그 발끝에도 못미침... 디자인 수준이.. 그리고 거의 비슷한 구조와 스타일로 가야함.. 사람들이 엔카에 익숙해서 그게 우리한테도 유리함. 포인트 색만 우리 스타일로 하고... 엔카 사이트 디자인 구조 확인해서 니가 해봐."
  > "이거 다하고 나면 GPT될테니깐 가서 검사 해달라고 해봐.. 핑퐁 1시간만 더해"
- 이에 따라 대한민국 중고차 소비자가 가장 친숙한 **엔카(Encar.com) 공식 2025/2026 표준 인터페이스 구조와 사용성**을 차마트(CHAMART)에 전면 이식하고, 차마트 고유의 금융/진단 신뢰 브랜드 컬러 시스템을 정립하였습니다.

---

### 2. 엔카 공식 표준 2단 레이아웃 및 핵심 UX 전면 이식 완료 내역

1. **엔카 시그니처 2단 분할 레이아웃 (`lg:grid lg:grid-cols-12 gap-7`)**:
   - PC 기준 최대 폭 1280px 규격 완벽 준수.
   - **좌측 3컬럼 (약 270px) 정밀 다단계 사이드 필터**:
     - 구분: 국산차 / 수입차 원클릭 탭
     - 제조사: 등록 매물 수 집계 배지가 연동된 동적 아코디언 (전체 3, 현대 1, 기아 2 등)
     - 모델명: 제조사 선택 시 하위 모델 리스트 조건부 노출
     - 가격대: 전체, ~1,500만, ~2,500만, ~3,500만, 3,500만원 초과 퀵버튼
     - 최소 연식: 전체, 2024년 이후, 2022년 이후, 2020년 이후 퀵버튼
     - 연료: 전체, 가솔린, 하이브리드, 디젤, 전기 태그 버튼
     - 안심 진단: 무사고 진단 매물 필터링 체크박스
     - 상단 헤더: 원클릭 필터 전체 초기화(rotate-ccw) 버튼
   - **선택된 필터 태그 칩 바 (Applied Filter Chips)**:
     - 선택된 모든 조건이 에메랄드 뱃지 칩(`[국산차 ×]`, `[현대 ×]`)으로 표출되며 개별 [×] 클릭 또는 전체 해제 지원.

2. **엔카 뷰 모드 전환 기능 (`[⊞ 앨범형 그리드]` vs `[☰ 리스트형 와이드 목록]`)**:
   - 상단 컨트롤 바에서 앨범형과 리스트형 뷰를 1클릭으로 양방향 실시간 전환:
     - **[⊞ 앨범형]**: 엔카 공식 5:3 비율 대형 실차 사진 카드, 시야를 침범하지 않는 우상단 찜(하트) 버튼, 차종/트림 볼드 타이포그래피, 무사고/성능점검부 태그, 볼드 정찰 판매가, 3대 비교 체크박스.
     - **[☰ 리스트형]**: 엔카식 와이드 가로 행 레이아웃 (좌측 220px 5:3 실차 사진 + 중앙 상세 스펙 및 차량번호 + 우측 굵은 정찰가, 비교, 찜, 상세보기 버튼).

3. **우측 플로팅 퀵바 (Quick Floating Bar)**:
   - 비교함(실시간 선택 대수 연동), 관심 차량 찜 카운트 위젯, 최상단 스크롤(TOP) 버튼을 스티키 위젯으로 상시 제공.

4. **브랜드 컬러 시스템 전면 쇄신 (안티-AI 템플릿 정체성 확립)**:
   - AI 생성물 느낌을 주던 촌스러운 네온 라임(`#C8FF3D`) 11건 전수 박멸 완료.
   - 차마트 고유의 **딥 틸/에메랄드 (`#176B68`, `#247D7C`)** 및 **럭셔리 다크 네이비 (`#101A2A`, `#152B3C`)**로 교체하여 수입 인증중고차 수준의 정갈함과 신뢰감 확보.

5. **태블릿 및 모바일 반응형 결함 원천 해결**:
   - 기존 커스텀 `.hidden { display: none !important; }`가 Tailwind의 반응형 접두사(`lg:block`, `sm:flex`)를 무력화하던 문제를 발견하고 완전 제거.
   - 태블릿(1024px) 구간 2열 그리드(`xl:grid-cols-3`) 및 `whitespace-nowrap`, `shrink-0` 적용으로 가격 및 비교/상세 버튼 줄바꿈/쪼개짐 원천 차단.

6. **운영 쇼룸과 스테이징 쇼룸의 정직한 격리 원칙 100% 준수**:
   - 운영 쇼룸(`http://localhost:8501/chamart`): 오직 승인된 실차만 노출 (`/api/chamart/vehicles`). 실차가 0대일 때 허위 매물 없이 "실차 검증 입고 준비 중입니다" 에메랄드 쉴드 배너 정직 표출.
   - 스테이징 쇼룸(`http://localhost:8501/staging/chamart`): 3대 시연 매물 기반 엔카식 2단 레이아웃 제공.
   - `scripts/test_boundary_matrix_067.py`: P0 혼합 데이터 경계 검증 100% ALL PASS 재입증 완료.

---

### 3. 실측 시각 증거 자료 안내 (`reports/`)
1. **종합 6분할 비교 대시보드 원본**: `reports/encar_design_showcase_dashboard.png` (2520 × 2630 픽셀)
   - [1] PC 1440px 앨범형 그리드 (5:3 실차 사진 + 좌측 270px 정밀 다단계 필터 + 우측 퀵바)
   - [2] PC 1440px 리스트형 와이드 보기 (엔카 가로목록 뷰 스위처 동작)
   - [3] PC 1440px 실차 상세 페이지 (5:3 대형 갤러리 + 딥 틸/네이비 디자인 시스템)
   - [4] 태블릿 1024px 반응형 뷰 (2열 여유 그리드 + 글자 쪼개짐 원천 차단)
   - [5] 모바일 390px 콤팩트 뷰 (원클릭 필터 시트 + 1열 단일 카드)
   - [6] 운영 쇼룸 1440px (미입고 시 '실차 검증 입고 준비 중' 정직한 안내 및 격리 원칙)
2. **개별 실측 화면 캡처 원본**:
   - `reports/encar_1440_staging_grid.png`
   - `reports/encar_1440_staging_list.png`
   - `reports/encar_1280_staging.png`
   - `reports/encar_1440_detail_fixed.png`
   - `reports/encar_1024_staging.png`
   - `reports/encar_390_staging_mobile.png`
   - `reports/encar_1440_production_clean.png`

---

총괄 디자인 감독님의 엔카 기준 개편 작업 종합 검사 판정 및 추가 보완/개선 지침(DIRECTIVE 069)을 하달해 주시기 바랍니다.
"""

def run_pingpong():
    print("=================================================================")
    print("  ChatGPT 세션에 엔카 기준 개편 완수 보고서 전송 및 응답 수신")
    print("=================================================================")

    js_code = f"""
async function sendReport() {{
  const p = await openTab({json.dumps(CHATGPT_URL)});
  await sleep(4000);

  // 1. 입력창 대기 및 포커스
  let focused = false;
  for (let t = 0; t < 10; t++) {{
    focused = await p.evaluate(() => {{
      const el = document.querySelector('div.ProseMirror') || document.querySelector('#prompt-textarea');
      if (el) {{
        el.focus();
        return true;
      }}
      return false;
    }});
    if (focused) break;
    await sleep(1000);
  }}
  console.log('[*] Input box focused:', focused);

  if (!focused) {{
    console.log('[!] Input box not found!');
    return;
  }}

  // 2. 텍스트 입력
  await p.keyboard.insertText({json.dumps(REPORT_PROMPT)});
  await sleep(2000);

  // 3. 전송 버튼 클릭
  const sendRes = await p.evaluate(() => {{
    const sendBtn = document.querySelector('button[data-testid=\"send-button\"]') ||
                    document.querySelector('button[data-testid=\"fruitjuice-send-button\"]') ||
                    document.querySelector('button[aria-label*=\"보내기\"]') ||
                    document.querySelector('button[aria-label*=\"Send\"]');
    if (sendBtn && !sendBtn.disabled) {{
      sendBtn.click();
      return 'CLICKED';
    }}
    return 'NO_BTN_OR_DISABLED';
  }});
  console.log('[*] Send button status:', sendRes);

  if (sendRes !== 'CLICKED') {{
    console.log('[*] Pressing Enter key fallback...');
    await p.keyboard.press('Enter');
  }}

  // 4. 응답 완료 대기 루프 (최대 180초)
  console.log('[*] Waiting for ChatGPT response generation...');
  await sleep(8000);

  for (let i = 0; i < 45; i++) {{
    const isGenerating = await p.evaluate(() => {{
      const stopBtn = document.querySelector('button[data-testid=\"stop-button\"]') ||
                      document.querySelector('button[aria-label*=\"중지\"]') ||
                      document.querySelector('button[aria-label*=\"Stop\"]');
      const streaming = document.querySelector('.result-streaming');
      return Boolean(stopBtn || streaming);
    }});

    console.log('Generating status [' + i + ']: ' + isGenerating);
    if (!isGenerating && i >= 3) {{
      await sleep(4000);
      const stillBusy = await p.evaluate(() => Boolean(document.querySelector('button[data-testid=\"stop-button\"]')));
      if (!stillBusy) break;
    }}
    await sleep(4000);
  }}

  // 5. 최신 텍스트 추출
  const text = await p.evaluate(() => {{
    const main = document.querySelector('main');
    return main ? main.innerText : document.body.innerText;
  }});

  console.log('===TEXT_START===');
  console.log(text.slice(-15000));
  console.log('===TEXT_END===');
}}
await sendReport();
"""

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"[*] 시도 {attempt}/{max_retries}...")
        res = subprocess.run(
            ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
            capture_output=True,
            text=True,
            check=False,
            timeout=360
        )
        stdout = res.stdout
        stderr = res.stderr

        if "===TEXT_START===" in stdout and "===TEXT_END===" in stdout:
            extracted = stdout.split("===TEXT_START===")[1].split("===TEXT_END===")[0].strip()
            with open("reports/DIRECTIVE_069_EXTRACTED.md", "w", encoding="utf-8") as f:
                f.write(extracted)
            print(f"[*] GPT 응답 수신 및 저장 성공! (길이: {len(extracted)}자): reports/DIRECTIVE_069_EXTRACTED.md")
            return 0
        else:
            print(f"[!] 시도 {attempt} 파싱 실패 (stdout: {len(stdout)}자, stderr: {len(stderr)}자)")
            if stderr:
                print("    STDERR 요약:", stderr[:250].replace('\n', ' '))
            if attempt < max_retries:
                print("    5초 후 재시도합니다...")
                time.sleep(5)

    print("[!] 모든 재시도 실패")
    return 1

if __name__ == "__main__":
    sys.exit(run_pingpong())
