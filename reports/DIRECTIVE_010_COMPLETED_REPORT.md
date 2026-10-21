# CHA-FICIAL AI PROJECT
## DIRECTIVE 010-C 완결 보고서: 최종 운영 데이터 정합성 정리 및 실제 시장 관측 실증

**수신:** 차피셜 AI 연구 총괄 감독 (ChatGPT)  
**발신:** Google Antigravity (실무 개발팀)  
**저장소:** `https://github.com/WisdomMax/chafficial`  
**PR 링크:** `https://github.com/WisdomMax/chafficial/pull/10`  
**대상 브랜치:** `feat/directive-010-market-observation-stream`  
**검증 일시:** 2026-10-21 11:55:00 KST  

---

## 0. DIRECTIVE 010-C 감사 요구사항 3대 조치 요약

1. **[조치 1] 기존 운영 DB 데이터 출처 정리 및 과거 재생 데이터 전면 격리:**
   - 수정 전 운영 DB를 [`data/chaficial_market_timeseries_pre_010c_backup.db`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/chaficial_market_timeseries_pre_010c_backup.db)로 안전 백업했습니다.
   - 운영 DB(`data/chaficial_market_timeseries.db`)에서 과거 010 재생 데이터(419건)를 완전히 격리 배제하고, 오직 실제 엔카 모바일 웹에서 실시간 수집된 **순수 실매물 126대(`REAL_OBSERVED`)**만을 보존하여 장부 무결성을 100% 회복했습니다.
   - 알고리즘 검증용 재생 픽스처 데이터는 [`data/chaficial_replay_benchmark.db`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/chaficial_replay_benchmark.db)로 엄격히 영구 분리되었습니다.
2. **[조치 2] 부분 수집(PARTIAL_SCRAPE) 보호 및 미노출 판정 원천 차단:**
   - 이번 126대 수집 배치는 1개 페이지 표본이므로 `is_partial_scrape=True`로 명시했습니다.
   - 파이프라인의 부분 수집 보호 로직에 따라 미노출 매물 카운터 증가 및 `DELISTED_SUSPECT` 전이가 100% 차단되었습니다 (`delisted_suspect_count=0`).
   - 수집 카드 250개 중 아반떼 CN7 126대 파싱, 비CN7 124대 제외 내역을 정직하게 기록했습니다.
3. **[조치 3] 시간 기록 정합성 (3대 시각 분리 영속화):**
   - 임의 산출 방식(+2초)을 전면 제거하고 실제 발생 시각을 3단계로 엄격히 분리 기록했습니다:
     - **웹 수집 시작:** `2026-10-21 11:55:00 KST` (UTC `2026-10-21T02:55:00.063928+00:00`)
     - **웹 수집 종료:** `2026-10-21 11:55:15 KST` (UTC `2026-10-21T02:55:15.444858+00:00`)
     - **DB 적재 완료:** `2026-10-21 12:00:20 KST` (UTC `2026-10-21T03:00:20.108099+00:00`)

---

## 1. 실제 시장 관측 장부 명세 (`REAL_OBSERVED`)

| 감사 항목 | 실측 증거 및 기록 |
| :--- | :--- |
| **관측 배치 ID** | `ENCAR_CN7_LIVE_20261021_01` |
| **데이터 출처 (`data_origin`)** | **`REAL_OBSERVED`** (실제 엔카 모바일 웹 실시간 조회) |
| **수집 범위 구분** | **`PARTIAL_SAMPLE` (is_partial_scrape: True)** |
| **웹 수집 시작 시각** | **2026-10-21 11:55:00 KST** |
| **웹 수집 종료 시각** | **2026-10-21 11:55:15 KST** |
| **DB 적재 완료 시각** | **2026-10-21 12:00:20 KST** |
| **원천 수집 파일** | [`data/raw_observations/encar_cn7_live_20261021_01.json`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/raw_observations/encar_cn7_live_20261021_01.json) |
| **원천 파일 SHA-256** | `c03deaec79e15eabda104b28b799ef52f8849bb702d2c40f857c0cd22945d32a` |
| **수집 카드 수 / 파싱 실매물 수** | **250개 카드 수집 / 아반떼 CN7 126대 파싱 (비CN7 124개 제외)** |
| **최초 발견 (`FIRST_SEEN`)** | **126대 (순수 운영 DB 기준)** |
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

## 2. 재생 벤치마크 장부 명세 (`REPLAY_FIXTURE`)

과거 010 시나리오 데이터 419건 및 다중 시점 시계열 동태 추적 알고리즘 검증은 격리된 벤치마크 환경에서 안전하게 보존·관리됩니다.

| 배치 ID | 데이터 출처 | 수집 매물 수 | 최초 발견 (`FIRST_SEEN`) | 재관측 수 | 미노출 의심 (`DELISTED`) | 성공 여부 | 검증 목적 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `REPLAY_CN7_FIXTURE_B01` | `REPLAY_FIXTURE` | 417대 | 417대 | 0대 | 0대 | SUCCESS | 기저 매물 최초 관측 적재 |
| `REPLAY_CN7_FIXTURE_B02` | `REPLAY_FIXTURE` | 417대 | 0대 | 417대 | 0대 | SUCCESS | 멱등성 실증 (중복 이벤트 0건) |
| `REPLAY_CN7_FIXTURE_B03` | `REPLAY_FIXTURE` | 418대 | 2대 (픽스처) | 416대 | 0대 | SUCCESS | 1대 미노출 보호(카운터:1, ACTIVE) 및 신규 2대 감지 |

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
5. **순수 실제 관측 운영 DB (126행 보존):**  
   [`data/chaficial_market_timeseries.db`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/data/chaficial_market_timeseries.db)

---

## 4. 결론 및 PR #10 최종 승인 요청

총괄 감독님의 DIRECTIVE 010-C 지침에 따라:
- 기존 운영 DB에서 재생 데이터(419건)를 완전 격리하고 백업을 확보했습니다.
- 운영 DB는 오직 실제 엔카 모바일 웹 실시간 증거와 일치하는 **126대 순수 실매물**만 보존합니다.
- 부분 수집 보호 정책(`is_partial_scrape=True`)으로 섣부른 미노출 판단을 100% 원천 차단했습니다.
- 웹 수집 시작/종료 시각과 DB 적재 완료 시각을 엄격히 분리 기록했습니다.

본 정합성 정리 작업이 GitHub PR #10 (`https://github.com/WisdomMax/chafficial/pull/10`)에 전수 반영되었으며, DIRECTIVE 010 최종 승인을 요청드립니다.
