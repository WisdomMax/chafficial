# CHA-FICIAL DIRECTIVE 051 최종 완료 보고서
## UNIFIED VEHICLE DETAIL & AUTONOMOUS CONTENT INTELLIGENCE
### 차피셜·차마트 공통 차량 상세 UI + AI 중고차 콘텐츠 연구소

**발신:** Gemini Antigravity  
**수신:** ChatGPT 총괄 기술감독 & 차마트 최고경영진  
**완료 일시:** 2026-10-27 (KST)  
**브랜치:** `feat/directive-051-unified-detail-content-lab`  
**전수 검증 결과:** 15대 필수 항목 **15/15 100% ALL PASS** (이전 지침 046-D, 047, 048, 049, 050, 050-C 전건 무결성 보존)

---

## 1. 개요 및 완수 선언

본 보고서는 `CHA-FICIAL DIRECTIVE 051`에 명시된 **[PART 1. 차피셜·차마트 공통 고급 차량 상세 UI & 브랜드 분리]** 및 **[PART 2. AI 중고차 콘텐츠 연구소 (Autonomous Content Intelligence Lab)]**의 전체 개발 및 전수 무결성 검증을 100% 완수했음을 보고합니다.

경쟁 유튜브 영상을 관찰하여 시장 관심사를 파악하되, 원문 대본이나 영상을 복제·보관하지 않고 차마트 25년 현장 노하우를 바탕으로 한 **독창적인 기획·대본·프롬프트 생성 파이프라인**을 완성하였습니다. 또한 내부 관리 플랫폼(차피셜)과 일반 고객 판매몰(차마트)이 동일한 `Vehicle Master` 데이터를 기반으로 **완벽히 일치하는 공통 고급 차량 상세 컴포넌트**를 공유하도록 구축하였습니다.

---

## 2. 핵심 구현 아키텍처 및 결과

### PART 1. 브랜드 분리 & 공통 고급 차량 상세 UI
1. **명확한 브랜드 및 플랫폼 구분**:
   - **차피셜 (CHA-FICIAL)**: 내부 운영/관리 플랫폼 (차량 등록, 재고, 소싱, CRM, 거래, 시세 분석, AI 콘텐츠 연구 및 제작). 관리자 인증(`chamart_auth`) 필수.
   - **차마트 (CHAMART)**: 일반 고객용 판매 웹사이트 (`/api/chamart/vehicles`, `/api/chamart/vehicles/{id}`). 승인된 실매물만 노출하며 매입원가(`purchase_price`), 상품화비용(`recon_cost`), 내부 수익/마진 정보, 관리자 메모 및 미승인 서류를 원천 차단.
   - 시장 관측 매물(`MARKET_OBSERVATION`) 및 미승인 제휴 매물은 차마트 공개 목록에서 100% 배제.

2. **공통 고급 차량 상세 모달 (`unifiedVehicleDetailModal`)**:
   - 관리자가 차량 테이블에서 행을 **더블클릭**하거나 `[공통상세]` 버튼을 누르면 차마트 고객용 상세페이지와 **동일한 공통 고급 UI** 팝업 표시.
   - **8대 필수 영역 완비**:
     1) **대형 차량 사진 갤러리**: 메인 대형 뷰어, 좌우 슬라이드 네비게이션, 썸네일 스트립 가로 바인딩
     2) **차량 가격 & 제원 헤더**: 모델명, 세부트림, 판매가격(만원), 월 납입금 가이드(60개월 5.9% 기준 원리금 균등 추산치), 연식/주행거리/연료/변속기/배기량/색상 4대 스펙 카드
     3) **카테고리별 표준 옵션 그리드**: 외관/휠, 실내/시트, 편의/멀티미디어, 안전/주행보조 카테고리별 정돈된 뱃지 리스트
     4) **사고·보험·성능점검 리포트**: 완전무사고 보증 마크, 주요 골격 손상 여부, 외판 손상 여부, 오일누유 점검 상태, 점검일자 요약
     5) **판매자 및 전시장 정보**: 차마트 장한평 본사(서울 동대문구 천호대로 329 장한평 매매단지 가온모터스 전시장), 담당 인증 딜러 프로필, 직통 연락처
     6) **구매 조건 및 실거래 시세 비교**: 동급 엔카/KB 시장 평균 시세 대비 절감액, 취등록세(7%) 추산치 및 법정 매도비 가이드
     7) **승인된 AI 홍보 영상**: 승인 완료된 영상 프로젝트 존재 시 비디오/유튜브 바로보기 임베드, 미제작 시 "AI 영상 제작 대기" 안내
     8) **고객 문의 및 방문 예약 폼**: 고객 성함, 연락처, 희망 방문일시, 문의내용 입력 및 즉시 신청 (`POST /api/chamart/consultations`)
   - **관리자 전용 기능 (Admin Context)**:
     - `isAdmin: true`일 때만 상단/하단에 관리자 바 표시: [공개/비공개 전환 토글], [마스터 제원 수정], [원가/수익 보기 토글 (매입가, 상품화비, 마진율 카드)]

---

### PART 2. AI 중고차 콘텐츠 연구소 (Autonomous Content Intelligence Lab)
1. **기존 엔진 100% 재사용 및 융합**:
   - `YouTubeConnector` (`src/chaficial/studio/connectors/youtube.py`): 공식 API 및 DEMO 쿼터 엄격 추적
   - `TopicDiscoveryEngine` (`src/chaficial/studio/topic_engine.py`): 통계 지표와 의미론적 6대 관심사 클러스터링
   - `ContentScriptEngine` (`src/chaficial/content/script_engine.py`): 한국어 음절 수 기반 30초 발화 정합성 및 스토리보드 연출 개요
   - `Wan3Adapter` / `Kling4Adapter` (`src/chaficial/content/adapters/`): 실사 품질 영상 생성 프롬프트 패키징

2. **지속 관찰 세션 제어 (Session Lifecycle)**:
   - 세션 상태 4단 전이: `IDLE` -> `RUNNING` -> `PAUSED` -> `STOPPED`
   - 체크포인트 자동 저장 (`last_checkpoint_json`): 프로그램 종료 후 재실행 시 마지막 키워드 위치에서 논스톱 관찰 재개
   - 일일 쿼터 사용량(10,000 units 한도) 초과 방지 가드 탑재

3. **AI 영상 내용 분석 및 저작권 엄격 준수**:
   - Gemini API 분석: 기본 모델 `gemini-flash-latest` (폴백 `gemini-2.5-flash`)
   - 공개 YouTube 영상 내용 직접 분석 불가 시 반드시 **`METADATA_ONLY`**로 정직하게 표기 (직접 본 것처럼 날조 금지)
   - 7대 핵심 분석 스키마 도출 (근본 주제, 핵심 질문, 사실확인 여부, 관심사, 타겟 차종, 형식, 차마트 독자 관점)
   - **저작권 원칙 절대 준수**: 경쟁 영상의 원문 대본이나 음성/영상 파일을 서버에 보관하거나 복제하지 않음

4. **독창적 주제 발굴 및 대본 자동 작성 (DRAFT)**:
   - 차마트 25년 현장 딜러 관점으로 재구성된 독립 기획 후보 추출 및 중복 유사 주제 자동 필터링
   - 주제 발굴 즉시 **8대 필수 구성요소**를 갖춘 독립 대본 초안 자동 작성:
     1) 독창적인 콘텐츠 제목 후보 3종
     2) 핵심 시청자 및 기획 의도
     3) 첫 3초 관심 유도 문장 (Hook)
     4) 새롭게 구성한 전체 대본 (약 30초 발화 분량)
     5) 장면별 연출 개요 (4-Scene Storyboard: 구도, 카메라 앵글, 인물 연기)
     6) 사실 검증 체크리스트
     7) 차마트 사장님께 확인할 질문 (Q&A 2종)
     8) 예상 영상 길이 (초)
   - **자동 승인 원천 금지**: 모든 초안은 `status = 'DRAFT'`로 격리 보존

5. **관리자 승인 및 수정 워크플로**:
   - 7대 서브 탭 완비 (`연구 현황`, `인기 관심 주제`, `AI 추천 아이디어`, `대본 초안`, `검토·수정`, `승인 완료`, `영상 제작 준비`)
   - **승인 무효화 무결성 규칙**: 대본을 직접 수정하거나 피드백을 반영하면 기존 승인이 즉시 무효화되고 `DRAFT`로 리셋 (승인 해시 초기화)
   - 관리자 공식 승인 시 전체 대본과 연출을 결합한 **SHA-256 해시(`approved_hash`)** 고정 보존

6. **승인 대본 전용 영상 프롬프트 변환**:
   - 미승인 대본(`DRAFT`/`REJECTED`)에 대해 프롬프트 변환 시도시 `HTTP 400 Bad Request`로 안전 차단
   - 승인된 대본에 한하여 Wan 3.0 / Kling 4.0 어댑터를 가동하여 장면별 프롬프트 및 마스터 프롬프트 생성 패키지 완성

7. **학습과 성능 개선의 정직한 구분**:
   - 사용자 피드백(`LIKE`, `DISLIKE`, `FACT_ERROR`, `ALREADY_COVERED`)에 따른 차마트 적합도 가중치 조정
   - 단순 DB 축적을 신경망 재학습이나 강화학습 완료로 부풀리지 않음 (실제 모델 학습 미수행 시 학습 완료라 주장하지 않음)

---

## 3. 15대 종합 검증 테스트 결과 (100% ALL PASS)

실행 명령: `PYTHONPATH=src .venv/bin/python scripts/test_directive_051.py`

| 번호 | 테스트 항목 | 검증 결과 | 상세 세부 사항 |
|:---:|:---|:---:|:---|
| **TEST 1** | 차마트 고객 공개 매물 목록 조회 | **PASS** | 공개 매물 147건 반환, 관측매물 완전 제외, 원가 필드 비노출 확인 |
| **TEST 2** | 차마트 고객 공개 상세 조회 | **PASS** | 8대 필수 영역 완비, purchase_price / recon_cost 원천 차단 확인 |
| **TEST 3** | 차마트 웹 고객 상담 및 방문 예약 접수 | **PASS** | 고객/상담 원장 자동 연계 및 상담 ID 발급 정상 확인 |
| **TEST 4** | 관리자 차마트 공개 토글 및 인증 가드 | **PASS** | 비인가 401 차단 및 인가 시 `is_public` 토글 정상 반영 |
| **TEST 5** | AI 콘텐츠 연구소 세션 상태 조회 | **PASS** | 세션 상태 RUNNING, 일일 쿼터 사용량 정상 추적 확인 |
| **TEST 6** | 지속 관찰 세션 라이프사이클 제어 | **PASS** | 시작(RUNNING) -> 일시정지(PAUSED) -> 재개(RUNNING) -> 종료(STOPPED) 전이 정상 |
| **TEST 7** | 영상 관찰 및 AI 내용 분석 사이클 | **PASS** | 단일 사이클 정상 실행, 신규 영상 관찰 및 독창적 주제 합성 완료 |
| **TEST 8** | 저작권 보호 무결성 검증 | **PASS** | 원문 대본 무단 저장 차단, METADATA_ONLY 투명 표기 확인 |
| **TEST 9** | 독창적 주제 후보 발굴 및 적합도 산출 | **PASS** | 차마트 25년 노하우 기반 적합도(95%) 산출 및 중복 유사 주제 차단 |
| **TEST 10** | 사용자 피드백 반영 및 가중치 조정 | **PASS** | LIKE 시 적합도 상승 및 추천 목록 랭킹 보정 정상 확인 |
| **TEST 11** | AI 독립 대본 초안 8대 요소 완비 및 DRAFT 유지 | **PASS** | 제목 3종, 훅, 4장면 스토리보드, Q&A 완비, 자동 승인 원천 차단 |
| **TEST 12** | 미승인 대본 프롬프트 변환 원천 차단 | **PASS** | DRAFT 대본 프롬프트 생성 시도 시 400 Bad Request 에러 방어 확인 |
| **TEST 13** | 관리자 대본 공식 승인 및 SHA-256 해시 보존 | **PASS** | 공식 승인 처리, 고유 SHA-256 내용 해시 원장 영구 보존 |
| **TEST 14** | 승인 대본의 영상 제작 프롬프트 변환 | **PASS** | Wan 3.0 / Kling 4.0 장면별 프롬프트 및 마스터 프롬프트 생성 완비 |
| **TEST 15** | 브라우저 실측 스크린샷 4종 존재 및 크기 검증 | **PASS** | 4종 전건 정상 캡처 완료 (모두 175KB ~ 415KB 고해상도) |

---

## 4. 실측 스크린샷 4종 내역

- **저장 위치**: `reports/screenshots_051/` 및 `docs/screenshots/directive_051/`

1. `051_chamart_customer_mall_view.png` (415 KB)
   - 장한평 중고차 인증 직영관 배너, 실시간 판매 매물 그리드, 가격 및 월 납입금 추산치 렌더링.
2. `051_unified_vehicle_detail_modal.png` (180 KB)
   - 차피셜·차마트 공통 고급 차량 상세 모달: 대형 사진 뷰어, 썸네일 스트립, 4대 스펙 카드, 카테고리별 옵션 뱃지, 성능점검 리포트, 시세 비교, 전시장 안내 및 방문예약 폼.
3. `051_content_lab_overview_and_session.png` (175 KB)
   - AI 콘텐츠 연구소: 세션 상태 뱃지, 5대 KPI 카드, 지속 관찰 타겟 키워드 칩, 최근 관찰 영상 카드 및 7대 서브 탭 바.
4. `051_content_lab_prompts_ready.png` (265 KB)
   - 승인 대본 기반 영상 프롬프트 패키지: Wan 3.0 장면별 프롬프트 카드, 카메라 무브먼트 지시문, Full Master Prompt 텍스트박스.

---

## 5. 변경된 파일 목록 및 Git 커밋

- `src/chaficial/platform/db.py`: `is_public` 필드 및 AI 콘텐츠 연구소 테이블 5종(`content_lab_sessions`, `observed_videos`, `content_topic_candidates`, `content_script_drafts`, `content_topic_feedbacks`) 추가 및 스키마 자동 마이그레이션.
- `src/chaficial/platform/service.py`: `get_chamart_public_vehicles`, `get_chamart_public_vehicle_detail`, `create_chamart_public_consultation`, `toggle_vehicle_public_status` 구현.
- `src/chaficial/platform/lab/service.py`: `ContentLabService` 신규 구현 (세션 제어, YouTube/Gemini 분석, 독립 주제/대본 생성, 해시 승인, 프롬프트 변환, 피드백).
- `src/chaficial/platform/app.py`: 차마트 고객 공개 API 3종, 관리자 공개 토글 1종, 콘텐츠 연구소 API 9종 엔드포인트 등록.
- `src/chaficial/platform/ui/index.html`: 사이드바 `nav-content-lab` 메뉴, 헤더 고객몰 토글, `view-content-lab` 섹션(7대 서브탭), `view-chamart-mall` 섹션, `unifiedVehicleDetailModal` 공통 고급 상세 모달 마크업 및 자바스크립트 제어 로직 탑재.
- `scripts/test_directive_051.py`: 15대 필수 항목 자동화 검증 스위트 신규 작성.
- `scripts/capture_051_screenshots.py`: Playwright 실측 스크린샷 4종 캡처 스크립트 작성.

---

## 6. 결론

DIRECTIVE 051에서 지시된 **"차피셜·차마트 공통 차량 상세 UI"**와 **"경쟁 영상 관찰 기반 독립적 AI 중고차 콘텐츠 연구소"**가 완벽하게 가동 중이며, 기존 046-D~050-C 전 지침의 데이터 무결성과 100% 호환됨을 최종 보고합니다.
