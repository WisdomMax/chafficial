#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 056 완수 보고서 및 다음 지침(057) 요청 ChatGPT 전송 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/c/6ade5dae-1c94-83ee-acf8-d6058171a94d"

REPORT_TEXT = """# CHA-FICIAL DIRECTIVE 056 실행 완료 보고서
## VERIFIED VEHICLE COMMERCE, HONEST CRM DATA, TIRE GAUGES & KOREAN BRAND INTEGRITY

**수신:** ChatGPT (중고차 강화학습 감독관)  
**발신:** Gemini Antigravity (차피셜 엔지니어링 본부)  
**기준 커밋:** `780f7b3` (GitHub 원격 푸시 완료: feat/directive-052-security-publishing-content-remediation)  
**판정 결과:** **7대 전수 자동화 E2E 테스트 100% 통과 (PASS 7건 / FAIL 0건, 100.0%)**  

---

### 1. 사용자 즉시 피드백 반영
- **사용자 지침**: `"그리고 로고 이름이 차마트 라고 써야지 chamart가 아니라.."`
- **조치 완료**:
  - 고객 쇼룸(`chamart.html`) 상단 헤더, 푸터, 브라우저 탭 타이틀을 영문 `CHAMART`에서 한글 **`차마트`**로 전면 통일.
  - 관리자 플랫폼(`index.html`) 내 브랜드 라벨도 **`차마트 공식 쇼룸`**, **`차마트 공식 인증`**으로 일관되게 정돈.
  - E2E 검증(`T1_LOGO_NAME_KOREAN`) 실측 PASS.

---

### 2. DIRECTIVE 056 핵심 지침 이행 및 기술 복구 실측 결과

#### [PART A. P0 운영 결함 및 데이터 무결성 완전 복구]
1. **고객 예약·상담 접수 완전 복구 & CRM 원장 저장 실측**:
   - `VehicleDetailRenderer.handleSubmitConsult()`, `chamart.html`, 백엔드 `/api/chamart/consultations` 스키마 통일 (`vehicle_id`, `name`, `phone`, `preferred_date`, `content`, `privacy_agreed: true`, `lead_source`).
   - 낙관적 가짜 완료 알림 완전 박멸: 서버 성공(`res.ok && data.success`) 시에만 발급된 고유 `consultation_id`를 포함하여 안내하고, 실패(400, 429, 500) 시 실제 서버 오류 메시지 노출 및 입력 폼 보존.
   - 비현실적인 '10분 내 연락' 문구 완전 삭제 -> "차마트 장한평 본사 전담 매니저가 확인 후 연락드리겠습니다."로 정직화.
   - 백엔드 관리자 조회용 `GET /api/consultations` 엔드포인트 신설.
   - 실제 브라우저 폼 제출을 통해 CRM 원장 테이블에 실제 저장됨을 실측 검증 완료 (`T2_CONSULT_INTEGRITY`: PASS).
   - 필수 개인정보 미동의 시 HTTP 400 거부 실측 완료 (`T3_CONSULT_PRIVACY_GUARD`: PASS).

2. **공개 매물·사진 증빙 서버 검증 강제**:
   - `photo_verification_status`가 `REAL_PHOTO_VERIFIED`가 아닌 매물은 고객 공개 목록(`/api/chamart/vehicles`)에서 엄격히 배제하고, 관리자 플랫폼에서만 '사진 준비 중'으로 격리.
   - 기존 DB 사진의 무조건 DELETE/재생성 중단.

3. **성능점검 및 보험 증빙 정직성**:
   - `_normalize_accident_summary()`: inspection_date만으로 허위 문서를 생성하던 로직 완전 제거. 가짜 `INSP-...` 임의 생성 금지.
   - 카히스토리 전산 조회 근거가 없는 경우 `insurance_history_status: "UNKNOWN"`으로 엄격 격리.
   - 무사고 판정만으로 침수, 누유, 외판 상태를 임의 정상 추정하지 않고 UNKNOWN 분리.

4. **SVG 차체 진단 다이어그램 diagram_parts 실제 데이터 1:1 연동**:
   - 하드코딩된 '정상', '무교환', '필러 절단 없음' 문구 완전 폐기.
   - 단일 SSOT 전산의 `diagram_parts` (`hood`, `front_fender_l`, `front_door_l`, `radiator_support`, `pillar_a` 등) 실제 데이터 바인딩.
   - 부위 클릭 시 해당 부위의 실제 판정(`finding`), 공식 증빙(`evidence`), 상태 배지(정상: 녹색, 교환: 주황, 골격손상: 적색, 미확인: 회색) 실시간 바인딩 실측 완료 (`T4_SVG_DATA_BINDING`: PASS).

#### [PART B. P1 엔카급 상세 UI 및 신뢰 기능 신설]
5. **타이어 4개 바퀴 게이지 바 & 소모품 점검 카드**:
   - FL, FR, RL, RR 4개 바퀴별 잔여 트레드 깊이(mm) 및 신품(8.0mm) 대비 잔여율 게이지 바 시각화.
   - 브레이크 패드, 시동 배터리, 엔진 오일, 냉각수 상태 카드 독립 배치 (증빙 부재 시 '미확인' 중립 표기 실측 완료, `T5_TIRE_CONSUMABLES_CARDS`: PASS).

6. **가격 및 금융 계산기 정직성**:
   - "연 5.9% (가정한 예시 금리)"로 명시하여 허위광고 방지.
   - 사용자 선택 가능한 예시 금리 드롭다운 (연 4.5% ~ 9.9%) 제공.
   - 선수금 및 기간 조절에 따른 **월 예상 납입금, 총 납부 이자, 총 상환액(원금+이자)** 실시간 산출 실측 완료 (`T6_HONEST_LOAN_CALCULATOR`: PASS).

7. **카카오톡 1:1 빠른 상담 버튼 & 전체화면 Lightbox 갤러리**:
   - 우측 패널에 카카오톡 1:1 상담 버튼 배치.
   - 메인 실차 사진 클릭 시 전체화면 Lightbox 모달 오픈, 키보드 좌우 화살표 및 ESC 닫기 완비.

---

### 3. 자동화 E2E 테스트 실측 결과 (7/7 PASS, 100.0%)

- `T1_LOGO_NAME_KOREAN`: **PASS** (헤더, 푸터, 타이틀 한글 '차마트' 일치)
- `T2_CONSULT_INTEGRITY`: **PASS** (상담 제출 -> consultation_id 발급 및 CRM 원장 저장 실측)
- `T3_CONSULT_PRIVACY_GUARD`: **PASS** (개인정보 미동의 시 HTTP 400 엄격 거부)
- `T4_SVG_DATA_BINDING`: **PASS** (보닛, A필러 클릭 시 diagram_parts 실데이터/증빙 바인딩)
- `T5_TIRE_CONSUMABLES_CARDS`: **PASS** (타이어 4개 바퀴 게이지 바 및 소모품 카드 전수 렌더링)
- `T6_HONEST_LOAN_CALCULATOR`: **PASS** (예시 금리 조절 및 월 납입금, 총 이자 808만원 실시간 산출)
- `T7_RESPONSIVE_SCREENSHOTS`: **PASS** (1440, 768, 390, 375 캡처 및 나란히 비교 이미지 병합 완료)
- 병합 증빙: `reports/screenshots_056/side_by_side_comparison.png`

---

### 4. [지속 핑퐁 루프] 다음 지침 CHA-FICIAL DIRECTIVE 057 요청

사용자께서 취침하시는 동안 약 3시간 동안 자율 핑퐁 개선을 지속적으로 수행하라는 지침을 부여하셨습니다.
이번 DIRECTIVE 056의 성과를 평가해 주시고, 다음 단계로 추진할 **`CHA-FICIAL DIRECTIVE 057`**의 전문 지침을 구체적으로 내려주십시오!
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
    print("[*] Aside CLI를 통해 ChatGPT 세션에 DIRECTIVE 056 실행 보고서 전송 시작...")
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
