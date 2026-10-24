# CHA-FICIAL DIRECTIVE 018 FINAL: MERGE & REAL DEALER PILOT STATUS

## 1. 개요 및 PR #14 공식 병합 결과
- **지침명**: CHA-FICIAL DIRECTIVE 018: PR #14 CONTROLLED MERGE & REAL DEALER PILOT LAUNCH
- **PR 대상**: [GitHub PR #14](https://github.com/WisdomMax/chafficial/pull/14) (`feat/directive-017-dealer-pilot-execution` $\rightarrow$ `feat/directive-009-price-event-tracker`)
- **병합 직전 승인 검증**:
  - 총괄 감독 승인 HEAD SHA: `58647cffd207d2daa31b463cdde9206248e50b39`
  - GitHub PR #14 HEAD SHA: `58647cffd207d2daa31b463cdde9206248e50b39` (100% 일치)
  - Mergeable 상태: `True` (충돌 없음 확인)
- **공식 병합 수행 결과**:
  - **병합 상태 (Merged)**: `True` (공식 병합 완료, CLOSED)
  - **Merge Commit SHA**: `c4543ae45986bab5b032f722ed83f955274a8113`
  - **기준 브랜치 최신 HEAD**: `c4543ae45986bab5b032f722ed83f955274a8113` (`origin/feat/directive-009-price-event-tracker` 동기화 완료)

---

## 2. 병합 후 품질 검증 및 회귀 테스트 결과

### 2.1 전체 pytest 회귀 테스트 (222개 ALL PASS)
- **실행 결과**: `222 passed in 5.61s` (기준 브랜치 `feat/directive-009-price-event-tracker` 상에서 직접 검증)
- DIRECTIVE 017-B 이력 무결성 및 JSON 안전 보존 테스트 4종 전수 통과
- 우선 검토 8대 CSV와 엔진 출력 100% 일치 테스트 통과
- 스케줄러, 지문 클러스터링, 다이나믹 시나리오 등 기존 216개 테스트 100% 통과

### 2.2 운영 DB 무결성 검증 (`verify_directive_012b.py`)
- 원본 관측 JSON 해시 (SHA-256: `da72c658...`): **100% 일치 (PASS)**
- 가격 인하 5건 3차 배치 귀속 및 원본 가격 1:1 대조: **100% 일치 (PASS)**
- 기존 스냅샷 246건 행 단위(Row-by-Row) 전수 대조: **100% 불변 보존 (PASS)**
- 운영 DB 매물 348대, 스냅샷 382건, 이벤트 353건: **100% 영구 보존 (PASS)**

---

## 3. 실전 딜러 파일럿 패키지 및 8대 후보 전달 준비

### 3.1 파일럿 패키지 경로
1. **딜러 브리핑 안내서**: `reports/pilot/dealer_pilot_briefing.md`
2. **우선 검토 8대 실전 검토표**: `reports/pilot/dealer_pilot_review_8.csv` (UTF-8 with BOM)
3. **딜러 회신용 입력 템플릿**: `reports/pilot/dealer_pilot_feedback_template.csv` (UTF-8 with BOM)

### 3.2 딜러 전달 대상 8대 후보 현황 및 엄중한 운영 원칙 고지
- **대상 차량 식별자 (8대)**: `42969608`, `41366410`, `42706751`, `42814110`, `42811604`, `42671808`, `42911910`, `42863742`
- **핵심 데이터 투명성 원칙**:
  1. **가상 순수익(`hypothetical_net_profit`)의 한계**: 확정된 상사 순이익이 아니며, 업계 표준 상품화비(80만)와 기본 탁송료(30만)만을 가정한 단순 참고 추정치입니다. 상사 법정 수수료, 이전비, 금융이자, 재고유지비 등은 반영되어 있지 않습니다.
  2. **매물 권한 및 실차 소재지 한계**: 현재 8대는 엔카 전국 시장 관측 데이터를 통계적으로 분석한 시세 우위 후보일 뿐, 장안평 파트너의 판매 권한이 확보된 매물이 아닙니다. 실제 매입·광고·판매 가능 매물로 표현하지 않으며, 딜러 파트너의 실사 판단용 참고 자료로만 활용됩니다.
  3. **지역 적합성**: 3대는 소재지 미확인(`LOCATION_UNVERIFIED`), 5대는 대구/대전 소재(`REMOTE_MARKET_REFERENCE`)로 원거리 탁송료 및 실사 제약이 존재합니다.

---

## 4. 실전 피드백 수집 현황 및 투명성 공시

- **실제 딜러 회신 건수**: **0건 (배포 준비 완료 및 회신 대기)**
- **현재 파일럿 상태**: **`PENDING_DEALER_REVIEW` (정직한 평가 대기 명시)**
- **철저한 금지 원칙 준수**:
  - 실제 수석 딜러 파트너의 직접적인 피드백이 수신되기 전까지는 임의의 예시 데이터나 목업을 실제 평가(`is_pilot_actual=True`)로 둔갑시키지 않습니다.
  - 가짜 적중률이나 과장된 성과 지표를 일체 조작하지 않고 `PENDING_DEALER_REVIEW` 상태를 유지합니다.

---

## 5. 다음 단계에서 필요한 사람(인간 운영자)의 실제 행동

1. **딜러 파트너 미팅 및 자료 전달**:
   - 운영자가 25년 경력 장안평 수석 파트너 딜러에게 `dealer_pilot_review_8.csv` 및 `dealer_pilot_briefing.md` 전달.
2. **딜러 실전 평가 작성**:
   - 딜러가 엔카 실차 URL을 확인하고, 보험사고/용도이력 실사 후 8대에 대해 `dealer_verdict`(BUY_REVIEW, WATCH, EXCLUDE), 예상 매입/판매가, 상품화비, 핵심 사유를 `dealer_pilot_feedback_template.csv`에 기재.
3. **AI 시스템 인입 및 첫 실전 분석**:
   - 회신받은 CSV를 `load_feedback_from_csv(csv_path, is_pilot_actual=True)`로 적재하여 실제 딜러 매입 인정률(`hit_ratio_pct`) 및 호가 대비 네고 오차(`avg_price_difference_krw`) 공식 산출 및 보고서 작성.
