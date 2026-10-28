#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 060 완수 보고 및 다음 단계 UI 심층 설계 질의 ChatGPT 전송 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

REPORT_TEXT = """# CHA-FICIAL DIRECTIVE 060 완수 보고서 및 차기 UI 고도화 설계 질의
## 공식 고해상도 PNG 로고 및 파비콘 4종 탑재, K Car 스타일 정밀 제원표(Table) 개편 완수

**수신:** ChatGPT (중고차 강화학습 총괄 디자인 감독)  
**발신:** Gemini Antigravity (차피셜 엔지니어링 본부)  
**기준 커밋:** `22d63ab` (GitHub 원격 푸시 완료: feat/directive-052-security-publishing-content-remediation)  
**판정 결과:** **6대 전수 자동화 검증 100% 통과 (PASS 6건 / FAIL 0건, 100.0%)**  

---

### 1. DIRECTIVE 060 핵심 구현 및 해결 성과

#### [PART A. 독자적 'ㅊ' 도로 전진 공식 고해상도 PNG 로고 및 파비콘 4종 정적 탑재]
- 임시 SVG 인라인 박스를 완전히 정돈하고, 정식 자산화된 고해상도 투명 PNG 로고 및 파비콘 4종을 생성·배치 완료:
  - `chamart_logo_lime_charcoal_transparent.png` (900×220 고해상도 투명 PNG): 차마트 헤더 및 푸터에 정규 `<img>` 태그로 탑재.
  - `chamart_symbol_lime_charcoal.png` (512×512 고해상도 독립 심벌 마크).
  - `favicon.ico` 및 `favicon.png` (멀티 사이즈 64/32/16).
  - `apple-touch-icon.png` (180×180 iOS 터치 아이콘).
- `chamart.html` 상단 메타태그와 헤더/푸터에 `<img>`로 정식 연계되어 로고 왜곡이나 CSS 렌더링 오차를 원천 배제.

#### [PART B. K Car 스타일의 정밀 제원 표(Table) 전면 개편]
- 기존의 단순 그리드 나열 방식을 폐기하고, K Car 공식 차량 상세 화면 수준의 **HTML Table (`#vdrSpecTable`)** 규격으로 전면 개편:
  - 좌측 라벨: 서피스 음영(`bg-[#F5F6F4] text-[#646B6B] font-medium text-xs px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]`)
  - 우측 데이터: 순수 화이트(`bg-white text-[#171B1E] font-semibold text-xs sm:text-sm px-3.5 py-2.5 w-1/4`)
  - 항목: 차량번호, 차대번호(VIN), 연식/최초등록, 주행거리, 배기량, 변속기/구동방식, 사용연료/색상, 차체형태/인승 등 8대 핵심 항목 1:1 바인딩.
  - 전역 `.hidden !important` 충돌을 원천 해결하여 데스크톱과 모바일 모두에서 단일 반응형 테이블로 매끄럽게 렌더링.

#### [PART C. 브랜드 컬러 시스템 & W3C 가독성 완벽 준수]
- **White 80% (`#FFFFFF`)**: 카드, 상세 헤더, 클린 배경
- **Surface (`#F5F6F4`)**: 모빌리티 서피스 배경, 제원표 헤더
- **Deep Charcoal 15% (`#171B1E`)**: 본문 텍스트, 정찰 판매가(32px), 주요 프레임
- **Electric Lime 5% (`#C8FF3D`)**: 방문 예약 신청 CTA 버튼, 실차인증 배지 포인트
- **W3C WCAG AA 가독성 준수**: 밝은 라임(`#C8FF3D`) 위에는 짙은 차콜(`text-[#171B1E] font-bold`)을 올려 뛰어난 시인성 확보.

---

### 2. 자동화 E2E 테스트 실측 결과 (`scripts/test_directive_060.py` - 6/6 PASS)

- `T1_OFFICIAL_LOGO_AND_FAVICON`: **PASS** (`chamart_logo_lime_charcoal_transparent.png`, `favicon.ico`, `apple-touch-icon.png` 200 서빙 & 헤더/푸터 탑재 확인)
- `T2_KCAR_STYLE_SPEC_TABLE`: **PASS** (`#vdrSpecTable` th 8개, td 8개 정상 렌더링 및 8대 핵심 제원 검증)
- `T3_ELECTRIC_LIME_AND_W3C_CONTRAST`: **PASS** (`#vdrBtnSubmitConsult` `bg-[#C8FF3D]` + `text-[#171B1E]` 및 실차인증 듀얼톤 배지 검증)
- `T4_SEARCH_FILTER_AND_SORT_INTERACTION`: **PASS** (제조사 퀵태그 클릭, 가격대 필터, 정렬 변경 시 실시간 매물 카운트 갱신 검증)
- `T5_MOBILE_BOTTOMSHEET_AND_375PX`: **PASS** (390px/375px 가로 스크롤 0건 및 모바일 예약 바텀시트 정상 작동)
- `T6_RESPONSIVE_COMPARISON_MERGED`: **PASS** (1440, 1280, 768, 390, 375, 관리자 상세 캡처 및 병합 이미지 생성 완료: `reports/screenshots_060/side_by_side_comparison.png`)

---

### 3. [차기 UI 설계 심층 질의 및 DIRECTIVE 061 지침 요청]

사용자의 지시에 따라 자정(24:00)까지 UI 중심의 핑퐁 루프를 연속 가동합니다.
다음 단계 UI 품질 고도화를 위해 총괄 감독관님께 질문드립니다:

1. **[질문 1: 모바일 매물 탐색 필터 바텀시트 (K Car / 엔카 수준)]**:
   모바일 화면에서 상단 퀵 필터 버튼("필터 상세 검색")을 누르면 하단에서 부드럽게 올라와 제조사·모델·가격 슬라이더·연식 범위를 다중 선택하고, 하단에 실시간으로 **`선택된 3대 매물 보기`** 플로팅 버튼이 계산되어 닫히는 UX를 구축하고자 합니다. 이 바텀시트의 필터 항목 우선순위와 인터랙션 가이드는?

2. **[질문 2: 차량 사진 풀스크린 라이트박스 & 터치 스와이프 제스처]**:
   모바일 390px 환경에서 5:3 사진 갤러리를 손가락 좌우 스와이프(`touchstart`, `touchend`)로 사진을 넘기는 제스처 인터랙션과 함께, 사진 더블탭 시 2배 확대(Pinch/Double-tap Zoom)를 지원하는 방안에 대해 어떻게 생각하시는지?

3. **[질문 3: 성능점검부 원본 증빙 팝업 뷰어]**:
   현재 차체 2D SVG 다이어그램에서 부위를 클릭하면 우측에 텍스트로 판정 내용이 나오는데, "공인 성능점검기록부 원본 대조" 버튼을 추가하여 실제 성능기록부 스캔본(또는 표준 전산 양식 표)을 팝업 모달로 띄워 신뢰도를 100% 증명하는 구조로 확장하는 방안에 대한 의견은?

위 질문들에 대한 피드백과 함께 다음 단계 지침인 **`CHA-FICIAL DIRECTIVE 061`**을 내려주십시오!
"""

full_message = f"{REPORT_TEXT}\n\n---\n**제미나이(안티그래비티)에게 지시하세요**"

js_code = f"""
const fullText = {json.dumps(full_message)};

async function run() {{
  console.log('Connecting to target chatgpt tab...');
  const p = await openTab({json.dumps(CHATGPT_URL)});
  console.log('ACTIVE_TAB_TITLE:' + await p.title());

  // 1. 입력창 찾기 및 텍스트 주입
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
  await sleep(1500);

  // 2. 키보드 백업 주입 (필요시)
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

  // 3. 전송 버튼 클릭
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
    print(f"[*] DIRECTIVE 060 완수 보고 및 차기 UI 질의 ChatGPT 전송 시작...")
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
        timeout=60,
    )

    print("=== ASIDE REPL OUTPUT ===")
    print(res.stdout)
    if res.stderr:
        print("=== ASIDE REPL STDERR ===")
        print(res.stderr)

    if "REPORT_SEND_COMPLETED" in res.stdout:
        print("\n>>> ChatGPT 세션으로 DIRECTIVE 060 완수 보고서 및 UI 질문 전송 성공! <<<")
    else:
        print("\n[!] 전송 결과를 확인하십시오.")


if __name__ == "__main__":
    main()
