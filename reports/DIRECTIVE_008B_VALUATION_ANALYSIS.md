# CHA-FICIAL AI PROJECT
## DIRECTIVE 008-B 실차 중심 시세 예측 오차 및 시장 데이터 검증 보고서 (Valuation Analysis)

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**기준 데이터셋:** `templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv` (총 417건 광고 / 282대 고유 실차)  
**데이터셋 SHA-256:** `657e1c2efb48d5b640ca4e4fa4dd01ffbcc24873cb1709e225d850468cba14a9`  
**평가 표본:** 고유 실차 기준 유효 평가 **224대** (광고 레코드 기준: 357건)  
**원시 결과 CSV:** [`outputs/directive_008b_vehicle_valuation_records.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008b_vehicle_valuation_records.csv)  
**일자:** 2026-10-21  

---

## 1. 정통 MAPE 공식 적용 및 고유 실차 vs 광고 레코드 평가 비교

DIRECTIVE 008-B의 지침에 따라 실제 등록 호가($\text{actual\_price}$)를 분모로 사용하는 정통 MAPE 공식을 적용했습니다.

$$\text{APE} = \frac{|\text{actual\_price} - \text{predicted\_fair\_value}|}{\text{actual\_price}} \times 100$$

### 평가 집계 단위별 시세 예측 오차 비교

| 평가 집계 단위 | 유효 평가 표본 | MAE (원) | MdAE (원) | MAPE (%) | sMAPE (%) | 베이스라인 대비 MAE 개선율 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **고유 실차 단위 (Canonical Vehicles)** | **224대** | **2,287,287원** | **1,025,750원** | **9.98%** | **10.39%** | **+24.58%** |
| **광고 레코드 단위 (All Listings)** | **357건** | **2,028,291원** | **911,220원** | **8.67%** | **9.05%** | **+30.09%** |

### 베이스라인(단순 코호트 중앙가) 대비 상태보정 모델 성능 비교 (고유 실차 기준)
- **베이스라인 (단순 코호트 중앙가):** MAE **3,032,924원** | MdAE **1,905,000원** | MAPE **14.97%**
- **상태보정 모델 (주행거리/사고감가 반영):** MAE **2,287,287원** | MdAE **1,025,750원** | MAPE **9.98%**
- **오차 감소율 (개선폭):** MAE **+24.58% 개선**, MAPE **+33.33% 개선**

---

## 2. 오차 분위수 분포 (고유 실차 224대 기준)

| 분위수 | 절대 가격 오차 (원) | 백분율 오차 (MAPE %) | 통계적 해석 |
| :---: | :---: | :---: | :--- |
| **P50 (중앙값)** | **1,025,750원** | **6.38%** | 전체 고유 실차의 50%가 이 오차 범위 이내에 위치 |
| **P75** | **1,969,956원** | **12.32%** | 전체 고유 실차의 75%가 이 오차 범위 이내에 위치 |
| **P90** | **3,575,816원** | **24.74%** | 상위 10% 극단치를 제외한 대다수 실차의 오차 상한 |
| **P95** | **4,283,570원** | **29.63%** | 95% 통계적 신뢰 한계 |

---

## 3. 연식 확정 표본 vs 연식 미확인 표본 분리 통계 (고유 실차 기준)

| 집단 구분 | 고유 실차 수 | MAE (원) | MdAE (원) | MAPE (%) | 통계적 특성 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **연식 확정 표본 (`CONFIRMED_YEAR`)** | **133대** | **1,773,299원** | **935,800원** | **9.52%** | 형식연도 확정으로 시세 정확도 최고 수준 |
| **연식 미확인 표본 (`UNKNOWN_YEAR`)** | **91대** | **3,038,499원** | **1,276,400원** | **10.66%** | 연식 미상에 따른 편차 반영, 신뢰도 LOW 강제 |

---

## 4. 주요 코호트별 오차 현황 (고유 실차 상위 8개 코호트)

| 정밀 코호트 키 (제조사_모델_세대_서브_라인_연식_트림_연료) | 유효 실차 수 | MAE (원) | MdAE (원) | MAPE (%) |
| :--- | :---: | :---: | :---: | :---: |
| `현대_아반떼_CN7_PRE_FACELIFT_STANDARD_UNKNOWN_YEAR_모던_가솔린` | **41대** | 3,153,972원 | 1,312,620원 | 11.49% |
| `현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2021_인스퍼레이션_가솔린` | **23대** | 1,318,517원 | 998,360원 | 9.37% |
| `현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2021_모던_가솔린` | **21대** | 1,042,056원 | 816,300원 | 7.52% |
| `현대_아반떼_CN7_FACELIFT_STANDARD_2024_모던_가솔린` | **16대** | 4,099,958원 | 798,640원 | 11.15% |
| `현대_아반떼_CN7_PRE_FACELIFT_STANDARD_UNKNOWN_YEAR_인스퍼레이션_가솔린` | **16대** | 1,468,338원 | 1,240,840원 | 9.84% |
| `현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2023_모던_가솔린` | **14대** | 1,195,209원 | 615,160원 | 7.25% |
| `현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2023_인스퍼레이션_가솔린` | **9대** | 1,060,931원 | 961,419원 | 5.74% |
| `현대_아반떼_CN7_PRE_FACELIFT_STANDARD_2023_스마트_가솔린` | **9대** | 2,110,369원 | 1,557,580원 | 14.06% |

---

## 5. 주행거리 감가 계수(km_rate_per_10k) 민감도 분석 (고유 실차 기준)

| 감가 계수 (1만km당) | 평가 실차 수 | MAE (원) | MdAE (원) | MAPE (%) | sMAPE (%) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **30만원 / 1만km** | 224대 | 2,414,721원 | 1,216,662원 | 10.77% | 11.19% |
| **40만원 / 1만km (기준)** | 224대 | 2,287,287원 | 1,025,750원 | 9.98% | 10.39% |
| **50만원 / 1만km** | 224대 | 2,174,687원 | 900,450원 | 9.22% | 9.66% |

> **판정:** 3가지 감가 계수 중 **50만원/1만km** 설정이 MAE 2,174,687원으로 고유 실차 기준에서도 가장 낮은 오차를 기록했습니다.

---

## 6. 산출물 파일 명세

1. **실제 수집 광고 데이터셋 (417건):**  
   [`templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv)
2. **고유 실차(282대) 대표 데이터셋:**  
   [`templates/DIRECTIVE_008B_UNIQUE_VEHICLES.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/templates/DIRECTIVE_008B_UNIQUE_VEHICLES.csv)
3. **원시 시세 예측 오차 전수 레코드 (비교표본 ID 포함):**  
   [`outputs/directive_008b_vehicle_valuation_records.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008b_vehicle_valuation_records.csv)
4. **실차 단위 중복 제거 완료 Top 20 기회 추천 매물:**  
   [`outputs/directive_008b_top_20_unique_opportunities.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008b_top_20_unique_opportunities.csv)
5. **실차 중복 등록 감사표:**  
   [`outputs/directive_008b_duplicate_vehicle_audit.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_008b_duplicate_vehicle_audit.csv)
