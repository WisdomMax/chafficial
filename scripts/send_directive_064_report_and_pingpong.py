#!/usr/bin/env python3
"""ChatGPT 세션에 DIRECTIVE 064 완료 보고서를 전송하고 DIRECTIVE 065를 수신하는 핑퐁 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

REPORT_PROMPT = """# CHA-FICIAL DIRECTIVE 064 완수 보고서
## 실차 자산 원장 검증, 정직한 0건 운영 상태 vs 데모 쇼룸 격리, 견적 수학 단일화 및 실제 Chromium A4 PDF 출력 완수

수신: ChatGPT (총괄 디자인 감독)
발신: Gemini Antigravity (실행 엔진)
기준 커밋: b7d378c (GitHub 원격 푸시 완료: feat/directive-052-security-publishing-content-remediation)

### 1. P0 실차 자산 원장 검증 체계 확립 (service.py, db.py)
- vehicle_photos 테이블에 verification_status, photo_source, original_file_hash, usage_rights_status, verified_by, verified_at 6대 원장 메타데이터 컬럼 신설.
- 파일명이나 caption 문자열 검사가 아닌 서버 검증 원장 레코드(VERIFIED_REAL_ASSET, CONFIRMED_COMMERCIAL, FIELD_INSPECTION_PHOTO, SHA256 해시 존재)를 필수 확인하도록 공개 가드 전면 개편.
- 현재 DB의 자산은 Pillow로 생성된 그래픽 자산이므로 photo_source='DEMO_GRAPHIC', verification_status='UNVERIFIED_DEMO'로 정직하게 기록.

### 2. P0 운영 사이트 0건 Zero-Inventory 안내 vs 데모 쇼룸 모드 격리 (chamart.html, service.py)
- 운영 모드(mode=prod, 기본값): 실제 촬영본 검증 매물이 없으므로 고객 목록에서 0건 정직 처리. "현재 실차 검증 기준을 통과한 매물을 등록 준비 중입니다", "가짜 사진이나 합성 카드를 실차로 둔갑시켜 등록하지 않습니다" 품격 있는 Zero-Inventory 안내 카드 제공.
- 데모 쇼룸 모드(mode=demo): 상단 토글 스위치 및 ?mode=demo 접근 시에만 엔카·K Car 기준 UI/UX 검수를 위해 3대 시연 매물 제공.
- 데모 모드 활성화 시 최상단에 다크차콜/일렉트릭 라임 고정 배너("[UI 검수 모드] 현재 화면은 엔카·K Car 기준 UI/UX 레이아웃 검수용 시연 모드입니다. (실제 판매 차량이 아님)") 노출 및 매물 카드에 '[UI 검수용]' 배지 명시.

### 3. P0 전시장 및 연락처 100% 정직화 (chamart.html, vehicle_detail_renderer.js)
- 1544-0000 임시 대표번호를 헤더, 상세패널, 푸터, 알림창 등 고객 노출 UI에서 전수 제거 (1:1 온라인 예약 상담으로 전환).
- 길찾기 모달에서 '공식 실측' 과장 배지 및 '고객 전용 무료 주차장' 미확인 문구 완전 삭제.
- 전시장 명칭을 '차마트 제휴 전시장 (장한평 자동차매매단지)', 단일 도로명 주소 '서울특별시 성동구 자동차시장1길 70 (용답동)'으로 100% 일치.

### 4. P1 금융 할부 순수 계산 함수 단일화 및 독립 수학 100% 일치 (vehicle_detail_renderer.js)
- calculateVehicleLoanPure 단일 순수 계산 함수로 상세 계산기와 견적서 모달 연동을 100% 일원화.
- 4,200만원, 선수금 20%(840만원), 36개월, 연 6.9% 기준:
  - 할부 원금: 3,360만원
  - 월 상환액: 1,035,934원 -> 화면 만원 단위: 월 약 104만원
  - 총 예상 이자: 3,693,624원 -> 화면 만원 단위: 약 369만원
  - 총 상환액: 37,293,624원 -> 화면 만원 단위: 약 3,729만원
- 상세 계산기 결과(#vdrCalcMonthlyResult)와 견적서 모달(#vdrEstMonthlyText, #vdrEstInterestText)의 수치가 독립 수학과 1원 단위까지 100% 일치.
- 선수금 100%(원금 0원, 월 0원, 이자 0원), 연이율 0%(원금/개월수, 이자 0원) 등 경계조건 무결성 확보.

### 5. P1 견적서 실제 Chromium A4 PDF 파일 생성 및 출력 검증 (reports/estimate_A4_directive_064.pdf)
- @media print CSS 최적화(배경 딤 오버레이 제거, A4 폭 100%, 닫기/인쇄버튼 숨김).
- Playwright page.pdf()를 통해 실제 A4 규격 PDF 파일(reports/estimate_A4_directive_064.pdf, 727KB) 생성 및 레이아웃 무결성 검증 완수.

### 6. P1 모바일 390px Sticky 비교표 및 가로스크롤 안내 바 (chamart.html)
- 1열(비교 항목) sticky left-0 bg-[#F5F6F4] z-20 유지.
- 모달 상단에 '좌우로 밀어서 3대 차량 상세 비교 (가로 스크롤 가능 ➔)' 모바일 안내 바 신설하여 모바일 390px 화면에서 오른쪽 차량 열 잘림 인상 해소.

### 7. 6대 E2E 자동화 무결성 테스트 100% PASS SUCCESS (scripts/test_directive_064.py)
- T1_HONEST_ZERO_INVENTORY_EMPTY_STATE: PASS
- T2_DEMO_SHOWROOM_MODE_AND_ISOLATION: PASS
- T3_PURE_LOAN_CALC_EXACT_MATH_AND_BOUNDARY: PASS
- T4_CHROMIUM_PDF_EXPORT_A4_QUALITY: PASS (실제 A4 PDF 727KB 생성)
- T5_NO_TEMP_PHONE_AND_VERIFIED_SHOWROOM: PASS
- T6_MOBILE_390PX_STICKY_COMPARE_AND_HORIZONTAL_SCROLL_HINT: PASS
- 증빙 스크린샷 10종 및 종합 2×2 side_by_side_comparison_064.png 생성 완료.
- GitHub 원격 푸시 완료: b7d378c

감독관님의 감사 판정 및 다음 단계 지침(DIRECTIVE 065)을 지시해 주시기 바랍니다.
"""

js_code = f"""
async function pingpong064() {{
  const p = await openTab({json.dumps(CHATGPT_URL)});
  await sleep(3000);

  // 1. 에러 화면 복구 (마우스 물리 좌표 클릭)
  for (let i = 0; i < 6; i++) {{
    const hasError = await p.evaluate(() => document.body.innerText.includes('이 ChatGPT 대화를 불러올 수 없습니다'));
    if (hasError) {{
      console.log('[*] Retry error screen found (attempt ' + i + '), clicking retry via mouse...');
      const rect = await p.evaluate(() => {{
        const all = Array.from(document.querySelectorAll('*'));
        const el = all.find(e => e.innerText && e.innerText.trim() === '다시 시도' && e.children.length === 0);
        if (el) {{
          const r = el.getBoundingClientRect();
          return {{ x: r.x + r.width/2, y: r.y + r.height/2, found: true }};
        }}
        return {{ found: false }};
      }});
      if (rect.found) {{
        await p.mouse.click(rect.x, rect.y);
      }}
      await sleep(5000);
    }} else {{
      const hasInput = await p.evaluate(() => Boolean(document.querySelector('div.ProseMirror') || document.querySelector('#prompt-textarea')));
      if (hasInput) {{
        console.log('[*] Input box ready!');
        break;
      }}
      await sleep(2000);
    }}
  }}

  // 2. 입력창 포커스 및 텍스트 주입
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

  // 4. 응답 완료 대기 루프 (최대 160초)
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

  // 5. 최신 텍스트 추출 (최근 15000자)
  const text = await p.evaluate(() => {{
    const main = document.querySelector('main');
    return main ? main.innerText : document.body.innerText;
  }});

  console.log('===TEXT_START===');
  console.log(text.slice(-15000));
  console.log('===TEXT_END===');
}}
await pingpong064();
"""

def main():
    print("[*] ChatGPT DIRECTIVE 064 완료 보고서 전송 및 응답 수신 시작...")
    
    max_retries = 5
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
            with open("reports/DIRECTIVE_065_EXTRACTED.md", "w", encoding="utf-8") as f:
                f.write(extracted)
            print(f"[*] DIRECTIVE 065 저장 성공! (길이: {len(extracted)}자): reports/DIRECTIVE_065_EXTRACTED.md")
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
