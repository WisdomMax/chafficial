"""차피셜 기회 탐지 엔진 파라미터 및 수익 시나리오 비용 가정 설정 (DIRECTIVE 015)."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CostAssumptions:
    """차량 매입 후 상품화 및 부대비용 가정치 (Hypothetical Estimates).

    주의: 실제 딜러 매입 원가나 수수료 데이터가 없는 현 단계에서는
    업계 표준 기반의 보수적/기준/낙관적 시나리오 분석을 위한 가정치입니다.
    """

    # 기준(Base) 시나리오 비용 (단위: 원)
    base_reconditioning_cost_krw: int = 800_000   # 표준 상품화(광택, 세차, 경정비) 비용
    base_logistics_cost_krw: int = 300_000        # 수도권 표준 탁송/이전 부대비용
    base_remote_surcharge_krw: int = 200_000      # 비수도권/지방 매물 추가 탁송료
    base_target_margin_krw: int = 500_000         # 딜러 목표 기본 마진 및 판매 수수료

    # 보수적(Conservative) 시나리오 비용 (단위: 원)
    conservative_reconditioning_cost_krw: int = 1_200_000  # 주요 부품 교환 등 보수적 상품화 비용
    conservative_logistics_cost_krw: int = 400_000         # 보수적 이전 부대비용
    conservative_remote_surcharge_krw: int = 300_000       # 장거리 탁송료
    conservative_target_margin_krw: int = 700_000          # 보수적 최소 요구 마진

    # 낙관적(Optimistic) 시나리오 비용 (단위: 원)
    optimistic_reconditioning_cost_krw: int = 500_000      # 단순 세차/기본 점검 수준
    optimistic_logistics_cost_krw: int = 200_000          # 근거리 탁송료
    optimistic_remote_surcharge_krw: int = 150_000        # 원거리 탁송 할인
    optimistic_target_margin_krw: int = 400_000           # 최소 운영 마진


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
