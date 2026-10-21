# CHA-FICIAL AI PROJECT
## DIRECTIVE 009-A 완료 보고서: 시계열 가격 변동 추적 엔진 및 무결성 감사

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**저장소:** `https://github.com/WisdomMax/chafficial`  
**대상 브랜치:** `feat/directive-009-price-event-tracker` (PR #9 대상)  
**베이스 브랜치:** `feat/directive-008-market-data-expansion` (PR #8)  
**기준 데이터셋:** `templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv` (SHA-256: `657e1c2efb48d5b640ca4e4fa4dd01ffbcc24873cb1709e225d850468cba14a9`)  
**검증 일시:** 2026-10-21  

---

## 0. 총괄 감독 지적 사항 100% 반영 요약

1. **실제 시장 관측(`REAL_OBSERVED`) vs 시계열 시뮬레이션(`SIMULATED`) 통계 분리:**  
   - 현재 수집된 엔카 아반떼 CN7 417건 데이터셋은 **단일 시점 기저 스냅샷**이므로, 실제 시장에서의 시간 경과 가격 인하는 과학적으로 **0건**임을 명확히 분리 보고합니다.
   - 시계열 변동 로직(인하 3건, 인상 1건, 동일 가격 1건, 주행거리 변동 1건)은 `SIMULATED` 데이터로 격리 태깅하여 파이프라인 무결성을 검증했습니다.
2. **SQLite DB 영속성 및 중복 배치 멱등성(Idempotency) 보장:**  
   - `unlink()`로 DB를 삭제하는 기존 방식을 제거하고 영속 DB(`data/chaficial_market_timeseries.db`)를 보존합니다.
   - 동일 관측 배치 재실행 시 중복 이벤트 발생 **0건**을 단위 테스트 및 파이프라인에서 입증했습니다.
3. **금융상품 및 결측 가격의 명시적 `NULL` 보존:**  
   - 금융상품(렌트/리스) 및 가격 미기재 차량은 스냅샷 및 집계에서 절대 0원이 아닌 `NULL`로 유지되며, 월납입액 변동이 가격 인하로 오인되지 않도록 차단했습니다.
4. **연속 검색 미노출 누락 카운터 및 `DELISTED_SUSPECT` 상태 전이:**  
   - 1~2회 일시적 미노출 시에는 `ACTIVE`를 유지하고, 연속 3회 미노출 시 `DELISTED_SUSPECT`로 안전 전이하는 메커니즘을 구현 및 감사표로 출력했습니다.

---

## 1. 실제 관측 vs 시뮬레이션 통계 비교표

| 구분 | 관측 출처 (`data_origin`) | 총 레코드 수 | 신규 등록 (`NEW_LISTING`) | 가격 인하 (`PRICE_DROP`) | 가격 인상 (`PRICE_INCREASE`) | 판매종료 의심 (`DELISTED_SUSPECT`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **실제 시장 관측** | `REAL_OBSERVED` | **417건** | **417건** | **0건 (정상)** | **0건 (정상)** | 0건 |
| **시계열 시뮬레이션** | `SIMULATED` | **6건** | 0건 | **3건** | **1건** | **1건** |
| **합계** | - | 423건 | 417건 | 3건 | 1건 | 1건 |

> **실제 시장 관측에 대한 학술적·운영적 정직성:**  
> 단일 시점에 관측된 417건 실매물에서는 과거 시계열 스냅샷이 없으므로 가격 변동 이벤트가 0건인 것이 완벽하게 정상입니다.  
> 이를 가상으로 포장하지 않고 `0건`으로 명시하며, 향후 일일 정기 배치가 누적됨에 따라 실제 시장 가격 인하 이벤트가 자동으로 기록됩니다.

---

## 2. 시뮬레이션 가격 인하 탐지 상세 내역

| 매물 ID | 이전 가격 | 인하 후 가격 | 가격 변동액 (KRW) | 변동률 (%) | 최초 관측 후 경과일 | 출처 구분 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `ENCAR:42649405` | 13,500,000원 | 12,800,000원 | **-700,000원** | **-5.19%** | 4일 | `SIMULATED` |
| `ENCAR:42238872` | 18,500,000원 | 17,900,000원 | **-600,000원** | **-3.24%** | 7일 | `SIMULATED` |
| `ENCAR:42925136` | 14,000,000원 | 13,500,000원 | **-500,000원** | **-3.57%** | 4일 | `SIMULATED` |

---

## 3. 핵심 아키텍처 및 멱등성 검증

1. **시간 역전 및 지연 입력(Out-of-order) 방지:**  
   - 수집 지연으로 과거 관측치가 뒤늦게 유입될 경우, 현재 시점의 가격 변동 이벤트(`PRICE_DROP` 등)를 왜곡하지 않고 과거 스냅샷으로만 안전 적재.
2. **복귀 매물 재등록 감지 (`RE_LISTED_SUSPECT`):**  
   - `DELISTED_SUSPECT` 상태였던 매물이 다시 검색에 노출되면 `consecutive_missing_count`가 0으로 초기화되고 `RE_LISTED_SUSPECT` 이벤트가 자동 생성됨.
3. **누적 가격 변동률 계산 (`cumulative_delta_pct`):**  
   - 최초 관측 가격(`initial_price_krw`) 대비 전체 감가율을 일관되게 추적하여 단기 변동과 장기 할인폭을 동시에 제공.

---

## 4. 단위 및 통합 테스트 전수 통과 (91개 ALL PASS)

- `tests/test_directive_009_price_tracker.py` (6개 통과)
- `tests/test_directive_009a_advanced_tracking.py` (9개 신규 고급 시나리오 전수 통과)
- **전체 테스트 스위트:** 91개 테스트 100% 통과 (`pytest tests/`)

---

## 5. 생성된 산출물 명세

1. **영속 시계열 데이터베이스:**  
   [`data/chaficial_market_timeseries.db`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/chaficial_market_timeseries.db)
2. **가격 변동 이벤트 전수 CSV (실제/시뮬레이션 분리 태깅):**  
   [`outputs/directive_009_price_events.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_009_price_events.csv)
3. **판매종료 의심 감사표 CSV:**  
   [`outputs/directive_009_delisted_suspect_audit.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_009_delisted_suspect_audit.csv)
4. **동일 실차 추정 링크 CSV (PROBABLE_SAME):**  
   [`outputs/directive_009_vehicle_identity_links.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_009_vehicle_identity_links.csv)
5. **고급 무결성 단위 테스트:**  
   [`tests/test_directive_009a_advanced_tracking.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/tests/test_directive_009a_advanced_tracking.py)
6. **재현 실행 CLI 스크립트:**  
   [`scripts/run_directive_009_price_tracking.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/scripts/run_directive_009_price_tracking.py)

---

## 6. PR #9 안내 및 총괄 감독 승인 요청

본 작업은 `feat/directive-009-price-event-tracker` 브랜치에 전수 반영되었으며, PR #9 (`https://github.com/WisdomMax/chafficial/pull/9`)에 푸시되었습니다.  
총괄 감독님의 엄격한 코드 및 데이터 감사와 승인을 요청드립니다.
