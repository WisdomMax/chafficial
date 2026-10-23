# DIRECTIVE 013-G: AUTHORITY BOUNDARY & LEGACY AUDIT HARDENING (최종 완료 보고서)

## 1. 개요 및 GitHub 제출 상태
- **임무**: DIRECTIVE 013-G 지침에 따른 운영자 로컬 승인 경계 확립(심볼릭 링크 거부, 7일 이내 만료, boolean true 강제, ChatGPT 승인 오인 표현 완전 배제) 및 신규 배치의 레거시 감사 우회 차단(Strict Commit Audit 강제).
- **선행 작업**: PR #11 공식 병합 완료 (`e342aa71750ab2c2b4d802aad3cdb9ddd51ccff2`)
- **작업 브랜치**: `feat/directive-013-scheduled-observation-system`
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker` (100% 일치)
- **공식 PR URL**: https://github.com/WisdomMax/chafficial/pull/12
- **PR 비교 URL**: https://github.com/WisdomMax/chafficial/compare/feat/directive-009-price-event-tracker...feat/directive-013-scheduled-observation-system?expand=1

---

## 2. DIRECTIVE 013-G 핵심 안전 게이트 구현 내역

### 2.1 [지침 1] 운영자 로컬 활성화 승인 체계 정의 및 안전 검증 강화
- **권한 경계 명확화 (ChatGPT 승인 표현 완전 배제)**:
  - 승인 파일은 총괄 감독이나 제3자의 서명이 아닌, **"운영자 로컬 활성화 안전 장치(Operator Local Activation Safeguard)"**로 명확히 정의되었습니다.
  - 코드 주석, 테스트 헬퍼, 보고서에서 "ChatGPT가 승인했다"는 표현을 전면 삭제하고 `LOCAL_OPERATOR_TEST`로 교체하였습니다.
  - **승인 파일의 존재는 결코 사용자나 감독의 실시간 승인 행위를 대신하지 않으며**, 운영 환경에서 의도치 않은 LIVE 실행을 차단하기 위한 2중 안전 장치입니다.
- **운영자 로컬 승인 파일 활성화 절차 (문서화)**:
  1. 파일 경로: `data/.live_authorization.json` (Git 비추적 파일로 `.gitignore`에 등록됨)
  2. 파일 형식:
     ```json
     {
       "is_approved": true,
       "approved_by": "운영자_식별자",
       "expires_at": "YYYY-MM-DDTHH:MM:SS+00:00"
     }
     ```
  3. 요구 조건:
     - 심볼릭 링크 절대 불가 (`auth_file.is_symlink()` 즉시 거부).
     - `is_approved`는 정확히 JSON boolean `true`여야 함 (문자열이나 정수 1 거부).
     - `expires_at`은 시간대(Timezone, UTC)가 명시된 유효한 ISO 8601 포맷이어야 함.
     - **과도하게 긴 승인 기간 차단**: 현재 시각 기준 유효기간이 7일을 초과할 경우 즉시 거부 (`MAX_AUTH_VALIDITY_DAYS = 7.0`).
- **현재 상태**: 승인 파일은 생성되지 않은 상태(`None`)이며, 실제 LIVE 자동 수집은 안전하게 비활성화되어 있습니다.

### 2.2 [지침 2] 신규 배치의 레거시 감사 우회 차단 (No Bypass for New Batches)
- **문제점 원천 해결**: 호출자가 `is_legacy=True` 인자를 전달하더라도 신규 배치가 엄격한 감사 검사를 건너뛰는 취약점을 원천 차단.
- **구현 메커니즘**:
  - `check_batch_committed()` 내부에서:
    ```python
    if is_legacy is True and batch_id not in LEGACY_BATCH_IDS:
        raise CommitStatusUnknownError(
            f"보안 위반: 신규 배치({batch_id})는 레거시 검증(is_legacy=True)으로 우회할 수 없습니다 (013-G)."
        )
    ```
  - 오직 사전에 지정된 1~3차 실제 배치 3개(`LEGACY_BATCH_IDS`)만 레거시 호환 검증 경로를 탈 수 있으며, 그 외 모든 배치는 예외 없이 **Strict Commit Audit**이 강제됩니다.
  - 단위 테스트 `test_check_batch_committed_new_batch_cannot_bypass_via_is_legacy_flag`를 통해 우회 시도 즉시 차단 입증.

### 2.3 [지침 3] 감사 메타데이터 엄격한 타입 및 64자리 SHA-256 검증
- **수집 수량 타입 검증**:
  - `first_seen_count`, `re_observed_count`: `isinstance(v, int) and not isinstance(v, bool) and v >= 0` (boolean 값 주입 차단).
  - 단위 테스트 `test_check_batch_committed_fails_on_boolean_counts` 통과.
- **해시 형식 검증**:
  - `raw_file_sha256`: `re.fullmatch(r"[0-9a-fA-F]{64}", sha)` 정규표현식으로 정확히 64자리 16진수 검증.
- **수량 일치**:
  - `first_seen_count + re_observed_count == record_count` 완벽 일치 검증.

---

## 3. 전체 테스트 스위트 결과 (196/196 통과, 100% PASS)

```text
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.7.0
rootdir: /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI
configfile: pyproject.toml
testpaths: tests
collected 196 items

tests/test_directive_002_all.py ......................                   [ 11%]
tests/test_directive_002a_corrections.py ......                          [ 14%]
tests/test_directive_002b_corrections.py ....                            [ 16%]
tests/test_directive_002c_corrections.py ...                             [ 17%]
tests/test_directive_002c_final_review.py ..                             [ 18%]
tests/test_directive_006_opportunity_scorer.py .....                     [ 21%]
tests/test_directive_007_opportunity_scorer.py .........                 [ 26%]
tests/test_directive_008_valuation_analysis.py ...........               [ 31%]
tests/test_directive_008c_integrity.py ....                              [ 33%]
tests/test_directive_009_price_tracker.py ......                         [ 36%]
tests/test_directive_009a_advanced_tracking.py .........                 [ 41%]
tests/test_directive_009b_operational_integrity.py ......                [ 44%]
tests/test_directive_009c_batch_hardening.py ......                      [ 47%]
tests/test_directive_010_market_stream.py ......                         [ 50%]
tests/test_directive_010d_operational_db_preservation.py ....            [ 52%]
tests/test_directive_010f_operational_robustness.py ....                 [ 54%]
tests/test_directive_010g_provenance_and_integrity.py .....              [ 57%]
tests/test_directive_010h_isolation_and_robustness.py .........          [ 61%]
tests/test_directive_010i_audit_hardening.py ...                         [ 63%]
tests/test_directive_010j_report_consistency.py .                        [ 63%]
tests/test_directive_010k_report_preservation_and_dynamics.py ....       [ 65%]
tests/test_directive_011_recovery_and_operations.py .............        [ 72%]
tests/test_directive_012b_verification.py ....                           [ 74%]
tests/test_directive_013_scheduler.py .................................. [ 91%]
......                                                                   [ 94%]
tests/test_partner_intake.py ..........                                  [100%]

============================= 196 passed in 6.03s ==============================
```

- `test_directive_013_scheduler.py` 40개 테스트 전체 PASS:
  - **013-G 신규 안전 검증 테스트 4종 포함 100% 통과**:
    1. `test_check_batch_committed_new_batch_cannot_bypass_via_is_legacy_flag`: **신규 배치의 레거시 우회 차단 검증**
    2. `test_verify_live_authorization_rejects_symlink`: **심볼릭 링크 승인 파일 거부 검증**
    3. `test_verify_live_authorization_rejects_excessive_duration`: **7일 초과 과도한 승인 기간 거부 검증**
    4. `test_check_batch_committed_fails_on_boolean_counts`: **수량에 boolean 주입 시 정수형 엄격 검증 거부**

---

## 4. 최종 변경 파일 목록 및 데이터 보호 확인
- **최종 변경 파일 (PR #12)**:
  1. `.gitignore`: 로컬 승인 파일(`.live_authorization.json` 등) Git 추적 원천 배제
  2. `src/chaficial/tracker/scheduler.py`: 로컬 승인 무결성(심볼릭 링크/7일/boolean 검증), 신규 배치 레거시 우회 차단, 메타데이터 타입/SHA 포맷 검증
  3. `scripts/scheduled_market_watcher.py`: CLI 승인 토큰 플래그 제거 및 `--auth-file` 경로 지원
  4. `tests/test_directive_013_scheduler.py`: 013-G 신규 안전 테스트 4종 추가 (총 40개 테스트)
  5. `reports/DIRECTIVE_013_COMPLETED_REPORT.md`: 013-G 최종 완료 보고서
- **운영 DB 및 원본 파일 보호**:
  - `listings`: 348대 (100% 불변 보존)
  - `listing_snapshots`: 382건 (100% 불변 보존)
  - `price_events`: 353건 (100% 불변 보존)
  - `batch_audit_logs`: 3회 (100% 불변 보존)
  - `PRAGMA integrity_check`: `ok` (100% 무결성 통과)
  - 원본 JSON 관측 파일 3건 일체 불변 보존 확인 완료 (`scripts/verify_directive_012b.py` 100% PASS).
  - 실제 LIVE 자동 수집은 비활성화 상태(`enable_live_execution=False`, 승인 파일 미생성)로 안전하게 보호 유지 중.

---

## 5. 결론 및 PR #12 최종 공식 병합 승인 요청
- **PR #12 공식 URL**: https://github.com/WisdomMax/chafficial/pull/12
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker`
- 총괄 감독(ChatGPT)님의 지침에 따라 권한 경계를 닫고(심볼릭 링크/7일 제한/boolean true 강제), 신규 배치의 레거시 우회 차단 및 메타데이터 타입 검증을 완벽히 구축하였습니다.
- 실제 LIVE 수집 승인과 PR #12 병합 승인이 분리 관리됨을 확인하였으며, PR #12의 최종 공식 병합 승인을 요청드립니다!
