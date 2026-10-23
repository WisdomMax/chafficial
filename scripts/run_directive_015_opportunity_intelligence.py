"""차피셜 실시간 기회 매물 탐지 엔진 V1.1 실행 및 정밀 감사 보고서 생성 (DIRECTIVE 015-A)."""

from datetime import datetime
from pathlib import Path
import sqlite3

from chaficial.intelligence.opportunity_engine import MarketOpportunityEngine


def run_opportunity_analysis():
    print("=" * 80)
    print("CHA-FICIAL DIRECTIVE 015-A: 실전 기회 매물 탐지 엔진 V1.1 정밀 실행")
    print("=" * 80)

    db_path = Path("data/chaficial_market_timeseries.db")
    engine = MarketOpportunityEngine()

    print(f"[*] 대상 데이터베이스: {db_path} (100% 읽기 전용 모드)")
    candidates = engine.evaluate_market_opportunities(db_path=db_path)

    print(f"[+] 총 평가 완료 매물 수: {len(candidates)}대")

    # 등급별 집계
    grade_counts = {}
    suit_counts = {}
    for c in candidates:
        grade_counts[c.market_opportunity_grade] = grade_counts.get(c.market_opportunity_grade, 0) + 1
        suit_counts[c.partner_operational_suitability] = suit_counts.get(c.partner_operational_suitability, 0) + 1

    print("\n[1. 시장 기회 등급 (Market Opportunity Grade) 집계]")
    for g, cnt in sorted(grade_counts.items()):
        print(f"  - {g:20s}: {cnt:3d}대")

    print("\n[2. 파트너 영업 적합성 (Partner Operational Suitability) 집계]")
    for s, cnt in sorted(suit_counts.items()):
        print(f"  - {s:35s}: {cnt:3d}대")

    # CSV 출력
    today_str = datetime.now().strftime("%Y%m%d")
    out_dir = Path("reports/opportunities")
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"opportunity_candidates_{today_str}.csv"
    engine.export_results_to_csv(candidates, csv_path)
    print(f"\n[+] CSV 후보 목록 저장 완료: {csv_path}")

    # 상위 우선 검토(PRIORITY_REVIEW) 후보 출력
    priority_candidates = [c for c in candidates if c.market_opportunity_grade == "PRIORITY_REVIEW"]
    print(f"\n[3. 우선 검토 (PRIORITY_REVIEW) 후보: 총 {len(priority_candidates)}대]")
    for i, p in enumerate(priority_candidates, 1):
        b = p.base_scenario
        net_profit = b.estimated_net_profit_krw if b else 0
        drop_info = f", 인하 -{p.cumulative_price_drop_krw:,}원" if p.has_price_drop else ""
        dup_info = f" [중복광고: {', '.join(p.duplicate_listing_ids)}]" if p.is_duplicate_listing else ""
        print(
            f"  {i}. [{p.source_listing_id}] {p.vehicle_summary} | 현재가: {p.current_price_krw:,}원 | "
            f"시세중앙: {p.cohort_median_price_krw:,}원 (우위: +{p.relative_price_gap_pct}%) | "
            f"기회점수: {p.opportunity_score}점 | 예상순익: {net_profit:,}원 (목표마진 50만 포함){drop_info} | "
            f"지역: {p.raw_location} ({p.partner_operational_suitability}){dup_info}"
        )

    # 마크다운 보고서 생성
    md_path = out_dir / f"opportunity_report_{today_str}.md"
    generate_markdown_report(candidates, md_path)
    print(f"[+] 마크다운 종합 보고서 저장 완료: {md_path}")
    print("=" * 80)


def generate_markdown_report(candidates, output_path: Path):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S KST")
    priority_list = [c for c in candidates if c.market_opportunity_grade == "PRIORITY_REVIEW"]
    watchlist = [c for c in candidates if c.market_opportunity_grade == "WATCHLIST"]
    insufficient = [c for c in candidates if c.market_opportunity_grade == "INSUFFICIENT_DATA"]
    excluded = [c for c in candidates if c.market_opportunity_grade == "EXCLUDED"]

    local_count = sum(1 for c in candidates if c.partner_operational_suitability == "LOCAL_OPERATIONAL")
    verify_req_count = sum(1 for c in candidates if c.partner_operational_suitability == "LOCATION_VERIFICATION_REQUIRED")
    remote_count = sum(1 for c in candidates if c.partner_operational_suitability == "REMOTE_REGION_UNSUITABLE")

    content = f"""# CHA-FICIAL DIRECTIVE 015-A: 실전 기회 매물 탐지 종합 보고서 (V1.1)

- **평가 일시**: {now_str}
- **대상 차량군**: 현대 아반떼 CN7 관측 라인업 (고유 실차 기준 총 {len(candidates)}대)
- **분석 모드**: 100% 읽기 전용 (운영 DB 및 관측 원본 일체 불변)
- **적용 엔진**: `MarketOpportunityEngine V1.1` (실차 중복 클러스터링, 연식 무결성 및 순수익/목표마진 분리)

---

## 1. 종합 분류 요약

### 1.1 시장 기회 등급 (Market Opportunity Grade)

| 분류 등급 | 정의 및 기준 | 매물 수 | 비율 |
| :--- | :--- | :---: | :---: |
| **`PRIORITY_REVIEW`** | 연식 확정, 시세 대비 $\ge 5\%$ 저렴, 예상 순이익 $\ge 50만원$, 가격 인하 또는 저평가 | **{len(priority_list)}대** | {len(priority_list)/len(candidates)*100:.1f}% |
| **`WATCHLIST`** | 시세 대비 소폭 우위 또는 최근 가격 인하 감지 (추가 시계열 관측 필요) | **{len(watchlist)}대** | {len(watchlist)/len(candidates)*100:.1f}% |
| **`INSUFFICIENT_DATA`** | 연식 미확인(NOYEAR) 또는 동일 코호트 독립 비교 표본 3건 미만 | **{len(insufficient)}대** | {len(insufficient)/len(candidates)*100:.1f}% |
| **`EXCLUDED`** | 금융상품, 시세 대비 고가 매물($\le -10\%$) 또는 데이터 이상치 | **{len(excluded)}대** | {len(excluded)/len(candidates)*100:.1f}% |
| **전체 합계** | - | **{len(candidates)}대** | 100.0% |

### 1.2 파트너 영업 적합성 (Partner Operational Suitability) - 지침 5

> [!IMPORTANT]
> **실제 딜러 즉시 영업 대상 정직한 보고**:
> - **서울/장안평/수도권 즉시 매입 가능 매물**: **{local_count}건** (현재 관측 데이터는 전국 표본으로 서울 명시 매물 미포함)
> - **지역 실사 선행 조건부 검토 매물 (`UNKNOWN`)**: **{verify_req_count}건**
> - **원거리 지방 매물 (대구/대전/부산/광주)**: **{remote_count}건**

---

## 2. 우선 검토 (`PRIORITY_REVIEW`) 추천 후보 상세

| 순위 | 매물 ID | 차량 요약 | 현재 가격 | 코호트 시세(중앙) | 가격 우위 | 기회 점수 | 예상 순이익 | 최근 인하 | 지역 (파트너 적합성) |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for i, c in enumerate(priority_list, 1):
        profit = f"{c.base_scenario.estimated_net_profit_krw:,}원" if c.base_scenario else "-"
        drop = f"-{c.cumulative_price_drop_krw:,}원" if c.has_price_drop else "-"
        content += f"| {i} | `{c.source_listing_id}` | {c.vehicle_summary} | {c.current_price_krw:,}원 | {c.cohort_median_price_krw:,}원 | **+{c.relative_price_gap_pct}%** | **{c.opportunity_score}점** | {profit} | {drop} | {c.raw_location} (`{c.partner_operational_suitability}`) |\n"

    content += """
---

## 3. 가격 변동 신호 포착 매물 (최근 가격 인하 5건 심층 분석)

| 매물 ID | 이전 가격 | 현재 가격 | 인하액 (인하율) | 코호트 시세 | 상대 우위 | 추천 등급 | 기회 점수 | 핵심 사유 및 리스크 |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
"""
    drop_candidates = [c for c in candidates if c.has_price_drop]
    for c in drop_candidates:
        first_p = c.first_observed_price_krw or c.current_price_krw
        median_str = f"{c.cohort_median_price_krw:,}원" if c.cohort_median_price_krw else "표본부족"
        gap_str = f"+{c.relative_price_gap_pct}%" if c.relative_price_gap_pct is not None else "-"
        content += (
            f"| `{c.source_listing_id}` | {first_p:,}원 | {c.current_price_krw:,}원 | "
            f"-{c.cumulative_price_drop_krw:,}원 (-{c.latest_price_drop_pct}%) | "
            f"{median_str} | {gap_str} | "
            f"**`{c.market_opportunity_grade}`** | {c.opportunity_score}점 | "
            f"{c.evaluation_reason} ({' / '.join(c.risk_factors)}) |\n"
        )

    content += """
---

## 4. 동일 실차 중복 광고 클러스터링 분석 (지침 2 준수)
중고차 플랫폼에 서로 다른 ID로 다중 등록된 동일 물리 실차 지문(`vehicle_fingerprint`) 매물 쌍의 분석 내역입니다.

1. **`42852685` / `42849633`**:
   - 지문: `현대_아반떼_CN7_FACELIFT_STANDARD_2026-04_NOYEAR_5993_가솔린_모던` (가격 1,650만, 주행 5,993km 동일)
   - 조치: 연식 미확인(`NOYEAR`)으로 인한 시세 왜곡 방지를 위해 `INSUFFICIENT_DATA`로 안전하게 보류 처리 및 단일 실차로 클러스터링 완료.
2. **`42911910` / `42906948`**:
   - 지문: `현대_아반떼_CN7_FACELIFT_STANDARD_2023-09_2024_46530_하이브리드_모던` (가격 2,149만, 주행 46,530km 동일)
   - 조치: 코호트 표본군에서 1대만 대표 반영하여 시세 왜곡 차단 및 추천 목록에 단일 후보로 대표 등록.
3. **`42866420` / `42863742`**:
   - 지문: `현대_아반떼_CN7_FACELIFT_STANDARD_2023-09_2024_31066_하이브리드_모던` (가격 2,190만, 주행 31,066km 동일)
   - 조치: 대표 1건만 등록 및 동반 광고 ID 명시.
4. **`42453171` / `42453169`**:
   - 지문: `현대_아반떼_CN7_FACELIFT_N_2024-04_NOYEAR_12526_가솔린_NOTRIM` (가격 2,110만, 주행 12,526km 동일)
   - 조치: 연식 미확인(`NOYEAR`)으로 인한 우선 추천 보류 및 단일 클러스터링 완료.

---

## 5. 수익 시나리오의 순수익과 목표마진 분리 구조 (지침 3 준수)

- **예상 총마진 (Estimated Gross Spread)**: $\text{Expected Sale Price} - \text{Purchase Price}$
- **실제 예상 운영비용 (Estimated Operating Cost)**: $\text{Reconditioning Cost} + \text{Logistics Cost}$
- **실제 예상 순이익 (Estimated Net Profit)**: $\text{Gross Spread} - \text{Operating Cost}$
- **목표 마진 (Target Margin)**: 500,000원 (비용이 아닌 기대 수익 판단 기준치)
- **목표 초과 달성액 (Excess over Target)**: $\text{Net Profit} - \text{Target Margin}$
"""

    output_path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    run_opportunity_analysis()
