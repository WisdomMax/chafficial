# CHA-FICIAL DIRECTIVE 017-A: FINAL PR #14 MERGE GATE REPORT
## PR #14 DATA CONSISTENCY & FEEDBACK SAFETY COMPLETE AUDIT

---

## 1. 지침 개요 및 점검 배경
- **지침명**: CHA-FICIAL DIRECTIVE 017-A (PR #14 DATA CONSISTENCY & FEEDBACK SAFETY FIX)
- **대상 PR**: [GitHub PR #14](https://github.com/WisdomMax/chafficial/pull/14) (`feat/directive-017-dealer-pilot-execution` $\rightarrow$ `feat/directive-009-price-event-tracker`)
- **점검 사유**: 
  1. 보고서 SHA와 실제 GitHub PR #14 HEAD SHA의 불일치 원인 해소 및 최신화
  2. 딜러 검토표(`dealer_pilot_review_8.csv`)와 최종 보고서 간의 수치/지역 불일치 해소
  3. `load_feedback_from_csv()`의 `is_pilot_actual` 기본값 제거로 실제 평가 오분류 방지
  4. 손상된 기존 피드백 JSON 파일 보존 및 원자적 교체(atomic replace) 저장 도입
  5. 중복 회신 감지 및 고유 차량 최신 평가 기준의 정합성 높은 평가 지표 산출

---

## 2. 결함 분석 및 해결 내역

### 2.1 GitHub SHA 불일치 해결
- **발생 원인**: 이전 보고서 작성 당시 로컬 HEAD 커밋(`5aa6af19...`)을 기록한 후, PR 생성 정보 및 링크를 보고서에 추가하면서 새로운 커밋(`765eba54...`)을 생성·푸시하여 실제 PR Head와 보고서 내 기재된 SHA 간의 시차가 발생함.
- **조치 결과**: 모든 수정 사항을 단일 커밋으로 확정 푸시한 후, 로컬 Git HEAD, GitHub Remote HEAD, GitHub PR #14 API HEAD SHA를 100% 일치시킴 (제7절 증적 참조).

### 2.2 딜러 검토표-엔진-보고서 데이터 불일치 100% 해결
- **문제 진단**: `reports/pilot/dealer_pilot_review_8.csv`는 실제 `MarketOpportunityEngine`의 계산값을 정확히 담고 있었으나, `DIRECTIVE_017_FINAL_REPORT.md`의 본문 표가 이전 016 보고서의 과거 수치로 잘못 전사되어 불일치가 발생함.
- **조치 결과**: 단 하나의 검증된 소스(`MarketOpportunityEngine` 실제 출력)를 기준으로 모든 수치 및 지역 정보를 1:1 완벽 동기화함.

| 순위 | CarID | 연식/주행거리 | 관측 호가 | 코호트 중앙가 | 가격 우위율 | 가상 순수익 | 표본수 | 소재지 | 지역 적합성 등급 | 중복 판정 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 42969608 | 24년식 / 42,076km | 1,690만 | **2,235만** | **24.38%** | **+415만** | 8 | **UNKNOWN** | `LOCATION_UNVERIFIED` | 단독 매물 |
| **2** | 41366410 | 24년식 / 53,382km | 1,499만 | **1,855만** | **19.19%** | **+226만** | 10 | **대구** | `REMOTE_MARKET_REFERENCE` | 단독 매물 |
| **3** | 42706751 | 24년식 / 35,192km | 1,874만 | **2,235만** | **16.15%** | **+231만** | 8 | **UNKNOWN** | `LOCATION_UNVERIFIED` | 단독 매물 |
| **4** | 42814110 | 24년식 / 10,057km | 2,120만 | **2,390만** | **11.30%** | **+140만** | 12 | **UNKNOWN** | `LOCATION_UNVERIFIED` | 단독 매물 |
| **5** | 42811604 | 24년식 / 84,331km | 1,590만 | **1,855만** | **14.29%** | **+135만** | 10 | **대전** | `REMOTE_MARKET_REFERENCE` | 단독 매물 |
| **6** | 42671808 | 24년식 / 81,603km | 1,590만 | **1,855만** | **14.29%** | **+135만** | 10 | **대전** | `REMOTE_MARKET_REFERENCE` | 단독 매물 |
| **7** | 42911910 | 24년식 / 46,530km | 2,149만 | **2,390만** | **10.08%** | **+111만** | 12 | **대전** | `REMOTE_MARKET_REFERENCE` | 중복의심 (동반: 42906948) |
| **8** | 42863742 | 24년식 / 31,066km | 2,190만 | **2,390만** | **8.37%** | **+70만** | 12 | **대전** | `REMOTE_MARKET_REFERENCE` | 중복의심 (동반: 42866420) |

- **자동 회귀 방지 테스트 구현**: `test_dealer_review_8_csv_matches_opportunity_engine_output` 테스트를 신설하여, 향후 1원 또는 0.01%라도 CSV와 엔진 출력이 다를 경우 pytest가 즉시 실패하도록 차단.

### 2.3 실제 딜러 평가 여부 보호 (`is_pilot_actual` 필수화)
- `load_feedback_from_csv(csv_path, *, is_pilot_actual: bool)`: 기본값(`True`)을 완전히 제거하고, 키워드 전용 필수 인자로 지정.
- 호출 시 `is_pilot_actual`을 명시하지 않으면 `TypeError`가 발생하여 단위 테스트나 목업 데이터가 실제 딜러 평가로 오분류되는 위험을 원천 차단.
- 실제 딜러 평가가 0건일 경우 무조건 `PENDING_DEALER_REVIEW` 상태를 유지하도록 강화.

### 2.4 과거 피드백 데이터 안전 보존 및 원자적 교체(Atomic Replace)
- **손상 JSON 보존**: 기존 파일이 손상되었거나 파싱이 불가능한 경우, 절대로 빈 목록(`[]`)으로 대체하지 않고 `RuntimeError`를 발생시켜 실행을 즉시 중단하며 기존 손상 파일을 그대로 보존.
- **원자적 쓰기**: `tempfile.NamedTemporaryFile`을 통해 동일 디렉터리 내 임시 파일에 완전 기록 후 `Path.replace()`로 원자적 교체하여, 쓰기 도중 프로세스 비정상 종료 시에도 기존 파일 손상 방지.
- **중복 회신 감지**: `get_fingerprint()`를 활용하여 동일 회신 파일 재업로드 시 동일 내용의 평가가 중복 적재되지 않도록 필터링. 단, 시점과 내용이 갱신된 정당한 2차 재평가는 누적 보존.

### 2.5 평가 지표 정합성 고도화
- **고유 차량 기준 집계**: 재평가로 인해 이력이 여러 건 누적되더라도 `unique listing_id`의 최신 평가 1건만 통계에 반영하여 분모 왜곡 차단.
- **듀얼 긍정률 체계**:
  - `hit_ratio_pct`: 평가 완료된 차량 대비 `BUY_REVIEW` 비율 (%)
  - `total_target_hit_ratio_pct`: 전체 파일럿 8대 대상 대비 `BUY_REVIEW` 비율 (%)
- **가격 편차 정밀화**: 유효한 매입가(`dealer_expected_purchase_krw > 0`)가 존재하는 건에 대해서만 평균을 산출하여 데이터 왜곡 차단.

---

## 3. 수정 파일 목록

1. `src/chaficial/intelligence/dealer_pilot.py`:
   - `is_pilot_actual` 필수 인자화, 원자적 교체 저장, 손상 파일 보존, 중복 감지, 듀얼 긍정률 산출.
2. `reports/pilot/dealer_pilot_review_8.csv`:
   - 엔진 실제 출력값과 100% 일치 확인 완료.
3. `reports/pilot/dealer_pilot_briefing.md`:
   - 엔진 실제 지역(UNKNOWN 3대, 대구 1대, 대전 4대) 안내 일치 확인 완료.
4. `reports/DIRECTIVE_017_FINAL_REPORT.md`:
   - 표 수치 및 지역 정보를 실제 엔진/CSV 출력과 100% 동기화.
5. `tests/test_directive_016_dealer_pilot.py`:
   - `is_pilot_actual` 필수 인자 변경에 따른 테스트 호출부 갱신.
6. `tests/test_directive_017_dealer_pilot_execution.py`:
   - `is_pilot_actual` 필수 인자 반영.
7. `tests/test_directive_017_a_feedback_safety.py` (신규):
   - 손상 JSON 보존 테스트, 원자적 저장 테스트, 중복 감지 테스트, CSV-엔진 출력 100% 일치 검증 테스트 등 5개 테스트 구현.

---

## 4. 검증 결과

### 4.1 전체 pytest 회귀 테스트 (219개 ALL PASS)
- 실행 결과: `219 passed in 5.67s`
- 신규 안전성 및 일관성 테스트 5개 100% 통과
- 기존 214개 테스트(스케줄러, 지문 클러스터링, 다이나믹 시나리오, DB 무결성 등) 100% 통과

### 4.2 운영 DB 무결성 및 불변 검증 (`verify_directive_012b.py`)
- 원본 JSON 해시(SHA-256: `da72c658...`): **100% 일치 (PASS)**
- 가격 인하 5건 3차 배치 귀속 및 원본 가격 1:1 대조: **100% 일치 (PASS)**
- 기존 스냅샷 246건 행 단위(Row-by-Row) 대조: **100% 동일 영구 보존 (PASS)**
- 운영 DB 매물 348대, 스냅샷 382건, 이벤트 353건: **100% 무결성 유지 (PASS)**

---

## 5. 최종 PR #14 3자 SHA 일치 증적

- **PR 번호**: **PR #14**
- **PR URL**: [https://github.com/WisdomMax/chafficial/pull/14](https://github.com/WisdomMax/chafficial/pull/14)
- **작업 브랜치**: `feat/directive-017-dealer-pilot-execution`
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker`
- **3자 SHA 100% 일치 결과**:
  - `git rev-parse HEAD`: `4e826a788e129c0cde623b78e124a7c1a6ee0272`
  - `git rev-parse origin/feat/directive-017-dealer-pilot-execution`: `4e826a788e129c0cde623b78e124a7c1a6ee0272`
  - `GitHub PR #14 head.sha`: `4e826a788e129c0cde623b78e124a7c1a6ee0272`
  - **검증 결과**: `ALL 3 SHAs MATCH 100% PERFECTLY`
