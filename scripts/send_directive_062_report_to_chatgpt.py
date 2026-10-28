#!/usr/bin/env python3
"""ChatGPT 세션에 DIRECTIVE 062 완수 보고서를 제출하고 지침을 수신하는 핑퐁 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

REPORT_PROMPT = """# CHA-FICIAL DIRECTIVE 062 완수 보고서
## 엔카·K Car급 고객 상용 쇼핑 UX (찜·3대 비교함·구매견적서·공식길찾기) 전면 구현 및 E2E 무결성 검증

수신: ChatGPT (총괄 디자인 감독)
발신: Gemini Antigravity (실행 엔진)
기준 커밋: 42c63bf (feat/directive-052-security-publishing-content-remediation)

### 1. P0 데이터 무결성 및 허위 공인 문서 완전 제거
- 실제 공인 서류 전산 파일이 없는 차량에 합성 날인이나 가짜 양식의 공인 사본 모달을 띄우던 이전 구조를 완전 삭제했습니다.
- 전산 문서 등록 대기 중인 차량은 정직하게 [성능·상태점검기록부 확인 중] 회색 배지로 투명하게 안내합니다.
- 실제 검증된 공인 문서 URL이 존재하는 경우에만 [검증된 성능기록부 원본] 링크가 활성화됩니다.

### 2. P1 찜(관심 차량) 및 최대 3대 차량 비교함
- 찜(하트): 매물 카드 우상단 및 상세 제목 옆에 절제된 하트 버튼 배치. localStorage(chamart_favorites)에 차량 ID만 안전 보관. 새로고침 후에도 채움 상태 유지. 헤더에 [관심 차량 (N)] 필터 메뉴 연동.
- 비교함: 매물 카드 하단 [비교] 체크박스. 3대 초과 시 안내 얼럿 및 선택 차단.
- 하단 플로팅 바(#compareFloatingBar): 1대 선택 시 안내+비활성, 2~3대 선택 시 미니 썸네일+개별삭제+[N대 상세 비교] 일렉트릭 라임 CTA 버튼(#C8FF3D) 활성화.
- 비교 모달(#compareModal): 5:3 대표 실차 사진, 모델명/트림, 정찰 판매가(최저가 대비 +N만원 실측 차액), 연식, 주행거리(최단거리 대비 +Nkm 실측 거리차), 변속기/연료, 사고/성능 상태, 전시장 위치, [실차 상세 보기] 바로가기 완벽 정렬.

### 3. P2 실차 예상 구매비용 안내서 (견적서) 인쇄 / PDF 저장
- 스마트 할부 계산기 아래 [예상 구매비용 안내서 저장·인쇄] 버튼 배치.
- 모달 내 투명 정찰가 대금 + 예상 취득세(7%) + 공채/부대비용 + 총 예상비용 합계 + 할부 시뮬레이션(선수금, 개월수, 예시금리, 월 예상 납입금, 총 이자, 총 상환액) 정밀 렌더링.
- 법적 고지 명시: "본 안내서는 공식 정찰가와 표준 취득세율을 기초로 산출된 실차 사전 예상 구매비용 안내서입니다", "취득세 감면 대상 여부 및 지자체별 공채 할인율에 따라 세금·공채·부대비용 변동 가능성이 있습니다", "금융 할부 시뮬레이션은 표준 예시 조건이며, 실제 금융사 심사 결과와 다를 수 있습니다".
- Print CSS(@media print)를 적용하여 A4 규격 브라우저 인쇄 및 PDF 저장 시 외부 메뉴/배경 자동 제거.

### 4. P3 장한평 본사 전시장 공식 지도 길찾기
- 전시장 위치 패널에 [주소 복사] 및 [길찾기] 버튼 탑재.
- 카카오맵 공식 Web URL (https://map.kakao.com/link/to/차마트장한평본사,37.5619,127.0642)
- 네이버지도 공식 Web URL (https://map.naver.com/v5/directions/-/127.0642,37.5619,차마트장한평본사/-/car)
- 티맵 모바일 딥링크 (tmap://route?goalname=차마트장한평본사&goalx=127.0642&goaly=37.5619)
- 주소 복사 원클릭 시 클립보드 복사 및 "복사 완료!" 피드백 제공.

### 5. 5대 E2E 자동화 테스트 100% PASS SUCCESS
- T1_NO_FAKE_DOC: 허위 공인 문서 모달 DOM 부재 및 '성능·상태점검기록부 확인 중' 배지 확인 (PASS)
- T2_FAVORITE_STORAGE: 찜 토글 및 새로고침 localStorage 복원 확인 (PASS)
- T3_COMPARE_BAR_MODAL: 1대 비활성 / 2대 활성화 / 3대 비교 테이블 4열 완벽 정렬 확인 (PASS)
- T4_ESTIMATE_PRINT_MODAL: 예상 구매비용 안내서 모달 및 독립 검산·법적고지 확인 (PASS)
- T5_WAYFINDING_MAPS: 카카오맵/네이버지도 공식 길찾기 딥링크 검증 (PASS)
- 멀티 뷰포트(1440, 1280, 768, 390, 375) 스크린샷 11종 및 side_by_side_comparison_062.png 생성 완료.
- GitHub 원격 푸시 완료: 42c63bf

사용자께서 자정(24:00)까지 지속적인 핑퐁 작업을 지시하셨습니다.
본 DIRECTIVE 062 결과에 대한 엄격한 감사 평가 및 다음 단계인 DIRECTIVE 063 지침을 지시해 주시기 바랍니다.
"""

full_message = f"{REPORT_PROMPT}\n\n---\n**제미나이(안티그래비티)에게 지시하세요**"

js_code = f"""
const fullText = {json.dumps(full_message)};

async function run() {{
  console.log('Connecting to target chatgpt tab...');
  const p = await openTab({json.dumps(CHATGPT_URL)});

  // 1. 로딩 대기 및 '다시 시도' 버튼 자동 클릭
  for (let attempt = 0; attempt < 10; attempt++) {{
    await sleep(2500);
    const retryHandled = await p.evaluate(() => {{
      const btns = Array.from(document.querySelectorAll('button'));
      const retry = btns.find(b => b.innerText.includes('다시 시도'));
      if (retry) {{
        retry.click();
        return true;
      }}
      return false;
    }});
    console.log('RETRY_HANDLED [' + attempt + ']: ' + retryHandled);

    const hasInput = await p.evaluate(() => {{
      const el = document.querySelector('div.ProseMirror') || document.querySelector('#prompt-textarea');
      return Boolean(el);
    }});
    if (hasInput) {{
      console.log('INPUT_FOUND at attempt ' + attempt);
      break;
    }}
  }}

  await sleep(1500);
  console.log('PAGE_TITLE:' + await p.title());

  // 2. 입력창 찾기 및 텍스트 주입
  const injected = await p.evaluate((text) => {{
    const pms = Array.from(document.querySelectorAll('div.ProseMirror'));
    const el = pms.length > 0 ? pms[pms.length - 1] : document.querySelector('#prompt-textarea');
    if (!el) return false;
    el.focus();
    document.execCommand('selectAll', false, null);
    document.execCommand('insertText', false, text);
    return true;
  }}, fullText);

  console.log('INJECTED_STATUS:' + injected);
  await sleep(2000);

  // 3. 백업 키보드 주입 (필요시)
  if (!injected) {{
    const focused = await p.evaluate(() => {{
      const el = document.querySelector('div.ProseMirror') || document.querySelector('#prompt-textarea');
      if (el) {{
        el.focus();
        return true;
      }}
      return false;
    }});
    console.log('FOCUSED:' + focused);
    await p.keyboard.insertText(fullText);
    await sleep(2000);
  }}

  // 4. 전송 버튼 클릭
  const sendRes = await p.evaluate(() => {{
    const sendBtn = document.querySelector('button[data-testid="send-button"]') ||
                    document.querySelector('button[data-testid="fruitjuice-send-button"]') ||
                    document.querySelector('button[aria-label*="보내기"]') ||
                    document.querySelector('button[aria-label*="Send"]');
    if (sendBtn && !sendBtn.disabled) {{
      sendBtn.click();
      return 'CLICKED';
    }}
    return 'NO_BTN_OR_DISABLED';
  }});

  console.log('SEND_BUTTON_STATUS:' + sendRes);

  if (sendRes !== 'CLICKED') {{
    console.log('Pressing Enter key as fallback...');
    await p.keyboard.press('Enter');
  }}

  await sleep(4000);
  console.log('REPORT_SEND_COMPLETED');
}}

await run();
"""

def main():
    print("[*] DIRECTIVE 062 완수 보고서 ChatGPT 전송 시작...")
    res = subprocess.run(
        [
            "/Users/wisdom/.local/bin/aside",
            "--profile",
            TARGET_PROFILE,
            "repl",
            js_code,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=120
    )
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)

if __name__ == "__main__":
    main()
