# DIRECTIVE 016: DEALER PILOT READINESS REPORT (PR #13 공식 병합 및 딜러 파일럿 검증 준비 완료 보고서)

## 1. GitHub PR #13 공식 병합 완료 (지침 1 준수)
- **PR 공식 URL**: https://github.com/WisdomMax/chafficial/pull/13
- **PR 최종 상태**: **`CLOSED / MERGED`** (`state: closed`, `merged: true`)
- **실제 Merge Commit SHA**: `c4ce84cb3238809fd173ebe847f6fae6f9ac246a`
- **병합 대상 (Base) 브랜치**: `feat/directive-009-price-event-tracker`
- **병합 소스 (Head) 브랜치**: `feat/directive-015-opportunity-intelligence-v1` (`15a9db5a657807d21b5c559dface681e4e9135a0`)
- **원격 반영 완료**: `origin/feat/directive-009-price-event-tracker`에 공식 병합 반영 완료

---

## 2. 딜러 파일럿 우선 검토 8대 실전 평가표 (지침 2 준수)

> [!IMPORTANT]
> **실전 파일럿 주의사항**:
> 1. 본 파일럿은 AI의 매입 추천을 무조건 신뢰하는 것이 아니라, **25년 경력 전문가 딜러의 검증을 통해 알고리즘의 실전 적합성을 측정·보정하는 단계**입니다.
> 2. 관측 데이터 상 지역이 `UNKNOWN`인 매물은 매입 확정 대상이 아니며, **지역 실사(전화/서류 확인)를 선행**해야 합니다.
> 3. 대구/대전 등 원거리 매물은 시장 분석 대상이며, 서울 장안평 파트너의 즉시 매입 대상과 구분하여 취급합니다.

| 순위 | 매물 ID | 차량 정보 | 현재 호가 | 코호트 시세(중앙) | 가격 우위 | 기회 점수 | 가정 순이익 (목표50만 초과분) | 지역 (영업 적합성) | 필수 실사 항목 | 엔카 원본 링크 |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: |
| 1 | `42969608` | 현대 아반떼 CN7<br>(2024년식, 42,076km) | 1,690만원 | 2,235만원 | **+24.4%** | **75.0점** | **4,150,000원**<br>(+365만원) | UNKNOWN<br>(`LOCATION_VERIFY`) | 보험사고/용도이력 실사필요<br>지역 소재지 유선 확인 | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42969608) |
| 2 | `41366410` | 현대 아반떼 CN7<br>(2024년식, 53,382km) | 1,499만원 | 1,855만원 | **+19.2%** | **75.0점** | **2,260,000원**<br>(+176만원) | 대구<br>(`REMOTE_UNSUITABLE`) | 지방 탁송료(+20만) 감안<br>성능점검 골격 수리 여부 | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=41366410) |
| 3 | `42706751` | 현대 아반떼 CN7<br>(2024년식, 35,192km) | 1,874만원 | 2,235만원 | **+16.2%** | **75.0점** | **2,310,000원**<br>(+181만원) | UNKNOWN<br>(`LOCATION_VERIFY`) | 3.5만km 짧은 주행 실차확인<br>단순교환 외판 유무 | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42706751) |
| 4 | `42814110` | 현대 아반떼 CN7<br>(2024년식, 10,057km) | 2,120만원 | 2,390만원 | **+11.3%** | **73.7점** | **1,400,000원**<br>(+90만원) | UNKNOWN<br>(`LOCATION_VERIFY`) | 1만km 신차급 컨디션 확인<br>제조사 보증 잔여 확인 | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42814110) |
| 5 | `42811604` | 현대 아반떼 CN7<br>(2024년식, 84,331km) | 1,590만원 | 1,855만원 | **+14.3%** | **73.0점** | **1,350,000원**<br>(+85만원) | 대전<br>(`REMOTE_UNSUITABLE`) | 8.4만km 가성비 회전율 검토<br>렌트이력(용도변경) 여부 | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42811604) |
| 6 | `42671808` | 현대 아반떼 CN7<br>(2024년식, 81,603km) | 1,590만원 | 1,855만원 | **+14.3%** | **73.0점** | **1,350,000원**<br>(+85만원) | 대전<br>(`REMOTE_UNSUITABLE`) | 8.1만km 가성비 회전율 검토<br>하체 부식/누유 점검 | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42671808) |
| 7 | `42911910` | 현대 아반떼 CN7<br>(2024년식, 46,530km) | 2,149만원 | 2,390만원 | **+10.1%** | **69.8점** | **1,110,000원**<br>(+61만원) | 대전<br>(`REMOTE_UNSUITABLE`) | 중복광고(`42906948`) 단일화<br>하이브리드 배터리 상태 | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42911910) |
| 8 | `42863742` | 현대 아반떼 CN7<br>(2024년식, 31,066km) | 2,190만원 | 2,390만원 | **+8.4%** | **57.8점** | **700,000원**<br>(+20만원) | 대전<br>(`REMOTE_UNSUITABLE`) | 중복광고(`42866420`) 단일화<br>하이브리드 인기 트림 확인 | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42863742) |

---

## 3. 전문가 피드백 수집 체계 및 데이터 보존 (지침 3 준수)
- **독립 저장소 완비**:
  - 기존 관측 원본 데이터 및 운영 DB와 100% 분리된 **`data/dealer_feedback/dealer_pilot_feedback_YYYYMMDD.json`** 경로에 보존.
  - 관리 모듈: `src/chaficial/intelligence/dealer_pilot.py` (`DealerPilotManager`)
- **딜러 실전 입력 스키마**:
  1. `dealer_verdict`: `BUY_REVIEW` (매입검토) / `WATCH` (관찰) / `EXCLUDE` (제외)
  2. `dealer_expected_purchase_krw`: 딜러 판단 실제 매입 가능 금액 (원)
  3. `dealer_expected_sale_krw`: 딜러 판단 실제 판매 가능 금액 (원)
  4. `dealer_expected_reconditioning_cost_krw`: 딜러 판단 상품화 소요비용 (원)
  5. `dealer_decision_reason`: 판단 이유 (예: "용도이력 대비 가격 적정", "골격 사고 의심으로 제외" 등)
  6. `reviewed_at`: 평가 일시

---

## 4. 파일럿 성과 측정 정의 (지침 4 준수)
- **적중률 (Hit Ratio, %)**: 상위 8대 중 딜러가 실전 매입 가치(`BUY_REVIEW`)를 인정한 비율
  $$\text{Hit Ratio (\%)} = \frac{\text{BUY\_REVIEW 건수}}{\text{총 검토 매물 수 (8대)}} \times 100$$
- **가격 편차 (Price Deviation, 원)**: AI 호가 매입가 vs 딜러 예상 매입가 편차
  $$\Delta \text{Purchase} = \text{AI Observed Price} - \text{Dealer Expected Price}$$
- **추천 제외 사유 분류**: 사고 의심, 용도 이력, 시세 대비 마진 부족, 원거리 물류비 과다 등
- **검증 불가 건수 집계**: 지역 미확인으로 유선 확인 실패 또는 이미 판매 종료(DELISTED)된 매물 집계

---

## 5. 전체 테스트 및 운영 데이터 무결성 검증 (100% ALL PASS)
- **전체 pytest 실행 결과**: **209개 테스트 100% 통과** (`209 passed in 5.51s`)
  - 신규 딜러 파일럿 수집 및 성과 분석 테스트 2개(`tests/test_directive_016_dealer_pilot.py`) 포함 전수 통과
- **운영 DB 및 관측 원본 불변 영구 보존**:
  - `scripts/verify_directive_012b.py` 100% ALL PASS
  - `listings`: 348대, `listing_snapshots`: 382건, `price_events`: 353건, `batch_audit_logs`: 3회 보존
  - 원본 JSON 관측 파일 3건 SHA-256 해시 일치 확인
- **운영 제한 준수**: LIVE 수집 비활성화, 운영 DB 변경 원천 차단 상태 유지

---

## 6. 결론 및 딜러 파일럿 실전 피드백 수집 착수 제언
- PR #13이 GitHub 상에서 공식적으로 **`CLOSED / MERGED`** 되었으며, 베이스 브랜치(`feat/directive-009-price-event-tracker`)에 완전히 통합되었습니다.
- 총괄 감독(ChatGPT)님의 지침에 따라 딜러 파일럿 8대 검토표와 독립 피드백 수집 체계가 완비되었습니다.
- 본 검토표를 바탕으로 25년 경력 딜러 파트너에게 전달하여 실전 평가 피드백 데이터를 축적하는 후속 절차를 지시해 주시기를 요청드립니다!
