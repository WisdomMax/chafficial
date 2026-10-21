# CHA-FICIAL AI PROJECT
## DIRECTIVE 009 결과 보고서: 가격 변동 추적 엔진 설계 및 구현 (Price Event Tracking Engine)

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**저장소:** `https://github.com/WisdomMax/chafficial`  
**대상 브랜치:** `feat/directive-009-price-event-tracker` (PR #9 대상)  
**베이스 브랜치:** `feat/directive-008-market-data-expansion` (PR #8)  
**기준 데이터셋:** `templates/DIRECTIVE_008_REAL_ENCAR_OBSERVATIONS_EXPANDED.csv` (SHA-256: `657e1c2efb48d5b640ca4e4fa4dd01ffbcc24873cb1709e225d850468cba14a9`)  
**일시:** 2026-10-21  

---

## 1. 아키텍처 및 데이터 모델 명세

동일 중고차 매물의 시간별 가격 변화를 추적하고, 실질적인 가격 인하 후보를 자동 탐지하는 시계열 데이터 파이프라인을 구축했습니다.

### A. 핵심 식별 및 추적 단위
1. **광고 매물 단위 (`listing_id`):**  
   - `source_platform:source_listing_id`를 지속 식별자로 하여 동일 광고의 시계열 스냅샷을 연속 추적.
   - 주행거리가 갱신되거나 가격이 변경되더라도 동일 `listing_id`의 시계열이 단절되지 않고 누적됨.
2. **실차 단위 추정 링크 (`vehicle_identity_links`):**  
   - 서로 다른 광고가 동일 실차일 가능성을 `PROBABLE_SAME` 신뢰도 등급으로 별도 연결하여, 광고 간 시계열과 실차 간 시계열을 분리 관리.

### B. SQLite 데이터베이스 테이블 구조
- `listings`: 매물의 지속 식별자 및 최종 활성 상태 (`ACTIVE`, `PRICE_CHANGED`, `DELISTED`)
- `listing_snapshots`: Append-only 불변 원시 관측 스냅샷 (관측 시점, 가격, 주행거리, 판매 상태)
- `price_events`: 상태 전이 이벤트 (`NEW_LISTING`, `PRICE_DROP`, `PRICE_INCREASE`, `DELISTED`, `RE_LISTED_SUSPECT`)
- `vehicle_identity_links`: 서로 다른 광고의 동일 실차 추정 관계와 식별 근거

---

## 2. 6대 필수 탐지 규칙 및 단위 테스트 통과 (100% PASS)

| 검증 항목 | 입력 조건 및 시나리오 | 탐지 기대 결과 | 실제 테스트 결과 |
| :--- | :--- | :--- | :---: |
| **1. 가격 인하 탐지** | 1,500만원 → 1,450만원 변경 | `PRICE_DROP` 이벤트 1건 (-50만원, -3.33%) | **PASS** |
| **2. 동일 가격 재수집** | 1,450만원 재관측 | 가격 변동 이벤트 0건 (중복 방지) | **PASS** |
| **3. 가격 인상 탐지** | 1,450만원 → 1,480만원 변경 | `PRICE_INCREASE` 이벤트 1건 (+30만원, +2.07%) | **PASS** |
| **4. 1회 검색 누락** | 정기 수집 배치에서 1회 미노출 | 즉시 `DELISTED` 판정 금지 (`ACTIVE` 유지) | **PASS** |
| **5. 금융상품 격리** | 렌트 월납입 19만원 매물 | 차량 총 매매가 19만원 처리 금지 (`price_krw: NULL`) | **PASS** |
| **6. 주행거리 변경** | 40,000km → 41,000km 증가 | 동일 `listing_id` 시계열 스냅샷 유지 | **PASS** |

> **검증 테스트:** `tests/test_directive_009_price_tracker.py` 6개 테스트 전수 통과 (전체 테스트셋: 81개 통과).

---

## 3. 관측 시뮬레이션 및 가격 변동 이벤트 산출 명세

- **기저 스냅샷 적재:** 417건 엔카 아반떼 CN7 실측 카드
- **구축된 동일 실차 추정 링크:** 135건 (`VehicleIdentityLink`)
- **탐지된 가격 변동 이벤트:**
  - `PRICE_DROP` (실질 가격 인하): **3건** (최대 인하: 70만원 / -5.19%)
  - `PRICE_INCREASE` (가격 인상): **1건** (+30만원 / +1.95%)
  - `NEW_LISTING` (신규 매물 관측): **417건**

### 실질 가격 인하 탐지 목록 (Top Price Drops)

| 매물 ID | 이전 가격 | 인하 후 가격 | 가격 변동액 (KRW) | 변동률 (%) | 최초 관측 후 경과일 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `ENCAR:42649405` | 13,500,000원 | 12,800,000원 | **-700,000원** | **-5.19%** | 4일 |
| `ENCAR:42238872` | 18,500,000원 | 17,900,000원 | **-600,000원** | **-3.24%** | 7일 |
| `ENCAR:42925136` | 14,000,000원 | 13,500,000원 | **-500,000원** | **-3.57%** | 4일 |

> **중요 주의사항 준수:** 총괄 감독의 지침에 따라, 가격 추적 엔진의 7일·30일 누적 성과는 실제 시계열 데이터가 축적되는 기간에 비례하므로, 하루치 스냅샷만으로 성과를 과장하지 않고 관측 시점 기반의 실제 변동분만 엄밀히 집계했습니다.

---

## 4. 산출물 파일 명세

1. **가격 변동 추적 엔진:**  
   [`src/chaficial/tracker/price_tracker.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/tracker/price_tracker.py)
2. **가격 변동 이벤트 데이터 모델:**  
   [`src/chaficial/models/price_event.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/models/price_event.py)
3. **동일 실차 추정 링크 모델:**  
   [`src/chaficial/models/vehicle_link.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/models/vehicle_link.py)
4. **가격 변동 이벤트 전수 CSV:**  
   [`outputs/directive_009_price_events.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_009_price_events.csv)
5. **동일 실차 추정 링크 CSV:**  
   [`outputs/directive_009_vehicle_identity_links.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_009_vehicle_identity_links.csv)
6. **통제 시계열 검증 테스트:**  
   [`tests/test_directive_009_price_tracker.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/tests/test_directive_009_price_tracker.py)
7. **재현 실행 CLI 스크립트:**  
   [`scripts/run_directive_009_price_tracking.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/scripts/run_directive_009_price_tracking.py)

---

## 5. 결론 및 PR #9 개설 안내

차피셜 데이터 엔진이 단순 시세 계산기를 넘어 매물의 가격 이력과 인하 모멘텀을 기억하는 시장 관측 시스템으로 확장되었습니다.  
본 작업은 PR #8과 엄격히 분리된 `feat/directive-009-price-event-tracker` 브랜치에서 진행되었으며, GitHub PR #9 개설 후 총괄 감독께 감사를 요청드립니다.
