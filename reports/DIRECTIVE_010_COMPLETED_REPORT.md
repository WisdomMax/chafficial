# CHA-FICIAL AI PROJECT
## DIRECTIVE 010-E 완결 보고서: 실제 반복 시장 관측 자동화 및 시계열 누적 실증

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**저장소:** `https://github.com/WisdomMax/chafficial`  
**PR 링크:** `https://github.com/WisdomMax/chafficial/pull/10`  
**대상 브랜치:** `feat/directive-010-market-observation-stream`  
**검증 일시:** 2026-10-21 12:08:25 KST  

---

## 0. DIRECTIVE 010-E 핵심 수행 요약

1. **실제 반복 관측 자동화 모드 분리 (`--mode live` vs `--mode replay`):**
   - 기존의 파일명 및 배치 ID 고정 구조를 완전히 탈피하여, 스크립트 실행마다 실제 웹을 실시간 조회하고 타임스탬프 기반 고유 `batch_id`와 원본 JSON 파일을 동적 생성하도록 구현했습니다.
2. **운영 DB 영구 보존 및 실제 시계열 누적 실증 (서로 다른 2개 시점 LIVE 관측):**
   - 1차 LIVE 수집: `ENCAR_CN7_LIVE_20261021_01` (11:55:00 KST, 126대 관측)
   - 2차 LIVE 수집: `ENCAR_CN7_LIVE_20261021_120825` (2026-10-21 12:08:25 KST, 120대 실시간 관측)
   - 운영 DB를 일절 삭제하지 않고 1차 관측 126대를 100% 보존한 상태에서 2차 실시간 관측이 누적되었습니다.
   - 누적 운영 DB 현황:
     - 총 고유 실매물: **238대** (기존 이력 100% 보존)
     - 총 관측 스냅샷: **246건**
     - 총 배치 감사 로그: **2건**
3. **실제 시장 가격 변동 정직성 준수:**
   - 1차와 2차 사이의 단기 시간 동안 실제 시장에서 관측된 가격 변동은 **0건 (인하 0건, 인상 0건)**으로 투명하게 보고합니다.
4. **부분 수집 보호 정책 완비 (`is_partial_scrape=True`):**
   - 1페이지 표본 관측에 대해 미노출 카운터 동결 보호를 적용하여 섣부른 `DELISTED_SUSPECT` 오판을 0건으로 완전 차단했습니다.
5. **백업 보호 정책:**
   - 실행 시 기존 백업을 덮어쓰지 않고 `data/backups/market_timeseries_backup_{timestamp}.db`로 타임스탬프 고유 백업을 생성합니다.

---

## 1. 실제 시장 2회 독립 LIVE 관측 감사 요약표

| 배치 ID | 관측 구분 | 웹 수집 시작 (KST) | 웹 수집 종료 (KST) | DB 적재 완료 (KST) | 수집 카드 / 실매물 | 최초발견 (`FIRST_SEEN`) | 재관측 | 가격변동 | 미노출의심 | 원본 파일 및 SHA-256 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `ENCAR_CN7_LIVE_20261021_01` | LIVE 1차 | 11:55:00 KST | 11:55:15 KST | 12:00:20 KST | 250개 / 126대 | 126대 | 0대 | 0건 | 0건 | `encar_cn7_live_20261021_01.json`<br>`c03deaec79e1...` |
| `ENCAR_CN7_LIVE_20261021_120825` | LIVE 2차 | 2026-10-21 12:08:25 KST | 2026-10-21 12:08:40 KST | 2026-10-21 12:08:40 KST | 248개 / 120대 | 112대 | 8대 | 0건 | 0건 | `encar_cn7_live_20261021_120825.json`<br>`3c3ef646d61302a8...` |

---

## 2. 순수 운영 DB (`data/chaficial_market_timeseries.db`) 5개 테이블 논리 SHA-256 해시

| 테이블 명 | 관리 레코드 수 | 논리 데이터 전체 행 SHA-256 해시 | 무결성 검증 |
| :--- | :---: | :---: | :---: |
| `listings` | **238행** | `5183ee9e4666a12c3b721ef9499dd5330fb72014e6bdbd03fc6b952611413d0a` | **영속 컬럼 직렬화 검증 완료 (126대 기존 이력 보존)** |
| `listing_snapshots` | **246행** | `8bf7b94983d7c7d07f7c1b9817cf2a2e28e4150776f4f4996a24f4268dae2bca` | **시계열 스냅샷 정상 누적 완료** |
| `price_events` | **238행** | `6ddbabb6f41c33f20b23f480899789f11db185283a0639e2413f741f3dad7707` | **실제 이벤트 무결성 보존** |
| `batch_audit_logs` | **2행** | `3a79b24e0b522e4b247273875ba428e6267ce2a4fe83f638d4a58a07bcf67831` | **2개 독립 LIVE 배치 영속 기록** |
| `vehicle_identity_links` | **0행** | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | **결정론적 빈 테이블 해시** |

---

## 3. 회귀 테스트 및 전체 테스트 통과 증거

```
tests/test_directive_010d_operational_db_preservation.py::test_operational_db_not_deleted_and_preserves_records PASSED
tests/test_directive_010d_operational_db_preservation.py::test_idempotent_reexecution_preserves_exact_state PASSED
tests/test_directive_010d_operational_db_preservation.py::test_partial_scrape_freezes_missing_counters PASSED
tests/test_directive_010d_operational_db_preservation.py::test_source_code_has_no_db_unlink_in_operational_scripts PASSED

============================= 113 passed in 1.17s ==============================
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

## 5. 결론 및 PR #10 최종 승인 및 DIRECTIVE 010 종료 요청

총괄 감독님의 DIRECTIVE 010-E 지침에 따라:
- `--mode live` / `--mode replay` 분리 자동화 구축.
- 서로 다른 2개 시점의 실제 LIVE 엔카 시장 관측을 성공적으로 완료하고 원본 증거(JSON 및 SHA-256)를 영속화.
- 기존 126대 관측 이력을 100% 보존하면서 신규 관측이 누적되는 시계열 데이터 엔진 구축 실증.

본 최종 결과가 GitHub PR #10 (`https://github.com/WisdomMax/chafficial/pull/10`)에 전수 반영되었으며, DIRECTIVE 010의 최종 승인 및 종료를 요청드립니다.
