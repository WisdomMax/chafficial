# CHA-FICIAL DIRECTIVE 050-C
## AUTH RECOVERY + GEMINI VISION CRM AUTOMATION
### 차량 상세조회 정상화 및 AI 명함·거래서류 자동 인식

**발신:** ChatGPT 총괄 기술감독  
**수신:** Gemini Antigravity  
**기준 커밋:** `52121a2`  
**우선순위:** P0 긴급 버그 수정 + AI 업무 자동화

---

## 1. 개발 목표

차피셜(CHAMART OS)에 다음 기능을 구현한다.

1. 모든 차량 상세보기 오류 해결
2. 명함 이미지 촬영만으로 고객 CRM 등록
3. 거래명세서·자동차 매매계약서·정산내역·입출금 내역 이미지 분석
4. 이미지에서 추출한 데이터를 기존 차량·고객·거래 관리와 연결
5. Gemini API 키 설정만 하면 AI 인식을 사용할 수 있는 구조 완성

기존 데이터와 화면은 보존한다.

---

## PHASE A. 차량 상세조회 및 인증 복구

현재 차량 목록은 열리지만 상세 조회 API에서 인증 오류가 발생할 수 있는 구조를 수정한다.

- 관리자 로그인 화면 및 세션 처리
- `/api/auth/me`로 인증 상태 확인
- 401 발생 시 재로그인 안내
- 차량 상세보기 404/500 오류 구분
- 브라우저 반복 alert 방지
- 차량 목록·상세·수정 API 인증 정책 일관화
- API 원본 HTTP 상태 및 서버 traceback 기록
- 로그아웃·세션 만료·서버 재시작 상황 검증

차량 상세조회를 위해 인증 기능을 제거하지 않는다.

**완료 조건:** 로그인 후 기존 차량과 신규 차량 각각 10건 이상 상세조회 정상 동작.

---

## PHASE B. Gemini Vision 공통 모듈

다른 업무에서 재사용할 수 있도록 `GeminiVisionService`를 분리 개발한다.

기본 모델: `gemini-flash-latest` (또는 `gemini-2.0-flash` / `gemini-1.5-flash`)  
저비용 대체 모델: `gemini-flash-lite`

환경설정:
- `GEMINI_API_KEY`: 비밀 API 키
- `GEMINI_VISION_MODEL`: 기본 모델 선택
- `GEMINI_VISION_FALLBACK_MODEL`: 대체 모델
- 호출 시간 초과 및 재시도 설정
- 하루 최대 호출량 또는 월별 사용량 추적

보안 및 운영:
- API 키는 프론트엔드나 로그에 절대 노출하지 않는다.
- 키가 없을 때 AI 기능을 비활성화하고 `API_KEY_REQUIRED` 상태를 명확히 표시한다.
- 관리자 설정 화면에서 키 등록 여부와 연결 테스트를 제공한다.
- 관리자 화면에는 키의 마지막 4자리만 표시한다.
- 호출 횟수, 성공률, 추정 비용을 기록한다.

---

## PHASE C. AI 명함 → 고객 CRM 자동 등록

### 1. 명함 처리 과정
1. 사용자가 명함 사진 업로드 또는 카메라 촬영
2. `GeminiVisionService`가 텍스트와 레이아웃 분석
3. 고객 후보 데이터 생성:
   - 이름
   - 직함/직책
   - 회사명
   - 휴대전화
   - 회사 전화
   - 이메일
   - 회사 주소
   - 주요 메모
4. 기존 CRM 고객과 전화번호/이메일 중복 비교
5. 사용자 확인 및 수정 화면 표시
6. 확인 버튼 클릭 시 CRM 고객으로 최종 저장

### 2. 고객 모델 보강
- `job_title`: 직함/직책
- `company_name`: 회사명
- `company_address`: 회사 주소
- `source`: `"BUSINESS_CARD_AI"`
- 원본 명함 이미지 경로 및 신뢰도 점수 저장

---

## PHASE D. AI 거래서류 → 거래 관리 자동 입력

### 1. 처리 대상 서류
- 자동차 양도증명서 (매매계약서)
- 차량 매매 정산서
- 상품화 비용 내역서
- 계좌 입출금 거래내역 캡처

### 2. 추출 정보
- 거래 일자
- 거래 유형: `PURCHASE`, `SALE`, `EXPENSE`, `DEPOSIT`
- 차량 정보: 차량번호, 차대번호(VIN)
- 상대방 정보: 고객명, 연락처, 상사명/딜러명
- 금액: 매매대금, 부가세, 취등록세 대행금, 알선수수료, 상품화비용 등
- 서류 진위성 검증 플래그: 공식 관인/서명 감지 여부

### 3. 기존 시스템 연결
- 차량번호 또는 VIN으로 기존 차량 자동 검색 및 연결
- 고객명과 전화번호로 기존 고객 자동 검색 및 연결
- 매칭 성공 시 초안(Draft) 자동 완성
- 매칭 실패 시 신규 등록 옵션 제공

### 4. 거래 원장 보호 규칙
- 추출 결과는 즉시 확정하지 않고 `TransactionDraft` 상태로 보관
- 관리자가 금액과 항목을 확인하고 승인해야 공식 거래 원장에 반영
- **입금 내역만으로 차량 판매 완료 처리를 하지 않는다.**
- 실제 거래 승인 전까지 실매출, ROI, RL Reward에 미검증 거래를 합산하지 않는다 (`is_verified_sale=False` 유지).

---

## PHASE E. 공통 문서 처리 아키텍처

- `DocumentProcessingStatus`: `UPLOADED` → `PROCESSING` → `EXTRACTED` → `NEEDS_REVIEW` → `APPROVED` / `REJECTED` / `FAILED`
- 이미지 저장: `data/uploads/documents/YYYY/MM/`
- 파일 검증: 허용 형식(JPEG, PNG, WebP, PDF), 최대 크기(15MB), 매직 바이트 검사
- 보안 감사 로그: 업로드 일시, IP, 파일 SHA-256 해시, 처리 결과

---

## PHASE F. 화면 UI 개선

1. 고객 관리 뷰:
   - `[명함 촬영]`, `[명함 이미지 업로드]` 버튼
   - AI 추출 미리보기 및 수정 모달
   - 중복 고객 경고 및 병합 안내
2. 거래 관리 뷰:
   - `[거래서류 촬영]`, `[거래내역 업로드]` 버튼
   - AI 거래 초안 확인 및 차량/고객 매칭 모달
3. 관리자 설정:
   - Gemini Vision 연결 상태 뱃지
   - 키 등록 여부, 모델 선택, 연결 테스트 버튼, 사용량 통계 패널

---

## PHASE G. 검증 및 테스트 요건

1. `scripts/test_directive_050c.py` 작성 (16대 검증 항목)
2. 인증 복구 검증:
   - 세션 없이 접근 시 401 처리
   - 정상 로그인 후 기존 차량 10건, 신규 차량 10건 상세조회 성공
3. Gemini Vision 검증:
   - 키 미설정 시 `API_KEY_REQUIRED` 정상 응답
   - 더미/실제 이미지로 명함 구조화 파싱 검증
   - 서류 이미지로 거래 초안 구조화 파싱 검증
4. 무결성 격리 검증:
   - 초안 서류가 공식 거래 및 실매출/RL Reward에 오염되지 않음 확인
5. 회귀 테스트:
   - 046-D (13/13), 047 (12/12), 048 (12/12), 049 (14/14), 050 (14/14) 100% 통과
6. Playwright 실측 스크린샷 4종:
   - `050c_vehicle_detail_authenticated.png`
   - `050c_business_card_crm_modal.png`
   - `050c_transaction_document_modal.png`
   - `050c_gemini_vision_settings.png`
