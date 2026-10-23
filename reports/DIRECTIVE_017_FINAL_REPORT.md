# CHA-FICIAL DIRECTIVE 017: DEALER PILOT EXECUTION & REAL-WORLD VALIDATION FINAL REPORT

## 1. 개요 및 실행 배경
- **지침명**: CHA-FICIAL DIRECTIVE 017: DEALER PILOT EXECUTION & REAL-WORLD VALIDATION
- **기준 브랜치**: `feat/directive-009-price-event-tracker` (PR #12, PR #13 병합 완료 Commit: `c4ce84c`)
- **작업 브랜치**: `feat/directive-017-dealer-pilot-execution`
- **핵심 목표**: 
  1. 25년 경력 장안평 수석 딜러 파트너 실전 평가 패키지 3종 완비
  2. 지역 적합성 3단계 분리 및 데이터 한계 투명성 공시
  3. 피드백 입력 유효성 검증(VERDICT 허용값, 음수 차단, 필수 사유) 체계 구축
  4. 재평가 시 덮어쓰지 않는 이력(History) 누적 보존 구조 및 CSV 피드백 로더 구현
  5. 실제 딜러 회신(`is_pilot_actual=True`)과 테스트 목업 분리 및 정직한 평가 대기(`PENDING_DEALER_REVIEW`) 상태 공시

---

## 2. 딜러 실전 파일럿 패키지 3종 상세

| 패키지 구성물 | 파일 경로 | 포맷 및 인코딩 | 주요 내용 |
| :--- | :--- | :--- | :--- |
| **1. 딜러 브리핑 문서** | `reports/pilot/dealer_pilot_briefing.md` | Markdown (UTF-8) | 파일럿 배경, 8대 후보 개요, 평가 항목 가이드, 주의사항 안내 |
| **2. 실전 검토표** | `reports/pilot/dealer_pilot_review_8.csv` | CSV (UTF-8 with BOM) | 우선 검토 8대 상세 스펙, AI 호가, 코호트 중앙값, 격차율, 가상순수익, 엔카 실차 URL, 지역 적합성 |
| **3. 회신 템플릿** | `reports/pilot/dealer_pilot_feedback_template.csv` | CSV (UTF-8 with BOM) | 딜러 평가 입력 양식 (`dealer_verdict`, 예상 매입/판매/상품화 비용, 판단 사유) |

> **인코딩 안내**: 한국어 MS Excel 더블 클릭 시 글자 깨짐이 없도록 두 CSV 파일 모두 UTF-8 with BOM(`\ufeff`)으로 제작되었습니다.

---

## 3. 우선 검토 8대 후보 및 지역 적합성(3단계) 분류 현황

수집된 엔카 관측 데이터(총 348대)의 `raw_location` 필드 전수 조사 결과, **서울/수도권 명시 매물이 0건**으로 확인되었습니다. 따라서 무리하게 장안평 즉시 매입 가능 매물로 포장하지 않고, 3단계 분류 체계에 따라 정직하게 분류하여 딜러 파트너에게 전달했습니다:

| 순위 | 매물 식별자 (CarID) | 연식/주행거리 | AI 관측가 | 코호트 중앙가 | 가격 격차율 | 가상 순수익 | 지역 분류 (`raw_location`) | 지역 적합성 등급 | 엔카 실차 확인 URL |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | 42969608 | 2024년식 / 42,076km | 1,690만 | 2,190만 | -22.8% | +415만 | 미기재 (`None`) | `LOCATION_UNVERIFIED` | [엔카 바로가기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42969608) |
| **2** | 41366410 | 2024년식 / 53,382km | 1,499만 | 2,190만 | -31.6% | +587만 | 미기재 (`None`) | `LOCATION_UNVERIFIED` | [엔카 바로가기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=41366410) |
| **3** | 42706751 | 2024년식 / 35,192km | 1,874만 | 2,190만 | -14.4% | +249만 | 미기재 (`None`) | `LOCATION_UNVERIFIED` | [엔카 바로가기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42706751) |
| **4** | 42814110 | 2024년식 / 10,057km | 2,120만 | 2,190만 | -3.2% | +28만 | 대구 | `REMOTE_MARKET_REFERENCE` | [엔카 바로가기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42814110) |
| **5** | 42811604 | 2024년식 / 84,331km | 1,590만 | 2,190만 | -27.4% | +505만 | 충북 | `REMOTE_MARKET_REFERENCE` | [엔카 바로가기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42811604) |
| **6** | 42671808 | 2024년식 / 81,603km | 1,590만 | 2,190만 | -27.4% | +505만 | 충북 | `REMOTE_MARKET_REFERENCE` | [엔카 바로가기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42671808) |
| **7** | 42911910 | 2024년식 / 46,530km | 2,149만 | 2,190만 | -1.9% | +2만 | 충남 | `REMOTE_MARKET_REFERENCE` | [엔카 바로가기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42911910) |
| **8** | 42863742 | 2024년식 / 31,066km | 2,190만 | 2,190만 | 0.0% | -35만 | 광주 | `REMOTE_MARKET_REFERENCE` | [엔카 바로가기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42863742) |

- **지역 분류 집계**:
  - `LOCAL_VERIFIED` (서울/장안평 매물): **0건**
  - `LOCATION_UNVERIFIED` (지역 미확인 - 딜러 실사 필요): **3건**
  - `REMOTE_MARKET_REFERENCE` (원거리 참고 매물 - 지방 시세 벤치마크): **5건**

---

## 4. 피드백 수집 및 유효성 검증 체계 강화 (`dealer_pilot.py`)

1. **엄격한 VERDICT 허용값 검증**:
   - `BUY_REVIEW` (매입 검토), `WATCH` (추가 관찰), `EXCLUDE` (제외) 3가지 값만 허용.
   - `BUY`, `PASS`, `HOLD`, `APPROVE` 등 비표준 입력 시 즉시 `ValueError` 차단.
2. **금액 필드 음수 입력 차단**:
   - `dealer_expected_purchase_krw >= 0`
   - `dealer_expected_sale_krw >= 0`
   - `dealer_expected_reconditioning_cost_krw >= 0`
   - 음수 값 입력 시 `ValueError` 발생.
3. **딜러 판단 사유 필수 입력 검증**:
   - 공백이나 누락 시 `ValueError` 발생으로 데이터 신뢰성 확보.
4. **CSV 회신 파일 로더 (`load_feedback_from_csv`) 구현**:
   - 엑셀 및 텍스트 편집기 호환(`utf-8-sig` / `utf-8`) 자동 감지.
   - 쉼표(`,`) 및 원화 기호 자동 제거 및 정수 파싱.
   - 미작성 행 자동 필터링 및 유효 행 정밀 인입.
5. **재평가 이력(History) 누적 보존 구조**:
   - 기존 JSON 파일이 존재할 경우 기존 데이터를 덮어쓰지 않고 `combined = existing_data + new_data` 구조로 누적 보존.
6. **실제 데이터와 목업 분리 플래그 (`is_pilot_actual`)**:
   - 단위 테스트용 mock 데이터(`is_pilot_actual=False`)와 실제 딜러의 피드백(`is_pilot_actual=True`)을 엄격히 분리하여 성과 지표 산출.

---

## 5. 파일럿 성과 지표 및 현재 진행 상태 공시

- **현재 파일럿 상태**: **`PENDING_DEALER_REVIEW` (딜러 실전 평가 대기)**
- **정직한 현황 공시**:
  - 현재 실제 수석 딜러 파트너에게 패키지 3종이 배포 대기 상태이며, 실제 딜러 회신이 완료되기 전까지는 임의의 가짜 합격률을 조작하지 않고 `PENDING_DEALER_REVIEW` 상태를 유지합니다.
  - 딜러 파트너가 `dealer_pilot_feedback_template.csv`를 작성하여 전달하면 즉시 `load_feedback_from_csv()` 및 `calculate_performance()`를 호출하여 공식 실전 적중률(`hit_ratio_pct`) 및 가격 오차(`avg_price_difference_krw`)를 산출할 준비가 완료되었습니다.

---

## 6. 품질 검증 및 회귀 테스트 결과

- **전체 pytest 회귀 테스트**: **215개 테스트 ALL PASS (100% 통과, 5.98초)**
  - 신규 `test_directive_017_dealer_pilot_execution.py` 6개 테스트 ALL PASS
  - 기존 209개 테스트(스케줄러, 지문 클러스터링, 다이나믹 시나리오, DB 무결성 등) 100% 통과
- **운영 DB 무결성 검증 (`verify_directive_012b.py`)**:
  - 원본 JSON 해시(SHA-256: `da72c658...`) 100% 일치
  - 가격 인하 5건 3차 배치 귀속 및 원본 가격 1:1 대조 통과
  - 기존 스냅샷 246건 행 단위(Row-by-Row) 100% 불변 보존 통과
  - 운영 DB 레코드(348대 매물, 382건 스냅샷, 353건 이벤트) 완벽 보존 확인
