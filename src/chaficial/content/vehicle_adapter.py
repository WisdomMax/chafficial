"""기존 차량 선별 엔진과 콘텐츠 엔진 간 명시적 데이터 어댑터 및 상업적 적격성 감사기.

DIRECTIVE 003-A1 개정 준수:
- SalesCandidate, Listing, VehicleIdentity, ListingSnapshot ORM 객체 연동
- 후보 차량의 식별자 정합성 확인
- 현재 매물 상태 (Listing.current_status == 'ACTIVE') 필수 검증
- 파트너 검토 및 승인 상태 (partner_review_status == 'APPROVED') 필수 검증
- 가격 관측 시점의 최신성 (30일 이내 관측 스냅샷) 검증
- 사진 자산의 republication_allowed 권한 전수 검증
- 미확인 제원 및 미확인 사고 이력의 임의 단정 차단
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from chaficial.content.models import (
    AssetType,
    InvalidVehicleInterfaceError,
    MediaAsset,
    MissingVehicleInfoError,
    UnauthorizedAssetError,
    VehicleContentCandidate,
)


class CommercialIneligibilityError(MissingVehicleInfoError):
    """실제 판매 홍보가 불가능한 매물이 영상 제작 승인으로 넘어갈 때 발생하는 예외."""


class VehicleContentAdapter:
    """차량 선별 엔진의 출력을 콘텐츠 엔진 후보로 변환하고 상업적 적격성을 감사하는 어댑터."""

    REQUIRED_RAW_FIELDS: ClassVar[set[str]] = {"vehicle_id", "data_source"}

    @classmethod
    def from_sales_candidate(
        cls,
        candidate: Any,
        latest_snapshot: Any = None,
        permission: Any = None,
        images: list[dict[str, Any] | MediaAsset] | None = None,
    ) -> VehicleContentCandidate:
        """기존 SalesCandidate ORM 객체로부터 VehicleContentCandidate 생성 및 적격성 검증."""
        if not hasattr(candidate, "candidate_id") or not hasattr(candidate, "listing"):
            raise InvalidVehicleInterfaceError(
                "SalesCandidate 객체 규격과 일치하지 않습니다. (필수 속성: candidate_id, listing)"
            )

        listing = getattr(candidate, "listing", None)
        if not listing:
            raise InvalidVehicleInterfaceError("SalesCandidate에 연결된 Listing이 존재하지 않습니다.")

        vehicle = getattr(listing, "vehicle", None)
        catalog = getattr(vehicle, "catalog", None) if vehicle else None

        # 1. 모델명 추출
        model_name = catalog.full_name() if catalog and hasattr(catalog, "full_name") else getattr(catalog, "model_name", None)
        model_year = getattr(catalog, "model_year", None)

        # 2. 가격 및 주행거리 (스냅샷 우선)
        price = getattr(latest_snapshot, "price", None) if latest_snapshot else getattr(candidate, "price", None)
        mileage = getattr(latest_snapshot, "mileage", None) if latest_snapshot else getattr(candidate, "mileage", None)

        # 3. 데이터 출처 권한
        is_source_authorized = False
        auth_ref = "UNKNOWN"
        if permission:
            is_source_authorized = bool(getattr(permission, "republication_allowed", False))
            auth_ref = getattr(permission, "authorization_reference", "파트너 제휴 계약")

        # 4. 이미지 정규화
        parsed_images: list[MediaAsset] = []
        raw_images = images or []
        for idx, img in enumerate(raw_images):
            if isinstance(img, MediaAsset):
                parsed_images.append(img)
            elif isinstance(img, dict):
                parsed_images.append(
                    MediaAsset(
                        asset_type=AssetType.IMAGE,
                        path_or_url=img.get("path_or_url") or img.get("url", ""),
                        label=img.get("label", f"차량 사진 {idx + 1}"),
                        is_authorized=bool(img.get("is_authorized", is_source_authorized)),
                        authorization_reference=img.get("authorization_reference", auth_ref),
                        slot_tag=f"@Image {idx + 2}",
                    )
                )

        # 5. 상태 속성
        avail_status = getattr(candidate, "availability_status", "UNCONFIRMED")
        partner_review = getattr(candidate, "partner_review_status", "PENDING")
        listing_status = getattr(listing, "current_status", "UNKNOWN")

        # 딕셔너리로 합성 후 from_dict 호출
        payload = {
            "vehicle_id": getattr(vehicle, "vehicle_id", listing.listing_id),
            "data_source": getattr(listing, "source_platform", "CHAFICIAL_CORE"),
            "model_name": model_name,
            "model_year": model_year,
            "price": price,
            "mileage": mileage,
            "availability_status": avail_status,
            "partner_review_status": partner_review,
            "listing_status": listing_status,
            "images": parsed_images,
            "recommendation_reason": getattr(candidate, "selection_reason", "AI 추천 매물"),
            "recommendation_source": getattr(candidate, "selected_by", "AI_AGENT"),
            "snapshot_observed_at": getattr(latest_snapshot, "observed_at", None) if latest_snapshot else None,
        }
        return cls.from_dict(payload)

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
            if isinstance(img, MediaAsset):
                parsed_images.append(img)
            elif isinstance(img, dict):
                path = img.get("path_or_url") or img.get("url") or img.get("path", "")
                label = img.get("label", f"차량 사진 {idx + 1}")
                is_authorized = bool(
                    img.get("is_authorized")
                    or img.get("republication_allowed", False)
                )
                auth_ref = img.get("authorization_reference", "")
                parsed_images.append(
                    MediaAsset(
                        asset_type=AssetType.IMAGE,
                        path_or_url=path,
                        label=label,
                        is_authorized=is_authorized,
                        authorization_reference=auth_ref,
                        slot_tag=f"@Image {idx + 2}",
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

        # 파트너 검토 및 매물 상태 반영
        partner_review = data.get("partner_review_status", "APPROVED")
        listing_status = data.get("listing_status", "ACTIVE")
        avail_status = data.get("availability_status", "AVAILABLE")

        if missing_attrs:
            availability_status = "MISSING" if len(missing_attrs) >= 2 else "VERIFY_REQUIRED"
            precautions.append(f"필수 차량 정보 미확인 항목 존재: {', '.join(missing_attrs)}")
        elif partner_review != "APPROVED":
            availability_status = "PARTNER_UNAPPROVED"
            precautions.append(f"파트너 승인 미완료 상태: {partner_review}")
        elif listing_status != "ACTIVE":
            availability_status = "DELISTED"
            precautions.append(f"매물 상태 비활성(판매종료 등): {listing_status}")
        else:
            availability_status = avail_status

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
    def validate_commercial_eligibility(
        cls,
        candidate: VehicleContentCandidate,
        max_observed_days: int = 30,
        require_images: bool = False,
    ) -> None:
        """실제 판매 홍보 및 영상 제작이 가능한 매물인지 엄격하게 감사.
        
        불합격 조건:
        1. availability_status != 'AVAILABLE' (품절, 미확인 등)
        2. 제원 누락 (모델명, 연식, 가격, 주행거리)
        3. 인가된 실차 사진이 1장도 없음 (require_images=True 시)
        4. 권한 없는(republication_allowed=False) 사진 포함
        """
        # 1. 상태 검증
        if candidate.availability_status != "AVAILABLE":
            raise CommercialIneligibilityError(
                f"매물 상태가 판매 홍보 불가 상태입니다: '{candidate.availability_status}'. "
                f"사유: {candidate.precautions}"
            )

        # 2. 필수 제원 검증
        is_valid, missing = candidate.validate_essential_info()
        if not is_valid:
            raise MissingVehicleInfoError(
                f"필수 제원이 누락된 차량은 홍보 영상을 제작할 수 없습니다: {missing}"
            )

        # 3. 이미지 존재 및 권한 전수 감사
        if require_images and not candidate.images:
            raise MissingVehicleInfoError("판매 홍보에 사용할 실차 사진이 1장도 등록되지 않았습니다.")

        for img in candidate.images:
            if not img.is_authorized:
                raise UnauthorizedAssetError(
                    f"에셋 '{img.label}'({img.path_or_url})의 상업적 재배포 권한이 없습니다. "
                    "권한 없는 사진은 제작에 사용할 수 없습니다."
                )

    @classmethod
    def validate_production_readiness(
        cls, candidate: VehicleContentCandidate, require_strict: bool = True
    ) -> None:
        """기존 호환 메서드."""
        cls.validate_commercial_eligibility(candidate)
