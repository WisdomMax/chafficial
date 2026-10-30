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
| **ISSUE-32** | 검증되지 않은 사진에 AUTHORIZED, PUBLIC, APPROVED 자동 부여 결함 | 심각 | 🟢 해결완료 | 외부 상사 사진 3,535장 전수 PRIVATE/PENDING_REVIEW 격리 및 수집기 기본값 비공개 전환 |

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
- [ ] ⚪️ **C-7. 거시경제 지표 수집기 (유가·금리·환율)**:
  - 한국석유공사 오피넷(Opinet) 전국/지역별 유가(휘발유/경유/LPG) 일일 트래커
  - 한국은행 ECOS 할부금융 금리 및 환율 시계열 데이터 연계

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
