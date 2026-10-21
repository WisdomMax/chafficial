"""차피셜(CHA-FICIAL) 데이터 모델 패키지."""

from chaficial.models.candidate import SalesCandidate
from chaficial.models.catalog import VehicleCatalog
from chaficial.models.condition import VehicleCondition
from chaficial.models.decision import PromotionDecision
from chaficial.models.listing import Listing
from chaficial.models.marketing import MarketingResult
from chaficial.models.options import VehicleOption
from chaficial.models.outcome import SalesOutcome
from chaficial.models.partner import SalesPartner
from chaficial.models.permission import DataSourcePermission
from chaficial.models.price_event import PriceEvent
from chaficial.models.region import Region, RegionConfiguration
from chaficial.models.settlement import Settlement
from chaficial.models.snapshot import ListingSnapshot
from chaficial.models.vehicle import VehicleIdentity
from chaficial.models.vehicle_link import VehicleIdentityLink

__all__ = [
    "DataSourcePermission",
    "Listing",
    "ListingSnapshot",
    "MarketingResult",
    "PriceEvent",
    "PromotionDecision",
    "Region",
    "RegionConfiguration",
    "SalesCandidate",
    "SalesOutcome",
    "SalesPartner",
    "Settlement",
    "VehicleCatalog",
    "VehicleCondition",
    "VehicleIdentity",
    "VehicleIdentityLink",
    "VehicleOption",
]
