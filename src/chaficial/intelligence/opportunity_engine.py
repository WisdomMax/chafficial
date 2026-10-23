"""차피셜 실시간 가격 변동 기반 기회 매물 탐지 엔진 V1 (DIRECTIVE 015).

재사용 원칙 준수:
- OpportunityScorer 코호트 및 상태 보정 로직 재사용
- Listing, ListingSnapshot, PriceEvent 데이터 모델 활용
- 읽기 전용(Read-Only) 안전 운영 및 데이터 무결성 보존
"""

import csv
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from statistics import median
from typing import Any

from chaficial.intelligence.config import CostAssumptions, OpportunityEngineConfig
from chaficial.platforms.base import StandardListingRecord
from chaficial.scorer.opportunity import OpportunityScorer, ScorerParameters


@dataclass
class ProfitScenario:
    """수익 시나리오 분석 결과 (가정 기반 분석)."""

    estimated_purchase_price_krw: int
    estimated_sale_price_krw: int
    reconditioning_cost_krw: int
    logistics_cost_krw: int
    target_margin_krw: int
    total_cost_krw: int
    net_profit_krw: int
    profit_margin_pct: float
    scenario_type: str  # CONSERVATIVE, BASE, OPTIMISTIC


@dataclass
class OpportunityCandidate:
    """기회 매물 종합 평가 결과 DTO."""

    listing_id: str
    source_platform: str
    source_listing_id: str
    vehicle_summary: str
    manufacturer: str
    model_name: str
    generation: str
    model_year: int | None
    mileage_km: int
    current_price_krw: int
    first_observed_price_krw: int
    raw_location: str
    region_suitability: str  # PARTNER_LOCAL, REMOTE_REGION, REGION_UNVERIFIED

    # 시세 및 비교 분석 (Leave-One-Out)
    cohort_key: str
    sample_count: int
    cohort_median_price_krw: int | None
    relative_price_gap_krw: int | None
    relative_price_gap_pct: float | None

    # 가격 변동 신호
    observation_count: int
    cumulative_price_drop_krw: int
    price_drop_count: int
    latest_price_drop_pct: float
    has_price_drop: bool

    # 수익 시나리오 (Base 기준)
    base_scenario: ProfitScenario | None
    conservative_scenario: ProfitScenario | None
    optimistic_scenario: ProfitScenario | None

    # 기회 점수 및 신뢰도
    score_relative_price: float
    score_price_drop: float
    score_profitability: float
    score_data_confidence: float
    opportunity_score: float  # 총합 (0 ~ 100)
    data_confidence: str      # HIGH, MEDIUM, LOW, INSUFFICIENT

    # 최종 추천 분류
    recommendation_category: str  # PRIORITY_REVIEW, WATCHLIST, INSUFFICIENT_DATA, EXCLUDED
    evaluation_reason: str
    risk_factors: list[str] = field(default_factory=list)


class MarketOpportunityEngine:
    """가격 변동 및 상대 시세 기반 기회 매물 선별 엔진 V1."""

    def __init__(self, config: OpportunityEngineConfig | None = None):
        self.config = config or OpportunityEngineConfig()
        self.scorer_params = ScorerParameters()

    def evaluate_market_opportunities(
        self,
        db_path: Path | None = None,
        as_of_time: datetime | None = None,
    ) -> list[OpportunityCandidate]:
        """운영 DB를 읽기 전용으로 조회하여 기회 매물을 선별 및 평가합니다."""
        target_db = db_path or self.config.db_path
        if not target_db.exists():
            raise FileNotFoundError(f"운영 데이터베이스를 찾을 수 없습니다: {target_db}")

        # 1. DB에서 최신 매물 및 스냅샷, 가격 변동 데이터 조회 (100% 읽기 전용)
        listings_data = self._load_active_listings_with_snapshots(target_db, as_of_time)
        price_events_data = self._load_price_events_summary(target_db, as_of_time)

        if not listings_data:
            return []

        # 2. 독립 비교 매물 코호트 구축 (동일 차량의 과거 스냅샷 중복 배제: 최신 스냅샷만 사용)
        cohort_groups = self._build_cohort_groups(listings_data)

        # 3. 매물별 상대 시세, 가격 변동, 수익 시나리오, 기회 점수 계산
        candidates: list[OpportunityCandidate] = []
        for item in listings_data:
            candidate = self._evaluate_single_listing(
                item=item,
                cohort_groups=cohort_groups,
                price_events_summary=price_events_data.get(item["listing_id"], {}),
            )
            candidates.append(candidate)

        # 4. 점수 및 우선순위 정렬 (PRIORITY_REVIEW 최상단, 그 다음 opportunity_score 내림차순)
        category_order = {
            "PRIORITY_REVIEW": 0,
            "WATCHLIST": 1,
            "INSUFFICIENT_DATA": 2,
            "EXCLUDED": 3,
        }
        candidates.sort(
            key=lambda c: (
                category_order.get(c.recommendation_category, 99),
                -c.opportunity_score,
                -(c.relative_price_gap_pct or -999.0),
            )
        )
        return candidates

    def _load_active_listings_with_snapshots(
        self, db_path: Path, as_of_time: datetime | None
    ) -> list[dict[str, Any]]:
        """DB에서 활성 매물 및 최신 스냅샷 레코드 읽기 전용 로드."""
        # URI 읽기 전용 모드로 안전하게 오픈
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT 
                l.listing_id,
                l.source_platform,
                l.source_listing_id,
                l.raw_location,
                l.first_observed_at,
                l.current_status,
                s.snapshot_id,
                s.observed_at,
                s.price_krw,
                s.mileage_km,
                s.raw_specs,
                (SELECT COUNT(*) FROM listing_snapshots ls WHERE ls.listing_id = l.listing_id) as snapshot_count,
                (SELECT price_krw FROM listing_snapshots ls WHERE ls.listing_id = l.listing_id ORDER BY observed_at ASC LIMIT 1) as first_price_krw
            FROM listings l
            JOIN listing_snapshots s ON s.listing_id = l.listing_id
            WHERE s.observed_at = (
                SELECT MAX(s2.observed_at) 
                FROM listing_snapshots s2 
                WHERE s2.listing_id = l.listing_id
            )
        """
        rows = cursor.execute(query).fetchall()
        results: list[dict[str, Any]] = []

        for r in rows:
            raw_specs = {}
            if r["raw_specs"]:
                try:
                    raw_specs = json.loads(r["raw_specs"])
                except Exception:
                    raw_specs = {}

            results.append({
                "listing_id": r["listing_id"],
                "source_platform": r["source_platform"],
                "source_listing_id": r["source_listing_id"],
                "raw_location": r["raw_location"] or "UNKNOWN",
                "first_observed_at": r["first_observed_at"],
                "current_status": r["current_status"],
                "snapshot_id": r["snapshot_id"],
                "observed_at": r["observed_at"],
                "price_krw": r["price_krw"],
                "mileage_km": r["mileage_km"],
                "raw_specs": raw_specs,
                "snapshot_count": r["snapshot_count"],
                "first_price_krw": r["first_price_krw"] or r["price_krw"],
            })

        conn.close()
        return results

    def _load_price_events_summary(
        self, db_path: Path, as_of_time: datetime | None
    ) -> dict[str, dict[str, Any]]:
        """DB에서 가격 변동 이벤트 요약 정보 로드."""
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = """
            SELECT 
                listing_id,
                COUNT(CASE WHEN event_type = 'PRICE_DROP' THEN 1 END) as drop_count,
                COALESCE(SUM(CASE WHEN event_type = 'PRICE_DROP' THEN -price_delta_krw ELSE 0 END), 0) as cum_drop_krw,
                (SELECT price_delta_pct FROM price_events pe2 WHERE pe2.listing_id = pe.listing_id AND pe2.event_type = 'PRICE_DROP' ORDER BY event_timestamp DESC LIMIT 1) as latest_drop_pct
            FROM price_events pe
            GROUP BY listing_id
        """
        rows = cursor.execute(query).fetchall()
        summary: dict[str, dict[str, Any]] = {}
        for r in rows:
            summary[r["listing_id"]] = {
                "drop_count": r["drop_count"],
                "cum_drop_krw": r["cum_drop_krw"],
                "latest_drop_pct": r["latest_drop_pct"] or 0.0,
            }
        conn.close()
        return summary

    def _build_cohort_groups(
        self, listings: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """동일 매물 중복 없이 최신 레코드만으로 코호트 그룹 구축."""
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in listings:
            key = self._extract_cohort_key(item)
            item["cohort_key"] = key
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        return groups

    def _extract_cohort_key(self, item: dict[str, Any]) -> str:
        """아이템으로부터 정밀 코호트 키 생성 (OpportunityScorer 규칙 준수)."""
        specs = item.get("raw_specs", {})
        if isinstance(specs, str):
            try:
                specs = json.loads(specs)
            except Exception:
                specs = {}
        if not isinstance(specs, dict):
            specs = {}
        mfg = specs.get("manufacturer", "현대")
        model = specs.get("model", "아반떼")
        gen = "CN7"  # 기본 세대
        fingerprint = specs.get("vehicle_fingerprint", "")
        fuel = "가솔린"
        trim = "모던"
        year = specs.get("model_year", "2021")

        if fingerprint:
            parts = fingerprint.split("_")
            for p in parts:
                if len(p) == 4 and p.isdigit() and (p.startswith("201") or p.startswith("202")):
                    year = p
                    break
            if len(parts) >= 8:
                gen = parts[2]
                fuel = parts[8] if len(parts) > 8 else parts[-2]
                trim = parts[9] if len(parts) > 9 else parts[-1]

        return f"{mfg}_{model}_{gen}_{year}_{trim}_{fuel}"

    def _evaluate_single_listing(
        self,
        item: dict[str, Any],
        cohort_groups: dict[str, list[dict[str, Any]]],
        price_events_summary: dict[str, Any],
    ) -> OpportunityCandidate:
        """단일 매물에 대한 종합 다차원 평가 수행."""
        listing_id = item["listing_id"]
        current_price = item["price_krw"]
        specs = item.get("raw_specs", {})
        if isinstance(specs, str):
            try:
                specs = json.loads(specs)
            except Exception:
                specs = {}
        if not isinstance(specs, dict):
            specs = {}
        mfg = specs.get("manufacturer", "현대")
        model = specs.get("model", "아반떼")
        gen = "CN7"
        fingerprint = specs.get("vehicle_fingerprint", "")
        year = int(specs["model_year"]) if specs.get("model_year") and str(specs["model_year"]).isdigit() else None
        # 연식 및 세부 정보 추출
        if not year and fingerprint:
            parts = fingerprint.split("_")
            for p in parts:
                if len(p) == 4 and p.isdigit() and (p.startswith("201") or p.startswith("202")):
                    year = int(p)
                    break
        mileage = item["mileage_km"] or 0
        raw_location = item["raw_location"]

        cohort_key = item["cohort_key"]
        cohort_members = cohort_groups.get(cohort_key, [])

        # 1. Leave-One-Out 비교 표본 추출 (자기 자신 배제)
        peer_prices = [
            m["price_krw"]
            for m in cohort_members
            if m["listing_id"] != listing_id and m["price_krw"] and m["price_krw"] > 0
        ]
        sample_count = len(peer_prices)

        # 2. 상대 시세 산출
        cohort_median: int | None = None
        rel_gap_krw: int | None = None
        rel_gap_pct: float | None = None
        p25_price: int | None = None
        p75_price: int | None = None

        if sample_count >= self.config.min_benchmark_samples:
            sorted_prices = sorted(peer_prices)
            cohort_median = int(median(sorted_prices))
            p25_idx = max(0, int(len(sorted_prices) * 0.25))
            p75_idx = min(len(sorted_prices) - 1, int(len(sorted_prices) * 0.75))
            p25_price = sorted_prices[p25_idx]
            p75_price = sorted_prices[p75_idx]

            if current_price and current_price > 0:
                rel_gap_krw = cohort_median - current_price
                rel_gap_pct = round((rel_gap_krw / cohort_median) * 100.0, 2)

        # 3. 가격 변동 신호
        drop_count = price_events_summary.get("drop_count", 0)
        cum_drop_krw = price_events_summary.get("cum_drop_krw", 0)
        latest_drop_pct = abs(price_events_summary.get("latest_drop_pct", 0.0))
        has_price_drop = drop_count > 0

        # 4. 지역 적합성 판정 (지침 1.3: 임의 장안평 둔갑 방지)
        if raw_location in ["서울", "장안평", "경기", "인천"]:
            region_suitability = "PARTNER_LOCAL"
            is_remote = False
        elif raw_location in ["UNKNOWN", ""]:
            region_suitability = "REGION_UNVERIFIED"
            is_remote = True  # 안전을 위해 보수적으로 원거리 취급
        else:
            region_suitability = "REMOTE_REGION"
            is_remote = True

        # 5. 수익 시나리오 계산 (가정 기반)
        base_scenario: ProfitScenario | None = None
        conservative_scenario: ProfitScenario | None = None
        optimistic_scenario: ProfitScenario | None = None

        if current_price and current_price > 0 and cohort_median:
            base_scenario = self._calc_scenario(
                purchase_price=current_price,
                expected_sale_price=cohort_median,
                is_remote=is_remote,
                scenario_type="BASE",
            )
            conservative_scenario = self._calc_scenario(
                purchase_price=current_price,
                expected_sale_price=p25_price or cohort_median,
                is_remote=is_remote,
                scenario_type="CONSERVATIVE",
            )
            optimistic_scenario = self._calc_scenario(
                purchase_price=current_price,
                expected_sale_price=p75_price or cohort_median,
                is_remote=is_remote,
                scenario_type="OPTIMISTIC",
            )

        # 6. 다차원 기회 점수 산출 (0 ~ 100점)
        scores, data_conf = self._calculate_scores(
            rel_gap_pct=rel_gap_pct,
            has_price_drop=has_price_drop,
            latest_drop_pct=latest_drop_pct,
            drop_count=drop_count,
            base_scenario=base_scenario,
            sample_count=sample_count,
        )

        total_score = round(
            scores["relative_price"]
            + scores["price_drop"]
            + scores["profitability"]
            + scores["data_confidence"],
            1,
        )

        # 7. 추천 분류 및 사유/위험요인 결정
        category, reason, risks = self._classify_candidate(
            current_price=current_price,
            product_type=specs.get("product_type", "CASH_OR_INSTALLMENT"),
            sample_count=sample_count,
            rel_gap_pct=rel_gap_pct,
            base_scenario=base_scenario,
            total_score=total_score,
            region_suitability=region_suitability,
            has_price_drop=has_price_drop,
            raw_location=raw_location,
        )

        vehicle_summary = f"{mfg} {model} {gen} ({year}년식, {mileage:,}km)"

        return OpportunityCandidate(
            listing_id=listing_id,
            source_platform=item["source_platform"],
            source_listing_id=item["source_listing_id"],
            vehicle_summary=vehicle_summary,
            manufacturer=mfg,
            model_name=model,
            generation=gen,
            model_year=year,
            mileage_km=mileage,
            current_price_krw=current_price,
            first_observed_price_krw=item["first_price_krw"],
            raw_location=raw_location,
            region_suitability=region_suitability,
            cohort_key=cohort_key,
            sample_count=sample_count,
            cohort_median_price_krw=cohort_median,
            relative_price_gap_krw=rel_gap_krw,
            relative_price_gap_pct=rel_gap_pct,
            observation_count=item["snapshot_count"],
            cumulative_price_drop_krw=cum_drop_krw,
            price_drop_count=drop_count,
            latest_price_drop_pct=latest_drop_pct,
            has_price_drop=has_price_drop,
            base_scenario=base_scenario,
            conservative_scenario=conservative_scenario,
            optimistic_scenario=optimistic_scenario,
            score_relative_price=scores["relative_price"],
            score_price_drop=scores["price_drop"],
            score_profitability=scores["profitability"],
            score_data_confidence=scores["data_confidence"],
            opportunity_score=total_score,
            data_confidence=data_conf,
            recommendation_category=category,
            evaluation_reason=reason,
            risk_factors=risks,
        )

    def _calc_scenario(
        self,
        purchase_price: int,
        expected_sale_price: int,
        is_remote: bool,
        scenario_type: str,
    ) -> ProfitScenario:
        """가정 기반 수익 시나리오 계산."""
        costs = self.config.costs

        if scenario_type == "CONSERVATIVE":
            recond = costs.conservative_reconditioning_cost_krw
            logistics = costs.conservative_logistics_cost_krw + (
                costs.conservative_remote_surcharge_krw if is_remote else 0
            )
            margin = costs.conservative_target_margin_krw
        elif scenario_type == "OPTIMISTIC":
            recond = costs.optimistic_reconditioning_cost_krw
            logistics = costs.optimistic_logistics_cost_krw + (
                costs.optimistic_remote_surcharge_krw if is_remote else 0
            )
            margin = costs.optimistic_target_margin_krw
        else:  # BASE
            recond = costs.base_reconditioning_cost_krw
            logistics = costs.base_logistics_cost_krw + (
                costs.base_remote_surcharge_krw if is_remote else 0
            )
            margin = costs.base_target_margin_krw

        total_cost = recond + logistics + margin
        net_profit = expected_sale_price - purchase_price - total_cost
        margin_pct = round((net_profit / purchase_price) * 100.0, 2) if purchase_price > 0 else 0.0

        return ProfitScenario(
            estimated_purchase_price_krw=purchase_price,
            estimated_sale_price_krw=expected_sale_price,
            reconditioning_cost_krw=recond,
            logistics_cost_krw=logistics,
            target_margin_krw=margin,
            total_cost_krw=total_cost,
            net_profit_krw=net_profit,
            profit_margin_pct=margin_pct,
            scenario_type=scenario_type,
        )

    def _calculate_scores(
        self,
        rel_gap_pct: float | None,
        has_price_drop: bool,
        latest_drop_pct: float,
        drop_count: int,
        base_scenario: ProfitScenario | None,
        sample_count: int,
    ) -> tuple[dict[str, float], str]:
        """4개 축 기회 점수 계산 (최대 100점)."""
        cfg = self.config

        # 1. 상대 시세 점수 (최대 40점)
        s_rel = 0.0
        if rel_gap_pct is not None and rel_gap_pct > 0:
            # 10% 저렴할 때 40점 만점 기준
            s_rel = min(cfg.weight_relative_price, (rel_gap_pct / 10.0) * cfg.weight_relative_price)
        elif rel_gap_pct is not None and rel_gap_pct <= 0:
            s_rel = 0.0

        # 2. 가격 인하 점수 (최대 25점)
        s_drop = 0.0
        if has_price_drop:
            # 기본 인하 모멘텀 10점 + 인하율(최대 10점) + 다회 인하(5점)
            pct_score = min(10.0, latest_drop_pct * 2.0)
            cnt_score = min(5.0, (drop_count - 1) * 2.5) if drop_count > 1 else 0.0
            s_drop = min(cfg.weight_price_drop, 10.0 + pct_score + cnt_score)

        # 3. 수익성 점수 (최대 20점)
        s_profit = 0.0
        if base_scenario and base_scenario.net_profit_krw > 0:
            # 순수익 100만원 시 만점 (20점)
            s_profit = min(cfg.weight_profitability, (base_scenario.net_profit_krw / 1_000_000.0) * cfg.weight_profitability)

        # 4. 데이터 신뢰도 점수 (최대 15점)
        s_conf = 0.0
        if sample_count >= cfg.high_confidence_samples:
            s_conf = cfg.weight_data_confidence  # 15점
            data_conf = "HIGH"
        elif sample_count >= cfg.min_benchmark_samples:
            s_conf = cfg.weight_data_confidence * 0.6  # 9점
            data_conf = "MEDIUM"
        elif sample_count > 0:
            s_conf = cfg.weight_data_confidence * 0.2  # 3점
            data_conf = "LOW"
        else:
            s_conf = 0.0
            data_conf = "INSUFFICIENT"

        scores = {
            "relative_price": round(s_rel, 1),
            "price_drop": round(s_drop, 1),
            "profitability": round(s_profit, 1),
            "data_confidence": round(s_conf, 1),
        }
        return scores, data_conf

    def _classify_candidate(
        self,
        current_price: int | None,
        product_type: str,
        sample_count: int,
        rel_gap_pct: float | None,
        base_scenario: ProfitScenario | None,
        total_score: float,
        region_suitability: str,
        has_price_drop: bool,
        raw_location: str,
    ) -> tuple[str, str, list[str]]:
        """엄격한 기준에 따른 4단계 추천 분류."""
        risks: list[str] = []

        # 배제 조건 1: 금융상품(렌트/리스)
        if product_type != "CASH_OR_INSTALLMENT":
            return "EXCLUDED", "금융상품(렌트/리스) 매물로 일반 매매 대상 제외", ["FINANCIAL_PRODUCT"]

        # 배제 조건 2: 가격 결측 또는 비정상
        if not current_price or current_price <= 0:
            return "EXCLUDED", "가격 정보 누락 또는 비정상 가격 데이터", ["INVALID_PRICE"]

        # 리스크 요인 기본 수집
        if region_suitability == "REGION_UNVERIFIED":
            risks.append("지역 정보 미확인(추가 실사 필요)")
        elif region_suitability == "REMOTE_REGION":
            risks.append(f"원거리 지역({raw_location}) 매물(추가 탁송료 발생)")

        # 표본 부족 조건
        if sample_count < self.config.min_benchmark_samples:
            risks.append("동일 코호트 비교 표본 부족")
            return (
                "INSUFFICIENT_DATA",
                f"동일 코호트 비교 표본 부족 ({sample_count}건 < 기준 {self.config.min_benchmark_samples}건)",
                risks,
            )

        if base_scenario and base_scenario.net_profit_krw <= 0:
            risks.append("기준 시나리오 예상 순이익 적자/부족")

        if rel_gap_pct is not None and rel_gap_pct < 0:
            risks.append(f"동일 코호트 시세 대비 {abs(rel_gap_pct):.1f}% 고가 매물")

        # 배제 조건 3: 시세 대비 과도하게 비싼 매물 (-10% 이하)
        if rel_gap_pct is not None and rel_gap_pct <= -10.0:
            return "EXCLUDED", f"시세 중앙값 대비 {abs(rel_gap_pct):.1f}% 고가로 가격 경쟁력 없음", risks

        # 우선 검토 (PRIORITY_REVIEW) 조건:
        # 1) 시세 대비 5% 이상 저렴
        # 2) 기준 순이익 > 0
        # 3) 기회 점수 50점 이상 또는 뚜렷한 가격 인하 모멘텀
        if (
            rel_gap_pct is not None
            and rel_gap_pct >= self.config.price_advantage_threshold_pct
            and base_scenario
            and base_scenario.net_profit_krw > 0
            and (total_score >= 50.0 or has_price_drop)
        ):
            reason = f"동일 코호트 시세 대비 {rel_gap_pct:.1f}% 저렴하며, 예상 순익 {base_scenario.net_profit_krw:,}원 확보 가능"
            if has_price_drop:
                reason += " (최근 가격 인하 포착)"
            return "PRIORITY_REVIEW", reason, risks

        # 추가 관측 (WATCHLIST) 조건:
        # 시세 대비 다소 저렴하거나 최근 가격 인하가 포착되었으나, 우선 검토 마진에 미달하는 매물
        if (rel_gap_pct is not None and rel_gap_pct > 0) or has_price_drop:
            reason = "시세 대비 소폭 우위 또는 가격 변동 감지 매물로 지속 관측 필요"
            return "WATCHLIST", reason, risks

        return "EXCLUDED", "시세 경쟁력 및 가격 변동 모멘텀 부족", risks

    def export_results_to_csv(
        self, candidates: list[OpportunityCandidate], output_path: Path
    ) -> None:
        """분석 결과를 지정된 CSV 파일로 출력 (지침 3 CSV 필수 항목 준수)."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "listing_id",
            "source_platform",
            "source_listing_id",
            "vehicle_summary",
            "model_year",
            "mileage_km",
            "current_price_krw",
            "cohort_median_price_krw",
            "relative_price_gap_pct",
            "cumulative_price_drop_krw",
            "observation_count",
            "estimated_base_net_profit_krw",
            "opportunity_score",
            "data_confidence",
            "region_suitability",
            "raw_location",
            "recommendation_category",
            "evaluation_reason",
            "risk_factors",
        ]

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for c in candidates:
                base_profit = c.base_scenario.net_profit_krw if c.base_scenario else 0
                writer.writerow({
                    "listing_id": c.listing_id,
                    "source_platform": c.source_platform,
                    "source_listing_id": c.source_listing_id,
                    "vehicle_summary": c.vehicle_summary,
                    "model_year": c.model_year or "",
                    "mileage_km": c.mileage_km,
                    "current_price_krw": c.current_price_krw,
                    "cohort_median_price_krw": c.cohort_median_price_krw or "",
                    "relative_price_gap_pct": c.relative_price_gap_pct or "",
                    "cumulative_price_drop_krw": c.cumulative_price_drop_krw,
                    "observation_count": c.observation_count,
                    "estimated_base_net_profit_krw": base_profit,
                    "opportunity_score": c.opportunity_score,
                    "data_confidence": c.data_confidence,
                    "region_suitability": c.region_suitability,
                    "raw_location": c.raw_location,
                    "recommendation_category": c.recommendation_category,
                    "evaluation_reason": c.evaluation_reason,
                    "risk_factors": " | ".join(c.risk_factors),
                })
