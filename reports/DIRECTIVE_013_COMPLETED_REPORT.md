# DIRECTIVE 013-D: TIME-SERIES LIVE OBSERVATION SCHEDULER & COMMIT BOUNDARY SAFETY (최종 완료 보고서)

## 1. 개요 및 GitHub 제출 상태
- **임무**: DIRECTIVE 013-D 주기적 LIVE 관측 스케줄러 구축, 커밋 경계 안전성(Commit Boundary Safety), 실행 중복 방지(No Double Execution) 완비.
- **선행 작업**: PR #11 공식 병합 완료 (`e342aa71750ab2c2b4d802aad3cdb9ddd51ccff2`)
- **작업 브랜치**: `feat/directive-013-scheduled-observation-system`
- **최신 커밋 SHA**: `9d29483b02b73363e951d65ba68f1d4199927c07`
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker`
- **공식 PR 생성 URL**: https://github.com/WisdomMax/chafficial/pull/12
- **PR 비교 URL**: https://github.com/WisdomMax/chafficial/compare/feat/directive-009-price-event-tracker...feat/directive-013-scheduled-observation-system?expand=1

---

## 2. DIRECTIVE 013-D 핵심 아키텍처 및 안전 검증 구현 내역

### 2.1 [최우선 과제] 러너 내부 TypeError 발생 시 호환성 오인 재호출 방지 (정확히 1회 호출 보장)
- **발견된 잠재 결함**: `try: runner(batch_id=...) except TypeError: runner()` 패턴은 러너 내부 비즈니스 로직에서 발생한 TypeError까지 파라미터 불일치로 오판하여 러너를 2번 연속 실행(Double Execution)할 위험이 있음.
- **해결 및 안전 보장**:
  - `inspect.signature(runner)`를 통한 실행 전 정적 시그니처 검사 도입.
  - 실행 전에 `batch_id` 지원 여부를 판별하여 러너 내부 예외와 파라미터 바인딩 오류를 완벽 분리.
  - LIVE 모드 시 `batch_id`를 지원하지 않는 러너는 즉시 `SchedulerConfigError`로 실행 거부 (엄격한 인터페이스 계약 강제).
  - 단위 테스트 `test_runner_internal_type_error_called_exactly_once` 및 `test_live_runner_without_batch_id_rejected`를 통해 정확히 1회만 호출되고 즉시 `FAILED` 종결됨을 실증.

### 2.2 [커밋 경계 안전성] 대상 DB 부재 및 조회 에러 시 Fail-Closed (재시도 원천 차단)
- **문제점 원천 해결**: 대상 DB 파일이 아직 생성되지 않았거나 락 경합 시 빈 결과나 `NOT_COMMITTED`를 반환하면 이미 실행 중이거나 커밋된 배치를 오인하여 중복 수집할 위험이 존재.
- **Fail-Closed 구현**:
  - `check_batch_committed(batch_id)`는 대상 DB 파일이 부재하거나 조회 중 에러 발생 시 즉시 `CommitStatusUnknownError` 발생.
  - 스케줄러는 이를 포착하여 **재시도 횟수(max_retries)와 무관하게 즉시 수집을 영구 차단**하고 `COMMIT_STATUS_UNKNOWN` 상태로 안전 종결.
  - 단위 테스트 `test_db_file_missing_treated_as_commit_status_unknown` 통과.

### 2.3 [루프 안전 중단] 사후 오류 및 상태 불확실 시 스케줄러 루프 즉시 중단 (Fail-Safe Break)
- **루프 연속 실행 차단**:
  - `COMMITTED_WITH_POST_ERROR`, `COMMIT_STATUS_UNKNOWN`, `FAILED` 상태 발생 시, 다음 주기로 자동 진행하지 않고 `run_loop()` 즉시 안전 중단(`break`).
  - 단위 테스트 `test_loop_breaks_on_committed_with_post_error` 및 `test_loop_breaks_on_commit_status_unknown` 통과.

### 2.4 고유 배치 ID 사전 발급 및 1:1 귀속성 검증 (타 프로세스 오인 차단)
- 스케줄러가 파이프라인 호출 전 고유한 `current_batch_id`(`ENCAR_CN7_LIVE_YYYYMMDD_HHMMSS_xxxxxx`)를 사전 발급하여 러너에 명시적 전달.
- 예외 발생 시 오직 자신이 발급한 `current_batch_id`가 DB에 커밋되었는지만 1:1 단독 검사.

### 2.5 5대 상태 판정 체계
| 상황 | 결과 상태 (`collection_status`) | 재수집 허용 여부 | 비고 |
| :--- | :---: | :---: | :--- |
| **커밋 전 일시적 네트워크 장애** | `RETRYABLE_FAILURE` | **제한적 허용** | `max_retries` 이내 지수 백오프 대기 후 재시도 |
| **현재 batch_id 커밋 확인 후 사후 오류** | `COMMITTED_WITH_POST_ERROR` | **재수집 절대 금지** | DB 커밋 완료 보존, 루프 즉시 중단 |
| **커밋 여부 확인 불가 (DB 부재/조회 실패)** | `COMMIT_STATUS_UNKNOWN` | **재수집 절대 금지** | Fail-Closed 즉시 안전 종료, 루프 중단 |
| **영구적 오류 (디스크/권한/스키마/로직)** | `FAILED` | **재수집 절대 금지** | Fail-Fast 1회 만에 즉시 중단, 루프 중단 |
| **수집 성공, 보고서 실패** | `PARTIAL_SUCCESS` | **재수집 절대 금지** | 수집 성공 확정, 수집 재실행 안 함 |

---

## 3. 전체 테스트 스위트 결과 (176/176 통과, 100% PASS)

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.7.0
rootdir: /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI
configfile: pyproject.toml
testpaths: tests
collected 176 items

tests/test_directive_002_all.py ......................                   [ 12%]
tests/test_directive_002a_corrections.py ......                          [ 15%]
tests/test_directive_002b_corrections.py ....                            [ 18%]
tests/test_directive_002c_corrections.py ...                             [ 19%]
tests/test_directive_002c_final_review.py ..                             [ 21%]
tests/test_directive_006_opportunity_scorer.py .....                     [ 23%]
tests/test_directive_007_opportunity_scorer.py .........                 [ 28%]
tests/test_directive_008_valuation_analysis.py ...........               [ 35%]
tests/test_directive_008c_integrity.py ....                              [ 37%]
tests/test_directive_009_price_tracker.py ......                         [ 40%]
tests/test_directive_009a_advanced_tracking.py .........                 [ 46%]
tests/test_directive_009b_operational_integrity.py ......                [ 49%]
tests/test_directive_009c_batch_hardening.py ......                      [ 52%]
tests/test_directive_010_market_stream.py ......                         [ 56%]
tests/test_directive_010d_operational_db_preservation.py ....            [ 58%]
tests/test_directive_010f_operational_robustness.py ....                 [ 60%]
tests/test_directive_010g_provenance_and_integrity.py .....              [ 63%]
tests/test_directive_010h_isolation_and_robustness.py .........          [ 68%]
tests/test_directive_010i_audit_hardening.py ...                         [ 70%]
tests/test_directive_010j_report_consistency.py .                        [ 71%]
tests/test_directive_010k_report_preservation_and_dynamics.py ....       [ 73%]
tests/test_directive_011_recovery_and_operations.py .............        [ 80%]
tests/test_directive_012b_verification.py ....                           [ 82%]
tests/test_directive_013_scheduler.py ....................               [ 94%]
tests/test_partner_intake.py ..........                                  [100%]

============================= 176 passed in 4.99s ==============================
```

- `test_directive_013_scheduler.py` 20개 테스트 전체 PASS:
  1. `test_scheduler_safety_guard_standby_mode`: STANDBY 안전 모드 검증
  2. `test_scheduler_lock_contention_blocks_duplicate_instance`: 프로세스 락 경합 차단 검증
  3. `test_transient_network_error_recovers_via_backoff`: 네트워크 오류 지수 백오프 복구 검증
  4. `test_permanent_error_fails_fast_without_retries`: 영구 오류 즉시 Fail-Fast 검증
  5. `test_collection_success_with_report_failure_does_not_retry_live`: 보고서 실패 시 재실행 차단 검증
  6. `test_loop_breaks_on_fatal_failure`: 치명적 실패 시 루프 안전 종료 검증
  7. `test_config_validation_rules`: 설정값 유효성 검증
  8. `test_failure_report_unique_naming_no_overwrite`: 장애 보고서 덮어쓰기 방지 검증
  9. `test_kst_date_conversion_boundary`: KST 자정 경계값 변환 검증
  10. `test_daily_market_reporter_atomic_creation`: 일별 요약 보고서 원자적 생성 검증
  11. `test_is_transient_network_error_classification`: 네트워크 vs 영구 에러 엄격 분류 검증
  12. `test_commit_boundary_post_error_does_not_re_collect`: 커밋 완료 후 사후 예외 시 재수집 차단 검증
  13. `test_disk_and_permission_errors_fail_fast_without_retry`: 권한/디스크 오류 즉시 Fail-Fast 검증
  14. `test_check_batch_committed_fail_closed_on_db_query_error`: 커밋 조회 실패 시 Fail-Closed 재시도 0회 차단 검증
  15. `test_batch_ownership_ignores_other_process_batches`: 타 프로세스 배치 오인 차단(배치 귀속성) 검증
  16. `test_loop_breaks_on_commit_status_unknown`: 커밋 상태 불확실 시 스케줄러 루프 즉시 안전 중단 검증
  17. `test_runner_internal_type_error_called_exactly_once`: **[013-D] 러너 내부 TypeError 발생 시 오인 재호출 없이 1회만 호출 검증**
  18. `test_live_runner_without_batch_id_rejected`: **[013-D] LIVE 러너의 batch_id 인자 지원 필수 계약 검증**
  19. `test_db_file_missing_treated_as_commit_status_unknown`: **[013-D] DB 파일 부재 시 CommitStatusUnknownError Fail-Closed 검증**
  20. `test_loop_breaks_on_committed_with_post_error`: **[013-D] COMMITTED_WITH_POST_ERROR 발생 시 스케줄러 루프 즉시 중단 검증**

---

## 4. 운영 DB 무결성 및 레코드 영구 보존 검증
운영 DB(`data/chaficial_market_timeseries.db`)는 1 byte도 변경되지 않고 온전히 보존되었습니다:

| 테이블명 | 레코드 수 | 논리 SHA-256 해시 | 상태 |
| :--- | :---: | :--- | :---: |
| `listings` | 348대 | `e83a6fcf46e96a12c28aa32b675a48d71ad0212b079b70ff33423a7d8e23cf11` | 불변 보존 |
| `listing_snapshots` | 382건 | `988a14e32318ff2bf314ee92b17fffb6069cc5b767e0a035c9332e1bd07cdf33` | 불변 보존 |
| `price_events` | 353건 | `4ed4893f05c877e3c22455dbb8d71bd627af8ead9c8b301e132063f219dabc26` | 불변 보존 |
| `batch_audit_logs` | 3회 | `0188b48f94691c2289481cd904de191e47badc1e0514ddec630f0971f5ae0882` | 불변 보존 |
| `PRAGMA integrity_check` | - | `ok` | 100% 통과 |

---

## 5. 결론 및 총괄 감독 승인 요청
- **PR #12 공식 생성**: `feat/directive-013-scheduled-observation-system` -> `feat/directive-009-price-event-tracker`
- **구현 완전성**: 러너 실행 중복 원천 차단, Fail-Closed 커밋 확인 및 루프 안전 중단 완비.
- 총괄 감독(ChatGPT)께 PR #12 검토 및 최종 공식 승인을 요청드립니다.
