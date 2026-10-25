# REPORT 042: DEALER GROUND-TRUTH PROVENANCE AUDIT & SYNTHETIC DATA QUARANTINE
## 실거래 데이터 출처 감사, 모의 데이터 전면 격리 및 실거래 대기 상태 확정 보고서

**지침 번호:** CHA-FICIAL DIRECTIVE 042  
**우선순위:** P0 / CRITICAL (데이터 출처 무결성 및 엄격한 증거주의)  
**작성일자:** 2026-10-25  
**프로젝트:** 차피셜(CHA-FICIAL) AI (`https://github.com/WisdomMax/chafficial`)  
**검증 스크립트:** `scripts/validate_dealer_transactions.py`  
**운영 원칙:**
1. 증빙 없는 데이터의 실거래 주장 절대 금지 (NO RECEIPT, NO CLAIM)
2. 합성(Mock) 데이터의 실거래 세트 완전 격리 (`SYNTHETIC DATA QUARANTINE`)
3. 운영 DB 불변, 허가 없는 GitHub 커밋·푸시 금지

---

## 1. 감사 판정 및 데이터 출처의 투명한 인정 (AUDIT ACCEPTANCE)

총괄 감독관의 감사 지적을 100% 수용하고, 데이터 출처에 대한 엄격한 사실 관계를 명확히 밝힙니다.

1. **REPORT 041 5건의 실체 규명:**
   - REPORT 041에 제시된 5건(`DTR_JAP_001~005`)은 실제 장안평 딜러의 매매계약서나 입출금 영수증 원본에서 나온 것이 아니라, **파이프라인의 15개 필드 매핑 및 수학적 정합성을 검증하기 위해 엔지니어가 작성한 모의 시나리오(Synthetic/Mock) 데이터**였습니다.
2. **수익 실증 주장 공식 철회:**
   - 실제 매매계약서 원본 대조가 없는 상태에서 390만 원의 순기여액을 `VERIFIED`로 보고했던 것은 차피셜의 증거주의 원칙에 위배된 것이었습니다.
   - 이에 따라 **실거래 수익 실증 주장을 전면 철회**하고, 검증 등급을 `D3`에서 **`D0 (SYNTHETIC)`**으로 즉시 강등했습니다.

---

## 2. 합성 데이터 전면 격리 조치 내역 (QUARANTINE COMPLETED)

실제 데이터와 테스트 데이터의 혼선을 원천 방지하기 위해 3중 격리 조치를 완료했습니다.

### 2.1 파일 분리 및 보관 경로
| 데이터셋 구분 | 파일 경로 | 현재 상태 | 데이터 건수 |
| :--- | :--- | :---: | :---: |
| **A. 알고리즘 추천 후보** | `data/dealer_pilot/dealer_pilot_8_linked.csv` | `TRANSACTION_UNKNOWN` / `D0` | 8건 |
| **B. 수식 검증용 합성 데이터 (격리)** | `data/dealer_pilot/synthetic_test_transactions.csv` | `SYNTHETIC_QUARANTINE` / `D0` | 5건 |
| **C. 실제 딜러 거래기록** | `data/dealer_pilot/dealer_real_transactions.csv` | **`READY_FOR_DEALER_DATA`** | **0건 (순수 대기)** |

### 2.2 검증 엔진 방어벽 강화 (`scripts/validate_dealer_transactions.py`)
- **D3/D4 증빙 필수화:** `evidence_level`이 명시적인 증빙 대조 등급(`D3`, `D4`)이 아닌 경우, 설령 모든 비용 칸이 채워져 있더라도 `is_profit_verified = False`로 강제 처리.
- **실거래 파일 순수성 보존:** `dealer_real_transactions.csv`는 현재 0건이며, 제휴 딜러의 계약서 사본 또는 금융 이체 증빙이 수신되기 전까지 어떠한 가짜 데이터도 진입할 수 없도록 원천 차단.

---

## 3. 격리 검증 엔진 실행 로그 (PASS)

```text
[*] DIRECTIVE 042: 딜러 실거래 데이터 출처 감사 및 격리 검증기 실행...
[+] 1. 입력 템플릿 검증: 3행 유효 (오류: 0건)
[+] 2. 격리된 합성 데이터(SYNTHETIC) 검증: 5행 유효 (전수 D0 격리 확인)
[+] 3. 실제 딜러 거래기록 파일(dealer_real_transactions.csv) 상태:
   -> [STATUS: READY_FOR_DEALER_DATA] 실거래 원본 증빙 인입 대기 중 (현재 등록 0건, 가짜 데이터 없음)
[+] 4. 추천 후보 8대 격리 확인: 8대 전원 TRANSACTION_UNKNOWN / D0 (True)

--- [DIRECTIVE 042 데이터 무결성 감사 결론] ---
1. 합성(Mock) 데이터 격리 완료: data/dealer_pilot/synthetic_test_transactions.csv (D0)
2. 실거래 파일 순수 상태 보존: data/dealer_pilot/dealer_real_transactions.csv (0건, READY_FOR_DEALER_DATA)
3. 허위 수익 주장 원천 차단: 실거래 증빙(D3/D4) 없는 합성 데이터는 순이익 검증 0건 처리 완료.
-----------------------------------------------
```

---

## 4. 결론 및 최종 상태 선언

1. **감사 요구사항 100% 이행**:
   - 합성 데이터는 격리 파일(`synthetic_test_transactions.csv`)로 전면 이관.
   - 실거래 파일(`dealer_real_transactions.csv`)은 0건으로 정화 완료.
2. **차피셜 시스템 현재 상태**:
   - **`READY_FOR_DEALER_DATA`** (딜러 실거래 데이터 수용 준비 완료)
   - 허위 실증이나 추정에 근거한 사업성 선언은 전면 보류.
3. **향후 운영 방침**:
   - 실제 장안평 딜러와의 오프라인 미팅 또는 공식 제휴를 통해 1차 거래 증빙(D2~D3급 영수증/계약서)이 물리적으로 입수될 때까지 추가적인 입력 시스템 고도화 및 인위적 모델 분석을 중단하고 대기 상태를 유지합니다.

**보고자:** 제미나이 (Antigravity 엔지니어)  
**상태:** DIRECTIVE 042 완수 및 합성 데이터 격리 완료 / `READY_FOR_DEALER_DATA` 확정
