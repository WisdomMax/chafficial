# [공식 보고] CHA-FICIAL DIRECTIVE 015: 실전 기회 매물 발굴 엔진 V1 및 PR #13 생성 완료 보고

## 0. GitHub PR #13 공식 생성 및 핵심 3자 SHA 100% 일치 증명
- **공식 PR URL**: https://github.com/WisdomMax/chafficial/pull/13
- **PR 번호**: **#13** (`state: open`, `mergeable: true`)
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker` (PR #12 병합 커밋 `e23d2029...` 최신)
- **작업(Head) 브랜치**: `feat/directive-015-opportunity-intelligence-v1`
- **로컬 브랜치 HEAD SHA**: `2d132dc2114941ccea17577ede19d53818e117d7`
- **원격 브랜치 HEAD SHA**: `2d132dc2114941ccea17577ede19d53818e117d7`
- **GitHub PR #13 HEAD SHA**: `2d132dc2114941ccea17577ede19d53818e117d7`
- **PR 비교(Compare) URL**: https://github.com/WisdomMax/chafficial/compare/feat/directive-009-price-event-tracker...feat/directive-015-opportunity-intelligence-v1?expand=1

---

## 1. 기존 코드 자산 재사용 내역 (Phase 1 감사 준수)
1. **`OpportunityScorer` (`src/chaficial/scorer/opportunity.py`)**:
   - `make_cohort_key` 정밀 군집화(`제조사_모델_세대_연식_트림_연료`) 및 Leave-One-Out 비교 로직을 100% 재사용하였습니다.
2. **`ValuationValidator` (`src/chaficial/analytics/valuation_validator.py`)**:
   - 중앙값(Median) 및 분위수(P25, P75) 계산 알고리즘을 재사용하였습니다.
3. **`Listing`, `ListingSnapshot`, `PriceEvent` 데이터 모델**:
   - 348대 매물 및 353건 가격 변동 이력을 활용하되, **동일 차량의 과거 여러 스냅샷이 독립 비교군(peers)으로 중복 집계되지 않도록 차량당 최신 스냅샷 1건만 표본으로 집계**하도록 엄격히 정제하였습니다.
4. **100% 읽기 전용(Read-Only) 운영 모드**:
   - SQLite URI `mode=ro`를 적용하여 운영 DB 및 원본 데이터를 1 bit도 건드리지 않고 읽기 전용 분석을 완수하였습니다.

---

## 2. 신규 파일 및 변경 파일 목록
1. `src/chaficial/intelligence/config.py`: 기회 탐지 가중치 및 가정 기반 3단계 수익 비용 모델 설정
2. `src/chaficial/intelligence/opportunity_engine.py`: 다차원 기회 탐지, Leave-One-Out 시세 비교, 점수 산출, 4단계 분류 엔진
3. `src/chaficial/intelligence/__init__.py`: 패키지 익스포트
4. `scripts/run_directive_015_opportunity_intelligence.py`: 실전 분석 실행 및 마크다운/CSV 보고서 자동 생성 CLI
5. `reports/opportunities/opportunity_report_20261024.md`: 실전 기회 매물 분석 종합 보고서
6. `reports/opportunities/opportunity_candidates_20261024.csv`: 지침 3 필수 필드를 전수 포함한 후보 매물 CSV
7. `tests/test_directive_015_opportunity_intelligence.py`: 지침 4 필수 10대 검증 항목을 다루는 6개 전용 회귀 테스트
8. `reports/DIRECTIVE_015_SYSTEM_DESIGN.md`: Phase 1 감사 및 시스템 설계서
9. `reports/DIRECTIVE_015_FINAL_REPORT.md`: 최종 완료 상세 보고서

---

## 3. 기회 점수 계산식 및 가중치 (0 ~ 100점)
- $\text{Opportunity Score} = S_{\text{rel}} + S_{\text{drop}} + S_{\text{profit}} + S_{\text{conf}}$
  - **상대 시세 점수 ($S_{\text{rel}}$, 최대 40점)**: 시세 중앙값 대비 가격 우위율(%)에 비례 (10% 저렴 시 40점 만점, 시세 이상 매물은 0점).
  - **가격 변동 점수 ($S_{\text{drop}}$, 최대 25점)**: 인하 모멘텀 10점 + 최근 인하율(최대 10점) + 다회 인하 빈도(최대 5점).
  - **수익성 점수 ($S_{\text{profit}}$, 최대 20점)**: 기준 시나리오 예상 순수익에 비례 (100만원 이상 시 20점 만점).
  - **데이터 신뢰도 점수 ($S_{\text{conf}}$, 최대 15점)**: 비교 표본 수 $\ge 5$건은 15점(`HIGH`), $3 \le n < 5$건은 9점(`MEDIUM`), $n < 3$건은 0~3점(`LOW`/`INSUFFICIENT`).

---

## 4. 수익 시나리오의 가정 및 한계 (투명한 명시)
- **보수적 (Conservative)**: 코호트 P25 판매 가정 / 상품화 120만 / 탁송 40만 (+원거리 30만) / 목표마진 70만
- **기준 (Base)**: 코호트 Median 판매 가정 / 상품화 80만 / 탁송 30만 (+원거리 20만) / 목표마진 50만
- **낙관적 (Optimistic)**: 코호트 P75 판매 가정 / 상품화 50만 / 탁송 20만 (+원거리 15만) / 목표마진 40만
- *한계 명시*: 실제 딜러 실매입가 및 거래 원가가 없는 현 단계에서는 업계 표준에 기반한 **가정 기반 시나리오(Hypothetical Scenario)**임을 시스템과 보고서에 명확히 표기하였습니다.

---

## 5. 실제 348대 관측 데이터 분석 결과 및 과대평가 방지 입증

### 5.1 4단계 추천 분류 결과
- **총 관측 매물**: 348대 (현대 아반떼 CN7)
- **`PRIORITY_REVIEW` (우선 검토)**: **20대 (5.7%)**
- **`WATCHLIST` (추가 관측)**: **24대 (6.9%)**
- **`INSUFFICIENT_DATA` (데이터 부족)**: **248대 (71.3%)**
- **`EXCLUDED` (부적합)**: **56대 (16.1%)**

### 5.2 가격 인하 5건 집중 분석 및 과대평가 방지
- **1위 선정**: `42872963` (2,490만 $\rightarrow$ 2,470만, -20만원 인하)
  - 동일 코호트 시세(2,724.5만) 대비 **+9.34% 저렴**, 기준 예상순익 **74.5만원** $\rightarrow$ **`PRIORITY_REVIEW` 1위 (78.9점)**
- **정직한 보류 (INSUFFICIENT_DATA)**:
  - `42316208` (1,650만 $\rightarrow$ 1,450만, -200만원, -12.12% 대폭 인하): 가격 인하 폭이 매우 크지만 동일 코호트 독립 표본이 0건으로 시세 비교 불가 $\rightarrow$ 무리한 추천을 차단하고 **`INSUFFICIENT_DATA`로 정직하게 보류!**
  - `42718815` (-50만원 인하), `42867093` (-20만원), `42864399` (-20만원): 동일 코호트 표본 부족(0~1건)으로 **`INSUFFICIENT_DATA` 보류**.

### 5.3 지역 정보 투명성 (지침 1.3 준수)
- 현재 확보된 348대 중 서울/장안평 명시 매물은 0건, `UNKNOWN` 264건, 지방 광역시 84건입니다.
- 지역 미확인 매물을 서울 장안평 매물로 임의 분류하지 않고, **`REGION_UNVERIFIED` 리스크 플래그**를 정확히 명시하였습니다.

---

## 6. 전체 테스트 및 운영 데이터 무결성 검증 (100% PASS)
- **전체 pytest**: **208개 테스트 전수 통과 (100% PASS)** (`208 passed in 5.39s`)
  - 신규 6개 테스트(`tests/test_directive_015_opportunity_intelligence.py`): 중복 추천 방지, 과거 스냅샷 독립 표본 오집계 차단, 비싼 매물 과대평가 차단, 알짜 매물 발굴, 지역 왜곡 방지, 금융상품 배제 전수 통과
- **운영 DB 및 관측 원본 불변 영구 보존**:
  - `scripts/verify_directive_012b.py` 100% ALL PASS
  - `listings`: 348대, `listing_snapshots`: 382건, `price_events`: 353건, `batch_audit_logs`: 3회 100% 불변 보존
  - 원본 JSON 관측 파일 3건 해시 100% 일치 확인

---

## 7. 결론 및 3단계(25년 경력 딜러의 실제 피드백 수집) 진입 제언
- **GitHub PR #13 공식 URL**: https://github.com/WisdomMax/chafficial/pull/13
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker`
- 총괄 감독(ChatGPT)님의 DIRECTIVE 015 지침을 100% 준수하여 기회 탐지 엔진 V1 개발과 PR #13 생성을 완료하였습니다.
- 운영 제한 원칙에 따라 LIVE 수집, 운영 DB 변경, PR 자체 병합은 일체 실행하지 않고 대기 중입니다.
- 총괄 감독님께서 강조하신 로드맵 3단계, 즉 **"도출된 20대 우선 검토 매물(`opportunity_candidates_20261024.csv`)을 25년 경력 딜러 파트너에게 전달하여 실제 매입 의사/이유/상품화 요구사항 피드백 데이터를 축적하는 단계"**로 전진하기 위한 검토 및 후속 지시를 요청드립니다!
