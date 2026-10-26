"""차마트(CHAMART) 실매물 소싱 서비스 및 매물 스냅샷/가격 추적 엔진 (DIRECTIVE 049).

- 엔카 서울 실매물 DB 저장 및 중복 방지
- 시장 관측 매물(MARKET_OBSERVED) 엄격 분리
- 장한평/서울 자동 분류 및 판정 사유 기록
- 매물 스냅샷 및 시계열 가격 변동 추적 (최초가, 인하액, 히스토리)
- 소싱 관리 화면용 통계 및 필터링 제공
"""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from chaficial.platform.db import Branch, Vehicle, VehicleListing
from chaficial.platform.sourcing.classifier import JanganpyeongClassifier
from chaficial.platform.sourcing.encar import EncarSourceAdapter

logger = logging.getLogger("chaficial.sourcing.service")


class SourcingService:
    """엔카 및 외부 매물 소싱 통합 관리 서비스."""

    @classmethod
    def sync_encar_seoul(
        cls,
        db: Session,
        limit: int = 20,
        page: int = 1,
        fetch_detail: bool = True,
    ) -> Dict[str, Any]:
        """엔카 서울 매물 수집 실행 및 DB 동기화/가격 변동 추적."""
        adapter = EncarSourceAdapter(timeout_sec=8, delay_sec=0.15)
        raw_listings = adapter.fetch_listings(region="서울", page=page, limit=limit, fetch_detail=fetch_detail)

        # 본사 지점(장한평) 확보
        jh_branch = db.query(Branch).filter(Branch.name.contains("장한평")).first()
        if not jh_branch:
            jh_branch = db.query(Branch).first()
        branch_id = jh_branch.id if jh_branch else "default_branch"

        now = datetime.datetime.utcnow()
        new_count = 0
        updated_count = 0
        price_drop_count = 0
        confirmed_jp_count = 0
        candidate_jp_count = 0

        synced_items = []

        for raw in raw_listings:
            # 1. 장한평/서울 소재지 분류
            loc_cat, reason = JanganpyeongClassifier.classify(
                raw_region=raw.raw_region,
                seller_location=raw.raw_seller_location,
                dealership_name=raw.raw_seller_name,
            )
            is_jp = loc_cat in ["JANGANPYEONG_CONFIRMED", "JANGANPYEONG_CANDIDATE"]

            if loc_cat == "JANGANPYEONG_CONFIRMED":
                confirmed_jp_count += 1
            elif loc_cat == "JANGANPYEONG_CANDIDATE":
                candidate_jp_count += 1

            # 2. 기존 매물 확인 (중복 제거 및 가격 추적)
            existing_listing = (
                db.query(VehicleListing)
                .filter(
                    VehicleListing.platform == "ENCAR",
                    VehicleListing.listing_id == raw.source_listing_id,
                )
                .first()
            )

            if not existing_listing:
                # ----------------------------------------------------------------
                # A. 신규 매물 등록
                # ----------------------------------------------------------------
                new_count += 1

                # 1) 시장 관측 매물(MARKET_OBSERVED)로 마스터 차량 생성
                plate_no = raw.plate_number or f"관측-{raw.source_listing_id[-6:]}"
                model_full = f"{raw.manufacturer} {raw.model} {raw.trim or ''}".strip()

                vehicle = Vehicle(
                    branch_id=branch_id,
                    plate_number=plate_no,
                    model_name=model_full,
                    year=raw.model_year,
                    mileage=raw.mileage_km,
                    fuel_type=raw.fuel_type,
                    transmission=raw.transmission,
                    color="미상",
                    purchase_price=0,
                    target_price=raw.price_krw,
                    status="FOR_SALE",
                    ownership_type="MARKET_OBSERVED",  # 시장 관측 매물 (자체 재고 아님!)
                    dealer_id=None,
                    vin=None,
                    displacement_cc=None,
                    first_registration_date=None,
                    drive_type="2WD",
                    interior_color="미상",
                    options_json="[]",
                    accident_history_json=json.dumps({
                        "accident_state": "UNCHECKED",
                        "frame_damage": "미확인 (엔카 매물 미검증)",
                        "outer_panel_exchange": "미확인 (엔카 매물 미검증)",
                        "verified_source": "엔카 온라인 매물 (성능점검 증빙 대기)",
                        "verified_at": None,
                    }, ensure_ascii=False),
                    inspection_summary_json="{}",
                    marketing_auth_json=json.dumps({
                        "authorized": False,
                        "video_allowed": False,
                        "photo_allowed": False,
                        "notes": "엔카 단순 관측 매물 - 권한 승인 대기",
                    }, ensure_ascii=False),
                    primary_photo_url=raw.primary_photo_url,
                    video_status="NONE",
                    is_demo=False,  # 실제 엔카 소싱 매물!
                )
                db.add(vehicle)
                db.flush()

                # 2) Listing 레코드 생성
                initial_history = [{
                    "observed_at": now.isoformat(),
                    "price": raw.price_krw,
                    "event": "INITIAL_OBSERVATION",
                }]

                listing = VehicleListing(
                    vehicle_id=vehicle.id,
                    platform="ENCAR",
                    listing_id=raw.source_listing_id,
                    listing_url=raw.source_url,
                    advertised_price=raw.price_krw,
                    initial_price=raw.price_krw,
                    price_drop_amount=0,
                    price_history_json=json.dumps(initial_history, ensure_ascii=False),
                    listing_status="ACTIVE",
                    first_observed_at=now,
                    last_observed_at=now,
                    region=raw.raw_region,
                    location_category=loc_cat,
                    identification_reason=reason,
                    raw_seller_location=raw.raw_seller_location,
                    raw_seller_name=raw.raw_seller_name,
                    is_janghanpyeong=is_jp,
                    data_confidence=raw.source_confidence,
                    market_avg_price=raw.price_krw,
                    opportunity_score=round(75.0 if is_jp else 65.0, 1),
                    observation_notes=f"엔카 서울 실매물 최초 수집 ({now.strftime('%Y-%m-%d %H:%M')})",
                    is_demo=False,
                )
                db.add(listing)

                synced_items.append({
                    "action": "NEW",
                    "listing_id": raw.source_listing_id,
                    "model_name": model_full,
                    "price": raw.price_krw,
                    "location_category": loc_cat,
                    "url": raw.source_url,
                })
            else:
                # ----------------------------------------------------------------
                # B. 기존 매물 업데이트 및 가격 변동 추적
                # ----------------------------------------------------------------
                updated_count += 1
                old_price = existing_listing.advertised_price
                new_price = raw.price_krw
                price_diff = new_price - old_price

                # 가격 변동 이력 갱신
                history = json.loads(existing_listing.price_history_json or "[]")

                if price_diff != 0:
                    event_type = "PRICE_DROP" if price_diff < 0 else "PRICE_INCREASE"
                    history.append({
                        "observed_at": now.isoformat(),
                        "price": new_price,
                        "change": price_diff,
                        "event": event_type,
                    })
                    existing_listing.price_history_json = json.dumps(history, ensure_ascii=False)
                    existing_listing.advertised_price = new_price

                    if price_diff < 0:
                        price_drop_count += 1
                        existing_listing.price_drop_amount = max(
                            0, (existing_listing.initial_price or old_price) - new_price
                        )
                        # 가성비 기회점수 상승 반영
                        existing_listing.opportunity_score = min(
                            98.0, (existing_listing.opportunity_score or 70.0) + 10.0
                        )

                # 메타데이터 및 관측 시점 갱신
                existing_listing.last_observed_at = now
                existing_listing.listing_status = "ACTIVE"
                existing_listing.location_category = loc_cat
                existing_listing.identification_reason = reason
                if raw.raw_seller_location:
                    existing_listing.raw_seller_location = raw.raw_seller_location
                if raw.raw_seller_name:
                    existing_listing.raw_seller_name = raw.raw_seller_name

                # 마스터 차량 가격도 동기화
                if existing_listing.vehicle:
                    existing_listing.vehicle.target_price = new_price

                synced_items.append({
                    "action": "UPDATED",
                    "listing_id": raw.source_listing_id,
                    "model_name": existing_listing.vehicle.model_name if existing_listing.vehicle else "미상",
                    "price": new_price,
                    "price_diff": price_diff,
                    "location_category": loc_cat,
                    "url": raw.source_url,
                })

        db.commit()

        return {
            "status": "SUCCESS",
            "source": "ENCAR",
            "region": "서울",
            "page": page,
            "total_fetched": len(raw_listings),
            "new_registered_count": new_count,
            "updated_count": updated_count,
            "price_drop_count": price_drop_count,
            "janganpyeong_confirmed_count": confirmed_jp_count,
            "janganpyeong_candidate_count": candidate_jp_count,
            "synced_at": now.isoformat(),
            "items": synced_items,
        }

    @classmethod
    def get_sourcing_summary(cls, db: Session) -> Dict[str, Any]:
        """소싱 관리 화면 상단 5대 KPI 통계 요약 (DIRECTIVE 049)."""
        all_encar_listings = (
            db.query(VehicleListing)
            .filter(VehicleListing.platform == "ENCAR", VehicleListing.is_demo == False)
            .all()
        )
        total_count = len(all_encar_listings)

        jp_confirmed = sum(1 for l in all_encar_listings if l.location_category == "JANGANPYEONG_CONFIRMED")
        jp_candidate = sum(1 for l in all_encar_listings if l.location_category == "JANGANPYEONG_CANDIDATE")
        seoul_other = sum(1 for l in all_encar_listings if l.location_category == "SEOUL_OTHER")
        seoul_unspecified = sum(1 for l in all_encar_listings if l.location_category == "SEOUL_UNSPECIFIED")

        # 최근 24시간 내 신규 등록 매물
        now = datetime.datetime.utcnow()
        one_day_ago = now - datetime.timedelta(days=1)
        new_today = sum(1 for l in all_encar_listings if l.first_observed_at and l.first_observed_at >= one_day_ago)

        # 가격 인하 매물
        price_drops = sum(1 for l in all_encar_listings if (l.price_drop_amount or 0) > 0)

        # 최근 동기화 시각
        last_seen = None
        if all_encar_listings:
            latest = max(all_encar_listings, key=lambda l: l.last_observed_at or l.first_observed_at)
            last_seen = (latest.last_observed_at or latest.first_observed_at).isoformat()

        return {
            "total_encar_seoul_count": total_count,
            "janganpyeong_confirmed_count": jp_confirmed,
            "janganpyeong_candidate_count": jp_candidate,
            "seoul_other_count": seoul_other,
            "seoul_unspecified_count": seoul_unspecified,
            "new_registered_today_count": new_today,
            "price_dropped_count": price_drops,
            "last_sourcing_at": last_seen,
            "platform_status": "ONLINE_ACTIVE",
            "source_authority": "공식 모바일 공개 검색 채널 (비인가 스크래핑 없음)",
        }

    @classmethod
    def list_sourcing_listings(
        cls,
        db: Session,
        location_filter: Optional[str] = None,
        price_drop_only: bool = False,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """소싱 매물 목록 조회 및 필터링."""
        query = (
            db.query(VehicleListing)
            .filter(VehicleListing.platform == "ENCAR", VehicleListing.is_demo == False)
        )

        if location_filter:
            if location_filter == "JANGANPYEONG_ALL":
                query = query.filter(
                    VehicleListing.location_category.in_(["JANGANPYEONG_CONFIRMED", "JANGANPYEONG_CANDIDATE"])
                )
            else:
                query = query.filter(VehicleListing.location_category == location_filter)

        if price_drop_only:
            query = query.filter(VehicleListing.price_drop_amount > 0)

        query = query.order_by(desc(VehicleListing.last_observed_at))
        listings = query.offset(offset).limit(limit).all()

        results = []
        for l in listings:
            v = l.vehicle
            if search and v:
                kw = search.lower()
                target_str = f"{v.model_name} {v.plate_number} {l.raw_seller_name or ''}".lower()
                if kw not in target_str:
                    continue

            results.append({
                "listing_id": l.listing_id,
                "platform": l.platform,
                "source_url": l.listing_url,
                "vehicle_id": l.vehicle_id,
                "model_name": v.model_name if v else "미상",
                "plate_number": v.plate_number if v else "미상",
                "year": v.year if v else 0,
                "mileage": v.mileage if v else 0,
                "advertised_price": l.advertised_price,
                "initial_price": l.initial_price,
                "price_drop_amount": l.price_drop_amount or 0,
                "location_category": l.location_category,
                "identification_reason": l.identification_reason,
                "raw_seller_location": l.raw_seller_location,
                "raw_seller_name": l.raw_seller_name,
                "opportunity_score": l.opportunity_score,
                "primary_photo_url": v.primary_photo_url if v else None,
                "first_observed_at": l.first_observed_at.strftime("%Y-%m-%d %H:%M") if l.first_observed_at else None,
                "last_observed_at": l.last_observed_at.strftime("%Y-%m-%d %H:%M") if l.last_observed_at else None,
            })

        return results
