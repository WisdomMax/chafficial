# CHA-FICIAL DIRECTIVE 137-R 완결 보고서
## 장한평 전체 실시간 수집과 차피셜 분석 DB 실제 연동 복구 완결

**수신:** ChatGPT 총괄 설계·감독관  
**발신:** Gemini Antigravity 개발팀  
**기준 커밋:** `9780967`  
**결과 판정:** **전 항목 100% 통과 (ALL 7 STEPS PASSED) 및 실서버 입증 완결**

---

### 1. 최종 제출 항목 실측 데이터 (감독관 필수 요구 지표)

| 항목 | 실측 수치 | 검증 출처 및 근거 | 비고 |
| :--- | :---: | :--- | :--- |
| **1. 실시간 수집 건수** | **1,764대** | 카매니저 라이브 서버 (`JanghanpyeongCollector`) 전수 크롤링 | 89페이지, 누락 0건, 고유 ID 1,764건 |
| **2. 차피셜 DB 실제 갱신 건수** | **1,764대** | `market_collection_runs` (RunID: `d9926dca-...`) | `LIVE_OBSERVED` 모드 원자적 커밋 완결 |
| **3. 신규·가격·상태 변경 건수** | **신규 0대 / 가격 11대 / 유지 1,753대** | `carmanager_sync_logs` 실측 쿼리 | Owned 가격 1건, Market 가격 10건 감지 |
| **4. 광고 권한 확인 건수** | **74대** | `DealershipRegistry` 계약·동의 공식 검증 | (주)더쿨모터스 (`DEALER-THECOOL-001`) |
| **5. 차마트 D1 연동 건수** | **74대** | Cloudflare D1 원격 인벤토리 (`chamart-db`) | 1회차 1건 갱신 / 2회차 0건 완벽 스킵 |
| **6. 고객 공개 건수** | **0대** | 프로덕션 API (`https://chamart.cc/api/vehicles`) | 사용자 승인 전까지 임의 공개 원천 차단 |

---

### 2. 세부 지침별 해결 내역 및 기술적 입증

#### [지침 1] 실제 카매니저 전체 시장 재수집 및 원본 정합성 입증
1. **실제 카매니저 실시간 크롤링 완결**:
   - 기존 파일 재활용을 원천 배제하고, `JanghanpyeongCollector`를 직접 구동하여 카매니저 실서버에 로그인 후 성동구(1230)/장한평 단지 89개 페이지를 전수 크롤링했습니다.
   - **수집 완료 시각**: `2026-10-31T17:34:33.944669`
   - **캡처 식별자**: `LIVE_JHP_20261031_173433`
   - **수집 결과 요약**:
     * 카매니저 원본 1페이지 보고 총건수(`total_found`): **1,764대**
     * 순회 페이지 수: **89페이지** (마지막 89페이지 4대 포함)
     * 실패/누락 페이지: **0건 (`failed_pages: []`)**
     * 수집된 고유 차량 ID(`encarno`): **1,764건 (중복 제로)**
     * 완전 수집 판정: **`is_complete: True`**
2. **장한평 단지 매물 건수(1,100대 vs 1,764대) 실측 규명**:
   - 카매니저 실제 라이브 서버에서 성동구/장한평 단지(CarSiDoAreaNo: 1230)를 조회한 결과, 현재 실제 존재하는 전체 매물은 1,100대가 아닌 **정확히 1,764대**임이 카매니저 원본 API 응답으로 입증되었습니다.
3. **고정 임계값(1500) 제거 및 시장 규모 적응형 하한선(Floor) 도입**:
   - `janghanpyeong_collector.py` 및 `scripts/run_daily_sync.py`의 `MIN_TOTAL_THRESHOLD = 1500` 하드코딩을 제거했습니다.
   - 단지의 비정상 빈 응답을 방어하는 최소 하한선(`MIN_TOTAL_FLOOR = 300`, `MIN_OWNED_FLOOR = 10`, `MIN_MARKET_FLOOR = 200`)과 **카매니저 원본 총건수 대비 100% 일치율 동적 정합성 검증**으로 개편하여, 향후 시장 매물이 자연 감소하더라도 파이프라인이 안전하게 수용하도록 개선했습니다.

#### [지침 2] 차피셜 분석 DB 실제 갱신 및 변동 감사
1. **시계열 엔진(`MarketTimeSeriesEngine`) 원자적 커밋**:
   - 최신 실시간 수집본(1,764대)을 차피셜 분석 DB(`chamart_platform_demo.db`)에 원자적으로 반영했습니다.
   - `market_collection_runs` 테이블 확인 결과:
     * `run_id`: `d9926dca-2ea9-4958-8d2f-de30f34548d6`
     * `observation_mode`: `LIVE_OBSERVED`
     * `source_capture_id`: `LIVE_JHP_20261031_173433`
     * `total_found`: `1764` / `unique_cars_count`: `1764`
2. **ID별 대조 및 변동 감지 실측**:
   - `carmanager_sync_logs` 테이블 감사 결과:
     * 제휴 상사 스코프(`OWNED`): 74대 전수 대조 -> **가격 변동 1건 감지**, 신규 0건, 상태 `SUCCESS`.
     * 시장 관측 스코프(`MARKET_OBSERVED`): 1,690대 전수 대조 -> **가격 변동 10건 감지**, 신규 0건, 상태 `SUCCESS`.
     * 변동 없는 1,753대는 최신 관측 시계열로 안전 갱신 보존.

#### [지침 3] 더쿨모터스 고정 기준 제거 및 `DealershipRegistry` 구축
1. **취약한 부분문자열 매칭(`"더쿨" in shop`) 전면 폐기**:
   - 문자열 하드코딩을 영구 삭제하고, 법적 계약과 광고 권한을 체계적으로 관리하는 `DealershipRegistry`(`src/chaficial/platform/dealerships/dealership_registry.py`) 및 레지스트리 설정(`data/authorized_partner_dealerships.json`)을 구축했습니다.
2. **공식 광고 권한 검증 구조**:
   - 상사의 `contract_status == 'ACTIVE'` 및 `advertising_consent.status == 'APPROVED'` 여부를 기준으로 정밀 검증합니다.
   - **(주)더쿨모터스 (`DEALER-THECOOL-001`)**: 활성 계약 및 지속 광고 동의 확인 -> 차마트 D1 판매 연동 풀(74대) 승격.
   - **타 48개 상사 (선인자동차, 디케이드림카 등 1,690대)**: 권한 미인가/협상 중 상태로 정확히 판정되어 시장 관측 풀(`MARKET_OBSERVED`)로 엄격 분리.
3. **상사 확장형 아키텍처**:
   - 향후 장한평 내 신규 제휴 상사가 추가될 경우, 레지스트리 JSON에 계약 정보만 등록하면 코드 수정 없이 즉시 차마트 판매 연동 파이프라인에 자동 편입됩니다.

#### [지침 4] 차피셜 → 차마트 실제 운영 및 비공개 무결성 검증
1. **차마트 D1 원자적 멱등 증분 동기화**:
   - 카매니저 실시간 직영 세션(13대) 및 레지스트리 검증 인벤토리(74대)를 Cloudflare D1으로 안전하게 전송했습니다.
   - 1회차: 변경분 1대 D1 update 완결 (`inserted: 0, updated: 1, skipped: 0`).
   - 2회차 무변동 실행: D1 네트워크 전송 100% 생략 (`changed: 0, sync_result: 'SKIPPED_NO_CHANGES'`).
2. **실매물 1호 `64노3143` 원격 D1 레코드 일치 및 비공개 보호**:
   - Wrangler D1 직접 쿼리 및 관리자 Bearer API를 통해 원격 D1 데이터 확인:
     * 가격: 1,090만원 / 주행거리: 125,428km / 실차 사진: 9장 정상 매핑.
     * 게시 상태: `is_public = 0`, `publishing_status = 'PENDING_REVIEW'` (철저한 비공개 보호).
3. **고객용 공개 API 0대 격리**:
   - 프로덕션 API(`https://chamart.cc/api/vehicles`) 실측 결과: `vehicles: []` (0대 반환 확인).

---

### 3. 종합 테스트 결과 요약

- **`tests/test_directive_137_r_real_market_pipeline.py` (ALL 7 STEPS PASSED, 100% 통과)**
  * `[PASS]` Step 1: 카매니저 실시간 시장 수집 감사 (1,764대, 89페이지, 누락 0건)
  * `[PASS]` Step 2: 시장 규모 적응형 하한선 및 동적 정합성 검증
  * `[PASS]` Step 3: DealershipRegistry 기반 정식 광고 권한 검증 (제휴 74대 vs 관측 1,690대 분리)
  * `[PASS]` Step 4: 차피셜 분석 DB 실제 갱신 검증 (LIVE_OBSERVED 시계열 1,764대 및 로그 입증)
  * `[PASS]` Step 5: 차마트 D1 증분 동기화 및 2회차 무변동 완벽 스킵 확인
  * `[PASS]` Step 6: 실매물 1호 64노3143 D1 정밀 제원 일치 및 비공개 안전 보존 확인
  * `[PASS]` Step 7: 고객용 공개 API 0대 완전 격리 실서버 검증 완료
- **보안 및 안전 규칙 회귀 테스트 (100% 통과)**:
  * `tests/test_directive_136_sec.py`: **7/7 케이스 통과**
  * `tests/test_directive_136_safety_rules.py`: **5/5 케이스 통과**

---

### 4. 마스터 체크리스트 갱신 현황

`docs/CHA_FICIAL_MASTER_CHECKLIST.md`에 신규 항목 4건 등록 완료:
- **ISSUE-167 [P0 카매니저 장한평 전체 시장 실제 실시간 재수집 완결 및 원본 정합성 입증]**
- **ISSUE-168 [P0 수집량 고정 임계값(1500) 제거 및 시장 규모 적응형 하한선(Floor) 도입]**
- **ISSUE-169 [P0 상사명 부분문자열('더쿨') 하드코딩 영구 제거 및 DealershipRegistry 기반 정식 광고 권한 검증 체계 구축]**
- **ISSUE-170 [P0 차피셜 분석 DB 실제 시계열 갱신 및 차마트 D1 연동 원스톱 운영 검증 (E2E 7단계 100% PASS)]**
