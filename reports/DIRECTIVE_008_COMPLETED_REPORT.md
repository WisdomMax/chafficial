# CHA-FICIAL AI PROJECT
## DIRECTIVE 008 실제 시장 데이터 확장 및 시세 정확도 검증 완료 보고서

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**일자:** 2026-10-21  
**대상 브랜치:** `feat/directive-008-market-data-expansion` (GitHub PR #8, base: PR #7)  
**검증 상태:** 67개 단위/통합 테스트 전수 통과 (`67 passed in 0.77s`)

---

## 1. 개요 및 개발 목표 달성

DIRECTIVE 008의 핵심 지시에 따라, 모바일 엔카 웹 브라우저 탐색 엔진을 안전하게 확장하여 아반떼 CN7 실매물 데이터를 대규모로 확보하고, 시세 평가 엔진(Opportunity Scorer)의 예측 오차 및 통계적 안정성을 전수 측정했습니다.

1. **파서 잔존 결함 100% 해소**:
   - `N Line` 우선 판별 후 `2.0 N` 검사로 고성능 N 오분류 원천 차단.
   - 단순 설명 문구("렌트이력 없음" 등)와 실제 렌트/리스 금융상품의 오탐 분리.
   - 모델연도(형식연도) 미표기 시 등록연도로 대체하는 임의 추정 제거 (`None` 유지).
2. **실매물 417건 확장 확보 (목표치 300건 대비 139% 달성)**:
   - 요청 제한(Rate Limit)을 철저히 준수하는 안전 지연(2.5~3.5초)과 체크포인트 자동 복원 체계를 구축하여 총 **417건**의 중복 없는 실측 데이터를 수집했습니다 (`templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv`).
3. **Leave-One-Out 기반 시세 예측 오차 및 민감도 전수 측정**:
   - 독립 표본 3대 이상 확보된 **362대**의 실매물에 대해 예측 오차 측정 완료:
     - **MAE (평균 절대 오차): 1,896,118원**
     - **MdAE (중앙값 절대 오차): 820,320원**
     - **MAPE (평균 백분율 오차): 11.28%**
     - **sMAPE (대칭 백분율 오차): 8.41%**
4. **점수와 다차원 신뢰도 분리**:
   - 데이터 완전성 점수(`data_completeness_score`), 시세 불확실성(`valuation_uncertainty_score`), 종합 신뢰도(`overall_confidence`)를 산출하여 신뢰도가 낮거나 사고 미확인인 매물 88건을 상세 확인 대상(`MANUAL_REVIEW_NEEDED`)으로 격리.

---

## 2. 잔존 파서 오류 수정 내역

| 결함 항목 | 수정 전 | 수정 후 (DIRECTIVE 008) | 검증 테스트 |
| :--- | :--- | :--- | :--- |
| **N vs N-Line 우선순위** | `"2.0 N" in text or " N " in text`가 먼저 실행되어 일부 N Line 매물이 N으로 오분류 위험 | `"N Line"`, `"N라인"`, `"N-Line"`을 최우선 판별한 후 고성능 N 검사 | `test_directive_008_n_line_vs_n_priority` 통과 |
| **금융상품 오탐** | `"렌트" in text` 등 단순 포함 검사로 "렌트이력 없음" 차량이 금융상품으로 오탐 | `r"렌트\s*월\s*[\d,]+만원"`, `장기렌트`, `렌트승계` 등 명시적 금융상품만 분리 | `test_directive_008_rental_explanation_vs_financial_product` 통과 |
| **모델연도 임의 추정** | `(22년형)` 미표기 시 최초등록연월의 연도(`2021`)로 강제 대체 | 모델연도 미표기 시 `None` 보존 (추정 주입 0%) | `test_directive_008_no_model_year_fallback_to_registration` 통과 |
| **파서 모듈 아키텍처** | 일회성 스크립트에 파서 로직 분산 | `src/chaficial/platforms/encar.py`의 `EncarCardParser`로 정규 모듈화 | 전체 테스트 모듈 임포트 연동 |

---

## 3. 확장 데이터셋 417건 품질 감사 요약

*세부 감사 문서: [`docs/DIRECTIVE_008_DATA_QUALITY_AUDIT.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/docs/DIRECTIVE_008_DATA_QUALITY_AUDIT.md)*

- **총 수집 건수:** **417건** (아반떼 CN7 실측 카드)
- **가상 기본값 주입률:** **0.0%** (모든 필드가 원본 실측 텍스트에 기반)
- **페이스리프트 분포:**
  - 전기형(`PRE_FACELIFT`): 363건 (87.1%)
  - 페이스리프트(`FACELIFT`, 더 뉴 아반떼): 54건 (12.9%)
- **파워트레인 라인 분포:**
  - 일반형(`STANDARD`): 374건 (89.7%)
  - N-Line(`N_LINE`): 19건 (4.6%)
  - 고성능 N(`N`): 24건 (5.8%)
- **상품 유형:**
  - 일반 판매(`CASH_OR_INSTALLMENT`): 405건 (97.1%)
  - 렌트/리스 월납입형(`RENT`/`LEASE`): 12건 (2.9%) $\rightarrow$ 시세 비교군에서 원천 분리
- **사고 정보 상태:**
  - 무사고(`NO_ACCIDENT`): 315건 (75.5%)
  - 단순수리(`SIMPLE_REPAIR`): 14건 (3.4%)
  - 미기재(`UNKNOWN`): 88건 (21.1%) $\rightarrow$ `MANUAL_REVIEW_NEEDED`로 격리

---

## 4. 시세 예측 오차(Valuation Accuracy) 및 통계 검증 결과

*상세 분석 보고서: [`reports/DIRECTIVE_008_VALUATION_ANALYSIS.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/DIRECTIVE_008_VALUATION_ANALYSIS.md)*

### 1) Leave-One-Out 교차 검증 오차 요약 (유효 표본 362대)
- **MAE (평균 절대 오차):** **1,896,118원**
- **MdAE (중앙값 절대 오차):** **820,320원**
- **MAPE (평균 백분율 오차):** **11.28%**
- **sMAPE (대칭 백분율 오차):** **8.41%**

> **실무적 해석:** 1,500만원 대 준중형 차량에서 MdAE 82만원, MAPE 11.2% 수준의 오차는 개별 차량의 유상 옵션(선루프, 내비게이션, 보스 오디오 등 약 100~200만원 차이)과 딜러별 협상 마진폭을 감안할 때 실무 운영에 충분히 활용 가능한 예측력입니다.

### 2) 주행거리 감가 계수(km_rate_per_10k) 민감도 분석
- **30만원 / 1만km:** MAE 1,939,812원 | MdAE 840,400원 | MAPE 11.53%
- **40만원 / 1만km (기준):** **MAE 1,896,118원 | MdAE 820,320원 | MAPE 11.28% (최적)**
- **50만원 / 1만km:** MAE 1,911,240원 | MdAE 835,000원 | MAPE 11.39%
- *결론:* 40만원 감가 계수가 가장 낮은 오차율을 보여 현행 파라미터가 유효함을 입증.

### 3) 데이터 완전성(사고 확인 여부)에 따른 오차 영향도
- **사고 상태 확인 매물 (308대):** MAE 1,745,210원 | **MAPE 10.42%** (정확도 우수)
- **사고 상태 미확인 매물 (54대):** MAE 2,756,800원 | **MAPE 16.18%** (오차 5.7%p 확대)
- *결론:* 사고 미확인 차량은 예측 불확실성이 크므로, 높은 점수가 나오더라도 자동 추천이 아닌 상세 확인 대상(`MANUAL_REVIEW_NEEDED`)으로 격리하는 설계가 통계적으로 타당함을 입증.

### 4) 상위 추천 순위 파라미터 안정성 (Rank Stability)
- 파라미터를 ±25% 변동(30만 vs 40만 vs 50만)시키더라도 상위 10대 핵심 추천 매물 중 **10대 중 9대(90%)가 그대로 유지**됨을 확인.

---

## 5. 산출물 파일 명세

1. **실제 수집 매물 데이터셋 (417건):**  
   [`templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv)
2. **상위 20대 기회 추천 매물 리스트:**  
   [`outputs/directive_008_top_20_opportunities.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008_top_20_opportunities.csv)
3. **상세 확인 필요 매물 리스트 (88건):**  
   [`outputs/directive_008_manual_review_needed.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008_manual_review_needed.csv)
4. **전체 매물 점수 중간 계산값 Breakdown:**  
   [`outputs/directive_008_score_breakdown.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008_score_breakdown.csv)
5. **데이터 품질 감사 보고서:**  
   [`docs/DIRECTIVE_008_DATA_QUALITY_AUDIT.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/docs/DIRECTIVE_008_DATA_QUALITY_AUDIT.md)
6. **시세 예측 오차 심층 분석 보고서:**  
   [`reports/DIRECTIVE_008_VALUATION_ANALYSIS.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/DIRECTIVE_008_VALUATION_ANALYSIS.md)

---

## 6. GitHub PR #8 생성 준비 및 단위 테스트 현황

- **PR 브랜치:** `feat/directive-008-market-data-expansion`
- **베이스 브랜치:** `feat/directive-007-real-listing-poc` (PR #7)
- **Pytest 검증 결과:** **67개 전수 통과** (`67 passed in 0.77s`)
- **Git 커밋 준비 완료.**

총괄 감독(ChatGPT)께 본 DIRECTIVE 008 성과의 검토 및 승인을 요청드립니다.