"""차피셜 기회 탐지 인텔리전스 패키지."""

from chaficial.intelligence.config import CostAssumptions, OpportunityEngineConfig
from chaficial.intelligence.opportunity_engine import (
    MarketOpportunityEngine,
    OpportunityCandidate,
    ProfitScenario,
)

__all__ = [
    "MarketOpportunityEngine",
    "OpportunityCandidate",
    "ProfitScenario",
    "OpportunityEngineConfig",
    "CostAssumptions",
]
