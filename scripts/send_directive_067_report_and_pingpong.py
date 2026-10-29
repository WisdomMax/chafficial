#!/usr/bin/env python3
"""ChatGPT 세션에 DIRECTIVE 067 완료 보고서를 전송하고 DIRECTIVE 068을 수신하는 핑퐁 스크립트."""

import json
import subprocess
import sys
import time

TARGET_PROFILE = "c759b216-69cc-436b-941a-dab4e621632d"
CHATGPT_URL = "https://chatgpt.com/"

REPORT_PROMPT = """# CHA-FICIAL DIRECTIVE 067 완수 보고서
## 혼합 데이터 공개 승인 경계 회귀 검증, 전수 경로 감사, A4 견적서 내용 보존 및 시각 증거 제출 완수

**수신:** ChatGPT (총괄 디자인 감독)  
**발신:** Gemini Antigravity (실행 엔진)  
**기준 커밋:** `175bf26` (GitHub 원격 푸시 완료: `feat/directive-052-security-publishing-content-remediation`)  

---

### 1. P0 혼합 데이터 공개 승인 경계 회귀 검증 (`scripts/test_boundary_matrix_067.py`)
운영 원본과 분리된 독립 임시 테스트 DB에 5종 혼합 데이터를 구성하여 전수 실측 검증을 완료하였습니다:
1. **공개 실차 (`V_VALID_PROD`)**: 운영 목록에 정상 1건 노출, 운영 상세 HTTP 200 반환, 상담 신청 정상 200 접수 및 **DB `consultations`에 정상 레코드 +1건 생성 확인** (PASS).
2. **비공개 운영 차량 (`V_UNPUBLISHED`)**: 운영 목록 100% 제외, 운영 상세 HTTP 404 차단, 상담 신청 HTTP 400 차단 및 **DB 레코드 미생성(0건) 확인** (PASS).
3. **시연용 데모 차량 (`V_DEMO`)**: 운영 목록 100% 제외, 운영 상세 HTTP 404 차단, 상담 신청 HTTP 400 차단 및 **DB 레코드 미생성(0건) 확인** (PASS).
4. **사진 미검증 차량 (`V_UNVERIFIED_PHOTO`)**: 운영 목록 100% 제외, 운영 상세 HTTP 404 차단, 상담 신청 HTTP 400 차단 및 **DB 레코드 미생성(0건) 확인** (PASS).
5. **존재하지 않는 차량 ID (`V_NOT_FOUND`)**: 운영 상세 HTTP 404 차단, 상담 신청 HTTP 400 차단 및 **DB 레코드 미생성(0건) 확인** (PASS).
6. **파라미터 변조 방어**: `mode` 파라미터 생략, `mode=prod`, `mode=demo`, `mode=xyz`, `mode=invalid_mode` 요청 시에도 운영 목록에 오직 승인된 실차(`V_VALID_PROD`) 1건만 반환됨을 확인 (PASS).
7. **스테이징 격리 모드 (`mode="demo"`)**: 데모 차량(`V_DEMO`)이 정상 제공됨을 확인 (PASS).

---

### 2. P0 실제 경로 전수 조사 보고서 구축 (`reports/directive_067/ROUTE_AUDIT.md`)
- 코드에 존재하는 11대 엔드포인트의 인증 요건, 공개 가드 적용 여부, 우회 접근 결과 및 논리적 격리 한계를 공식 감사표로 문서화 완료:
  - `/api/chamart/vehicles`: 공개 (None), `allow_demo=False` 강제, 데모/미검증 제외, 0건 반환.
  - `/api/chamart/vehicles/{id}`: 공개 (None), `allow_demo=False` 강제, 미승인 ID HTTP 404 차단.
  - `/api/chamart/consultations`: 공개 (None), 비승인 매물 상담 HTTP 400 차단 및 DB 레코드 미생성.
  - `/api/staging/chamart/vehicles`: 격리 (None), `allow_demo=True` 고정, 3대 시연 매물 제공.
  - `/api/vehicles`: 관리자 토큰 필수 (`require_auth`), 토큰 부재 시 401 차단.

---

### 3. P1 A4 견적서 실제 내용 보존 증거 제출 (`reports/directive_067/`)
- **표준 시연 차량 견적서**:
  - PDF 원본: `reports/directive_067/estimate_standard.pdf` (422,566 바이트, **Page count == 1**)
  - sips 1:1 고해상도 렌더 PNG: `reports/directive_067/estimate_standard_page1.png`
- **긴 차명 케이스 견적서** ("더 뉴 제네시스 G80 3.5T 가솔린 AWD 스포츠 패키지 캘리그래피 풀옵션..."):
  - PDF 원본: `reports/directive_067/estimate_long_title.pdf` (446,582 바이트, **Page count == 1**)
  - sips 1:1 고해상도 렌더 PNG: `reports/directive_067/estimate_long_title_page1.png`
- **내용 보존 검증 결과**:
  - `overflow: hidden` 트릭 없이 `overflow: visible` 상태에서 순수 A4 규격(너비 100%, 높이 약 265mm) 안에 자연스럽게 수용.
  - 차량명, 발급일, 정찰 판매가, 취득세(7%), 부대비용, 총비용 합계, 할부 시뮬레이션(원금/기간/금리/월납입금/이자), `[시연용 견적서]` 워터마크 및 고지문이 잘림이나 겹침 없이 100% 온전히 보존됨을 확인.

---

### 4. P1 반응형 시각 검수 및 증빙 대시보드 (`reports/directive_067/`)
- 360px 모바일 소형 빈 상태: `360x800_prod_mobile_small.png`
- 390px 모바일 표준 빈 상태: `390x844_prod_mobile_standard.png`
- 768px 태블릿 스테이징 쇼룸: `768x1024_staging_tablet.png`
- 1440px 데스크톱 스테이징 쇼룸: `1440x900_staging_desktop.png`
- 390px 모바일 비교 모달 (가로스크롤 안내 바 표출): `390x844_staging_compare_modal.png`
- 종합 4분할 비교 대시보드: `side_by_side_comparison_067.png`

---

### 5. `reports/directive_067/` 산출물 디렉토리 구조
- `ROUTE_AUDIT.md`: 실제 경로 전수 조사표
- `estimate_standard.pdf`: 표준 견적서 A4 원본
- `estimate_standard_page1.png`: 표준 견적서 sips 고해상도 렌더링
- `estimate_long_title.pdf`: 긴 차명 견적서 A4 원본
- `estimate_long_title_page1.png`: 긴 차명 견적서 sips 고해상도 렌더링
- `360x800_prod_mobile_small.png`, `390x844_prod_mobile_standard.png`, `768x1024_staging_tablet.png`, `1440x900_staging_desktop.png`, `390x844_staging_compare_modal.png`
- `side_by_side_comparison_067.png`: 4분할 종합 대시보드

총괄 디자인 감독님의 DIRECTIVE 067 최종 감사 판정 및 다음 지침(DIRECTIVE 068)을 하달해 주시기 바랍니다.
"""

js_code = f"""
async function pingpong067() {{
  const p = await openTab({json.dumps(CHATGPT_URL)});
  await sleep(3000);

  // 1. 입력창 포커스 및 텍스트 주입
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

  // 2. 전송 버튼 클릭
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

  // 3. 응답 완료 대기 루프 (최대 160초)
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

  // 4. 최신 텍스트 추출
  const text = await p.evaluate(() => {{
    const main = document.querySelector('main');
    return main ? main.innerText : document.body.innerText;
  }});

  console.log('===TEXT_START===');
  console.log(text.slice(-15000));
  console.log('===TEXT_END===');
}}
await pingpong067();
"""

def main():
    print("[*] ChatGPT 세션에 DIRECTIVE 067 완료 보고서 전송 및 응답 수신 시작...")
    
    max_retries = 3
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
            with open("reports/DIRECTIVE_068_EXTRACTED.md", "w", encoding="utf-8") as f:
                f.write(extracted)
            print(f"[*] DIRECTIVE 068 저장 성공! (길이: {len(extracted)}자): reports/DIRECTIVE_068_EXTRACTED.md")
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
