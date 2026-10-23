# DIRECTIVE 013-E: LIVE AUTHORIZATION, PARTIAL SUCCESS HALT & COMMIT PROVENANCE AUDIT (최종 완료 보고서)

## 1. 개요 및 GitHub 제출 상태
- **임무**: DIRECTIVE 013-E 지침에 따른 LIVE 실행 승인 체계 분리, PARTIAL_SUCCESS 루프 안전 중단 및 단독 복구 경로 마련, 배치 커밋 감사 계약(데이터 기원, 원천 파일 SHA-256, 수량 무결성) 강화.
- **선행 작업**: PR #11 공식 병합 완료 (`e342aa71750ab2c2b4d802aad3cdb9ddd51ccff2`)
- **작업 브랜치**: `feat/directive-013-scheduled-observation-system`
- **최신 커밋 HEAD SHA**: `5c7ae16643a890d9187dea750103545987bddea8`
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker` (현재 병합 전략과 100% 일치)
- **공식 PR URL**: https://github.com/WisdomMax/chafficial/pull/12
- **PR 비교 URL**: https://github.com/WisdomMax/chafficial/compare/feat/directive-009-price-event-tracker...feat/directive-013-scheduled-observation-system?expand=1

---

## 2. DIRECTIVE 013-E 핵심 아키텍처 및 안전 검증 구현 내역

### 2.1 [지침 1] LIVE 실행 승인 체계 분리 (개발 옵션 vs 운영 승인 정책)
- **문제점 원천 차단**: CLI 옵션(`--enable-live-scheduler`)이나 개발용 환경변수만으로 실수로 실제 엔카 모바일 웹에 LIVE 수집이 시작되는 위험을 원천 제거.
- **2단계 승인 아키텍처**:
  - `enable_live_execution: bool = False` (개발/플래그 레벨 의도)
  - `live_ops_approved: bool = False` (운영 감독의 공식 승인 플래그)
  - `live_ops_approval_token: str = ""` (총괄 감독이 발급한 승인 확인 문자열: `DIRECTIVE_013_LIVE_SUPERVISOR_AUTHORIZED`)
- **Fail-Closed 방어**:
  - `enable_live_execution=True`가 주어지더라도 `live_ops_approved=True` 및 유효한 승인 토큰이 일치하지 않으면 즉시 `LiveExecutionNotAuthorizedError`를 발생시켜 수집 전 단계에서 완전히 거부.
  - CLI(`scripts/scheduled_market_watcher.py`)에서도 `--approved-by-supervisor` 및 `--approval-token`이 필수 요구되며 누락 시 즉시 Fail-Closed 종료.
  - 단위 테스트 `test_live_execution_rejected_without_supervisor_approval` 및 `test_live_execution_rejected_with_invalid_token` 통과.

### 2.2 [지침 2] PARTIAL_SUCCESS 자동 루프 중단 및 단독 보고서 복구 경로
- **루프 안전 중단 (Fail-Safe Break)**:
  - 수집 및 DB 커밋은 성공했으나 일별 요약 보고서 생성/디스크 쓰기가 실패한 `PARTIAL_SUCCESS` 발생 시, 보고 체계가 정상화될 때까지 무인 루프를 지속하지 않고 `run_loop()` 즉시 안전 중단 (`break`).
  - 단위 테스트 `test_partial_success_breaks_run_loop`를 통해 1회 만에 루프 안전 종료 실증.
- **보고서 단독 복구 경로 (`recover_daily_report`)**:
  - 수집 결과는 DB에 100% 보존하며 수집 파이프라인은 절대 재호출하지 않음.
  - `scheduler.recover_daily_report(target_date_str=...)`를 통해 오직 보고서만 안전하게 재생성/복구.
  - 단위 테스트 `test_recover_daily_report_standalone`를 통해 수집 러너 호출 0회 및 보고서 단독 복구 입증.

### 2.3 [지침 3] 배치 커밋 감사 계약 강화 (Commit Provenance Audit)
- **단순 ID 존재 확인 탈피 -> 6단계 다중 무결성 검증**:
  - `check_batch_committed(batch_id)`는 단순 행 존재 여부만 보지 않고 `BatchAuditLog` 스키마와 원천 파일 무결성을 전수 검사:
    1. **중복 ID 검증**: 동일 `batch_id`가 복수 개 조회되면 DB 무결성 파괴로 판정하여 `CommitStatusUnknownError` 발생.
    2. **수집 수량 유효성**: `record_count is None` 또는 `record_count < 0`인 경우 즉시 Fail-Closed.
    3. **데이터 기원(Provenance) 검증**: `source_platform != "ENCAR"`인 경우 즉시 불일치 차단.
    4. **검색 범위 검증**: `search_scope`가 비어있거나 올바른 스코프가 아니면 차단.
    5. **원천 파일 물리 실존 및 SHA-256 검증**: `notes`에 기록된 `raw_file_path`의 실존 여부를 검사하고, 디스크 상의 실제 파일 SHA-256을 계산하여 `raw_file_sha256`과 1 byte도 틀림없이 일치하는지 대조. 변조/소실 시 즉시 `CommitStatusUnknownError` 차단.
    6. **적재 수량 일치 검증**: `first_seen_count + re_observed_count == record_count` 여부를 대조.
  - 기존 SQLite DB 스키마는 100% 하위 호환성을 유지하면서, 실패 주입 테스트 6종 전체 통과 입증.

---

## 3. 전체 테스트 스위트 결과 (187/187 통과, 100% PASS)

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.7.0
rootdir: /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI
configfile: pyproject.toml
testpaths: tests
collected 187 items

tests/test_directive_002_all.py ......................                   [ 11%]
tests/test_directive_002a_corrections.py ......                          [ 14%]
tests/test_directive_002b_corrections.py ....                            [ 17%]
tests/test_directive_002c_corrections.py ...                             [ 18%]
tests/test_directive_002c_final_review.py ..                             [ 19%]
tests/test_directive_006_opportunity_scorer.py .....                     [ 22%]
tests/test_directive_007_opportunity_scorer.py .........                 [ 27%]
tests/test_directive_008_valuation_analysis.py ...........               [ 33%]
tests/test_directive_008c_integrity.py ....                              [ 35%]
tests/test_directive_009_price_tracker.py ......                         [ 38%]
tests/test_directive_009a_advanced_tracking.py .........                 [ 43%]
tests/test_directive_009b_operational_integrity.py ......                [ 46%]
tests/test_directive_009c_batch_hardening.py ......                      [ 49%]
tests/test_directive_010_market_stream.py ......                         [ 52%]
tests/test_directive_010d_operational_db_preservation.py ....            [ 55%]
tests/test_directive_010f_operational_robustness.py ....                 [ 57%]
tests/test_directive_010g_provenance_and_integrity.py .....              [ 59%]
tests/test_directive_010h_isolation_and_robustness.py .........          [ 64%]
tests/test_directive_010i_audit_hardening.py ...                         [ 66%]
tests/test_directive_010j_report_consistency.py .                        [ 66%]
tests/test_directive_010k_report_preservation_and_dynamics.py ....       [ 68%]
tests/test_directive_011_recovery_and_operations.py .............        [ 75%]
tests/test_directive_012b_verification.py ....                           [ 78%]
tests/test_directive_013_scheduler.py ...............................    [ 94%]
tests/test_partner_intake.py ..........                                  [100%]

============================= 187 passed in 5.24s ==============================
```

- `test_directive_013_scheduler.py` 31개 테스트 전체 PASS:
  - 기존 20개 기본/안전 테스트 100% 통과
  - **신규 추가된 013-E 핵심 검증 테스트 11종 100% 통과**:
    1. `test_live_execution_rejected_without_supervisor_approval`: **운영자 승인 부재 시 Fail-Closed 거부 검증**
    2. `test_live_execution_rejected_with_invalid_token`: **승인 토큰 불일치/위조 시 Fail-Closed 거부 검증**
    3. `test_partial_success_breaks_run_loop`: **PARTIAL_SUCCESS 발생 시 스케줄러 루프 즉시 종료 검증**
    4. `test_recover_daily_report_standalone`: **수집 러너 호출 0회 및 보고서 단독 복구 검증**
    5. `test_check_batch_committed_fails_on_duplicate_batch_id`: **동일 batch_id 중복 시 Fail-Closed 검증**
    6. `test_check_batch_committed_fails_on_invalid_record_count`: **음수/무효 record_count 감지 시 Fail-Closed 검증**
    7. `test_check_batch_committed_fails_on_platform_mismatch`: **데이터 기원(플랫폼) 불일치 감지 시 Fail-Closed 검증**
    8. `test_check_batch_committed_fails_on_missing_raw_file`: **원천 파일 물리 소실 감지 시 Fail-Closed 검증**
    9. `test_check_batch_committed_fails_on_raw_file_sha_mismatch`: **원천 파일 SHA-256 변조 감지 시 Fail-Closed 검증**
    10. `test_check_batch_committed_fails_on_quantity_mismatch`: **세부 적재 수량 불일치 감지 시 Fail-Closed 검증**
    11. `test_check_batch_committed_success_with_valid_audit`: **완벽한 감사 메타데이터 충족 시 정상 COMMITTED 검증**

---

## 4. 운영 DB 무결성 및 레코드 영구 보존 검증
운영 DB(`data/chaficial_market_timeseries.db`)는 1 byte도 변경되지 않고 온전히 보존되었습니다:

| 테이블명 | 레코드 수 | 상태 |
| :--- | :---: | :---: |
| `listings` | 348대 | 불변 영구 보존 |
| `listing_snapshots` | 382건 | 불변 영구 보존 |
| `price_events` | 353건 | 불변 영구 보존 |
| `batch_audit_logs` | 3회 | 불변 영구 보존 |
| `PRAGMA integrity_check` | - | `ok` (100% 무결성 통과) |

- 기존 1, 2, 3차 관측 원본 파일(`data/raw_observations/*.json`) 일체 불변 보존 확인.
- 실제 LIVE 자동 수집은 비활성 상태(`enable_live_execution=False`, `live_ops_approved=False`)로 안전하게 보호 유지 중.

---

## 5. 결론 및 PR #12 최종 공식 병합 승인 요청
- **PR #12 공식 URL**: https://github.com/WisdomMax/chafficial/pull/12
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker`
- 총괄 감독(ChatGPT)님의 지침에 따라 LIVE 실행 승인 체계 분리, PARTIAL_SUCCESS 루프 안전 중단, 배치 커밋 감사 계약 강화를 완벽히 구현하고 테스트를 완료하였습니다.
- PR #12의 검토 및 최종 공식 병합 승인을 요청드립니다!
