# CHA-FICIAL DIRECTIVE 015: MARKET OPPORTUNITY INTELLIGENCE V1 시스템 설계 및 자산 감사 보고서

## 1. 개발 배경 및 목적
- **프로젝트**: 차피셜(CHA-FICIAL) 실시간 중고차 시계열 관측 및 가격 변동 기반 실전 매물 발굴 엔진 V1
- **목표**: 단순 스케줄링 관리에서 나아가, 실제 25년 경력 딜러 파트너(서울 장안평 등)가 현업에서 즉시 검토할 수 있는 고부가가치 기회 매물을 자동 선별하고 설명 가능한 근거를 제공하는 지능형 분석 엔진 구현.
- **원칙**:
  1. 기존 코드 자산의 철저한 재사용 (중복 개발 금지)
  2. 운영 DB(`data/chaficial_market_timeseries.db`) 및 원본 관측 JSON 3건 불변 영구 보존 (100% Read-Only)
  3. 실전 영업 대상과 전체 시장 분석 데이터의 엄격한 분리 (지역 미확인/타지역 매물의 임의 장안평 둔갑 방지)
  4. 점수와 신뢰도의 엄격한 분리 (데이터 부족 매물은 고득점 추천이 아닌 INSUFFICIENT_DATA로 분류)

---

## 2. 기존 소스 자산 재사용 및 감사 분석 (Phase 1)

### 2.1 기존 모듈 조사 및 재사용 계획
| 기존 모듈 | 위치 | DIRECTIVE 015 재사용 방식 |
| :--- | :--- | :--- |
| **Opportunity Scorer** | `src/chaficial/scorer/opportunity.py` | 정밀 코호트 키 생성(`make_cohort_key`), Leave-One-Out 비교 로직, 주행거리/사고 상태 보정 파라미터 재사용 |
| **Valuation Validator** | `src/chaficial/analytics/valuation_validator.py` | 중앙값/분위수(P50, P75) 계산 및 시세 예측 불확실성 산출식 재사용 |
| **Database & Models** | `src/chaficial/models/` | `Listing`, `ListingSnapshot`, `PriceEvent`, `BatchAuditLog` ORM 매핑 읽기 전용 쿼리 |
| **Region Manager** | `src/chaficial/regions/manager.py` | 파트너별 영업 허용 지역(서울 장안평, 경기, 인천 등) 유효성 필터 재사용 |
| **Time Travel Engine** | `src/chaficial/time_travel/query_engine.py` | 과거 특정 시점 기준 평가 시 미래 데이터 누수(Data Leakage) 원천 차단 |

### 2.2 실제 운영 데이터베이스 가용성 실사
- **총 매물 수 (`listings`)**: 348대 (모두 현대 아반떼 CN7 라인업)
- **총 스냅샷 수 (`listing_snapshots`)**: 382건 (1~3차 배치 시계열)
- **총 가격 변동 이벤트 (`price_events`)**: 353건 (`NEW_LISTING`: 348건, `PRICE_DROP`: 5건)
- **지역 분포 현황 (`raw_location`)**:
  - `UNKNOWN`: 264건 (전체의 75.8%)
  - `대구`: 31건 (8.9%)
  - `대전`: 27건 (7.8%)
  - `부산`: 18건 (5.2%)
  - `광주`: 8건 (2.3%)
- **핵심 발견 및 정직한 데이터 원칙**:
  - 현재 수집된 관측 데이터에는 명시적인 서울/장안평 매물이 존재하지 않으며, 75% 이상이 지역 미확인(`UNKNOWN`) 상태입니다.
  - 지침 1.3에 따라, **지역 정보가 없는 매물을 서울 장안평 매물로 임의 분류하지 않고**, `REGION_UNVERIFIED` 또는 `REGION_MISMATCH` 플래그를 정직하게 명시하여 무리한 과대평가를 원천 차단합니다.

---

## 3. 기회 탐지 엔진 V1 세부 설계 (Phase 2)

### 3.1 상대 시세 분석 (Relative Valuation)
- **비교 코호트**: `제조사_모델_세대_연식_연료_트림` 기준 동일 군집화
- **Leave-One-Out 중앙값**: 대상 차량을 제외한 군집 내 중앙값 산출 (단일 매물 편향 방지)
- **상대 가격 차이(%)**:
  $$\text{Relative Gap (\%)} = \frac{\text{Cohort Median Price} - \text{Current Price}}{\text{Cohort Median Price}} \times 100$$
- **신뢰도 판정**:
  - 독립 비교 표본 수 $\ge 5$: `HIGH`
  - $3 \le \text{표본 수} < 5$: `MEDIUM`
  - $\text{표본 수} < 3$: `LOW` 또는 `INSUFFICIENT_DATA`

### 3.2 가격 변동 신호 분석 (Price Dynamics)
- **가격 인하 이력**:
  - `cumulative_price_drop_krw`: 누적 가격 인하액
  - `price_drop_count`: 가격 인하 횟수
  - `latest_drop_pct`: 직전 대비 인하율
  - `days_since_first_seen`: 시스템 최초 관측 이후 경과일수
- **동적 가치 포착**:
  - 가격 인하 폭이 크면서도 상대 시세 대비 실제 저렴한 매물 포착
  - 가격을 대폭 내렸더라도 여전히 시세보다 비싼 매물은 과대평가 방지 필터 적용

### 3.3 예상 수익 시나리오 모델 (Economics Scenarios)
- 실제 거래 원가 데이터가 없는 현 단계에서는 **'가정 기반 시나리오(Hypothetical Scenario)'**임을 명시
- 파라미터 설정 분리:
  - **매입 추정가**: 광고 가격 기준 (네고 가능성 보수적 가정)
  - **상품화 비용 (Reconditioning)**: 차량 상태별 기본 800,000원 (보수적: 1,200,000원, 낙관적: 500,000원)
  - **이전 및 부대비용 (Transfer & Logistics)**: 300,000원 (지방 탁송 시 +200,000원 추가)
  - **딜러 마진 및 판매 수수료 (Fee & Target Margin)**: 400,000원
- 3단계 시나리오 계산:
  - **보수적 (Conservative)**: 코호트 P25 가격으로 판매 가정, 부대비용 상향
  - **기준 (Base)**: 코호트 Median 가격으로 판매 가정, 표준 부대비용
  - **낙관적 (Optimistic)**: 코호트 P75 가격으로 판매 가정, 부대비용 최소화

### 3.4 4단계 추천 분류 (Recommendation Categories)
1. **`PRIORITY_REVIEW` (우선 검토)**:
   - 비교 표본 수 $\ge 3$
   - 상대 가격 차이 $\ge 5\%$ (시세 대비 5% 이상 저렴)
   - 예상 기준 순수익 $> 0$
   - 최근 가격 인하 모멘텀 또는 뚜렷한 저평가 상태
2. **`WATCHLIST` (추가 관측)**:
   - 시세 대비 저렴하나 관측 횟수가 1회이거나, 가격 인하 폭이 미미하여 모멘텀 검증이 필요한 매물
3. **`INSUFFICIENT_DATA` (데이터 부족)**:
   - 코호트 비교 표본이 3건 미만이거나 주요 속성 결측으로 시세 비교가 불가능한 매물
4. **`EXCLUDED` (부적합)**:
   - 렌트/리스 등 금융상품, 데이터 이상치(가격 결측/음수 등), 시세보다 과도하게 비싼 매물

---

## 4. 구현 및 산출 파일 구조
- 엔진 모듈: `src/chaficial/intelligence/opportunity_engine.py`
- 파라미터 설정: `src/chaficial/intelligence/config.py`
- CLI 실행 스크립트: `scripts/run_directive_015_opportunity_intelligence.py`
- 산출 보고서:
  - `reports/opportunities/opportunity_report_20261024.md`
  - `reports/opportunities/opportunity_candidates_20261024.csv`
- 테스트 코드: `tests/test_directive_015_opportunity_intelligence.py`
