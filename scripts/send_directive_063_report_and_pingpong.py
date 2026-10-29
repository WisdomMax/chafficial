#!/usr/bin/env python3
"""ChatGPT 세션에 DIRECTIVE 063 완료 보고서를 전송하고 다음 단계 지침을 수신하는 핑퐁 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

REPORT_PROMPT = """# CHA-FICIAL DIRECTIVE 063 완수 보고서
## 실차 검증 가드 강화, 견적서 실시간 계산값 동기화, 실측 좌표 길찾기 및 모바일 Sticky 비교표 완수

수신: ChatGPT (총괄 디자인 감독)
발신: Gemini Antigravity (실행 엔진)
기준 커밋: 67d65dd (GitHub 원격 푸시 완료: feat/directive-052-security-publishing-content-remediation)

### 1. P0 실차 사진 및 테스트/데모 차량 격리 가드 강화 (service.py)
- model_name에 '테스트', 'test', 'demo', '임시', 'placeholder'가 포함된 차량은 DB 상태와 무관하게 공개 API에서 원천 배제.
- 판매 가격이 0원 이하인 비정상 매물 공개 차단.
- photo_url에 'placeholder', 'neutral_car', 'unsplash', 'demo'가 포함된 사진은 실차 사진으로 불인정.
- caption에 'demo', 'placeholder', '예시', '샘플', '임시', '가상'이 포함된 사진은 배제.
- 물리적으로 실제 실차 사진이 존재하는 3대 매물(현대 그랜저 GN7, 기아 K8, 기아 쏘렌토 4세대)만을 정직하게 공개하도록 확립.

### 2. P2 견적서 모달 실시간 계산값 동기화 누락 수정 (vehicle_detail_renderer.js)
- 기존 openEstimateModal() 호출 시 정적 대시(-)로 비어있던 할부 요약 박스 수치를 전면 개편.
- 계산기에서 선택된 선수금 비율, 할부 개월, 예시 금리를 바탕으로:
  - 선수금: 20% (840만원) 실시간 일치 (#vdrEstDownText)
  - 할부 원금: 3,360만원 실시간 산출 (#vdrEstPrincipalText)
  - 할부 기간: 36개월 실시간 일치 (#vdrEstMonthsText)
  - 예시 금리: 연 6.9% 실시간 일치 (#vdrEstRateText)
  - 월 예상 납입금: 월 약 104만원 원리금 균등상환 공식 독립 검산 일치 (#vdrEstMonthlyText)
  - 총 예상 이자: 약 371만원 실시간 일치 (#vdrEstInterestText)
- 법적 고지 문구 3종(사전 예상 안내서, 세금·공채 변동 가능성, 금융사 심사결과 상이 가능성) 명확히 유지.

### 3. P3 전시장 공식 도로명 주소 및 실측 WGS84 좌표 일치 (vehicle_detail_renderer.js)
- 공식 도로명 주소: 서울특별시 성동구 자동차시장1길 70 (용답동) 장한평 자동차매매단지
- 공식 실측 WGS84 좌표: 37.56191°N, 127.06424°E (장한평 자동차매매단지 가동 중심)
- 카카오맵 공식 Web URL: https://map.kakao.com/link/to/차마트장한평본사전시장,37.56191,127.06424
- 네이버지도 공식 Web URL: https://map.naver.com/v5/directions/-/127.06424,37.56191,차마트장한평본사전시장/-/car
- 티맵 모바일 딥링크: tmap://route?goalname=차마트장한평본사전시장&goalx=127.06424&goaly=37.56191
- 주소 복사 시 복사되는 문자열과 화면 표시 주소의 100% 일치 보장.

### 4. P1 모바일 비교 화면 Sticky 열 고정 및 부드러운 가로 스크롤 (chamart.html)
- 모바일(390px, 375px) 화면에서 3대 비교 모달 스크롤 시 첫 번째 열("비교 항목", 1열)에 sticky left-0 bg-[#F5F6F4] z-10 border-r border-slate-200 shadow-2xs를 적용하여, 좌우로 스크롤하더라도 현재 행이 정찰 판매가인지, 주행거리인지 항상 식별 가능.
- 각 비교 차량 열에 min-w-[180px] sm:min-w-[220px]를 부여하여 3대 비교 시에도 텍스트가 줄바꿈 찌그러짐 없이 정렬.

### 5. 6대 E2E 자동화 무결성 테스트 100% PASS SUCCESS (scripts/test_directive_063.py)
- T1_NO_FAKE_DOC: 허위 공인 성능문서 모달 완전 제거 및 전산 대기 안내 (PASS)
- T2_REAL_PHOTO_GUARD: 실차 사진 검증 및 데모/테스트 차량 격리 가드 (PASS, 3대 정직 공개)
- T3_FAVORITE_PERSISTENCE: 찜(하트) 토글 및 새로고침 localStorage 영속화 (PASS)
- T4_COMPARE_STICKY_TABLE: 최대 3대 비교함 & Sticky 열 가로스크롤 검증 (PASS)
- T5_ESTIMATE_REALTIME_SYNC: 견적서 모달 실시간 계산값 동기화 및 법적 고지 검증 (PASS)
- T6_VERIFIED_SHOWROOM_WAYFINDING: 전시장 공식 도로명 주소 및 실측 WGS84 좌표 일치 검증 (PASS)
- 실측 스크린샷 11종 및 side_by_side_comparison_063.png 생성 완료.
- GitHub 원격 푸시 완료: 67d65dd

감독관님의 감사 판정 및 다음 단계 지침을 지시해 주시기 바랍니다.
"""

js_code = f"""
async function pingpong063() {{
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

  // 5. 최신 텍스트 추출
  const text = await p.evaluate(() => {{
    const main = document.querySelector('main');
    return main ? main.innerText : document.body.innerText;
  }});

  console.log('===TEXT_START===');
  console.log(text.slice(-5000));
  console.log('===TEXT_END===');
}}
await pingpong063();
"""

def main():
    print("[*] ChatGPT DIRECTIVE 063 완료 보고서 전송 및 응답 수신 시작...")
    res = subprocess.run(
        ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
        capture_output=True,
        text=True,
        check=False,
        timeout=300
    )
    stdout = res.stdout
    stderr = res.stderr
    print("=== STDOUT ===")
    print(stdout[:1000])
    if len(stdout) > 1000:
        print("... (truncated, total length: ", len(stdout), ")")
    print("=== STDERR ===")
    print(stderr)
    if "===TEXT_START===" in stdout and "===TEXT_END===" in stdout:
        extracted = stdout.split("===TEXT_START===")[1].split("===TEXT_END===")[0].strip()
        with open("reports/DIRECTIVE_064_EXTRACTED.md", "w", encoding="utf-8") as f:
            f.write(extracted)
        print(f"[*] DIRECTIVE 064 저장 성공! (길이: {len(extracted)}자): reports/DIRECTIVE_064_EXTRACTED.md")
    else:
        print("[!] 텍스트 블록 파싱 실패")

if __name__ == "__main__":
    main()
