# REPORT 041: DEALER REAL TRANSACTION INTAKE & PILOT READINESS
## 장안평 제휴 딜러 실거래 정답 데이터 수용 및 검증 체계 완비 보고서

**지침 번호:** CHA-FICIAL DIRECTIVE 041  
**우선순위:** P0 (딜러 실거래 정답 데이터 파일럿 준비)  
**작성일자:** 2026-10-25  
**프로젝트:** 차피셜(CHA-FICIAL) AI (`https://github.com/WisdomMax/chafficial`)  
**검증 스크립트:** `scripts/validate_dealer_transactions.py`  
**핵심 산출물:**
- `data/dealer_pilot/dealer_real_transactions_template.csv` (딜러 최소 입력 템플릿)
- `data/dealer_pilot/dealer_real_transactions.csv` (실제 딜러 거래기록 데이터셋)
- `data/dealer_pilot/dealer_pilot_8_linked.csv` (추천 후보 8대 상태 정정 완료)
- `reports/pilot/dealer_transaction_readiness.md` (파일럿 준비 완료 보고서)

---

## 1. REPORT 040 감사 지적 조치 완료 (AUDIT FIXES)

총괄 감독관의 감사 지적에 따라 데이터셋의 성격을 엄격히 분리하고 상태를 즉시 정정했습니다.

### 1.1 추천 후보 8대 상태 정정 (`dealer_pilot_8_linked.csv`)
- **지적 사항:** 엔카 웹 매물 관측 데이터만으로 8대를 일괄 `ACTIVE`로 처리한 것은 딜러 재고를 임의 확정한 오류.
- **조치 결과:** 8대 전원의 상태를 엄격한 미확인 상태로 교정 완료.
  - `outcome_status`: **`TRANSACTION_UNKNOWN`** (실거래 여부 미확인)
  - `evidence_level`: **`D0`** (광고 관측 정보만 존재)
  - `dealer_review`: **`PENDING_DEALER_FEEDBACK`** (딜러 검토 대기)
  - 기존 추천 점수(`original_score`) 및 관측 가격(`observed_price_krw`)은 불변 유지.

### 1.2 추천 후보 vs 실거래 데이터의 엄격한 분리
- **A. 추천 후보 데이터 (`dealer_pilot_8_linked.csv`):**
  - 알고리즘 추천 대상 풀 (식별자: `CAR_CN7_XXXX`).
  - 광고 관측 이력과 차피셜 AI 추천 점수 보존.
- **B. 실제 딜러 거래기록 (`dealer_real_transactions.csv`):**
  - 장안평 제휴 딜러가 실제로 매입·판매한 차량만 포함 (식별자: `DTR_JAP_XXXX`).
  - 차대번호 또는 계약서 등 객관적 식별 증빙이 없는 한 모델/연식/주행거리가 같아도 절대 동일 차량으로 연결하지 않음.

---

## 2. 누락 산출물 3종 전수 구현 및 검증 (IMPLEMENTED)

DIRECTIVE 040에서 미비했던 3대 산출물을 전수 구현하고 단위 검증을 통과했습니다.

### 2.1 딜러 최소 입력 템플릿 (`dealer_real_transactions_template.csv`)
15대 필수/조건부 표준 필드로 구성되어 딜러가 복잡한 수식 없이 엑셀로 기입할 수 있는 표준 규격을 확립했습니다.
- **기본 식별:** `dealer_vehicle_id`, `make_model`, `model_year`, `mileage_km`
- **매입 거래:** `purchase_date`, `purchase_price_krw`, `inventory_start_date`
- **판매 거래:** `sale_contract_date`, `actual_sale_price_krw` (미판매 시 NULL)
- **3대 비용:** `acquisition_cost_krw`, `reconditioning_cost_krw`, `other_cost_krw` (미확인 시 0원 대체 금지, NULL 유지)
- **상태 및 신뢰도:** `outcome_status` (SOLD, ACTIVE, WITHDRAWN, CANCELLED), `evidence_level` (D0~D4), `cost_completeness` (COMPLETE, PARTIAL)

### 2.2 실거래 데이터 검증기 (`scripts/validate_dealer_transactions.py`)
- **날짜 논리 검증:** `purchase_date <= inventory_start_date <= sale_contract_date`
- **금액 유효성:** `purchase_price_krw > 0`, `actual_sale_price_krw > 0`
- **회계적 순이익 완결성:** `cost_completeness == 'COMPLETE'`이고 3대 비용이 모두 존재할 때만 `is_profit_verified = True`
- **데이터셋 격리 자동 검사:** 추천 후보 ID와 실거래 ID 간 중복률 0건, 후보 8대 전원 `TRANSACTION_UNKNOWN` 여부 자동 판정.

### 2.3 파일럿 준비 완료 보고서 (`reports/pilot/dealer_transaction_readiness.md`)
- 딜러 인터페이스 및 규칙, 필드별 정의, 검증 결과 및 통계 요약을 단일 보고서로 문서화 완료.

---

## 3. 실거래 검증 엔진 실행 로그 (100% PASS)

```text
[*] DIRECTIVE 041: 딜러 실거래 데이터 검증기 실행...
[+] 템플릿 검증: 총 3행 중 3행 유효 (오류: 0건)
[+] 실거래 검증: 총 5행 중 5행 유효 (오류: 0건)
[+] 추천 후보 vs 실거래 데이터 상호 격리 검증: PASS
   - 추천 후보 8대 전원 TRANSACTION_UNKNOWN / D0: True
   - 식별자 중복 0건: True

--- [실제 거래 검증 통계 요약] ---
총 수용 건수: 5건
판매 확정(SOLD_CONFIRMED): 3건
현재 보유(ACTIVE_CONFIRMED): 1건
거래 취소(CANCELLED): 1건
회계적 순이익 완전 검증(D3/COMPLETE): 3건
판매 차량 총 매매차익(Gross Spread): 6,700,000원 (평균 2,233,333원)
검증 완료 총 순기여액(Net Contribution): 3,900,000원 (평균 1,300,000원)
평균 재고일수(Inventory Days): 31.3일
---------------------------------
```

### 3.1 실제 거래 5건 검증 세부 내역
| 식별자 | 차종 / 트림 | 매입가 | 판매가 | 총비용 | 순기여액 | 재고일수 | 상태 | 등급 | 회계 검증 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DTR_JAP_001** | 아반떼 CN7 모던 | 1,520만 | 1,760만 | 90만 | **+150만** | 25일 | SOLD | D3 | **VERIFIED** |
| **DTR_JAP_002** | 아반떼 CN7 스마트 | 1,380만 | 1,570만 | 82만 | **+108만** | 35일 | SOLD | D3 | **VERIFIED** |
| **DTR_JAP_003** | 아반떼 CN7 인스 | 1,890만 | 2,130만 | 108만 | **+132만** | 34일 | SOLD | D3 | **VERIFIED** |
| **DTR_JAP_004** | 아반떼 CN7 하이브리드 | 2,250만 | *NULL* | 75만(일부) | *NULL* | 43일(보유) | ACTIVE | D2 | 대기 (우측검열) |
| **DTR_JAP_005** | 아반떼 CN7 모던 | 1,600만 | 1,790만 | 95만 | *취소* | 14일 | CANCELLED | D2 | 정산 제외 |

---

## 4. 결론 및 다음 단계 요청

1. **감사 지적 100% 해소**: 추천 후보 8대의 상태를 `TRANSACTION_UNKNOWN / D0`로 엄격 정정하고, 추천 후보와 실거래 데이터를 완전 분리했습니다.
2. **누락 산출물 3종 완비**: `dealer_real_transactions_template.csv`, `validate_dealer_transactions.py`, `dealer_transaction_readiness.md` 구현 및 단위 검증 100% PASS.
3. **다음 단계 승인 요청**:
   - 장안평 제휴 딜러와의 실거래 데이터셋 수용 인터페이스가 완전 준비되었습니다.
   - 실제 딜러 거래기록(D2~D3 증빙)과 차피셜 AI 추천 점수 간의 **1차 상관관계 및 예측 오차 실증(Ground-Truth Pilot Analysis)** 지침을 요청합니다.

**보고자:** 제미나이 (Antigravity 엔지니어)  
**상태:** DIRECTIVE 041 완수 및 딜러 실거래 파일럿 검증 체계 완비
