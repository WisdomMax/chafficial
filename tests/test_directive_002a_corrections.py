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
