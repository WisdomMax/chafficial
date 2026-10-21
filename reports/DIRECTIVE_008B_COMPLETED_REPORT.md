# CHA-FICIAL AI PROJECT
## DIRECTIVE 008-B 완결 보고서: 실차 중심 아키텍처 및 평가 통계 재현성 최종 감사

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**대상 저장소:** `https://github.com/WisdomMax/chafficial`  
**대상 브랜치:** `feat/directive-008-market-data-expansion` (PR #8)  
**기준 데이터셋:** `templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv`  
**데이터셋 SHA-256:** `657e1c2efb48d5b640ca4e4fa4dd01ffbcc24873cb1709e225d850468cba14a9`  
**작업 단계:** PHASE 1 / DIRECTIVE 008-B FINAL VERIFICATION  
**우선순위:** HIGH  
**작업 일시:** 2026-10-21  

---

## 0. 임무 수행 요약

DIRECTIVE 008-B 지침에 명시된 4가지 핵심 요구사항을 100% 충족하여 구현 및 검증을 완료했습니다.

1. **실차 지문(Vehicle Fingerprint) 재정의:** 가변적인 '가격' 속성을 지문에서 완전 배제하고 물리적 불변 제원만으로 지문을 재구성하여 가격 변동 시에도 동일 실차로 완벽 추적되도록 개선했습니다.
2. **Top 20 실차 단위 디듀플리케이션:** 점수 순 상위 매물 추천 시 동일 실차 지문을 가진 쌍둥이 매물 중 최고점 대표 1건(Canonical Record)만 선별하도록 필터링하여, Top 20 내 **동일 실차 중복 0건**을 달성했습니다.
3. **정통 MAPE 공식 및 집계 단위 명확화:** 실제 등록 호가($\text{actual\_price}$)를 분모로 하는 정통 MAPE 공식을 적용하고, **'광고 레코드 단위(417건)'** 통계와 **'고유 실차 단위(282대)'** 통계를 분리 집계했습니다.
4. **보고서 수치 불일치 0.00% 달성:** 단일 파이썬 스크립트 실행 메모리 상에서 원시 CSV와 감사 보고서, 시세 분석 보고서, 완결 보고서를 동시에 렌더링하여 데이터 SHA-256, MAE, MdAE, MAPE, 표본 수가 100% 일치하도록 보장했습니다.

---

## 1. 데이터셋 무결성 및 실차 식별 현황

| 측정 항목 | 관측치 | 무결성 검증 조치 |
| :--- | :---: | :--- |
| **총 관측 광고 레코드 수** | **417건** | 엔카 아반떼 CN7 실측 카드 전수 수집 |
| **식별된 고유 실차 수** | **282대** | 물리 불변 제원 지문(`vehicle_fingerprint`) 기준 |
| **동일 실차 중복 광고 그룹** | **135개 실차** | 동일 실차가 복수 딜러/상사에 중복 등록된 그룹 |
| **중복 등록된 총 광고 레코드 수** | **270건** | 최고 2회까지 중복 등록 확인 |
| **단독 등록 실차 수** | **147대** | 단일 광고로만 등록된 고유 실차 |
| **데이터셋 SHA-256 해시** | `657e1c2efb48d5b640ca4e4fa4dd01ffbcc24873cb1709e225d850468cba14a9` | 파일 변조 및 불일치 원천 차단 |
| **가상/임의 기본값 주입률** | **0.0%** | 누락 속성은 UNKNOWN 코호트로 분리 보존 |

---

## 2. 시세 예측 오차(Valuation Accuracy) 통계 검증

### 집계 단위별 오차 및 베이스라인 대비 성능 비교

$$\text{APE} = \frac{|\text{actual\_price} - \text{predicted\_fair\_value}|}{\text{actual\_price}} \times 100$$

| 집계 단위 및 모델 구분 | 유효 평가 표본 | MAE (원) | MdAE (원) | MAPE (%) | sMAPE (%) | 베이스라인 대비 MAE 개선 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **고유 실차 기준 (상태보정 모델)** | **224대** | **2,287,287원** | **1,025,750원** | **9.98%** | **10.39%** | **+24.58%** |
| **고유 실차 기준 (단순중앙가 베이스라인)** | 224대 | 3,032,924원 | 1,905,000원 | 14.97% | - | 기준점 (0.0%) |
| **광고 레코드 기준 (상태보정 모델)** | **357건** | **2,028,291원** | **911,220원** | **8.67%** | **9.05%** | **+30.09%** |

### 고유 실차 기준 오차 분위수 (Quantile Distribution)

| 분위수 | 절대 가격 오차 (원) | 백분율 오차 (MAPE %) | 해석 |
| :---: | :---: | :---: | :--- |
| **P50 (중앙값)** | **1,025,750원** | **6.38%** | 전체 고유 실차의 50%가 이 오차 범위 이내 |
| **P75** | **1,969,956원** | **12.32%** | 전체 고유 실차의 75%가 이 오차 범위 이내 |
| **P90** | **3,575,816원** | **24.74%** | 90% 실차의 오차 상한 |
| **P95** | **4,283,570원** | **29.63%** | 95% 신뢰 한계 |

---

## 3. 실차 단위 디듀플리케이션 Top 20 추천 결과

기존 008-A에서 발생했던 쌍둥이 매물(`42925136`과 `42924382`)의 1·2위 동시 진입 문제를 완벽히 해결했습니다.  
`deduplicate_by_fingerprint=True` 로직을 통해 동일 실차는 점수/신뢰도/완전성이 가장 높은 1건(Canonical Record)만 선별되었습니다.

- **Top 20 추천 매물 수:** 20대
- **Top 20 내 동일 실차 중복 수:** **0대 (100% 상이한 고유 실차)**
- **결과 파일:** [`outputs/directive_008b_top_20_unique_opportunities.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008b_top_20_unique_opportunities.csv)

---

## 4. 검증 테스트 결과 (69개 -> 72개)

1. `test_mape_denominator_is_actual_price`: MAPE 계산 시 분모가 예측가가 아닌 실제 등록 호가인지 수식 검증.
2. `test_top_20_unique_vehicles_no_duplicate_fingerprint`: Top 20 추천 결과 내 `vehicle_fingerprint` 중복이 0건인지 검증.
3. `test_fingerprint_excludes_price_invariant_to_price_change`: 가격 인하 스냅샷 발생 시에도 물리 제원 지문이 불변인지 검증.

**전체 테스트 결과: 72개 테스트 100% 통과 (PASS)**

---

## 5. 최종 산출물 및 아티팩트 명세

1. **실제 수집 광고 데이터셋 (417건):**  
   [`templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv)
2. **고유 실차 대표 데이터셋 (282대):**  
   [`templates/DIRECTIVE_008B_UNIQUE_VEHICLES.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/templates/DIRECTIVE_008B_UNIQUE_VEHICLES.csv)
3. **원시 시세 예측 오차 전수 레코드 (비교표본 ID 포함):**  
   [`outputs/directive_008b_vehicle_valuation_records.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008b_vehicle_valuation_records.csv)
4. **실차 단위 중복 제거 완료 Top 20 기회 매물:**  
   [`outputs/directive_008b_top_20_unique_opportunities.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008b_top_20_unique_opportunities.csv)
5. **실차 중복 등록 감사표:**  
   [`outputs/directive_008b_duplicate_vehicle_audit.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008b_duplicate_vehicle_audit.csv)
6. **품질 감사 보고서:**  
   [`docs/DIRECTIVE_008B_DATA_QUALITY_AUDIT.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/docs/DIRECTIVE_008B_DATA_QUALITY_AUDIT.md)
7. **시세 오차 정밀 분석 보고서:**  
   [`reports/DIRECTIVE_008B_VALUATION_ANALYSIS.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/DIRECTIVE_008B_VALUATION_ANALYSIS.md)
8. **GitHub PR #8:**  
   `https://github.com/WisdomMax/chafficial/pull/8`

총괄 감독(ChatGPT)의 최종 검토 및 DIRECTIVE 008 완결 승인을 정중히 요청드립니다.
