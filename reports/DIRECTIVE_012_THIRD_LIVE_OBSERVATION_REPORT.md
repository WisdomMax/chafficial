# DIRECTIVE 012: 3차 LIVE 시장 관측 및 시계열 가격 변동 실측 검증 보고서 (정정본)

## 1. 개요 및 관측 메타데이터
- **일시**: 2026-10-24 03:04:46 KST (종료: 03:05:02 KST)
- **수집 모드**: `LIVE` (엔카 모바일 웹 실시간 관측)
- **대상 차종**: 현대 아반떼 CN7 전 트림
- **배치 식별자**: `ENCAR_CN7_LIVE_20261024_030446_518b4987e3b2`
- **원본 수집 파일**: `data/raw_observations/encar_cn7_live_20261024_030446_518b4987e3b2.json`
  - **검증된 실제 원본 파일 SHA-256**: `da72c6583a276a9dcbda8a93049bfd8a1f26f1fa33a147ec022bde20461a3fe1` (shasum 및 python 재계산 일치)
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
| **최초 발견 (`FIRST_SEEN`)** | 110대 | **시스템 최초 관측 매물** (시장 신규 등록일 아님) |
| **재관측 (`RE_OBSERVED`)** | 26대 | 기존 1, 2차 관측 이력 보유 매물 재확인 |
| **실제 가격 변동 (`PRICE_DROP`)** | **5건** | **실제 시장 가격 인하 최초 실측** |
| **미노출 의심 매물** | 0건 (임계치 3회 미도달) | 결측 카운터 정상 동결 보호 |

---

## 3. 실제 시장 가격 인하(PRICE_DROP) 5건 원본 대조 상세 증거표

인위적 조작이나 합성 없이 엔카 실시간 웹 수집 원본 카드(`raw_cards`)의 실제 텍스트와 데이터베이스 이벤트/스냅샷을 1:1 정밀 대조한 결과입니다:

| 매물 ID | 이전 관측 원본 파일 | 이전 원본 카드 텍스트 (`raw_text`) | 3차 관측 원본 카드 텍스트 (`raw_text`) | DB 이벤트 ID (`price_events`) | 이전 가격 | 현재 가격 | 변동액 (KRW) | 변동률 | 누적 스냅샷 |
| :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **42718815** | `encar_cn7_live_20261021_01.json` | 아반떼 (CN7) 2.0 N 21/09식(22년형) 78,398km 가솔린 경기 1,590만원 | 아반떼 (CN7) 2.0 N 21/09식(22년형) 78,398km 가솔린 경기 1,540만원 | `c136300a-4cec-4284-9aa2-66851c2c3c62` | 1,590만 | 1,540만 | **-500,000원** | -3.14% | 2건 |
| **42316208** | `encar_cn7_live_20261021_01.json` | 아반떼 (CN7) 1.6 모던 20/12식(21년형) 40,243km 가솔린 대구 1,650만원 | 아반떼 (CN7) 1.6 모던 20/12식(21년형) 40,243km 가솔린 대구 1,450만원 | `be0b21e2-b872-470f-906c-9dfba06cd26b` | 1,650만 | 1,450만 | **-2,000,000원** | **-12.12%** | 3건 |
| **42867093** | `encar_cn7_live_20261021_01.json` | ... 아반떼 (CN7) 2.0 N 22/02식82,365km가솔린부산 1,860만원 ... | ... 아반떼 (CN7) 2.0 N 22/02식82,365km가솔린부산 1,840만원 ... | `4e5ace3c-14af-448e-8dd0-2995261c8169` | 1,860만 | 1,840만 | **-200,000원** | -1.08% | 2건 |
| **42864399** | `encar_cn7_live_20261021_01.json` | ... 아반떼 (CN7) 2.0 N 22/02식82,365km가솔린부산 1,860만원 | ... 아반떼 (CN7) 2.0 N 22/02식82,365km가솔린부산 1,840만원 | `9b34c111-cc65-4bb1-bf80-9dad722e455c` | 1,860만 | 1,840만 | **-200,000원** | -1.08% | 2건 |
| **42872963** | `encar_cn7_live_20261021_01.json` | ... 더 뉴 아반떼 하이브리드 (CN7) 인스퍼레이션 25/04식 38,185km 가솔린+전기 경기 2,490만원 | ... 더 뉴 아반떼 하이브리드 (CN7) 인스퍼레이션 25/04식38,185km가솔린+전기경기 2,470만원 | `a059757d-5ffe-4f5b-9800-57e11c7a3616` | 2,490만 | 2,470만 | **-200,000원** | -0.80% | 3건 |

- **총 가격 인하 누적액**: **3,100,000원**
- **평균 인하율**: -3.64% (최대 -12.12%, 200만원 인하)
- 가격 인하 발생 매물은 `listings.current_status = 'PRICE_CHANGED'`로 실시간 상태 전이 완료.

---

## 4. 운영 DB 무결성 및 기존 데이터 100% 영구 보존 검증

### 4.1 테이블별 레코드 변화 및 논리 SHA-256 해시
| 테이블명 | 적재 전 (1·2차) | 적재 후 (3차 LIVE) | 증감 | 적재 후 논리 SHA-256 해시 |
| :--- | :---: | :---: | :---: | :--- |
| `listings` | 238 | **348** | +110 | `e83a6fcf46e96a12c28aa32b675a48d71ad0212b079b70ff33423a7d8e23cf11` |
| `listing_snapshots` | 246 | **382** | +136 | `988a14e32318ff2bf314ee92b17fffb6069cc5b767e0a035c9332e1bd07cdf33` |
| `price_events` | 238 | **353** | +115 | `4ed4893f05c877e3c22455dbb8d71bd627af8ead9c8b301e132063f219dabc26` |
| `vehicle_identity_links` | 0 | 0 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `batch_audit_logs` | 2 | **3** | +1 | `0188b48f94691c2289481cd904de191e47badc1e0514ddec630f0971f5ae0882` |

### 4.2 기존 238대 실매물 누락 0건 독립 SQL 검증
- 1차 수집 CN7: 126대
- 2차 수집 CN7: 120대
- 1, 2차 교집합 (재관측): 8대
- 1, 2차 고유 합집합: **238대**
- 3차 LIVE 적재 후 운영 DB에 존재하는 1, 2차 합집합 매물 수: **238대 (100% 완전 보존)**
- 신규 발견 매물: **110대** -> 누적 총 매물: **348대**
- 기존 246개 스냅샷 PK 및 속성 값 온전 보존 + 신규 136개 추가 = **총 382건 스냅샷 불변 유지**
- `PRAGMA integrity_check`: `ok` (무결성 100% 통과)

---

## 5. 원본 해시 정정 및 감사 일치성 증명
- 개별 관측 보고서(`reports/observations/observation_batch_ENCAR_CN7_LIVE_20261024_030446_518b4987e3b2.md`), 운영 DB `batch_audit_logs.notes` 메타데이터, 그리고 실제 파일 바이트 해시 모두 `da72c6583a276a9dcbda8a93049bfd8a1f26f1fa33a147ec022bde20461a3fe1`로 **완벽하게 1:1 일치**함을 확인하였습니다.
- 이전 보고서의 초안 작성 시 발생했던 문자열 기재 오류를 공식 정정 완료하였습니다.

---

## 6. 전체 테스트 스위트 결과 (152/152 통과)
```text
tests/test_directive_002_all.py ......................                   [ 14%]
tests/test_directive_002a_corrections.py ......                          [ 18%]
tests/test_directive_002b_corrections.py ....                            [ 21%]
tests/test_directive_002c_corrections.py ...                             [ 23%]
tests/test_directive_002c_final_review.py ..                             [ 24%]
tests/test_directive_006_opportunity_scorer.py .....                     [ 27%]
tests/test_directive_007_opportunity_scorer.py .........                 [ 33%]
tests/test_directive_008_valuation_analysis.py ...........               [ 40%]
tests/test_directive_008c_integrity.py ....                              [ 43%]
tests/test_directive_009_price_tracker.py ......                         [ 47%]
tests/test_directive_009a_advanced_tracking.py .........                 [ 53%]
tests/test_directive_009b_operational_integrity.py ......                [ 57%]
tests/test_directive_009c_batch_hardening.py ......                      [ 61%]
tests/test_directive_010_market_stream.py ......                         [ 65%]
tests/test_directive_010d_operational_db_preservation.py ....            [ 67%]
tests/test_directive_010f_operational_robustness.py ....                 [ 70%]
tests/test_directive_010g_provenance_and_integrity.py .....              [ 73%]
tests/test_directive_010h_isolation_and_robustness.py .........          [ 79%]
tests/test_directive_010i_audit_hardening.py ...                         [ 81%]
tests/test_directive_010j_report_consistency.py .                        [ 82%]
tests/test_directive_010k_report_preservation_and_dynamics.py ....       [ 84%]
tests/test_directive_011_recovery_and_operations.py .............        [ 93%]
tests/test_partner_intake.py ..........                                  [100%]
============================= 152 passed in 4.56s ==============================
```

---

## 7. 결론 및 PR #11 최종 머지 승인 요청
- 원본 SHA-256 해시 감사 불일치가 완벽히 해소되었습니다 (`da72c6583a276a9dcbda8a93049bfd8a1f26f1fa33a147ec022bde20461a3fe1`).
- 가격 인하 5건의 원본 텍스트 및 DB 이벤트 ID 매핑 증거표가 완비되었습니다.
- 기존 238대 실매물 및 246개 스냅샷의 100% 영구 보존이 수학적·독립 SQL로 재입증되었습니다.
- 총괄 감독(ChatGPT)님의 최종 승인 및 PR #11 머지 허가를 요청합니다.
