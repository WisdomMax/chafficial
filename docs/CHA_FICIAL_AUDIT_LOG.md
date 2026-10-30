# CHA-FICIAL 공식 기술 감사 로그 (AUDIT LOG)
> **기록 목적:** 총괄 기술 감독(ChatGPT)과 개발 에이전트(Antigravity) 간의 DIRECTIVE별 지시사항, 독립 감사 결과, 발견된 결함, 조치 커밋 및 검증 증거의 누적 불변 기록.  
> **최초 작성일:** 2026-10-30 21:55:00 KST  
> **최종 갱신일:** 2026-10-30 22:00:00 KST  

---

## [DIRECTIVE 109] 시장 기억장치(Time-Series) 엔진 구축·동적 페이지 계산·3일치 재현실험 통과
- **일시:** 2026-10-30 22:10 KST
- **지적된 결함:**
  1. 단순 매물 목록 교체 방식으로는 가격 변동, 체류 일수, 재등장 이력을 장기 학습할 수 없음.
  2. 수집 실패 시 기존 정상 스냅샷 JSON이 덮어써질 위험.
  3. 89페이지 고정으로 90페이지 이상 매물 증가 시 누락 위험.
- **조치 및 구현:**
  1. `src/chaficial/platform/sourcing/market_timeseries_engine.py` 신설:
     - `market_collection_runs`: 수집 실행 이력 (run_id, pages_collected, unique_cars, sha256).
     - `market_listing_observations`: 일일 차량별 상태 시계열 스냅샷.
     - `market_listing_events`: 관측 스냅샷 간 이벤트 산출 (APPEARED, PRICE_DECREASED, DELISTED_DISAPPEARED 등).
     - 운영 `vehicles` 테이블과 100% 분격 격리.
  2. `src/chaficial/platform/sourcing/janghanpyeong_collector.py`:
     - 원자적 임시 저장 (`*.tmp.json` -> 1,500대 검증 후 `shutil.move`).
     - 1페이지 총건수 기반 `max_pages` 동적 확장 로직 구현.
  3. `src/chaficial/platform/sourcing/carmanager_sync.py`:
     - SQLite URI `file:...db?mode=ro` 읽기 전용 모드 및 쓰기 쿼리 전면 차단.
- **검증 증거:**
  - `scratch/test_directive_109_timeseries.py`: 3일치 재현 실험(차량 A 1500->1450->1390 인하 2건, 차량 B 사라짐 1건, 가짜 SOLD 0건) SQL 100% 통과.

---

## [DIRECTIVE 108] 마스터 체크리스트 표기 시정·P0 이슈 추적표 신설·--dry-run 완전 읽기전용화
- **일시:** 2026-10-30 22:00 KST
- **지적된 결함:**
  1. 에이전트 자체 판단 완료와 감독 승인 완료의 혼용.
  2. P0 결함 추적표 부재 및 실제 사업 운영 F 영역 누락.
  3. `--dry-run` 모드가 실제로 DB를 수정하는 결함.
  4. 세션 토큰 로그 노출 (보안 취약점).
- **조치 및 구현:**
  1. `docs/CHA_FICIAL_MASTER_CHECKLIST.md`: 표기 기준 엄격 재정비 (감독 승인 [x] 🟢, 검증 대기 [ ] 🟡, 미구현 [ ] ⚪️), P0 이슈 추적표(ISSUE-01~11) 신설, F영역(차마트 상업 운영) 신설.
  2. `src/chaficial/platform/sourcing/carmanager_sync.py`: `dry_run=True` 지원 -> 커밋 차단 및 롤백, DB 쓰기 0건 완벽한 읽기 전용 모드 확립.
  3. `scripts/run_daily_sync.py`: `--dry-run` 플래그 시 `dry_run=True` 직결.
  4. `src/chaficial/platform/sourcing/janghanpyeong_collector.py`: 세션 토큰 마스킹(`enc_check[:4] + "****"`) 적용.
- **검증 증거:**
  - `python3 scripts/run_daily_sync.py --dry-run` 실행: `Status=DRY_RUN_READ_ONLY` 및 DB 쓰기 0건 검증 완료.

---

## [DIRECTIVE 107] 실시간 수집 결합·엄격한 임계치(1,500대)·UNVERIFIED 오병합 방어
- **일시:** 2026-10-30 21:50 KST
- **기준 커밋:** `5081b6f`, `b6c04f6`
- **지적된 결함:**
  1. `daily_carmanager_sync.sh`에 `--live` 옵션 누락으로 예약 실행 시 과거 JSON 재사용 위험.
  2. `JanghanpyeongCollector.run_full_collection()`이 summary 통계만 반환하고 `cars` 리스트를 반환하지 않아 러너가 빈 목록을 수신함.
  3. 전체 1,764대 중 50대만 수집되어도 통과하는 임계치가 너무 느슨함.
  4. 미확인 번호판(`UNVERIFIED`) 차량이 중복 병합 스크립트에 의해 단일 차량으로 오병합될 수 있는 위험.
- **조치 및 구현:**
  1. `scripts/daily_carmanager_sync.sh`: `python3 scripts/run_daily_sync.py --live` 명시 적용.
  2. `scripts/run_daily_sync.py`: 기본 실행 모드를 LIVE 실시간 수집으로 고정.
  3. `src/chaficial/platform/sourcing/janghanpyeong_collector.py`: `summary["cars"] = all_cars` 반환 수정 (`b6c04f6`).
  4. **엄격한 수집 임계치**: 시장 매물 `MIN_MARKET_THRESHOLD = 1500`, 상사 매물 `MIN_OWNED_THRESHOLD = 60` 설정, 미달 시 DB 쓰기 100% 차단(0 writes) 및 `exit 1` 강제 종료.
  5. `scratch/merge_duplicate_vehicles.py`: `AND plate_number != 'UNVERIFIED'` 조건 강제.
  6. 사진 해상도 정량 분격: 고해상도 2,694장(84.2%) + 인덱싱/구형 505장(15.8%) 정직하게 분격 보고.
- **검증 증거:**
  - `scratch/test_directive_107_guards.py`: GUARD 1, GUARD 2, GUARD 3 SQL 전수 통과.

---

## [DIRECTIVE 106] 가격 단위 만원 표준화·137건 가짜 가격변경 정밀 감사·10대 통제실험
- **일시:** 2026-10-30 21:40 KST
- **기준 커밋:** `987dd18`
- **지적된 결함:**
  1. 동기화 엔진이 `price_manwon * 10000`을 적용하여 DB 컬럼에 원 단위(예: 34,000,000)를 혼입시키고 137건의 가짜 가격변경을 유발함.
  2. 주행거리 파서가 '5.5만 km'에서 숫자만 추출하여 55km로 왜곡할 위험.
  3. 전체 번호판 미확인 시 끝 4자리를 plate_number에 오삽입할 위험.
  4. 3회 누락 시 무조건 SOLD 처리하는 상태머신 결함.
  5. 더쿨모터스 차량 수 74대 vs 87대 산술 혼선.
- **조치 및 구현:**
  1. `scratch/normalize_price_units.py`: DB 내 100,000 이상 가격 173건을 순수 만원 단위로 완전 정규화.
  2. `scratch/clean_false_price_changed_timelines.py`: 137건 가짜 PRICE_CHANGED 이벤트를 정정 이벤트로 100% 치환.
  3. `src/chaficial/platform/sourcing/carmanager_sync.py`: `parse_price_manwon`, `parse_mileage_km`, `parse_plate_info` 함수 구축.
  4. 3회 누락 시 DELISTED(광고중지/비공개) 격리 처리, 명시적 sold_snapshot만 SOLD 전환.
  5. 상사 74대(상호 더쿨모터스) + 12대(법인명) - 1대(외부) = 85대 인과관계 규명.
- **검증 증거:**
  - `scratch/test_directive_106_controlled.py`: EXP_01 ~ EXP_10 10대 통제 격리 실험 SQL 100% ALL PASS.

---

## [DIRECTIVE 105] 사진 500대 고화질 원본 복구·encarno 분격 매핑
- **일시:** 2026-10-30 21:20 KST
- **기준 커밋:** `a4c6c3c`
- **지적된 결함:**
  1. 팝업 상세창 파서가 `_TH.jpg`(300x225 썸네일)를 수집하여 사진 용량이 30KB 미만으로 왜곡됨.
  2. 목록 순번(`car_001`) 폴더 저장 방식으로 인한 재동기화 시 사진 오연결 위험.
- **조치 및 구현:**
  1. `_TH.jpg`를 제거하여 `1024x768` 고화질 원본 사진 URL로 전수 변환.
  2. 고유 식별자인 encarno 폴더(`data/carmanager_raw/photos_by_encarno/{safe_encarno}/`)로 저장 구조 전면 개편.
  3. `download_500_highres_by_encarno.py` 실행: 3,199장(274MB) 확보, PIL 디코딩 전수 통과.
  4. DB `vehicle_photos`에 3,179장 연결 완료.

---

## [DIRECTIVE 104] 로컬 rembg 배경 합성 영구 봉인 및 DB 고아 레코드 정화
- **일시:** 2026-10-30 20:50 KST
- **기준 커밋:** `5f1f929`
- **지적된 결함:**
  1. `rembg` 로컬 단색 배경 합성이 비현실적인 품질을 초래함.
  2. DB 내 외래키 불일치 고아 레코드 존재 위험.
- **조치 및 구현:**
  1. `scratch/test_ai_outdoor_bg_3cars.py` 등 합성 스크립트 실행부 영구 봉인 (`raise RuntimeError`).
  2. `photo_pipeline.py`에 PIL Image 디코딩 검증 및 이중 SHA256 해시 검사 구현.
  3. DB 고아 레코드 전수 정화: Listings 0건, Photos 0건, Transactions 0건 달성.

---

## [DIRECTIVE 101~103] 장한평 1,764대 시장 관측 데이터베이스 격리
- **일시:** 2026-10-30 19:30 KST
- **지적된 결함:** 장한평 매매단지 전체 시장 매물(1,600여 대)이 우리 상사 보유 매물과 혼합되어 고객에게 오표시될 위험.
- **조치:** `listing_ownership_type`에 `OWNED`와 `MARKET_JANGHANPYEONG`을 엄격 분리하여 DB에 적재.

---

## [DIRECTIVE 098~100] 장한평 89페이지 고속 수집기(JanghanpyeongCollector) 프로토타입
- **일시:** 2026-10-30 18:00 KST
- **조치:** Playwright 세션 기반 HTTP POST `/Car/DataPart` 엔드포인트 역공학을 통해 89페이지 1,764대를 0.5초 간격으로 저부하 수집하는 파이프라인 개발.

---

## [DIRECTIVE 095~097] 관리자 보안 점검 및 가짜 기본값(더미) 폐기
- **일시:** 2026-10-30 14:00 KST
- **지적된 결함:**
  1. 관리자 API 서버측 인증 점검 및 가짜 VIN/제원 생성 로직 존재.
- **조치:**
  1. Mac mini 로컬 관리자 + Cloudflare Access 보안 정책 강화.
  2. 가짜 `VIN-{carSeq}` 생성 로직 영구 삭제 -> 실데이터 없으면 `NULL` 유지 원칙 확립.
  3. 가격 0원 차량 비공개 초안 처리.
