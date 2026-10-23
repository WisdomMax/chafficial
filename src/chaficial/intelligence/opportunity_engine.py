"""차피셜 실시간 가격 변동 기반 기회 매물 탐지 엔진 V1.2 (DIRECTIVE 015-B).

개선 사항 (DIRECTIVE 015-B):
1. [결정적 단일 행 선택] CTE ROW_NUMBER() OVER (PARTITION BY listing_id ORDER BY observed_at DESC, snapshot_id DESC) 적용으로 동일 시각 스냅샷 중복 조회 원천 차단
2. [중복 신뢰 수준 분리] POSSIBLE_DUPLICATE(지문 기반 추정), CONFIRMED_DUPLICATE(독립 식별자 확인), NO_DUPLICATE_DETECTED 분리
3. [수익 추정 표현 정정] hypothetical_net_profit 명시 및 미반영 비용(세금, 상사수수료, 금융비용 등) 주의사항 명기
4. [딜러 파일럿 준비] 딜러 실전 검토표 및 피드백 입력 필드(dealer_review_verdict 등) 완비
"""

import csv
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from statistics import median
from typing import Any

from chaficial.intelligence.config import CostAssumptions, OpportunityEngineConfig
from chaficial.scorer.opportunity import ScorerParameters


@dataclass
class ProfitScenario:
    """가정 기반 수익 시나리오 분석 결과 (DIRECTIVE 015-B)."""

    hypothetical_purchase_price_krw: int
    hypothetical_sale_price_krw: int
    hypothetical_gross_spread_krw: int       # 가정 총마진 (판매가 - 매입가)
    hypothetical_operating_cost_krw: int     # 가정 운영비용 (상품화비 + 탁송/이전비)
    hypothetical_net_profit_krw: int         # 가정 순이익 (총마진 - 실제 운영비용)
    target_margin_krw: int                   # 딜러 목표 마진 기준 (판단 기준치)
    excess_over_target_krw: int              # 목표 마진 초과 달성분 (순이익 - 목표마진)
    hypothetical_margin_pct: float           # 가정 순이익률 (순이익 / 매입가 * 100)
    scenario_type: str                       # CONSERVATIVE, BASE, OPTIMISTIC
    unreflected_costs_note: str = "취득세, 매매수수료, 금융비용, 재고보유비용 미반영 가정치"


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

    # 분리된 평가 지표 (지침 5)
    market_opportunity_grade: str        # PRIORITY_REVIEW, WATCHLIST, INSUFFICIENT_DATA, EXCLUDED
    partner_operational_suitability: str  # LOCAL_OPERATIONAL, LOCATION_VERIFICATION_REQUIRED, REMOTE_REGION_UNSUITABLE

    # 실차 지문 및 중복 신뢰 수준 (지침 2)
    vehicle_fingerprint: str
    duplicate_status: str                # NO_DUPLICATE_DETECTED, POSSIBLE_DUPLICATE, CONFIRMED_DUPLICATE
    duplicate_listing_ids: list[str]

    # 시세 및 비교 분석 (Leave-One-Out 및 실차 단위 표본 정제)
    cohort_key: str
    sample_count: int                    # 독립 비교 표본 수 (동일 실차 지문 배제)
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
    opportunity_score: float             # 총합 (0 ~ 100)
    data_confidence: str                 # HIGH, MEDIUM, LOW, INSUFFICIENT

    # 최종 추천 분류
    recommendation_category: str         # 이전 호환성 필드 (= market_opportunity_grade)
    evaluation_reason: str
    risk_factors: list[str] = field(default_factory=list)


class MarketOpportunityEngine:
    """가격 변동 및 상대 시세 기반 기회 매물 선별 엔진 V1.2."""

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

        # 1. DB에서 활성 매물, 최신 스냅샷 조회 (CTE ROW_NUMBER() 적용으로 단 1행만 결정적 로드)
        listings_data = self._load_active_listings_with_snapshots(target_db, as_of_time)
        price_events_data = self._load_price_events_summary(target_db, as_of_time)

        if not listings_data:
            return []

        # 2. 동일 실차 지문(vehicle_fingerprint) 중복 매물 클러스터링
        fingerprint_map, duplicate_clusters = self._cluster_duplicate_fingerprints(listings_data)

        # 3. 독립 비교 매물 코호트 구축 (동일 실차 지문은 1건의 대표 가격만 반영하여 시세 왜곡 차단)
        cohort_groups = self._build_cohort_groups(listings_data)

        # 4. 매물별 상대 시세, 가격 변동, 수익 시나리오, 기회 점수 계산
        candidates: list[OpportunityCandidate] = []
        seen_fingerprints: set[str] = set()

        for item in listings_data:
            fp = item["vehicle_fingerprint"]
            is_dup = len(fingerprint_map.get(fp, [])) > 1
            other_ids = [m["source_listing_id"] for m in fingerprint_map.get(fp, []) if m["listing_id"] != item["listing_id"]]

            candidate = self._evaluate_single_listing(
                item=item,
                cohort_groups=cohort_groups,
                price_events_summary=price_events_data.get(item["listing_id"], {}),
                is_duplicate=is_dup,
                duplicate_ids=other_ids,
            )

            # 추천 목록 중복 방지: 동일 실차 지문이 복수일 경우 1건만 대표로 추천 등록
            if fp and fp in seen_fingerprints and is_dup:
                continue
            if fp:
                seen_fingerprints.add(fp)

            candidates.append(candidate)

        # 5. 점수 및 우선순위 정렬 (PRIORITY_REVIEW 최상단, 그 다음 opportunity_score 내림차순)
        category_order = {
            "PRIORITY_REVIEW": 0,
            "WATCHLIST": 1,
            "INSUFFICIENT_DATA": 2,
            "EXCLUDED": 3,
        }
        candidates.sort(
            key=lambda c: (
                category_order.get(c.market_opportunity_grade, 99),
                -c.opportunity_score,
                -(c.relative_price_gap_pct or -999.0),
            )
        )
        return candidates

    def _load_active_listings_with_snapshots(
        self, db_path: Path, as_of_time: datetime | None
    ) -> list[dict[str, Any]]:
        """DB에서 활성 매물 및 최신 스냅샷 레코드 읽기 전용 로드 (CTE ROW_NUMBER() 적용 - 지침 1)."""
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        as_of_str = as_of_time.strftime("%Y-%m-%d %H:%M:%S") if as_of_time else "9999-12-31 23:59:59"

        # 지침 1: CTE ROW_NUMBER()를 사용하여 동일 시각 복수 스냅샷이 존재해도 결정적으로 단 1행만 반환
        query = """
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
                (
                    SELECT COUNT(*) 
                    FROM listing_snapshots ls 
                    WHERE ls.listing_id = l.listing_id 
                      AND ls.observed_at <= ?
                ) as snapshot_count,
                (
                    SELECT price_krw 
                    FROM listing_snapshots ls 
                    WHERE ls.listing_id = l.listing_id 
                      AND ls.observed_at <= ? 
                    ORDER BY ls.observed_at ASC, ls.snapshot_id ASC 
                    LIMIT 1
                ) as first_price_krw
            FROM listings l
            JOIN ranked_snapshots s ON s.listing_id = l.listing_id AND s.rn = 1
            WHERE l.first_observed_at <= ?
            ORDER BY s.observed_at DESC, s.snapshot_id DESC
        """
        rows = cursor.execute(query, (as_of_str, as_of_str, as_of_str, as_of_str)).fetchall()
        results: list[dict[str, Any]] = []

        for r in rows:
            raw_specs = r["raw_specs"]
            if isinstance(raw_specs, str):
                try:
                    raw_specs = json.loads(raw_specs)
                except Exception:
                    pass
            if isinstance(raw_specs, str):
                try:
                    raw_specs = json.loads(raw_specs)
                except Exception:
                    pass
            if not isinstance(raw_specs, dict):
                raw_specs = {}

            fp = raw_specs.get("vehicle_fingerprint") or ""
            year = self._extract_clean_year(raw_specs, fp)

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
                "model_year": year,
                "vehicle_fingerprint": fp,
                "snapshot_count": r["snapshot_count"],
                "first_price_krw": r["first_price_krw"] or r["price_krw"],
            })

        conn.close()
        return results

    def _load_price_events_summary(
        self, db_path: Path, as_of_time: datetime | None
    ) -> dict[str, dict[str, Any]]:
        """DB에서 가격 변동 이벤트 요약 정보 로드 (과거 시점 누수 차단)."""
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        as_of_str = as_of_time.strftime("%Y-%m-%d %H:%M:%S") if as_of_time else "9999-12-31 23:59:59"

        query = """
            SELECT 
                listing_id,
                COUNT(CASE WHEN event_type = 'PRICE_DROP' THEN 1 END) as drop_count,
                COALESCE(SUM(CASE WHEN event_type = 'PRICE_DROP' THEN -price_delta_krw ELSE 0 END), 0) as cum_drop_krw,
                (
                    SELECT price_delta_pct 
                    FROM price_events pe2 
                    WHERE pe2.listing_id = pe.listing_id 
                      AND pe2.event_type = 'PRICE_DROP' 
                      AND pe2.event_timestamp <= ? 
                    ORDER BY pe2.event_timestamp DESC, pe2.event_id DESC 
                    LIMIT 1
                ) as latest_drop_pct
            FROM price_events pe
            WHERE pe.event_timestamp <= ?
            GROUP BY listing_id
        """
        rows = cursor.execute(query, (as_of_str, as_of_str)).fetchall()
        summary: dict[str, dict[str, Any]] = {}
        for r in rows:
            summary[r["listing_id"]] = {
                "drop_count": r["drop_count"],
                "cum_drop_krw": r["cum_drop_krw"],
                "latest_drop_pct": r["latest_drop_pct"] or 0.0,
            }
        conn.close()
        return summary

    def _extract_clean_year(self, specs: dict[str, Any], fingerprint: str) -> int | None:
        """model_year 및 vehicle_fingerprint에서 정밀 연식 추출."""
        s_year = str(specs.get("model_year", "")).strip()
        if s_year.isdigit() and len(s_year) == 4 and (s_year.startswith("201") or s_year.startswith("202")):
            return int(s_year)

        if fingerprint:
            parts = fingerprint.split("_")
            for p in parts:
                if len(p) == 4 and p.isdigit() and (p.startswith("201") or p.startswith("202")):
                    return int(p)

        return None

    def _cluster_duplicate_fingerprints(
        self, listings: list[dict[str, Any]]
    ) -> tuple[dict[str, list[dict[str, Any]]], list[list[str]]]:
        """동일 vehicle_fingerprint 기반 중복 매물 클러스터링."""
        fp_map: dict[str, list[dict[str, Any]]] = {}
        for item in listings:
            fp = item["vehicle_fingerprint"]
            if not fp:
                continue
            if fp not in fp_map:
                fp_map[fp] = []
            fp_map[fp].append(item)

        clusters = [
            [m["source_listing_id"] for m in members]
            for fp, members in fp_map.items()
            if len(members) > 1
        ]
        return fp_map, clusters

    def _build_cohort_groups(
        self, listings: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """동일 매물 및 동일 실차 중복 없이 대표 가격만으로 코호트 그룹 구축."""
        groups: dict[str, list[dict[str, Any]]] = {}
        seen_fp_per_cohort: dict[str, set[str]] = {}

        for item in listings:
            key = self._extract_cohort_key(item)
            item["cohort_key"] = key
            if key not in groups:
                groups[key] = []
                seen_fp_per_cohort[key] = set()

            fp = item["vehicle_fingerprint"]
            if fp and fp in seen_fp_per_cohort[key]:
                continue
            if fp:
                seen_fp_per_cohort[key].add(fp)

            groups[key].append(item)

        return groups

    def _extract_cohort_key(self, item: dict[str, Any]) -> str:
        """아이템으로부터 정밀 코호트 키 생성."""
        specs = item.get("raw_specs", {})
        mfg = specs.get("manufacturer", "현대")
        model = specs.get("model", "아반떼")
        gen = "CN7"
        fingerprint = item.get("vehicle_fingerprint", "")
        fuel = "가솔린"
        trim = "모던"
        year_val = item.get("model_year")
        year_str = str(year_val) if year_val is not None else "UNKNOWN_YEAR"

        if fingerprint:
            parts = fingerprint.split("_")
            if len(parts) >= 8:
                gen = parts[2]
                fuel = parts[8] if len(parts) > 8 else parts[-2]
                trim = parts[9] if len(parts) > 9 else parts[-1]

        return f"{mfg}_{model}_{gen}_{year_str}_{trim}_{fuel}"

    def _evaluate_single_listing(
        self,
        item: dict[str, Any],
        cohort_groups: dict[str, list[dict[str, Any]]],
        price_events_summary: dict[str, Any],
        is_duplicate: bool,
        duplicate_ids: list[str],
    ) -> OpportunityCandidate:
        """단일 매물에 대한 정밀 종합 다차원 평가 수행."""
        listing_id = item["listing_id"]
        current_price = item["price_krw"]
        specs = item.get("raw_specs", {})
        mfg = specs.get("manufacturer", "현대")
        model = specs.get("model", "아반떼")
        gen = "CN7"
        year = item.get("model_year")
        mileage = item["mileage_km"] or 0
        raw_location = item["raw_location"]
        fp = item.get("vehicle_fingerprint", "")

        cohort_key = item["cohort_key"]
        cohort_members = cohort_groups.get(cohort_key, [])

        # 1. Leave-One-Out 비교 표본 추출: 대상 매물 및 대상 실차와 동일한 지문은 전원 배제
        peer_prices = [
            m["price_krw"]
            for m in cohort_members
            if m["listing_id"] != listing_id
            and (not fp or m.get("vehicle_fingerprint") != fp)
            and m["price_krw"]
            and m["price_krw"] > 0
        ]
        sample_count = len(peer_prices)

        # 2. 상대 시세 산출
        cohort_median: int | None = None
        rel_gap_krw: int | None = None
        rel_gap_pct: float | None = None
        p25_price: int | None = None
        p75_price: int | None = None

        if year is not None and sample_count >= self.config.min_benchmark_samples:
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

        # 4. 파트너 영업 적합성 분리
        if raw_location in ["서울", "장안평", "경기", "인천"]:
            partner_suitability = "LOCAL_OPERATIONAL"
            is_remote = False
        elif raw_location in ["UNKNOWN", ""]:
            partner_suitability = "LOCATION_VERIFICATION_REQUIRED"
            is_remote = True
        else:
            partner_suitability = "REMOTE_REGION_UNSUITABLE"
            is_remote = True

        # 중복 신뢰 수준 설정 (지침 2: 독립 식별자 없으므로 POSSIBLE_DUPLICATE)
        if is_duplicate:
            dup_status = "POSSIBLE_DUPLICATE"
        else:
            dup_status = "NO_DUPLICATE_DETECTED"

        # 5. 수익 시나리오 계산 (가정 기반 수익 추정치 - 지침 3)
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
            model_year=year,
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
            model_year=year,
            sample_count=sample_count,
            rel_gap_pct=rel_gap_pct,
            base_scenario=base_scenario,
            total_score=total_score,
            partner_suitability=partner_suitability,
            has_price_drop=has_price_drop,
            raw_location=raw_location,
            is_duplicate=is_duplicate,
            duplicate_ids=duplicate_ids,
        )

        year_display = f"{year}년식" if year else "연식미확인"
        vehicle_summary = f"{mfg} {model} {gen} ({year_display}, {mileage:,}km)"

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
            market_opportunity_grade=category,
            partner_operational_suitability=partner_suitability,
            vehicle_fingerprint=fp,
            duplicate_status=dup_status,
            duplicate_listing_ids=duplicate_ids,
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
        """가정 기반 수익 시나리오 계산 (순수익과 목표마진 분리 - 지침 3)."""
        costs = self.config.costs

        if scenario_type == "CONSERVATIVE":
            recond = costs.conservative_reconditioning_cost_krw
            logistics = costs.conservative_logistics_cost_krw + (
                costs.conservative_remote_surcharge_krw if is_remote else 0
            )
            target_margin = costs.conservative_target_margin_krw
        elif scenario_type == "OPTIMISTIC":
            recond = costs.optimistic_reconditioning_cost_krw
            logistics = costs.optimistic_logistics_cost_krw + (
                costs.optimistic_remote_surcharge_krw if is_remote else 0
            )
            target_margin = costs.optimistic_target_margin_krw
        else:  # BASE
            recond = costs.base_reconditioning_cost_krw
            logistics = costs.base_logistics_cost_krw + (
                costs.base_remote_surcharge_krw if is_remote else 0
            )
            target_margin = costs.base_target_margin_krw

        # 1. 총 스프레드 (가정 매매 차익)
        gross_spread = expected_sale_price - purchase_price

        # 2. 실제 발생 운영비용 (상품화 + 탁송)
        operating_cost = recond + logistics

        # 3. 실제 예상 순이익 (총차익 - 운영비용)
        net_profit = gross_spread - operating_cost

        # 4. 목표 마진 초과 달성액
        excess_over_target = net_profit - target_margin

        net_margin_pct = round((net_profit / purchase_price) * 100.0, 2) if purchase_price > 0 else 0.0

        return ProfitScenario(
            hypothetical_purchase_price_krw=purchase_price,
            hypothetical_sale_price_krw=expected_sale_price,
            hypothetical_gross_spread_krw=gross_spread,
            hypothetical_operating_cost_krw=operating_cost,
            hypothetical_net_profit_krw=net_profit,
            target_margin_krw=target_margin,
            excess_over_target_krw=excess_over_target,
            hypothetical_margin_pct=net_margin_pct,
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
        model_year: int | None,
    ) -> tuple[dict[str, float], str]:
        """4대 축 기회 점수 계산."""
        cfg = self.config

        if model_year is None:
            s_rel = 0.0
            data_conf = "INSUFFICIENT"
            s_conf = 0.0
        else:
            s_rel = 0.0
            if rel_gap_pct is not None and rel_gap_pct > 0:
                s_rel = min(cfg.weight_relative_price, (rel_gap_pct / 10.0) * cfg.weight_relative_price)
            elif rel_gap_pct is not None and rel_gap_pct <= 0:
                s_rel = 0.0

            if sample_count >= cfg.high_confidence_samples:
                s_conf = cfg.weight_data_confidence
                data_conf = "HIGH"
            elif sample_count >= cfg.min_benchmark_samples:
                s_conf = cfg.weight_data_confidence * 0.6
                data_conf = "MEDIUM"
            elif sample_count > 0:
                s_conf = cfg.weight_data_confidence * 0.2
                data_conf = "LOW"
            else:
                s_conf = 0.0
                data_conf = "INSUFFICIENT"

        s_drop = 0.0
        if has_price_drop:
            pct_score = min(10.0, latest_drop_pct * 2.0)
            cnt_score = min(5.0, (drop_count - 1) * 2.5) if drop_count > 1 else 0.0
            s_drop = min(cfg.weight_price_drop, 10.0 + pct_score + cnt_score)

        s_profit = 0.0
        if base_scenario and base_scenario.hypothetical_net_profit_krw > 0:
            s_profit = min(cfg.weight_profitability, (base_scenario.hypothetical_net_profit_krw / 1_500_000.0) * cfg.weight_profitability)

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
        model_year: int | None,
        sample_count: int,
        rel_gap_pct: float | None,
        base_scenario: ProfitScenario | None,
        total_score: float,
        partner_suitability: str,
        has_price_drop: bool,
        raw_location: str,
        is_duplicate: bool,
        duplicate_ids: list[str],
    ) -> tuple[str, str, list[str]]:
        """엄격한 4단계 기회 등급 분류."""
        risks: list[str] = []

        if partner_suitability == "LOCATION_VERIFICATION_REQUIRED":
            risks.append("지역 정보 미확인(추가 실사 필요)")
        elif partner_suitability == "REMOTE_REGION_UNSUITABLE":
            risks.append(f"원거리 지역({raw_location}) 매물(추가 탁송료 발생)")

        if is_duplicate:
            risks.append(f"동일 지문 추정 중복 광고 감지 (POSSIBLE_DUPLICATE: ID {', '.join(duplicate_ids)})")

        if product_type != "CASH_OR_INSTALLMENT":
            return "EXCLUDED", "금융상품(렌트/리스) 매물로 일반 매매 대상 제외", ["FINANCIAL_PRODUCT"]

        if not current_price or current_price <= 0:
            return "EXCLUDED", "가격 정보 누락 또는 비정상 가격 데이터", ["INVALID_PRICE"]

        if model_year is None:
            risks.append("연식 정보 미확인(NOYEAR: 시세 비교 불가)")
            return (
                "INSUFFICIENT_DATA",
                "차량 연식 정보 미확인으로 정밀 시세 비교 불가 (우선 추천 보류)",
                risks,
            )

        if sample_count < self.config.min_benchmark_samples:
            risks.append("동일 코호트 비교 표본 부족")
            return (
                "INSUFFICIENT_DATA",
                f"동일 코호트 비교 표본 부족 ({sample_count}건 < 기준 {self.config.min_benchmark_samples}건)",
                risks,
            )

        if base_scenario and base_scenario.hypothetical_net_profit_krw <= 0:
            risks.append("기준 시나리오 예상 순이익 적자/부족")

        if rel_gap_pct is not None and rel_gap_pct < 0:
            risks.append(f"동일 코호트 시세 대비 {abs(rel_gap_pct):.1f}% 고가 매물")

        if rel_gap_pct is not None and rel_gap_pct <= -10.0:
            return "EXCLUDED", f"시세 중앙값 대비 {abs(rel_gap_pct):.1f}% 고가로 가격 경쟁력 없음", risks

        if (
            model_year is not None
            and rel_gap_pct is not None
            and rel_gap_pct >= self.config.price_advantage_threshold_pct
            and base_scenario
            and base_scenario.hypothetical_net_profit_krw >= self.config.costs.base_target_margin_krw
            and (total_score >= 50.0 or has_price_drop)
        ):
            reason = (
                f"{model_year}년식 동일 코호트 시세 대비 {rel_gap_pct:.1f}% 저렴하며, "
                f"가정 기반 순이익 {base_scenario.hypothetical_net_profit_krw:,}원 확보 가능"
            )
            if has_price_drop:
                reason += " (최근 가격 인하 포착)"
            return "PRIORITY_REVIEW", reason, risks

        if (rel_gap_pct is not None and rel_gap_pct > 0) or has_price_drop:
            reason = "시세 대비 소폭 우위 또는 가격 변동 감지 매물로 지속 관측 필요"
            return "WATCHLIST", reason, risks

        return "EXCLUDED", "시세 경쟁력 및 가격 변동 모멘텀 부족", risks

    def export_results_to_csv(
        self, candidates: list[OpportunityCandidate], output_path: Path
    ) -> None:
        """분석 결과를 지정된 CSV 파일로 출력 (지침 4 딜러 실전 검토표 양식 완비)."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "listing_id",
            "source_platform",
            "source_listing_id",
            "source_url",
            "vehicle_summary",
            "model_year",
            "mileage_km",
            "current_price_krw",
            "cohort_median_price_krw",
            "relative_price_gap_pct",
            "cumulative_price_drop_krw",
            "observation_count",
            "hypothetical_gross_spread_krw",
            "hypothetical_operating_cost_krw",
            "hypothetical_net_profit_krw",
            "target_margin_krw",
            "excess_over_target_krw",
            "opportunity_score",
            "data_confidence",
            "market_opportunity_grade",
            "partner_operational_suitability",
            "duplicate_status",
            "duplicate_listing_ids",
            "raw_location",
            "history_check_required",
            # 딜러 파일럿 실전 피드백 입력란 (지침 4)
            "dealer_review_verdict",
            "dealer_expected_purchase_price_krw",
            "dealer_expected_sale_price_krw",
            "dealer_expected_reconditioning_cost_krw",
            "dealer_decision_reason",
            "dealer_reviewed_at",
            "evaluation_reason",
            "risk_factors",
        ]

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for c in candidates:
                b = c.base_scenario
                url = f"https://www.encar.com/dc/dc_cardetailview.do?method=kidiCarDet&carid={c.source_listing_id}"
                writer.writerow({
                    "listing_id": c.listing_id,
                    "source_platform": c.source_platform,
                    "source_listing_id": c.source_listing_id,
                    "source_url": url,
                    "vehicle_summary": c.vehicle_summary,
                    "model_year": c.model_year or "",
                    "mileage_km": c.mileage_km,
                    "current_price_krw": c.current_price_krw,
                    "cohort_median_price_krw": c.cohort_median_price_krw or "",
                    "relative_price_gap_pct": c.relative_price_gap_pct or "",
                    "cumulative_price_drop_krw": c.cumulative_price_drop_krw,
                    "observation_count": c.observation_count,
                    "hypothetical_gross_spread_krw": b.hypothetical_gross_spread_krw if b else 0,
                    "hypothetical_operating_cost_krw": b.hypothetical_operating_cost_krw if b else 0,
                    "hypothetical_net_profit_krw": b.hypothetical_net_profit_krw if b else 0,
                    "target_margin_krw": b.target_margin_krw if b else 0,
                    "excess_over_target_krw": b.excess_over_target_krw if b else 0,
                    "opportunity_score": c.opportunity_score,
                    "data_confidence": c.data_confidence,
                    "market_opportunity_grade": c.market_opportunity_grade,
                    "partner_operational_suitability": c.partner_operational_suitability,
                    "duplicate_status": c.duplicate_status,
                    "duplicate_listing_ids": " | ".join(c.duplicate_listing_ids),
                    "raw_location": c.raw_location,
                    "history_check_required": "보험사고/침수/용도이력 실사필요",
                    # 딜러 입력 필드는 공백으로 초기화
                    "dealer_review_verdict": "",
                    "dealer_expected_purchase_price_krw": "",
                    "dealer_expected_sale_price_krw": "",
                    "dealer_expected_reconditioning_cost_krw": "",
                    "dealer_decision_reason": "",
                    "dealer_reviewed_at": "",
                    "evaluation_reason": c.evaluation_reason,
                    "risk_factors": " | ".join(c.risk_factors),
                })
