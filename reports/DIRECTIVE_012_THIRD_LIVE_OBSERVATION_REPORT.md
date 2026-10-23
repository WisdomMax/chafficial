# DIRECTIVE 012: 3차 LIVE 시장 관측 및 시계열 가격 변동 실측 최종 검증 보고서 (012-B 완료본)

## 1. 개요 및 관측 메타데이터
- **일시**: 2026-10-24 03:04:46 KST (종료: 03:05:02 KST)
- **수집 모드**: `LIVE` (엔카 모바일 웹 실시간 관측)
- **대상 차종**: 현대 아반떼 CN7 전 트림
- **배치 식별자**: `ENCAR_CN7_LIVE_20261024_030446_518b4987e3b2`
- **원본 수집 파일**: `data/raw_observations/encar_cn7_live_20261024_030446_518b4987e3b2.json`
  - **검증된 실제 원본 파일 SHA-256**: `da72c6583a276a9dcbda8a93049bfd8a1f26f1fa33a147ec022bde20461a3fe1` (shasum, python hashlib 및 단위 테스트 일치)
  - 원본 파일 크기: 97,464 bytes
  - 원천 관측 카드 수: 248개
  - 수집 소요 시간: 14.1초
- **운영 DB 사전 백업본**: `data/backups/market_timeseries_backup_20261024_030446_eb757e21301e.db` (PRAGMA integrity_check = ok)

---

## 2. 3차 관측 및 시계열 적재 실적 (동적 산출)

| 항목 | 수치 / 내용 | 비고 |
| :--- | :--- | :--- |
| **원천 수집 카드** | 248개 | 엔카 모바일 웹 실시간 추출 카드 수 |
| **정밀 파싱 성공** | 136대 (파싱률 54.8%) | 타 차종 및 불완전 카드 112개 안전 제외 |
| **최초 발견 (`FIRST_SEEN`)** | 110대 | **시스템 최초 관측 매물** (`NEW_LISTING`, 시장 신규 등록일 아님) |
| **재관측 (`RE_OBSERVED`)** | 26대 | 기존 1, 2차 관측 이력 보유 매물 재확인 |
| **실제 가격 변동 (`PRICE_DROP`)** | **5건** | **실제 시장 가격 인하 최초 실측** (3차 배치에 100% 귀속) |
| **미노출 의심 매물** | 0건 (임계치 3회 미도달) | 결측 카운터 정상 동결 보호 |

---

## 3. [DIRECTIVE 012-B] 가격 인하 5건의 3차 배치 귀속 및 원본 가격 1:1 전수 검증

3차 관측 배치(`ENCAR_CN7_LIVE_20261024_030446_518b4987e3b2`)의 `event_ids` 감사 메타데이터 범위 내에서 전수 조회한 결과, 5건 모두 3차 배치에 정확히 귀속되었으며 원본 가격과 DB 가격 간 불일치가 0건(100% 일치)임을 확인하였습니다:

| 매물 ID | 이전 관측 원본 파일 | 이전 원본 카드 텍스트 (`raw_text`) | 3차 원본 카드 텍스트 (`raw_text`) | 3차 배치 귀속 PriceEvent ID | 이전 가격 (원본 vs DB) | 현재 가격 (원본 vs DB) | 변동액 (KRW) | 변동률 | 배치 귀속 상태 |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **42718815** | `encar_cn7_live_20261021_01.json` | 아반떼 (CN7) 2.0 N 21/09식(22년형) 78,398km 가솔린 경기 1,590만원 | 아반떼 (CN7) 2.0 N 21/09식(22년형) 78,398km 가솔린 경기 1,540만원 | `c136300a-4cec-4284-9aa2-66851c2c3c62` | 1,590만 == 1,590만 | 1,540만 == 1,540만 | **-500,000원** | -3.14% | **VERIFIED_100%** |
| **42316208** | `encar_cn7_live_20261021_01.json` | 아반떼 (CN7) 1.6 모던 20/12식(21년형) 40,243km 가솔린 대구 1,650만원 | 아반떼 (CN7) 1.6 모던 20/12식(21년형) 40,243km 가솔린 대구 1,450만원 | `be0b21e2-b872-470f-906c-9dfba06cd26b` | 1,650만 == 1,650만 | 1,450만 == 1,450만 | **-2,000,000원** | **-12.12%** | **VERIFIED_100%** |
| **42867093** | `encar_cn7_live_20261021_01.json` | ... 아반떼 (CN7) 2.0 N 22/02식82,365km가솔린부산 1,860만원 ... | ... 아반떼 (CN7) 2.0 N 22/02식82,365km가솔린부산 1,840만원 ... | `4e5ace3c-14af-448e-8dd0-2995261c8169` | 1,860만 == 1,860만 | 1,840만 == 1,840만 | **-200,000원** | -1.08% | **VERIFIED_100%** |
| **42864399** | `encar_cn7_live_20261021_01.json` | ... 아반떼 (CN7) 2.0 N 22/02식82,365km가솔린부산 1,860만원 | ... 아반떼 (CN7) 2.0 N 22/02식82,365km가솔린부산 1,840만원 | `9b34c111-cc65-4bb1-bf80-9dad722e455c` | 1,860만 == 1,860만 | 1,840만 == 1,840만 | **-200,000원** | -1.08% | **VERIFIED_100%** |
| **42872963** | `encar_cn7_live_20261021_01.json` | ... 더 뉴 아반떼 하이브리드 (CN7) 인스퍼레이션 25/04식 38,185km 가솔린+전기 경기 2,490만원 | ... 더 뉴 아반떼 하이브리드 (CN7) 인스퍼레이션 25/04식38,185km가솔린+전기경기 2,470만원 | `a059757d-5ffe-4f5b-9800-57e11c7a3616` | 2,490만 == 2,490만 | 2,470만 == 2,470만 | **-200,000원** | -0.80% | **VERIFIED_100%** |

- **총 가격 인하 누적액**: **3,100,000원** (평균 인하율 -3.64%, 최대 -12.12%)
- 5개 매물 모두 3차 관측 배치 실행 직후 `listings.current_status = 'PRICE_CHANGED'`로 정상 상태 전이 완료.

---

## 4. [DIRECTIVE 012-B] 사전 백업 DB vs 운영 DB 간 기존 스냅샷 246건 행 단위(Row-by-Row) 전수 검증

3차 LIVE 수집 직전 배타적으로 생성된 백업 DB(`market_timeseries_backup_20261024_030446_eb757e21301e.db`)와 현재 운영 DB 간의 스냅샷 레코드 전수 비교 결과:

- **사전 백업 스냅샷 수**: **246건**
- **운영 DB 전체 스냅샷 수**: **382건** (기존 246건 + 3차 신규 136건)
- **행 단위(Row-by-Row) 전수 검사 결과**:
  - 검사 완료: **246건 / 246건**
  - 검사 항목: `snapshot_id`(PK), `listing_id`, `observed_at`, `price_krw`, `mileage_km`, `listing_status`, `normalized_region_id`, `source_record_hash`, `raw_specs`
  - **불일치(Mismatch) 발생 건수**: **0건 (100% 동일 불변 보존 입증)**

---

## 5. [DIRECTIVE 012-B] 기존 매물 238건 보존 및 정상 갱신 필드 분리 검증

- **사전 백업 매물 수**: **238대**
- **운영 DB 전체 매물 수**: **348대** (기존 238대 + 3차 신규 110대)
- **불변 고유 식별 정보 검증**:
  - 검사 항목: `listing_id`(PK), `source_platform`, `source_listing_id`, `first_observed_at`, `raw_location`
  - **식별 정보 100% 불변 보존**: **238대 / 238대 (100%)**
- **정상 갱신 필드 검증**:
  - 가격 인하 발생 5대: `current_status = 'PRICE_CHANGED'` (정상 상태 전이 확인)
  - 미변동 233대: `current_status = 'ACTIVE'`, 결측 카운터 `consecutive_missing_count = 0` (정상 동결 유지 확인)

---

## 6. 전체 테스트 스위트 결과 (156/156 통과)
```text
tests/test_directive_002_all.py ......................                   [ 14%]
tests/test_directive_002a_corrections.py ......                          [ 17%]
tests/test_directive_002b_corrections.py ....                            [ 20%]
tests/test_directive_002c_corrections.py ...                             [ 22%]
tests/test_directive_002c_final_review.py ..                             [ 23%]
tests/test_directive_006_opportunity_scorer.py .....                     [ 26%]
tests/test_directive_007_opportunity_scorer.py .........                 [ 32%]
tests/test_directive_008_valuation_analysis.py ...........               [ 39%]
tests/test_directive_008c_integrity.py ....                              [ 42%]
tests/test_directive_009_price_tracker.py ......                         [ 46%]
tests/test_directive_009a_advanced_tracking.py .........                 [ 51%]
tests/test_directive_009b_operational_integrity.py ......                [ 55%]
tests/test_directive_009c_batch_hardening.py ......                      [ 59%]
tests/test_directive_010_market_stream.py ......                         [ 63%]
tests/test_directive_010d_operational_db_preservation.py ....            [ 66%]
tests/test_directive_010f_operational_robustness.py ....                 [ 68%]
tests/test_directive_010g_provenance_and_integrity.py .....              [ 71%]
tests/test_directive_010h_isolation_and_robustness.py .........          [ 77%]
tests/test_directive_010i_audit_hardening.py ...                         [ 79%]
tests/test_directive_010j_report_consistency.py .                        [ 80%]
tests/test_directive_010k_report_preservation_and_dynamics.py ....       [ 82%]
tests/test_directive_011_recovery_and_operations.py .............        [ 91%]
tests/test_directive_012b_verification.py ....                           [ 93%]
tests/test_partner_intake.py ..........                                  [100%]
============================= 156 passed in 4.71s ==============================
```

---

## 7. 결론 및 PR #11 최종 병합 승인 요청
1. **가격 인하 5건의 3차 배치 귀속 및 원본 가격 1:1 대조 완벽 입증**: 3차 배치 감사 로그에 5건이 정확히 귀속되었으며, 원본 텍스트와 DB 가격 간 오차 0원.
2. **사전 백업 대비 기존 스냅샷 246건의 행 단위(Row-by-Row) 불변 보존 완벽 입증**: 불일치 0건.
3. **기존 매물 238건의 식별정보 보존 및 상태 전이 완벽 입증**: 5건 `PRICE_CHANGED`, 233건 `ACTIVE` 유지.
4. **원본 파일 SHA-256 일치 및 전체 156개 테스트 100% 통과**.
5. PR #11의 베이스 브랜치는 `feat/directive-009-price-event-tracker`이며, 총괄 감독님의 최종 공식 병합 승인을 요청합니다!
