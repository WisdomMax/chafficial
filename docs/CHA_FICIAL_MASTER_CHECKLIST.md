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
| **ISSUE-78** | 50대 원본 파서의 실제 필드 매핑 불일치로 인한 메타데이터 누락 | 심각 | 🟢 해결완료 | `audit_directive_123_task1_parser.py` (실제 필드 1:1 매핑, 번호판뒷자리/차종/연식/주행거리 100% 추출 성공) |
| **ISSUE-79** | 환경변수 조작에 의한 운영 저장소 쓰기 보호 우회 가능성 | 높음 | 🟢 해결완료 | `cross_platform_matcher.py` (os.path.realpath 기반 물리적 운영 DB 판별로 모의 데이터 쓰기 불변 차단) |
| **ISSUE-80** | MANUAL_VERIFIED의 URL 호스트네임 정밀 검증 및 서버 관리자 승인 부재 | 높음 | 🟢 해결완료 | `cross_platform_matcher.py` (urllib.parse 기반 ALLOWED_HOSTS 화이트리스트 및 admin_approval 딕셔너리 검증) |
| **ISSUE-81** | 상세조회 큐의 IN_PROGRESS 작업 워커 크래시 중단 복구 부재 | 보통 | 🟢 해결완료 | `incremental_market_observer.py` (recover_stale_in_progress_tasks로 중단 작업 PENDING 안전 복구 통과) |
| **ISSUE-82** | MANUAL_VERIFIED의 단순 딕셔너리 제출을 통한 비인가 승인 우회 위험 | 심각 | 🟢 해결완료 | `cross_platform_matcher.py` (DB 내 실제 admin_approvals 테이블의 APPROVED 레코드 물리적 검증 통과) |
| **ISSUE-83** | 상세조회 큐의 정상 실행 워커 방해 및 구 워커의 결과 덮어쓰기 결함 | 보통 | 🟢 해결완료 | `incremental_market_observer.py` (임대 만료(Lease Expiration) 기반 크래시 복구 및 claim_token 고유 발급/검증) |
| **ISSUE-84** | 원본 50대 연료 미표기 15건의 원본 누락 규명 및 데이터 무결성 보존 | 보통 | 🟢 해결완료 | `audit_directive_124_task3_fuel.py` (원본 fuel 빈문자열 100% 보존 및 fuel_inferred/confidence 분리 완료) |
| **ISSUE-85** | 실시간 50대 관측 미확보 시 가짜 차분 통계 생성 위험 | 높음 | 🟢 해결완료 | `datapart_page1_real.html` 4.6KB 셸 규명 및 REAL_PILOT_PENDING_NEW_CAPTURE 정직 분류 확립 |
| **ISSUE-86** | 일일 동기화 중간 실패 시 시계열/OWNED 부분 커밋(Dirty Commit) 위험 | 심각 | 🟢 해결완료 | `scripts/run_daily_sync.py` (단일 BEGIN IMMEDIATE 트랜잭션 롤백 및 스테이징 무결성 100% 검증 통과) |
| **ISSUE-87** | CrossPlatformMatcher 생성자의 임의 DDL 쓰기 및 관리자 승인 플랫폼/ID 미검증 | 심각 | 🟢 해결완료 | `cross_platform_matcher.py` (생성자 DDL 제거, 승인 DB platform/external_car_id 물리적 일치 강제) |
| **ISSUE-88** | 큐 재시도 경로 부재(FAILED 선점 불가) 및 claim_token 선택적 우회 취약점 | 높음 | 🟢 해결완료 | `incremental_market_observer.py` (FAILED 재선점 지원, claim_token 필수 강제 및 임대 유효성 검증) |
| **ISSUE-89** | 일일 동기화 MARKET 함수 내부 SQL 오류 시 롤백 및 트랜잭션 락 충돌 위험 | 심각 | 🟢 해결완료 | `scripts/run_daily_sync.py` (트랜잭션 진입 전 스키마 확인, MARKET 내부 실제 오류 롤백 100% 입증) |
| **ISSUE-90** | 근거 약한 차량의 연료 임의 가솔린 추측 왜곡 결함 | 보통 | 🟢 해결완료 | `audit_directive_124_task3_fuel.py` (스타렉스/CLS 2건 UNKNOWN(conf:0.0) 보정, 4.7KB 빈 셸 Git 동기화) |
| **ISSUE-91** | 일일 동기화 기본 실행의 89페이지 고속 실시간 수집 활성화 결함 | 높음 | 🟢 해결완료 | `scripts/run_daily_sync.py` (기본값 안전 검증 모드 전환, --live 플래그 명시 시에만 네트워크 가동) |
| **ISSUE-92** | 과거 스냅샷(`janghanpyeong_full_collection.json`)의 운영 DB 오염 및 동일 원본 이벤트 중복 결함 | 심각 | 🟢 해결완료 | `run_daily_sync.py`, `market_timeseries_engine.py` (HISTORICAL_REPLAY 강제 및 raw_sha256 중복 이벤트 차단) |
| **ISSUE-93** | 관리자 승인 platform / external_car_id NULL 허용 보안 취약점 | 보통 | 🟢 해결완료 | `cross_platform_matcher.py` (NULL/빈값 무조건 승인 거부, 승인 레코드 100% 필수 일치 강제) |
| **ISSUE-94** | 상세조회 큐 FAILED 항목 무제한 즉시 재선점 및 lease_expires_at NULL 우회 결함 | 높음 | 🟢 해결완료 | `incremental_market_observer.py` (next_retry_at 백오프 부여, lease_expires_at NULL 엄격 차단) |
| **ISSUE-95** | 카매니저 실시간 T2 관측 원본(50대) 미확보 상태 규명 | 보통 | 🟡 관측대기 | `datapart_page1_real.html` 4.7KB 빈 셸 확인, 신규 캡처 페이로드 대기 상태(REAL_PILOT_PENDING_NEW_CAPTURE) 정직 유지 |
| **ISSUE-96** | 일일 동기화 파이프라인 db_path 하드코딩으로 인한 독립 테스트 격리 실패 | 보통 | 🟢 해결완료 | `scripts/run_daily_sync.py` (db_path 파라미터 완전 존중, 외부 HTTP 0건 보장 통합 테스트 완료) |
| **ISSUE-97** | 글로벌 원본 해시 중복 차단으로 인한 다음 날 연속 관측(Days on Market) 누락 결함 (P0) | 심각 | 🟢 해결완료 | `market_timeseries_engine.py` (동일 관측 세션 재전송만 차단, 일자별 연속 관측 정상 적재 및 0 변동 이벤트 입증) |
| **ISSUE-98** | 과거 스냅샷 방어의 DB 파일명 의존 취약점 | 보통 | 🟢 해결완료 | `scripts/run_daily_sync.py` (파일명과 무관하게 HISTORICAL_REPLAY 모드의 라이브 커밋 100% 차단) |
| **ISSUE-99** | 출처 없는 수집 시각 임의 하드코딩 날짜 왜곡 결함 | 낮음 | 🟢 해결완료 | `scripts/run_daily_sync.py` (임의 날짜 하드코딩 배제, UNKNOWN 유지) |
| **ISSUE-100** | 큐 재시도 대기 선형 백오프 지적에 따른 지수 백오프 전환 | 보통 | 🟢 해결완료 | `incremental_market_observer.py` (60s, 120s, 240s 지수 백오프 공식 적용) |
| **ISSUE-101** | 롤백 테스트 위양성(assert False 취약점) 및 세부 필드(가격·상태·관측시각) 불변성 검증 부재 | 보통 | 🟢 해결완료 | `test_directive_126_task4_pipeline_integration.py`, `test_directive_126_task1_replay_guard.py` (1,764/1,764대 전수 불변 검증) |
| **ISSUE-102** | 과거 스냅샷 재생 시 가격/상태/last_observed_at/unverified count 역행 및 신규 마스터 오등록 위험 (P0) | 심각 | 🟢 해결완료 | `carmanager_sync.py` (HISTORICAL_REPLAY 모드에서 target_price, advertised_price, last_observed_at, unverified count 갱신 및 신규 마스터 등록 완전 차단, 6대 회귀 테스트 100% 통과) |
| **ISSUE-103** | allow_historical_test_commit 플래그의 운영 DB 연결 경계 취약점 (P0) | 심각 | 🟢 해결완료 | `scripts/run_daily_sync.py` (운영 DB(chamart_platform_demo.db) 경로 판별 시 allow_historical_test_commit 여부와 무관하게 쓰기 100% 차단 및 DRY_RUN=True 강제) |
| **ISSUE-104** | source_capture_id 및 메타데이터 부재로 인한 동일 원본 재실행과 실제 재관측 구분 불가 결함 | 높음 | 🟢 해결완료 | `market_timeseries_engine.py` (source_capture_id, source_capture_at, imported_at, observation_scope, observation_mode 분리 저장, 동일 capture_id 3회 재전송 시 1회 적재 멱등성, 다른 날짜 새 capture_id 시 2회 정상 적재 및 0 변동 이벤트 입증) |
| **ISSUE-105** | 원본 수집 시각 부재 시 현재 시각으로 임의 승격 위험 및 부분 목록 관측의 허위 DELISTED 산출 결함 | 높음 | 🟢 해결완료 | `market_timeseries_engine.py` (source_capture_at NULL 엄격 유지 및 현재 시각 승격 0건, is_partial=True 및 부분 목록 관측 시 DELISTED/SOLD 산출 0건 가드 적용) |
| **ISSUE-106** | 실제 T2 장한평 50대 목록 수동 캡처 인수인계 표준 절차 및 차분 도구 부재 | 보통 | 🟢 해결완료 | `docs/CARMANAGER_T2_MANUAL_CAPTURE_GUIDE.md`, `scripts/run_manual_t2_ingest.py` (7단계 SOP 확립, 5대 필수 지표 출력 파이프라인 완비, T2 원본 부재 시 REAL_PILOT_PENDING_NEW_CAPTURE 정직 유지) |
| **ISSUE-107** | `run_manual_t2_ingest.py` HTML 형식 오인 및 메타데이터 SHA256 미검증 결함 | 보통 | 🟢 해결완료 | `scripts/run_manual_t2_ingest.py` (HTML UNSUPPORTED_FORMAT 명시 거부, 메타데이터 필수화 및 SHA256 대조 강제, 6대 정밀 테스트 100% 통과) |
| **ISSUE-108** | 운영 DB 판별의 문자열 매칭(`test`, `tmp`, `sandbox` 부재 검사) 취약점 | 보통 | 🟢 해결완료 | `scripts/run_daily_sync.py`, `carmanager_sync.py` (`os.path.realpath` canonical 정확 일치 판별로 전환) |
| **ISSUE-109** | 실제 T2 수동 인계 대기 상태(`REAL_PILOT_PENDING_NEW_CAPTURE`) 전환 및 추가 기능 확장 동결 | 보통 | 🟢 해결완료 | T2 원본 확보 전까지 신규 크롤러/Feature Store/RL 개발 동결 및 수동 인계 대기 상태 고정 |

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

---

## G. Cloudflare 차마트 운영 및 차피셜 DB 동기화 (DIRECTIVE 130 / 131)

- [ ] 🟡 **G-1. Cloudflare 운영 DB 및 배포 환경 감사**: 로컬 SQLite(1,801대) 및 D1(168대 실차, 100대 격리) 스키마·데이터 전수 감사, SQL 풀 백업(2.8MB) 생성 및 복원 100% 무결성 검증 완료
- [ ] 🟡 **G-2. 더미 데이터 격리 및 정리**: 100대 가상 데모 차량 및 2,000장 가상 사진을 `quarantined_*` 테이블로 안전 격리 완료, 본 테이블 실차량 168대 및 상담 30건, 거래 37건 100% 보존
- [ ] 🟡 **G-3. 실제 차량 사진 정합성 확보**: 모델명 기반 임의 사진 매핑(`resolveRealCarPhoto`) 및 가상 30장 생성기 완전 폐기, 실제 승인 사진만 노출하고 부재 시 정직한 '사진 준비 중' SVG 적용
- [ ] 🟡 **G-4. 차마트 우선 노출 4단계 적용**: (1) 차마트 직영+실사진 (2) 차마트 직영+사진없음 (3) 타사+실사진 (4) 타사+사진없음 4단계 티어 우선 쿼리 및 프론트엔드 연동 (감독관 독립 승인 대기 유지)
- [ ] 🟡 **G-5. 원자적 멱등성 및 동기화 보안 (ISSUE-110, ISSUE-115, ISSUE-124, ISSUE-125)**: 전용 D1 테이블 `sync_idempotency_keys` 구축, PK 충돌 기반 원자적 락 획득, Fencing Token 및 임대 만료 가드, 키 누락 시 400 거부, 동일 키/동일 페이로드 캐시 리플레이(중복 연산 0건), 상이 페이로드 409 거부 (감독관 독립 승인 대기 유지)
- [ ] 🟡 **G-6. 자동 증분 동기화 및 복구 (ISSUE-114, ISSUE-116, ISSUE-132, ISSUE-133, ISSUE-134, ISSUE-135)**: 서버 기반 상사 인가 테이블(`dealers`), 정식 번호판 정규식 엄격 검증, SOLD 차량 재공개 차단 가드 및 Mac mini 지속 자동 동기화 데몬(`ContinuousSyncDaemon`) 완성 (감독관 독립 승인 대기 유지)
- [ ] 🟡 **G-7. 고객 공개 정보 진실성 및 접근 제어 (ISSUE-111, ISSUE-112, ISSUE-113)**: 상세페이지 가상 보증(무사고/침수/시세80만원차액) 전면 삭제 및 '진단 대기' 정직한 표기, 비공개 매물 상세 직접 접근 시 404 차단, 신규 동기화 매물 무조건 `is_public=0` 강제
- [ ] 🟡 **G-8. 실제 운영 환경 통합 검증**: Cloudflare Pages 프로덕션(`main` 브랜치) 배포, `https://chamart.cc` 및 `https://chamart.pages.dev` 실서버 엔드투엔드 브라우저 렌더링 검증 (목록 카드 높이 104px 슬림화)
- [ ] 🟡 **G-9. AI 자동등록 확장 기반**: `ai_vision_analysis_json`, `ai_recommended_primary_photo`, `ai_confidence_score`, `ai_review_status` 등 GPT 비전 다중 업로드 및 자동등록 확장 스키마 마이그레이션 완료

---

## H. DIRECTIVE 130 / 131 독립 감사 및 결함 조치 이력 (Audit Remediation)

### 1. DIRECTIVE 130 1차·2차 독립 감사 결함 전수 조치 현황 (ISSUE-110 ~ ISSUE-116)
- **ISSUE-110 [P0 보안 - 기본 인증 토큰 하드코딩 노출]**:
  - 조치: `_worker.js` 및 `chamart_sync_client.py` 내 `DEFAULT_SYNC_TOKEN` 전면 삭제. `env.SYNC_API_KEY` 미설정 또는 16자 미만 시 즉시 401 Unauthorized 차단.
- **ISSUE-111 [P0 진실성 - 상세페이지 허위 정보 생성]**:
  - 조치: 실제 카히스토리/성능점검부 미확인 매물에 대한 가상 `is_accident_free: true`, `total_loss: false`, `시세 대비 80만원 저렴` 날조 하드코딩 전면 삭제. 데이터 부재 시 `null`, `'성능점검 서류 확인 대기'`, `'실차 진단 및 정밀 시세 분석 대기'` 정직한 표기 적용.
- **ISSUE-112 [P0 접근 제어 - 비공개 차량 상세 URL 접근]**:
  - 조치: 상세 API에 `WHERE id = ? AND is_public = 1 AND is_demo = 0 AND (publishing_status = 'APPROVED' OR publishing_status = 'PUBLISHED' OR publishing_status IS NULL) AND status IN ('AVAILABLE', 'FOR_SALE')` 엄격 적용. 미승인·더미·판매완료 매물 직접 접근 시 404 Not Found 반환.
- **ISSUE-113 [P0 노출 제어 - 신규 차량 자동 공개 경로]**:
  - 조치: 클라이언트 페이로드 전송값과 무관하게 신규 동기화 차량은 무조건 `is_public = 0` (비공개) 강제 고정. 관리자 직접 검토/승인 전 노출 원천 봉쇄.
- **ISSUE-114 [P1 일관성 - 판매완료 시 비공개 미전환 및 임의 상태값]**:
  - 조치: 허용 상태 화이트리스트(`['AVAILABLE', 'FOR_SALE', 'RESERVED', 'SOLD', 'SUSPENDED', 'DELETED', 'INACTIVE']`) 검증 도입. `SOLD`, `SUSPENDED`, `DELETED`, `INACTIVE` 수신 시 `is_public = 0` 자동 전환.
- **ISSUE-115 [P0 신뢰성 - 멱등성 서버 검증 부재 및 동시성 경합]**:
  - 조치: 전용 테이블 `sync_idempotency_keys` 구축, PK 충돌 기반 원자적 락 획득 메커니즘 실장. 키 누락 시 400 거부, 동일 키/동일 페이로드 완료 건 즉시 캐시 리플레이(중복 INSERT 0건), 상이 페이로드 409 충돌 차단. 동일 요청 10개 동시 실행 race condition 단위 테스트 통과.
- **ISSUE-116 [P1 소유권 - 차피셜 동기화의 관리자 필드 침범]**:
  - 조치: `UPDATE vehicles` 시 `target_price`(관리자 판매가), `is_public`(공개 여부), `listing_ownership_type`(직영 소속 여부)을 UPDATE 구문에서 완전 제외. 운영 DB의 관리자 고유 권한 100% 보존.

### 2. DIRECTIVE 131-R / P0 HOTFIX-A 결함 조치 이력 (ISSUE-117 ~ ISSUE-120)
- **ISSUE-117 [P0 시연 잔존 - 제네시스 GV70 (073서 7777) 가상 매물 운영 D1 최상단 노출]**:
  - 원인: 과거 시연용 등록 매물이 `is_demo=0`, `is_public=1`, `priority_rank=100`, `publishing_status='APPROVED'`로 남아있어 차마트 1위 노출.
  - 조치: 차량 ID `76d8576a-5c6f-4555-b9f0-89db74cb30b8` 단건 지정을 통해 `is_demo=1`, `is_public=0`, `publishing_status='UNPUBLISHED'`, `priority_rank=0`으로 안전 비공개 격리 완료. 변경 전 D1 백업(3.0MB) 및 레코드 감사 JSON 확보. 상세 URL 직접 조회 시 404 차단 검증.
- **ISSUE-118 [P0 노출 정책 - `publishing_status IS NULL` 허용 및 허위 기본값 누수]**:
  - 원인: 목록/상세 API SQL에 `publishing_status IS NULL` 허용문 잔존으로 미승인 차량 노출 여지 발생, 신규 등록 시 `displacement_cc=1999`, `drive_type='2WD'`, `year-01-01` 등 허위 기본값 저장.
  - 조치: 목록 및 상세 API에 `publishing_status IN ('APPROVED', 'PUBLISHED')` 필수화(`IS NULL` 완전 제거). 신규 등록 시 미확인 제원은 전부 `null` 저장.
- **ISSUE-119 [P0 사진 정합성 - 가상 에셋의 실차 사진 오판별 및 하드코딩 무사고 태그]**:
  - 원인: `isValidPhoto()`가 단순 문자열 일부만 체크하여 `/static/img/ui_fixtures/`, `/static/img/vehicles/` 등을 실차 사진으로 인정, 프론트엔드 카드에 무조건 '무사고' 배지 하드코딩.
  - 조치: `isValidRealVehiclePhoto()`로 개편하여 시연·픽스처·더미 에셋 전면 차단, 실제 수집 사진(`http://`, `https://`)만 허용하고 부재 시 정직한 `no_photo.svg` 강제. 프론트엔드 카드 하드코딩 무사고 태그 전면 삭제.
- **ISSUE-120 [P0 멱등성 실패 복구 & 엣지 캐시 즉시 만료]**:
  - 원인: `sync_idempotency_keys`에서 `FAILED` 키 재선점 불가, 엔드포인트 상이 시 미검증, 목록 API 엣지 캐시(60초)로 판매완료 즉시 미반영.
  - 조치: 엔드포인트 상이 시 `409 IDEMPOTENCY_ENDPOINT_MISMATCH`, `status='FAILED'` 원자적 재선점 허용, 60초 초과 stale lock 재선점 구현. 목록 API `Cache-Control: public, max-age=0, must-revalidate` 적용. D1 마이그레이션 `0002_directive_131_idempotency.sql` 배포.

### 3. DIRECTIVE 131-R / HOTFIX-B 결함 조치 이력 (ISSUE-121 ~ ISSUE-124)
- **ISSUE-121 [P0 상세정보 진실성 - 미확인 제원 기본값 및 가상 보증 문구 잔존]**:
  - 조치: `_worker.js` 및 `functions/api/chamart/vehicles/[id].js` 내 배기량(1999cc), 구동방식(2WD), 연초일(`year-01-01`), 침수·전손 보증, 무사고 하드코딩 전면 삭제. 미확인 정보는 전부 `null` 또는 `'실차 진단 및 상세 조건 확인 대기'`로 통일.
- **ISSUE-122 [P0 비교 화면 가상 에셋 누수 - `ui_fixtures/아반떼_01.jpg` 대체 사진]**:
  - 조치: 차량 비교 모달 렌더러 내 하드코딩 대체 이미지 `/static/img/ui_fixtures/아반떼_01.jpg`를 전면 삭제하고 `resolveFrontendCarPhoto(v)`를 적용하여 정직한 `no_photo.svg` 강제.
- **ISSUE-123 [P0 공개 권한 검증 - 4대 시연 매물 출처 미확인 비공개 전환]**:
  - 조치: D1 공개 승인 매물 4대(`88오 1512`, `99다 3635`, `77조 7788`, `88오 5001`) 전수 검사 결과 상사/직영 판매 권한 미증명 매물로 확인되어 `is_public = 0`, `publishing_status = 'PENDING_REVIEW'`로 안전 격리. 공개 목록 내 가상·미확인 매물 노출 0건 입증.
- **ISSUE-124 [P0 멱등성 락 지연 완료 덮어쓰기 방어 (Optimistic Locking Guard)]**:
  - 조치: 60초 임대 만료 후 구 작업자의 지연 완료 처리가 신규 작업자를 덮어쓰지 못하도록 `WHERE idempotency_key = ? AND status = 'IN_PROGRESS' AND updated_at = ?` 조건부 갱신 강제. stale worker overwrite 원천 차단.

### 4. DIRECTIVE 132: 최종 운영 안전성 검증 및 차마트 실매물 시범 등록 (ISSUE-125 ~ ISSUE-127)
- **ISSUE-125 [P0 멱등성 완성 - Fencing Token & Lease Expiry Guard]**:
  - 조치: 60초 임대 만료 후 구 작업자의 지연 완료 시 `completeRes.meta.changes === 0` 검증 도입하여 성공 응답 반환 금지(`409 IDEMPOTENCY_LEASE_EXPIRED`). `FAILED` 전환도 현재 락 소유자(`activeLockUpdatedAt`)만 갱신 가능하도록 엄격화.
- **ISSUE-126 [P0 운영 무결성 - Cloudflare 배포 식별자 및 Git 추적성 실측]**:
  - 조치: `scripts/verify_directive_131_full.py` 동적 타임스탬프 및 커밋 해시 자동 주입, Cloudflare Pages 배포 식별자(`35791b91`) 및 Git 커밋 1:1 대응 검증.
- **ISSUE-127 [P0 실매물 시범 등록 - 카매니저 실매물 5대 선별 및 승인 대기열 적재]**:
  - 조치: 장한평 전시장 (주)더쿨모터스 실매물 1호 `64노3143` (랜드로버 디스커버리 스포츠 1,090만원, 제시번호 2026099548, 실차 사진 9장 완비) 100% 검증 완료. 후보 2~5호(벤츠 E-클래스, 스타리아, G80, 랭글러) 가격/사진 등록 대기열 편성(`reports/DIRECTIVE_132_REAL_VEHICLE_CANDIDATES.json`). 사용자 최종 승인 전 비공개 안전 유지.

### 5. DIRECTIVE 132-A: 실매물 1호 공개 직전 승인 게이트 이행 (ISSUE-128 ~ ISSUE-130)
- **ISSUE-128 [P0 실매물 1호 승인 게이트 - (주)더쿨모터스 판매 권한 검증 및 D1 비공개 스테이징]**:
  - 조치:
    1. **판매 권한 및 제원 검증**: (주)더쿨모터스(장안모터프라자) 위탁 매물 `64노3143`(제시번호 `2026099548`), 카매니저 실차 사진 9장 권한, 판매가 1,090만원, 차대번호 `SALCA2BN5JH761441`, 최초등록일 `2018-09-14`, 저당 정보는 KB차차차 저당 1건 확인에 따라 '자동차등록원부(을부) 조회 대기'로 정직하게 보존.
    2. **D1 비공개 스테이징**: 원격 D1 DB에 중복 없이 등록 완료 (`id = 'e6670a2e-c532-435e-b34a-b4a3ff9a677c'`, `is_public = 0`, `publishing_status = 'PENDING_REVIEW'`, `is_demo = 0`, `listing_ownership_type = 'EXTERNAL'`).
    3. **제시번호 & 실차 사진 9장 매핑**: `vehicle_listings` 제시번호 `2026099548` 1:1 매핑, `vehicle_photos` 카매니저 정식 실차 사진 9장 등록 완료 (`approval_status = 'PENDING'`, `public_visibility = 'PRIVATE'`).
    4. **고객 API 미노출 검증**: `GET /api/chamart/vehicles` 응답 0건(`[]`) 유지, 상세 API `GET /api/chamart/vehicles/e6670a2e...` 404 차단 실측 완료.
    5. **사용자 승인 게이트**: 사용자 명시적 최종 승인 전까지 `is_public=0` 엄격 유지.
- **ISSUE-129 [P0 사진 승인 분리 결함 - 미승인 사진 고객 노출 차단 및 승인 사진 기반 4단계 정렬]**:
  - 원인: `is_public = 1` 전환 시 `vehicle_photos`의 `approval_status` 미검증으로 `primary_photo_url`에 존재하는 미승인 사진이 고객에게 노출될 수 있는 아키텍처 결함.
  - 조치:
    1. **목록/상세 API 사진 승인 강제**: `vehicle_photos.approval_status = 'APPROVED'` 및 `public_visibility = 'PUBLIC'` 조건 충족 사진만 조회·노출.
    2. **미승인 사진 fallback 완전 삭제**: 상세 API에서 `primary_photo_url` 우회 로직을 영구 삭제하고, 승인 사진이 0장이면 예외 없이 `no_photo.svg` 렌더링.
    3. **4단계 정렬 승인 사진 기준 개편**: 4단계 노출 순위(차마트+사진있음 등)를 `vehicle_photos` 내 승인 실사진 유무 서브쿼리로만 계산하도록 SQL 전면 개편.
    4. **단위 테스트 완비**: 9장 중 1장 미승인 시 8장만 반환, 0장 승인 시 fallback, 4단계 정렬 순위 100% 통과(`tests/test_directive_132_a_photo_approval.py`).
    5. **저당 정보 정직성 확보**: KB차차차 저당 1건 표기 이력을 반영하여 성급한 '저당 없음' 기재를 폐기하고 '자동차등록원부(을부) 조회 대기'로 정정.
- **ISSUE-130 [P0 상사 진실성 - EXTERNAL 매물 직영 오표기 차단 및 임의 전화번호/주소 고정값 영구 삭제]**:
  - 원인: 목록/상세 API에서 모든 차량에 `branch_name: '차마트 장한평 본사 직영점'`, 고정 연락처 `02-2244-8800`이 하드코딩되어 제휴 상사 위탁 매물이 직영으로 오안내되는 결함.
  - 조치:
    1. **판매 상사와 직영 역할 명확 분리**: `listing_ownership_type`이 `OWNED`/`CHAMART_OWNED`일 때만 직영 표기, `EXTERNAL` 매물은 `vehicle_listings` 테이블의 실제 상사명(`(주)더쿨모터스`) 및 제휴 상사 표기 강제.
    2. **허위 대표번호/고정 주소 전면 삭제**: `dealer_info.contact: null`, 주소는 DB의 실제 `raw_seller_location` 연동, 플랫폼 역할(`차마트 온라인 중개 플랫폼`) 명시.
    3. **단위 테스트 추가**: EXTERNAL vs OWNED 상사명/지점명 분리 검증 100% 통과.
- **ISSUE-131 [P0 상사 소재지 예외 고정값 완전 삭제 및 최종 상용 게이트 종결]**:
  - 조치: 제휴 상사 소재지 fallback에서 하드코딩 주소를 제거하고 `null` 또는 `'소재지 확인 대기'`로 통일. 전체 감사 기록 정합성 일치 및 사용자 최종 공개 결정 대기열 유지.

### 6. DIRECTIVE 133: 카매니저·차피셜·차마트 실매물 자동 연동 완성 (ISSUE-132 ~ ISSUE-134)
- **ISSUE-132 [P0 실매물 DB 연동 - 카매니저 더쿨모터스(74대) 전수 검증 및 확정 실매물 36대 식별]**:
  - 원인: 차마트 공개 매물이 0대인 원인은 D1 내 `publishing_status IN ('APPROVED', 'PUBLISHED')` 매물이 전무하고 시연 매물이 전면 비공개 격리되어 있었기 때문.
  - 조치:
    1. 카매니저 원시 데이터(장한평 74대) 및 직영 계정(13대) 전수 분석 결과, 13대 전체가 74대 내 1:1 일치 포함됨을 규명.
    2. 확정 판매 가격이 등록된 실매물 36대(실매물 1호 `64노3143` 포함) 및 가격 미확정('상담') 매물 38대로 정확히 분리.
    3. 시장 조사용 1,801대 관측 데이터와 판매 권한 보유 상사 매물을 엄격히 분리하여 D1에 1:1 매핑 적재.
- **ISSUE-133 [P0 상사 단위 지속 동의 - 제휴 상사 실매물 자동 승인(36대) 및 상담 매물(38대) 비공개 안전 격리]**:
  - 조치:
    1. (주)더쿨모터스 상사 단위 지속적 게시 동의(Continuous Dealer Consent) 정책을 `_worker.js` 동기화 엔진에 실장.
    2. 확정 가격 판매중 매물 36대에 대해 반복 사용자 승인 없이 `is_public = 1, publishing_status = 'APPROVED', listing_ownership_type = 'EXTERNAL'` 자동 게시 적용.
    3. 가격 미확정(상담) 38대 매물은 `is_public = 0, publishing_status = 'PENDING_REVIEW'`로 비공개 안전 격리.
    4. 카매니저 실차 사진 35대 `approval_status = 'APPROVED', public_visibility = 'PUBLIC'` 자동 승인 등록, 사진 없는 1대는 정직한 `photo_count = 0, primary_photo_url = 'no_photo.svg'`(사진 준비 중) 처리.
    5. 실매물 1호 `64노3143`의 9장 실차 사진(카매니저 정식 수집본) 전원 `APPROVED/PUBLIC` 승인 완료.
- **ISSUE-134 [P0 실시간 양방향 동기화 - 가격 변경 반영, 판매 완료(SOLD) 즉시 비공개 전환 및 고객 문의 연동]**:
  - 조치:
    1. 15대 단위 안전 청크 전송 파이프라인(`scratch/run_directive_133_sync.py`) 구축으로 74대 전원 무결성 갱신 완료 (`inserted=0, updated=74`).
    2. 실측 검증: 가격 변경(`950만원 -> 930만원`) 증분 전송 시 D1 실시간 반영 확인 (`updated = 1`).
    3. 실측 검증: 판매 완료(`status = 'SOLD'`) 전송 즉시 `is_public = 0, publishing_status = 'UNPUBLISHED'` 비공개 전환 확인 (`unpublished = True`).
    4. 실측 검증: 테스트 차량 정상 가격(950만원) 및 정상 판매 상태(`FOR_SALE, is_public=1`) 복구 완료.
    5. 차마트 웹 접수 고객 상담 30건을 차피셜 운영 관리 화면으로 안전하게 전달하는 `/api/sync/consultations` GET 엔드포인트 구축 및 정상 인입 검증.
    6. 가상 매물(GV70 `073서 7777`) 재노출 0건 회귀 검증 완료.

### 7. DIRECTIVE 133-R: 실매물 36대 공개 데이터 무결성 및 자동 연동 최종 보정 (ISSUE-135 ~ ISSUE-138)
- **ISSUE-135 [P0 안전 복원 - 실매물 1호 64노3143 및 임시 번호판 35대 비공개 원상 복원]**:
  - 원인: 실매물 1호 `64노3143`의 사용자 명시 승인 게이트 우회 노출 및 `더쿨-XXXX` 임시 식별자 사용 35대의 성급한 자동 공개 승인 결함.
  - 조치:
    1. D1 원격 마이그레이션(`0003_directive_133_r_safety_and_dealers.sql`)을 통해 `64노3143` 즉시 `is_public = 0, publishing_status = 'PENDING_REVIEW'`, 사진 10장 `PENDING/PRIVATE`로 안전 복원.
    2. `더쿨-XXXX` 임시 번호판 매물 35대 전원 데이터 보존 방식의 `is_public = 0, publishing_status = 'PENDING_REVIEW'` 비공개 안전 격리 완료.
    3. 운영 D1 공개 차량 0대(`approved_count = 0`) 원상 회복 실측 완료.
- **ISSUE-136 [P0 상사 동의 구조 개편 - 클라이언트 선언 불신 및 서버 D1 dealers 인가 테이블 검증]**:
  - 원인: 클라이언트 페이로드의 `dealer_consented=True` 또는 상사명 단순 문자열 체크만으로 자동 승인하는 취약한 아키텍처.
  - 조치:
    1. D1 `dealers` 테이블에 (주)더쿨모터스(`dealer-thecool-motors`, `ACTIVE`, 계약일 `2026-10-01`) 정식 인가 레코드 등록.
    2. `_worker.js`에서 클라이언트 플래그를 완전 무시하고 서버 D1 `dealers` 테이블의 `ACTIVE` 등록 여부를 SQL로 직접 대조 검증.
    3. 정식 번호판 정규식(`^\d{2,3}[가-힣]\d{4}$`) 검증 도입: `더쿨-XXXX` 등 임시/가상 번호판 자동 공개 원천 차단.
    4. 실매물 1호 `64노3143` 전용 게이트 가드: 동기화 시도 시에도 사용자 명시 승인 전까지 무조건 `PENDING_REVIEW` 및 비공개 강제.
    5. 단위 테스트 완비: `tests/test_directive_133_r_safety_rules.py` 6개 케이스 100% 통과.
- **ISSUE-137 [P0 데이터 소유권 및 상태 보호 - SOLD 차량 재공개 차단 및 제원 날조 금지]**:
  - 원인: 과거 스냅샷 재전송 시 판매완료(SOLD) 차량이 다시 공개될 수 있는 취약점 및 누락 제원에 임의 기본값(2020년, 0km, 가솔린) 주입.
  - 조치:
    1. `_worker.js`에 SOLD 상태 전이 가드 실장: `existing.status === 'SOLD' || existing.publishing_status === 'UNPUBLISHED'`인 매물은 관리자 승인 없이 동기화로 재공개 절대 불가(`status = 'SOLD'` 영구 보존).
    2. 제원 날조 금지: 누락된 연식, 주행거리, 연료, 미션, 색상은 기본값 대체 없이 엄격히 `null`로 저장.
- **ISSUE-138 [P1 지속 자동 동기화 실증 - Mac mini 증분 데몬 및 격리 프로브 검증]**:
  - 조치:
    1. Mac mini 백그라운드 동기화 데몬 엔진 `src/chaficial/platform/sourcing/continuous_sync_daemon.py` 구축.
    2. 변경 차량만 감지하는 MD5 요약 해시 기반 증분 비교 로직 및 영구 로깅(`data/sync_daemon.log`) 구현.
    3. 운영 차량 훼손 방지를 위한 격리 프로브(`TEST-PROBE-DIRECTIVE-133`) 검증 완료: 가격 변경(`1500->1450`), 판매완료(`SOLD`), 스냅샷 재전송 재공개 차단, 최종 정리(`DELETED`) 100% 실측 통과.

### 8. DIRECTIVE 134: 실제 판매 매물 복구 및 자동 동기화 운영 실증 (ISSUE-139 ~ ISSUE-142)
- **ISSUE-139 [P0 프로덕션 안전 결함 긴급 수정 - 테스트 식별자 원천 차단 및 D1 잔존 레코드 영구 삭제]**:
  - 원인: DIRECTIVE 133-R에서 프로브 검증에 사용된 `TEST-PROBE-DIRECTIVE-133`이 D1 `vehicles` 및 `vehicle_listings`에 잔존(is_public=0이었으나 `publishing_status='APPROVED'`).
  - 조치:
    1. D1 원격 DB에서 `TEST-PROBE-DIRECTIVE-133` 영구 삭제 완료 (`test_vehicles_count = 0`).
    2. `cloudflare/dist-customer/_worker.js`에 `/^(TEST|PROBE|DEMO|MOCK|TEMP)-/i` 정규식 기반 차단 가드 실장: 테스트 식별자 유입 시 HTTP 400 (`TEST_IDENTIFIER_PROHIBITED_IN_PROD`) 거부 프로덕션 실측 완료.
- **ISSUE-140 [P0 상사 진실성 및 동의 증빙 체계화 - 딜러 정보 정정 및 마케팅/사진 동의 검증 컬럼 연동]**:
  - 원인: D1 `dealers` 테이블에 가상 전화번호 기재 및 단순 ACTIVE 상태만으로 자동 승인하는 취약점.
  - 조치: 마이그레이션 `0004_directive_134_remediation.sql` 실행:
    1. 가상 딜러(가온모터스, 우리상사, 제일오토) 전원 `INACTIVE`로 비활성화하여 자동 동기화 오분류 원천 차단.
    2. 더쿨모터스 대표자명을 정식 법인 대표자인 `유동호`로 정정, 미확인 전화번호는 `확인대기`로 정정, 실제 위탁/광고 동의 증빙(`internal://auth_proofs/64노3143_thecoolmotors_auth.json`)과 연결.
    3. `marketing_consent_verified INTEGER`, `photo_consent_verified INTEGER`, `consent_proof_uri TEXT` 컬럼 추가 및 `_worker.js`에서 `marketing_consent_verified = 1` 대조 강제.
- **ISSUE-141 [P0 실제 매물 식별 구조 복구 - 임시 가상 번호판 날조 영구 퇴출 및 고유 식별자 정립]**:
  - 원인: 크롤링 데이터의 번호판 뒷자리만으로 `더쿨-XXXX` 형태의 임의 번호판을 생성하여 등록하던 비정상적 구조.
  - 조치:
    1. 직영 13대(정식 전체 번호판 완비)와 크롤링 61대를 엄격 분리.
    2. 전체 번호판이 없는 매물에 대해 `더쿨-XXXX` 가상 번호판 생성을 전면 폐기하고, 원본 번호판이 없으면 `plate_number: null` 및 카매니저 원본 고유 ID(`encarno`), 제시번호(`suggestNo`)로만 정직하게 식별.
    3. `vehicle_listings` 테이블의 매핑을 카매니저 실제 제시번호(`2026129974`, `2026121600`, `2026119893`, `2026100117`, `2026099548`) 1:1 매핑으로 전수 갱신.
- **ISSUE-142 [P1 진짜 실시간 동기화 및 운영 시범 검증 - launchd 데몬 구성, 로컬 샌드박스 프로브 및 검증 5대 비공개 스테이징]**:
  - 조치:
    1. Mac mini `launchd` 데몬 서비스(`~/Library/LaunchAgents/com.chaficial.sync.plist`) 구성 및 래퍼 스크립트(`scripts/run_sync_daemon.sh`) 작성.
    2. 운영 D1에 테스트 데이터를 넣지 않고, 로컬 SQLite 샌드박스(`data/chamart/test_sync_sandbox.db`)에서 프로브 검증(가격 변경, SOLD 전이, 재공개 차단) 100% 통과.
    3. 실제 권한 증빙을 갖춘 직영 5대(`64노3143`, `277노8340`, `358고4799`, `160버5497`, `145더8176`)를 비공개(`is_public = 0, PENDING_REVIEW`)로 완벽 보존하고, 사용자 명시적 최종 승인 전까지 공개하지 않는 안전 게이트 준수.
    4. Cloudflare Pages 프로덕션 배포 완료 (`04f4057e`). 공개 API 실측 0대(`[]`) 및 테스트 식별자 400 거부 실측 완료.

### 9. DIRECTIVE 135: 카매니저 실시간 수집과 차마트 D1 동기화 단절 복구 (ISSUE-143 ~ ISSUE-146)
- **ISSUE-143 [P0 실시간 수집기 연동 - CarManagerLiveClient 세션 기반 실시간 인벤토리 수집]**:
  - 원인: 데몬이 고정 로컬 JSON만 단순 파싱하여 실시간 카매니저 세션과의 연결 단절.
  - 조치: `CarManagerLiveClient.fetch_live_my_cars()`를 데몬 수집 파이프라인에 직접 통합. 실시간 세션 조회 실측 성공(14대 직접 확인) 및 실패 시 검증된 스냅샷(74대) 안전 보존(Fallback) 아키텍처 완성.
- **ISSUE-144 [P0 실제 동기화 활성화 - dry_run 제거 및 D1 HTTP 200 검증 체크포인트 갱신]**:
  - 원인: 데몬 `run_forever()`가 강제 `dry_run=True`로 실행되어 실제 D1에 반영되지 않고 가짜 체크포인트가 저장되던 결함.
  - 조치: `dry_run=False`로 전환하여 15대 단위 안전 청크로 실제 D1 전송 실측 (`updated: 74, skipped: 0`). D1 서버의 `success: true` 응답을 확인한 경우에만 해시 체크포인트를 갱신하도록 무결성 보장.
- **ISSUE-145 [P0 원본 ID 기반 61대 비공개 연결 - plate_number 부재 시 skipped 결함 수정]**:
  - 원인: `_worker.js`에서 `!v.plate_number` 검사로 인해 번호판 앞자리가 마스킹된 61대 매물이 무조건 skipped 처리되던 아키텍처 결함.
  - 조치: `_worker.js` 수정: `!v.id`만 검사하고, 유효 번호판이 없으면 `plate_number = NULL` 및 `registration_number = encarno`로 매핑하여 D1에 안전하게 `is_public = 0, PENDING_REVIEW`로 100% 적재 성공. Cloudflare Pages 재배포 완료 (`7677e103`).
- **ISSUE-146 [P0 엔드투엔드 단일 파이프라인 실증 - 무변동 스킵 및 증분 감지 100% PASS]**:
  - 조치:
    1. 최초 동기화 사이클: 74대 전수 D1 동기화 완료 (`updated: 74`).
    2. 두 번째 무변동 사이클: 카매니저 실시간 조회 후 변경 매물 0대 감지 ➡️ D1 전송 생략 (`SKIPPED_NO_CHANGES`) 100% 실측.
    3. 단위 테스트 `tests/test_directive_135_e2e.py` 작성 및 4개 스텝 100% 통과 (실시간 수집, 원본 ID 매칭, 무변동 스킵, 1건 증분 변동 감지).

### 10. DIRECTIVE 135-R: 실시간 수집-D1 동기화 무결성 및 실매물 1호 검수 증빙 완성 (ISSUE-147 ~ ISSUE-150)
- **ISSUE-147 [P0 가상 번호판 날조 원천 배제 및 정식 원본 식별체계 확립]**:
  - 조치:
    1. `더쿨-XXXX` 등 임의 번호판 완전 폐기, 원본 번호판 미확보 차량은 `plate_number: null` 및 카매니저 원본 고유 ID(`encarno`), 제시번호로 1:1 정식 식별.
    2. `_worker.js`에서 유효 정규식을 통과한 번호판만 바인딩하고 그렇지 않으면 엄격히 `null`로 보존.
- **ISSUE-148 [P0 실시간 라이브 세션 직영 매물 + 캐시 스냅샷 무결 파이프라인 E2E 실측]**:
  - 조치:
    1. `tests/test_directive_135_r_real_e2e.py` 작성 및 실측 실행.
    2. Step 1: 카매니저 실시간 관리자 세션 연동 성공 (직영 13대 실시간 수집 + 단지 61대 스냅샷 캐시 통합 = 총 74대).
    3. Step 2: 원본 판매/광고중지 상태 정밀 매핑 (`FOR_SALE`, `IN_REVIEW`, 가격 미기재 ➡️ `IN_REVIEW`).
    4. Step 3: Cloudflare D1 15대 단위 5개 청크 실제 전송 완료 (`updated: 74, skipped: 0, inserted: 0`).
    5. Step 4: 2회차 연속 동기화 사이클 실행 시 변경 매물 0대 감지 ➡️ Cloudflare D1 전송 완벽 생략 (`SKIPPED_NO_CHANGES`) 실측 통과.
    6. Step 5: Mac mini launchd 상주 서비스(`com.chaficial.sync`) 등록 상태 및 로그 정상 확인. (5개 스텝 100% PASS).
- **ISSUE-149 [P0 실매물 1호 64노3143 사진 레코드 중복 제거 및 9장 비공개 격리 확정]**:
  - 조치:
    1. D1 `vehicle_photos` 테이블에서 1번 사진 URL 중복 레코드(`PHOTO-e6670a2e...-1`) 영구 삭제.
    2. 정품 카매니저 실차 사진 정확히 9장 확정 보존 (`sort_order: 1~9`, `category: EXTERIOR/INTERIOR`, `public_visibility: 'PRIVATE'`, `approval_status: 'PENDING'`).
    3. 차량 레코드 상태: `is_public = 0`, `publishing_status = 'PENDING_REVIEW'`, `status = 'IN_REVIEW'`, `listing_ownership_type = 'EXTERNAL'`.
- **ISSUE-150 [P0 고객용 공개 API 0대 격리 및 관리자 검수 증빙 패키지 확보]**:
  - 조치:
    1. 프로덕션 고객용 공개 API(`https://chamart.cc/api/chamart/vehicles`) 응답 0대(`[]`) 및 상세 URL 직접 접근 시 HTTP 404 차단 실측 완료.
    2. Playwright를 통한 화면 캡처 4종 생성 및 아티팩트 보존:
       - `directive135_r_pc_list_blocked.png` (PC 목록 0대 비공개 격리 입증)
       - `directive135_r_mobile_list_blocked.png` (모바일 목록 0대 비공개 격리 입증)
       - `directive135_r_pc_detail_preview.png` (실매물 1호 64노3143 PC 관리자 검수 프리뷰)
       - `directive135_r_mobile_detail_preview.png` (실매물 1호 64노3143 모바일 관리자 검수 프리뷰)

### 11. DIRECTIVE 136: 실제 판매 운영을 위한 마지막 연결 및 게시 승인 상태 보존 (ISSUE-151 ~ ISSUE-155)
- **ISSUE-151 [P0 관리자 공개 승인 상태 영구 보존 - shouldAutoPublish 결함 제거]**:
  - 원인: `_worker.js`에서 `shouldAutoPublish = false` 분기로 인해 기존에 관리자가 승인한 차량(`APPROVED / is_public=1`)마저 가격/제원 동기화 시 비공개/`PENDING_REVIEW`로 되돌아가던 심각한 운영 결함.
  - 조치:
    1. `_worker.js` 상태 보존 가드 구현: 기존 승인 차량(`existing.publishing_status === 'APPROVED' && existing.is_public === 1`)은 가격이나 제원이 변경되어 동기화되더라도 `is_public = 1, publishing_status = 'APPROVED'` 상태를 영구 유지.
    2. 단, 판매완료(`SOLD`) 또는 광고중지(`SUSPENDED`) 시에는 즉시 `is_public = 0, publishing_status = 'UNPUBLISHED'`로 비공개 전환.
    3. 실매물 1호 `64노3143`은 사용자의 명시적 최종 승인 전까지 무조건 `is_public = 0, publishing_status = 'PENDING_REVIEW'` 게이트 엄격 보호.
    4. 단위 테스트 `tests/test_directive_136_safety_rules.py` 작성 및 5개 케이스 100% 통과.
- **ISSUE-152 [P0 실시간 판매 상태 추적 및 광고중지/판매완료 정밀 분리]**:
  - 조치:
    1. `continuous_sync_daemon.py`에서 광고중지(`SUSPENDED`)와 실제 판매완료(`SOLD`)를 분리.
    2. 실시간 세션 조회 성공 시, 실시간 목록에서 사라진 직영 차량은 판매완료로 단정하지 않고 상태 미확인(`IN_REVIEW`)으로 분류하여 재조회 대상으로 격리.
    3. 주행거리 제원 매핑 시 반올림이나 임의 기본값을 배제하고 카매니저 원본 실측 주행거리(`125,428km`)를 1순위로 정확히 바인딩.
- **ISSUE-153 [P0 운영 E2E 테스트 엄격화 - launchd 등록 및 D1 원격 재조회 1:1 값 일치 검증]**:
  - 조치:
    1. `tests/test_directive_136_e2e.py` 작성:
       - Step 1: launchd `com.chaficial.sync` 등록 여부 엄격 assertion (`assert has_launchd_entry is True`).
       - Step 2: 실시간 카매니저 세션 수집 및 64노3143 정밀 제원(`125,428km`, `1,090만원`) 검증.
       - Step 3: Cloudflare D1 74대 전수 실제 전송 (`updated: 74, skipped: 0`).
       - Step 4: 원격 D1 재조회하여 실시간 전송 값과 완벽 일치 비교 (`target_price = 1090`, `mileage = 125428`, `is_public = 0`, `publishing_status = 'PENDING_REVIEW'`).
       - Step 5: 2회차 무변동 실행 시 D1 전송 완벽 생략 (`SKIPPED_NO_CHANGES`).
       - Step 6: 관리자 API를 통한 실제 D1 레코드 조회 검증.
       - Step 7: 고객용 공개 API 0대 격리 확인 (전체 7단계 100% PASS).
- **ISSUE-154 [P0 인증된 관리자 전용 실매물 API 구축 및 실제 D1 기반 검수 화면 캡처]**:
  - 조치:
    1. `_worker.js`에 `GET /api/admin/vehicles/:id` 엔드포인트 구현: 토큰(`X-Admin-Token` 또는 `?token=...`) 검증 후 비공개 차량도 D1 원격 실시간 레코드와 연결된 사진 9장을 포함한 전체 JSON 1:1 반환.
    2. 하드코딩이나 브라우저 주입을 전면 배제하고, Playwright 브라우저가 실제 D1 관리자 API를 직접 호출하여 렌더링한 화면을 스크린샷으로 캡처 보존:
       - `directive136_pc_admin_detail_real.png` (D1 실제 원격 데이터 기반 PC 관리자 검수 프리뷰)
       - `directive136_mobile_admin_detail_real.png` (D1 실제 원격 데이터 기반 모바일 관리자 검수 프리뷰)
       - `directive136_pc_public_list_zero.png` (고객용 공개 목록 0대 차단 입증)
       - `directive136_mobile_public_list_zero.png` (고객용 모바일 공개 목록 0대 차단 입증)
- **ISSUE-155 [P1 사용자 승인 후 운영 체계 확립 - 상사 단위 사전 승인 및 지속 파이프라인 완성]**:
  - 조치:
    1. 제휴 상사 (주)더쿨모터스(`dealer-thecool-motors`, 대표자 `유동호`, `marketing_consent_verified = 1`, `photo_consent_verified = 1`) 검증 완료.
    2. 사용자가 향후 실매물 공개를 승인하면, 해당 차량은 가격이 바뀌어도 공개 상태를 유지하고, 카매니저에서 판매완료/광고중지 시 자동으로 차마트에서 내려가는 완전 자동화 라이프사이클 체계 확립.

### 12. DIRECTIVE 136-SEC: 관리자 API 인증 취약점 긴급 보정 및 운영 보안 검증 (ISSUE-156 ~ ISSUE-159)
- **ISSUE-156 [P0 하드코딩 기본 토큰 영구 완전 폐기 및 Cloudflare Secret 엄격 검증]**:
  - 원인: `_worker.js`에 임시 fallback 인증값(`chamart-sync-secret-2026`)이 남아있어 Cloudflare Secret 미설정 시에도 기본 문자열로 관리자 API 접근이 허용될 수 있는 중대 보안 취약점.
  - 조치:
    1. `_worker.js`에서 fallback 문자열 및 기본값 영구 완전 제거.
    2. Cloudflare Secret(`env.CHAMART_ADMIN_TOKEN`)이 16자 이상 문자열로 명시 설정되지 않은 경우 어떠한 요청도 허용하지 않고 즉시 `401 Unauthorized` (`UNAUTHORIZED_ADMIN_ACCESS`) 차단.
    3. 코드베이스, 테스트 코드, 스크린샷 캡처 스크립트 전체에서 하드코딩 토큰을 완전 제거하고 환경변수/암호화 시크릿 기반으로 전면 리팩토링.
- **ISSUE-157 [P0 ?token= URL 쿼리 파라미터 인증 완전 차단 및 Bearer 헤더 단일화]**:
  - 원인: URL 파라미터(`?token=...`)를 통한 토큰 전달 시 브라우저 히스토리, 웹서버/CDN 접근 로그, 리퍼러 헤더 등에 비밀값이 노출될 수 있음.
  - 조치:
    1. `_worker.js`에서 `url.searchParams.get('token')` 파싱 로직 원천 제거.
    2. 관리자 접근 시 오직 `Authorization: Bearer <token>` 및 `X-Chamart-Admin-Key` 헤더만 허용.
    3. `tests/test_directive_136_sec.py`를 통해 `?token=...` 요청 시 401 차단 실서버 검증 완료.
- **ISSUE-158 [P0 동기화 토큰과 관리자 토큰 분리 및 타이밍 공격 방지 안전 비교]**:
  - 조치:
    1. 데몬 동기화 인증(`CHAMART_SYNC_TOKEN` / `SYNC_API_KEY`)과 관리자 조회 인증(`CHAMART_ADMIN_TOKEN`)을 물리적/논리적으로 엄격 분리 (`verifySyncAuth` vs `verifyAdminAuth`).
    2. 관리자 토큰으로 동기화 엔드포인트 호출 시 401 차단, 동기화 토큰으로 관리자 엔드포인트 호출 시 401 차단 상호 격리 검증 완료.
    3. 문자열 타이밍 분석 공격을 방지하기 위해 비트 XOR 기반 `constantTimeEqual` 비교 함수 적용.
- **ISSUE-159 [P0 관리자 API 반환 정보 축소 및 실서버 전수 보안 검증 (100% PASS)]**:
  - 조치:
    1. 관리자 엔드포인트에서 `SELECT v.*` 내부 컬럼 덤프를 전면 제거하고 필수 제원 및 승인된 사진 9장(`LIMIT 20`)만 선별 반환 (`dealer_id`, `options_json`, `memo` 등 내부 필드 배제).
    2. Cloudflare Pages production 환경에 `wrangler pages secret put`을 통해 `CHAMART_ADMIN_TOKEN`, `CHAMART_SYNC_TOKEN`을 안전하게 주입하고 재배포 (`e034a1e4.chamart.pages.dev`, 프로덕션 `https://chamart.cc`).
    3. 종합 보안 검증(`tests/test_directive_136_sec.py`): 토큰 부재(401), 폐기 토큰(401), URL 쿼리(401), Sync 토큰 관리자 접근(401), Admin 토큰 동기화 접근(401), 정상 Bearer 인증(200 OK), 고객 공개 0대 격리 7개 전 케이스 100% 통과.
    4. 기존 136 동기화 파이프라인 E2E 테스트(`tests/test_directive_136_e2e.py` 7단계 전체 100% PASS) 및 안전 규칙 단위 테스트(`test_directive_136_safety_rules.py` 5/5 PASS) 회귀 검증 완료.
    5. Bearer 인증 기반 실제 D1 관리자 화면 스크린샷 4종 갱신 보존.

### 13. DIRECTIVE 136-SEC-R: 테스트 토큰 노출 위험 영구 제거 및 256비트 암호화 토큰 교체 (ISSUE-160 ~ ISSUE-162)
- **ISSUE-160 [P0 보안 테스트 Case 3 URL 쿼리 파라미터 실제 토큰 전송 제거 및 합성 토큰 검증]**:
  - 원인: `tests/test_directive_136_sec.py` Case 3에서 `url.searchParams.get('token')` 차단 여부를 검증하기 위해 실제 `ADMIN_TOKEN`을 URL 쿼리에 실어 서버로 전송하여 중간 프록시/CDN 로그에 남을 수 있는 잠재적 위험 발생.
  - 조치:
    1. 실제 토큰 전송을 영구 제거하고 가상의 합성 더미 토큰(`synthetic-dummy-query-probe-token-never-used-in-prod`)을 쿼리에 전달하여 401 차단 검증.
    2. Worker 소스코드 차원에서 `url.searchParams.get('token')` 로직이 영구 삭제되었음을 정적/동적으로 이중 확인.
- **ISSUE-161 [P0 화면 캡처 스크립트 브라우저 evaluate 내 토큰 문자열 삽입 제거 및 서버 측 인증 격리]**:
  - 원인: `capture_directive_136_real_admin_screens.py`에서 `page.evaluate()` 내부 자바스크립트 문자열에 토큰을 직접 바인딩하여 브라우저 콘텍스트 내 노출 위험 존재.
  - 조치:
    1. 브라우저 내 직접 `fetch` 호출을 전면 배제하고, Python 서버 측(`urllib.request`)에서 `Authorization: Bearer` 헤더로 D1 관리자 데이터를 안전하게 사전 조회.
    2. 조회된 순수 차량 데이터 JSON 객체만 `page.evaluate((data) => { ... }, real_d1_data)` 인자로 전달하여 모달을 렌더링하도록 완전 격리.
    3. 브라우저 DOM, JS 콘텍스트, 네트워크 어디에도 인증 토큰이 노출되지 않도록 조치 완료 및 스크린샷 4종 갱신.
- **ISSUE-162 [P0 운영 관리자 토큰 256비트 암호학적 난수 교체 및 Cloudflare Secret 재등록]**:
  - 조치:
    1. 이전 테스트에 사용되었을 가능성이 있는 관리자 토큰을 즉시 폐기.
    2. `secrets.token_hex(32)` (256비트 엔트로피) 암호학적 난수로 `CHAMART_ADMIN_TOKEN` 및 `CHAMART_SYNC_TOKEN`을 신규 생성하여 Cloudflare Pages production Secret으로 안전하게 교체 등록.
    3. Pages 최신 배포(`98c4ba42.chamart.pages.dev`, `https://chamart.cc`) 수행.
    4. Cloudflare Pages 무료/기본 플랜의 원시 액세스 로그 미제공 한계를 사실대로 명시 보고.
    5. 보안 테스트 7개 전 케이스(`test_directive_136_sec.py`) 및 E2E 테스트 7단계(`test_directive_136_e2e.py`) 100% PASS 최종 통과.

### 14. DIRECTIVE 137: 장한평 전체 시장 연동 및 차마트 판매 운영 전환 (ISSUE-163 ~ ISSUE-166)
- **ISSUE-163 [P0 카매니저 장한평 전체 시장 1,764대(49개 상사) 수집 풀 파서 구축 및 전용 필터 제거]**:
  - 조치:
    1. 기존 더쿨모터스 74대 전용 필터를 전체 시장 수집 경로에서 전면 제거.
    2. 카매니저 장한평 단지 크롤링 원본 `janghanpyeong_full_collection.json` 1,764대(유니크 encarno 1,764대, 49개 상사 전수)를 안전하게 파싱하는 `fetch_janghanpyeong_market_pool()` 구축.
    3. 상사별 분포 실측: 선인자동차 225대, 디케이드림카 114대, 더이룸카 89대, 용정상사 77대, 더쿨모터스 74대, 가교상사 63대, 서울자동차판 60대, 호국모터스 58대 등 49개 상사 전수 분류.
- **ISSUE-164 [P0 전체 시장 분석 데이터(1,690대)와 차마트 판매 권한 데이터(74대)의 엄격 분리]**:
  - 조치:
    1. 차피셜 AI 분석 DB 총 1,801대(장한평 시장 관측 1,770대 + 직영 31대)는 시장 시세 및 감가율 분석 목적으로 독립 보존.
    2. 장한평 1,764대 중 광고 및 판매 권한이 공식 확인된 제휴 상사((주)더쿨모터스 74대) 매물만 차마트 D1 판매 관리 풀로 선별.
    3. 광고 권한 미확인 매물(1,690대)은 시장 관측 풀(`MARKET_OBSERVED`)로 분류하여 D1 동기화 대상에서 원천 배제함으로써 무단 광고 및 허위 매물 위험을 방지.
- **ISSUE-165 [P0 카매니저 실시간 세션 연동 및 변경 감지 기반 원자적 멱등 D1 증분 동기화]**:
  - 조치:
    1. 카매니저 실시간 직영 세션을 통해 13대 실시간 매물 제원(실측 주행거리, 정밀 판매가격 등)을 조회하고 실매물 1호 `64노3143`의 정밀 제원(125,428km / 1,090만원)을 실시간 바인딩.
    2. MD5 기반 상태 해시를 통해 변경이 감지된 차량(39대)만 선별하여 청크 단위 원자적 멱등 동기화 수행 (39대 D1 update 성공, inserted: 0, updated: 39).
    3. 2회차 연속 실행 시 무변동 매물에 대해 D1 API 호출을 100% 생략(`SKIPPED_NO_CHANGES`)하여 서버 부하 및 API 쿼터 완벽 보호.
- **ISSUE-166 [P0 운영 무결성 및 공개 0대 격리 유지 전수 검증 (E2E 7단계 100% PASS)]**:
  - 조치:
    1. 원격 D1 재조회를 통해 `64노3143`의 제원(가격 1,090만원, 주행거리 125,428km, 사진 9장 정상 매핑)과 비공개 상태(`is_public=0`, `publishing_status='PENDING_REVIEW'`)가 완벽 일치함을 검증.
    2. 관리자 API(Bearer 인증)를 통해서만 안전하게 세부 제원이 확인되며, 고객용 공개 API(`chamart.cc/api/vehicles`)는 매물 0대로 완전 격리 유지 확인 (임의 공개 원천 차단).
    3. 종합 E2E 검증(`tests/test_directive_137_market_sync.py` 7단계 100% PASS), 보안 회귀(`test_directive_136_sec.py` 7/7 PASS), 안전 규칙(`test_directive_136_safety_rules.py` 5/5 PASS) 전수 합격.

### 15. DIRECTIVE 137-R: 장한평 전체 실시간 수집 및 차피셜 DB/차마트 실제 연동 복구 (ISSUE-167 ~ ISSUE-170)
- **ISSUE-167 [P0 카매니저 장한평 전체 시장 실제 실시간 재수집 완결 및 원본 정합성 입증]**:
  - 조치:
    1. 기존 JSON 캐시 재활용을 배제하고 `JanghanpyeongCollector`를 직접 가동하여 카매니저 라이브 서버에서 성동구/장한평 단지 전체 시장 89페이지를 실시간 전수 크롤링 완료 (수집 시각: `2026-10-31T17:34:33.944669`, 캡처 ID: `LIVE_JHP_20261031_173433`).
    2. 카매니저 실서버 1페이지에서 보고한 총건수 1,764대와 실제 수집된 고유 차량 ID(`encarno`) 1,764건이 100% 일치함을 입증 (누락 페이지 0건, 실패 0건, `is_complete=True`).
    3. 카매니저 실서버에 존재하는 실제 장한평 매물이 약 1,100대가 아닌 정확히 1,764대임을 실측 입증.
- **ISSUE-168 [P0 수집량 고정 임계값(1500) 제거 및 시장 규모 적응형 하한선(Floor) 도입]**:
  - 조치:
    1. `janghanpyeong_collector.py` 및 `scripts/run_daily_sync.py`에서 하드코딩된 `MIN_TOTAL_THRESHOLD = 1500`를 제거.
    2. 시장 변동에 유연하게 적응하는 최소 하한선(`MIN_TOTAL_FLOOR = 300`, `MIN_OWNED_FLOOR = 10`, `MIN_MARKET_FLOOR = 200`)과 카매니저 원본 총건수 대비 100% 일치율 동적 정합성 검증으로 개선.
- **ISSUE-169 [P0 상사명 부분문자열('더쿨') 하드코딩 영구 제거 및 DealershipRegistry 기반 정식 광고 권한 검증 체계 구축]**:
  - 조치:
    1. `data/authorized_partner_dealerships.json` 및 `DealershipRegistry`를 신규 구축하여 법적 계약(`contract_status == 'ACTIVE'`)과 광고 동의(`advertising_consent.status == 'APPROVED'`)를 기준으로 광고 권한을 공식 판정.
    2. (주)더쿨모터스(74대)는 정식 계약 및 광고 동의 확인으로 차마트 D1 판매 연동 풀로 승격.
    3. 타 48개 상사(1,690대)는 미권한 시장 관측 풀(`MARKET_OBSERVED`)로 엄격 분리하여 무단 광고를 원천 차단.
    4. 향후 신규 제휴 상사 등록 시 JSON 등록만으로 즉시 연동되는 확장형 구조 확립.
- **ISSUE-170 [P0 차피셜 분석 DB 실제 시계열 갱신 및 차마트 D1 연동 원스톱 운영 검증 (E2E 7단계 100% PASS)]**:
  - 조치:
    1. `MarketTimeSeriesEngine`을 통해 차피셜 분석 DB(`chamart_platform_demo.db`)에 오늘 실시간 관측 시계열(`RunID = d9926dca-...`, `LIVE_OBSERVED`, 1,764대 전수)을 원자적 커밋 완료.
    2. `carmanager_sync_logs` 및 `vehicles` 테이블 갱신: Owned 74대, Market 1,690대 정합성 감사 완료.
    3. 차마트 D1 원자적 멱등 동기화 및 2회차 무변동 완벽 스킵(`SKIPPED_NO_CHANGES`) 실서버 확인.
    4. 실매물 1호 `64노3143` 원격 D1 제원(125,428km / 1,090만원 / 사진 9장) 및 비공개(`is_public=0`) 유지, 고객용 공개 API 0대 격리 100% 확인.
    5. 종합 검증(`tests/test_directive_137_r_real_market_pipeline.py`) 7단계 100% PASS 합격.







