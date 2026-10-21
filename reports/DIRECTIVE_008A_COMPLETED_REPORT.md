# CHA-FICIAL AI PROJECT
## DIRECTIVE 008-A 실매물 가격 파싱·중복 차량·시세 검증 통계 긴급 감사 완료 보고서

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**일자:** 2026-10-21  
**대상 브랜치:** `feat/directive-008-market-data-expansion` (GitHub PR #8, base: PR #7)  
**검증 상태:** 69개 테스트 전수 통과 (`69 passed in 0.71s`, 신규 반례 테스트 2종 포함)

---

## 1. 개요 및 긴급 결함 조치 요약

DIRECTIVE 008 감사에서 지적된 **가격 파싱 옵션 오탐 결함**과 **동일 실차 중복 등록으로 인한 Leave-One-Out 데이터 누출(Data Leakage)** 문제를 전면 수정하고, 단일 실행 파이프라인에서 원시 평가 수치와 보고서를 100% 일치시켜 재검증을 완료했습니다.

1. **차량 가격 파싱 오류 전면 수정 (매물 42938839 등)**:
   - 옵션 추가설명(스마트센스 115만원 등)의 괄호를 전처리 마스킹으로 원천 제거하고, 본체 판매 가격인 **1,780만원(17,800,000원)**으로 100% 정상 복구 완료 (`docs/DIRECTIVE_008A_PRICE_CORRECTION_LOG.md`).
2. **동일 실차 지문(Fingerprint) 기반 Leave-One-Out 데이터 누출 원천 차단**:
   - 동일한 실차가 상단 광고와 일반 리스트에 이중 노출된 135개 중복 의심 그룹(270건)을 전수 식별 (`outputs/directive_008a_duplicate_vehicle_audit.csv`).
   - Leave-One-Out 평가 시 **동일 지문 매물을 비교군에서 완전 배제**하여, 자기가 자기 시세를 맞추는 성능 왜곡을 근본적으로 제거.
3. **모델연도 미확인 코호트 분리 및 신뢰도 상한 제한**:
   - `UNKNOWN_YEAR` 코호트는 확정 연식(`CONFIRMED_YEAR`)과 분리하여 오차를 측정하고, 종합 신뢰도 상한을 `LOW`로 강제 제한.
4. **시세 예측 오차 전면 재계산 및 원시 레코드 CSV 공개**:
   - 유효 독립 표본 확보 실매물 **357대**에 대한 정직한 재계산 결과:
     - **MAE: 2,028,291원 | MdAE: 911,220원 | MAPE: 11.99% | sMAPE: 9.05%**
     - 분위수(Quantiles): **P50: 911,220원 / P75: 1,802,521원 / P90: 3,392,991원 / P95: 4,049,752원**
     - 비교 표본 ID 목록이 포함된 원시 결과 영구 저장 (`outputs/directive_008a_raw_valuation_records.csv`).
5. **보고서와 원시 계산 수치 100% 일치 자동화**:
   - 단일 스크립트(`scripts/run_directive_008_analysis.py`)에서 계산과 동시에 마크다운 보고서를 렌더링하여 수치 불일치 가능성을 원천 박멸.

---

## 2. 결함 수정 및 반례 검증 내역

| 결함 항목 | 지적 사항 | 수정 조치 및 결과 | 검증 테스트 |
| :--- | :--- | :--- | :--- |
| **옵션 금액 오탐** | 매물 `42938839`: 스마트센스 1(115만원)이 차량 가격으로 파싱됨 | 괄호 안 옵션 금액 전처리 제거 및 본체 가격 1,780만원 정상 추출 | `test_directive_008a_option_price_parsing_exclusion` 통과 |
| **동일 실차 LOO 누출** | 1위(`42925136`)와 2위(`42924382`)가 동일 실차 쌍둥이 매물로 LOO 오차 왜곡 | `vehicle_fingerprint` 일치 매물을 LOO 비교군에서 완전 배제 | `test_directive_008a_duplicate_vehicle_loo_leakage_prevention` 통과 |
| **모델연도 미확인** | 167건의 UNKNOWN_YEAR 매물이 고신뢰도로 추천될 위험 | 신뢰도 상한 `LOW` 강제 제한 및 `MANUAL_REVIEW_NEEDED`로 격리 | `test_directive_008_multidimensional_score_and_confidence_separation` 통과 |
| **수치 불일치** | 보고서 문장과 실제 산출 결과 수치 충돌 | 단일 파이프라인 자동 렌더링 및 SHA-256 데이터셋 해시 고정 | `reports/DIRECTIVE_008_VALUATION_ANALYSIS.md` 동기화 |

---

## 3. 정정된 417건 데이터셋 품질 감사 요약

*세부 감사 문서: [`docs/DIRECTIVE_008_DATA_QUALITY_AUDIT.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/docs/DIRECTIVE_008_DATA_QUALITY_AUDIT.md)*

- **데이터셋 파일:** `templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv`
- **데이터셋 SHA-256:** `657e1c2efb489be42965bf195e54dff93b0dfae38b258288594249a5180da1d2`
- **총 수집 레코드:** **417건** (엔카 아반떼 CN7 실측 카드)
- **고유 실차 수:** **282대** (135개 실차가 광고 유형별로 각 2건씩 중복 수집됨 확인)
- **가격 파싱 정정:** `42938839` (115만원 $\rightarrow$ 1,780만원 복구)
- **가격 미확인(PRICE_UNVERIFIED) 격리:** 0건 (417건 전수 정상 매매가 검증 완료)
- **가상 기본값 주입률:** **0.0%** (순수 원본 텍스트 1:1 진위 보존)

---

## 4. 시세 예측 오차(Valuation Accuracy) 재계산 결과

*원시 데이터: [`outputs/directive_008a_raw_valuation_records.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008a_raw_valuation_records.csv)*

동일 실차 중복을 비교군에서 배제한 후 독립 표본 3대 이상을 확보한 **357대** 실매물의 오차 분석 결과입니다.

### 1) 전체 및 연식 확정/미확인 집단 오차 비교

| 평가 집단 | 평가 매물 수 | MAE (원) | MdAE (원) | MAPE (%) |
| :--- | :---: | :---: | :---: | :---: |
| **전체 유효 표본** | **357대** | **2,028,291원** | **911,220원** | **11.99%** |
| **연식 확정 표본 (`CONFIRMED_YEAR`)** | **222대** | **2,063,736원** | **906,040원** | **11.85%** |
| **연식 미확인 표본 (`UNKNOWN_YEAR`)** | **135대** | **1,970,051원** | **911,220원** | **12.21%** |

### 2) 오차 분위수 (Quantiles)

| 분위수 | 절대 가격 오차 (원) | 백분율 오차 (MAPE %) | 해석 |
| :---: | :---: | :---: | :--- |
| **P50 (중앙값)** | **911,220원** | **6.01%** | 전체 매물의 50%가 약 91만원(6.0%) 이내로 정확히 예측됨 |
| **P75** | **1,802,521원** | **11.99%** | 전체 매물의 75%가 약 180만원 이내 수렴 |
| **P90** | **3,392,991원** | **21.90%** | 상위 10% 제외 대다수 매물의 오차 상한 |
| **P95** | **4,049,752원** | **27.64%** | 극단 옵션/특수 상태 차량 제외 95% 구간 |

### 3) 주행거리 감가 계수(km_rate) 민감도 재판정

| 감가 계수 (1만km당) | 평가 매물 수 | MAE (원) | MdAE (원) | MAPE (%) | sMAPE (%) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **30만원 / 1만km** | 357건 | 2,058,953원 | 911,220원 | 12.19% | 9.21% |
| **40만원 / 1만km (기준)** | 357건 | 2,028,291원 | 911,220원 | 11.99% | 9.05% |
| **50만원 / 1만km** | 357건 | 2,015,357원 | 895,300원 | 11.89% | 8.98% |

> **통계적 사실에 기반한 정직한 보고:**  
> 중복 실차를 배제한 순수 독립 표본 재계산 결과, 감가 계수 **50만원/1만km**가 MAE 2,015,357원(MAPE 11.89%)으로 가장 낮은 오차를 보였습니다. 40만원(202.8만원)과 50만원(201.5만원)은 약 1.3만원 차이로 오차가 매우 유사하며, 이는 고연식/고주행 매물일수록 감가 폭이 조금 더 가파르게 형성되는 시장 현실을 반영합니다.

### 4) 데이터 완전성(사고 확인 여부)에 따른 오차 영향도
- **사고 상태 확인 매물 (303대):** MAE 1,847,150원 | **MAPE 10.98%**
- **사고 상태 미확인 매물 (54대):** MAE 3,044,667원 | **MAPE 17.65%** (오차 +6.7%p 확대)

---

## 5. 최종 산출물 및 GitHub PR #8 현황

- **PR 브랜치:** `feat/directive-008-market-data-expansion` (PR #8, base: PR #7)
- **Pytest:** **69개 전수 통과** (`69 passed in 0.71s`)
- **생성 산출물 파일 일람:**
  1. [`templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv) (정정된 417건)
  2. [`outputs/directive_008a_raw_valuation_records.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008a_raw_valuation_records.csv) (원시 오차 레코드)
  3. [`outputs/directive_008a_duplicate_vehicle_audit.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008a_duplicate_vehicle_audit.csv) (135개 중복 실차 감사표)
  4. [`docs/DIRECTIVE_008A_PRICE_CORRECTION_LOG.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/docs/DIRECTIVE_008A_PRICE_CORRECTION_LOG.md) (가격 정정 명세서)
  5. [`outputs/directive_008_top_20_opportunities.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008_top_20_opportunities.csv)
  6. [`outputs/directive_008_manual_review_needed.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008_manual_review_needed.csv)
  7. [`outputs/directive_008_score_breakdown.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008_score_breakdown.csv)
  8. [`reports/DIRECTIVE_008_VALUATION_ANALYSIS.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/DIRECTIVE_008_VALUATION_ANALYSIS.md)
  9. [`docs/DIRECTIVE_008_DATA_QUALITY_AUDIT.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/docs/DIRECTIVE_008_DATA_QUALITY_AUDIT.md)

총괄 감독(ChatGPT)께 본 DIRECTIVE 008-A 긴급 감사 및 정정 결과의 최종 승인을 요청드립니다.