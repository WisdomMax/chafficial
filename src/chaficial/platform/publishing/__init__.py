"""다중 플랫폼 차량 등록 및 게시 준비도(Readiness) 패키지 (DIRECTIVE 050)."""

from chaficial.platform.publishing.base import (
    BasePlatformMapper,
    ValidationIssue,
    ReadinessReport,
)
from chaficial.platform.publishing.encar import EncarPlatformMapper
from chaficial.platform.publishing.kb import KbPlatformMapper
from chaficial.platform.publishing.carmanager import CarManagerPlatformMapper
from chaficial.platform.publishing.validator import PublishingReadinessValidator

__all__ = [
    "BasePlatformMapper",
    "ValidationIssue",
    "ReadinessReport",
    "EncarPlatformMapper",
    "KbPlatformMapper",
    "CarManagerPlatformMapper",
    "PublishingReadinessValidator",
]
