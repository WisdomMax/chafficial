"""가상 중고차 데이터 생성기 (합성 데이터 100건 이상 생성).

무결성 검증, 시계열 재현 및 비즈니스 로직 테스트를 위한 합성 데이터를 생성합니다.
실제 시장의 통계적 분포를 모사한 것으로 주장하지 않으며, 테스트 전용으로만 사용됩니다.
"""

import random
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from chaficial.models.catalog import VehicleCatalog
from chaficial.models.condition import VehicleCondition
from chaficial.models.listing import Listing
from chaficial.models.options import VehicleOption
from chaficial.models.partner import SalesPartner
from chaficial.models.permission import DataSourcePermission
from chaficial.models.snapshot import ListingSnapshot
from chaficial.models.vehicle import VehicleIdentity
from chaficial.regions.manager import RegionManager


class SyntheticDataGenerator:
    """100건 이상의 한국형 중고차 테스트 데이터 생성기."""

    def __init__(self, session: Session, seed: int = 42):
        self.session = session
        self.rng = random.Random(seed)
        self.region_manager = RegionManager()

    def generate_all(self, target_count: int = 120) -> list[Listing]:
        """카탈로그, 권한, 딜러 파트너, 매물 및 시계열 스냅샷을 생성합니다."""
        self.region_manager.seed_default_regions(self.session)
        self._seed_permissions()
        catalogs = self._seed_catalogs()
        partner = self._seed_partner()

        base_time = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
        listings: list[Listing] = []

        locations = [
            ("서울 동대문구 장안동 장안평 매매단지", "REGION_JANGANPYEONG"),
            ("서울 성동구 용답동 장안평 시장", "REGION_JANGANPYEONG"),
            ("경기 수원시 권선구 도이치오토월드", "REGION_SUWON"),
            ("경기 수원시 권선구 SK V1 모터스", "REGION_SUWON"),
            ("인천 서구 가좌동 인천 M파크", "REGION_INCHEON"),
            ("경기 부천시 송내대로 DY카랜드", "REGION_BUCHEON"),
            ("부산 해운대구 반여동 매매단지", "REGION_NATIONWIDE"),
            ("대전 유성구 복용동 디오토몰", "REGION_NATIONWIDE"),
            ("대구 동구 안심로 매매단지", "REGION_NATIONWIDE"),
            ("광주 서구 매월동 엠플러스", "REGION_NATIONWIDE"),
        ]

        platforms = ["ENCAR", "KB_CHACHACHA", "KARROT", "DEALER_DIRECT"]

        for i in range(target_count):
            cat = self.rng.choice(catalogs)
            loc_text, _ = self.rng.choice(locations)
            platform = self.rng.choice(platforms)

            # 차량 식별 생성 (일부 미확정 상태 유지)
            has_plate = self.rng.random() > 0.15
            plate = f"{self.rng.randint(10, 99)}가 {self.rng.randint(1000, 9999)}" if has_plate else None
            identity_status = "CONFIRMED" if has_plate else "UNCONFIRMED"
            confidence = 1.0 if has_plate else 0.4

            vehicle = VehicleIdentity(
                catalog_id=cat.catalog_id,
                plate_number=plate,
                vin=f"KMH{cat.model_name[:2]}{self.rng.randint(100000, 999999)}" if has_plate else None,
                identity_status=identity_status,
                identity_confidence=confidence,
            )
            self.session.add(vehicle)
            self.session.flush()

            # 매물 생성
            first_obs = base_time + timedelta(days=self.rng.randint(0, 30), hours=self.rng.randint(0, 23))
            resolved_region = self.region_manager.resolve_region_from_text(loc_text)

            listing = Listing(
                source_platform=platform,
                source_listing_id=f"LST-{platform}-{10000 + i}",
                vehicle_id=vehicle.vehicle_id,
                seller_reference=partner.partner_id if resolved_region == "REGION_JANGANPYEONG" else None,
                first_observed_at=first_obs,
                raw_location=loc_text,
                normalized_region_id=resolved_region,
                current_status="ACTIVE",
            )
            self.session.add(listing)
            self.session.flush()

            # 가격 및 주행거리 설정
            base_price = (cat.model_year - 2015) * 2_000_000 + self.rng.randint(5_000_000, 15_000_000)
            mileage = (2026 - cat.model_year) * self.rng.randint(10_000, 25_000) + self.rng.randint(5_000, 20_000)

            # 스냅샷 1: 최초 등록
            snap1 = ListingSnapshot(
                listing_id=listing.listing_id,
                observed_at=first_obs,
                ingested_at=first_obs + timedelta(minutes=5),
                price_krw=base_price,
                mileage_km=mileage,
                listing_status="ACTIVE",
                normalized_region_id=resolved_region,
                raw_specs={"color": "화이트", "sunroof": self.rng.choice([True, False])},
            )
            self.session.add(snap1)

            # 일부 매물은 가격 인하 스냅샷 추가 (시계열 변화)
            if self.rng.random() > 0.5:
                reduced_price = base_price - self.rng.randint(300_000, 1_500_000)
                second_obs = first_obs + timedelta(days=self.rng.randint(3, 10))
                snap2 = ListingSnapshot(
                    listing_id=listing.listing_id,
                    observed_at=second_obs,
                    ingested_at=second_obs + timedelta(minutes=5),
                    price_krw=reduced_price,
                    mileage_km=mileage + self.rng.randint(10, 50),
                    listing_status="PRICE_CHANGED",
                    normalized_region_id=resolved_region,
                )
                self.session.add(snap2)
                listing.current_status = "PRICE_CHANGED"

            # 일부 매물은 단순 매물 삭제 (DELISTED) 처리
            if self.rng.random() > 0.8:
                delist_obs = first_obs + timedelta(days=self.rng.randint(12, 20))
                snap_delist = ListingSnapshot(
                    listing_id=listing.listing_id,
                    observed_at=delist_obs,
                    ingested_at=delist_obs + timedelta(minutes=5),
                    price_krw=base_price,
                    mileage_km=mileage,
                    listing_status="DELISTED",
                    normalized_region_id=resolved_region,
                )
                self.session.add(snap_delist)
                listing.current_status = "DELISTED"

            # 차량 상태 및 성능점검 (외판 단순수리와 주요 골격 손상 분리)
            has_accident = self.rng.random() > 0.6
            is_major = has_accident and (self.rng.random() > 0.7)
            accident_class = (
                "MAJOR_ACCIDENT" if is_major else ("SIMPLE_REPAIR" if has_accident else "NO_ACCIDENT")
            )

            outer_repairs = {"fender_replaced": True, "door_painted": True} if has_accident else {}
            structural_damages = {"pillar_repaired": True, "wheelhouse_welded": True} if is_major else {}

            condition = VehicleCondition(
                listing_id=listing.listing_id,
                vehicle_id=vehicle.vehicle_id,
                inspection_status="CONFIRMED" if self.rng.random() > 0.1 else "UNCONFIRMED",
                accident_classification=accident_class,
                outer_panel_repairs=outer_repairs,
                structural_damages=structural_damages,
                insurance_record_verified=self.rng.random() > 0.2,
                my_damage_amount_krw=self.rng.randint(0, 3_000_000) if has_accident else 0,
                other_damage_amount_krw=self.rng.randint(0, 2_000_000) if has_accident else 0,
                is_total_loss=False,
                is_flood=False,
                is_theft=False,
                owner_change_count=self.rng.randint(0, 3),
                usage_change=self.rng.random() > 0.85,
                engine_condition="CONFIRMED_GOOD" if self.rng.random() > 0.2 else "UNCONFIRMED",
                transmission_condition="CONFIRMED_GOOD" if self.rng.random() > 0.2 else "UNCONFIRMED",
                oil_leak_status="NO_LEAK" if self.rng.random() > 0.3 else "UNCONFIRMED",
                observed_at=first_obs,
                ingested_at=first_obs + timedelta(minutes=10),
            )
            self.session.add(condition)

            # 옵션 정보 등록 (PRESENT / ABSENT / UNKNOWN 분리)
            option_codes = ["SUNROOF", "NAVIGATION", "VENTILATED_SEAT", "HUD", "SMART_CRUISE"]
            for code in option_codes:
                rand_val = self.rng.random()
                status = "PRESENT" if rand_val > 0.5 else ("ABSENT" if rand_val > 0.2 else "UNKNOWN")
                opt = VehicleOption(
                    listing_id=listing.listing_id,
                    vehicle_id=vehicle.vehicle_id,
                    option_code=code,
                    option_status=status,
                    verification_source="PLATFORM_TAG",
                    observed_at=first_obs,
                )
                self.session.add(opt)

            listings.append(listing)

        self.session.commit()
        return listings

    def _seed_catalogs(self) -> list[VehicleCatalog]:
        catalogs_data = [
            # 아반떼 세대 구분 (AD vs CN7)
            VehicleCatalog(manufacturer="현대", model_name="아반떼", generation="AD", is_facelift=False, trim="스마트", model_year=2017, fuel_type="가솔린"),
            VehicleCatalog(manufacturer="현대", model_name="아반떼", generation="AD", is_facelift=True, sub_model="더 뉴 아반떼 AD", trim="모던", model_year=2019, fuel_type="가솔린"),
            VehicleCatalog(manufacturer="현대", model_name="아반떼", generation="CN7", is_facelift=False, sub_model="올 뉴 아반떼 CN7", trim="인스퍼레이션", model_year=2021, fuel_type="가솔린"),
            VehicleCatalog(manufacturer="현대", model_name="아반떼", generation="CN7", is_facelift=True, sub_model="더 뉴 아반떼 CN7", trim="인스퍼레이션", model_year=2023, fuel_type="하이브리드"),
            # 쏘나타 & 그랜저
            VehicleCatalog(manufacturer="현대", model_name="쏘나타", generation="DN8", is_facelift=False, trim="프리미엄", model_year=2020, fuel_type="가솔린"),
            VehicleCatalog(manufacturer="현대", model_name="그랜저", generation="IG", is_facelift=True, sub_model="더 뉴 그랜저 IG", trim="익스클루시브", model_year=2021, fuel_type="하이브리드"),
            VehicleCatalog(manufacturer="현대", model_name="그랜저", generation="GN7", is_facelift=False, sub_model="디 올 뉴 그랜저", trim="캘리그래피", model_year=2023, fuel_type="가솔린"),
            # 기아 K3, K5, 쏘렌토, 스포티지
            VehicleCatalog(manufacturer="기아", model_name="K3", generation="BD", is_facelift=False, trim="트렌디", model_year=2019, fuel_type="가솔린"),
            VehicleCatalog(manufacturer="기아", model_name="K5", generation="DL3", is_facelift=False, trim="노블레스", model_year=2021, fuel_type="가솔린"),
            VehicleCatalog(manufacturer="기아", model_name="스포티지", generation="NQ5", is_facelift=False, trim="시그니처", model_year=2022, fuel_type="디젤"),
            VehicleCatalog(manufacturer="기아", model_name="쏘렌토", generation="MQ4", is_facelift=False, trim="노블레스", model_year=2021, fuel_type="하이브리드"),
            # 수입차 예시
            VehicleCatalog(manufacturer="BMW", model_name="5시리즈", generation="G30", is_facelift=True, trim="520i M 스포츠", model_year=2021, fuel_type="가솔린"),
            VehicleCatalog(manufacturer="벤츠", model_name="E클래스", generation="W213", is_facelift=True, trim="E250 아방가르드", model_year=2022, fuel_type="가솔린"),
        ]
        self.session.add_all(catalogs_data)
        self.session.flush()
        return catalogs_data

    def _seed_permissions(self) -> None:
        perms = [
            DataSourcePermission(
                source_id="ENCAR",
                source_name="엔카닷컴",
                permission_status="RESTRICTED",
                collection_allowed=False,
                storage_allowed=False,
                model_training_allowed=False,
                republication_allowed=False,
                authorization_reference="약관 준수 및 무단 크롤링 금지",
            ),
            DataSourcePermission(
                source_id="MOLIT_PUBLIC",
                source_name="국토교통부 공공데이터포털",
                permission_status="AUTHORIZED",
                collection_allowed=True,
                storage_allowed=True,
                model_training_allowed=True,
                republication_allowed=False,
                authorization_reference="공공데이터포털 이용허락조건",
            ),
            DataSourcePermission(
                source_id="JANGANPYEONG_PARTNER_DIRECT",
                source_name="장안평 파트너 딜러 직접 위탁 매물",
                permission_status="AUTHORIZED",
                collection_allowed=True,
                storage_allowed=True,
                model_training_allowed=True,
                republication_allowed=True,
                authorization_reference="딜러 파트너십 서면 광고위탁 동의서",
            ),
        ]
        self.session.add_all(perms)
        self.session.flush()

    def _seed_partner(self) -> SalesPartner:
        partner = SalesPartner(
            partner_name="장안평 25년 경력 베테랑 실무 파트너",
            operating_region_id="REGION_JANGANPYEONG",
            partner_status="ACTIVE",
            experience_years=25,
            contact_masked="010-****-1234",
        )
        self.session.add(partner)
        self.session.flush()
        return partner
