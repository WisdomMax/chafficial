# 🚘 CHA-FICIAL AI PROJECT
## DIRECTIVE 006 완료 보고서
### 전국 중고차 매물 분석 MVP 및 Top 10 기회 매물 자동 선별 엔진 V0.1 개발 완료

**발신:** Google Antigravity (차피셜 AI 연구팀)  
**수신:** CHA-FICIAL AI 연구 총괄 감독 (ChatGPT)  
**저장소:** https://github.com/WisdomMax/chafficial  
**신규 작업 브랜치:** [`feat/directive-006-opportunity-scorer`](https://github.com/WisdomMax/chafficial/tree/feat/directive-006-opportunity-scorer)  
**종속 관계:** `main` <- PR #1 <- PR #2 <- PR #3 <- PR #4 <- PR #5 <- **[PR #6 (DIRECTIVE 006)]**  
**테스트 상태:** **52개 전수 통과** (`52 passed in 0.64s`) / Ruff 전수 통과 (`All checks passed!`)  
**목표 상태:** **`DIRECTIVE 006 MVP IMPLEMENTED / READY FOR REAL LISTING EVALUATION`**  
**작성일자:** 2026-10-21  

---

## 0. 핵심 성과 요약

| 점검 지표 | 수치 / 판정 | 비고 |
| :--- | :---: | :--- |
| **개발 상태** | **동결 해제 / MVP 구현 완료** | 전국 매물 기회 평가 엔진(Scorer V0.1) 완성 |
| **단위/통합 테스트** | **52개 전수 통과** | 기존 47개 전수 유지 + 신규 5개 추가 |
| **코드 린트 (Ruff)** | **All checks passed!** | 무결성 유지 |
| **지원 플랫폼 식별기** | **엔카, KB차차차, KCar 등** | URL 기반 플랫폼 및 고유 매물 ID 자동 추출 |
| **기회 점수 산정 엔진** | **상태 조정 공정 시세 기반** | 표본 3대 미만 시 `INSUFFICIENT_DATA` 안전 통제 |
| **자동 선별 CLI** | **정상 작동 및 CSV 출력** | `outputs/top_10_opportunities.csv` 생성 완료 |
| **최종 완료 상태** | **COMPLETED** | **`DIRECTIVE 006 MVP IMPLEMENTED / READY FOR REAL LISTING EVALUATION`** |

---

## 1. 구현된 핵심 코드 및 파일 경로

1. **플랫폼 인터페이스 및 URL 파서:**
   - [`src/chaficial/platforms/base.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platforms/base.py): 표준 매물 레코드 규격(`StandardListingRecord`), 엔카/KB차차차/KCar URL 파싱 및 고유 매물 ID 자동 추출기(`PlatformUrlParser`).
2. **기회 매물 평가 점수 엔진:**
   - [`src/chaficial/scorer/opportunity.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/scorer/opportunity.py): `OpportunityScorer V0.1`. 동일군 표본 3대 검증, 중앙 등록가 대비 주행거리 편차 가치 보정, 사고/외판 상태 감가, 가격 인하 모멘텀, 데이터 신뢰도 반영 0~100점 기회 점수 산정.
3. **무결성 인입 및 평가 파이프라인:**
   - [`src/chaficial/pipeline/ingest_and_score.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/pipeline/ingest_and_score.py): CSV 매물 로드, SQLite DB 적재 및 동일 매물 가격 인하 시 `ListingSnapshot` 불변(Append-only) 이력 보존, 코호트 일괄 평가, Top-N CSV 내보내기.
4. **실행 가능한 CLI 도구:**
   - [`src/chaficial/cli/opportunity_cli.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/cli/opportunity_cli.py): 명령줄 기반 매물 분석, DB 적재, Top 10 기회 매물 콘솔 브리핑 및 CSV 추출 CLI.
5. **규격 및 테스트:**
   - [`docs/DIRECTIVE_006_OPPORTUNITY_SCORER_SPEC.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/docs/DIRECTIVE_006_OPPORTUNITY_SCORER_SPEC.md): 점수 산정 공식, 표본 제약, 알고리즘 한계점 기술 명세서.
   - [`templates/DIRECTIVE_006_MARKET_OBSERVATIONS_SAMPLE.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/templates/DIRECTIVE_006_MARKET_OBSERVATIONS_SAMPLE.csv): 아반떼 CN7, 그랜저 GN7, 스포티지 NQ5, 제네시스 등 20건 시장 관측 데이터셋.
   - [`tests/test_directive_006_opportunity_scorer.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/tests/test_directive_006_opportunity_scorer.py): 5대 신규 검증 테스트 전수 통과.

---

## 2. 실제 실행 명령 및 실행 결과

### 1) CLI 실행 명령
```bash
python -m chaficial.cli.opportunity_cli \
  --input templates/DIRECTIVE_006_MARKET_OBSERVATIONS_SAMPLE.csv \
  --output outputs/top_10_opportunities.csv \
  --top 10
```

### 2) 상위 기회 매물 분석 결과 (상위 5건 예시)

| 순위 | 차량 요약 | 등록가격 | 비교 중앙가 (표본) | 상태조정 공정시세 | 실질 경쟁력 | 기회 점수 | 플랫폼 / 출처 ID |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1위** | 현대 아반떼 CN7 모던 (2021년식 / 21,500km) | 1,450만원 | 1,465만원 (6대) | **1,605만원** | **+9.7%** | **89.3점** | ENCAR / 38291021 |
| **2위** | 현대 아반떼 CN7 인스퍼레이션 (2021년식 / 19,000km) | 1,680만원 | 1,755만원 (4대) | **1,817만원** | **+7.5%** | **82.8점** | ENCAR / 38291030 |
| **3위** | 기아 스포티지 NQ5 시그니처 (2022년식 / 18,000km) | 2,420만원 | 2,550만원 (4대) | **2,598만원** | **+6.8%** | **79.7점** | ENCAR / 38291038 |
| **4위** | 현대 그랜저 GN7 캘리그래피 (2023년식 / 12,000km) | 3,600만원 | 3,785만원 (4대) | **3,837만원** | **+6.2%** | **78.9점** | ENCAR / 38291034 |
| **5위** | 현대 아반떼 CN7 모던 (2021년식 / 32,000km) | 1,600만원 | 1,465만원 (6대) | **1,563만원** | **-2.4%** | **65.3점** | ENCAR / 38291024 |

*결과 파일: [`outputs/top_10_opportunities.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/top_10_opportunities.csv)*

---

## 3. 점수 산정 공식 및 알고리즘의 한계

### 1) 산정 공식 요약
- **상태 조정 공정 시세:**  
  $$\text{Adjusted Fair Value} = \text{Median Price} + \left(\frac{\text{Median Mileage} - \text{Target Mileage}}{10,000} \times 400,000\text{원}\right) + \text{Accident Adj}$$
- **기회 점수 (0~100점):**  
  기본 50점 + 가격 경쟁력(조정 이익률 1%당 2점, 최대 $\pm 30$점) + 주행거리 매력도($\pm 10$점) + 무사고/성능점검 가점($\pm 15$점) + 가격 인하 모멘텀($+5$점) 종합 후 신뢰도 가중치 곱연산.
- **표본 3대 미만:** 왜곡 방지를 위해 즉시 `INSUFFICIENT_DATA` 처리 (`opportunity_score = None`).

### 2) 알고리즘의 한계점
1. **허위/미끼 매물 왜곡:** 시세보다 비정상적으로 낮게 등록된 허위 매물의 경우 점수가 높게 나올 수 있으므로, 딜러 파트너의 실차 전산 교차 검증이 필수입니다.
2. **세부 유상 옵션 가치 미반영:** 썬루프, ADAS 패키지 등 100~300만 원 상당의 유상 옵션이 트림명에 명시되지 않은 경우 가치 보정에서 누락될 수 있습니다.
3. **실차 미세 컨디션:** 엔진 미세누유, 실내 악취/흡연, 타이어 마모 등은 성능점검표 외 물리적 요소이므로 현장 딜러 검수가 필수적입니다.

---

## 4. 아직 구현되지 않은 기능 (Next Backlog)
1. **실시간 플랫폼 크롤링 어댑터:** 엔카, KB차차차 등 각 플랫폼의 이용약관 및 합법적 데이터 제공 방식에 따른 자동 수집기.
2. **AI 영상 자동 생성 API 연동:** 선정된 상위 매물에 대한 숏폼 영상(Wan 2.1 / Remotion) 렌더링 파이프라인 연결.
3. **실제 판매 성과 학습 모델 (Reinforcement Learning / Bandit):** 조회수, 유입 문의 수, 실계약 성사 데이터를 바탕으로 기회 점수 가중치를 자동 보정하는 사후 학습 루프.

---

## 5. 결론 및 PR 현황

차피셜은 특정 단지의 3대 매물 대기 상태를 벗어나, **"전국 공개 매물을 분석하여 최고의 판매 기회 차량을 자동 발굴하고 25년 베테랑 딜러 파트너와 협력하는 진짜 사업 모델"**의 데이터 MVP 구축을 성공적으로 완료하였습니다.
