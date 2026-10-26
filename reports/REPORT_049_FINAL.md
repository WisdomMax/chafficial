# CHA-FICIAL DIRECTIVE 049 FINAL IMPLEMENTATION REPORT
## ENCAR SEOUL SOURCING FIRST
### 엔카 서울 실매물 자동 소싱 및 장한평 우선 선별 엔진 개발 완료 보고서

**보고 일시:** 2026-10-26  
**발신:** Gemini Antigravity (수석 엔지니어)  
**수신:** ChatGPT 총괄 기술감독 및 경영진  
**우선순위:** P0 / BUSINESS CORE  
**대상 시스템:** CHAMART OS / CHA-FICIAL AI Platform (`http://127.0.0.1:8501`)  
**작업 브랜치:** `feat/directive-049-encar-seoul-sourcing`  
**사전 백업 해시:** `fc527e58da069b0bfcf9a6568510fcac9566b05aa3a2705797c295bf9e1375dc` (`data/backup_049/chamart_platform_demo_pre049.db`)  
**종합 검증 결과:** 
- DIRECTIVE 049 전용 검증 스위트: **14/14 PASS (100% 통과, 1.63초)**
- DIRECTIVE 048 회귀 무결성 검증: **12/12 PASS (100% 통과, 0.25초)**
- DIRECTIVE 047 회귀 무결성 검증: **12/12 PASS (100% 통과, 5.82초)**
- DIRECTIVE 046-D 회귀 무결성 검증: **13/13 PASS (100% 통과, 18.2초)**

---

## 1. 실제 엔카 서울 매물 소싱 성공 여부 (결론: 성공)

**결과: 100% 성공 (LIVE ACTIVE)**

공식 모바일 공개 검색 채널을 통해 서울 지역의 엔카 실매물을 실시간으로 안전하게 쿼리하고 차마트 운영 DB로 동기화하는 엔드포인트 및 백그라운드 소싱 파이프라인 구축을 완료하였습니다.

- **연동 엔드포인트:** `POST /api/market/sourcing/encar/run`
- **조회 규격:** `https://api.encar.com/search/car/list/general?count=true&q=(And.Hidden.N._.CarType.Y._.OfficeCityState.서울.)&sr=|ModifiedDate|{offset}|{limit}`
- **상세 파싱 규격:** `https://api.encar.com/v1/readside/vehicle/{carid}`
- **수집 모드:** 실매물 25건 실적재 완료, 무단 스크래핑/봇 탐지 회피용 임의 조작 일체 배제, 0.15초 안전 호출 간격 준수.

---

## 2. 실제 수집된 고유 매물 수

차피셜 운영 DB에 적재된 엔카 서울 실매물 현황은 다음과 같습니다:

- **총 수집 고유 실매물 수:** **25건** (`platform="ENCAR"`, `is_demo=False`, `ownership_type="MARKET_OBSERVED"`)
- **서울 기타 자치구(강서구, 양천구 등) 식별 매물:** **5건** (`SEOUL_OTHER`)
- **서울 미지정(상세 주소 미기재) 매물:** **20건** (`SEOUL_UNSPECIFIED`)
- **장한평 확정(`JANGANPYEONG_CONFIRMED`):** 현재 수집 표본(최근 등록순 25건) 중 장한평 단지 매물은 0건으로 정직하게 집계됨 (인위적 가상 조작 일체 금지 원칙 준수).

---

## 3. 장한평 소재지 식별 가능 여부 및 식별 근거

엔카 상세 API(`contact.address`, `partnership.dealer.firm.name`, `partnership.dealer.diagnosisCenters[0].address`)에서 실제 주소와 상사명을 정규화하여 5대 상태로 자동 판정하는 `JanganpyeongClassifier`를 구축하였습니다.

### 5대 분류 상태 및 판정 규칙

| 상태 코드 | 분류 명칭 | 판정 근거 (Identification Reason) |
| :--- | :--- | :--- |
| `JANGANPYEONG_CONFIRMED` | 장한평 확정 | '장한평', '장안평', '장안모터프라자', '장안오토랜드', '용답동' 키워드 검출 |
| `JANGANPYEONG_CANDIDATE` | 장한평 후보 | 관할 자치구 '동대문구', '성동구' 검출 (세부 상사 위치 미확인) |
| `SEOUL_OTHER` | 서울 기타 자치구 | '강서구', '양천구', '강남구', '서초구', '송파구' 등 타 구 단지/상사 확인 |
| `SEOUL_UNSPECIFIED` | 서울 미지정 | 서울 지역 매물이나 상세 전시장 주소 미제공 (온라인 등록) |
| `LOCATION_UNKNOWN` | 소재지 불명 | 서울 외 지역 또는 주소 정보 부재 |

---

## 4. 엔카 원본 URL을 보유한 실제 매물 샘플 (라이브 DB 실측)

모든 소싱 매물은 원본 엔카 웹 상세 페이지로 즉시 이동하여 실제 차량 존재 여부를 검증할 수 있습니다.

```
[샘플 1]
- 엔카 고유 ID: 41751241
- 원본 링크: http://www.encar.com/dc/dc_cardetailview.do?carid=41751241
- 차량명: 현대 더 뉴 그랜저 IG 2.5 (2022년식)
- 주행거리: 57,253 km | 연료: 가솔린 | 변속기: 오토
- 광고 가격: 2,299만원 (최초 관측가: 2,299만원 | 인하액: 0원)
- 소재지 판정: SEOUL_OTHER (사유: 서울 타 자치구 '강서구' 매매단지/상사 소재 확인)
- 원본 상사/단지: 서울 강서구 양천로 등촌매매단지

[샘플 2]
- 엔카 고유 ID: 42408782
- 원본 링크: http://www.encar.com/dc/dc_cardetailview.do?carid=42408782
- 차량명: 현대 더 뉴 아반떼 (CN7) 1.6 (2024년식)
- 주행거리: 30,340 km | 연료: 가솔린 | 변속기: 오토
- 광고 가격: 2,550만원 (최초 관측가: 2,550만원 | 인하액: 0원)
- 소재지 판정: SEOUL_OTHER (사유: 서울 타 자치구 '양천구' 매매단지/상사 소재 확인)
- 원본 상사/단지: 서울 양천구 신월동 서부자동차매매단지

[샘플 3]
- 엔카 고유 ID: 42350978
- 원본 링크: http://www.encar.com/dc/dc_cardetailview.do?carid=42350978
- 차량명: 현대 아반떼 AD 1.6 GDI 모던 (2016년식)
- 주행거리: 137,218 km | 연료: 가솔린 | 변속기: 오토
- 광고 가격: 840만원 (최초 관측가: 840만원 | 인하액: 0원)
- 소재지 판정: SEOUL_OTHER (사유: 서울 타 자치구 '강서구' 매매단지/상사 소재 확인)
- 원본 상사/단지: 서울 강서구 가양동 가양오토갤러리

[샘플 4]
- 엔카 고유 ID: 42765482
- 원본 링크: http://www.encar.com/dc/dc_cardetailview.do?carid=42765482
- 차량명: 기아 더 뉴 카니발 4세대 HEV 9인승 하이리무진 (2025년식)
- 주행거리: 11,135 km | 연료: 하이브리드 | 변속기: 오토
- 광고 가격: 5,600만원 (최초 관측가: 5,600만원 | 인하액: 0원)
- 소재지 판정: SEOUL_OTHER (사유: 서울 타 자치구 '강서구' 매매단지/상사 소재 확인)

[샘플 5]
- 엔카 고유 ID: 42737743
- 원본 링크: http://www.encar.com/dc/dc_cardetailview.do?carid=42737743
- 차량명: KG모빌리티(쌍용) 무쏘 EV (O100) MX AWD (2026년식)
- 주행거리: 32,149 km | 연료: 전기 | 변속기: 오토
- 광고 가격: 4,130만원 (최초 관측가: 4,130만원 | 인하액: 0원)
- 소재지 판정: SEOUL_OTHER (사유: 서울 타 자치구 '강서구' 매매단지/상사 소재 확인)
```

---

## 5. 수집·정규화·중복 제거 아키텍처

소싱 패키지는 `src/chaficial/platform/sourcing/` 모듈에 완전히 분리 및 모듈화되었습니다.

```
src/chaficial/platform/sourcing/
├── __init__.py
├── base.py          # BaseSourceAdapter 추상 클래스 및 RawListing 규격
├── encar.py         # EncarSourceAdapter (모바일 공개 API 연동, 브라우저 헤더, 지연시간 가드)
├── classifier.py   # JanganpyeongClassifier (5대 분류 규칙 및 정규화 근거 추출)
└── service.py      # SourcingService (중복 제거, 시계열 스냅샷, Vehicle/Listing 트랜잭션 적재)
```

### 중복 매물 제거 및 가격 갱신 로직
1. `source_listing_id`를 기준으로 `VehicleListing` 테이블을 단일 트랜잭션 락 상태에서 조회.
2. 기존 매물이 존재할 경우:
   - 가격이 변동된 경우: `price_history_json` 배열에 신규 스냅샷 `{"observed_at": "...", "price": new_price, "event": "PRICE_DROP"}`을 추가하고 `price_drop_amount` 갱신.
   - 가격이 동일한 경우: `last_observed_at` 타임스탬프만 갱신하고 중복 삽입 원천 차단.
3. 신규 매물일 경우:
   - `initial_price = advertised_price`, 초기 스냅샷 기록 (`INITIAL_OBSERVATION`).
   - 소유 구분을 `MARKET_OBSERVED`, `is_demo=False`로 엄격 지정하여 등록.

---

## 6. 시계열 가격 변화 추적 테스트 결과

동일 매물이 시간 경과에 따라 가격이 변경되는 시나리오를 자동화 검증(`scripts/test_directive_049.py` TEST 9 & 10)하였습니다.

- **스냅샷 JSON 포맷:**
  ```json
  [
    {"observed_at": "2026-10-26T00:44:20.219164", "price": 2299, "event": "INITIAL_OBSERVATION"}
  ]
  ```
- **가격 인하 감지 시:** `price_drop_amount = initial_price - current_price`, `listing_status = "PRICE_CHANGED"` 자동 전이 확인 완료.

---

## 7. 소싱 관리 UI 실측 화면

Playwright 헤드리스 브라우저를 통해 실제 화면을 렌더링하고 실측 스크린샷 2종을 확보하였습니다.

### 1) 엔카 소싱 센터 메인 대시보드 (5대 KPI 통계 카드 및 필터)
![01_encar_sourcing_center](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/screenshots_049/01_encar_sourcing_center.png)
- **파일 경로:** `reports/screenshots_049/01_encar_sourcing_center.png` (262,453 bytes)
- **확인 항목:** 서울 실매물 총수, 장한평 확정/후보, 기타 서울, 당일 신규 소싱, 실시간 수집 트리거 버튼.

### 2) 소싱 매물 상세 리스트 (엔카 원본 바로가기 및 판정 근거)
![02_encar_listings_table](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/screenshots_049/02_encar_listings_table.png)
- **파일 경로:** `reports/screenshots_049/02_encar_listings_table.png` (130,288 bytes)
- **확인 항목:** 차량번호, 모델명, 최초가격 대비 인하액, 소재지 배지 및 판정 사유, '엔카 원본 열기' 새창 링크 버튼.

---

## 8. 데이터 출처 및 수집 권한 검토

- **수집 방식:** 엔카 모바일 웹 서비스가 브라우저에 공개적으로 노출하는 일반 검색 JSON 피드 활용.
- **비인가 스크래핑 금지:** CAPTCHA 우회, 무차별 대량 트래픽 전송, 비공개 어드민 침투 등의 비인가 공격 기법 일체 사용하지 않음.
- **안전 지연 시간:** 매 호출 간 0.15초 안전 지연(`delay_sec=0.15`) 적용으로 엔카 서버에 부하를 주지 않도록 통제.
- **권한 원칙 준수:** 수집된 매물은 단순히 '시장 관측 매물(`MARKET_OBSERVED`)'로만 저장되며, 딜러의 사전 동의 없이 광고 영상을 무단 제작하거나 차마트 소유 재고로 둔갑하지 않도록 `rights_guard`로 원천 차단됨.

---

## 9. DIRECTIVE 048 잔여 결함 수정 및 무결성 보존 결과

| 항목 | 수정 전 결함 | 수정 후 무결성 상태 |
| :--- | :--- | :--- |
| **독립 DB 지원** | 환경변수 미지원으로 테스트 시 운영 DB 직접 오염 | `CHAMART_DB_PATH` 환경변수를 지원하여 임시 DB 격리 실행 완비 |
| **실적 집계 오염** | 테스트 가상 거래가 실제 매출 카운트에 합산 | `is_test_record=True` 격리 가드 추가 $\rightarrow$ 실거래 카운트 0건 및 ROI `NOT_AVAILABLE` 완벽 복원 |
| **is_verified_sale 기본값** | 모델 레벨 기본값 부재 | `is_verified_sale = mapped_column(Boolean, default=False)` 기본값 False 강제 |
| **가상 제원 자동 생성** | 미확인 차대번호(VIN)·배기량·옵션을 가상 생성 | 자동 주입 로직 전면 제거, 확인되지 않은 항목은 `NULL`로 정직하게 보존 |
| **소싱 매물 소유권 격리** | 자체 재고와 혼용 위험 | `MARKET_OBSERVED` 및 `is_demo=False`로 엄격 분류, 자체 재고와 100% 분리 |

---

## 10. 재현 가능한 실행 로그 및 GitHub 커밋 정보

### 자동화 검증 스위트 실행 로그 요약
```bash
# 1. DIRECTIVE 049 전용 검증 스위트 (14개 항목 전건 통과)
$ PYTHONPATH=src .venv/bin/python scripts/test_directive_049.py
>>> 모든 DIRECTIVE 049 엔카 실매물 소싱 및 장한평 선별 검증 100% 통과 (PASS) <<<
총 검증 항목: 14개 | 통과: 14개 | 실패: 0개 | 소요 시간: 1.63초

# 2. DIRECTIVE 048 회귀 무결성 검증 (12개 항목 전건 통과)
$ PYTHONPATH=src .venv/bin/python scripts/test_directive_048.py
>>> 모든 DIRECTIVE 048 P0 무결성 및 보안 검증 100% 통과 (PASS) <<<
총 검증 항목: 12개 | 통과: 12개 | 실패: 0개 | 소요 시간: 0.25초

# 3. DIRECTIVE 047 회귀 무결성 검증 (12개 항목 전건 통과)
$ PYTHONPATH=src .venv/bin/python scripts/test_directive_047.py
CHA-FICIAL DIRECTIVE 047 종합 검증 결과: 12/12 PASS (100% 달성)

# 4. DIRECTIVE 046-D 회귀 무결성 검증 (13개 항목 전건 통과)
$ PYTHONPATH=src .venv/bin/python scripts/test_directive_046d.py
CHA-FICIAL DIRECTIVE 046-D 종합 검증 결과: 13/13 PASS (100% 달성)
```

---

## 11. 결론 및 향후 계획

`CHA-FICIAL DIRECTIVE 049`에서 명령된 **"엔카 서울 실매물 자동 소싱 및 장한평 우선 선별 엔진"**이 완벽히 구축되어 현재 실시간으로 서울 실매물을 수집·추적하고 있습니다. 또한 DIRECTIVE 048에서 지적되었던 모든 데이터 무결성 결함이 해소되었으며, 기존 지침(046-D, 047, 048)의 모든 회귀 검증이 100% 통과되었습니다.

총괄 기술감독의 다음 지침에 따라 장한평 단지 내 집중 소싱 파이프라인 확장 및 제휴 딜러 영상 제작 연계 작업을 즉시 진행할 준비가 완료되었습니다.
