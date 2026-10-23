# DIRECTIVE 015-B FINAL MERGE GATE REPORT (최종 병합 게이트 및 딜러 파일럿 준비 완료 보고서)

## 1. GitHub PR #13 현황 및 핵심 3자 SHA 100% 일치 증명
- **공식 PR URL**: https://github.com/WisdomMax/chafficial/pull/13
- **PR 번호**: **#13** (`state: open`, `mergeable: true`, 충돌 없음)
- **기준(Base) 브랜치**: `feat/directive-009-price-event-tracker`
- **작업(Head) 브랜치**: `feat/directive-015-opportunity-intelligence-v1`
- **로컬 브랜치 HEAD SHA**: `732d5304807ebc6a92440a0e471f9eb6a9a938e9`
- **원격 브랜치 HEAD SHA**: `732d5304807ebc6a92440a0e471f9eb6a9a938e9`
- **GitHub PR #13 HEAD SHA**: `732d5304807ebc6a92440a0e471f9eb6a9a938e9`
- **PR 설명 갱신 완료**: 8대 우선 추천, 207개 테스트 통과 수치로 GitHub PR 설명 동기화 완료

---

## 2. DIRECTIVE 015-B 4대 필수 지침 완료 내역

### 2.1 [지침 1] 동일 시각 스냅샷 중복 조회 SQL 수정 (결정적 단일 행 보장)
- **원인 분석**:
  - `s.observed_at = (SELECT MAX(s2.observed_at) ...)` 조건은 동일 시각(`observed_at`)에 복수 스냅샷이 존재할 경우 단일 매물에 대해 여러 행이 조인될 수 있는 취약점이 있었습니다.
- **수정 완료 (CTE `ROW_NUMBER()` 도입)**:
  - SQLite 3.25+ 지원 윈도우 함수를 사용하여 완벽한 결정적 단일 행 선택을 보장하였습니다.
```sql
WITH ranked_snapshots AS (
    SELECT 
        snapshot_id,
        listing_id,
        observed_at,
        price_krw,
        mileage_km,
        raw_specs,
        ROW_NUMBER() OVER (
            PARTITION BY listing_id 
            ORDER BY observed_at DESC, snapshot_id DESC
        ) as rn
    FROM listing_snapshots
    WHERE observed_at <= ?
)
SELECT ...
FROM listings l
JOIN ranked_snapshots s ON s.listing_id = l.listing_id AND s.rn = 1
WHERE l.first_observed_at <= ?
```
- **회귀 테스트 통과**: 동일 시각 스냅샷 2개 주입 시 타이브레이커(`snapshot_id DESC`)에 의해 정확히 1행만 반환됨을 검증(`test_same_timestamp_snapshots_returns_exactly_single_row` PASS).

### 2.2 [지침 2] 중복 광고 판정 신뢰 수준 분리 및 민감도 분석
- **신뢰 수준 명확화**:
  - `CONFIRMED_DUPLICATE`: 차량등록번호, 차대번호(VIN) 등 독립 고유 식별자가 일치하는 경우 (현재 엔카 공개 데이터에는 미포함)
  - `POSSIBLE_DUPLICATE`: 동일 물리 지문(`vehicle_fingerprint`: 연식/트림/주행거리/등록연월 등)이 일치하나 독립 식별 근거가 없는 '지문 기반 추정 중복' (116건)
  - `NO_DUPLICATE_DETECTED`: 중복 의심 없음
- **민감도 분석 보고**:
  - **클러스터링 적용 시 (현재)**: 고유 실차 232대 기준, 코호트 중앙값 왜곡 차단 $\rightarrow$ `PRIORITY_REVIEW` **8대** 선정.
  - **개별 매물 미클러스터링 시**: 중복 등록된 매물(`42911910`/`42906948`, `42863742`/`42866420`)이 추천 목록에 2번씩 중복 노출되고 코호트 표본 수가 인위적으로 부풀려져 딜러 검토의 혼란을 초래함을 확인.

### 2.3 [지침 3] 수익 추정 표현 정정 (가정 기반 수익 명시)
- **표현 및 필드명 전면 개편**:
  - `hypothetical_gross_spread_krw`: 가정 총마진 (예상 판매가 - 호가 매입가)
  - `hypothetical_operating_cost_krw`: 가정 실제 운영비용 (상품화비 80만 + 탁송비 30만)
  - `hypothetical_net_profit_krw`: 가정 순이익 (실제 확정 수익이 아닌 가정치)
  - `target_margin_krw`: 목표 마진 기준치 (500,000원, 비용이 아님)
  - `excess_over_target_krw`: 목표 마진 초과 달성분
- **미반영 비용 고지**: 취득세, 매매상사 법정 수수료, 금융/이자비용, 재고보유비용(주차비 등) 미반영 한계를 CSV 및 보고서에 명기.

### 2.4 [지침 4] 딜러 파일럿 실전 검토표 및 피드백 양식 완비
- 딜러 전달용 CSV(`reports/opportunities/opportunity_candidates_20261024.csv`)에 25년 경력 딜러 파트너의 실전 평가 입력 컬럼 완비:
  - `dealer_review_verdict`: 매입검토 / 관찰 / 제외
  - `dealer_expected_purchase_price_krw`: 딜러 예상 매입 가능가
  - `dealer_expected_sale_price_krw`: 딜러 예상 판매 가능가
  - `dealer_expected_reconditioning_cost_krw`: 딜러 판단 상품화 소요비용
  - `dealer_decision_reason`: 판단 이유
  - `dealer_reviewed_at`: 검토 일시

---

## 3. 정제된 우선 검토 (`PRIORITY_REVIEW`) 8대 실전 딜러 파일럿 후보

| 순위 | 매물 ID | 차량 요약 | 현재 호가 | 코호트 시세 | 가격 우위 | 기회 점수 | 가정 순이익 | 목표초과분 | 지역 (영업 적합성) | 엔카 매물 링크 |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | `42969608` | 현대 아반떼 CN7 (2024년식, 42,076km) | 1,690만원 | 2,235만원 | **+24.4%** | **75.0점** | **4,150,000원** | +365만원 | UNKNOWN (`LOCATION_VERIFY`) | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42969608) |
| 2 | `41366410` | 현대 아반떼 CN7 (2024년식, 53,382km) | 1,499만원 | 1,855만원 | **+19.2%** | **75.0점** | **2,260,000원** | +176만원 | 대구 (`REMOTE_UNSUITABLE`) | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=41366410) |
| 3 | `42706751` | 현대 아반떼 CN7 (2024년식, 35,192km) | 1,874만원 | 2,235만원 | **+16.2%** | **75.0점** | **2,310,000원** | +181만원 | UNKNOWN (`LOCATION_VERIFY`) | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42706751) |
| 4 | `42814110` | 현대 아반떼 CN7 (2024년식, 10,057km) | 2,120만원 | 2,390만원 | **+11.3%** | **73.7점** | **1,400,000원** | +90만원 | UNKNOWN (`LOCATION_VERIFY`) | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42814110) |
| 5 | `42811604` | 현대 아반떼 CN7 (2024년식, 84,331km) | 1,590만원 | 1,855만원 | **+14.3%** | **73.0점** | **1,350,000원** | +85만원 | 대전 (`REMOTE_UNSUITABLE`) | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42811604) |
| 6 | `42671808` | 현대 아반떼 CN7 (2024년식, 81,603km) | 1,590만원 | 1,855만원 | **+14.3%** | **73.0점** | **1,350,000원** | +85만원 | 대전 (`REMOTE_UNSUITABLE`) | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42671808) |
| 7 | `42911910` | 현대 아반떼 CN7 (2024년식, 46,530km) | 2,149만원 | 2,390만원 | **+10.1%** | **69.8점** | **1,110,000원** | +61만원 | 대전 (`REMOTE_UNSUITABLE`) | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42911910) |
| 8 | `42863742` | 현대 아반떼 CN7 (2024년식, 31,066km) | 2,190만원 | 2,390만원 | **+8.4%** | **57.8점** | **700,000원** | +20만원 | 대전 (`REMOTE_UNSUITABLE`) | [엔카 상세보기](https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid=42863742) |

---

## 4. 전체 테스트 및 운영 데이터 무결성 검증 (100% PASS)
- **전체 pytest 실행 결과**: **207개 테스트 100% ALL PASS** (`207 passed in 5.63s`)
  - 신규 CTE ROW_NUMBER() 동일 시각 스냅샷 단일 행 반환 테스트(`test_same_timestamp_snapshots_returns_exactly_single_row`) 포함 100% 통과
- **운영 DB 및 관측 원본 불변 영구 보존**:
  - `scripts/verify_directive_012b.py` 100% ALL PASS
  - `listings`: 348대, `listing_snapshots`: 382건, `price_events`: 353건, `batch_audit_logs`: 3회 100% 불변 보존
  - 원본 JSON 관측 파일 3건 해시 일치 확인

---

## 5. 결론 및 PR #13 최종 공식 병합 승인 요청
- 총괄 감독(ChatGPT)님의 DIRECTIVE 015-B 필수 요구사항(동일 시각 스냅샷 CTE 단일행 선택, 중복 신뢰 수준 분리, 수익 가정치 정정, 딜러 파일럿 입력표 완비, PR 본문 설명 갱신)을 100% 완비하였습니다.
- **GitHub PR #13의 최종 공식 코드 병합(Merge)을 승인해 주시기를 요청드립니다!**
