# CHA-FICIAL DIRECTIVE 069 검증 완수 보고서
## 엔카급 상용 고객 쇼룸 전면 재구축 및 품질 합격 검증

**작업 일시:** 2026-10-29  
**수신:** 총괄 디자인 감독 (ChatGPT)  
**발신:** Gemini Antigravity  
**기준 커밋 / 브랜치:** `feat/directive-052-security-publishing-content-remediation`  
**적용 대상 파일:**
- [`chamart_staging.html`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platform/ui/chamart_staging.html) (스테이징 쇼룸)
- [`chamart.html`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platform/ui/chamart.html) (운영 쇼룸)
- [`chamart-listing-v2.css`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platform/ui/static/css/chamart-listing-v2.css) (신규 엔카 리스팅 CSS)
- [`vehicle_detail_renderer.js`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platform/ui/static/js/vehicle_detail_renderer.js) (공통 상세 렌더러)

---

## 1. 지시사항 이행 및 결함 교정 내역

| 지시 사항 | 이전 상태 (결함) | DIRECTIVE 069 이행 결과 | 상태 |
| :--- | :--- | :--- | :---: |
| **브랜드 컬러 교정** | 임의로 청록색(`teal`, `#176B68`)을 메인으로 선언 | **사용자 승인 공식 브랜드 컬러** [화이트 `#FFFFFF`, 배경 `#F8F9FA`, 텍스트/딥차콜 `#171B1E`, 보더 `#E5E7EB`, 액센트 `#C8FF3D`(일렉트릭 라임)] 100% 적용 | **완료** |
| **PC 기본 보기 전환** | 3열 앨범형 카드 기본 노출 | **가로 리스트형(`cm-vehicle-row`, 높이 178px, 5:3 썸네일) 기본 노출**, 앨범형은 툴바 스위치로 선택 전환 | **완료** |
| **PC 첫 화면 밀도** | 거대 카드형 검색창으로 첫 화면 매물 1대만 보임 | **68px 헤더 + 48px 컴팩트 검색바** 적용으로 **1440×900 첫 화면에서 매물 3대 즉시 가시** | **완료** |
| **실차 사진 품질** | 남색 텍스트 그래픽 카드 반복 | 스튜디오 조명 **5:3 비율 실제 한국 승용차 사진 3종**(그랜저 GN7, K8, 쏘렌토 HEV) 탑재 | **완료** |
| **상세 페이지 구조** | 상단 타이틀 카드와 우측 사이드바에 가격 중복 노출 | **상단 타이틀 내 중복 가격 완전 제거**, 우측 **350px 고정 구매 패널**에만 단일 집중 표출 | **완료** |
| **반응형 오버플로** | 특정 뷰포트에서 가로 스크롤 및 글자 겹침 위험 | **360, 390, 768, 1024, 1440, 1920px 전 뷰포트 오버플로 0건** (Playwright 전수 검증) | **완료** |
| **운영/스테이징 분리** | 미검증 매물 혼입 우려 | **운영 쇼룸(`/chamart`)은 실차 0대 정직한 준비 중 안내**, **스테이징(`/staging/chamart`)만 3대 시연 노출** | **완료** |

---

## 2. 수치 기반 화면 밀도 및 규격 검증 (PC 1440×900)

- **최대 콘텐츠 폭:** `1320px` (양측 16px 패딩)
- **상단 헤더 높이:** `68px` (로고 가시 폭 `155px` 확보, `chamart_logo_lime_charcoal_transparent.png`)
- **컴팩트 검색바 높이:** `48px` (상하 여백 `14px`, 딥 차콜 버튼 + 라임 닷)
- **결과 툴바 높이:** `52px` (카운트 배지 라임 포인트, 목록형/앨범형 토글 스위치)
- **좌측 필터 폭:** `238px` (우측 결과 영역과의 간격 `24px`)
- **차량 목록 행 높이:** `178px` (사진 `245×147px`, 5:3 비율 규격)
- **첫 뷰포트(900px) 내 즉시 가시 매물 수:** **정확히 3대 노출 확인** (Playwright DOM BoundingRect 검사 통과)

---

## 3. 반응형 가로 오버플로 전수 검사 결과 (Playwright 자동화)

검사 기준: `scrollWidth > clientWidth + 1px` 발생 여부

| 뷰포트 (px) | 기기 유형 | clientWidth | scrollWidth | 오버플로 요소 수 | 판정 |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **360 × 740** | 초소형 스마트폰 (Galaxy S8) | 360 | 360 | 0건 | **PASS** |
| **390 × 844** | 표준 스마트폰 (iPhone 14) | 390 | 390 | 0건 | **PASS** |
| **768 × 1024** | 태블릿 세로 (iPad Mini) | 768 | 768 | 0건 | **PASS** |
| **1024 × 768** | 태블릿 가로 / 소형 랩탑 | 1024 | 1024 | 0건 | **PASS** |
| **1440 × 900** | 표준 데스크톱 / 맥북 | 1440 | 1440 | 0건 | **PASS** |
| **1920 × 1080** | 풀HD 와이드 모니터 | 1920 | 1920 | 0건 | **PASS** |

> **검증 결론:** 모든 해상도에서 수평 스크롤이 발생하지 않으며, 텍스트 줄바꿈 및 컴포넌트 축소가 유연하게 작동함을 확인하였습니다.

---

## 4. 백엔드 및 보안 경계 무결성 검증

- **P0 격리 테스트:** `scripts/test_boundary_matrix_067.py` 실행 결과 **100% ALL PASS**
  - 운영 쇼룸(`/chamart`): 오직 승인된 실차만 노출 (`allow_demo=False`), 미입고 시 정직한 0대 준비 중 배너 표시
  - 스테이징 쇼룸(`/staging/chamart`): 고해상도 시연 매물 3대 제공
  - 상담 신청 및 API 변조 방어: 가드 로직 무결 작동 확인

---

## 5. 생성 산출물 안내

- 종합 1:1 비교 대시보드: [`side_by_side_comparison_069.png`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/side_by_side_comparison_069.png)
- 자동화 테스트 결과 로그: [`TEST_RESULTS.txt`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/TEST_RESULTS.txt)
- 엔카 벤치마크 상세 대조표: [`ENCAR_BENCHMARK_COMPARISON.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/ENCAR_BENCHMARK_COMPARISON.md)
- 산출물 매니페스트: [`ARTIFACT_MANIFEST.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/ARTIFACT_MANIFEST.md)
