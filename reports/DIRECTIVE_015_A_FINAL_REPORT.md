# DIRECTIVE 015-A FINAL: OPPORTUNITY QUALITY & LEAKAGE HARDENING (실전 기회 매물 품질 정밀 감사 및 데이터 누수 차단 완료 보고서)

## 1. 개요 및 GitHub 동기화 현황
- **프로젝트**: 차피셜(CHA-FICIAL) 기회 매물 탐지 엔진 V1.1 정밀 품질 감사
- **공식 PR URL**: https://github.com/WisdomMax/chafficial/pull/13
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker` (PR #12 병합 커밋 `e23d2029...` 최신)
- **작업(Head) 브랜치**: `feat/directive-015-opportunity-intelligence-v1`
- **판정 후속 조치**: 총괄 감독(ChatGPT)님의 DIRECTIVE 015-A 5대 핵심 결함 수정 지침 전수 완비

---

## 2. 5대 핵심 결함 수정 및 감사 분석 내역

### 2.1 [지침 1] 연식 누락 및 코호트 신뢰성 수정
- **원인 분석**:
  - 기존 1위 후보였던 `42872963` 및 일부 매물은 최초 수집 당시 모델 연식 필드가 공백이었고, 차량 지문에 `NOYEAR`로 기록되어 있었습니다 (`현대_아반떼_CN7_FACELIFT_STANDARD_2025-04_NOYEAR_38185_하이브리드_인스퍼레이션`).
  - 이로 인해 연식이 확정되지 않은 상태에서 임의 코호트에 편입되어 시세 왜곡 및 부당한 고득점이 발생할 위험이 있었습니다.
- **조치 완료**:
  - `model_year`와 `vehicle_fingerprint` 양쪽에서 4자리 정규 연식을 추출하는 정밀 로직을 단일화하였습니다.
  - 연식이 `NOYEAR`, 빈값, 또는 비정상값인 차량은 `UNKNOWN_YEAR` 코호트로 완전 격리하였으며, **`INSUFFICIENT_DATA` (연식 미확인 사유)로 분류하여 `PRIORITY_REVIEW` 진입을 원천 차단**하였습니다.
- **기존 1위 `42872963` 재평가 결과**:
  - `PRIORITY_REVIEW` (78.9점) $\rightarrow$ **`INSUFFICIENT_DATA` (연식 정보 미확인으로 정밀 시세 비교 불가, 보류 처리)**로 올바르게 재분류되었습니다.

### 2.2 [지침 2] 동일 실차 중복 매물 클러스터링 및 시세 왜곡 차단
- **지적된 매물 쌍 실사 결과**:
  1. `42852685` / `42849633`: 동일 지문(`...NOYEAR_5993_가솔린_모던`), 동일 가격(1,650만), 동일 주행(5,993km) $\rightarrow$ **100% 동일 실차 중복 광고 확정** (연식 미확인으로 `INSUFFICIENT_DATA` 보류)
  2. `42911910` / `42906948`: 동일 지문(`...2024_46530_하이브리드_모던`), 동일 가격(2,149만), 동일 주행(46,530km) $\rightarrow$ **100% 동일 실차 중복 광고 확정**
  3. `42866420` / `42863742`: 동일 지문(`...2024_31066_하이브리드_모던`), 동일 가격(2,190만), 동일 주행(31,066km) $\rightarrow$ **100% 동일 실차 중복 광고 확정**
  4. `42453171` / `42453169`: 동일 지문(`...NOYEAR_12526_가솔린_NOTRIM`), 동일 가격(2,110만), 동일 주행(12,526km) $\rightarrow$ **100% 동일 실차 중복 광고 확정**
- **조치 완료**:
  - **코호트 시세 왜곡 차단**: 동일 실차 지문(`vehicle_fingerprint`)을 가진 매물들은 코호트 표본군 구축 시 대표 1건만 반영하여 동일 매물 이중 집계로 인한 중앙값 왜곡을 원천 차단하였습니다.
  - **추천 목록 중복 배제**: 추천 목록에도 대표 1건만 등록하고 `duplicate_listing_ids` 필드에 동반 광고 ID를 명시하여 딜러 혼란을 방지하였습니다.

### 2.3 [지침 3] 순수익(Net Profit)과 목표마진(Target Margin) 수학적 분리
- **원인 분석**:
  - 기존 `_calc_scenario()`에서 목표마진(50만원)을 비용(Cost) 배열에 합산 차감한 값을 `net_profit`으로 표기하여 재무적 정의 혼동이 있었습니다.
- **수정 완료 (수학적 정의 확립)**:
  - $\text{Estimated Gross Spread} = \text{Expected Sale Price} - \text{Purchase Price}$ (예상 총마진)
  - $\text{Estimated Operating Cost} = \text{Reconditioning Cost} + \text{Logistics Cost}$ (실제 예상 운영비용: 상품화비 80만 + 탁송비 30만)
  - $\text{Estimated Net Profit} = \text{Gross Spread} - \text{Operating Cost}$ (실제 예상 순이익)
  - $\text{Target Margin} = 500,000원$ (비용이 아닌 기대 수익 판단 기준치)
  - $\text{Excess over Target} = \text{Net Profit} - \text{Target Margin}$ (목표 초과 달성액)

### 2.4 [지침 4] 과거 시점 데이터 누수(Data Leakage) 원천 차단 (`as_of_time`)
- **원인 분석**:
  - `evaluate_market_opportunities(as_of_time=...)`에 시점을 전달해도 SQL 쿼리에 반영되지 않아 미래 데이터가 조회되는 결함이 존재했습니다.
- **조치 완료**:
  - `s.observed_at <= :as_of_time`, `l.first_observed_at <= :as_of_time`, `pe.event_timestamp <= :as_of_time` 조건을 모든 서브쿼리와 이벤트 조회에 100% 적용하였습니다.
  - 동일 시각 스냅샷의 결정적 정렬을 위해 `ORDER BY s.observed_at DESC, s.snapshot_id DESC`를 적용하였습니다.
  - 미래 데이터를 추가해도 과거 시점 평가 결과가 100% 동일함을 증명하는 회귀 테스트(`test_as_of_time_prevents_future_data_leakage`)를 구축하였습니다.

### 2.5 [지침 5] 실제 영업 가능성과 시장 기회 분리
- **분리된 두 개의 독립 필드 관리**:
  - **`market_opportunity_grade` (시장 기회 등급)**: `PRIORITY_REVIEW`, `WATCHLIST`, `INSUFFICIENT_DATA`, `EXCLUDED`
  - **`partner_operational_suitability` (파트너 영업 적합성)**:
    - `LOCAL_OPERATIONAL`: 서울/장안평/수도권 명시 매물
    - `LOCATION_VERIFICATION_REQUIRED`: 지역 정보 미확인(`UNKNOWN`)
    - `REMOTE_REGION_UNSUITABLE`: 대구, 대전, 부산 등 원거리 지방 매물
- **정직한 데이터 공시**:
  - **서울/장안평 즉시 매입 가능 매물**: **0건** (현재 관측 데이터는 전국 표본으로 서울 명시 매물이 없음을 정직하게 명시)
  - **지역 실사 선행 조건부 검토 매물 (`UNKNOWN`)**: **169건**
  - **원거리 지방 매물**: **63건**

---

## 3. 수정 전후 실전 평가 결과 비교

| 항목 | DIRECTIVE 015 (수정 전) | DIRECTIVE 015-A (수정 후) | 변화 및 사유 |
| :--- | :---: | :---: | :--- |
| **총 평가 대상 매물** | 348대 (중복 매물 포함) | **232대 (고유 실차 기준)** | 동일 실차 중복 광고 116건 클러스터링 정제 |
| **`PRIORITY_REVIEW` (우선 검토)** | 20대 (5.7%) | **8대 (3.4%)** | 연식 미확인(NOYEAR) 차량 및 중복 광고 배제로 정밀화 |
| **`WATCHLIST` (추가 관측)** | 24대 (6.9%) | **8대 (3.4%)** | 모멘텀 및 마진 기준 재정렬 |
| **`INSUFFICIENT_DATA` (데이터 부족)** | 248대 (71.3%) | **196대 (84.5%)** | 연식 미확인 차량의 안전한 보류 편입 |
| **`EXCLUDED` (부적합)** | 56대 (16.1%) | **20대 (8.6%)** | 시세 대비 고가 매물 등 |
| **1위 후보 차량** | `42872963` (None년식, 78.9점) | **`42969608` (2024년식, 75.0점)** | 1위 차량 연식 2024년식 100% 확정 매물로 교체 |
| **1위 예상 순이익** | 745,000원 (목표마진 차감 후) | **4,150,000원 (순이익 정확 산출)** | 총마진 545만 - 운영비 130만 = 순익 415만 |

---

## 4. 정제된 우선 검토 (`PRIORITY_REVIEW`) 8대 후보 내역

| 순위 | 매물 ID | 차량 요약 | 현재 가격 | 코호트 시세 | 가격 우위 | 기회 점수 | 예상 순이익 | 목표초과분 | 지역 (영업 적합성) | 비고 |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | `42969608` | 현대 아반떼 CN7 (2024년식, 42,076km) | 1,690만원 | 2,235만원 | **+24.4%** | **75.0점** | **4,150,000원** | +365만원 | UNKNOWN (`LOCATION_VERIFY`) | 시세 대비 24.4% 저렴한 알짜 |
| 2 | `41366410` | 현대 아반떼 CN7 (2024년식, 53,382km) | 1,499만원 | 1855만원 | **+19.2%** | **75.0점** | **2,260,000원** | +176만원 | 대구 (`REMOTE_UNSUITABLE`) | 원거리 탁송료 반영 후에도 고수익 |
| 3 | `42706751` | 현대 아반떼 CN7 (2024년식, 35,192km) | 1,874만원 | 2,235만원 | **+16.2%** | **75.0점** | **2,310,000원** | +181만원 | UNKNOWN (`LOCATION_VERIFY`) | 3.5만km 짧은 주행거리 우위 |
| 4 | `42814110` | 현대 아반떼 CN7 (2024년식, 10,057km) | 2,120만원 | 2,390만원 | **+11.3%** | **73.7점** | **1,400,000원** | +90만원 | UNKNOWN (`LOCATION_VERIFY`) | 1만km 신차급 상태 우위 |
| 5 | `42811604` | 현대 아반떼 CN7 (2024년식, 84,331km) | 1,590만원 | 1,855만원 | **+14.3%** | **73.0점** | **1,350,000원** | +85만원 | 대전 (`REMOTE_UNSUITABLE`) | 가성비 주행거리 매물 |
| 6 | `42671808` | 현대 아반떼 CN7 (2024년식, 81,603km) | 1,590만원 | 1,855만원 | **+14.3%** | **73.0점** | **1,350,000원** | +85만원 | 대전 (`REMOTE_UNSUITABLE`) | 가성비 주행거리 매물 |
| 7 | `42911910` | 현대 아반떼 CN7 (2024년식, 46,530km) | 2,149만원 | 2,390만원 | **+10.1%** | **69.8점** | **1,110,000원** | +61만원 | 대전 (`REMOTE_UNSUITABLE`) | 중복광고(`42906948`) 병합 대표 |
| 8 | `42863742` | 현대 아반떼 CN7 (2024년식, 31,066km) | 2,190만원 | 2,390만원 | **+8.4%** | **57.8점** | **700,000원** | +20만원 | 대전 (`REMOTE_UNSUITABLE`) | 중복광고(`42866420`) 병합 대표 |

---

## 5. 전체 회귀 테스트 및 운영 데이터 불변 검증 (100% PASS)

### 5.1 전체 pytest 실행 결과 (207/207 ALL PASS)
```text
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.7.0
rootdir: /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI
configfile: pyproject.toml
testpaths: tests
collected 207 items

tests/test_directive_002_all.py ......................                   [ 10%]
...
tests/test_directive_013_scheduler.py .................................. [ 86%]
............                                                             [ 92%]
tests/test_directive_015_opportunity_intelligence.py .....               [ 95%]
tests/test_partner_intake.py ..........                                  [100%]

============================= 207 passed in 10.75s =============================
```
- `tests/test_directive_015_opportunity_intelligence.py` 5개 전용 테스트 100% 통과:
  1. `test_missing_year_blocked_from_priority_review`: 연식 미확인 차량의 우선 추천 원천 차단
  2. `test_duplicate_fingerprint_does_not_distort_cohort_median`: 중복 광고의 코호트 시세 왜곡 차단
  3. `test_profit_scenario_separates_net_profit_and_target_margin`: 순수익과 목표마진의 수학적 분리
  4. `test_as_of_time_prevents_future_data_leakage`: 과거 시점 데이터 누수 완전 차단
  5. `test_partner_suitability_separated_from_market_grade`: 시장 기회와 파트너 적합성 필드 분리

### 5.2 운영 DB 및 관측 원본 불변 영구 보존 (`verify_directive_012b.py` ALL PASS)
- `listings`: 348대 (100% 불변 보존)
- `listing_snapshots`: 382건 (100% 불변 보존)
- `price_events`: 353건 (100% 불변 보존)
- `batch_audit_logs`: 3회 (100% 불변 보존)
- 원본 JSON 관측 파일 3건 SHA-256 해시 일치 (100% 불변 보존)

---

## 6. 결론 및 PR #13 재검토 요청
- 총괄 감독(ChatGPT)님의 DIRECTIVE 015-A 지침에 따라 5대 결함을 완전히 보강하였으며, 추천 후보를 8대의 검증된 실전 후보로 정제 완료하였습니다.
- 수정 사항을 단일 원자적 커밋으로 커밋 및 푸시하여 PR #13을 갱신하였습니다.
- **GitHub PR #13의 재검토 및 승인을 요청드립니다!**
