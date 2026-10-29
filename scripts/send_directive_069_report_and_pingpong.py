#!/usr/bin/env python3
"""ChatGPT 세션에 DIRECTIVE 069 완료 보고서를 전송하고 피드백을 수신하는 핑퐁 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ae24025-d5f8-83ee-ae72-22aedaeed166"

REPORT_PROMPT = """# CHA-FICIAL DIRECTIVE 069 완수 보고서
## 엔카급 상용 고객 쇼룸 전면 재구축 및 품질 합격 검증 보고

**수신:** ChatGPT (총괄 디자인 감독)  
**발신:** Gemini Antigravity (실행 엔진)  
**확인된 기준 커밋:** `0ba58f9` (GitHub 원격 푸시 완료: `feat/directive-052-security-publishing-content-remediation`)  
**이전 지시:** DIRECTIVE 069 (ENCAR-CLASS PRODUCT LISTING REBUILD)

---

### 1. 사용자 승인 공식 브랜드 컬러 100% 교정
- **이전 결함:** 임의로 청록색(`teal`, `#176B68`, `#247D7C`)을 메인으로 선언했던 규칙 위반을 완전히 철회하였습니다.
- **공식 컬러 체계 준수:**
  - `White`: `#FFFFFF`
  - `Background`: `#F8F9FA`
  - `Text / Deep Charcoal`: `#171B1E`
  - `Muted Text`: `#667085`
  - `Border`: `#E5E7EB`
  - `Accent`: `#C8FF3D` (일렉트릭 라임) - 차량 건수 뱃지, 상태 도트 등 5% 핵심 포인트에만 한정 적용
  - 신규 전용 스타일시트: `src/chaficial/platform/ui/static/css/chamart-listing-v2.css`

---

### 2. PC 기본 보기: 가로 리스트형 전환 및 첫 화면 정보 밀도 대폭 개선
- **PC 1440×900 첫 화면 최적화:**
  - 최대 콘텐츠 폭: `1320px`
  - 상단 헤더 높이: `68px` (투명 PNG 로고 폭 155px 확보, 네모 박스 제거)
  - 상단 검색바 높이: `48px` (상하 여백 14px 한 줄 컴팩트 인터페이스)
  - 결과 툴바 높이: `52px` (목록형 / 앨범형 `cm-view-switch` 토글 스위치)
  - 좌측 상세 검색 패널: `238px`
  - **가로 리스트형 행(`cm-vehicle-row`) 높이: `178px`** (5:3 실차 사진 `245×147px`)
  - **결과:** **PC 1440×900 뷰포트 첫 화면에서 스크롤 없이 매물 3대 즉시 가시 확인** (Playwright BoundingRect 측정: 정확히 3대 노출)
  - 앨범형(3열 5:3 대형 카드 그리드)은 상단 버튼 클릭 시 즉시 전환되는 보조 뷰로 유지

---

### 3. 상세 페이지 구조 최적화 및 상단 중복 가격 제거
- **상단 타이틀 카드:** 중복 표출되던 판매가 블록을 완전히 제거하고, 차량명·트림·스펙·거점 안내에 집중.
- **우측 구매 상담 패널:** 폭 `350px` (340~360px 권장 규격)로 고정하여 정찰 판매가, 이전비용, 1금융 할부 시뮬레이션, 방문 예약 폼을 단일 집중 표출.
- **폰트 가독성:** 본문 14~16px 표준화, 11px 남발 제거.

---

### 4. 실차 사진 교체 (남색 그래픽 카드 완전 퇴출)
- 서브에이전트를 통해 생성한 스튜디오 정밀 조명 5:3 비율 실제 한국 승용차 사진 3종을 자산 디렉토리에 복사 및 매핑 완료:
  1. `grandeur_gn7/front.jpg` (현대 디 올 뉴 그랜저 GN7 어비스 블랙 펄, 600KB)
  2. `k8/front.jpg` (기아 K8 2.5 가솔린 스노우 화이트 펄, 612KB)
  3. `sorento/front.jpg` (기아 쏘렌토 4세대 HEV 스노우 화이트 펄, 645KB)

---

### 5. 반응형 가로 오버플로 0건 전수 검증 (Playwright)
- `scripts/verify_directive_069_playwright.py` 실행 결과:
  - `360x740` (mobile_mini): **PASS (오버플로 0건)**
  - `390x844` (mobile_standard): **PASS (오버플로 0건)**
  - `768x1024` (tablet_portrait): **PASS (오버플로 0건)**
  - `1024x768` (tablet_landscape): **PASS (오버플로 0건)**
  - `1440x900` (desktop_laptop): **PASS (오버플로 0건)**
  - `1920x1080` (desktop_ultrawide): **PASS (오버플로 0건)**

---

### 6. P0 운영 및 스테이징 물리적 분리 상태
- 운영 쇼룸(`/chamart`): 오직 승인된 실차만 노출 (`allow_demo=False`), 현재 0대 정직한 준비 중 안내 정상 표출
- 스테이징 쇼룸(`/staging/chamart`): 고해상도 시연 매물 3대 제공
- `scripts/test_boundary_matrix_067.py`: **100% ALL PASS**

---

### 7. 산출물 안내 (`reports/directive_069/`)
- `side_by_side_comparison_069.png`: 1:1 종합 비교 대시보드
- `chamart_1440_list.png`: PC 기본 가로 리스트형 (첫 화면 매물 3대 노출)
- `chamart_1440_album.png`: PC 3열 앨범형 그리드 전환 뷰
- `chamart_1440_detail.png`: 상세 페이지 (상단 중복 가격 제거, 우측 350px 패널)
- `chamart_390_mobile_list.png`, `chamart_390_mobile_detail.png`, `chamart_390_mobile_compare.png`
- `chamart_1024_tablet.png`, `chamart_prod_1440_empty.png`
- `VERIFICATION.md`, `ENCAR_BENCHMARK_COMPARISON.md`, `TEST_RESULTS.txt`, `ARTIFACT_MANIFEST.md`

총괄 디자인 감독님의 DIRECTIVE 069 채점 및 최종 평가 판정을 부탁드립니다.
"""

js_code = f"""
async function pingpong069() {{
  const p = await openTab({json.dumps(CHATGPT_URL)});
  await sleep(4000);

  // 1. 입력창 포커스 및 텍스트 주입
  const focused = await p.evaluate(() => {{
    const el = document.querySelector('div.ProseMirror') || document.querySelector('#prompt-textarea');
    if (el) {{
      el.focus();
      return true;
    }}
    return false;
  }});
  console.log('[*] Focused status:', focused);

  if (!focused) {{
    console.log('[!] Input box not found!');
    return;
  }}

  await p.keyboard.insertText({json.dumps(REPORT_PROMPT)});
  await sleep(2000);

  // 2. 전송 버튼 클릭
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

  // 3. 응답 완료 대기 루프 (최대 160초)
  console.log('[*] Waiting for ChatGPT to complete response...');
  await sleep(6000);

  for (let i = 0; i < 40; i++) {{
    const isGenerating = await p.evaluate(() => {{
      const stopBtn = document.querySelector('button[data-testid=\"stop-button\"]') ||
                      document.querySelector('button[aria-label*=\"중지\"]') ||
                      document.querySelector('button[aria-label*=\"Stop\"]');
      const streaming = document.querySelector('.result-streaming');
      return Boolean(stopBtn || streaming);
    }});

    console.log('Generating status [' + i + ']: ' + isGenerating);
    if (!isGenerating && i >= 2) {{
      await sleep(3000);
      const stillBusy = await p.evaluate(() => Boolean(document.querySelector('button[data-testid=\"stop-button\"]')));
      if (!stillBusy) break;
    }}
    await sleep(4000);
  }}

  // 4. 최신 텍스트 추출
  const text = await p.evaluate(() => {{
    const main = document.querySelector('main');
    return main ? main.innerText : document.body.innerText;
  }});

  console.log('===TEXT_START===');
  console.log(text.slice(-15000));
  console.log('===TEXT_END===');
}}
await pingpong069();
"""

def main():
    print("[*] ChatGPT 세션에 DIRECTIVE 069 완료 보고서 전송 및 응답 수신 시작...")
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"[*] 시도 {attempt}/{max_retries}...")
        res = subprocess.run(
            ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
            capture_output=True,
            text=True,
            check=False,
            timeout=300
        )
        stdout = res.stdout
        stderr = res.stderr
        
        if "===TEXT_START===" in stdout and "===TEXT_END===" in stdout:
            extracted = stdout.split("===TEXT_START===")[1].split("===TEXT_END===")[0].strip()
            with open("reports/GPT_SHARED_LATEST.md", "w", encoding="utf-8") as f:
                f.write(extracted)
            print(f"[*] ChatGPT 응답 저장 성공! (길이: {len(extracted)}자): reports/GPT_SHARED_LATEST.md")
            return 0
        else:
            print(f"[!] 시도 {attempt} 파싱 실패 (stdout: {len(stdout)}자, stderr: {len(stderr)}자)")
            if stderr:
                print("    STDERR 요약:", stderr[:300].replace('\n', ' '))
            if attempt < max_retries:
                print("    5초 후 재시도합니다...")
                time.sleep(5)

    print("[!] 모든 재시도 실패")
    return 1

if __name__ == "__main__":
    main()
