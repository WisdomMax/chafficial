# CHA-FICIAL AI PROJECT
## DIRECTIVE 010-D 완결 보고서: 운영 DB 영구 보존 및 삭제 결함 완전 제거 실증

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**저장소:** `https://github.com/WisdomMax/chafficial`  
**PR 링크:** `https://github.com/WisdomMax/chafficial/pull/10`  
**대상 브랜치:** `feat/directive-010-market-observation-stream`  
**검증 일시:** 2026-10-21 12:05:00 KST  

---

## 0. DIRECTIVE 010-D 긴급 결함 수정 조치 결과

1. **운영 DB 삭제 로직(`db_path.unlink()`) 영구 완전 제거:**
   - `scripts/run_directive_010_market_stream.py` 211행의 `if db_path.exists(): db_path.unlink()`를 완전히 제거했습니다.
   - 운영 DB(`data/chaficial_market_timeseries.db`)가 존재하더라도 기존 데이터를 절대 삭제하지 않고 그대로 연결하여 누적 적재하도록 수정했습니다.
2. **연속 실행 시 멱등성 및 관측 이력 100% 보존 실증:**
   - 동일 배치를 2회 연속 실행했을 때, 파이프라인의 멱등성 스킵 정책(`ALREADY_PROCESSED_IDEMPOTENT_SKIP`)이 작동하여 DB 행 수가 1비트도 변하지 않고 **126행 그대로 보존**됨을 확인했습니다.
   - 연속 2회 실행 전후 운영 DB 행 수:
     - `listings`: **126행 -> 126행 (완전 불변 보존)**
     - `listing_snapshots`: **126행 -> 126행 (완전 불변 보존)**
     - `price_events`: **126행 -> 126행 (완전 불변 보존)**
     - `batch_audit_logs`: **1행 -> 1행 (완전 불변 보존)**
3. **부분 수집 보호 정책 실증 (`is_partial_scrape=True`):**
   - 부분 수집 시 미노출 카운터가 증가하지 않고 동결 보존되어 `DELISTED_SUSPECT` 오판이 0건으로 차단됨을 회귀 테스트로 검증했습니다.
4. **010-D 전용 회귀 테스트 세트 완비:**
   - [`tests/test_directive_010d_operational_db_preservation.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/tests/test_directive_010d_operational_db_preservation.py) (4개 테스트 신설 및 전수 통과).
   - 전체 테스트: **113개 전수 통과 (100% PASS, 1.17s)**.

---

## 1. 운영 DB 영구 보존 및 순수 실매물 장부 명세 (`REAL_OBSERVED`)

| 감사 항목 | 실측 증거 및 기록 |
| :--- | :--- |
| **관측 배치 ID** | `ENCAR_CN7_LIVE_20261021_01` |
| **데이터 출처 (`data_origin`)** | **`REAL_OBSERVED`** (실제 엔카 모바일 웹 실시간 조회) |
| **운영 DB 보존 정책** | **`PERMANENT_PRESERVE` (unlink/초기화 코드 전면 영구 제거)** |
| **수집 범위 구분** | **`PARTIAL_SAMPLE` (is_partial_scrape: True)** |
| **웹 수집 시작 시각** | **2026-10-21 11:55:00 KST** |
| **웹 수집 종료 시각** | **2026-10-21 11:55:15 KST** |
| **DB 적재 완료 시각** | **2026-10-21 12:00:20 KST** |
| **원천 수집 파일** | [`data/raw_observations/encar_cn7_live_20261021_01.json`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/raw_observations/encar_cn7_live_20261021_01.json) |
| **원천 파일 SHA-256** | `c03deaec79e15eabda104b28b799ef52f8849bb702d2c40f857c0cd22945d32a` |
| **수집 카드 수 / 파싱 실매물 수** | **250개 카드 수집 / 아반떼 CN7 126대 파싱 (비CN7 124개 제외)** |
| **순수 운영 DB 관리 매물 수** | **126대 (과거 재생 데이터 419건 완전 격리 완료)** |
| **실제 가격 변동** | **0건 (인하 0건, 인상 0건)** |
| **미노출 의심 (`DELISTED_SUSPECT`)** | **0건 (부분 수집 보호 정책으로 전면 차단)** |
| **수집 성공 여부** | **SUCCESS** |

> **순수 운영 DB (`data/chaficial_market_timeseries.db`) 5개 테이블 논리 SHA-256 해시:**
> - `listings` (126행): `b9d3f740c7f6ea5e172212202275a611056b8bd0fb8ce40dda06bb78e578de4b`
> - `listing_snapshots` (126행): `e29f87b2e47070bf6cc82e50954e373f94014e2a8ff5e4e11e5218c665c42b58`
> - `price_events` (126행): `2f902065d5f8a708cf47131eb70f201c1be43b8be36b6ddaab5e4201be78009f`
> - `batch_audit_logs` (1행): `2eefa4e5d8744dabe3ec41fe13f5d9e73b2fb4ed096b4a96b417eba869be24fc`
> - `vehicle_identity_links` (0행): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

---

## 2. DIRECTIVE 010-D 회귀 테스트 결과 (4개 신설, 전체 113개 통과)

```
tests/test_directive_010d_operational_db_preservation.py::test_operational_db_not_deleted_and_preserves_records PASSED
tests/test_directive_010d_operational_db_preservation.py::test_idempotent_reexecution_preserves_exact_state PASSED
tests/test_directive_010d_operational_db_preservation.py::test_partial_scrape_freezes_missing_counters PASSED
tests/test_directive_010d_operational_db_preservation.py::test_source_code_has_no_db_unlink_in_operational_scripts PASSED

============================= 113 passed in 1.17s ==============================
```

---

## 3. 핵심 산출물 파일 명세

1. **실제 시장 관측 원본 JSON:**  
   [`data/raw_observations/encar_cn7_live_20261021_01.json`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/raw_observations/encar_cn7_live_20261021_01.json)
2. **시간 정합성 반영 실제 시장 관측 감사 CSV:**  
   [`outputs/directive_010_real_market_audit_summary.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_010_real_market_audit_summary.csv)
3. **실제 수집 매물 126대 목록 CSV:**  
   [`outputs/directive_010_real_observed_listings.csv`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/outputs/directive_010_real_observed_listings.csv)
4. **수정 전 운영 DB 백업본:**  
   [`data/chaficial_market_timeseries_pre_010c_backup.db`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/chaficial_market_timeseries_pre_010c_backup.db)
5. **순수 실제 관측 운영 DB (126행 영구 보존):**  
   [`data/chaficial_market_timeseries.db`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/chaficial_market_timeseries.db)
6. **운영 DB 영구 보존 회귀 테스트 코드:**  
   [`tests/test_directive_010d_operational_db_preservation.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/tests/test_directive_010d_operational_db_preservation.py)

---

## 4. 결론 및 PR #10 최종 승인 요청

총괄 감독님의 지침에 따라:
- `db_path.unlink()`를 소스 코드에서 완전히 제거하여 운영 DB 삭제 위험을 영구 차단했습니다.
- 동일 배치 재실행 시 멱등성 검증을 거쳐 126행이 100% 불변 보존됨을 실증했습니다.
- 4개 회귀 테스트를 신설하여 전체 113개 테스트 전수 통과를 달성했습니다.

본 작업이 GitHub PR #10 (`https://github.com/WisdomMax/chafficial/pull/10`)에 전수 반영되었으며, DIRECTIVE 010 최종 승인을 요청드립니다.
