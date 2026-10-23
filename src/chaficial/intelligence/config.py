"""차피셜 기회 탐지 엔진 파라미터 및 수익 시나리오 비용 가정 설정 (DIRECTIVE 015-A)."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CostAssumptions:
    """차량 매입 후 실제 운영비용(Operating Cost) 및 목표마진(Target Margin) 가정치.

    - 운영비용 (Operating Cost): 실제 지출되는 상품화비 및 탁송/이전비
    - 목표마진 (Target Margin): 딜러 파트너가 요구하는 최소 기대 수익 기준
    """

    # 기준(Base) 시나리오
    base_reconditioning_cost_krw: int = 800_000   # 표준 상품화(광택, 세차, 경정비) 실제 지출비
    base_logistics_cost_krw: int = 300_000        # 수도권 표준 탁송/이전 실제 지출비
    base_remote_surcharge_krw: int = 200_000      # 비수도권/지방 매물 추가 탁송료
    base_target_margin_krw: int = 500_000         # 딜러 목표 기본 마진 (비용이 아닌 기대수익 기준)

    # 보수적(Conservative) 시나리오
    conservative_reconditioning_cost_krw: int = 1_200_000  # 정비 리스크 반영 상품화비
    conservative_logistics_cost_krw: int = 400_000         # 보수적 탁송/부대비용
    conservative_remote_surcharge_krw: int = 300_000       # 장거리 탁송료
    conservative_target_margin_krw: int = 700_000          # 보수적 최소 요구 마진 기준

    # 낙관적(Optimistic) 시나리오
    optimistic_reconditioning_cost_krw: int = 500_000      # 기본 세차/점검 수준 상품화비
    optimistic_logistics_cost_krw: int = 200_000          # 근거리 탁송료
    optimistic_remote_surcharge_krw: int = 150_000        # 탁송료 할인
    optimistic_target_margin_krw: int = 400_000           # 최소 기대 마진 기준


@dataclass
class OpportunityEngineConfig:
    """기회 탐지 엔진 통합 설정."""

    min_benchmark_samples: int = 3          # 최소 독립 비교 표본 수 (Leave-One-Out)
    high_confidence_samples: int = 5        # 높은 신뢰도 인정 최소 표본 수
    significant_price_drop_pct: float = 3.0 # 의미 있는 가격 인하율 기준 (3.0%)
    price_advantage_threshold_pct: float = 5.0 # 시세 대비 우위 최소 기준 (5.0%)

    # 가중치 (총합 100점)
    weight_relative_price: float = 40.0     # 상대 시세 대비 가격 경쟁력 (최대 40점)
    weight_price_drop: float = 25.0         # 최근 가격 인하 폭 및 빈도 (최대 25점)
    weight_profitability: float = 20.0      # 수익 시나리오 마진성 (최대 20점)
    weight_data_confidence: float = 15.0    # 데이터 충분성 및 표본 신뢰도 (최대 15점)

    # 파트너 영업 허용 지역 (기본: 서울/장안평 및 수도권)
    target_partner_regions: list[str] = field(
        default_factory=lambda: ["서울", "장안평", "경기", "인천"]
    )

    costs: CostAssumptions = field(default_factory=CostAssumptions)
    db_path: Path = Path("data/chaficial_market_timeseries.db")
