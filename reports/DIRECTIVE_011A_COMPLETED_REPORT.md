# CHA-FICIAL AI PROJECT
## DIRECTIVE 011-A 완료 보고서: 감사 보고서 복구 정확성 보완 및 운영 회귀 테스트 완비

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**저장소:** `https://github.com/WisdomMax/chafficial`  
**대상 브랜치:** `feat/directive-011-timeseries-operation`  
**기준 일시:** 2026-10-21 12:55:00 KST  
**PR #11 URL:** `https://github.com/WisdomMax/chafficial/pull/11`

---

## 0. 총괄 감독 감사 지적사항 및 해결 조치 요약

| 총괄 감독 지적 사항 | 식별된 결함 및 위험 | DIRECTIVE 011-A 조치 결과 | 무결성 상태 |
| :--- | :--- | :--- | :---: |
| **1. 수집 시각 복구** | `processed_at`을 웹 수집 시작·종료에 모두 사용하여 실제 수집 시각으로 허위 표기될 위험 | 영속 저장되지 않은 웹 수집 시각은 `NOT_RECORDED (DB 적재 시각 {processed_at}만 보존됨)`으로 정직하게 표기, 신규 배치는 메타데이터에서 실제 시각 복원 | **해결 완료** |
| **2. 가격 변동 금액** | `total_price_drop_krw=0` 하드코딩으로 가격 인하가 발생해도 0원으로 표시될 결함 | 하드코딩 0원 영구 제거. 실제 `PriceEvent`로부터 `sum(abs(price_delta_krw))` 정확 재계산 | **해결 완료** |
| **3. 원본 JSON 매칭 및 검증** | 배치 ID 파일명 추측 및 신규 계산 해시를 기존 해시와 대조하지 않아 변조 탐지 불가 | 신규 배치부터 경로와 SHA-256을 메타데이터에 영속 저장하여 역조회 대조 (누락/변조/교체 차단). 레거시 배치는 `LEGACY_UNVERIFIED`로 정직하게 표기 | **해결 완료** |
| **4. 과거 DB 상태 분리** | 복구 시점의 현재 전체 DB 건수·해시를 과거 배치 상태로 오인할 위험 | `과거 배치 당시 관측 통계` vs `복구 실행 시점 누적 DB 상태 (AS_OF_RECONSTRUCTION)` 섹션으로 물리적 분리 표기. 당시 해시 미기록 시 현재 해시로 대체하지 않음 | **해결 완료** |
| **5. 운영 DB 고정값 테스트** | `assert listing_count == 238` 고정으로 3차 LIVE 이후 정상 데이터 증가 시 테스트 실패 위험 | 고정값(`== 238`) 단언을 하한(`>= 238`) 및 기존 PK 부분집합(`issubset`) 불변성 검증으로 전환. 복구 테스트는 독립 임시 DB로 완전 격리 | **해결 완료** |
| **6. 덮어쓰기 보호** | 기존 보고서가 있을 때 무단 덮어쓰기 위험 | `overwrite=False` 시 `FileExistsError` 차단, 명시적 `overwrite=True`만 허용 | **해결 완료** |

---

## 1. 비파괴 감사 메타데이터 아키텍처 및 DB 보존 계획

1. **테이블 스키마 보존 원칙**:
   - 기존 운영 DB(`data/chaficial_market_timeseries.db`)의 5개 테이블 물리 스키마와 7개 영속 컬럼 구조를 100% 보존합니다.
   - 신규 감사 메타데이터는 `BatchAuditLog.notes` 필드 내에 구조화된 JSON 형태로 안전하게 영속화합니다.
2. **레거시 배치와 신규 배치의 완전한 자동 판정**:
   - `BatchAuditLog.get_audit_metadata()`: 일반 텍스트이거나 비어있는 경우 `None`을 반환하여 `LEGACY_UNVERIFIED`로 자동 판정.
   - 신규 배치: 원본 파일 경로, 실제 SHA-256, 웹 수집 시작/종료 시각, 커밋 당시 논리 해시, 실제 가격 인하액 등을 완벽히 역조회 검증.

---

## 2. 필수 실패 및 복구 시나리오 8종 독립 검증 결과 (`tests/test_directive_011_recovery_and_operations.py`)

```bash
$ uv run pytest tests/test_directive_011_recovery_and_operations.py -v
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.7.0
rootdir: /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI
configfile: pyproject.toml
collecting ... collected 9 items

tests/test_directive_011_recovery_and_operations.py::test_failure_scenario_1_missing_raw_json_raises_error PASSED [ 11%]
tests/test_directive_011_recovery_and_operations.py::test_failure_scenario_2_tampered_raw_json_raises_error PASSED [ 22%]
tests/test_directive_011_recovery_and_operations.py::test_failure_scenario_3_wrong_batch_json_replacement_fails PASSED [ 33%]
tests/test_directive_011_recovery_and_operations.py::test_failure_scenario_4_non_existent_batch_raises_error PASSED [ 44%]
tests/test_directive_011_recovery_and_operations.py::test_failure_scenario_5_existing_report_overwrite_rejection PASSED [ 55%]
tests/test_directive_011_recovery_and_operations.py::test_failure_scenario_6_price_drop_batch_reconstruction_accurate PASSED [ 66%]
tests/test_directive_011_recovery_and_operations.py::test_failure_scenario_7_past_batch_reconstruction_after_new_live_added PASSED [ 77%]
tests/test_directive_011_recovery_and_operations.py::test_operational_db_preservation_and_non_hardcoded_invariants PASSED [ 88%]
tests/test_directive_011_recovery_and_operations.py::test_legacy_batch_reconstruction_marks_unverified_honestly PASSED [100%]

============================== 9 passed in 0.27s ===============================
```

---

## 3. 전체 테스트 스위트 148개 100% 통과 원시 로그

```bash
$ uv run pytest
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.7.0
rootdir: /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI
configfile: pyproject.toml
testpaths: tests
collecting ... collected 148 items

tests/test_directive_002_all.py ......................                   [ 14%]
tests/test_directive_002a_corrections.py ......                          [ 18%]
tests/test_directive_002b_corrections.py ....                            [ 21%]
tests/test_directive_002c_corrections.py ...                             [ 23%]
tests/test_directive_002c_final_review.py ..                             [ 25%]
tests/test_directive_006_opportunity_scorer.py .....                     [ 28%]
tests/test_directive_007_opportunity_scorer.py .........                 [ 34%]
tests/test_directive_008_valuation_analysis.py ...........               [ 41%]
tests/test_directive_008c_integrity.py ....                              [ 44%]
tests/test_directive_009_price_tracker.py ......                         [ 48%]
tests/test_directive_009a_advanced_tracking.py .........                 [ 54%]
tests/test_directive_009b_operational_integrity.py ......                [ 58%]
tests/test_directive_009c_batch_hardening.py ......                      [ 62%]
tests/test_directive_010_market_stream.py ......                         [ 66%]
tests/test_directive_010d_operational_db_preservation.py ....            [ 69%]
tests/test_directive_010f_operational_robustness.py ....                 [ 72%]
tests/test_directive_010g_provenance_and_integrity.py .....              [ 75%]
tests/test_directive_010h_isolation_and_robustness.py .........          [ 81%]
tests/test_directive_010i_audit_hardening.py ...                         [ 83%]
tests/test_directive_010j_report_consistency.py .                        [ 84%]
tests/test_directive_010k_report_preservation_and_dynamics.py ....       [ 87%]
tests/test_directive_011_recovery_and_operations.py .........            [ 93%]
tests/test_partner_intake.py ..........                                  [100%]

============================= 148 passed in 3.23s ==============================
```

---

## 4. 운영 DB (`data/chaficial_market_timeseries.db`) 5개 테이블 논리 해시 불변 검증

| 대상 테이블 명 | 관리 레코드 수 | 논리 데이터 전체 행 SHA-256 해시 | 무결성 확인 |
| :--- | :---: | :---: | :---: |
| `listings` | **238행** | `5183ee9e4666a12c3b721ef9499dd5330fb72014e6bdbd03fc6b952611413d0a` | **100% 영구 불변 보존 확인** |
| `listing_snapshots` | **246행** | `8bf7b94983d7c7d07f7c1b9817cf2a2e28e4150776f4f4996a24f4268dae2bca` | **100% 영구 불변 보존 확인** |
| `price_events` | **238행** | `6ddbabb6f41c33f20b23f480899789f11db185283a0639e2413f741f3dad7707` | **100% 영구 불변 보존 확인** |
| `vehicle_identity_links` | **0행** | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **결정론적 빈 테이블 해시** |
| `batch_audit_logs` | **2행** | `3a79b24e0b522e4b247273875ba428e6267ce2a4fe83f638d4a58a07bcf67831` | **2개 실측 배치 영속 보존 확인** |

---

## 5. 결론 및 3차 LIVE 관측 준비 완료

- **복구 정확성 보완 완료**: 미기록 정보(`NOT_RECORDED`) 투명 공시, 원본 JSON 해시 변조 검증, `PRICE_DROP` 금액 실제 재계산, 과거 vs 현재 DB 상태 분리 표기 완비.
- **운영 회귀 테스트 정상화**: 고정값 의존성을 완전히 탈피하여, 향후 3차 LIVE 수집 및 실전 운영에서 데이터가 지속 누적되어도 전체 148개 테스트가 영구적으로 정상 통과하도록 체계 구축.
- **제출 준비 완료**: 브랜치 커밋 및 푸시 후 PR #11에 반영 완료.

다음 지시에 따라 3차 LIVE 관측 또는 추가 운영 검증을 진행할 준비가 완료되었습니다.
