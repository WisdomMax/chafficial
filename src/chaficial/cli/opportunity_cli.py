"""차피셜 전국 중고차 매물 분석 및 Top 10 기회 매물 자동 선별 CLI."""

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from chaficial.database.base import Base
from chaficial.pipeline.ingest_and_score import OpportunityPipeline


def main():
    parser = argparse.ArgumentParser(
        description="CHA-FICIAL OPPORTUNITY SCORER V0.1: 전국 중고차 매물 분석 및 기회 매물 선별 CLI"
    )
    parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="분석 대상 매물 CSV 파일 경로",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="outputs/top_opportunities.csv",
        help="상위 기회 매물 저장 대상 CSV 경로 (기본값: outputs/top_opportunities.csv)",
    )
    parser.add_argument(
        "--top",
        "-n",
        type=int,
        default=10,
        help="선별할 상위 매물 개수 (기본값: 10)",
    )
    parser.add_argument(
        "--db-url",
        default="sqlite:///data/chaficial_market.db",
        help="SQLite DB URL (기본값: sqlite:///data/chaficial_market.db)",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("🚘 CHA-FICIAL AI : 전국 중고차 매물 기회 평가 엔진 V0.1 (CLI)")
    print("=" * 70)

    # 1. CSV 데이터 로드
    print(f"[*] 1단계: CSV 매물 데이터 로드 중: {args.input}")
    try:
        records = OpportunityPipeline.load_records_from_csv(args.input)
    except (FileNotFoundError, ValueError, KeyError, OSError) as e:
        print(f"[-] CSV 파일 로드 실패: {e}")
        sys.exit(1)
    print(f"[+] 총 {len(records)}건의 매물 레코드를 성공적으로 로드했습니다.")

    # 2. SQLite DB 초기화 및 데이터 적재
    db_path_str = args.db_url.replace("sqlite:///", "")
    if db_path_str and not db_path_str.startswith(":memory:"):
        Path(db_path_str).parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(args.db_url, echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    print(f"[*] 2단계: SQLite 데이터베이스 무결성 적재 및 시계열 스냅샷 생성 중 ({args.db_url})")
    with SessionLocal() as session:
        stats = OpportunityPipeline.ingest_records_to_db(session, records)
        print(f"    - 신규 등록 매물: {stats['new_listings']}건")
        print(f"    - 기존 매물 재확인: {stats['existing_listings']}건")
        print(f"    - 생성된 시계열 스냅샷: {stats['new_snapshots']}건")
        print(f"    - 가격 인하 감지 건수: {stats['price_changed_count']}건")

    # 3. 동일군 벤치마크 및 기회 점수 계산
    print("[*] 3단계: 동일 차종·연식·트림 비교 매물 벤치마크 및 기회 점수(Opportunity Score) 산출...")
    evaluated_results = OpportunityPipeline.evaluate_all(
        records, price_drop_flags=stats.get("price_drop_flags")
    )

    # 4. 상위 Top-N 선별 및 CSV 출력
    print(f"[*] 4단계: 상위 {args.top}대 기회 매물 선별 및 CSV 저장: {args.output}")
    top_items = OpportunityPipeline.export_top_opportunities_to_csv(
        evaluated_results, args.output, top_n=args.top
    )

    # 4-1. DIRECTIVE 008: 세부 중간 계산값 breakdown CSV 및 상세 확인 목록 출력
    breakdown_path = "outputs/directive_008_score_breakdown.csv"
    OpportunityPipeline.export_score_breakdown_csv(evaluated_results, breakdown_path)
    print(f"[+] 점수 산출 상세 중간 계산값 저장 완료: {breakdown_path}")

    manual_review_path = "outputs/directive_008_manual_review_needed.csv"
    review_items = OpportunityPipeline.export_manual_review_candidates_to_csv(evaluated_results, manual_review_path)
    print(f"[+] 상세 확인(검증) 필요 매물 저장 완료: {manual_review_path} (총 {len(review_items)}건)")

    # 하위 호환 007-B 파일도 동시 보존
    OpportunityPipeline.export_score_breakdown_csv(evaluated_results, "outputs/directive_007b_score_breakdown.csv")

    # 5. 콘솔 리포트 요약
    print("\n" + "=" * 70)
    print(f"🏆 CHA-FICIAL AI 선정 상위 {len(top_items)}대 판매 기회 추천 매물 리스트")
    print("=" * 70)

    for idx, item in enumerate(top_items, start=1):
        score_str = f"{item.opportunity_score:.1f}점" if item.opportunity_score is not None else "N/A"
        adv_pct = f"{item.adjusted_advantage_pct:+.1f}%" if item.adjusted_advantage_pct is not None else "N/A"
        fair_val = f"{item.adjusted_fair_value_krw:,}원" if item.adjusted_fair_value_krw else "N/A"
        median_val = f"{item.benchmark_median_price_krw:,}원" if item.benchmark_median_price_krw else "N/A"
        norm_val = f"{item.normalized_baseline_median_krw:,}원" if item.normalized_baseline_median_krw else "N/A"

        print(f"[{idx:02d}위] {item.vehicle_summary}")
        print(f"      • 기회점수: {score_str} | 신뢰도: {item.data_confidence} | 상태: {item.evaluation_status} ({item.estimation_nature})")
        print(f"      • 등록가격: {item.price_krw:,}원 (표본 중앙가: {median_val}, 무사고기준가: {norm_val}, 독립표본 {item.sample_count}대)")
        print(f"      • 상태조정시세: {fair_val} (실질경쟁력: {adv_pct})")
        print(f"      • 출처: [{item.source_platform}] ID: {item.source_listing_id} (유형: {item.data_origin})")
        if item.source_url:
            print(f"      • URL: {item.source_url}")
        print(f"      • 선정근거: {item.selection_reason}")
        print("-" * 70)

    print(f"\n[+] 분석 및 선별이 완료되었습니다. 결과가 '{args.output}'에 저장되었습니다.")


if __name__ == "__main__":
    main()
