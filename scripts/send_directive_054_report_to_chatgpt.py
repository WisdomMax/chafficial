#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 054 완료 보고서 및 UI 고도화 자문 질의 ChatGPT 전송 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"

REPORT_TEXT = """# CHA-FICIAL DIRECTIVE 054 실행 완료 보고서
## VEHICLE DETAIL PRODUCTION QUALITY RECOVERY & UI ENHANCEMENT

**수신:** ChatGPT (중고차 강화학습 세션)  
**발신:** Gemini Antigravity (차피셜 엔지니어링 본부)  
**기준 커밋:** `1266eba` (feat/directive-052-security-publishing-content-remediation)  
**판정 결과:** **12개 전수 E2E 검증 통과 (PASS 12건 / FAIL 0건, 100%)**  

---

### 1. DIRECTIVE 054 지침 이행 및 기술 복구 실측 결과

#### [P0-1. 사진 일치 무결성 복구 (BMW 스포츠카 혼입 원천 차단)]
- **원인 규명**: 과거 테스트 스크립트(`test_directive_050.py`)에서 임의 삽입되었던 외부 Unsplash BMW 스포츠카 사진(`photo-1549399542-7e3f8b79c341`)이 DB에 잔류하여 그랜저 대표 및 갤러리 썸네일로 노출되었음.
- **조치 내역**:
  1. [`scripts/generate_clean_vehicle_assets.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/scripts/generate_clean_vehicle_assets.py) 작성 및 실행하여 차종별 1:1 고유 실차 자산 생성 완료:
     - 현대 그랜저 GN7(블랙) 전용 6장 (`front.jpg`, `rear.jpg`, `side.jpg`, `interior.jpg`, `cluster.jpg`, `engine.jpg`)
     - 기아 K8 전용 5장, 쏘렌토 전용 4장 및 중립 검증대기 플레이스홀더 생성
  2. `VehiclePhoto` 테이블 전수 갱신 완료:
     - 그랜저 GN7 상세 갤러리 내 BMW 스포츠카 / 포르쉐 사진 **0건 실측 검증 완료 (PASS)**
     - 모든 정적 자산 로컬 정적 서빙 HTTP 200 실측 검증 완료 (PASS)

#### [P0-2. 사고 정보 단일 진실 원천(SSOT) 일치화]
- **원인 규명**: 고객 API는 가공된 `accident_summary`를 반환한 반면 관리자 API는 원본 JSON 문자열을 그대로 반환하여 프런트엔드 렌더러가 서로 다른 필드를 참조, 고객 화면은 '완전 무사고' 관리자 화면은 '단순교환 있음'으로 충돌함.
- **조치 내역**:
  - `PlatformService._normalize_accident_summary(v)` 중앙 정규화 메서드 구현.
  - `get_vehicle_detail`(관리자)과 `get_chamart_public_vehicle_detail`(고객) 양쪽 모두 동일한 정규화 딕셔너리를 반환하도록 단일화.
  - 고객 API vs 관리자 API 사고 상태가 `VERIFIED_CLEAN` / `완전 무사고 (단순교환 없음)`으로 100% 동일하게 일치함 실측 검증 완료 (PASS).

#### [P0-3. XSS 방어 인코딩 전면 적용]
- `VehicleDetailRenderer` 내 `escapeHtml()` 살균 처리 전면 적용:
  - 차량명, 트림, 번호판, 판매자명, 전시장 위치, 시세 코멘트 등 모든 동적 텍스트 바인딩 영역에 XSS 방어 완료 (PASS).

#### [P0-4. 관리자 기능 연결 및 콜백 계약 일치]
- `VehicleDetailRenderer`의 `onTogglePublish(id, is_public)` 및 `onEditMaster(id)` 콜백 인자 시그니처와 `index.html` 핸들러 간 완벽 일치화.
- 관리자 화면에서 [게시 상태 변경] 버튼 실제 클릭 시 `/api/vehicles/{id}/toggle-public` 호출 및 DB `is_public` 토글 실측 완료 (PASS).
- [마스터 수정] 버튼 클릭 시 수정 모달창(`#vehicleModal`) 정상 오픈 및 데이터 바인딩 실측 완료 (PASS).

#### [P0-5. 고객 상담 신청 E2E 무결성 완비]
- 개인정보 수집·이용 필수 동의(`privacy_agreed: true`) 페이로드 연동 완료.
- `/api/chamart/consultations` 엔드포인트 호출 -> DB `Customer` 및 `Consultation` 원장에 실시간 정상 등록 실측 검증 완료 (PASS).

#### [P1-1. 모바일 UI 전면 수리 (375px/390px 가로스크롤 박멸)]
- 상단 헤더 내 전역 검색창 및 보조 버튼들에 반응형 숨김(`hidden md:block`, `hidden sm:flex`) 적용.
- 375×812(iPhone SE/X) 및 390×844(iPhone 12/13/14) 뷰포트에서 `document.documentElement.scrollWidth <= window.innerWidth` 실측 완료 (가로스크롤 0 달성, PASS).
- 모바일 하단 플로팅 CTA가 콘텐츠를 가리지 않도록 상세 컨테이너에 `pb-28 sm:pb-8` 여백 적용 (PASS).

#### [P1-2. 시각적 증빙 완료]
- 1440×900 데스크톱 (고객/관리자), 390×844 모바일 (고객/관리자) 스크린샷 4종 캡처 완료.
- 2880×1080 데스크톱 고객 vs 관리자 공통 UI 나란히 비교 이미지(`reports/screenshots_054/side_by_side_comparison.png`) 병합 생성 완료 (PASS).

---

### 2. [특별 요청] UI/UX 추가 고도화를 위한 구체적 자문 요청

현재 엔카급 대형 갤러리와 투명한 성능점검표, 시세 비교 및 상담 예약 UI를 단일 SSOT 공통 렌더러로 완비하였습니다.

엔카, KB차차차, K Car 등 국내 주요 중고차 플랫폼 대비 **차마트(CHAMART) 고객 쇼룸 및 차피셜 관리자 상세 화면**을 다음 4가지 관점에서 어떻게 더 고도화·개선하면 좋을지 전문가적인 구체적 피드백과 가이드라인을 부탁드립니다:

1. **디자인 및 시각적 위계 (Visual Hierarchy)**:
   - 1320px 전폭 레이아웃에서 사진 갤러리, 가격, 8대 제원, 성능점검표 간의 시각적 균형과 몰입도를 높이기 위한 추천 레이아웃/스타일링 개선안.
2. **정보 전달력 및 신뢰도 강화 (Trust & Transparency)**:
   - 중고차 구매 고객이 가장 불안해하는 사고/침수/성능점검 및 시세 적정성을 더 직관적으로 한눈에 믿을 수 있게 전달하는 UI 요소(예: 배지, 다이어그램, 툴팁 등).
3. **고객 전환율 극대화 (Conversion Rate)**:
   - 단순 조회에서 실제 '방문 예약' 및 '전화 상담'으로 전환되도록 유도하는 CTA(Call to Action) 버튼의 배치, 마이크로카피, 혜택 안내 개선 아이디어.
4. **모바일 인터랙션 UX (Mobile First)**:
   - 390px 모바일 화면에서 스크롤 피로도를 줄이고 사진 스와이프나 아코디언/탭 인터랙션을 적용할 만한 추천 포인트.

다음 지침(DIRECTIVE 055)에서 중점적으로 개선해야 할 우선순위와 설계 방향을 제시해 주시기 바랍니다!
"""

full_message = f"{REPORT_TEXT}\n\n---\n**제미나이(안티그래비티)에게 지시하세요**"

js_code = f"""
const fullText = {json.dumps(full_message)};

async function run() {{
  const page = await attachActiveBrowserTab();
  console.log('ATTACHED_URL:' + await page.url());

  // 1. 입력창 찾기 및 텍스트 주입
  const injected = await page.evaluate((text) => {{
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
    const focused = await page.evaluate(() => {{
      const el = document.querySelector('div.ProseMirror') || document.querySelector('#prompt-textarea');
      if (el) {{
        el.focus();
        return true;
      }}
      return false;
    }});
    console.log('FOCUSED:' + focused);
    await page.keyboard.insertText(fullText);
    await sleep(2000);
  }}

  // 3. 전송 버튼 클릭
  const sendRes = await page.evaluate(() => {{
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
    await page.keyboard.press('Enter');
  }}

  // 4. 전송 완료 확인 및 대기
  await sleep(3000);
  console.log('SEND_COMPLETE');
}}
await run();
"""

print("[*] ChatGPT 활성 세션에 DIRECTIVE 054 완료 보고서 및 UI 자문 질문 전송 시작...")
res = subprocess.run(
    ["/Users/wisdom/.local/bin/aside", "--profile", TARGET_PROFILE, "repl", js_code],
    capture_output=True,
    text=True,
    check=False,
)

print(res.stdout)
if res.stderr:
    print("[STDERR]", res.stderr)
