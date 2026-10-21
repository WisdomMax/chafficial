# CHA-FICIAL AI PROJECT
## DIRECTIVE 010-H 완결 보고서: 운영 관측 무결성 및 격리 최종 실증 (PR #10 최종 승인 요청)

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**저장소:** `https://github.com/WisdomMax/chafficial`  
**PR 링크:** `https://github.com/WisdomMax/chafficial/pull/10`  
**대상 브랜치:** `feat/directive-010-market-observation-stream`  
**검증 일시:** 2026-10-21 12:25:00 KST  

---

## 0. DIRECTIVE 010-H 핵심 보완 및 감사 지적 조치 요약

총괄 감독님의 `DIRECTIVE 010-H` 감사 지침에 따라, 과장된 수사("완벽", "100% 원천 차단", "수학적 불가능")를 철저히 배제하고 실측과 검증 가능한 코드에 기반하여 다음 5대 항목을 정직하게 보완했습니다.

1. **REPLAY 경로 강제 격리 및 우회 방어:**
   - `db_path_override`로 운영 DB를 지정하거나 심볼릭 링크를 통해 우회하는 시도를 방어하기 위해 `target_db_path.resolve() == OFFICIAL_OPERATIONAL_DB_PATH` 검증 로직을 도입했습니다.
   - REPLAY 모드에서 운영 DB 경로를 지정할 경우 즉시 `ValueError`가 발생하여 실행이 거부됨을 테스트(`test_replay_mode_rejects_operational_db_path`)로 실증했습니다.
2. **동시 실행 방지 프로세스 파일 락(FileLock) 도입:**
   - LIVE 관측 실행 시 `fcntl.flock` 기반의 배타적 파일 락(`data/.live_run.lock`)을 적용했습니다.
   - 다른 프로세스가 이미 관측을 수행 중일 경우 `OperationalLockError`를 발생시키며 DB 변경 전에 안전하게 즉시 중단되도록 구현하고 테스트(`test_live_concurrent_lock_prevents_dual_execution`)로 검증했습니다.
3. **세분화된 5대 실패 주입(Fault Injection) 독립 검증:**
   - ① 잘못된 JSON 응답: `test_fault_injection_invalid_json` (PASSED)
   - ② 수집 카드 0건: `test_fault_injection_zero_cards` (PASSED)
   - ③ 카드는 수집되었으나 아반떼 CN7 파싱 0건: `test_fault_injection_zero_cn7_parsed` (PASSED)
   - ④ 원본 JSON 파일 저장 실패 (디렉토리 권한/충돌): `test_fault_injection_raw_file_save_failure` (PASSED)
   - ⑤ DB 적재 중 런타임 오류: `test_fault_injection_db_ingest_failure` (트랜잭션 롤백 및 성공 감사 로그 0건 검증, PASSED)
   - 모든 실패 상황에서 운영 DB 논리 데이터와 배치 감사 로그가 오염되지 않음을 확인했습니다.
4. **기존 데이터 전체 속성 보존 및 Mutation Detection 실증:**
   - 단순 Primary Key 부분집합 검사를 넘어, 1차 수집된 126대 매물과 스냅샷의 전체 영속 필드(`source_platform`, `raw_location`, `current_status`, `consecutive_missing_count`, `first_observed_at`, 스냅샷 가격 등)가 2차 적재 후에도 100% 동일하게 보존됨을 확인했습니다.
   - 의도적으로 속성을 변조하는 Mutation Test를 수행하여 검증 함수가 변조를 즉시 감지함을 증명했습니다 (`test_existing_data_full_attributes_and_mutation_detection`).
5. **독립 원본 JSON 두 파일로부터 238대 고유 매물 수학적 재계산 증명:**
   - 1차 원본(`encar_cn7_live_20261021_01.json`): 아반떼 CN7 **126대**
   - 2차 원본(`encar_cn7_live_20261021_120825.json`): 아반떼 CN7 **120대**
   - 교집합 (2회 모두 관측된 재관측 매물): **8대**
   - 1차에만 존재하는 매물: **118대** (`126 - 8`)
   - 2차에만 존재하는 신규 매물: **112대** (`120 - 8`)
   - 합집합 고유 실매물: `118 + 112 + 8 = 238대`
   - 두 원본 파일의 파싱 합집합 결과가 운영 DB의 `source_listing_id` 집합과 정확히 1:1 일치함을 독립 테스트(`test_independent_two_batch_json_recalculation_to_238`)로 증명했습니다.

---

## 1. 실제 시장 2회 독립 LIVE 관측 장부 명세 (`REAL_OBSERVED`)

| 배치 ID | 관측 구분 | 웹 수집 시작 (KST) | 웹 수집 종료 (KST) | DB 적재 완료 (KST) | 수집 카드 / CN7 실매물 | 최초발견 (`FIRST_SEEN`) | 재관측 | 가격변동 | 미노출의심 | 원본 파일 및 전체 SHA-256 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `ENCAR_CN7_LIVE_20261021_01` | LIVE 1차 | 11:55:00 KST | 11:55:15 KST | 12:00:20 KST | 250개 / 126대 | 126대 | 0대 | 0건 | 0건 | `encar_cn7_live_20261021_01.json`<br>`c03deaec79e15eabda104b28b799ef52f8849bb702d2c40f857c0cd22945d32a` |
| `ENCAR_CN7_LIVE_20261021_120825` | LIVE 2차 | 12:08:25 KST | 12:08:40 KST | 12:08:40 KST | 248개 / 120대 | 112대 | 8대 | 0건 | 0건 | `encar_cn7_live_20261021_120825.json`<br>`3c3ef646d61302a8bf380c5e7b243beaa1c33f11d102e3aa9e73b40d6eef3550` |

> **학술적·운영적 정직성 준수 확인:**
> - `FIRST_SEEN`은 시스템 최초 발견 시점이며, 시장 최초 출고/등록일이 아닙니다.
> - 1차와 2차 사이 단기 시간 동안 실제 시장 가격 변동은 **0건**으로 확인되어 투명하게 유지했습니다.
> - 동일 실차 추정 링크(`vehicle_identity_links`)는 0건으로 정직하게 구분했습니다.

---

## 2. 순수 운영 DB (`data/chaficial_market_timeseries.db`) 5개 테이블 논리 SHA-256 해시

| 테이블 명 | 관리 레코드 수 | 논리 데이터 전체 행 SHA-256 해시 | 무결성 검증 |
| :--- | :---: | :---: | :---: |
| `listings` | **238행** | `5183ee9e4666a12c3b721ef9499dd5330fb72014e6bdbd03fc6b952611413d0a` | **126대 기존 이력 100% 보존 확인** |
| `listing_snapshots` | **246행** | `8bf7b94983d7c7d07f7c1b9817cf2a2e28e4150776f4f4996a24f4268dae2bca` | **시계열 스냅샷 정상 누적 확인** |
| `price_events` | **238행** | `6ddbabb6f41c33f20b23f480899789f11db185283a0639e2413f741f3dad7707` | **실제 이벤트 무결성 보존 확인** |
| `batch_audit_logs` | **2행** | `3a79b24e0b522e4b247273875ba428e6267ce2a4fe83f638d4a58a07bcf67831` | **2개 독립 LIVE 배치 영속 기록** |
| `vehicle_identity_links` | **0행** | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **결정론적 빈 테이블 해시** |

---

## 3. 전체 테스트 스위트 131개 100% 통과 원시 로그

```bash
$ uv run pytest
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.1.1, pluggy-1.7.0
rootdir: /Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI
configfile: pyproject.toml
testpaths: tests
collecting ... collected 131 items

tests/test_directive_002_all.py ......................                   [ 16%]
tests/test_directive_002a_corrections.py ......                          [ 21%]
tests/test_directive_002b_corrections.py ....                            [ 24%]
tests/test_directive_002c_corrections.py ...                             [ 26%]
tests/test_directive_002c_final_review.py ..                             [ 28%]
tests/test_directive_006_opportunity_scorer.py .....                     [ 32%]
tests/test_directive_007_opportunity_scorer.py .........                 [ 38%]
tests/test_directive_008_valuation_analysis.py ...........               [ 47%]
tests/test_directive_008c_integrity.py ....                              [ 50%]
tests/test_directive_009_price_tracker.py ......                         [ 54%]
tests/test_directive_009a_advanced_tracking.py .........                 [ 61%]
tests/test_directive_009b_operational_integrity.py ......                [ 66%]
tests/test_directive_009c_batch_hardening.py ......                      [ 70%]
tests/test_directive_010_market_stream.py ......                         [ 75%]
tests/test_directive_010d_operational_db_preservation.py ....            [ 78%]
tests/test_directive_010f_operational_robustness.py ....                 [ 81%]
tests/test_directive_010g_provenance_and_integrity.py .....              [ 85%]
tests/test_directive_010h_isolation_and_robustness.py .........          [ 92%]
tests/test_partner_intake.py ..........                                  [100%]

============================= 131 passed in 1.48s ==============================
```

---

## 4. 핵심 산출물 파일 명세

1. **실제 시장 관측 원본 파일들:**  
   - 1차: [`data/raw_observations/encar_cn7_live_20261021_01.json`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/raw_observations/encar_cn7_live_20261021_01.json)
   - 2차: [`data/raw_observations/encar_cn7_live_20261021_120825.json`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/raw_observations/encar_cn7_live_20261021_120825.json)
2. **누적 배치 감사 요약 CSV:**  
   [`outputs/directive_010_real_market_audit_summary.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_010_real_market_audit_summary.csv)
3. **운영 DB 누적 실매물 목록 CSV:**  
   [`outputs/directive_010_real_observed_listings.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_010_real_observed_listings.csv)
4. **순수 실제 관측 운영 시계열 DB:**  
   [`data/chaficial_market_timeseries.db`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/chaficial_market_timeseries.db)

---

## 5. 결론 및 PR #10 최종 정식 승인 및 DIRECTIVE 010 종료 요청

총괄 감독님의 DIRECTIVE 010-H 지침에 따라:
- REPLAY 모드의 운영 DB 접근을 `resolve()` 기반으로 강력히 차단.
- `fcntl.flock` 파일 락을 통한 LIVE 관측의 동시 실행 방지 체계 실증.
- 5대 실패 상황(JSON 오류, 카드 0건, CN7 0건, 파일 저장 실패, DB 오류) 개별 검증 완료.
- 기존 데이터 전체 속성 보존 및 변조 주입 탐지 테스트 실증.
- 두 원본 JSON 파일로부터 238대 고유 실매물 수학적 도출 완료.
- 과장된 표현을 전면 정정하고 전체 131개 테스트 100% 통과 확보.

PR #10 (`https://github.com/WisdomMax/chafficial/pull/10`)에 본 모든 내용이 최종 반영되었으므로, PR #10의 정식 승인 및 DIRECTIVE 010의 공식 종료를 요청드립니다.
