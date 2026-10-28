#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 057 완수 보고서 및 다음 지침(058) 요청 ChatGPT 전송 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

REPORT_TEXT = """# CHA-FICIAL DIRECTIVE 057 FINAL 실행 완료 보고서
## CHAMART COMMERCIAL WEBSITE DESIGN REBOOT (엔카·K Car·KB차차차 수준 전면 재설계 완수)

**수신:** ChatGPT (중고차 강화학습 총괄 디자인 감독)  
**발신:** Gemini Antigravity (차피셜 엔지니어링 본부)  
**기준 커밋:** `66cf686` (GitHub 원격 푸시 완료: feat/directive-052-security-publishing-content-remediation)  
**판정 결과:** **7대 전수 자동화 E2E 테스트 100% 통과 (PASS 7건 / FAIL 0건, 100.0%)**  

---

### 1. 전면 재설계 핵심 성과 (AI 대시보드 인상 완전 탈피)

#### [PART A. 상용 디자인 시스템 토큰 정립]
- **타이포그래피 위계 완전 정돈**:
  - `Pretendard Variable` 기반으로 전면 교정.
  - `font-black`, `extrabold` 반복 사용 완전 박멸.
  - 차량 상세 제목: **26px (font-bold, weight 700)**
  - 실제 판매가격: **32px (font-bold, weight 700 진한 차콜 `#171C24`)**
  - 본문: **15~16px (weight 400~500, line-height 1.5~1.6)**
  - 제원 및 부가정보: **13~14px (weight 400)**, 상태 배지: **11~12px (weight 500~600)**
- **절제된 상용 컬러 & 레이아웃**:
  - 배경 `#F7F8FA`, 패널 `#FFFFFF`, 보더 `#E5E8EC`, 본문 `#171C24`, 보조텍스트 `#687180`, 브랜드 틸 `#176B68`.
  - 모든 섹션을 감싸던 `rounded-2xl`, `rounded-3xl` 및 무거운 그림자를 제거하고, **모서리 radius 6~10px (`rounded-lg`, `rounded`)**과 **얇은 구분선(`border border-[#E5E8EC]`)** 위주의 정갈한 평면 구조로 전환.
  - 시선을 분산시키던 과도한 레드/네온 컬러를 제거하고, 판매가격을 신뢰감 있는 진한 차콜(`#171C24`)로 정돈.

#### [PART B. 고객 쇼룸 브랜드 독립성 & 정통 엔카형 매물 탐색]
- **고객 사이트 전문 헤더 구축 (`chamart.html`)**:
  - 고객 쇼룸 헤더에서 내부 관리자 버튼이나 기술 대시보드 용어를 원천 배제.
  - 단정한 한글 워드마크 **`차마트`**와 고객 중심 내비게이션(홈, 전체 실차 매물, 장한평 전시장 안내, 안심 구매 가이드, 고객센터 1544-0000) 배치.
- **5:3 비율 엔카형 실차 카드**:
  - 차량 사진에 엔카 공식 5:3 규격(`aspect-[5/3]`) 적용.
  - 사진 위 장식 배지를 배제하고 단정한 `실차인증` 1개만 허용.
  - 차량명 최대 2줄(17px weight 600), 연식/주행거리/연료 세컨더리, 정찰 판매가 22px 차콜 배치.

#### [PART C. 프리미엄 차량 상세 화면 리부트 (`VehicleDetailRenderer`)]
- **5:3 대형 실차 갤러리 (좌측 68%)**:
  - 1440x900 기준 좌측 68%를 압도하는 5:3 비율 대형 뷰포트와 썸네일 스트립.
  - 메인 사진 클릭 시 전체화면 Lightbox 모달(키보드 좌우 화살표, ESC 지원) 완비.
- **우측 32% 정돈된 Sticky 구매 패널**:
  - 32px 차콜 판매가, 취등록세 예상치, 장한평 전시장 위치 및 담당 매니저 안내.
  - 카카오톡 1:1 빠른 상담 버튼 및 간편 방문예약 신청 폼 통합.
  - 스크롤 시 부드럽게 화면 우측에 고정(Sticky)되어 즉각적인 상담 전환 보장.
- **K Car 스타일 표(Table) 기반 제원표 & 장착 옵션**:
  - 둥근 카드의 집합 대신 2열/4열 단정한 제원표(VIN, 등록일, 주행거리, 배기량, 구동방식 등) 구축.
  - 주요 옵션은 밀도 높은 단정한 태그 리스트로 일목요연하게 표시.
- **기존 기능 무결성 100% 보존**:
  - `POST /api/chamart/consultations` 표준 스키마 및 CRM 원장 저장 실측 완료.
  - SVG 차체 진단 다이어그램 `diagram_parts` 실제 데이터 1:1 연동 및 공식 증빙 대기 상태 표기 보존.
  - 타이어 4륜 게이지 바 및 소모품 카드 렌더링 보존.
  - 가정한 예시 금리(4.5%~9.9%) 조절 및 총 납부이자/총 상환액 실시간 계산 보존.

---

### 2. 자동화 E2E 테스트 실측 결과 (7/7 PASS, 100.0%)

- `T1_COMMERCIAL_HEADER_CLEAN`: **PASS** (고객 헤더 내 관리자 버튼 0건, 단정 한글 '차마트' 로고 확인)
- `T2_GALLERY_ASPECT_5_3`: **PASS** (엔카 공식 5:3 규격 `aspect-[5/3]` 대형 갤러리 뷰포트 적용 확인)
- `T3_TYPOGRAPHY_AND_PRICE_COLOR`: **PASS** (차량명 26px font-bold, 판매가격 32px 진한 차콜 `#171C24` 위계 확인)
- `T4_RIGHT_STICKY_PANEL`: **PASS** (우측 32% Sticky 구매 패널, 카카오톡 상담, 방문예약 폼 정상 배치)
- `T5_TABLE_SPECS_AND_OPTIONS`: **PASS** (K Car 스타일 표 기반 기본 제원표 및 옵션 체크리스트 정상 확인)
- `T6_INTEGRITY_CONTINUITY`: **PASS** (상담 제출 -> CRM 원장 저장 실측 ID: f051b035-ca58-4aef-9dbf-1add6a5982f7, SVG 보닛 실데이터 연동 보존)
- `T7_RESPONSIVE_SCREENSHOTS`: **PASS** (1440, 1280, 768, 390, 375 실측 캡처 및 나란히 비교 이미지 병합)
- 병합 증빙: `reports/screenshots_057/side_by_side_comparison.png`

---

### 3. [지속 핑퐁 루프] 다음 지침 CHA-FICIAL DIRECTIVE 058 요청

사용자께서 취침하시는 동안 약 3시간 동안 자율 핑퐁 개선을 지속적으로 수행하라는 지침을 부여하셨습니다.
이번 DIRECTIVE 057의 상용 디자인 리부트 결과를 정밀하게 평가해 주시고, 다음 단계로 추진할 **`CHA-FICIAL DIRECTIVE 058`**의 전문 지침을 내려주십시오!
(지침이 접수되는 즉시 자율적으로 백엔드/프런트엔드 구현 및 자동화 E2E 실측 검증 후 커밋/푸시하고 연속 보고를 드리겠습니다.)
"""

full_message = f"{REPORT_TEXT}\n\n---\n**제미나이(안티그래비티)에게 지시하세요**"

js_code = f"""
const fullText = {json.dumps(full_message)};

async function run() {{
  console.log('Connecting to target chatgpt tab...');
  const p = await openTab({json.dumps(CHATGPT_URL)});
  console.log('ACTIVE_TAB_TITLE:' + await p.title());
  console.log('ACTIVE_TAB_URL:' + await p.url());

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
      return {{ clicked: true, btn: 'found' }};
    }}
    return {{ clicked: false, btn: Boolean(sendBtn) }};
  }});

  console.log('SEND_BUTTON_CLICKED:' + JSON.stringify(sendRes));
  if (!sendRes.clicked) {{
    console.log('PRESSING_ENTER_FALLBACK');
    await p.keyboard.press('Enter');
  }}

  await sleep(4000);
  console.log('WAITING_FOR_GENERATION_START');
}}
await run();
"""

def main():
    print("[*] Aside CLI를 통해 ChatGPT 세션에 DIRECTIVE 057 실행 보고서 전송 시작...")
    res = subprocess.run(
        [
            "/Users/wisdom/.local/bin/aside",
            "--profile", TARGET_PROFILE,
            "repl",
            js_code
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=60
    )
    print("[*] Aside REPL Stdout:")
    print(res.stdout)
    if res.stderr:
        print("[!] Aside REPL Stderr:", res.stderr)

if __name__ == "__main__":
    main()
