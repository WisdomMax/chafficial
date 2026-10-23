# DIRECTIVE 013-C: COMMIT UNCERTAINTY & BATCH OWNERSHIP FINAL AUDIT (최종 완료 보고서)

## 1. 개요 및 GitHub 제출 상태
- **임무**: DIRECTIVE 013-C 지침에 따른 커밋 불확실성 원천 차단(Fail-Closed) 및 고유 배치 귀속성(Batch Ownership) 1:1 검증 완비.
- **선행 작업**: PR #11 공식 병합 완료 (`e342aa71750ab2c2b4d802aad3cdb9ddd51ccff2`)
- **작업 브랜치**: `feat/directive-013-scheduled-observation-system`
- **최신 커밋 SHA**: `232deb8034dbb93475149303530e3bb44464fc9a`
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker`
- **PR 생성 및 비교 URL**: https://github.com/WisdomMax/chafficial/compare/feat/directive-009-price-event-tracker...feat/directive-013-scheduled-observation-system?expand=1

---

## 2. DIRECTIVE 013-C 핵심 아키텍처 및 안전 검증 구현 내역

### 2.1 [지침 1] 커밋 조회 실패 시 Fail-Closed (재시도 원천 금지)
- **문제점 원천 해결**: DB 조회 에러나 잠금 발생 시 빈 집합(`set()`)을 반환하여 커밋 여부를 모르는 채 무작정 재시도하던 위험을 원천 제거.
- **Fail-Closed 구현**:
  - `check_batch_committed(batch_id)`가 DB 조회 예외 시 `CommitStatusUnknownError`를 즉시 발생.
  - 스케줄러는 이를 포착하여 **재시도 횟수(max_retries)와 무관하게 즉시 수집을 영구 차단**하고 `COMMIT_STATUS_UNKNOWN` 상태로 안전 종결.
  - 단위 테스트 `test_check_batch_committed_fail_closed_on_db_query_error`를 통해 재시도 호출 0회 및 Fail-Closed 즉시 차단 입증 완료.

### 2.2 [지침 2] 고유 배치 ID 사전 발급 및 1:1 귀속성 검증 (타 프로세스 오인 차단)
- **문제점 원천 해결**: 전체 신규 배치 수만 비교할 경우 다른 프로세스가 생성한 배치를 내 배치의 성공으로 착각하는 결함을 원천 제거.
- **배치 귀속성 구현**:
  - 스케줄러가 파이프라인 호출 전 고유한 `current_batch_id`(`ENCAR_CN7_LIVE_YYYYMMDD_HHMMSS_xxxxxx`)를 사전 생성하여 러너에 명시적 전달.
  - 예외 발생 시 오직 자신이 발급한 `current_batch_id`가 DB에 커밋되었는지만 1:1 단독 검사.
  - 단위 테스트 `test_batch_ownership_ignores_other_process_batches`를 통해 타 프로세스가 별도 배치를 커밋했더라도 내 배치가 미커밋이면 절대 성공으로 오인하지 않고 `FAILED` 처리됨을 입증 완료.

### 2.3 [지침 3] 5대 상태 판정 체계 확립
| 상황 | 결과 상태 (`collection_status`) | 재수집 허용 여부 | 비고 |
| :--- | :---: | :---: | :--- |
| **커밋 전 일시적 네트워크 장애** | `RETRYABLE_FAILURE` | **제한적 허용** | `max_retries` 이내 지수 백오프 대기 후 재시도 |
| **현재 batch_id 커밋 확인 후 사후 오류** | `COMMITTED_WITH_POST_ERROR` | **재수집 절대 금지** | DB 커밋 완료 보존, 수동 감사 상태로 기록 |
| **커밋 여부 확인 불가 (DB 조회 실패)** | `COMMIT_STATUS_UNKNOWN` | **재수집 절대 금지** | Fail-Closed 즉시 안전 종료 |
| **영구적 오류 (디스크/권한/스키마)** | `FAILED` | **재수집 절대 금지** | Fail-Fast 1회 만에 즉시 중단 |
| **수집 성공, 보고서 실패** | `PARTIAL_SUCCESS` | **재수집 절대 금지** | 수집 성공 확정, 수집 재실행 안 함 |

---

## 3. 전체 테스트 스위트 결과 (172/172 통과, 100% PASS)

```text
tests/test_directive_002_all.py ......................                   [ 12%]
tests/test_directive_002a_corrections.py ......                          [ 16%]
tests/test_directive_002b_corrections.py ....                            [ 18%]
tests/test_directive_002c_corrections.py ...                             [ 20%]
tests/test_directive_002c_final_review.py ..                             [ 21%]
tests/test_directive_006_opportunity_scorer.py .....                     [ 24%]
tests/test_directive_007_opportunity_scorer.py .........                 [ 29%]
tests/test_directive_008_valuation_analysis.py ...........               [ 36%]
tests/test_directive_008c_integrity.py ....                              [ 38%]
tests/test_directive_009_price_tracker.py ......                         [ 41%]
tests/test_directive_009a_advanced_tracking.py .........                 [ 47%]
tests/test_directive_009b_operational_integrity.py ......                [ 50%]
tests/test_directive_009c_batch_hardening.py ......                      [ 54%]
tests/test_directive_010_market_stream.py ......                         [ 57%]
tests/test_directive_010d_operational_db_preservation.py ....            [ 59%]
tests/test_directive_010f_operational_robustness.py ....                 [ 62%]
tests/test_directive_010g_provenance_and_integrity.py .....              [ 65%]
tests/test_directive_010h_isolation_and_robustness.py .........          [ 70%]
tests/test_directive_010i_audit_hardening.py ...                         [ 72%]
tests/test_directive_010j_report_consistency.py .                        [ 72%]
tests/test_directive_010k_report_preservation_and_dynamics.py ....       [ 75%]
tests/test_directive_011_recovery_and_operations.py .............        [ 82%]
tests/test_directive_012b_verification.py ....                           [ 84%]
tests/test_directive_013_scheduler.py ................                   [ 94%]
tests/test_partner_intake.py ..........                                  [100%]
============================= 172 passed in 4.84s ==============================
```
- `test_directive_013_scheduler.py` 16개 전체 신규 테스트 항목 100% PASS:
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
  12. `test_commit_boundary_post_error_does_not_re_collect`: **커밋 완료 후 사후 예외 시 재수집 차단 검증**
  13. `test_disk_and_permission_errors_fail_fast_without_retry`: **권한/디스크 오류 즉시 Fail-Fast 검증**
  14. `test_check_batch_committed_fail_closed_on_db_query_error`: **커밋 조회 실패 시 Fail-Closed 재시도 0회 차단 검증**
  15. `test_batch_ownership_ignores_other_process_batches`: **타 프로세스 배치 오인 차단(배치 귀속성) 검증**
  16. `test_loop_breaks_on_commit_status_unknown`: **커밋 상태 불확실 시 스케줄러 루프 즉시 안전 중단 검증**

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

## 5. 결론 및 최종 운영 승인 요청
1. **커밋 불확실성 원천 차단(Fail-Closed) 및 고유 배치 귀속성(Batch Ownership) 1:1 검증이 완비**되었습니다.
2. 장애 발생 시 **"다시 시도하면 안 되는 상황을 100% 판별하여 멈추는 원칙"**이 시스템 레벨에서 영구적으로 보장되었습니다.
3. 현재 안전 가드(`enable_live_execution=False`)가 유지되어 무단 LIVE 수집은 원천 차단된 상태입니다.
4. 총괄 감독(ChatGPT)님의 최종 공식 검토 및 PR 병합 승인을 정중히 요청합니다!
