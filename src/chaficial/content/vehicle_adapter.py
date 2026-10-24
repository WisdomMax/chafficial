"""기존 차량 선별 엔진과 콘텐츠 엔진 간 명시적 데이터 어댑터 및 상업적 적격성 감사기.

DIRECTIVE 003-A2 개정 준수:
- 실제 SQLAlchemy ORM 모델(SalesCandidate, Listing, VehicleIdentity, ListingSnapshot 등) 필드 정확히 바인딩
  - price_krw (원 단위) -> price (만원 단위: price_krw // 10000)
  - mileage_km (km 단위)
  - observed_at (스냅샷 관측 시각)
- 최신 스냅샷 자동 정렬 선택 및 관측 시점 최신성(30일) 검증
- Fail-Closed 원칙: 누락/미확인 시 기본값 UNCONFIRMED / PENDING / UNKNOWN 강제
- 내부 사용 권한(internal_storage_allowed)과 외부 광고 재배포 권한(republication_allowed) 엄격 분리
- 사진이 0장이거나 비인가 사진 포함 시 홍보 프로젝트 생성 원천 차단
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from chaficial.content.models import (
    AssetType,
    CommercialIneligibilityError,
    FactEvidence,
    InvalidVehicleInterfaceError,
    MediaAsset,
    MissingVehicleInfoError,
    UnauthorizedAssetError,
    VehicleContentCandidate,
    VerificationStatus,
)


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

        # 1. 모델명 및 연식 추출
        model_name = catalog.full_name() if catalog and hasattr(catalog, "full_name") else getattr(catalog, "model_name", None)
        model_year = getattr(catalog, "model_year", None)

        # 2. 최신 스냅샷 탐색 (명시적 전달이 없으면 listing.snapshots에서 observed_at 기준 최신 선택)
        selected_snapshot = latest_snapshot
        if selected_snapshot is None and hasattr(listing, "snapshots") and listing.snapshots:
            # observed_at 기준 내림차순 정렬하여 가장 최신 스냅샷 선택
            try:
                snapshots_sorted = sorted(
                    listing.snapshots,
                    key=lambda s: getattr(s, "observed_at", datetime.min.replace(tzinfo=UTC)),
                    reverse=True,
                )
                if snapshots_sorted:
                    selected_snapshot = snapshots_sorted[0]
            except (AttributeError, TypeError):
                selected_snapshot = None

        # 3. 가격 (price_krw -> price 만원 단위 변환) 및 주행거리 (mileage_km)
        price_krw: int | None = None
        price_manwon: int | None = None
        mileage_km: int | None = None
        observed_at: datetime | None = None

        if selected_snapshot:
            price_krw = getattr(selected_snapshot, "price_krw", None)
            if price_krw is not None and price_krw > 0:
                price_manwon = price_krw // 10000  # 원 단위 -> 만원 단위 변환
            mileage_km = getattr(selected_snapshot, "mileage_km", None)
            observed_at = getattr(selected_snapshot, "observed_at", None)
        else:
            # 스냅샷이 없으면 candidate 직접 속성 확인
            raw_p = getattr(candidate, "price", None)
            if raw_p is not None:
                price_manwon = raw_p if raw_p < 1_000_000 else raw_p // 10000
                price_krw = price_manwon * 10000
            mileage_km = getattr(candidate, "mileage", None)

        # 4. 데이터 출처 권한 (내부 보관과 외부 광고 재배포 엄격 분리)
        repub_allowed = False
        internal_allowed = False
        auth_ref = "UNKNOWN"
        if permission:
            repub_allowed = bool(getattr(permission, "republication_allowed", False))
            internal_allowed = bool(getattr(permission, "storage_allowed", False))
            auth_ref = getattr(permission, "authorization_reference", "파트너 계약서")

        # 5. 이미지 정규화
        parsed_images: list[MediaAsset] = []
        raw_images = images or []
        for idx, img in enumerate(raw_images):
            if isinstance(img, MediaAsset):
                parsed_images.append(img)
            elif isinstance(img, dict):
                p_repub = bool(img.get("republication_allowed", repub_allowed))
                p_internal = bool(img.get("internal_storage_allowed", internal_allowed))
                parsed_images.append(
                    MediaAsset(
                        asset_type=AssetType.IMAGE,
                        path_or_url=img.get("path_or_url") or img.get("url", ""),
                        label=img.get("label", f"차량 사진 {idx + 1}"),
                        republication_allowed=p_repub,
                        internal_storage_allowed=p_internal,
                        authorization_reference=img.get("authorization_reference", auth_ref),
                        slot_tag=f"@Image {idx + 2}",
                    )
                )

        # 6. 상태 속성 (Fail-closed 기본값)
        avail_status = getattr(candidate, "availability_status", "UNCONFIRMED")
        partner_review = getattr(candidate, "partner_review_status", "PENDING")
        listing_status = getattr(listing, "current_status", "UNKNOWN")

        # 7. 증빙 구성
        evidences: list[FactEvidence] = []
        if selected_snapshot:
            evidences.append(
                FactEvidence(
                    source_type="ListingSnapshot",
                    document_ref=getattr(selected_snapshot, "snapshot_id", "SNAPSHOT-LATEST"),
                    verified_at=observed_at or datetime.now(UTC),
                    verification_status=VerificationStatus.VERIFIED,
                    verified_by="CHAFICIAL_DATA_ENGINE",
                    notes=f"실거래 관측 가격: {price_manwon}만원 (원단위 {price_krw:,}원), 주행: {mileage_km:,}km",
                )
            )

        payload = {
            "vehicle_id": getattr(vehicle, "vehicle_id", listing.listing_id),
            "data_source": getattr(listing, "source_platform", "CHAFICIAL_CORE"),
            "model_name": model_name,
            "model_year": model_year,
            "price": price_manwon,
            "price_krw": price_krw,
            "mileage": mileage_km,
            "availability_status": avail_status,
            "partner_review_status": partner_review,
            "listing_status": listing_status,
            "snapshot_observed_at": observed_at,
            "images": parsed_images,
            "evidences": evidences,
            "recommendation_reason": getattr(candidate, "selection_reason", "AI 추천 매물"),
            "recommendation_source": getattr(candidate, "selected_by", "AI_AGENT"),
        }
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VehicleContentCandidate:
        """딕셔너리 형태의 차량/매물 정보를 콘텐츠 후보로 변환 (Fail-closed 기본값 강제)."""
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
        price_krw = data.get("price_krw")
        if price is None and price_krw is not None and price_krw > 0:
            price = price_krw // 10000
        elif price is not None and price_krw is None:
            price_krw = price * 10000

        mileage = data.get("mileage")
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
                repub = bool(img.get("republication_allowed", False))
                internal = bool(img.get("internal_storage_allowed", False))
                auth_ref = img.get("authorization_reference", "")
                parsed_images.append(
                    MediaAsset(
                        asset_type=AssetType.IMAGE,
                        path_or_url=path,
                        label=label,
                        republication_allowed=repub,
                        internal_storage_allowed=internal,
                        authorization_reference=auth_ref,
                        slot_tag=f"@Image {idx + 2}",
                    )
                )

        # Fail-closed 기본값 강제 (누락 시 PENDING / UNKNOWN / UNCONFIRMED)
        partner_review = data.get("partner_review_status", "PENDING")
        listing_status = data.get("listing_status", "UNKNOWN")
        raw_avail = data.get("availability_status", "UNCONFIRMED")
        snapshot_observed_at = data.get("snapshot_observed_at")

        # 제원 결함 검사
        missing_attrs: list[str] = []
        if not model_name:
            missing_attrs.append("model_name")
        if model_year is None or model_year < 1980:
            missing_attrs.append("model_year")
        if price is None or price <= 0:
            missing_attrs.append("price")
        if mileage is None or mileage < 0:
            missing_attrs.append("mileage")

        # 상태 결정: 임의로 누락 정보를 승인으로 채우지 않음
        if missing_attrs:
            availability_status = "MISSING"
            precautions.append(f"필수 차량 정보 미확인: {', '.join(missing_attrs)}")
        elif partner_review != "APPROVED":
            availability_status = "PARTNER_UNAPPROVED"
            precautions.append(f"파트너 승인 미완료 ({partner_review})")
        elif listing_status != "ACTIVE":
            availability_status = "DELISTED"
            precautions.append(f"매물 상태 비활성 ({listing_status})")
        else:
            availability_status = raw_avail

        evidences = list(data.get("evidences") or [])
        if not evidences and snapshot_observed_at:
            evidences.append(
                FactEvidence(
                    source_type="ListingSnapshot",
                    document_ref=f"SNAP-OBS-{vehicle_id}",
                    verified_at=snapshot_observed_at,
                    verification_status=VerificationStatus.VERIFIED,
                    verified_by="CHAFICIAL_MARKET_INTELLIGENCE",
                    notes=f"관측 가격: {price}만원, 주행거리: {mileage}km",
                )
            )

        return VehicleContentCandidate(
            vehicle_id=vehicle_id,
            data_source=data_source,
            model_name=model_name,
            model_year=model_year,
            price=price,
            price_krw=price_krw,
            mileage=mileage,
            options=options,
            verified_pros=verified_pros,
            precautions=precautions,
            verified_at=datetime.now(UTC) if not missing_attrs else None,
            availability_status=availability_status,
            partner_review_status=partner_review,
            listing_status=listing_status,
            snapshot_observed_at=snapshot_observed_at,
            images=parsed_images,
            evidences=evidences,
            recommendation_reason=data.get("recommendation_reason", "AI 수익성 선별 매물"),
            recommendation_source=data.get("recommendation_source", "OPPORTUNITY_ENGINE"),
        )

    @classmethod
    def validate_commercial_eligibility(
        cls,
        candidate: VehicleContentCandidate,
        max_observed_days: int = 30,
        require_images: bool = True,  # 기본값 True: 사진 없는 매물 생성 차단
    ) -> None:
        """실제 판매 홍보 및 영상 제작이 가능한 매물인지 엄격하게 감사 (Fail-closed)."""
        # 1. 상태 검증
        if candidate.availability_status != "AVAILABLE":
            raise CommercialIneligibilityError(
                f"매물 상태가 판매 홍보 불가 상태입니다: '{candidate.availability_status}'. "
                f"사유: {candidate.precautions}"
            )

        if candidate.partner_review_status != "APPROVED":
            raise CommercialIneligibilityError(
                f"파트너 승인이 완료되지 않은 차량입니다: '{candidate.partner_review_status}'"
            )

        if candidate.listing_status != "ACTIVE":
            raise CommercialIneligibilityError(
                f"매물이 현재 시장에서 유효하지 않습니다: '{candidate.listing_status}'"
            )

        # 2. 필수 제원 검증
        is_valid, missing = candidate.validate_essential_info()
        if not is_valid:
            raise MissingVehicleInfoError(
                f"필수 제원이 누락된 차량은 홍보 영상을 제작할 수 없습니다: {missing}"
            )

        # 3. 가격 관측 최신성 검증 (누락 시 차단, 30일 초과 시 차단)
        if not candidate.snapshot_observed_at:
            raise CommercialIneligibilityError(
                "가격 관측 시각(snapshot_observed_at)이 누락되어 최신성을 검증할 수 없습니다."
            )

        obs = candidate.snapshot_observed_at
        if obs.tzinfo is None:
            obs = obs.replace(tzinfo=UTC)
        age_days = (datetime.now(UTC) - obs).total_seconds() / 86400.0
        if age_days > max_observed_days:
            raise CommercialIneligibilityError(
                f"가격 관측 시점({obs.date()})이 {max_observed_days}일을 초과하여 최신 가격 검증이 필요합니다. "
                f"(경과일: {age_days:.1f}일)"
            )

        # 4. 이미지 존재 및 권한 전수 감사 (실제 사진 없는 경로 전면 차단)
        if require_images and not candidate.images:
            raise MissingVehicleInfoError("판매 홍보에 사용할 실차 사진이 1장도 등록되지 않았습니다.")

        for img in candidate.images:
            if not img.republication_allowed:
                raise UnauthorizedAssetError(
                    f"에셋 '{img.label}'({img.path_or_url})의 상업적 재배포 권한(republication_allowed)이 없습니다. "
                    "단순 내부 보관 권한으로는 외부 홍보 영상을 제작할 수 없습니다."
                )

    @classmethod
    def validate_production_readiness(
        cls, candidate: VehicleContentCandidate, require_strict: bool = True
    ) -> None:
        """호환용 메서드."""
        cls.validate_commercial_eligibility(candidate, require_images=require_strict)
