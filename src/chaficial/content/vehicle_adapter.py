"""기존 차량 선별 엔진과 콘텐츠 엔진 간 명시적 데이터 어댑터 및 인터페이스.

DIRECTIVE 003-A 명세 준수:
- 기존 SalesCandidate, Listing, Vehicle 등에서 추천 차량 정보를 전달받음
- 가격, 연식, 주행거리, 옵션, 특이사항 검증
- 정보 누락 시 임의로 채우지 않고 MISSING / VERIFY_REQUIRED 상태 부여
- 인터페이스 규격 불일치 시 InvalidVehicleInterfaceError 발생
- 사용 권한(republication_allowed)이 확보된 이미지 자산 관리
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from chaficial.content.models import (
    AssetType,
    InvalidVehicleInterfaceError,
    MediaAsset,
    MissingVehicleInfoError,
    VehicleContentCandidate,
)


class VehicleContentAdapter:
    """차량 선별 엔진의 출력을 콘텐츠 엔진 후보로 변환하는 명시적 어댑터."""

    REQUIRED_RAW_FIELDS: ClassVar[set[str]] = {"vehicle_id", "data_source"}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VehicleContentCandidate:
        """딕셔너리 형태의 차량/매물 정보를 콘텐츠 후보로 변환."""
        if not isinstance(data, dict):
            raise InvalidVehicleInterfaceError(
                f"차량 데이터는 반드시 dict 형태여야 합니다. (입력 타입: {type(data)})"
            )

        missing_fields = cls.REQUIRED_RAW_FIELDS - set(data.keys())
        if missing_fields:
            raise InvalidVehicleInterfaceError(
                f"차량 데이터에 필수 식별 인터페이스 필드가 누락되었습니다: {missing_fields}"
            )

        vehicle_id = str(data["vehicle_id"]).strip()
        if not vehicle_id:
            raise InvalidVehicleInterfaceError("vehicle_id는 비어 있을 수 없습니다.")

        data_source = str(data["data_source"]).strip()

        # 차량 제원 추출
        model_name = data.get("model_name")
        model_year = data.get("model_year")
        price = data.get("price")
        mileage = data.get("mileage")

        # 옵션 및 특징
        options = list(data.get("options") or [])
        verified_pros = list(data.get("verified_pros") or [])
        precautions = list(data.get("precautions") or [])

        # 이미지 에셋 정규화
        raw_images = data.get("images") or []
        parsed_images: list[MediaAsset] = []
        for idx, img in enumerate(raw_images):
            if isinstance(img, dict):
                path = img.get("path_or_url") or img.get("url") or img.get("path", "")
                label = img.get("label", f"차량 사진 {idx + 1}")
                is_authorized = bool(
                    img.get("is_authorized")
                    or img.get("republication_allowed", False)
                )
                auth_ref = img.get("authorization_reference", "")
            elif isinstance(img, str):
                path = img
                label = f"차량 사진 {idx + 1}"
                is_authorized = False  # 문자열만 전달된 경우 기본 비인가(보수적 접근)
                auth_ref = "UNKNOWN"
            else:
                continue

            parsed_images.append(
                MediaAsset(
                    asset_type=AssetType.IMAGE,
                    path_or_url=path,
                    label=label,
                    is_authorized=is_authorized,
                    authorization_reference=auth_ref,
                    slot_tag=f"@Image {idx + 2}"  # @Image 1은 대표님 시트용 슬롯
                )
            )

        # 상태 결정: 임의로 누락 정보를 채우지 않고 상태로 표시
        missing_attrs: list[str] = []
        if not model_name:
            missing_attrs.append("model_name")
        if model_year is None or model_year < 1980:
            missing_attrs.append("model_year")
        if price is None or price <= 0:
            missing_attrs.append("price")
        if mileage is None or mileage < 0:
            missing_attrs.append("mileage")

        if missing_attrs:
            availability_status = "MISSING" if len(missing_attrs) >= 2 else "VERIFY_REQUIRED"
            precautions.append(f"필수 차량 정보 미확인 항목 존재: {', '.join(missing_attrs)}")
        else:
            availability_status = data.get("availability_status", "AVAILABLE")

        return VehicleContentCandidate(
            vehicle_id=vehicle_id,
            data_source=data_source,
            model_name=model_name,
            model_year=model_year,
            price=price,
            mileage=mileage,
            options=options,
            verified_pros=verified_pros,
            precautions=precautions,
            verified_at=datetime.now(UTC) if not missing_attrs else None,
            availability_status=availability_status,
            images=parsed_images,
            recommendation_reason=data.get("recommendation_reason", "AI 수익성 선별 매물"),
            recommendation_source=data.get("recommendation_source", "OPPORTUNITY_ENGINE"),
        )

    @classmethod
    def validate_production_readiness(
        cls, candidate: VehicleContentCandidate, require_strict: bool = True
    ) -> None:
        """콘텐츠 제작 진입 전 필수 제원 및 권한의 완결성을 최종 검증."""
        is_valid, missing = candidate.validate_essential_info()
        if not is_valid:
            raise MissingVehicleInfoError(
                f"차량 필수 정보가 누락되어 콘텐츠 제작을 시작할 수 없습니다: {missing}. "
                f"현재 상태: {candidate.availability_status}"
            )

        if candidate.availability_status not in ("AVAILABLE", "CONFIRMED"):
            raise MissingVehicleInfoError(
                f"차량 상태가 제작 불가 상태입니다: {candidate.availability_status}. "
                "확인된 정보로 갱신하거나 상태를 AVAILABLE로 변경해야 합니다."
            )

        if require_strict and not candidate.images:
            raise MissingVehicleInfoError("제작에 사용할 검증된 차량 이미지가 1장도 없습니다.")
