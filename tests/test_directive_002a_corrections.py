"""DIRECTIVE 002-A 감사 결함 수정 및 회귀 방지 테스트 스위트."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, UTC
from chaficial.regions.manager import RegionManager
from chaficial.models import (
    Listing,
    ListingSnapshot,
    SalesCandidate,
    SalesOutcome,
    Settlement,
)
from chaficial.time_travel.query_engine import TimeTravelQueryEngine


# ==============================================================================
# 수정 A: 지역 판정 정확성 (행정구역 vs 매매단지 오분류 방지)
# ==============================================================================

def test_region_residential_address_not_misclassified_as_complex(db_session):
    """일반 주거지 주소가 특정 중고차 매매단지로 오분류되지 않아야 함."""
    reg_mgr = RegionManager()
    reg_mgr.seed_default_regions(db_session)

    # 1. 인천 서구 일반 아파트/주거지 주소
    res_incheon = reg_mgr.resolve_region_detailed("인천 서구 가정동 루원시티 아파트 101동")
    assert res_incheon.region_id != "REGION_INCHEON"  # 엠파크 매매단지로 확정되면 안 됨!
    assert res_incheon.is_market_complex is False

    # 2. 동대문구 장안동 일반 빌라/주거지 주소
    res_jangan = reg_mgr.resolve_region_detailed("서울시 동대문구 장안동 123-45 빌라 202호")
    assert res_jangan.region_id != "REGION_JANGANPYEONG"  # 장안평 매매단지로 자동 확정 금지!
    assert res_jangan.is_market_complex is False

    # 3. 실제 장안평 매매단지 내 매물
    res_real_jangan = reg_mgr.resolve_region_detailed("서울 동대문구 장안동 장안평 자동차 매매단지 C동 201호")
    assert res_real_jangan.region_id == "REGION_JANGANPYEONG"
    assert res_real_jangan.is_market_complex is True
    assert res_real_jangan.confidence == "CONFIRMED"

    # 4. 실제 수원 도이치오토월드 매물
    res_real_suwon = reg_mgr.resolve_region_detailed("경기 수원시 권선구 권선로 308-5 도이치오토월드 3층")
    assert res_real_suwon.region_id == "REGION_SUWON"
    assert res_real_suwon.is_market_complex is True


def test_region_partner_verified_origin_preservation(db_session):
    """파트너가 직접 확인한 매물은 파트너의 관할 권역으로 신뢰 상태가 보존되어야 함."""
    reg_mgr = RegionManager()
    reg_mgr.seed_default_regions(db_session)

    # 주소가 다소 간략하더라도 파트너 직영 확인 건
    res = reg_mgr.resolve_region_detailed(
        raw_location="서울 동대문구 관내 딜러보관소",
        partner_operating_region="REGION_JANGANPYEONG",
    )
    assert res.region_id == "REGION_JANGANPYEONG"
    assert res.confidence == "CONFIRMED_BY_PARTNER"


# ==============================================================================
# 수정 B: 시계열 데이터 불변성 (Append-only 강제)
# ==============================================================================

def test_snapshot_orm_update_blocked(db_session):
    """SQLAlchemy ORM을 통한 ListingSnapshot UPDATE 시도가 차단되어야 함."""
    listing = Listing(source_platform="ENCAR", source_listing_id="IMMUTABLE-1", raw_location="장안평")
    db_session.add(listing)
    db_session.flush()

    snap = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=datetime.now(UTC),
        price_krw=10_000_000,
        mileage_km=50_000,
    )
    db_session.add(snap)
    db_session.commit()

    # ORM을 통한 업데이트 시도
    snap.price_krw = 9_000_000
    with pytest.raises((IntegrityError, Exception)):
        db_session.commit()
    db_session.rollback()


def test_snapshot_raw_sql_update_and_delete_blocked(db_session):
    """Raw SQL을 통한 ListingSnapshot UPDATE 및 DELETE가 DB 트리거 레벨에서 차단되어야 함."""
    listing = Listing(source_platform="ENCAR", source_listing_id="IMMUTABLE-2", raw_location="장안평")
    db_session.add(listing)
    db_session.flush()

    snap = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=datetime.now(UTC),
        price_krw=20_000_000,
        mileage_km=30_000,
    )
    db_session.add(snap)
    db_session.commit()

    # 1. Raw SQL UPDATE 시도
    with pytest.raises(Exception):
        db_session.execute(
            text("UPDATE listing_snapshots SET price_krw = 15000000 WHERE snapshot_id = :sid"),
            {"sid": snap.snapshot_id},
        )
        db_session.commit()
    db_session.rollback()

    # 2. Raw SQL DELETE 시도
    with pytest.raises(Exception):
        db_session.execute(
            text("DELETE FROM listing_snapshots WHERE snapshot_id = :sid"),
            {"sid": snap.snapshot_id},
        )
        db_session.commit()
    db_session.rollback()

    # 불변성 검증: 원본 데이터가 변경/삭제되지 않고 그대로 유지되어야 함
    reloaded = db_session.get(ListingSnapshot, snap.snapshot_id)
    assert reloaded is not None
    assert reloaded.price_krw == 20_000_000


# ==============================================================================
# 수정 C: 과거 시점 조회의 일관성 및 지연 입력 누출 차단
# ==============================================================================

def test_time_travel_candidate_lifecycle_and_delayed_ingest_protection(db_session):
    """10/1 등록 -> 10/5 인하 -> 10/10 삭제 및 10/15 지연 입력 처리 검증."""
    reg_mgr = RegionManager()
    reg_mgr.seed_default_regions(db_session)

    t_oct01 = datetime(2026, 10, 1, 10, 0, tzinfo=UTC)
    t_oct05 = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)
    t_oct10 = datetime(2026, 10, 10, 10, 0, tzinfo=UTC)
    t_oct15 = datetime(2026, 10, 15, 10, 0, tzinfo=UTC)

    # 매물 생성 (현재 상태는 삭제 상태로 세팅해둠)
    listing = Listing(
        source_platform="ENCAR",
        source_listing_id="TIME-TRAVEL-001",
        raw_location="서울 동대문구 장안동 장안평 매매단지",
        normalized_region_id="REGION_JANGANPYEONG",
        first_observed_at=t_oct01,
        current_status="DELISTED",
    )
    db_session.add(listing)
    db_session.flush()

    # 10/1 스냅샷: 최초 등록 1,000만원
    snap_oct01 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=t_oct01,
        ingested_at=t_oct01 + timedelta(minutes=5),
        price_krw=10_000_000,
        mileage_km=30_000,
        listing_status="ACTIVE",
    )
    # 10/5 스냅샷: 가격 인하 950만원
    snap_oct05 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=t_oct05,
        ingested_at=t_oct05 + timedelta(minutes=5),
        price_krw=9_500_000,
        mileage_km=30_050,
        listing_status="PRICE_CHANGED",
    )
    # 10/10 스냅샷: 매물 삭제
    snap_oct10 = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=t_oct10,
        ingested_at=t_oct10 + timedelta(minutes=5),
        price_krw=9_500_000,
        mileage_km=30_100,
        listing_status="DELISTED",
    )
    # 10/15에 뒤늦게 입력된 과거(10/4 관측) 기록
    snap_delayed = ListingSnapshot(
        listing_id=listing.listing_id,
        observed_at=datetime(2026, 10, 4, 12, 0, tzinfo=UTC),
        ingested_at=t_oct15,  # 시스템 입력 시각이 10/15!
        price_krw=9_800_000,
        mileage_km=30_020,
        listing_status="PRICE_CHANGED",
    )
    db_session.add_all([snap_oct01, snap_oct05, snap_oct10, snap_delayed])
    db_session.commit()

    # 1. 10월 3일 조회: 최초 가격(1,000만원) 및 판매 가능 매물에 포함
    t_query_oct03 = datetime(2026, 10, 3, 0, 0, tzinfo=UTC)
    snap_at_oct03 = TimeTravelQueryEngine.get_listing_snapshot_at(db_session, listing.listing_id, t_query_oct03)
    assert snap_at_oct03 is not None
    assert snap_at_oct03.price_krw == 10_000_000
    assert snap_at_oct03.listing_status == "ACTIVE"

    candidates_oct03 = TimeTravelQueryEngine.get_sales_candidates_as_of(
        db_session, target_region_id="REGION_JANGANPYEONG", as_of_time=t_query_oct03
    )
    assert any(c["listing_id"] == listing.listing_id for c in candidates_oct03)

    # 2. 10월 7일 조회: 변경된 가격(950만원) 및 판매 가능 매물에 포함
    # 주의: 10/15에 입력된 980만원짜리 지연 스냅샷은 당시 시스템에 없었으므로 배제되어야 함!
    t_query_oct07 = datetime(2026, 10, 7, 0, 0, tzinfo=UTC)
    snap_at_oct07 = TimeTravelQueryEngine.get_listing_snapshot_at(db_session, listing.listing_id, t_query_oct07)
    assert snap_at_oct07 is not None
    assert snap_at_oct07.price_krw == 9_500_000  # 980만원이 아님!
    assert snap_at_oct07.listing_status == "PRICE_CHANGED"

    candidates_oct07 = TimeTravelQueryEngine.get_sales_candidates_as_of(
        db_session, target_region_id="REGION_JANGANPYEONG", as_of_time=t_query_oct07
    )
    assert any(c["listing_id"] == listing.listing_id for c in candidates_oct07)

    # 3. 10월 12일 조회: 매물 삭제 상태 (판매 가능 후보 목록에서 완전히 제외되어야 함!)
    t_query_oct12 = datetime(2026, 10, 12, 0, 0, tzinfo=UTC)
    snap_at_oct12 = TimeTravelQueryEngine.get_listing_snapshot_at(db_session, listing.listing_id, t_query_oct12)
    assert snap_at_oct12 is not None
    assert snap_at_oct12.listing_status == "DELISTED"

    candidates_oct12 = TimeTravelQueryEngine.get_sales_candidates_as_of(
        db_session, target_region_id="REGION_JANGANPYEONG", as_of_time=t_query_oct12
    )
    assert not any(c["listing_id"] == listing.listing_id for c in candidates_oct12)


# ==============================================================================
# 수정 D: 지역 설정값 실제 반영 (동적 확장)
# ==============================================================================

def test_region_configuration_dynamic_sales_regions(db_session):
    """RegionConfiguration의 sales_region_ids 변경 시 코드 수정 없이 조회 대상이 확장되는지 검증."""
    reg_mgr = RegionManager()
    reg_mgr.seed_default_regions(db_session)

    # 1. 장안평, 수원, 인천 매물 각각 생성
    l_jangan = Listing(source_platform="ENCAR", source_listing_id="D-JNG", raw_location="장안평 매매단지", normalized_region_id="REGION_JANGANPYEONG", current_status="ACTIVE")
    l_suwon = Listing(source_platform="ENCAR", source_listing_id="D-SWN", raw_location="도이치오토월드", normalized_region_id="REGION_SUWON", current_status="ACTIVE")
    l_incheon = Listing(source_platform="ENCAR", source_listing_id="D-INC", raw_location="인천 M파크", normalized_region_id="REGION_INCHEON", current_status="ACTIVE")
    db_session.add_all([l_jangan, l_suwon, l_incheon])
    db_session.commit()

    # 초기 기본 상태: 장안평 매물만 조회되어야 함
    default_listings = reg_mgr.get_configured_sales_listings(db_session)
    assert len(default_listings) == 1
    assert default_listings[0].listing_id == l_jangan.listing_id

    # 2. 설정을 수원 및 인천까지 확장
    reg_mgr.update_sales_regions(db_session, ["REGION_JANGANPYEONG", "REGION_SUWON", "REGION_INCHEON"])

    # 확장 후 조회: 3개 매물이 모두 조회되어야 함
    expanded_listings = reg_mgr.get_configured_sales_listings(db_session)
    expanded_ids = [l.listing_id for l in expanded_listings]
    assert len(expanded_listings) == 3
    assert l_jangan.listing_id in expanded_ids
    assert l_suwon.listing_id in expanded_ids
    assert l_incheon.listing_id in expanded_ids

    # 3. 전국 분석 범위(NATIONWIDE)는 판매 지역 설정 변경과 무관하게 독립 유지되는지 확인
    cfg = reg_mgr.get_active_configuration(db_session)
    assert cfg.analysis_region_scope == "NATIONWIDE"
