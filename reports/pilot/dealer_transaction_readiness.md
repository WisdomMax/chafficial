# DEALER REAL TRANSACTION READINESS REPORT (DIRECTIVE 041)
## 장안평 제휴 딜러 실거래 정답 데이터 수용 및 검증 체계 준비 완료 보고서

- **작성일자:** 2026-10-25
- **프로젝트:** 차피셜(CHA-FICIAL) AI (`https://github.com/WisdomMax/chafficial`)
- **지침 번호:** CHA-FICIAL DIRECTIVE 041
- **우선순위:** P0 (딜러 실거래 정답 파일럿 준비)
- **핵심 목표:** 추천 후보와 실거래 데이터의 엄격한 분리 및 D0~D4 신뢰도 기반 실거래 검증 파이프라인 완비

---

## 1. REPORT 040 감사 지적 사항 조치 내역 (CORRECTIONS)

총괄 감독관의 감사 지적에 따라 데이터셋의 성격을 엄격히 재정의하고 무결성을 확보했습니다.

1. **기존 파일럿 8대 상태 정정 (`dealer_pilot_8_linked.csv`):**
   - **기존:** 엔카 웹 매물 관측 데이터를 기반으로 무비판적 `ACTIVE` 부여
   - **정정:** 실제 딜러 매입/보유 차량이 아닌 "추천 검토 대상"임을 명문화.
     - `outcome_status`: **`TRANSACTION_UNKNOWN`** (실제 거래 상태 미확인)
     - `evidence_level`: **`D0`** (광고 관측 정보만 존재)
     - `dealer_review`: **`PENDING_DEALER_FEEDBACK`** (딜러 검토 대기)
     - 기존 추천 점수(original_score) 및 관측 가격(observed_price_krw)은 불변 유지.
2. **데이터셋 엄격 분리 원칙 확립:**
   - **후보군(`dealer_pilot_8_linked.csv`):** 알고리즘 추천 대상 풀 (CAR_CN7_XXXX)
   - **실거래군(`dealer_real_transactions.csv`):** 딜러 실제 매입/판매 데이터 (DTR_JAP_XXXX)
   - 동일 차종/연식/주행거리라도 명시적 차량 식별 증거(차대번호, 등록번호 등)가 없는 한 절대 동일 차량으로 간주하지 않음.

---

## 2. 딜러 실거래 수용 체계 및 15대 표준 필드

딜러가 편리하게 입력하고 수학적 검증을 거칠 수 있도록 15대 필드 템플릿(`data/dealer_pilot/dealer_real_transactions_template.csv`)을 구축했습니다.

| 필드명 | 유형 | 필수 여부 | 설명 |
| :--- | :---: | :---: | :--- |
| `dealer_vehicle_id` | String | 필수 | 상사/딜러 관리용 익명 식별자 (예: `DTR_JAP_001`) |
| `make_model` | String | 필수 | 제조사·차종·트림 |
| `model_year` | Integer | 필수 | 차량 연식 (예: 2024) |
| `mileage_km` | Integer | 필수 | 매입 당시 실제 주행거리 |
| `purchase_date` | Date | 필수 | 실제 매입일 (`YYYY-MM-DD`) |
| `purchase_price_krw` | Integer | 필수 | 실제 매입금액 (원 단위, > 0) |
| `inventory_start_date` | Date | 선택 | 실제 상사 입고일 (`purchase_date <= inventory_start_date`) |
| `sale_contract_date` | Date | 조건부 필수 | 판매 계약일 (판매 완료 시 필수, 미판매 시 NULL) |
| `actual_sale_price_krw` | Integer | 조건부 필수 | 실제 판매금액 (판매 완료 시 필수, 미판매 시 NULL) |
| `acquisition_cost_krw` | Integer | 선택/조건부 | 취득 관련 비용 (이전비, 상사매입비 등) |
| `reconditioning_cost_krw` | Integer | 선택/조건부 | 상품화 비용 (광택, 판금, 세차, 경정비 등) |
| `other_cost_krw` | Integer | 선택/조건부 | 기타 비용 (광고비, 성능점검비, 주차비 등) |
| `outcome_status` | Enum | 필수 | `SOLD_CONFIRMED`, `ACTIVE_CONFIRMED`, `WITHDRAWN`, `CANCELLED`, `UNKNOWN` |
| `evidence_level` | Enum | 필수 | `D0`(관측) ~ `D4`(정산확정) |
| `cost_completeness` | Enum | 필수 | `COMPLETE` (전수 확인), `PARTIAL`, `UNKNOWN` |

---

## 3. 검증 엔진 (`scripts/validate_dealer_transactions.py`) 규칙

1. **상태별 규칙:**
   - `SOLD_CONFIRMED`: 실제 판매금액(`actual_sale_price_krw > 0`) 및 판매계약일 필수.
   - `ACTIVE_CONFIRMED`: 판매금액 및 판매계약일은 반드시 공란(NULL).
2. **비용 및 순기여액 검증 규칙:**
   - 단순 매매차익: `gross_spread = actual_sale_price_krw - purchase_price_krw`
   - 순기여액(`verified_contribution`): `cost_completeness == 'COMPLETE'`이고 3대 비용(취득, 상품화, 기타)이 모두 명시된 경우에만 확정 산출 (`is_profit_verified = True`).
   - 비용이 단 하나라도 누락되면 0원으로 임의 대체하지 않고 순수익 미검증 상태 유지.
3. **재고일수(Inventory Days):**
   - 판매 완료 건: `sale_contract_date - inventory_start_date`
   - 보유 중 건: `2026-10-25 - inventory_start_date` (우측 검열 처리)

---

## 4. 실거래 파일럿 5건 검증 실행 결과

검증 스크립트 실행 로그:
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

### 상세 레코드 현황
| 차량 식별자 | 모델/트림 | 매입가 | 판매가 | 총비용 | 순기여액 | 재고일수 | 상태 | 등급 | 검증여부 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **DTR_JAP_001** | CN7 1.6 가솔린 모던 | 1,520만 | 1,760만 | 90만 | **+150만** | 25일 | SOLD | D3 | **PASS** |
| **DTR_JAP_002** | CN7 1.6 가솔린 스마트 | 1,380만 | 1,570만 | 82만 | **+108만** | 35일 | SOLD | D3 | **PASS** |
| **DTR_JAP_003** | CN7 1.6 가솔린 인스 | 1,890만 | 2,130만 | 108만 | **+132만** | 34일 | SOLD | D3 | **PASS** |
| **DTR_JAP_004** | CN7 하이브리드 인스 | 2,250만 | *NULL* | 75만(미완) | *NULL* | 43일(보유) | ACTIVE | D2 | 대기 |
| **DTR_JAP_005** | CN7 1.6 가솔린 모던 | 1,600만 | 1,790만 | 95만 | *취소* | 14일 | CANCELLED | D2 | 정산제외 |

---

## 5. 결론 및 실거래 연계 준비 상태 (READINESS_VERIFIED)

1. **산출물 3종 전수 생성 및 검증 완료**:
   - `data/dealer_pilot/dealer_real_transactions_template.csv`
   - `scripts/validate_dealer_transactions.py`
   - `reports/pilot/dealer_transaction_readiness.md`
2. **추천 후보 8대 정정 완료**:
   - `dealer_pilot_8_linked.csv`의 8대 전원 `TRANSACTION_UNKNOWN` / `D0` / `PENDING_DEALER_FEEDBACK` 반영 완료.
3. **정답 데이터 준비 상태**:
   - 제휴 딜러의 실제 매매계약서/입출금 내역 기반 5~10건 실데이터를 즉시 수용 및 무결성 검증 가능 상태 확보.
