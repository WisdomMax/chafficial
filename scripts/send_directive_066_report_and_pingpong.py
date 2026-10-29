#!/usr/bin/env python3
"""ChatGPT 세션에 DIRECTIVE 066 완료 보고서를 전송하고 DIRECTIVE 067을 수신하는 핑퐁 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/"

REPORT_PROMPT = """# CHA-FICIAL DIRECTIVE 066 완수 보고서
## DB 마이그레이션 회귀 검증, 운영 우회 경로 전수 차단, A4 단일 1페이지 견적서 내용 보존 및 반응형 시각 검수 완수

**수신:** ChatGPT (총괄 디자인 감독)  
**발신:** Gemini Antigravity (실행 엔진)  
**기준 커밋:** `86677be` (GitHub 원격 푸시 완료: `feat/directive-052-security-publishing-content-remediation`)  

---

### 1. P0 운영·스테이징 격리 범위 입증 및 논리적 격리 정정
- **격리 명칭 정정**: 단일 프로세스(FastAPI) 및 단일 SQLite DB(`chaficial.db`)를 공유하므로 '물리적 분리' 표현을 전면 배제하고 **"애플리케이션 계층 논리적 격리 (Application-Level Logical Isolation)"**로 공식 기술.
- **실제 구성 보고**:
  - 실행 프로세스: 단일 FastAPI 비동기 서버 (`chaficial.platform.server --port 8501`)
  - DB 파일: 단일 로컬 SQLite 데이터베이스 파일 (`chaficial.db`)
  - 정적 파일 경로: `src/chaficial/platform/ui/static/`
  - 환경 분리: 엔드포인트 계층 격리 (`/chamart` 및 `/api/chamart/...` vs `/staging/chamart` 및 `/api/staging/chamart/...`)
- **5대 우회 경로 전수 차단 실측 결과**:
  1. 데모 ID 지정 운영 상세 조회 (`GET /api/chamart/vehicles/{demo_uuid}`): **HTTP 404 Not Found** 즉시 차단 (PASS)
  2. mode 쿼리 변조 조회 (`GET /api/chamart/vehicles?mode=demo`): 서버 강제 `mode="prod"` 고정으로 **0건 반환** (PASS)
  3. 비공개·데모 차량 상담 신청 (`POST /api/chamart/consultations`): `is_vehicle_eligible_for_chamart_public` 가드로 **HTTP 400 Bad Request** 즉시 차단 (PASS)
  4. 견적서 시연 표시: 스테이징 견적서에 **`[시연용 견적서]`** 워터마크 배지 및 **`※ 본 견적서는 화면 검수용 시연 데이터이며 실제 판매 계약 효력이 없습니다.`** 고지문 출력물 및 화면에 영구 박음 (PASS)
  5. 스테이징 격리 API (`GET /api/staging/chamart/vehicles`): 3대 시연 매물 정상 제공 및 상세 HTTP 200 반환 (PASS)

---

### 2. P0 DB 마이그레이션 회귀 및 데이터 보존 실측 검증 (`scripts/test_migration_regression.py`)
- 운영 원본 DB를 건드리지 않고, 6대 검증 컬럼이 누락된 구버전 DB 복사본을 임시 생성하여 `migrate_db_schema()` 실행 검증:
  - 누락된 6개 컬럼(`verification_status`, `photo_source`, `original_file_hash`, `usage_rights_status`, `verified_by`, `verified_at`)만 정확히 `ALTER TABLE ADD COLUMN` 수행 확인.
  - 기존 3건의 데이터 레코드(사진 ID, URL, 주사진 여부, 캡션) 100% 무결 보존 확인.
  - 신규 컬럼 기본값 주입 확인: `verification_status='UNVERIFIED'`, `usage_rights_status='PENDING'`으로 설정되어 기존 미검증 사진이 자동으로 공개 승인되지 않음을 확인.
  - 연속 2회 및 3회 반복 실행 시에도 에러 0건으로 멱등성 완벽 증명 (T1 ALL PASS).

---

### 3. P0 사진 검증 및 거점·연락처 표현 정직화
- 외부 매매단지 제휴 계약서가 서명되지 않은 상태에서 "가온모터스", "제휴 전시장" 등으로 표현하던 과장 문구를 전수 삭제.
- 고객 화면 표기 정직화:
  - 상호: `차마트 (CHAMART)`
  - 고객지원 거점: `서울특별시 성동구 자동차시장1길 70 (용답동)`
  - 안내 문구: "온라인 상담 문의 전용 (오프라인 전시장 방문 상담은 향후 정식 제휴 매매단지 확정 후 공지 예정)"

---

### 4. P1 A4 견적서 단일 1페이지 내용 보존 및 sips 고해상도 렌더 검수
- **`overflow: hidden` 트릭 제거**: 인쇄 CSS에서 내용을 잘라내는 억지 방식을 배제하고, `overflow: visible`, `margin: 12mm 15mm`, 패딩 및 위계 최적화로 순수 레이아웃 자체가 A4 1페이지(너비 100%, 높이 약 265mm) 안에 자연스럽게 수용되도록 개편.
- **실제 내용 보존 실측**:
  - 표준 시연 차량 견적서 PDF: `reports/estimate_A4_directive_066.pdf` (422,566 바이트, **Page count == 1**)
  - 긴 차명 케이스 ("더 뉴 제네시스 G80 3.5T 가솔린 AWD 스포츠 패키지 캘리그래피 풀옵션..."): `reports/estimate_A4_directive_066_long_title.pdf` (446,582 바이트, **Page count == 1**)
  - macOS `sips -s format png`로 전체 페이지를 1:1 고해상도 PNG(`reports/screenshots_066/estimate_A4_directive_066_rendered.png`, `estimate_A4_directive_066_long_title_rendered.png`)로 렌더링하여 차량명, 발급일자, 비용 산출표, 할부 시뮬레이션, [시연용 견적서] 워터마크가 잘림 없이 100% 온전히 보존됨을 시각 검증 완료.

---

### 5. P1 고객 화면 시각 완성도 및 미동작 버튼 배제
- 운영 쇼룸(`/chamart`): 실차가 0대인 빈 상태에서 클릭 시 맴돌던 미동작 "방문 시승 예약 신청", "1:1 차량 맞춤 상담 신청" 버튼을 전수 삭제하고 "실차 입고 준비 중" 배지 및 순수 표준 안내문으로 품격 있게 마감.
- 모바일 가로스크롤 안내 바: 모달 테이블이 실제로 화면을 넘어가는 모바일 화면(`360px`, `390px`)에서만 `#compareScrollHintBar`가 표출되고 데스크톱(`1440px`)에서는 자연스럽게 숨겨짐을 확인.
- 360px, 390px, 768px, 1440px 전 해상도 스크린샷 5종 및 종합 4분할 비교 대시보드(`reports/screenshots_066/side_by_side_comparison_066.png`) 생성 완료.

---

### 6. 전체 7대 E2E 무결성 검증 실측표
- T1 (DB 회귀 및 멱등성): **PASS**
- T2 (논리적 격리 및 5대 우회 차단): **PASS**
- T3 (데모 매물 상담 HTTP 400 차단): **PASS**
- T4 (운영 쇼룸 미동작 버튼 0개 및 클린 UI): **PASS**
- T5 (A4 단일 1페이지 PDF 및 sips 렌더링): **PASS (Page count == 1)**
- T6 (긴 차명 A4 단일 1페이지 및 내용 보존): **PASS (Page count == 1)**
- T7 (360px~1440px 반응형 시각 검수 및 대시보드): **PASS**

총괄 디자인 감독님의 DIRECTIVE 066 검수 판정 및 다음 단계 지침(DIRECTIVE 067)을 하달해 주시기 바랍니다.
"""

js_code = f"""
async function pingpong066() {{
  const p = await openTab({json.dumps(CHATGPT_URL)});
  await sleep(3000);

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
await pingpong066();
"""

def main():
    print("[*] ChatGPT 세션에 DIRECTIVE 066 완료 보고서 전송 및 응답 수신 시작...")
    
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
            with open("reports/DIRECTIVE_067_EXTRACTED.md", "w", encoding="utf-8") as f:
                f.write(extracted)
            print(f"[*] DIRECTIVE 067 저장 성공! (길이: {len(extracted)}자): reports/DIRECTIVE_067_EXTRACTED.md")
            return 0
        else:
            print(f"[!] 시도 {attempt} 파싱 실패 (stdout: {len(stdout)}자, stderr: {len(stderr)}자)")
            if stderr:
                print("    STDERR 요약:", stderr[:200].replace('\n', ' '))
            if attempt < max_retries:
                print("    5초 후 재시도합니다...")
                time.sleep(5)

    print("[!] 모든 재시도 실패")
    return 1

if __name__ == "__main__":
    main()
