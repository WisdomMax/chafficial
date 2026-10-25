# REPORT 045-C: REMOTE DEMO VERIFICATION
## 차마트 외부 시연 실접속 및 이메일 인증 보호 터널 실증 보고서

**우선순위:** P0 (EXTERNAL DEMO RELEASE BLOCKER)  
**수행 일시:** 2026-10-26 03:56 KST  
**검증 상태:** `ACCESS_PROTECTED / REMOTE_TEST_PENDING / SECURITY_HARDENED / 9_OF_9_TESTS_PASS`  
**웹 서비스 주소:** `http://127.0.0.1:8501` (로컬 루프백 전용 바인딩)  
**터널 도구:** Cloudflare Tunnel (`cloudflared 2026.10.3` 업그레이드 및 `--allowed-mail` 실증)  
**담당 조직:** 차마트(CHAMART) & 차피셜 AI 엔지니어링팀  

---

## 1. Cloudflare 버전 및 `--allowed-mail` 옵션 지원 실증

DIRECTIVE 045-C의 핵심 지적에 따라, 2026년 10월 2일 Cloudflare가 공식 발표한 이메일 인증 보호 Quick Tunnel 기능 지원 여부를 전수 검증했습니다.

- **업그레이드 이전 버전:** `cloudflared 2026.7.3` (이메일 보호 미지원 버전)
- **Homebrew 업그레이드 수행:** `brew upgrade cloudflared` (완료)
- **현재 설치 및 검증 버전:** `cloudflared 2026.10.3` (built 2026-10-21T10:51:09Z)
- **CLI 도움말 옵션 실증:**
  ```text
  --allowed-mail value
      Email addresses or wildcard domains allowed to access a protected Quick Tunnel.
      May be repeated or comma-separated. (accepts multiple inputs)
  ```
- **판정:** **VERIFIED** (공식 `--allowed-mail` 옵션 완벽 지원 확인)

---

## 2. 보호된 임시 터널 구성 및 드라이런 실증

무인증 공개 터널 위험을 원천 차단하기 위해 `--allowed-mail` 플래그를 필수로 적용하는 보호 터널 프로토콜을 실증했습니다.

- **실증 실행 명령:**
  ```bash
  /opt/homebrew/bin/cloudflared tunnel \
    --url http://127.0.0.1:8501 \
    --allowed-mail "director-demo@chamart.co.kr"
  ```
- **드라이런 결과:**
  - Cloudflare 에지와의 QUIC 프로토콜 연결 수립 및 실제 보호된 임시 HTTPS 도메인(`https://relax-observe-effort-subaru.trycloudflare.com`) 정상 발급 확인.
  - 무인가 외부 노출 방지를 위해 발급 검증 직후 프로세스를 graceful termination(안전 종료) 처리 완료.
- **보호 메커니즘:**
  - 해당 URL 접속 시 Cloudflare Zero Trust 로그인 화면이 먼저 호출되며, 인가된 이메일 계정으로 발송된 일회용 OTP 핀 번호를 입력해야만 내부 차마트 웹사이트에 도달할 수 있습니다.

---

## 3. 서버 및 세션 보안 최종 하드닝

### A. 관리자 비밀번호 완전 교체 및 Fail-safe
- 과거 노출 가능성이 있는 임의 비밀번호를 영구 폐기하고, 암호학적으로 안전한 32자리 무작위 문자열(`secrets.token_urlsafe(24)`)로 `.env`의 `CHAMART_ADMIN_PASSWORD`를 전면 교체했습니다.
- 이전 비밀번호 및 임의 문자열 로그인 시 즉각 **HTTP 401 Unauthorized** 차단을 실증했습니다 (TEST 2 PASS).
- 환경변수 미설정 시 임의 비밀번호를 자동 생성하지 않고 서버 기동을 즉시 중단하는 Fail-safe 정책 유지.

### B. HTTPS 환경 세션 쿠키 Secure 속성 자동 활성화
- Cloudflare Tunnel 및 HTTPS 환경 접속 시(`CF-Ray` 또는 `X-Forwarded-Proto: https` 동반 시) 세션 쿠키에 `Secure` 플래그가 자동 활성화되도록 `app.py`를 보강했습니다.
- 검증 결과: `Set-Cookie: chamart_auth=...; Max-Age=86400; Path=/; SameSite=lax; Secure; HttpOnly` 정상 발급 확인 (TEST 4 PASS).

### C. CF-Connecting-IP 헤더 위조 스푸핑 방어
- Cloudflare 에지가 보증하는 유효한 `CF-Ray` 헤더가 동반되지 않은 직접 로컬 호출에서는 임의의 `CF-Connecting-IP` 헤더를 신뢰하지 않고 실제 소켓 IP(`127.0.0.1`)를 강제 적용하도록 수정했습니다.
- 이를 통해 헤더 조작을 통한 Brute-force 로그인 횟수 제한(5회 실패 시 429 차단) 우회 취약점을 원천 방어했습니다 (TEST 3 PASS).

### D. 로컬 전용 바인딩
- FastAPI 서버는 오직 `127.0.0.1:8501` 루프백 인터페이스에만 바인딩되어 외부 직접 접속이 불가능하며, 오직 Cloudflare 터널을 통해서만 안전하게 중계됩니다.

---

## 4. 미인가 API 직접 호출 차단 및 세션 무효화 실증

1. **미인가 API 직접 접근 차단 (HTTP 401):**
   - `GET /api/customers` $\rightarrow$ **HTTP 401 Unauthorized**
   - `GET /api/transactions` $\rightarrow$ **HTTP 401 Unauthorized**
   - `GET /api/documents` $\rightarrow$ **HTTP 401 Unauthorized**
   - `GET /api/media-projects` $\rightarrow$ **HTTP 401 Unauthorized**
   - `POST /api/vehicles` $\rightarrow$ **HTTP 401 Unauthorized**
2. **로그아웃 세션 즉각 폐기:**
   - `/api/auth/logout` 호출 즉시 인메모리 세션 저장소에서 토큰 삭제.
   - 폐기된 이전 토큰으로 재호출 시 즉각 **HTTP 401 Unauthorized** 반환 확인.
3. **무차별 대입(Brute-force) 429 차단:**
   - 60초 내 5회 로그인 실패 시 HTTP 429 (Too Many Requests) 즉시 차단 실증 완료.

---

## 5. 데이터 무결성 및 시연 격리 상태

1. **국토교통부 통계 정합성:**
   - 2026년 9월 등록자료 엑셀 `24.이전 등록현황(당월)` Row 21 원본 수치인 **`전국 298,293건 (매매업자 199,879건, 당사자 92,751건, 기타 5,663건)`**을 대시보드에 일치 반영하고, "행정 이전등록"임을 명문화했습니다.
2. **시연 데이터 격리:**
   - 모든 시연 데이터는 격리 DB(`data/chamart/chamart_platform_demo.db`, 98,304 B)에서만 동작합니다.
   - 실제 딜러 실거래 기록은 **0건(`REAL_DATA_0`)**으로 순수하게 보존 중입니다.
   - 실제 고객 개인정보 및 계약서 원본 외부 노출 **0건**.

---

## 6. 미팅 시연용 1분 원클릭 스크립트 구축

사용자가 복잡한 터미널 명령 없이 미팅 현장에서 1분 만에 안전하게 시연할 수 있도록 `scripts/run_chamart_demo.sh`를 구축했습니다.

### [실행 방법]
```bash
# 허용할 시연자 이메일을 인자로 전달하여 1회 실행
./scripts/run_chamart_demo.sh ceo@chamart.co.kr
```

### [주요 동작]
1. `.env` 파일 및 관리자 비밀번호 무결성 자동 검사
2. 포트 8501 플랫폼 서버 백그라운드 기동
3. `--allowed-mail` 보호 옵션이 적용된 Cloudflare 터널 자동 기동
4. 터미널 화면에 외부 HTTPS 접속 주소 및 로그인 안내 출력
5. **시연 종료 시 `Ctrl + C`를 누르면 `trap` 핸들러가 동작하여 서버와 터널을 즉시 안전 종료(Graceful Cleanup) 처리**

---

## 7. 9대 보안 및 실증 테스트 결과 (100% PASS)

```
=================================================================
CHA-FICIAL DIRECTIVE 045-C: 외부 접속 보안 및 실증 테스트 시작
=================================================================
[PASS] TEST 1: 최신 cloudflared version 2026.10.3 (built 2026-10-21T10:51:09Z) 및 --allowed-mail 옵션 지원 실증 완료
[PASS] TEST 2: 관리자 비밀번호 교체 및 구/잘못된 비밀번호 401 차단 성공
[PASS] TEST 3: 직접 요청 시 비신뢰 CF-Connecting-IP 헤더 위조 차단 방어 확인
[PASS] TEST 4: HTTPS 환경 세션 쿠키 Secure; HttpOnly; SameSite=Lax 적용 확인
[PASS] TEST 5: 미인가 API 직접 호출 5종 전수 401 Unauthorized 차단 확인
[PASS] TEST 6: 세션 토큰 즉시 폐기 및 5회 실패 시 HTTP 429 차단 실증 완료
[PASS] TEST 7: --allowed-mail 보호 터널 주소 발급 실증 및 안전 종료 (https://relax-observe-effort-subaru.trycloudflare.com)
[PASS] TEST 8: 국토부 298,293건 원본 정합성 및 데모 DB 격리(실거래 0건) 확인
[PASS] TEST 9: 미팅용 1분 원클릭 스크립트 (scripts/run_chamart_demo.sh) 검증 완료
-----------------------------------------------------------------
최종 결과: 9대 전 항목 통과 (100% PASS)
=================================================================
```

---

## 8. 최종 상태 판정 및 미팅 대기

- **현재 상태:** `ACCESS_PROTECTED / REMOTE_TEST_PENDING` (상태 3)
- **판정 근거:**
  - `cloudflared 2026.10.3`의 `--allowed-mail` 보호 터널 생성 및 주소 발급 실증 완료.
  - 미인가 사용자 차단 프로토콜 및 세션/API 보안 하드닝 100% 통과.
  - 단, 실제 외부 모바일/노트북에서의 실시간 OTP 이메일 수신 및 현장 브라우저 조작은 미팅 시 사용자의 실제 이메일로 즉시 수행될 수 있도록 대기 중(`REMOTE_TEST_PENDING`).
- **미팅 준비 상태:** `scripts/run_chamart_demo.sh` 준비 완료로 즉시 시연 가능.
