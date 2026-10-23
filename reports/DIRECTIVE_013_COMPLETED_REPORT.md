# DIRECTIVE 013-B: 커밋 경계 안전성 및 네트워크 전용 재시도 정책 완료 보고서

## 1. 개요 및 GitHub 제출 상태
- **임무**: DIRECTIVE 013-B 지침에 따른 커밋 경계 안전성(Commit Boundary Safety) 완비, 재시도 예외 범위 엄격화(Strict Network-Only Transient Errors), 운영 DB 논리 해시 무결성 검증.
- **선행 작업**: PR #11 공식 병합 완료 (`e342aa71750ab2c2b4d802aad3cdb9ddd51ccff2`)
- **작업 브랜치**: `feat/directive-013-scheduled-observation-system`
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker`
- **PR 생성 및 비교 URL**: https://github.com/WisdomMax/chafficial/compare/feat/directive-009-price-event-tracker...feat/directive-013-scheduled-observation-system?expand=1

---

## 2. DIRECTIVE 013-B 핵심 구현 내역

### 2.1 [지침 2] 커밋 경계 안전성 (Commit Boundary Safety)
- **문제점 원천 해결**: 러너가 DB 커밋에 성공한 직후 네트워크 단절이나 사후 로깅 중 예외가 발생하더라도, 스케줄러가 이를 미커밋 실패로 오인하여 동일 배치를 재수집하는 결함을 원천 차단.
- **구현 메커니즘**:
  - 파이프라인 호출 전 DB의 커밋된 `batch_id` 목록을 사전 조회(`_get_committed_batch_ids()`).
  - 예외 발생 시 사후 `batch_id` 목록과 대조하여 신규 배치가 이미 DB에 커밋되었는지 즉시 검사.
  - 신규 배치가 이미 커밋된 상태라면 파이프라인 재실행을 차단하고 `COMMITTED_WITH_POST_ERROR`로 안전 격리.
- **검증 완료**: 단위 테스트 `test_commit_boundary_post_error_does_not_re_collect`를 통해 커밋 후 예외 주입 시에도 파이프라인이 정확히 1회만 호출되고 재수집되지 않음을 입증.

### 2.2 [지침 3] 엄격한 네트워크 전용 재시도 예외 분류 (`is_transient_network_error`)
- **문제점 원천 해결**: `OSError` 전체를 재시도하던 광범위한 예외 처리를 전면 개정하여, 디스크 풀이나 파일 권한 에러까지 무의미하게 재시도하는 위험을 차단.
- **선별적 네트워크 예외만 허용**:
  - `ConnectionError`, `TimeoutError`, `http.client.RemoteDisconnected`, 네트워크 소켓 errno (`ECONNRESET`, `ETIMEDOUT`, `ENETUNREACH`, `EHOSTUNREACH`, `ENETDOWN`).
- **영구적 예외 즉시 중단 (Fail-Fast)**:
  - `PermissionError`, `FileNotFoundError`, `IsADirectoryError`, `sqlite3.Error`, `ValueError` 등은 재시도 없이 1회 만에 즉시 중단.
- **검증 완료**: `test_is_transient_network_error_classification`, `test_disk_and_permission_errors_fail_fast_without_retry` 통과.

### 2.3 [지침 4] 수집 성공과 보고서 실패의 독립 분리 및 장애 감사
- 수집 성공 후 일별 요약 보고서 생성이 실패하더라도 LIVE 수집을 절대 재시도하지 않음 (`test_collection_success_with_report_failure_does_not_retry_live`).
- 장애 보고서는 마이크로초와 UUID 난수 접미사를 결합하여 배타적(`x` 모드)으로 생성하여 동일 시점 덮어쓰기 원천 차단.

---

## 3. 전체 테스트 스위트 결과 (169/169 통과, 100% PASS)

```text
tests/test_directive_002_all.py ......................                   [ 13%]
tests/test_directive_002a_corrections.py ......                          [ 16%]
tests/test_directive_002b_corrections.py ....                            [ 18%]
tests/test_directive_002c_corrections.py ...                             [ 20%]
tests/test_directive_002c_final_review.py ..                             [ 21%]
tests/test_directive_006_opportunity_scorer.py .....                     [ 24%]
tests/test_directive_007_opportunity_scorer.py .........                 [ 30%]
tests/test_directive_008_valuation_analysis.py ...........               [ 36%]
tests/test_directive_008c_integrity.py ....                              [ 39%]
tests/test_directive_009_price_tracker.py ......                         [ 42%]
tests/test_directive_009a_advanced_tracking.py .........                 [ 47%]
tests/test_directive_009b_operational_integrity.py ......                [ 51%]
tests/test_directive_009c_batch_hardening.py ......                      [ 55%]
tests/test_directive_010_market_stream.py ......                         [ 58%]
tests/test_directive_010d_operational_db_preservation.py ....            [ 60%]
tests/test_directive_010f_operational_robustness.py ....                 [ 63%]
tests/test_directive_010g_provenance_and_integrity.py .....              [ 66%]
tests/test_directive_010h_isolation_and_robustness.py .........          [ 71%]
tests/test_directive_010i_audit_hardening.py ...                         [ 73%]
tests/test_directive_010j_report_consistency.py .                        [ 73%]
tests/test_directive_010k_report_preservation_and_dynamics.py ....       [ 76%]
tests/test_directive_011_recovery_and_operations.py .............        [ 84%]
tests/test_directive_012b_verification.py ....                           [ 86%]
tests/test_directive_013_scheduler.py .............                      [ 94%]
tests/test_partner_intake.py ..........                                  [100%]
============================= 169 passed in 5.18s ==============================
```
- `test_directive_013_scheduler.py` 13개 전체 항목 100% PASS:
  1. `test_scheduler_safety_guard_standby_mode`: STANDBY 모드 동작 검증
  2. `test_scheduler_lock_contention_blocks_duplicate_instance`: 프로세스 락 경합 차단 검증
  3. `test_transient_network_error_recovers_via_backoff`: 네트워크 오류 지수 백오프 복구 검증
  4. `test_permanent_error_fails_fast_without_retries`: 영구 오류 즉시 중단 검증
  5. `test_collection_success_with_report_failure_does_not_retry_live`: 수집 성공 후 보고서 실패 시 재실행 차단 검증
  6. `test_loop_breaks_on_fatal_failure`: 치명적 실패 시 루프 안전 종료 검증
  7. `test_config_validation_rules`: 인터벌/모드 설정값 검증
  8. `test_failure_report_unique_naming_no_overwrite`: 장애 보고서 덮어쓰기 방지 검증
  9. `test_kst_date_conversion_boundary`: KST 자정 경계값 변환 검증
  10. `test_daily_market_reporter_atomic_creation`: 일별 요약 보고서 원자적 생성 검증
  11. `test_is_transient_network_error_classification`: 네트워크 vs 영구 에러 분류 검증
  12. `test_commit_boundary_post_error_does_not_re_collect`: **커밋 경계 사후 예외 시 재수집 차단 검증**
  13. `test_disk_and_permission_errors_fail_fast_without_retry`: **권한/디스크 오류 즉시 Fail-Fast 검증**

---

## 4. 운영 DB 무결성 및 논리 SHA-256 해시 검증
운영 DB(`data/chaficial_market_timeseries.db`)의 기존 348대 실매물, 382건 스냅샷, 353건 이벤트, 3개 배치 로그는 1 byte도 변경되지 않고 온전히 보존되었습니다:

| 테이블명 | 레코드 수 | 논리 SHA-256 해시 | 상태 |
| :--- | :---: | :--- | :---: |
| `listings` | 348대 | `e83a6fcf46e96a12c28aa32b675a48d71ad0212b079b70ff33423a7d8e23cf11` | 불변 보존 |
| `listing_snapshots` | 382건 | `988a14e32318ff2bf314ee92b17fffb6069cc5b767e0a035c9332e1bd07cdf33` | 불변 보존 |
| `price_events` | 353건 | `4ed4893f05c877e3c22455dbb8d71bd627af8ead9c8b301e132063f219dabc26` | 불변 보존 |
| `batch_audit_logs` | 3회 | `0188b48f94691c2289481cd904de191e47badc1e0514ddec630f0971f5ae0882` | 불변 보존 |
| `PRAGMA integrity_check` | - | `ok` | 100% 통과 |

---

## 5. 결론 및 최종 승인 요청
1. **커밋 경계 안전성(Commit Boundary Safety) 및 네트워크 전용 재시도 정책이 완벽히 구축**되었습니다.
2. 현재 안전 가드(`enable_live_execution=False`)가 유지되어 실제 LIVE 수집은 안전하게 비활성화되어 있습니다.
3. 원격 브랜치 `feat/directive-013-scheduled-observation-system`을 최신 커밋으로 푸시하였으며, 총괄 감독(ChatGPT)님의 최종 승인 및 병합 허가를 요청합니다!
