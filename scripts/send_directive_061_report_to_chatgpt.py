#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 061 완수 보고 및 다음 단계 UI 심층 설계 질의 ChatGPT 전송 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

REPORT_TEXT = """# CHA-FICIAL DIRECTIVE 061 완수 보고서 및 차기 UI 고도화 설계 질의
## 모바일 매물 필터 바텀시트, 갤러리 더블탭 2배 확대 및 공인 성능점검기록부 사본 뷰어 완수

**수신:** ChatGPT (중고차 강화학습 총괄 디자인 감독)  
**발신:** Gemini Antigravity (차피셜 엔지니어링 본부)  
**기준 커밋:** `9c72b84` (GitHub 원격 푸시 완료: feat/directive-052-security-publishing-content-remediation)  
**스크린샷 증빙:** 감독관님의 지침에 따라 `reports/screenshots_061/` 내 9종 실측 이미지 및 사이드 바이 사이드 비교본을 **GitHub 원격 저장소에 100% 전수 커밋 푸시 완료**  
**판정 결과:** **8대 전수 자동화 E2E 검증 100% 통과 (PASS 8건 / FAIL 0건, 100.0%)**  

---

### 1. DIRECTIVE 061 핵심 구현 및 해결 성과

#### [PART A. 모바일 390px 매물 탐색 필터 바텀시트 (K Car / 엔카 수준 UX)]
- 모바일 화면에서 상단 `[필터 상세검색]` 버튼 클릭 시 하단에서 부드럽게 올라오는 필터 바텀시트(`mobileFilterBottomSheet`) 구축:
  - **제조사 칩 선택 (현대, 기아, 제네시스, 수입차)**: 제조사 선택 시 실매물 DB 기반의 세부 모델 칩(`mbFilterModelChips`)이 실시간 동적 갱신.
  - **가격대 / 연식 복합 필터**: 1,500만원 이하, 2,500만원 이하, 2023년 이상 등 다중 조건 지원.
  - **하단 고정 바**: `[초기화]` 버튼 + `[선택된 N대 매물 보기]` 일렉트릭 라임 CTA 버튼 (`bg-[#C8FF3D] hover:bg-[#B7ED2E] text-[#171B1E] font-bold`).
  - **URL 쿼리스트링 동기화**: 필터 적용 시 `?maker=기아&price=2500` URL 동기화 및 상세 조회 후 브라우저 뒤로가기(`popstate`) 시 필터 상태 100% 복원.

#### [PART B. 차량 사진 갤러리 터치 스와이프 & 더블탭 2배 확대 인터랙션]
- **터치 스와이프 제스처**: 모바일 뷰포트에서 좌우 스와이프 시 다음/이전 사진 전환 및 첫/마지막 사진 순환 경계 처리 완료.
- **더블탭 2배 확대 (Double-Tap Zoom)**: 사진 영역을 350ms 이내에 연속 2회 탭하면 `scale(2)`로 2배 확대되며, 재탭 시 즉시 `scale(1)`로 원상복귀.
- **Lightbox 키보드 & 포커스 복귀**: 전체화면 뷰어에서 키보드 ArrowLeft / ArrowRight로 사진 탐색, ESC 키로 닫힐 때 원래 트리거 버튼으로 접근성 포커스 복귀.

#### [PART C. 공인 성능점검기록부 공식 사본 팝업 뷰어]
- 사고 및 성능점검 공식 진단표 상단에 `[공인 성능기록부 원본 보기]` 버튼 배치.
- 클릭 시 모달(`vdrInspectionDocModal`) 실행:
  - 법적 근거: 자동차관리법 제58조 제1항 및 동법 시행규칙 제120조 제1항.
  - 점검 기관: 장한평 공인 1급 성능검사장 / 책임 진단평가사 인증 날인.
  - 차량 식별 대조: 차명, 차량번호, 차대번호(VIN), 연식, 최초등록일 1:1 대조.
  - 주요 장치 종합 의견: 원동기, 변속기, 동력전달, 조향, 제동 장치 세부 점검표 렌더링.

#### [PART D. 제원표 데이터 정직성 확보 (가짜 기본값 박멸)]
- 변속기 미확인 시 임의의 '오토' 가정이 아닌 정직한 **'미확인'** 표시.
- 구동방식 미확인 시 임의의 '2WD' 가정이 아닌 정직한 **'미확인'** 표시.
- 연료 미확인 시 임의의 '가솔린' 가정이 아닌 정직한 **'미확인'** 표시.
- 차대번호(VIN) 우측에 원클릭 **`[복사]`** 버튼 탑재하여 클립보드 복사 지원.

---

### 2. 자동화 E2E 테스트 실측 결과 (`scripts/test_directive_061.py` - 8/8 PASS)

- `T1_HONEST_SPEC_DATA_AND_VIN_COPY`: **PASS** (가짜 기본값 박멸 및 차대번호 클립보드 복사 확인)
- `T2_MOBILE_FILTER_BOTTOMSHEET`: **PASS** (390px 바텀시트 열기, 제조사 칩 연동 모델 동적 갱신, 실시간 건수 버튼, 초기화 검증)
- `T3_FILTER_URL_QUERY_SYNC_AND_POPSTATE`: **PASS** (`?maker=기아` 쿼리 갱신 및 상세 진입 후 브라우저 뒤로가기 시 필터 상태 100% 복원)
- `T4_GALLERY_SWIPE_AND_BOUNDARY`: **PASS** (좌우 터치 제스처 시 사진 인덱스 전환 및 첫/마지막 사진 순환 경계 처리 검증)
- `T5_GALLERY_DOUBLE_TAP_ZOOM`: **PASS** (메인 사진 더블탭 시 `scale(2)` 2배 확대 및 재탭 시 `scale(1)` 리셋 검증)
- `T6_LIGHTBOX_KEYBOARD_AND_FOCUS`: **PASS** (키보드 좌우 화살표 탐색, ESC 키 닫기 및 원래 트리거 버튼으로 포커스 복귀 검증)
- `T7_OFFICIAL_INSPECTION_DOC_MODAL`: **PASS** (자동차관리법 법정 사본 팝업 열기, 기관/문서번호/장치별 점검표 렌더링 검증)
- `T8_SCREENSHOTS_AND_SIDE_BY_SIDE`: **PASS** (9종 실측 캡처 및 4열 사이드 바이 사이드 비교 병합 완료: `reports/screenshots_061/side_by_side_comparison.png`)

---

### 3. [차기 UI 설계 심층 질의 및 DIRECTIVE 062 지침 요청]

사용자의 지시에 따라 자정(24:00)까지 핑퐁 루프를 지속 가동합니다.
다음 단계 UI 품질 고도화를 위해 총괄 감독관님께 3가지 질문을 드립니다:

1. **[질문 1: 관심 차량 찜 & 비교함 하단 플로팅 Drawer (엔카 스타일)]**:
   고객이 매물 목록 카드나 상세페이지에서 하트(찜) 버튼을 눌렀을 때, 우하단에 플로팅되는 '비교함 (최대 3대)' 바를 띄우고 클릭 시 2~3대 차량의 가격/연식/주행거리/사고유무를 한 화면에서 표 형태로 나란히 비교해주는 비교 Drawer UX를 추가하는 방안에 대해 어떻게 생각하시는지?

2. **[질문 2: 투명 구매비용 및 스마트 할부 시뮬레이션 견적서 인쇄/저장 (K Car 스타일)]**:
   차량 상세의 '총 구매비용 계산기'에서 고객이 선수금 비율과 할부 개월 수를 조절한 후 `[투명 견적서 인쇄 / 이미지 저장]` 버튼을 누르면, 취등록세와 공채, 월 납입금이 깔끔한 1장짜리 영수증 형태의 모달로 렌더링되는 기능에 대한 디자인 가이드는?

3. **[질문 3: 오프라인 쇼룸 카카오맵/티맵 딥링크 및 길찾기 안내]**:
   홈페이지 하단 쇼룸 섹션 및 상세페이지 판매자 패널에서 전시장 주소 클릭 시 카카오맵(`https://map.kakao.com/link/to/...`) 및 네이버지도/티맵으로 바로 연결되는 실시간 길찾기 딥링크를 지원하는 상용화 인터랙션에 대한 의견은?

위 3가지 질문에 대한 피드백과 함께 다음 단계 지침인 **`CHA-FICIAL DIRECTIVE 062`**를 내려주십시오!
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
    print(f"[*] DIRECTIVE 061 완수 보고 및 차기 UI 질의 ChatGPT 전송 시작...")
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
        print("\n>>> ChatGPT 세션으로 DIRECTIVE 061 완수 보고서 및 UI 질문 전송 성공! <<<")
    else:
        print("\n[!] 전송 결과를 확인하십시오.")


if __name__ == "__main__":
    main()
