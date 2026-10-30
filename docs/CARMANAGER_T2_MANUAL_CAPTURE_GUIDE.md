# 카매니저 실제 T2 관측 데이터 수동 캡처 및 인수인계 표준 가이드
**문서 식별자:** `CHA-DOC-SOP-T2-CAPTURE-001`  
**관련 지침:** DIRECTIVE 128 (TASK 4)  
**현재 원본 상태:** `REAL_PILOT_PENDING_NEW_CAPTURE`  
**보안 분류:** 사내 기술 표준 (자격증명 및 토큰 마스킹 필수)

---

## 1. 개요 및 목적
차피셜 중고차 시장 시계열 분석 엔진은 장한평 단지 실매물의 체류일수(Days on Market), 신규 유입(Appeared), 가격 변동(Price Changes), 판매/광고중지(Delisted)를 정밀 추적합니다.
본 가이드는 인위적인 가짜 데이터나 크롤러 차단 위험 없이, **카매니저에 합법적으로 로그인한 운영자의 브라우저 환경에서 장한평 50대 실매물 목록의 순수 응답 데이터를 안전하고 표준화된 방식으로 캡처하여 차피셜 DB에 인수인계하는 7단계 절차**를 정의합니다.

---

## 2. 보안 및 개인정보 준수 수칙 (P0 원칙)
1. **토큰 및 비밀번호 배제:** 저장 파일에 브라우저 쿠키(Cookie), Authorization 헤더, 세션 토큰, 비밀번호 등 민감 자격증명을 일체 포함하지 않습니다.
2. **순수 응답 데이터 한정:** 네트워크 응답 본문(Response Body, JSON 또는 렌더링된 순수 HTML 테이블 영역)만 저장합니다.
3. **접근 권한 준수:** 운영자 계정이 정당하게 열람 권한을 가진 장한평 지역 매물 화면에 대해서만 캡처를 수행합니다.

---

## 3. 표준 수동 캡처 7단계 절차 (Standard Operating Procedure)

### [STEP 1] 브라우저 개발자 도구 준비
1. Chrome 또는 Chromium 기반 브라우저를 열고 카매니저에 정상 로그인합니다.
2. `F12` 또는 `Cmd + Option + I` (Mac)를 눌러 **개발자 도구(Developer Tools)**를 엽니다.
3. 상단 탭에서 **Network(네트워크)** 탭으로 이동한 뒤 `Fetch/XHR` 필터를 선택하고 `Preserve log(로그 보존)`를 체크합니다.

### [STEP 2] 장한평 50대 목록 화면 조회
1. 매물 검색 메뉴에서 지역/단지를 **"서울 장한평"** (성동구/동대문구 장한평 매매단지)으로 지정합니다.
2. 페이지당 목록 표시 개수를 **50대**로 설정합니다 (미지원 시 기본 1페이지 조회).
3. **검색(조회)** 버튼을 클릭하여 목록이 화면에 정상 렌더링되는 것을 확인합니다.

### [STEP 3] 정상 데이터 응답 식별
1. Network 탭 목록에서 차량 목록 데이터를 반환한 요청을 찾습니다:
   - 일반적인 엔드포인트: `/car/searchList`, `/api/cars`, `/datapart/list` 또는 유사 목록 API.
2. 해당 요청을 클릭하고 **Response(응답)** 탭을 확인하여, 50대 매물의 차량번호(`carNo`), 매물ID(`encarno`/`carSeq`), 가격(`price`), 모델명(`carName`) 등이 포함된 정상 응답(JSON 또는 HTML)인지 확인합니다.

### [STEP 4] 순수 응답 본문 저장 (자격증명 제외)
1. Response 본문 영역에서 마우스 우클릭 -> `Save as...` 또는 전체 선택(`Ctrl+A`) 후 복사(`Ctrl+C`)합니다.
2. 텍스트 에디터(VS Code 등)에 붙여넣고, **쿠키나 인증 헤더가 섞이지 않았는지 확인**합니다.
3. 다음 경로 및 명명 규칙으로 저장합니다:
   - 경로: `data/carmanager_raw/t2_captures/`
   - 파일명: `janghanpyeong_t2_manual_YYYYMMDD_HHMM.json` (또는 `.html`)

### [STEP 5] 캡처 메타데이터 기록 (Provenance Manifest)
저장한 원본 파일과 함께 동일 디렉토리에 동명의 메타데이터 파일(`*.meta.json`)을 생성하여 다음 정보를 기록합니다:
```json
{
  "source_capture_id": "T2_MANUAL_20261101_1000",
  "source_capture_at": "2026-11-01T10:00:00+09:00",
  "observation_scope": "JANGHANPYEONG_PAGE_1_50CARS",
  "observation_mode": "MANUAL_CAPTURE",
  "collector_account": "MASKED_OPERATOR",
  "search_filter": {
    "region": "장한평",
    "page": 1,
    "page_size": 50,
    "sort": "LATEST_REGISTERED"
  },
  "raw_file_name": "janghanpyeong_t2_manual_20261101_1000.json"
}
```

### [STEP 6] 무결성 SHA256 해시 산출
터미널에서 저장된 원본의 SHA256 체크섬을 산출하여 메타데이터에 기록하고 무결성을 고정합니다:
```bash
shasum -a 256 data/carmanager_raw/t2_captures/janghanpyeong_t2_manual_20261101_1000.json
```

### [STEP 7] 차피셜 차분 적재 파이프라인 투입
준비된 원본을 수동 인입 전용 파이프라인에 전달하여 T1(과거 1,764대 베이스라인)과의 차분을 검증합니다:
```bash
.venv/bin/python3 scripts/run_manual_t2_ingest.py --input data/carmanager_raw/t2_captures/janghanpyeong_t2_manual_20261101_1000.json --meta data/carmanager_raw/t2_captures/janghanpyeong_t2_manual_20261101_1000.meta.json
```

---

## 4. T2 인입 시 필수 출력 지표 사양
수동 캡처된 T2 데이터가 파이프라인에 투입되면 다음 5대 핵심 지표가 즉시 리포팅됩니다:
1. **고유 매물 ID 수 (Total Unique Listings in T2):** 캡처 파일 내 정규화된 유효 매물 건수.
2. **기존 T1에 존재한 ID 수 (Existing in T1 Baseline):** 과거 1,764대 마스터에 이미 등록되어 체류일수가 누적되는 매물 수.
3. **T1 대비 새롭게 확인된 ID 수 (New Discovered in T2):** 과거에 없다가 신규 등장(Appeared)한 매물 수.
4. **동일 ID에서 확인된 가격 변경 수 (Price Changed):** T1 대비 인상/인하가 확인된 매물 수.
5. **비교 불가능하거나 정보가 부족한 ID 수 (Uncomparable/Invalid):** 필수 필드(식별자 또는 가격)가 결측된 매물 수.

---

## 5. 원본 부재 시의 시스템 원칙
- 실제 운영자 브라우저에서 상기 절차로 캡처된 신선한 T2 원본이 인입되기 전까지, 시스템은 과거 데이터를 최신 관측으로 위장하거나 임의 날짜를 생성하지 않으며 **`REAL_PILOT_PENDING_NEW_CAPTURE`** 상태를 엄격히 유지합니다.
