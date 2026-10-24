# DIRECTIVE 015 FINAL: MARKET OPPORTUNITY INTELLIGENCE V1 (실전 기회 매물 발굴 엔진 완료 보고서)

## 1. 개요 및 GitHub 동기화 현황
- **프로젝트**: 차피셜(CHA-FICIAL) 실시간 중고차 시장 관측 및 시계열 기반 실전 기회 매물 발굴 엔진 V1
- **개발 브랜치**: `feat/directive-015-opportunity-intelligence-v1`
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker` (PR #12 공식 병합 완료 커밋 `e23d20292bf95840225866dd169fdaeea4d24841` 기준)
- **개발 담당**: Gemini / Antigravity
- **기술 감독**: ChatGPT
- **비교(Compare) URL**: https://github.com/WisdomMax/chafficial/compare/feat/directive-009-price-event-tracker...feat/directive-015-opportunity-intelligence-v1?expand=1

---

## 2. 기존 자산 재사용 및 중복 구현 방지 내역 (Phase 1 감사 준수)
1. **Opportunity Scorer (`src/chaficial/scorer/opportunity.py`)**:
   - 정밀 코호트 키 생성 규칙(`제조사_모델_세대_연식_트림_연료`) 및 Leave-One-Out 비교 원칙 100% 재사용.
2. **Valuation Validator (`src/chaficial/analytics/valuation_validator.py`)**:
   - 코호트 중앙값(Median) 및 분위수(P25, P75) 오차 통계 검증 로직 재사용.
3. **Price Event Tracker & Snapshots (`src/chaficial/models/`)**:
   - `listings`, `listing_snapshots`, `price_events` 테이블 데이터 활용.
   - 단, 동일 차량의 과거 여러 스냅샷이 독립 비교군(peers)으로 중복 집계되지 않도록 **최신 스냅샷 1건만 독립 표본으로 사용하는 엄격한 표본 정제 로직** 구현.
4. **운영 DB 및 원본 파일 100% 읽기 전용(Read-Only) 보존**:
   - SQLite URI `mode=ro` 적용으로 DB 변경 원천 차단.

---

## 3. 핵심 엔진 구현 및 점수 체계 (`opportunity_engine.py`)

### 3.1 4대 평가 축 및 기회 점수 계산식 (최대 100점)
$$\text{Opportunity Score} = S_{\text{rel}} + S_{\text{drop}} + S_{\text{profit}} + S_{\text{conf}}$$

1. **상대 시세 점수 ($S_{\text{rel}}$, 최대 40점)**:
   - 동일 코호트 중앙값 대비 가격 차이(%)에 비례 (10% 이상 저렴 시 40점 만점, 시세 이상 매물은 0점).
2. **가격 변동 점수 ($S_{\text{drop}}$, 최대 25점)**:
   - 가격 인하 감지 시 기본 10점 + 최근 인하율 점수(최대 10점) + 다회 인하 점수(최대 5점).
3. **수익성 점수 ($S_{\text{profit}}$, 최대 20점)**:
   - 기준(Base) 시나리오 예상 순수익에 비례 (순익 100만원 시 20점 만점).
4. **데이터 신뢰도 점수 ($S_{\text{conf}}$, 최대 15점)**:
   - 독립 비교 표본 수 $\ge 5$: 15점 (`HIGH`), $3 \le n < 5$: 9점 (`MEDIUM`), $n < 3$: 0~3점 (`LOW`/`INSUFFICIENT`).

### 3.2 4단계 추천 분류 및 엄격한 과대평가 방지 필터
- **`PRIORITY_REVIEW` (우선 검토)**:
  - 독립 비교 표본 수 $\ge 3$
  - 상대 가격 차이 $\ge 5.0\%$ (시세 대비 5% 이상 저렴)
  - 기준 예상 순익 $> 0$
  - 종합 점수 $\ge 50$점 또는 뚜렷한 가격 인하 모멘텀
- **`WATCHLIST` (추가 관측)**:
  - 시세 대비 소폭 우위이거나 가격 인하가 포착되었으나, 우선 검토 마진에 미달하는 매물
- **`INSUFFICIENT_DATA` (데이터 부족)**:
  - 동일 코호트 비교 표본 3건 미만 (무리한 추천 방지)
- **`EXCLUDED` (부적합)**:
  - 렌트/리스 등 금융상품, 데이터 결측, 시세 대비 과도하게 비싼 매물($\le -10\%$)

### 3.3 수익 시나리오의 가정 및 한계 (투명한 공개)
- **보수적**: 코호트 P25 판매 가정 / 상품화 120만 / 탁송 40만 (+원거리 30만) / 최소마진 70만
- **기준**: 코호트 Median 판매 가정 / 상품화 80만 / 탁송 30만 (+원거리 20만) / 목표마진 50만
- **낙관적**: 코호트 P75 판매 가정 / 상품화 50만 / 탁송 20만 (+원거리 15만) / 최소마진 40만
- *한계 명시*: 본 수익 시나리오는 업계 표준 비용에 기반한 '가정 기반 시나리오(Hypothetical Scenario)'이며, 실제 딜러 실매입가 및 네고 결과에 따라 달라질 수 있습니다.

---

## 4. 실제 348대 관측 데이터 분석 결과

### 4.1 전체 분류 통계
- **총 매물 수**: 348대 (현대 아반떼 CN7 라인업)
- **`PRIORITY_REVIEW` (우선 검토)**: **20대 (5.7%)**
- **`WATCHLIST` (추가 관측)**: **24대 (6.9%)**
- **`INSUFFICIENT_DATA` (데이터 부족)**: **248대 (71.3%)**
- **`EXCLUDED` (부적합)**: **56대 (16.1%)**

### 4.2 가격 인하 5건에 대한 과대평가 방지 검증 결과
1. **`42872963`**: 2,490만 $\rightarrow$ 2,470만 (-20만원, -0.8%)
   - 코호트 시세(2,724만) 대비 **+9.34% 저렴**, 예상순익 74.5만원 확보 가능 $\rightarrow$ **`PRIORITY_REVIEW` 1위 선정 (78.9점)**.
2. **`42316208`**: 1,650만 $\rightarrow$ 1,450만 (-200만원, -12.12%)
   - 대폭 인하되었으나 동일 코호트 독립 표본 0건으로 시세 비교 불가 $\rightarrow$ 무리한 추천 없이 **`INSUFFICIENT_DATA` (데이터 부족) 정직하게 보류!**
3. **`42718815`**: 1,590만 $\rightarrow$ 1,540만 (-50만원) $\rightarrow$ **`INSUFFICIENT_DATA` 보류**.
4. **`42867093` & `42864399`**: 1,860만 $\rightarrow$ 1,840만 (-20만원) $\rightarrow$ **`INSUFFICIENT_DATA` 보류**.

### 4.3 지역 투명성 확보 (지침 1.3 준수)
- 현재 관측 매물 348대 중 서울/장안평 명시 매물은 0건, UNKNOWN 264건, 지방 광역시 84건.
- 지역 정보가 없는 매물을 서울 장안평 매물로 임의 왜곡하지 않고, `REGION_UNVERIFIED` 리스크 플래그를 정확히 명시하였습니다.

---

## 5. 전체 테스트 및 운영 데이터 무결성 검증 (100% PASS)

### 5.1 전체 pytest 실행 결과 (208/208 ALL PASS)
```text
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.7.0
rootdir: /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI
configfile: pyproject.toml
testpaths: tests
collected 208 items

tests/test_directive_002_all.py ......................                   [ 10%]
...
tests/test_directive_013_scheduler.py .................................. [ 86%]
............                                                             [ 92%]
tests/test_directive_015_opportunity_intelligence.py ......              [ 95%]
tests/test_partner_intake.py ..........                                  [100%]

============================= 208 passed in 5.39s ==============================
```
- `tests/test_directive_015_opportunity_intelligence.py` 신규 6개 회귀 테스트 100% 통과:
  1. 동일 매물 중복 추천 방지
  2. 동일 차량 여러 스냅샷의 독립 비교군 중복 집계 차단
  3. 가격 인하 폭이 커도 시세보다 비싼 매물 과대평가 차단 (EXCLUDED)
  4. 가격 인하가 없더라도 상대적으로 저렴한 알짜 매물 탐지
  5. 지역 미확인 매물의 장안평 왜곡 방지
  6. 금융상품(렌트/리스) 원천 배제

### 5.2 운영 DB 및 관측 원본 불변 영구 보존 (`verify_directive_012b.py` ALL PASS)
- `listings`: 348대 (100% 불변 보존)
- `listing_snapshots`: 382건 (Row-by-Row 100% 불변 보존)
- `price_events`: 353건 (100% 불변 보존)
- `batch_audit_logs`: 3회 (100% 불변 보존)
- 원본 JSON 관측 파일 3건 해시 일치 (100% 불변 보존)

---

## 6. 결론 및 3단계(25년 경력 딜러의 실제 피드백 수집) 진입 제언
- **산출물**:
  - 엔진 코드: `src/chaficial/intelligence/opportunity_engine.py`
  - 설정 모듈: `src/chaficial/intelligence/config.py`
  - CLI 도구: `scripts/run_directive_015_opportunity_intelligence.py`
  - 보고서 및 CSV:
    - `reports/opportunities/opportunity_report_20261024.md`
    - `reports/opportunities/opportunity_candidates_20261024.csv`
  - 테스트: `tests/test_directive_015_opportunity_intelligence.py`
- **다음 단계 제언**:
  - 총괄 감독(ChatGPT)님의 전략적 방향에 따라, 도출된 상위 20대 우선 검토 매물(`opportunity_candidates_20261024.csv`)을 25년 경력 딜러 파트너에게 전달하여 **"실제 매입 의사 / 매입 불가 사유 / 요구 상품화 내역"**을 수집하는 **3단계 실전 딜러 피드백 수집 및 데이터셋 축적 단계**로 진입할 것을 적극 제안드립니다!
