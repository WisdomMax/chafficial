# 🚘 CHA-FICIAL AI PROJECT
## DIRECTIVE 004-B 완료 보고서 (PHASE 1 PREFLIGHT)
### 시계열 미래 누출 차단 · 실데이터 진위 검증 프로토콜 · 비공개 파일럿 인입 체계 완비

**발신:** Google Antigravity (차피셜 AI 연구팀)  
**수신:** CHA-FICIAL AI 연구 총괄 감독 (ChatGPT)  
**저장소:** https://github.com/WisdomMax/chafficial  
**신규 작업 브랜치:** [`feat/directive-004b-pilot-preflight`](https://github.com/WisdomMax/chafficial/tree/feat/directive-004b-pilot-preflight)  
**종속 관계:** `main` <- PR #1 <- PR #2 <- PR #3 <- **PR #4 (004-B)**  
**작성일자:** 2026-10-21  

---

## 0. 핵심 지표 현황 요약 (보수적 사실주의 원칙)

| 점검 지표 | 수치 / 판정 | 비고 |
| :--- | :---: | :--- |
| **합성 데이터 검증 건수** | **3건** | `templates/PARTNER_LISTING_INTAKE_SYNTHETIC_SAMPLE.csv` 전수 통과 |
| **실제 파트너 제공 데이터 건수** | **0건** | 외부 실매물 수집 전 안전 인입 환경만 완비 (Phase 1 완료) |
| **실제 광고 권한 검증 건수** | **0건** | 서면 위임 증빙 전 마케팅 대상 전면 배제 |
| **실제 거래 및 정산 확인 건수** | **0건** | 실제 거래 발생 없음 |
| **실제 광고 집행 비용** | **0원** | 유료 광고 집행 전면 동결 |
| **아직 확보하지 못한 자료** | **미확보** | 장안평 파트너 서면 위임 계약서 실물, 성능점검표 마스킹 사본, 비식별 실매물 3건 |
| **실데이터 입수 전 승인 필요 사항** | **대기 중** | 사장님(총괄 감독)의 장안평 파트너 현장 접촉 및 공식 계약 체결 서면 승인 |
| **최종 판정 상태** | **COMPLETED / BLOCKED** | **`DIRECTIVE 004-B PHASE 1 COMPLETED / REAL-DATA PILOT BLOCKED`** |

---

## 1. 004-B Phase 1 주요 구현 및 개선 사항

### 1) 시계열 판매 상태 미래 정보 누출 원천 차단 (Time-Travel 무결성)
- **문제점:** 사후 계약된 차량(예: 10월 1일 등록, 10월 10일 계약)을 인입할 때 첫 관측 스냅샷(`SNAP_..._INIT`)에 미래의 `DELISTED` 상태가 반영될 위험이 존재했음.
- **개선 구현 (`build_orm_entities`):**
  - 최초 관측 스냅샷은 사후 계약 여부와 무관하게 무조건 10월 1일 당시의 상태인 **`ACTIVE`** 및 목표 등록가로 고정 기록.
  - 계약 체결 사실은 10월 10일 관측 시점의 **별도 2차 스냅샷(`SNAP_..._CLOSED`)**으로 분리 생성.
  - 이를 통해 10월 5일 등 과거 시점으로 시장 데이터를 조회했을 때 미래의 판매 완료 사실이 역유출되는 것을 원천 차단.

### 2) 실데이터 승인 플래그의 신뢰성 및 진위성 격리
- 단순 Python 코드 내에서 생성된 `IntakeApprovalProof` 객체는 실데이터 진위를 보장하지 못하므로 무조건 **`SIMULATED_AUTHORIZED`**로 격리.
- 공식 현장 실사 감사 토큰(`verification_token`)과 현장 검증 플래그가 완비된 경우에만 `VERIFIED_REAL` 승격 경로를 설계하여, 현재 단계의 실데이터 건수를 **0건**으로 엄격 동결.

### 3) 광고 권한과 실제 게시 허가(Live Ad Authorization)의 엄격한 분리
- `is_marketing_eligible`: 서면 위임 및 유효기간 검증 통과 여부.
- `is_live_ad_authorized`: 실제 SNS 게시 및 유료 광고 집행 허가 여부 -> Phase 1에서는 무조건 **`False`**로 고정.

### 4) RFC 4180 표준 CSV 파서 보완
- 인용부호 안에 포함된 `#` 문자열(예: `"#특이사항: 전면 휀더 교환"`)이 파일 최상단 주석 제거 로직에 의해 훼손되지 않도록 표준 파싱 로직 정비.
- 필드 내 줄바꿈, 쉼표, 중복 헤더, 열 개수 불일치를 엄격히 통제된 에러로 검증.

---

## 2. 신규 4대 반례 테스트 (Suite A, B, C, D) 검증 결과

- **테스트 A (`test_suite_a_normal_synthetic_3_cars_flush_and_rollback`):**  
  합성 매물 3건 가격/연식/주행거리 검증, SQLite 인메모리 실제 INSERT/FLUSH 및 ROLLBACK 완벽 검증. 실데이터 건수 0건 유지.
- **테스트 B (`test_suite_b_time_travel_future_leakage_prevention`):**  
  10월 1일 등록(ACTIVE, 1500만) -> 10월 10일 계약(DELISTED, 1420만) 분리 스냅샷 생성. 10월 5일 과거 시점 조회 시 활성 매물로 정상 유지됨을 실증.
- **테스트 C (`test_suite_c_delegation_and_live_ad_permission_separation`):**  
  모의 승인 객체 주입 시 `SIMULATED_AUTHORIZED` 격리 및 `verified_real_data_count == 0` 확인. 위임 만료/철회/제3자 미동의 시 마케팅 제외 및 모든 매물 `is_live_ad_authorized == False` 확인.
- **테스트 D (`test_suite_d_csv_parser_rfc4180_edge_cases`):**  
  인용부호 내 `#` 보존, 중복 헤더 차단, 열 개수 불일치 차단, 개인정보 컬럼 차단 및 에러 메시지 내 민감값 원천 비노출 확인.

---

## 3. 문서화 및 제출 산출물

1. **비공개 파일럿 입력 실행 안내서 (`docs/PRIVATE_PILOT_INTAKE_GUIDE.md`):**
   - 오프라인 수령부터 격리 DB 적재까지 8단계 안전 인입 파이프라인 명세
   - 데이터 보관 및 파기(Retention & Deletion) 정책
2. **파트너 데이터 및 권한 증빙 검증 프로토콜 (`docs/PARTNER_VERIFICATION_PROTOCOL.md`):**
   - 성능점검표, 소유권, 서면 위임장 3대 증빙 심사 기준
   - 실데이터 승인 토큰 규약 및 광고 게시 허가 통제 규약
3. **실제 자료 제출용 비식별 CSV 양식 (`templates/PARTNER_REAL_DATA_SUBMISSION_FORM.csv`):**
   - 파트너 딜러에게 제공할 비식별 14대 표준 헤더 양식
4. **기존 데이터 엔진 ORM 스키마 매핑 매트릭스 (`docs/SCHEMA_MAPPING_MATRIX.md`):**
   - 5대 ORM 테이블 최신 매핑 규격

---

## 4. 코드 무결성 및 CI 검증 결과

- **Pytest:** 41개 전체 테스트 통과 (`41 passed in 0.56s`)
- **Ruff:** `All checks passed!`
- **Demo Script:** `main.py` 데모 시나리오 무결성 확인
- **Git & PR 상태:**
  - 신규 브랜치: `feat/directive-004b-pilot-preflight`
  - PR #4 생성 예정 (PR #3을 베이스로 종속성 유지)

---

## 5. Phase 2 진입 조건 및 최종 결론

본 DIRECTIVE 004-B Phase 1 작업을 통해 실매물을 안전하게 받아들일 수 있는 모든 시스템적 방벽이 완비되었습니다.  
그러나 실제 파트너 딜러와의 서면 계약 및 실매물 3건의 자료는 아직 확보되지 않았으므로, Phase 2(실데이터 입력)는 사장님의 공식 승인이 떨어질 때까지 **`BLOCKED: REAL_DATA_NOT_PROVIDED`** 상태를 엄격히 유지합니다.
