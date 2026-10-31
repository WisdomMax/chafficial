# CHA-FICIAL DIRECTIVE 137-CLOSE 완결 보고서
## 실제 운영 결함 수정, 부분문자열 제거, 광고 권한 판정 정정 및 개인정보 보호 완결

**수신:** ChatGPT 총괄 설계·감독관  
**발신:** Gemini Antigravity 개발팀  
**기준 커밋:** `e633a7f` -> 신규 픽스 커밋  
**우선순위:** P0 완결  
**결과 판정:** **감독관 지시 4대 결함 전면 조치 완료 및 격리 DB 회귀 테스트 100% 통과**

---

### 1. 감독관 지시 4대 항목 조치 결과 증적

#### [지시 1] 제휴 매물 0~9대 정상 동기화 보장 및 `owned_res` 안전 정의 (`UnboundLocalError` 원천 차단)
- **문제점**: 제휴 차량이 10대 미만일 때 전체 동기화 스킵 플래그로 인해 1~9대의 정상 제휴 매물까지 탈락되고, 0대일 때 `owned_res` 변수가 바인딩되지 않아 아카이빙 시 `UnboundLocalError`가 발생할 위험이 있었습니다.
- **조치 결과**:
  1. `scripts/run_daily_sync.py`에서 `owned_cars`가 0대일 때 `owned_res`를 `SKIPPED_EMPTY` 상태의 명시적 딕셔너리로 안전 바인딩하여 아카이빙 및 결과 보고 시 변수 미정의 오류를 원천 배제했습니다.
  2. 제휴 매물이 1대 이상이면 1~9대, 10대, 74대 등 모든 매물을 누락 없이 `service.run_sync(min_expected_count=1)`로 정상 동기화하도록 수정했습니다.
  3. 격리된 테스트 DB에서 0대, 1대, 9대, 10대, 74대 시나리오를 전수 회귀 검증 완료 (`tests/test_directive_137_close_edge_cases.py` 7/7 PASS).

#### [지시 2] 상사 식별에서 부분문자열 매칭 영구 제거 및 정규화 동등 비교(`==`) 구축
- **문제점**: `dealership_registry.py` 내 `any(k in cleaned_shop for k in match_keys)` 로직으로 인해 `"더쿨"`이 포함된 임의 문자열이 오매칭될 위험이 있었습니다.
- **조치 결과**:
  1. `src/chaficial/platform/dealerships/dealership_registry.py`에서 부분문자열 탐색 로직을 전면 삭제했습니다.
  2. 상사 고유 ID(`dealership_id`), 공식 명칭(`official_name`), 등록된 정확한 별칭 목록(`danji_exact_names`: `(주)더쿨모터스`, `더쿨모터스`, `주식회사 더쿨모터스`)과의 엄격한 정규화 동등 비교(`==`)만 허용하도록 전환했습니다.
  3. `"더쿨"` 단독, `"더쿨자동차"`, `"더쿨모터스클럽"` 등 변형/부분문자열은 100% 매칭 거부(`UNREGISTERED_MARKET_OBSERVED_DEALERSHIP`)됨을 단위 테스트로 입증했습니다.

#### [지시 3] 카매니저 딜러 등록 정보와 차마트 광고·사진 게재 권한 분리 및 미승인(`PENDING_CONFIRMATION`) 정정
- **문제점**: 카매니저 딜러 등록 사실만으로 차마트 광고 권한을 `APPROVED`로 표시했던 판정 오류가 지적되었습니다.
- **조치 결과**:
  1. 카매니저 상사/딜러 등록 상태(`is_partner_dealership=True`, D1 비공개 인벤토리 관리 대상)와 차마트 광고·사진 게재 권한(`is_advertising_approved=False`)을 명확히 분리했습니다.
  2. 별도 서면/동의 증빙이 확인되지 않은 더쿨모터스 74대의 광고 권한을 `APPROVED`에서 `PENDING_CONFIRMATION`으로 전면 정정했습니다.
  3. 공식 승인 광고 권한: **0대**, 광고 권한 확인 필요: **74대**, 고객용 홈페이지 공개: **0대**로 지표를 정정하였습니다.
  4. 기존 D1 매물은 전원 비공개(`is_public=0`, `PENDING_REVIEW`)로 엄격 보존됩니다.

#### [지시 4] 공개 GitHub 저장소 내 딜러 개인정보(휴대전화 번호) 마스킹 보호 및 비공개 격리
- **문제점**: 공개 저장소 커밋 파일에 딜러 7인의 실제 휴대전화 번호가 평문으로 포함되었습니다.
- **조치 결과**:
  1. `authorized_partner_dealerships.json` 및 문서에서 딜러 7인의 휴대전화 번호를 `010-XXXX-****` 형태로 전면 마스킹 처리했습니다.
  2. 전체 평문 연락처는 로컬 비공개 설정 파일(`data/.dealership_contacts_private.json`, 권한 0600, `.gitignore` 적용)로 분리 격리하여 공개 저장소 유출을 원천 차단했습니다.

---

### 2. 최종 필수 6대 지표 현황

| 항목 | 실측 수치 | 검증 상태 |
| :--- | :---: | :--- |
| **1. 실시간 수집 건수** | **1,764대** | 카매니저 라이브 서버 실측 (89페이지, 누락 0건) |
| **2. 차피셜 DB 실제 갱신 건수** | **1,764대** | 시계열 LIVE_OBSERVED 원자적 커밋 완결 |
| **3. 소속 상사 등록 확인 건수** | **74대** | DealershipRegistry 동등 비교 기반 공인 상사 확인 |
| **4. 공식 승인 광고 권한 건수** | **0대** | `PENDING_CONFIRMATION` (서면/동의 증빙 대기) |
| **5. 차마트 D1 비공개 연동 건수** | **74대** | Cloudflare D1 원격 인벤토리 (`is_public=0` 보존) |
| **6. 홈페이지 고객 공개 건수** | **0대** | 프로덕션 API 0대 격리 (사용자 최종 승인 전 비공개) |

---

### 3. 검증 테스트 결과 (100% PASS)

- **`tests/test_directive_137_close_edge_cases.py` (7/7 ALL PASS)**:
  * test_01: 상사 식별 부분문자열 영구 제거 및 동등 비교 검증 통과
  * test_02: 카매니저 딜러 등록과 차마트 광고 권한 엄격 분리 검증 통과
  * test_03: 공개 설정 파일 내 딜러 연락처 마스킹 보호 및 비공개 파일 격리 검증 통과
  * test_04: 격리 DB 0대 동기화 시 `owned_res` 안전 정의 (`SKIPPED_EMPTY`) 검증 통과
  * test_05: 격리 DB 1대 동기화 시 100% 정상 적재 검증 통과
  * test_06: 격리 DB 9대 동기화 시 100% 정상 적재 검증 통과 (10대 미만 결함 해결)
  * test_07: 격리 DB 10대 및 74대 전수 정상 적재 및 비공개(`is_public=0`) 보존 검증 통과
- **`tests/test_directive_137_r_real_market_pipeline.py` (7단계 E2E ALL PASS)**:
  * Step 1: 카매니저 라이브 시장 수집 감사 통과 (1,764대, 89페이지, 누락 0건)
  * Step 2: 시장 규모 적응형 하한선 및 동적 정합성 검증 확인
  * Step 3: DealershipRegistry 기반 공인 상사 식별 및 광고 권한 분리 완료 (제휴 74대 vs 시장관측 1,690대)
  * Step 4: 차피셜 분석 DB 실제 갱신 검증 완료 (LIVE_OBSERVED 시계열 1,764대)
  * Step 5: 차피셜 -> 차마트 D1 증분 동기화 및 2회차 무변동 완벽 스킵 확인
  * Step 6: 실매물 1호 `64노3143` D1 정밀 제원 일치 및 비공개 안전 보존 확인
  * Step 7: 고객용 공개 API 0대 완전 격리 실서버 검증 완료
- **보안 및 안전 규칙 회귀 테스트**:
  * `test_directive_136_sec.py`: 7/7 케이스 PASS
  * `test_directive_136_safety_rules.py`: 5/5 케이스 PASS
