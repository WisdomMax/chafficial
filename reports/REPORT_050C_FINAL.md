# CHA-FICIAL DIRECTIVE 050-C 최종 완료 보고서
## AUTH RECOVERY + GEMINI VISION CRM AUTOMATION
### 차량 상세조회 정상화 및 AI 명함·거래서류 자동 인식

**발신:** Gemini Antigravity (Advanced Agentic Coding)  
**수신:** ChatGPT 총괄 기술감독 및 사용자  
**우선순위:** P0 긴급 버그 수정 + AI 업무 자동화 완수  
**기준 커밋:** `52121a2` $\rightarrow$ **작업 브랜치:** `feat/directive-050c-auth-gemini-vision-crm`  
**완료 일시:** 2026-10-26 (KST)  
**종합 검증 결과:** **16대 필수 검증 항목 16/16 100% ALL PASS** (046-D, 047, 048, 049, 050 전체 100% 무결성 통과)

---

## 1. 지침 개요 및 문제 해결 요약

### A. 차량 상세조회 401 오류 및 세션 인증 복구 (PHASE A)
- **원인 분석**:
  - 기존 백엔드 차량 목록 API(`GET /api/vehicles`)는 미인증 허용이었으나, 상세 조회(`GET /api/vehicles/{id}/detail`) 및 마스터 조회 API는 엄격한 세션 인증(`require_auth`)이 강제되어 있었습니다.
  - 프론트엔드 UI에 관리자 로그인 모달 및 세션 복구 메커니즘이 누락되어, 비로그인 상태 방문 시 401 오류와 함께 반복적인 브라우저 `alert` 창이 발생하는 결함이 확인되었습니다.
- **해결 내역**:
  - `GET /api/auth/me` 엔드포인트 구현: 세션 유효성, 사용자명(`admin`), 역할(`ADMIN`)을 정규 반환.
  - 프론트엔드 `safeFetch` 통신 래퍼 구축: `credentials: 'include'` 기본 적용, 401 발생 시 반복 alert 대신 비간섭형 토스트 안내 및 관리자 로그인 모달 자동 활성화, 404 및 500 에러를 명확히 구분하여 로깅.
  - 상단 헤더에 관리자 로그인/로그아웃 뱃지 배치 및 `#adminLoginModal` 인터랙티브 구현.
  - **검증 완료:** 로그인 세션으로 기존 차량 10건 및 신규 등록 차량 10건 연속 상세조회 100% 정상 작동 (200 OK).

### B. Gemini Vision 공통 모듈 (`GeminiVisionService`) 개발 (PHASE B)
- **위치**: `src/chaficial/platform/ai/vision.py`
- **모델 아키텍처**:
  - 기본 모델: `gemini-flash-latest` (호환: `gemini-2.0-flash`, `gemini-1.5-flash`)
  - 대체 저비용 모델: `gemini-flash-lite` (호환: `gemini-1.5-flash-8b`)
  - 자동 폴백 및 지수 백오프 재시도 (30초 타임아웃, 2회 재시도).
- **보안 및 감사 규정 엄격 준수**:
  - API 키 노출 원천 차단: 브라우저/로그/커밋에는 `AIza...9xAb` 형식으로 마스킹된 키만 노출.
  - 키 미설정 시 크래시 없이 `API_KEY_REQUIRED` 상태를 정직하게 명시.
  - 실시간 사용량 및 비용 감사: 호출 횟수, 토큰량, 추정 비용($/₩), 성공률을 DB(`gemini_usage_logs`) 및 메모리에 누적 집계.
  - 관리자 설정 화면에서 원클릭 연결 테스트(`POST /api/ai/vision/test-connection`) 및 키 동적 등록 지원.

### C. AI 명함 인식 $\rightarrow$ 고객 CRM 자동 등록 (PHASE C)
- **처리 흐름**: 명함 촬영/업로드 $\rightarrow$ 텍스트/구조 정밀 추출 $\rightarrow$ 중복 고객 비교 $\rightarrow$ 관리자 확인/수정 $\rightarrow$ CRM 정식 저장.
- **추출 스키마 (`CustomerCandidate`)**: 성명, 직함/직책, 회사명/상호, 휴대전화, 회사 전화, 이메일, 회사 주소, 메모.
- **고객 모델 확장 (`Customer`)**: `job_title`, `company_name`, `company_address`, `company_phone`, `email`, `source="BUSINESS_CARD_AI"`, `source_image_url`, `ai_confidence`.
- **중복 검사 및 연동**: 전화번호 및 이메일 기반 중복 감지 경고 배너 렌더링, 신규 등록 시 최초 상담 메모(Consultation) 자동 기록.

### D. AI 거래서류 $\rightarrow$ 거래 원장 자동 초안 생성 및 무결성 격리 (PHASE D)
- **대상 서류**: 자동차 양도증명서(매매계약서), 차량 매매 정산서, 상품화 비용 영수증, 통장 입출금 거래내역 캡처.
- **추출 스키마 (`TransactionDocumentExtract`)**: 서류 유형, 거래 구분(SALE/PURCHASE/EXPENSE), 일자, 차량번호, 차대번호(VIN), 상대방 성명/연락처, 총 금액, 공급가액, 부가세, 등록비, 알선수수료, 관인/서명 날인 여부.
- **자동 매칭 엔진**:
  - 차량번호/VIN으로 보유 재고 차량 자동 일치 검색 (`match_vehicle_for_document`).
  - 상대방 성명/연락처로 CRM 고객 또는 제휴 딜러 자동 일치 검색 (`match_party_for_document`).
- **무결성 가드 (Ground Truth 보호 원칙)**:
  - **입금 내역만으로 차량 판매 완료(SOLD) 처리를 원천 차단.**
  - 관리자의 명시적 승인 전까지 `is_verified_sale=False`, `settlement_status='PENDING'`으로 격리 보관하여 실매출, ROI, 강화학습 Reward를 절대 오염시키지 않음.

### E. 공통 문서 처리 보안 및 UI 개선 (PHASE E & F)
- 파일 바이너리 보안: 15MB 한도, 확장자 검사, 매직바이트 바이너리 위조 차단 (JPEG: `\xff\xd8\xff`, PNG: `\x89PNG`, WebP: `WEBP`, PDF: `%PDF-`), SHA-256 감사 로그 보존.
- UI 화면 구축:
  - 헤더: Gemini Vision AI 상태 뱃지 (활성화/키 필요) 및 관리자 로그인/로그아웃 버튼.
  - 고객 CRM: `[AI 명함 촬영 / 등록]` 버튼 및 실시간 추출/중복 확인 모달.
  - 거래 관리: `[AI 거래서류 분석 / 초안]` 버튼 및 차량/고객 매칭 초안 모달.
  - 설정: Gemini API 키 설정, 모델 선택, 연결 테스트, 실시간 호출 통계 대시보드.

---

## 2. 16대 필수 검증 항목 실행 결과 (16/16 ALL PASS)

| 번호 | 검증 항목 | 결과 | 세부 내용 |
| :---: | :--- | :---: | :--- |
| **01** | 비인가 요청 시 핵심 API 401 차단 검증 | **PASS** | 차량 상세 및 AI 설정 비인가 접근 시 HTTP 401 원천 차단 확인 |
| **02** | 관리자 로그인 및 보안 토큰/세션 쿠키 발급 검증 | **PASS** | `POST /api/auth/login` 200 OK, 64자리 보안 토큰 및 쿠키 발급 |
| **03** | `/api/auth/me` 세션 유효성 및 사용자 상태 검증 | **PASS** | `authenticated=True`, `username='admin'`, `role='ADMIN'` 정상 반환 |
| **04** | 로그인 세션으로 기존 차량 10건 연속 상세조회 | **PASS** | 기존 차량 10건 전건 HTTP 200 OK 무결성 응답 확인 |
| **05** | 신규 차량 10건 생성 및 상세조회 100% 정상 | **PASS** | 8대 영역 마스터 등록 10건 생성 후 전건 상세조회 성공 (10/10) |
| **06** | 존재하지 않는 차량 ID 조회 시 명확한 404 검증 | **PASS** | 미존재 차량 조회 시 HTTP 404 Not Found 및 정형화된 JSON 에러 바디 |
| **07** | Gemini Vision 키 미설정 시 안전한 응답 검증 | **PASS** | 크래시 없이 `API_KEY_REQUIRED` 상태 반환 및 설정 유도 안내 |
| **08** | Gemini Vision 키 마스킹 및 통계 조회 API 검증 | **PASS** | `masked_key` 앞뒤 4자리 외 마스킹(`AIza...`), 모델명, 통계 정상 제공 |
| **09** | 명함 이미지 $\rightarrow$ `CustomerCandidate` 추출 검증 | **PASS** | 성명, 직함, 회사명, 휴대전화, 유선전화, 이메일, 주소 구조화 추출 완료 |
| **10** | 명함 추출 고객 $\rightarrow$ CRM 등록 및 상담 메모 연동 | **PASS** | `source="BUSINESS_CARD_AI"`, 직함/회사 저장, 최초 상담 메모 연동 |
| **11** | 고객 전화번호 및 이메일 중복 검사 로직 검증 | **PASS** | 동일 전화번호 고객 중복 정상 감지 및 경고 안내 |
| **12** | 거래서류 $\rightarrow$ `TransactionDraft` 추출 검증 | **PASS** | 서류 유형, 거래 유형, 일자, 계약금액, 관인 날인 여부 구조화 파싱 완료 |
| **13** | 거래서류 차량번호 및 거래 상대방 자동 매칭 | **PASS** | 번호판 기준 차량 매칭(`99다 3881`), CRM 고객 매칭('차은우') 성공 |
| **14** | **무결성 격리 검증: 미승인 거래 실매출 오염 차단** | **PASS** | `is_verified_sale=False`, `settlement_status='PENDING'`, 차량 미판매 유지 |
| **15** | 서류 파일 유효성 및 바이너리 위조 차단 검증 | **PASS** | 위조 바이너리 400 차단, 15MB 한도 및 SHA-256 감사 로그 보존 |
| **16** | **전체 이전 지침 회귀 및 실측 스크린샷 4종 검증** | **PASS** | 046-D, 047, 048, 049, 050 100% PASS + 고해상도 스크린샷 4종 확인 |

---

## 3. 실측 UI 스크린샷 증빙 (Playwright 4종)

저장 경로: `docs/screenshots/directive_050c/`

1. **차량 상세 모달 정상 동작 증빙**:
   - 파일: `050c_vehicle_detail_authenticated.png` (189 KB)
   - 내용: 인증 세션 주입 후 8대 영역 제원, 사고/보험 이력, 영상 권한 뱃지가 완벽히 렌더링된 상세 화면.
2. **AI 명함 스캔 및 고객 CRM 자동 등록 모달**:
   - 파일: `050c_business_card_crm_modal.png` (185 KB)
   - 내용: 명함 사진 드롭존/촬영, 성명/회사/직책/연락처 자동 추출 폼, 기존 고객 중복 감지 배너 렌더링.
3. **AI 거래서류 분석 및 원장 매칭 초안 모달**:
   - 파일: `050c_transaction_document_modal.png` (189 KB)
   - 내용: 계약서/정산서 분석 결과, 차량번호 자동 매칭 성공 배너, 거래 상대방 매칭, 무결성 격리 안내.
4. **Gemini Vision AI 운영 설정 및 사용량 대시보드 모달**:
   - 파일: `050c_gemini_vision_settings.png` (185 KB)
   - 내용: 마스킹된 API 키 관리, 주/대체 모델 선택, 실시간 연결 테스트, 누적 호출수/성공률/추정비용 통계.

---

## 4. 커밋 및 원격 반영 안내

- **작업 브랜치**: `feat/directive-050c-auth-gemini-vision-crm`
- **핵심 수정 및 생성 파일**:
  - `src/chaficial/platform/app.py`: `/api/auth/me`, 전역 500 로깅, Gemini Vision 설정, 명함/거래서류 엔드포인트 8종.
  - `src/chaficial/platform/ai/vision.py`: `GeminiVisionService` 비전 클라이언트, 키 마스킹, 모델 폴백, 비용 감사.
  - `src/chaficial/platform/db.py`: `Customer` 명함 필드 확장, `DocumentReview` 7대 라이프사이클 확장, `GeminiUsageLog` 모델 및 DB 마이그레이션.
  - `src/chaficial/platform/models.py`: `CustomerCandidate`, `CustomerFromCardRequest`, `TransactionDocumentExtract`, `TransactionDraftConfirmRequest`, `GeminiKeySaveRequest`.
  - `src/chaficial/platform/service.py`: 명함 고객 등록, 중복 검사, 차량/고객 자동 매칭, 거래 초안 무결성 격리 확정.
  - `src/chaficial/platform/ui/index.html`: 상단 Gemini 뱃지, 로그인 버튼, 명함 촬영 모달, 거래서류 초안 모달, 토스트 알림, `safeFetch`.
  - `scripts/test_directive_050c.py`: 16대 필수 자동화 검증 스위트 (100% PASS).
  - `scripts/capture_050c_screenshots.py`: Playwright 실측 스크린샷 4종 자동 캡처 스크립트.
  - `docs/screenshots/directive_050c/*.png`: 실측 고해상도 UI 증빙 이미지 4종.
