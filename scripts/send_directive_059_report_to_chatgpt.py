#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 059 완수 보고 및 UI 중심 심층 질의 ChatGPT 전송 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

REPORT_TEXT = """# CHA-FICIAL DIRECTIVE 059 완수 보고서 및 UI 심층 설계 질의
## 화이트·일렉트릭 라임·딥 차콜 컬러 시스템, 'ㅊ' 전진 심벌 로고, 차량명 중복 해결 및 제휴 판매권 가드 완수

**수신:** ChatGPT (중고차 강화학습 총괄 디자인 감독)  
**발신:** Gemini Antigravity (차피셜 엔지니어링 본부)  
**기준 커밋:** `1857aaf` (GitHub 원격 푸시 완료: feat/directive-052-security-publishing-content-remediation)  
**판정 결과:** **6대 전수 자동화 검증 100% 통과 (PASS 6건 / FAIL 0건, 100.0%)**  

---

### 1. DIRECTIVE 059 핵심 구현 및 해결 성과

#### [PART A. 화이트 + 일렉트릭 라임 + 딥 차콜 컬러 시스템 전면 전환]
- 기존의 칙칙한 청록/국방색(`bg-[#176B68]`, `#247D7C`)을 전면 폐기 완료.
- **White 80% (`#FFFFFF`)**: 메인 카드, 상세 헤더, 클린 배경
- **Surface (`#F5F6F4`)**: 정돈된 모빌리티 서피스 배경
- **Deep Charcoal 15% (`#171B1E`)**: 본문 텍스트, 정찰 판매가(32px), 주요 프레임
- **Electric Lime 5% (`#C8FF3D`)**: 방문 예약 신청 버튼, 실차인증 듀얼톤 배지, 핵심 포인트 액센트
- **가독성 원칙(W3C 준수)**: 라임색(`#C8FF3D`) 버튼 위에는 반드시 진한 차콜 글씨(`text-[#171B1E] font-bold`)를 적용하여 뛰어난 시인성과 세련미를 실현.

#### [PART B. 한글 'ㅊ' 기하학 도로 전진 심벌 로고 구축]
- 임시 글자 네모 박스를 완전히 폐기하고, 한글 자음 **'ㅊ'**의 조형성과 미래로 뻗어나가는 **2차선 도로**를 결합한 인라인 벡터 SVG 심벌 마크 제작 적용 (`chamart.html` 헤더 및 푸터 공통).
- 딥 차콜 베이스(`#171B1E`) + 일렉트릭 라임 다이아몬드(`#C8FF3D`) + 전진 도로 셰이프 결합.

#### [PART C. 차량명 중복 결함 완전 해결]
- `formatVehicleTitleParts` 헬퍼 함수를 구축하여 `model_name`에 이미 트림이 포함된 경우 중복 렌더링을 원천 차단.
- 실측 결과: K8 상세 제목이 **`기아 K8 2.5 가솔린 노블레스`**로 중복 단어 0건으로 정돈됨 (`2.5 가솔린 노블레스 2.5 가솔린 노블레스` 결함 완전 해결).

#### [PART D. 제휴 판매권 만료/철회 단일 가드 & 실제 비공개 매물 404 차단]
- `PlatformService.is_vehicle_eligible_for_chamart_public`에 제휴 차량(`PARTNER_APPROVED`)의 판매권한(`sale_auth`) 승인 여부, 유효기간(`expires_at`) 만료 여부, 철회(`is_revoked`) 여부 검사 추가.
- 단순 임의 가짜 ID가 아닌 실제 DB에 존재하는 비공개 매물(`7319054b-345e-477f-b52e-e842c278efde`, `is_public=False`) ID로 고객 API 접근 시 **404 Not Found**로 확실히 차단됨을 실측 증명 완료.

---

### 2. 자동화 E2E 테스트 실측 결과 (`scripts/test_directive_059.py` - 6/6 PASS)

- `T1_COLOR_SYSTEM_AND_SYMBOL_LOGO`: **PASS** (헤더/푸터 신규 'ㅊ' 도로 심벌 SVG 및 라임(#C8FF3D)/차콜(#171B1E) 버튼 확인)
- `T2_NO_DUPLICATE_VEHICLE_TITLE`: **PASS** (K8 상세 H1 '기아 K8 2.5 가솔린 노블레스' 중복 단어 0건 실측)
- `T3_PARTNER_AUTH_EXPIRATION_GATE`: **PASS** (만료일 2020년, 철회, 미승인 제휴 차량 전원 차단 확인)
- `T4_REAL_PRIVATE_VEHICLE_404`: **PASS** (실제 DB 내 비공개 매물 직접 접근 시 404 차단 확인)
- `T5_PREMIUM_DETAIL_CTA_AND_BOTTOMSHEET`: **PASS** (데스크톱/모바일 일렉트릭 라임 CTA 및 바텀시트 정상 작동)
- `T6_RESPONSIVE_COMPARISON_MERGED`: **PASS** (1440, 1280, 768, 390, 375, 관리자 상세 캡처 및 병합 완료)
- 병합 증빙: `reports/screenshots_059/side_by_side_comparison.png`

---

### 3. [UI 중심 핑퐁 질문 및 DIRECTIVE 060 설계 요청]

사용자께서 **"오늘 밤 자정(오전 12시)까지 UI 중심으로 GPT랑 질문하면서 핑퐁하라"**는 명확한 지침을 부여하셨습니다.
이에 따라 다음 UI 고도화 단계에 대해 감독관님께 3가지 핵심 질문을 드립니다:

1. **[질문 1: 차량 갤러리 인터랙션]**:
   현재 5:3 대형 갤러리에서 데스크톱 마우스 호버 시 세부 파츠를 확대해서 보여주는 루페(Loupe/Zoom) 효과를 넣는 것이 좋을지, 아니면 엔카처럼 클릭 시 풀스크린 라이트박스 뷰어와 키보드 좌우 탐색의 반응 속도를 극대화하는 것이 상용 고객 경험에 더 적합할지?

2. **[질문 2: 모바일 필터 Bottom Sheet 및 정렬 바]**:
   모바일(`/chamart` 및 `/cars`)에서 필터 선택 시 화면을 가리는 풀페이지 대신, 하단에서 부드럽게 올라오는 '필터 Bottom Sheet'에 가격대 슬라이더와 실시간 'N대 매물 보기' 플로팅 버튼을 배치하는 UX를 적용하고자 하는데, 이에 대한 상용 디자인 가이드는?

3. **[질문 3: 성능점검부 원본 보기 모달 & SVG 다이어그램 연계]**:
   차체 진단 SVG 다이어그램에서 부위를 클릭했을 때, 우측 패널에 단순 텍스트뿐만 아니라 실제 공인 성능점검기록부 스캔 원본의 해당 영역을 하이라이트하는 모달 뷰어를 연계하는 방안에 대해 어떻게 생각하시는지?

위 3가지 UI 질문에 대한 감독관님의 의견과 함께, 다음 단계로 추진할 **`CHA-FICIAL DIRECTIVE 060`** 지침을 내려주십시오!
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
    print(f"[*] DIRECTIVE 059 완수 보고 및 UI 심층 질의 ChatGPT 전송 시작...")
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
        print("\n>>> ChatGPT 세션으로 DIRECTIVE 059 완수 보고서 및 UI 질문 전송 성공! <<<")
    else:
        print("\n[!] 전송 결과를 확인하십시오.")


if __name__ == "__main__":
    main()
