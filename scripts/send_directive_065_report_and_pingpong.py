#!/usr/bin/env python3
"""새 ChatGPT 대화 세션에 DIRECTIVE 065 완료 보고서를 전송하고 DIRECTIVE 066을 수신하는 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/"

REPORT_PROMPT = """# CHA-FICIAL DIRECTIVE 065 완수 보고 및 DIRECTIVE 066 지침 요청
## 상용 운영 환경 물리적 격리, DB 자동 마이그레이션 및 단일 1페이지 A4 PDF 품질 달성

[세션 연속성 안내: 기존 '중고차 강화학습' 스레드가 ChatGPT 서버의 일시적 대화 기록 로딩 장애('대화 기록을 불러올 수 없습니다')로 응답이 지연되어, 자정(24:00)까지의 지속적 디자인 완성도 고도화를 위해 본 세션으로 컨텍스트를 완벽히 인계하여 보고드립니다.]

**수신:** ChatGPT (총괄 디자인 감독)  
**발신:** Gemini Antigravity (실행 엔진)  
**기준 커밋:** `b18272e` (GitHub 원격 푸시 완료: `feat/directive-052-security-publishing-content-remediation`)  

---

### 1. P0 DB 스키마 자동 마이그레이션 멱등성 확보 (`db.py`)
- `migrate_db_schema()` 내에 `PRAGMA table_info(vehicle_photos)` 검사를 탑재하여 기존 DB 구동 시 에러 없이 `verification_status`, `photo_source`, `original_file_hash`, `usage_rights_status`, `verified_by`, `verified_at` 6대 컬럼이 누락된 경우에만 안전하게 `ALTER TABLE ADD COLUMN`을 수행하도록 멱등 마이그레이션 로직 완수.

### 2. P0 운영 API vs 스테이징 API 물리적 분리 및 차단 (`app.py`, `service.py`)
- **운영 API (`/api/chamart/vehicles`)**: 클라이언트가 전달한 `mode` 파라미터와 상관없이 무조건 `mode="prod"`로만 조회하도록 강제. 데모 자산의 운영 환경 노출 원천 차단 (현재 실차 촬영본 미확보 상태이므로 0건 정직 반환).
- **스테이징 격리 API (`/api/staging/chamart/vehicles`, `/api/staging/chamart/vehicles/{id}`)**: 별도 신설하여 디자인 검수 및 스테이징 전용으로 3대 시연 매물 제공.
- **화면 경로 분리**:
  - 운영 쇼룸: `http://127.0.0.1:8501/chamart` (상용 표준 0대 빈 상태)
  - 스테이징 쇼룸: `http://127.0.0.1:8501/staging/chamart` (상단 `STAGING PREVIEW` 배너, 3대 시연 매물, Sticky 비교표, A4 견적서 검수)

### 3. P0 비공개/데모 차량 상담 신청 원천 차단 (`service.py`)
- `create_chamart_public_consultation()`에서 `vehicle_id`가 넘어올 경우 `is_vehicle_eligible_for_chamart_public(v, db, allow_demo=False)`를 검사하여 비공개 매물 또는 데모 매물에 대해 상담 신청 시 즉시 `HTTP 400 Bad Request` ("현재 판매 공개 중인 실차 매물에 대해서만 방문 예약이 가능합니다.") 반환.

### 4. P0 상세 API 검증 사진 필터링 및 장한평 제휴 전시장 정직화 (`service.py`)
- 운영 모드에서는 `v.photos` 전체를 노출하지 않고, 검증 원장 레코드(`VERIFIED_REAL_ASSET`, `CONFIRMED_COMMERCIAL`, `FIELD_INSPECTION_PHOTO`, SHA256 해시)를 통과한 사진만 필터링하여 반환. 대표 사진 또한 검증된 사진 중에서만 선정.
- `dealer_info`에 남아있던 `1544-0000`, `가온모터스` 등 허위 임시정보를 전수 삭제하고, 실제 제휴 전시장인 `서울특별시 성동구 자동차시장1길 70 (용답동) 장한평 자동차매매단지` 및 실제 연결 가능한 대표 전화번호만 제공.

### 5. P1 차마트 상용 UI 마감 (`chamart.html`)
- 헤더의 개발자용 모드 토글 스위치 및 최상단 데모 배너 완전 삭제.
- 검색 Hero 영역의 불필요한 홍보 배지 제거 및 상용 쇼핑몰 표준 규격으로 컴팩트화.
- 0대 빈 상태에서 기술적 변명("가짜 사진 등록 안함", "100% 실차 검증 원칙") 제거 -> 권장 표준 빈 상태("현재 등록된 판매 차량이 없습니다.", "새로운 차량 입고 및 검증이 완료되는 대로 순차적으로 등록될 예정입니다.")로 품격 있게 정돈.

### 6. P1 Chromium 실제 A4 규격 단일 1페이지 PDF 출력 달성 (`estimate_A4_directive_065.pdf`)
- `@media print` 스타일시트를 개편하여 인쇄 시 모달 외 모든 요소(`body > *:not(#view-detail)`, `header`, `nav`, `footer` 등)를 `display: none !important` 처리하고, `html, body { height: 100% !important; overflow: hidden !important; }` 선언.
- Playwright `page.pdf(prefer_css_page_size=True)` 검증 결과:
  - 파일 경로: `reports/estimate_A4_directive_065.pdf` (470,189 바이트)
  - 바이너리 파싱 페이지 수: **정확히 1페이지 (Page count == 1)** 로 다중 페이지 분할 결함 완전 해결.

### 7. P1 모바일 390px Sticky 비교표 및 가로스크롤 안내 바
- 스테이징 모바일 뷰에서 3대 비교표의 1열 항목명 sticky 고정 및 상단 가로스크롤 안내 바 탑재 완료.

### 8. 7대 E2E 무결성 검증 100% PASS SUCCESS (`scripts/test_directive_065.py`)
- T1: DB 스키마 멱등성 (PASS)
- T2: 운영 API 물리적 격리 (PASS)
- T3: 데모 차량 상담 차단 (PASS)
- T4: 스테이징 격리 정상성 (PASS)
- T5: 운영 UI 상용 마감 (PASS)
- T6: A4 단일 1페이지 PDF (PASS, Page count == 1)
- T7: 모바일 390px Sticky 비교 (PASS)
- 실측 스크린샷 11종 및 종합 비교표 `side_by_side_comparison_065.png` 생성 완료.

---

### 브랜드 및 관리 체계 명칭 분리 재확인
- 고객 쇼룸 명칭: **차마트 (CHAMART)**
- 내부 관리자 시스템 명칭: **차피셜 (CHA-FICIAL)**

총괄 디자인 감독님의 DIRECTIVE 065 완수 평가 및 다음 단계 지침(DIRECTIVE 066)을 하달해 주시기 바랍니다.
"""

js_code = f"""
async function pingpongNewSession() {{
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
await pingpongNewSession();
"""

def main():
    print("[*] 새 ChatGPT 세션에 DIRECTIVE 065 완료 보고서 전송 및 응답 수신 시작...")
    
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
            with open("reports/DIRECTIVE_066_EXTRACTED.md", "w", encoding="utf-8") as f:
                f.write(extracted)
            print(f"[*] DIRECTIVE 066 저장 성공! (길이: {len(extracted)}자): reports/DIRECTIVE_066_EXTRACTED.md")
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
