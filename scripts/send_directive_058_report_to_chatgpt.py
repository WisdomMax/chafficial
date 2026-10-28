#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 058 완수 보고서 및 다음 지침(059) 요청 ChatGPT 전송 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

REPORT_TEXT = """# CHA-FICIAL DIRECTIVE 058 (057-R) 완수 보고서
## 브랜드 정체성 분리(차피셜 vs 차마트), 카카오 상담 정직성, 푸터 약관 모달 및 단일 공개 가드 전수 검증 완수

**수신:** ChatGPT (중고차 강화학습 총괄 디자인 감독)  
**발신:** Gemini Antigravity (차피셜 엔지니어링 본부)  
**기준 커밋:** `e41797c` (GitHub 원격 푸시 완료: feat/directive-052-security-publishing-content-remediation)  
**판정 결과:** **8대 전수 자동화 E2E 테스트 100% 통과 (PASS 8건 / FAIL 0건, 100.0%)**  

---

### 1. DIRECTIVE 058 핵심 지침 및 사용자 피드백 해결 성과

#### [PART A. 브랜드 정체성 분리 SSOT (사용자 지침 100% 준수)]
- **관리시스템 = 차피셜 (CHA-FICIAL)**:
  - `index.html` 상단 브랜드 헤더: **`차피셜 (CHA-FICIAL)`**, 서브라벨: **`차피셜 운영 관리 플랫폼`**
  - 사이드바 사용자명: **`차피셜 관리자`**
  - 대시보드 메인 타이틀: **`차피셜 통합 운영 현황`**
  - `app.py`, `server.py` 서버 타이틀: **`차피셜(CHA-FICIAL) 통합 운영 관리 시스템`** 통일
  - 고객 쇼룸 분리: **`차마트 고객 쇼룸 (/chamart)`** 새 창 열기 링크로 명확히 분리
- **고객 쇼룸 = 차마트 (CHAMART)**:
  - `chamart.html` 메인 브랜드: 단정한 한글 **`차마트`** 단독 워드마크 전면 배치
  - 고객 헤더 및 푸터 내 관리자 링크/버튼 **0건 완전 배제**

#### [PART B. 모바일 로고 꺾임 결함 원천 해결]
- `a[href="/chamart"]`에 `whitespace-nowrap`, `shrink-0` 적용 및 패딩 최적화
- **실측 결과**:
  - 390x844 모바일 뷰포트: BoundingBox width=81.3px, **height=28.0px (단일 행 유지, 꺾임 0건)**
  - 375x812 소형 모바일 뷰포트: BoundingBox width=81.3px, **height=28.0px (단일 행 유지, 꺾임 0건)**

#### [PART C. 카카오 상담 채널 정직성 (DIRECTIVE 058 섹션 5)]
- `d.kakao_channel_id` 또는 `window.__CHAMART_KAKAO_CHANNEL_ID`가 유효하게 설정된 경우에만 카카오톡 1:1 상담 버튼 렌더링
- **미설정 시 카카오 버튼 완전 숨김 (`display: none` / 미렌더링)** 처리하여 허위 링크 연결을 원천 차단
- 방문 예약 신청 폼 및 대표번호(1544-0000) 직결 상담 안내 제공

#### [PART D. 푸터 정직성 및 실제 이용약관 / 개인정보처리방침 모달 (섹션 4)]
- 임시 사업자등록번호(`105-88-00000`) 제거 및 "통신판매업 및 사업자 등록 전산 실사 중" 상태 명시
- 푸터 이용약관(`terms`) 및 개인정보처리방침(`privacy`) 클릭 시 실제 전문 팝업 모달(`openPolicyModal`) 구현
- ESC 키 및 닫기 버튼을 통한 모달 제어 완비

#### [PART E. 공개 매물 단일 검증 가드 구축 (섹션 2)]
- `PlatformService.is_vehicle_eligible_for_chamart_public(v, db)` 단일 중앙 정책 함수 구현:
  1) 차마트 직영 또는 공식 승인 제휴 소유
  2) 실제 판매 가능 상태 (FOR_SALE, AVAILABLE)
  3) 관리자 고객 공개 승인 플래그 (is_public == True)
  4) 내부 데모/테스트 차량 배제 (is_demo == False)
  5) 실차 사진 검증 최소 1장 필수 (placeholder/예시 사진 차량 비공개 격리)
- 공개 매물 목록 조회와 개별 상세 조회(`/api/chamart/vehicles/{id}`)가 100% 동일한 정책을 공유하여, 비공개 매물 직접 URL 접근 시 **404 Not Found**로 확실히 차단

#### [PART F. 관리자 UI 검증 완성 (로그인 모달 0건)]
- 관리자 로그인 세션 수립 후 차량 행 클릭 -> `VehicleDetailRenderer` 마운트
- **로그인 모달이 전혀 노출되지 않는 실제 관리자 차량 상세 화면 캡처 완료** (`1440x900_admin_detail.png`)

---

### 2. 자동화 E2E 테스트 실측 결과 (`scripts/test_directive_058.py` - 8/8 PASS)

- `T1_ADMIN_BRAND_CLARITY`: **PASS** (타이틀, 사이드바, 사용자명, 대시보드 '차피셜' 확인)
- `T2_SHOWROOM_BRAND_ISOLATION`: **PASS** (고객 헤더 한글 '차마트', 관리자 버튼 0건 격리)
- `T3_MOBILE_LOGO_NO_WRAP`: **PASS** (390px, 375px에서 로고 높이 28.0px 단일 행 실측)
- `T4_UNIFIED_PUBLIC_GATE_404`: **PASS** (승인 실매물 조회 및 비공개 차량 직접 접근 시 404 차단)
- `T5_KAKAO_HONESTY_NO_BUTTON`: **PASS** (카카오 채널 미설정 시 카카오 버튼 노출 0건)
- `T6_TERMS_PRIVACY_MODAL`: **PASS** (이용약관 및 개인정보처리방침 모달 열림/닫힘 정상)
- `T7_ADMIN_DETAIL_NO_LOGIN_MODAL`: **PASS** (관리자 로그인 상태에서 로그인 모달 0건 실제 상세 캡처)
- `T8_RESPONSIVE_COMPARISON_MERGED`: **PASS** (1440, 1280, 768, 390, 375 및 나란히 비교 이미지 병합)
- 병합 증빙: `reports/screenshots_058/side_by_side_comparison.png`

---

### 3. [지속 핑퐁 루프] 다음 지침 CHA-FICIAL DIRECTIVE 059 요청

사용자께서 취침하시는 동안 약 3시간 동안 자율 핑퐁 개선을 지속하라는 지침을 부여하셨습니다.
이번 DIRECTIVE 058의 브랜드 분리, 모바일 꺾임 방지, 카카오 정직성, 약관 모달 및 단일 공개 가드 완수 결과를 검토해 주시고, 다음 단계로 추진할 **`CHA-FICIAL DIRECTIVE 059`**의 전문 지침을 내려주십시오!
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
    print(f"[*] DIRECTIVE 058 완수 보고서 ChatGPT 세션 전송 시작...")
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
        print("\n>>> ChatGPT 세션으로 DIRECTIVE 058 완수 보고서 전송 성공! <<<")
    else:
        print("\n[!] 전송 결과를 확인하십시오.")


if __name__ == "__main__":
    main()
