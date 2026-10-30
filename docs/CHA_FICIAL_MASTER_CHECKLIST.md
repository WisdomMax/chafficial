# CHA-FICIAL 마스터 프로젝트 체크리스트 & 영구 개발 로드맵
> **기준 커밋:** DIRECTIVE 110-R 보강 (`9c5de40` -> DIRECTIVE 110-R)  
> **최종 갱신일:** 2026-10-30 22:30:00 KST  
> **상태 표기 원칙 (Supervisor Approval Standard):**  
> - `[x] 🟢 감독 승인 완료 (Approved by Supervisor)`: 총괄 감독관이 독립 감사를 통해 직접 승인한 항목만 [x] 표기  
> - `[ ] 🟡 구현 완료 / 검증 대기 (Implemented, Pending Audit)`: 코드는 구현 및 자체 테스트 완료되었으나 감독관의 공식 승인 대기 상태  
> - `[ ] ⚪️ 미구현 / 착수 예정 (Planned)`: 향후 로드맵 상의 착수 예정 작업  
> - `[ ] 🔴 보류 / 결함 발견 (Blocked / Issue Found)`: 결함 발생으로 운영 승인 차단 상태  

---

## 📌 P0 결함 추적표 (Issue Tracking Table)

| 결함 ID | 결함 설명 | 위험도 | 조치 상태 | 관련 커밋 / 검증 증거 |
| :--- | :--- | :---: | :---: | :--- |
| **ISSUE-01** | 가격 단위(만원 vs 원) 혼입으로 137건 가짜 가격변경 발생 | 심각 | 🟢 해결완료 | `987dd18` (173건 만원 정규화, 타임라인 정정) |
| **ISSUE-02** | 썸네일(_TH) 수집으로 인한 저화질(16KB) 사진 저장 | 높음 | 🟢 해결완료 | `a4c6c3c` (1024x768 원본 복구 2,419장, encarno 매핑) |
| **ISSUE-03** | 순번(car_001) 재사용으로 인한 재수집 시 사진 오연결 위험 | 높음 | 🟢 해결완료 | `a4c6c3c` (고유 encarno 디렉터리 분격 격리) |
| **ISSUE-04** | 주행거리 파서가 '5.5만 km'를 55km로 왜곡할 위험 | 심각 | 🟢 해결완료 | `987dd18` (정규표현식 파서 단일화 및 유닛테스트 통과) |
| **ISSUE-05** | 번호판 미확인 시 끝 4자리를 plate_number에 오삽입 | 보통 | 🟢 해결완료 | `987dd18` (UNVERIFIED 처리 및 observation_notes 격리) |
| **ISSUE-06** | 수집기 반환값에 cars가 누락되어 --live 경로 빈 목록 수신 | 심각 | 🟢 해결완료 | `b6c04f6` (summary["cars"] 명시 반환) |
| **ISSUE-07** | daily_carmanager_sync.sh에 --live 옵션 누락으로 정적 JSON 재사용 | 심각 | 🟢 해결완료 | `5081b6f` (--live 옵션 명시 및 기본 실행 LIVE 고정) |
| **ISSUE-08** | 50대 이상이면 통과하는 느슨한 수집량 임계치로 매물 대량 누락 위험 | 심각 | 🟢 해결완료 | `5081b6f` (시장 1,500대 미만 시 즉시 0건 쓰기 및 exit 1 차단) |
| **ISSUE-09** | 번호판 중복 병합 스크립트가 UNVERIFIED 번호판을 오병합할 위험 | 높음 | 🟢 해결완료 | `5081b6f` (WHERE plate_number != 'UNVERIFIED' 강제) |
| **ISSUE-10** | --dry-run 옵션이 실제 DB를 수정하는 결함 | 심각 | 🟢 해결완료 | `carmanager_sync.py` (dry_run=True 시 DB 롤백 및 쓰기 0건) |
| **ISSUE-11** | 수집기 세션 토큰 로그 노출 (보안 취약점) | 보통 | 🟢 해결완료 | `janghanpyeong_collector.py` (토큰 마스킹 적용) |
| **ISSUE-12** | 전역 SHA256 중복 검사로 인한 일일 동일 매물 관측 유실 (Days on Market 파괴) | 심각 | 🟢 해결완료 | `market_timeseries_engine.py` (run_id 기준 멱등성 및 일일 관측 영구 보존) |
| **ISSUE-13** | 운영 DB 가격 변경 후 시계열 DB 적재 실행 순서 역전 | 심각 | 🟢 해결완료 | `run_daily_sync.py` (시계열 성공 확인 후 운영 DB 반영 순서 교정) |
| **ISSUE-14** | 시계열 적재 실패 시에도 전체 작업을 성공으로 오표시 | 심각 | 🟢 해결완료 | `run_daily_sync.py` (시계열 실패 시 즉각 파이프라인 차단 및 운영 쓰기 0건) |
| **ISSUE-15** | 수집 완전성을 단순 1,500대 하한선으로만 판정 | 높음 | 🟢 해결완료 | `janghanpyeong_collector.py` (total_found 대조, max_pages 도달, failed_pages=0 검증) |
| **ISSUE-16** | dry-run 모드 시 시계열 엔진 생성자의 DDL(테이블 생성) 쓰기 발생 결함 | 심각 | 🟢 해결완료 | `market_timeseries_engine.py` (dry_run 시 DDL 건너뛰고 mode=ro 읽기 전용 적용) |
| **ISSUE-17** | source 및 search_condition 미분리로 인한 이전 관측 대조 혼선 | 높음 | 🟢 해결완료 | `market_timeseries_engine.py` (동일 source/검색조건 한정 직전 스냅샷 쿼리) |
| **ISSUE-18** | photo_count 미확인 매물에 임의 0 하드코딩 왜곡 | 보통 | 🟢 해결완료 | `market_timeseries_engine.py` (사진 미확인 시 엄격한 NULL 저장) |
| **ISSUE-19** | 관측 레코드별 원본 데이터 해시(raw_hash) 누락 | 보통 | 🟢 해결완료 | `market_timeseries_engine.py` (매물 json SHA256 불변 기록) |
| **ISSUE-20** | 90페이지 이상 동적 수집 실질적 통합 실험 부재 | 높음 | 🟢 해결완료 | `test_directive_110_r_integration.py` (실험 A~G 7대 통합 실험 100% 통과) |
| **ISSUE-21** | 수집기-시계열 엔진 필드명 불일치로 인한 1,764대 가격 0원 및 모델/연식/상사 NULL 오염 | 심각 | 🟢 해결완료 | `normalizer.py` (공통 정규화 계층 구축 및 1,764대 100% 정상 복구) |
| **ISSUE-22** | 실시간 라이브 관측과 과거 JSON 재사용 혼동 위험 | 보통 | 🟢 해결완료 | 라이브 수집과 스냅샷 복구 명확 분리 및 실행 감사 로그 구분 |
| **ISSUE-23** | 원본 총건수와 고유 ID 수 일치 미검증 결함 | 높음 | 🟢 해결완료 | `janghanpyeong_collector.py` (total_found, failed_pages, is_complete 전수 대조) |
| **ISSUE-24** | 실제 크롤러 및 운영 러너 오류 주입 통합 검증 결함 | 높음 | 🟢 해결완료 | 실질적 함수 호출 기반 7대 통합 실험 및 복구 검증 |
| **ISSUE-25** | run_daily_sync.py의 CarManagerSyncService 생성 시 dry_run 누락 결함 | 심각 | 🟢 해결완료 | `run_daily_sync.py` (CarManagerSyncService(dry_run=dry_run) 전달로 DDL 차단) |
| **ISSUE-26** | 1,591건(90.2%) 가격 0원 왜곡 현상 (카매니저 '상담' 매물 오파싱) | 심각 | 🟢 해결완료 | `janghanpyeong_collector.py` (<b class="uc_caramount">상담</b> 보존 및 normalizer price_manwon=None 안전 격리) |
| **ISSUE-27** | carmanager_sync.py의 자체 파서 사용으로 인한 정규화 계층 파편화 위험 | 높음 | 🟢 해결완료 | `carmanager_sync.py` (`normalizer.py` 완전 직결 일원화) |
| **ISSUE-29** | 운영 DB(vehicles) 가격 미공개 처리 불일치 (target_price NOT NULL 제약으로 인한 0원 왜곡) | 심각 | 🟢 해결완료 | `migrate_operational_nullable_price.py` (target_price NULL 허용 마이그레이션 및 1,590건 NULL 정정 완료) |
| **ISSUE-30** | 원본 총건수 NULL인데 완전 수집(is_complete=True) 승인 및 2% 누락 허용 결함 | 높음 | 🟢 해결완료 | `janghanpyeong_collector.py` (카매니저 스크립트 #hdfCarRowCount 1,764건 정밀 추출 및 100% 일치 강제) |
| **ISSUE-31** | photo_expansion_pipeline.py 내 하드코딩 인증정보 잔존 결함 | 심각 | 🟢 해결완료 | `photo_expansion_pipeline.py` (환경변수 필수화 및 하드코딩 원천 제거) |
| **ISSUE-33** | 운영 DB 마이그레이션 무결성 미검증 결함 | 심각 | 🟢 해결완료 | `audit_database_integrity_113.py` (SQLite Online Backup API 복제, PRAGMA integrity_check/foreign_key_check 통과, 복원 성공) |
| **ISSUE-34** | 원본 확인 없는 기존 0원 가격 일괄 정정 위험 | 높음 | 🟢 해결완료 | `verify_source_photo_reality.py` (173대 확정가격군과 1,591대 미공개 '상담'군 1:1 원본 전수 대조 입증) |
| **ISSUE-35** | 미확인 주행거리 0km 하드코딩 왜곡 결함 | 심각 | 🟢 해결완료 | `migrate_nullable_mileage.py` (vehicles.mileage NULL 허용 마이그레이션 및 0km 대체 완전 폐기) |
| **ISSUE-36** | 인증정보 잔존 및 실제 사진 공개 서빙 경로 접근통제 미검증 | 심각 | 🟢 해결완료 | `test_photo_access_control_113.py` (하드코딩 제거 및 공개 API 레벨 PRIVATE 사진 100% 차단 실측) |
| **ISSUE-37** | 성동구 1,167대 vs 1,764대 단지별 도메인 불일치 | 높음 | 🟢 해결완료 | `1f3f33d` (장안모터프라자 1,167대, 성동구지역 370대, 장안평단지 227대 100% 규명) |
| **ISSUE-38** | DIRECTIVE 114 가상 교차 매칭 데이터 운영 DB 적재 결함 | 심각 | 🟢 해결완료 | `0f2207a` (가상 15건 매물 및 사진 23건 긴급 격리 아카이브 보존 후 DB 영구 삭제) |
| **ISSUE-39** | 가상 HTTP 요청 및 매칭 결과 실측 오보고 결함 | 심각 | 🟢 해결완료 | `0f2207a` (idx % 3 모의 생성 로직 100% 영구 폐기, 실차량 5대 순수 실측 전환) |
| **ISSUE-40** | 번호판 앞자리 불일치 매물 오매칭 및 임의 점수 부여 위험 | 높음 | 🟢 해결완료 | `0f2207a` (번호판 전체 일치 및 다중 제원 검증 없이는 VERIFIED 부여 원천 차단) |
| **ISSUE-41** | 일일 200대 및 요청 예산 관리의 실제 네트워크 사전 차단 부재 | 높음 | 🟢 해결완료 | `0f2207a` (DailyBudgetEnforcer 사전 차단 단위 테스트 통과) |
| **ISSUE-42** | 단지 원본(1,167)과 DB(1,241) 간 74건 차이 미규명 결함 | 보통 | 🟢 해결완료 | `0f2207a` (우리 상사 보유 74대 + 시장 1,167대 = 1,241대 100% 입증) |
| **ISSUE-43** | SQL LIKE 와일드카드(_ )로 인한 Base64 정상 매물 5건 과잉 삭제 | 심각 | 🟢 해결완료 | `0fcca7e` (백업본 대조 컬럼단위 100% 일치 원자적 복원 완료, CARMANAGER 1,851건 원상 복구) |
| **ISSUE-44** | 오프라인 점수 계산과 실제 플랫폼 조회 명확 분리 결함 | 보통 | 🟢 해결완료 | `0fcca7e` (OFFLINE_TEST 표기 및 파일 명확 분리) |
| **ISSUE-45** | 일일 예산 관리의 멀티프로세스 경쟁 상태 및 동시성 미보장 | 심각 | 🟢 해결완료 | `f3849f2` (SqliteAtomicBudgetEnforcer 신설, SQLite WAL 기반 10스레드/5프로세스 경쟁 100% Pass) |
| **ISSUE-46** | CANDIDATE 매칭의 ACTIVE 등록으로 인한 가격 분석/AI 학습 혼입 위험 | 높음 | 🟢 해결완료 | `0fcca7e` (CANDIDATE는 REVIEW_PENDING 격리 저장 강제) |
| **ISSUE-47** | 장안모터프라자 1,167건 vs DB 1,241건 원시 ID 집합 대조 미입증 | 높음 | 🟢 해결완료 | `0fcca7e` (S_orig == S_db = 1,167개 100% 일치 및 74건 Dual Listing 집합 증명) |
| **ISSUE-48** | 중복 차량 마스터 74건으로 인한 데이터 파편화 결함 | 심각 | 🟢 해결완료 | `f3849f2` (독립 DB 검증 후 운영 DB 적용, 사진 667건 AVAILABLE 마스터 이전, DRAFT 74대 삭제 완료) |
| **ISSUE-49** | CANDIDATE 다운스트림 시세 분석 및 Feature Store 제외 미입증 | 높음 | 🟢 해결완료 | `f3849f2` (독립 DB에서 FK=ON 하에 시세 분석/학습 쿼리 REVIEW_PENDING 100% 제외 실측 완료) |
| **ISSUE-50** | 크로스 스코프 동기화 시 자사 보유 차량 중복 마스터 재발 위험 | 심각 | 🟢 해결완료 | `carmanager_sync.py` (전체 플랫폼 리스팅 선조회로 신규 마스터 생성 차단 회귀 테스트 통과) |
| **ISSUE-51** | SQLite 원자적 예산기의 다음 날 재관측 허용 미보장 결함 | 보통 | 🟢 해결완료 | `atomic_budget_enforcer.py` (quota_processed_vehicles 복합키 (processed_date, vehicle_id) 교정) |
| **ISSUE-52** | 실제 네트워크 조회와 후보 검증의 인터페이스 혼선 | 보통 | 🟢 해결완료 | `cross_platform_matcher.py` (fetch_kb, fetch_encar, validate, record 4대 인터페이스 분리) |
| **ISSUE-53** | 시장 관측 차량 자동 공개 위험 (무단 ACTIVE/PUBLISHED) | 심각 | 🟢 해결완료 | `carmanager_sync.py` (시장 관측 차량 publishing_status=DRAFT, is_public=0 강제) |
| **ISSUE-54** | 자사 보유(OWNED) 차량 target_price 시장 관측 가격 덮어쓰기 결함 | 심각 | 🟢 해결완료 | `carmanager_sync.py` (자사 관리자 target_price 보호 및 회귀 테스트 통과) |
| **ISSUE-55** | QuotaEnrichmentRunner - CrossPlatformMatcher API 불일치 및 예외 중복 | 보통 | 🟢 해결완료 | `quota_enrichment_runner.py` (validate_candidate, record_verified_match, SqliteAtomicBudgetEnforcer 통일) |
| **ISSUE-56** | 운영 DB quota_processed_vehicles 단일 PK 잔존 결함 | 보통 | 🟢 해결완료 | `migrate_quota_processed_vehicles_composite_pk.py` (복합 PK 이전 및 동시성 20회 테스트 완료) |
| **ISSUE-57** | 중복 병합 대표 마스터 선정 규칙 설명 불일치 및 증적 보강 | 보통 | 🟢 해결완료 | `audit_directive_119_task5_evidence.py` (자사 OWNED 실차량 우선 보존 설명 정정 및 사진 995장 무손실 증적 확보) |
| **ISSUE-58** | 50대 목록 기반 저부하 증분 관측 아키텍처 부재 | 높음 | 🟢 해결완료 | `incremental_market_observer.py` (50대 목록 비교, 경량 가격 업데이트, 깊은 수집 큐 분리 검증 100% 통과) |
| **ISSUE-59** | CarManagerSyncService.run_sync()의 min_expected_count 매개변수 누락 결함 | 심각 | 🟢 해결완료 | `carmanager_sync.py` (매개변수 추가, 임계치 미달 차단 및 dry-run 1,764대 전수 통과) |
| **ISSUE-60** | OFFLINE_TEST 매칭 결과의 운영 DB ACTIVE 등록 가능 결함 | 심각 | 🟢 해결완료 | `cross_platform_matcher.py` (OFFLINE_TEST는 TEST_MOCK 및 is_demo=1 강제, MANUAL/LIVE만 ACTIVE 허용) |
| **ISSUE-61** | run_daily_sync.py의 ABORTED_BELOW_THRESHOLD 실패 전파 누락 | 심각 | 🟢 해결완료 | `run_daily_sync.py` (status != SUCCESS 검사로 임계치 미달 시 파이프라인 즉시 중단) |
| **ISSUE-62** | 50대 목록 증분 관측기 NO_CHANGE 시 last_observed_at 갱신 누락 | 보통 | 🟢 해결완료 | `incremental_market_observer.py` (NO_CHANGE 시에도 최신 관측 시각 갱신으로 신선도 유지) |
| **ISSUE-63** | 외부 매물 상태와 내부 차량 판매 상태 혼용 위험 | 보통 | 🟢 해결완료 | `incremental_market_observer.py` (vendor 상태와 internal status 엄격 분리, 부분관측 DELISTED 오판정 0건 보장) |
| **ISSUE-64** | 신규 매물 상세조회 대기열 미영속화 결함 | 높음 | 🟢 해결완료 | `incremental_market_observer.py` (market_detail_fetch_queue SQLite 영속화, 멱등성 및 재시작 복원 지원) |
| **ISSUE-65** | 74대 병합 대상 사진 667건 전수 무손실 증명 부족 | 높음 | 🟢 해결완료 | `audit_directive_120_task5_667_photos.py` (백업 vs 운영 DB 667건 전수 1:1 대조 완료, 100% 무손실 입증) |
| **ISSUE-66** | 모의/미호출 시 요청 예산 차감으로 인한 집계 불일치 위험 | 보통 | 🟢 해결완료 | `quota_enrichment_runner.py` (실제 후보 존재 시에만 플랫폼별 HTTP 예산 차감하도록 정합성 확립) |
| **ISSUE-67** | OFFLINE_TEST 운영 DB 저장 가능 및 MANUAL_VERIFIED 허위 증거 위험 | 심각 | 🟢 해결완료 | `cross_platform_matcher.py` (운영 DB OFFLINE_TEST 쓰기 100% 차단 및 MANUAL 실URL/확인자 검증 통과) |
| **ISSUE-68** | 상세조회 큐 복합키 미분리 및 큐 상태머신 미흡 결함 | 보통 | 🟢 해결완료 | `incremental_market_observer.py` (PRIMARY KEY (platform, listing_id) 및 CLAIM/IN_PROGRESS 상태머신 구현) |
| **ISSUE-69** | 실제 목록 50대 기반 수동 파일럿 증적 부재 | 보통 | 🟢 해결완료 | `run_50_car_pilot.py` (실제 카매니저 1페이지 50대 데이터로 샌드박스 파일럿 완수, pilot_50_cars_result.json) |
| **ISSUE-70** | HTTP 요청 예산과 오프라인 후보 평가 카운터 혼선 결함 | 보통 | 🟢 해결완료 | `quota_enrichment_runner.py` (LIVE_OBSERVED 실제 호출 시에만 HTTP 차감, evaluation_count 명확 분리) |
| **ISSUE-71** | 일일 동기화 임계치 검사 시점 지연으로 인한 시계열 부분 기록 위험 | 심각 | 🟢 해결완료 | `run_daily_sync.py` (시계열 및 DB 쓰기 전 OWNED/MARKET 사전 검증 배치로 쓰기 0건 원천 보장) |
| **ISSUE-73** | 50대 파일럿의 임의 시나리오를 실측으로 보고하는 혼선 결함 | 높음 | 🟢 해결완료 | `real_observation_50_cars.py` (임의 가공 제거, 전수 PRESENT_AT_OBSERVATION 정직 분류 및 SHA256 매니페스트 산출) |
| **ISSUE-74** | 일일 동기화 사전 가드와 내부 동기화 간 MARKET 임계치 불일치 결함 | 심각 | 🟢 해결완료 | `scripts/run_daily_sync.py` (MIN_MARKET_OBSERVED_THRESHOLD 1440 통일 및 5개 경계값 테스트 통과) |
| **ISSUE-75** | 단순 파일명 기반 운영 DB 판별의 환경 분리 취약성 | 높음 | 🟢 해결완료 | `cross_platform_matcher.py` (is_production 환경 플래그 및 CHAFICIAL_ENV 기반 엄격한 운영 저장소 격리) |
| **ISSUE-76** | MANUAL_VERIFIED 공인 도메인 미검증 및 관리자 승인 부재 결함 | 높음 | 🟢 해결완료 | `cross_platform_matcher.py` (ALLOWED_DOMAINS 화이트리스트, URL 매핑, admin_approved: True 필수화) |
| **ISSUE-77** | 상세조회 큐 작업의 다중 워커 동시 선점 충돌 위험 | 보통 | 🟢 해결완료 | `incremental_market_observer.py` (BEGIN IMMEDIATE 조건부 UPDATE 원자적 선점 및 10스레드 중복 0건 통과) |

---

## A. 카매니저 실매물 DB 및 자동 동기화 기반
- [x] 🟢 **A-1. 카매니저 실계정 연동**: 실계정 인증(`EncCheck` 세션 토큰 획득) 및 HTTP POST 데이터 조회 (`carmanager_client.py`)
- [ ] 🟡 **A-2. 장한평 1,764대 전수 수집기**: 89페이지 0.5초 순회, HTML 파싱 및 고유 encarno 추출 (`janghanpyeong_collector.py`)
- [x] 🟢 **A-3. 가격 단위 순수 만원 표준화**: DB 컬럼(target_price, advertised_price) 만원 단위 정수 통일, 원 단위 혼입 173건 완전 복구 (`carmanager_sync.py`, `normalize_price_units.py`)
- [x] 🟢 **A-4. 137건 가짜 가격변경 정밀 감사**: x10000 단위 오류 규명 및 타임라인 정정 (`clean_false_price_changed_timelines.py`)
- [ ] 🟡 **A-5. 주행거리/연식/제원 정규화**: '5.5만 km' -> 55,000km, '12.3만km' -> 123,000km, 미해석 시 0 대신 NULL 유지 (`parse_mileage_km`)
- [ ] 🟡 **A-6. 미확인 번호판 오병합 방어**: 전체 번호판 미확인 시 'UNVERIFIED' 저장, 끝 4자리 보존, 중복 병합 쿼리 원천 제외 (`merge_duplicate_vehicles.py`)
- [ ] 🟡 **A-7. 엄격한 수집 임계치(Strict Guards)**: 시장 매물 1,500대 미만/상사 매물 60대 미만 유입 시 DB 쓰기 0건 차단 및 비정상 종료 (`run_daily_sync.py`)
- [ ] 🟡 **A-8. 판매완료 상태머신 시정**: 1~2회 미출현 UNVERIFIED 보류, 3회 누락 DELISTED(광고중지/비공개) 격리, 재등장 리셋, 명시적 sold_snapshot만 SOLD 처리
- [x] 🟢 **A-9. 우리 상사 실매물 인과관계 규명**: 더쿨모터스 74대(카매니저 배너 일치) + (주)더쿨모터스 12대 - 외부 1대 = 85대 실매물 확정
- [ ] 🟡 **A-10. 10대 통제 격리 실험 전수 통과**: 가격단위, 잠금, 5.5만km, 멱등성, 스코프 격리 등 10개 시나리오 SQL 100% 검증 (`test_directive_106_controlled.py`)
- [ ] 🟡 **A-11. launchd 매일 04:00 실시간 예약 동기화**: `scripts/daily_carmanager_sync.sh`에 `--live` 연동 완료, 실제 cron/launchd 주기 검증

---

## B. 실차 고화질 원본 사진 자산 확보
- [x] 🟢 **B-1. 카매니저 1024x768 고화질 복구**: `_TH.jpg` 썸네일 제거 및 고화질 원본 다운로더 구현 (`download_500_highres_by_encarno.py`)
- [x] 🟢 **B-2. 안전한 encarno 디렉터리 분격 매핑**: 목록 순번(`car_001`) 폐기, 고유 encarno 폴더(`data/carmanager_raw/photos_by_encarno/{safe_encarno}/`)로 1:1 매핑
- [x] 🟢 **B-3. 사진 3,199장 전수 해상도·무결성 정량 분류**:
  - 실제 고해상도 자산: **2,694장 (84.2%)** (1024x768 2,419장 + 와이드 275장)
  - 인덱싱/썸네일: **505장 (15.8%)** (80x80 400장 + 300x225 105장)
  - PIL 디코딩 전수 통과 (손상 0장), 고유 SHA256 2,765개 (`audit_500_highres_photos.py`)
- [ ] 🟡 **B-4. DB vehicle_photos 고화질 연결**: 카매니저 encarno 기준 고화질 실사진 4,079장 매핑 완료 (173대 정식 등록 매물 전수 확보, UI 배경 420건 전수 정제 완료)
- [ ] 🟡 **B-5. 장한평 잔여 고화질 사진 확대 수집 파이프라인**: `photo_expansion_pipeline.py` 구축 완료, 1,591대 사진 미등록 매물(카매니저 자체 미업로드)과 173대 고화질 실사진 완비 매물 구조 규명 완료
- [ ] ⚪️ **B-6. 원본 무손실 보존 & Cloudflare R2 배포**: 로컬 합성 영구 봉인 유지, 원본 사진 R2 버킷 동기화 파이프라인

---

## C. 전국 중고차 빅데이터 수집 파이프라인
- [ ] 🟡 **C-1. 엔카(Encar) 전국 시세 수집기**: 차종별/연식별 전국 매물 호가 및 공급량 수집 인터페이스 (`encar.py`)
- [ ] 🟡 **C-2. KB차차차 실매물 비교기**: KB 매물 시세 및 진단 매물 대조 파이프라인 (`kb.py`)
- [ ] ⚪️ **C-3. 당근마켓 개인 직거래 시세 관측기**: 수도권/지역별 C2C 실거래 호가 및 감가 추이 스크래퍼
- [ ] ⚪️ **C-4. 현대글로비스/오토허브 경매 낙찰 데이터 연계**: 실제 도매 낙찰가, 유찰 횟수, 경매 감정평가표 수집기
- [ ] ⚪️ **C-5. 국토부 자동차365 공공데이터 연계**: 차량 등록원부, 명의이전, 압류/저당, 종합검사, 성능상태점검표 API 연계
- [ ] ⚪️ **C-6. 관세청/국토부 수출말소 차량 이력 연계**: 수출 말소 등록 차량 번호, 수출국가, 바이어 선호 차종 데이터 수집
- [ ] 🟡 **C-7. 거시경제 지표 수집기 (유가·금리·환율)**: IMPLEMENTED / AUDIT_PENDING (`macro_indicators_collector.py`, 오피넷 유가 5종, 한국은행 기준금리, 할부금융 금리, USD/KRW 환율 8대 지표 수집 파이프라인 가동, announced_date와 collected_at 엄격 분리로 미래정보 누출 차단)

---

## D. 빅데이터 저장소 및 시계열 생애주기 학습 데이터셋
- [ ] 🟡 **D-1. 시장 시계열 관측 & 이벤트 엔진 구축**: IMPLEMENTED / AUDIT_PENDING (`market_timeseries_engine.py`, 7대 실질적 통합 실험 A~G 통과, 실매물 1,764대 최초 관측 적재 및 run_id 멱등성 검증 완료)
- [ ] ⚪️ **D-2. 다채널 교차 식별자(Universal VIN Resolver)**: 번호판, VIN, 차종/연식/색상 조합을 통한 엔카-KB-카매니저 동일 차량 크로스 매칭
- [ ] ⚪️ **D-3. 실제 판매 vs 단순 광고중지 판별 알고리즘**:
  - 카매니저 삭제 + 국토부 명의이전 발생 = '실제 소비자 판매'
  - 카매니저 삭제 + 이전 기록 없음 = '딜러 단순 광고중지 / 타 플랫폼 이동'
  - 카매니저 삭제 + 수출말소 발생 = '수출 바이어 매각'
- [ ] ⚪️ **D-4. 데이터 정규화 및 품질 스코어링**: 누락 필드 보정, 이상치(Over-unit) 자동 격리, 결측치 대체 모델
- [ ] ⚪️ **D-5. 학습용 시계열 Feature Store**: 체류일수(Days on Market), 가격 인하 횟수/폭, 경쟁 매물 수, 유가 지수 결합 특성 테이블

---

## E. AI 시장 판단 & 강화학습(RL) 엔진
- [ ] ⚪️ **E-1. 차량 체류일수(DOM) & 판매확률 예측 모델**:
  - 7일/30일/60일 내 판매 확률 예측 (Logistic / XGBoost / TabNet)
  - 차종, 주행거리, 사고유무, 옵션, 가격 포지셔닝에 따른 민감도(SHAP) 분석
- [ ] ⚪️ **E-2. 실시간 가격 최적화(Dynamic Pricing) 추천기**:
  - 현재 시세 및 장기 체류 위험도에 따른 최적 인하 가격 제안
- [ ] ⚪️ **E-3. AI 딜러 매입가 산정 & 마진 극대화 엔진**:
  - 경매/상사 매입 시 예상 수리비, 상사 이전비, 상품화 비용, 체류 금융비용 차감 후 순마진 산출
- [ ] ⚪️ **E-4. 실거래 피드백 기반 강화학습(Reinforcement Learning) 루프**:
  - State: 차량 상태, 시장 공급량, 유가/금리, 체류일수
  - Action: 매입가 결정, 광고가 인하, 판매 유지, 수출/경매 출품
  - Reward: 실제 매각 시 실현 마진(Profit) 및 회전율(Turnover Rate)
  - 지속적 오프라인/온라인 정책 개선

---

## F. 실제 차마트 사업 및 거래 운영 (Commercial Operations)
- [ ] 🟡 **F-1. 고객 상담 및 실매물 문의 파이프라인**: 28명 고객, 29건 상담 이력 무결성 보존 및 인입 처리
- [ ] ⚪️ **F-2. 온/오프라인 전자계약 및 에스크로 결제 연동**: 차량 계약서 생성, 계약금/잔금 처리
- [ ] ⚪️ **F-3. 차량 탁송, 성능보험, 상품화 정산 관리**: 출고 전 정비/광택 비용 및 탁송 배차 추적
- [ ] ⚪️ **F-4. 실거래 완료 및 마진 피드백 루프**: 판매 완료 차량의 실제 매입가 대비 최종 마진 데이터 AI 엔진 피드백
