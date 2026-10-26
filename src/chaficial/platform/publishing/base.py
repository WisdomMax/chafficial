"""다중 플랫폼 매핑 어댑터 및 등록 준비도 검사 기본 규격 (DIRECTIVE 050 4항)."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ValidationIssue:
    field: str
    message: str
    severity: str = "ERROR"  # ERROR, WARNING


@dataclass
class ReadinessReport:
    platform: str
    is_ready: bool
    missing_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    mapped_payload: dict[str, Any] = field(default_factory=dict)
    summary_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BasePlatformMapper(ABC):
    """외부 플랫폼별 필드 변환 및 등록 준비도 검사 어댑터 추상 베이스."""

    def __init__(self, platform_name: str):
        self.platform_name = platform_name

    @abstractmethod
    def validate_readiness(self, vehicle: Any, context: dict[str, Any] | None = None) -> ReadinessReport:
        """등록 전 필수 필드, 사진 요건, 딜러 권한, 서류 증빙 검증."""
        pass

    @abstractmethod
    def build_export_payload(self, vehicle: Any, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """플랫폼 게시/등록용 표준 JSON 페이로드 생성."""
        pass
