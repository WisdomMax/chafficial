# 🚘 CHA-FICIAL AI PROJECT
## DIRECTIVE 004-A FINAL AUDIT FIX 완료 보고서
### ORM 제약조건 정합성 실증 · 개인정보 원천 차단 · 권한 보안 게이트 및 실데이터 분리 완비

**발신:** Google Antigravity (차피셜 AI 연구팀)  
**수신:** CHA-FICIAL AI 연구 총괄 감독 (ChatGPT)  
**저장소:** https://github.com/WisdomMax/chafficial  
**신규 작업 브랜치:** [`feat/directive-004a-partner-intake`](https://github.com/WisdomMax/chafficial/tree/feat/directive-004a-partner-intake)  
**대상 PR #3:** https://github.com/WisdomMax/chafficial/pull/3  
**기준 커밋:** `55ae970` -> **감사 수정 커밋:** [`5b1488f`](https://github.com/WisdomMax/chafficial/commit/5b1488f)  
**GitHub Actions CI:** [Run #39521228638 (Completed / Success)](https://github.com/WisdomMax/chafficial/actions/runs/39521228638)  
**작성일자:** 2026-10-21  

---

## 0. 핵심 지표 현황 요약 (보수적 사실주의 원칙)

| 점검 지표 | 수치 / 판정 | 비고 |
| :--- | :---: | :--- |
| **합성 샘플 검증 건수** | **3건** | `templates/PARTNER_LISTING_INTAKE_SYNTHETIC_SAMPLE.csv` 전수 통과 |
| **확보·검증된 실제 데이터** | **0건** | 외부 실매물 임의 수집 없음 (실제 인입 전 안전장치 구축 완료) |
| **실제 광고 권한 확인 건수** | **0건 (미확인)** | 서면 위임 증빙 없는 차량 마케팅 대상 전면 배제 |
| **실제 계약 및 정산 확인 건수** | **0건** | 실제 거래 및 광고 집행 0원 동결 |

---

## 1. 감사 지적 결함별 수정 및 검증 결과

### 1) CRITICAL: ORM 매핑 결과의 실제 DB 제약조건 위반 해결
- **결함 원인:**
  - `VehicleCatalog`: `catalog_id`에 임의 문자열 주입 및 NOT NULL인 `generation` 누락.
  - `VehicleIdentity`: DB CHECK에 없는 `identity_status="ANONYMIZED_PARTNER_CODE"` 및 근거 없는 0.95 confidence 부여.
  - `Listing` & `ListingSnapshot`: DB CHECK에 없는 `SOLD` 상태값 사용 및 `REG_SEOUL_JANGANPYEONG` 오타.
  - `SalesCandidate`: 인입 엔진에서 후보군을 임의로 자동 생성.
- **수정 조치:**
  - `catalog_id`는 DB Autoincrement 정수이므로 인스턴스화 시 지정하지 않음.
  - `generation`은 `sub_model` 또는 'UNKNOWN'으로 보정하여 NOT NULL 준수.
  - `identity_status`는 DB CHECK 규격인 `'UNCONFIRMED'`, `identity_confidence`는 0.5 기본값 적용.
  - 판매 완료 시 상태는 DB CHECK 규격에 따라 `'DELISTED'`로 전이 (미계약은 `'ACTIVE'`).
  - 지역 ID는 `configs/regions.yaml`에 정의된 **`REGION_JANGANPYEONG`**으로 정정.
  - 일반 매물 인입과 판매 후보(`SalesCandidate`) 선정을 엄격히 분리 (인입 시 후보 자동 생성 금지).
- **실제 SQLite DB INSERT/FLUSH 실증 (`test_synthetic_3_cars_actual_orm_insert_and_flush`):**
  - 메모리 SQLite에 Base 스키마 전체를 생성하고, 합성 매물 3건의 ORM 객체를 `session.add_all()` 및 `session.flush()` 실행하여 **모든 NOT NULL, CHECK, FK 제약조건을 100% 통과함을 실증**하였습니다.
  - 검증 직후 `session.rollback()`을 호출하여 DB 오염이 전혀 없음을 확인하였습니다.

### 2) CRITICAL: CSV 검증 및 개인정보 유출 방지
- **결함 원인:** 필수 헤더 외에 허용되지 않은 추가 컬럼이나 개인정보(차량번호, 차대번호, 소유자명 등) 유입 시 거절 로직 부재.
- **수정 조치:**
  - `PERMITTED_HEADERS` 외 임의 컬럼 유입 시 `FORBIDDEN_EXTRA_COLUMN` 에러 발생.
  - 개인정보 관련 키워드(plate, vin, owner, ssn, phone, 차량번호, 차대번호, 소유자, 연락처 등) 컬럼 탐지 시 `PII_COLUMN_PROHIBITED`로 즉시 거절.
  - 에러 리포트 내에 실명이나 차량번호 등 민감 원본 값을 전혀 노출하지 않도록 메시지 정제.
- **테스트 검증 (`test_forbidden_extra_columns_and_pii_rejection`):** PASS

### 3) HIGH: 광고 위임 권한의 보안 및 상태 관리
- **결함 원인:** 단순 문자열 'DELEGATED' 또는 단순 ID 집합으로 권한을 관리하여 유효기간, 철회, 제3자 위임 범위 누락 위험.
- **수정 조치:**
  - `DelegationProof` 서면 증빙 모델 도입 (`valid_until`, `is_revoked`, `third_party_firm_consent`).
  - 유효기간 경과, 권한 철회, 제3자 상사 위탁 차량의 동의 미확인 시 `is_marketing_eligible=False`로 자동 제외.
  - 테스트용 권한 1건은 오직 테스트 가상 객체일 뿐이며 현실 세계의 실제 확보 건수는 계속 0건으로 유지.
- **테스트 검증 (`test_delegation_proof_security_expiry_revocation_and_third_party`):** PASS

### 4) HIGH: 계약 및 정산 금액 검증
- **결함 원인:** SETTLED 상태 계산 시 누락된 비용/수수료 항목을 0으로 임의 대체할 가능성.
- **수정 조치:**
  - `SETTLED` 상태에서 필수 정산 필드가 비어있으면 `MISSING_SETTLED_AMOUNTS`로 인입 거절.
  - 음수 수수료 및 음수 비용 항목 탐지(`NEGATIVE_SETTLEMENT_AMOUNT`).
  - 미계약(`UNSETTLED`) 상태의 미확정 필드는 NULL을 정상 허용.
- **테스트 검증 (`test_settlement_missing_amounts_and_negative_amounts_rejection`):** PASS

### 5) HIGH: 합성 데이터와 실데이터 분리
- **결함 원인:** 단순 Boolean `is_synthetic=False` 호출만으로 실데이터 카운트가 오를 위험.
- **수정 조치:**
  - 관리자(사장님)의 공식 승인 증빙(`IntakeApprovalProof`)이 명시적으로 주입되지 않으면 외부 데이터는 `UNVERIFIED_EXTERNAL`로 안전 격리.
  - 최종 검증 수치:
    - 합성 검증 데이터: 3건
    - 확보·검증된 실제 데이터: 0건
    - 실제 광고 권한 확인: 0건
    - 실제 계약·정산 확인: 0건
- **테스트 검증 (`test_strict_separation_of_synthetic_and_real_data`):** PASS

---

## 2. 수정한 파일 목록 및 테스트 결과

### 1) 수정한 파일 목록
1. `src/chaficial/intake/validator.py`: ORM 매핑 정합성, PII 컬럼 차단, 권한 증빙 모델, 정산 검증, 실데이터 분리
2. `src/chaficial/intake/__init__.py`: 신규 증빙 클래스(`DelegationProof`, `IntakeApprovalProof`) export
3. `tests/test_partner_intake.py`: 5대 핵심 실증 테스트 (SQLite 실제 FLUSH 포함)
4. `docs/SCHEMA_MAPPING_MATRIX.md`: 실제 DB 스키마 제약조건 반영 재작성
5. `reports/DIRECTIVE_004A_PILOT_READINESS_REPORT.md`: 본 최종 감사 보고서

### 2) 테스트 및 CI 결과
- **Pytest:** 42개 전체 테스트 통과 (`42 passed in 0.55s`)
  - `tests/test_partner_intake.py`: 5개 신규 테스트 전수 통과
- **Ruff:** `All checks passed!`
- **Demo Script:** `main.py` 데모 시나리오 무결성 검증 완료

---

## 3. 남은 한계와 기술 부채 (투명한 고지)

1. **실매물 3건의 미확보:**  
   본 004-A 단계는 어디까지나 "잘못된 데이터와 무단 권한을 걸러내는 안전 인입 엔진"을 완성한 것이며, 실제 장안평 딜러와의 서면 계약 및 실매물 3건의 데이터는 아직 수집되지 않았습니다 (004-B에서 착수 예정).
2. **카탈로그 자동 세대(Generation) 추정 모델 부재:**  
   현재는 입력 템플릿의 `sub_model` 문자열을 기반으로 `generation`을 매핑하고 있으며, 복잡한 트림/세대 자동 판정 NLP 모델은 향후 고도화 과제로 남아있습니다.
3. **오프라인 검증 의존성:**  
   성능점검기록부의 진위 여부는 현재 식별코드 기반의 규칙 검증에 머물러 있으며, 공공/상사 전산망과의 실시간 크로스체크는 정식 API 인가 전까지 오프라인 대조가 필요합니다.
