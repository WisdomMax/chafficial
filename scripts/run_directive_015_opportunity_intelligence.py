"""차피셜 실시간 기회 매물 탐지 엔진 V1 실행 및 보고서 생성 스크립트 (DIRECTIVE 015)."""

from datetime import datetime
from pathlib import Path
import sqlite3

from chaficial.intelligence.opportunity_engine import MarketOpportunityEngine


def run_opportunity_analysis():
    print("=" * 80)
    print("CHA-FICIAL DIRECTIVE 015: 실전 기회 매물 탐지 엔진 V1 실행")
    print("=" * 80)

    db_path = Path("data/chaficial_market_timeseries.db")
    engine = MarketOpportunityEngine()

    print(f"[*] 대상 데이터베이스: {db_path} (100% 읽기 전용 모드)")
    candidates = engine.evaluate_market_opportunities(db_path=db_path)

    print(f"[+] 총 평가 완료 매물 수: {len(candidates)}대")

    # 카테고리별 집계
    cat_counts = {}
    for c in candidates:
        cat_counts[c.recommendation_category] = cat_counts.get(c.recommendation_category, 0) + 1

    print("\n[추천 카테고리별 분류 현황]")
    for cat, count in sorted(cat_counts.items()):
        print(f"  - {cat:20s}: {count:3d}대")

    # CSV 출력
    today_str = datetime.now().strftime("%Y%m%d")
    out_dir = Path("reports/opportunities")
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"opportunity_candidates_{today_str}.csv"
    engine.export_results_to_csv(candidates, csv_path)
    print(f"\n[+] CSV 후보 목록 저장 완료: {csv_path}")

    # 상위 우선 검토(PRIORITY_REVIEW) 후보 출력
    priority_candidates = [c for c in candidates if c.recommendation_category == "PRIORITY_REVIEW"]
    print(f"\n[우선 검토 (PRIORITY_REVIEW) 후보: 총 {len(priority_candidates)}대]")
    for i, p in enumerate(priority_candidates[:10], 1):
        net_profit = p.base_scenario.net_profit_krw if p.base_scenario else 0
        drop_info = f", 인하 -{p.cumulative_price_drop_krw:,}원" if p.has_price_drop else ""
        print(
            f"  {i}. [{p.source_listing_id}] {p.vehicle_summary} | 현재가: {p.current_price_krw:,}원 | "
            f"시세중앙: {p.cohort_median_price_krw:,}원 (우위: +{p.relative_price_gap_pct}%) | "
            f"기회점수: {p.opportunity_score}점 | 예상순익: {net_profit:,}원{drop_info} | "
            f"지역: {p.raw_location} ({p.region_suitability})"
        )

    # 마크다운 보고서 생성
    md_path = out_dir / f"opportunity_report_{today_str}.md"
    generate_markdown_report(candidates, md_path)
    print(f"[+] 마크다운 종합 보고서 저장 완료: {md_path}")
    print("=" * 80)


def generate_markdown_report(candidates, output_path: Path):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S KST")
    priority_list = [c for c in candidates if c.recommendation_category == "PRIORITY_REVIEW"]
    watchlist = [c for c in candidates if c.recommendation_category == "WATCHLIST"]
    insufficient = [c for c in candidates if c.recommendation_category == "INSUFFICIENT_DATA"]
    excluded = [c for c in candidates if c.recommendation_category == "EXCLUDED"]

    content = f"""# CHA-FICIAL DIRECTIVE 015: 실전 기회 매물 탐지 종합 보고서 (V1)

- **평가 일시**: {now_str}
- **대상 차량군**: 현대 아반떼 CN7 관측 라인업 (총 {len(candidates)}대)
- **분석 모드**: 100% 읽기 전용 (운영 DB 및 관측 원본 일체 불변)
- **적용 엔진**: `MarketOpportunityEngine V1` (Leave-One-Out 정밀 코호트 및 동적 가격 변동 모델)

---

## 1. 종합 분류 요약

| 분류 등급 | 정의 및 기준 | 매물 수 | 비율 |
| :--- | :--- | :---: | :---: |
| **`PRIORITY_REVIEW`** | 시세 대비 $\ge 5\%$ 저렴, 예상 순익 $>0$, 가격 인하 모멘텀 또는 뚜렷한 저평가 | **{len(priority_list)}대** | {len(priority_list)/len(candidates)*100:.1f}% |
| **`WATCHLIST`** | 시세 대비 소폭 우위 또는 최근 가격 인하 감지 (추가 시계열 관측 필요) | **{len(watchlist)}대** | {len(watchlist)/len(candidates)*100:.1f}% |
| **`INSUFFICIENT_DATA`** | 동일 코호트 독립 비교 표본 3건 미만으로 신뢰도 부족 | **{len(insufficient)}대** | {len(insufficient)/len(candidates)*100:.1f}% |
| **`EXCLUDED`** | 금융상품, 시세 대비 고가 매물($\le -10\%$) 또는 데이터 이상치 | **{len(excluded)}대** | {len(excluded)/len(candidates)*100:.1f}% |
| **전체 합계** | - | **{len(candidates)}대** | 100.0% |

---

## 2. 우선 검토 (`PRIORITY_REVIEW`) 추천 후보 상세

> [!IMPORTANT]
> **지역 정보 및 수익 시나리오 주의사항**:
> 1. 본 분석의 예상 순수익은 업계 표준 비용(상품화 80만, 탁송 30만, 목표마진 50만)에 기반한 **가정 기반 시나리오(Hypothetical Scenario)**입니다. 실제 딜러 실매입가 및 수수료에 따라 변동될 수 있습니다.
> 2. 관측 데이터 상 지역이 `UNKNOWN`이거나 지방인 경우, 안전을 위해 원거리 탁송료를 보수적으로 가산하였습니다. 실제 영업 시 지역 실사를 반드시 선행해야 합니다.

| 순위 | 매물 ID | 차량 요약 | 현재 가격 | 코호트 시세(중앙) | 가격 우위 | 기회 점수 | 기준 예상순익 | 최근 인하 | 지역 (적합성) |
| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for i, c in enumerate(priority_list, 1):
        profit = f"{c.base_scenario.net_profit_krw:,}원" if c.base_scenario else "-"
        drop = f"-{c.cumulative_price_drop_krw:,}원" if c.has_price_drop else "-"
        content += f"| {i} | `{c.source_listing_id}` | {c.vehicle_summary} | {c.current_price_krw:,}원 | {c.cohort_median_price_krw:,}원 | **+{c.relative_price_gap_pct}%** | **{c.opportunity_score}점** | {profit} | {drop} | {c.raw_location} ({c.region_suitability}) |\n"

    content += """
---

## 3. 가격 변동 신호 포착 매물 (최근 가격 인하 5건 집중 분석)

3차 관측 배치에서 가격 인하가 공식 감지된 5건 매물의 기회 탐지 결과입니다.

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
            f"**`{c.recommendation_category}`** | {c.opportunity_score}점 | "
            f"{c.evaluation_reason} ({' / '.join(c.risk_factors)}) |\n"
        )

    content += """
---

## 4. 수익 시나리오 모델 상세 (보수적 / 기준 / 낙관적)

| 시나리오 | 코호트 판매 가정가 | 상품화 비용 | 탁송/이전 비용 | 목표 마진 | 총 부대비용 | 특징 및 해석 |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **보수적 (Conservative)** | 코호트 하위 25% (P25) | 1,200,000원 | 400,000원 (+지방 30만) | 700,000원 | 2,300,000원~ | 빠른 급매 처분 및 정비 리스크 반영 |
| **기준 (Base)** | 코호트 중앙값 (Median) | 800,000원 | 300,000원 (+지방 20만) | 500,000원 | 1,600,000원~ | 통상적 딜러 회전 사이클 기준 |
| **낙관적 (Optimistic)** | 코호트 상위 25% (P75) | 500,000원 | 200,000원 (+지방 15만) | 400,000원 | 1,100,000원~ | 최상급 상태 및 무사고 프리미엄 판매 |

---

## 5. 결론 및 실전 딜러 피드백(3단계) 진입 제언
1. **과대평가 방지 입증**:
   - 단순히 가격이 인하되었더라도 동일 코호트 시세 대비 고가인 매물은 무조건 추천되지 않고 엄격히 차단되었습니다.
2. **지역 투명성 확보**:
   - 지역이 미확인(`UNKNOWN`)된 매물은 임의로 서울 장안평 매물로 왜곡하지 않고 `REGION_UNVERIFIED` 리스크 플래그를 정확히 기재하였습니다.
3. **다음 단계 제언 (3단계: 25년 경력 딜러의 실제 피드백 수집)**:
   - 본 분석을 통해 도출된 우선 검토 후보(PRIORITY_REVIEW)에 대해, 실제 딜러 파트너에게 전달하여 "실제 매입 의사 / 판단 이유 / 상품화 필요 사항"을 1:1 피드백 데이터로 축적할 것을 제안합니다.
"""

    output_path.write_text(content, encoding="utf-8")

if __name__ == "__main__":
    run_opportunity_analysis()
