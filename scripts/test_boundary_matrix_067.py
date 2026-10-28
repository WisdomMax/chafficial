#!/usr/bin/env python3
"""DIRECTIVE 067 P0: 혼합 데이터 기반 공개 승인 경계 회귀 검증 스크립트.

임시 격리 DB에서 5대 시나리오(공개 실차, 비공개, 데모, 미검증 사진, 존재하지 않는 ID)를 구성하고
목록 노출, 상세 접근, 상담 신청, DB 레코드 생성 여부, 파라미터 변조 방어를 엄격히 검증합니다.
"""

import os
import sys
import tempfile
import uuid
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from chaficial.platform.db import Base, Vehicle, VehiclePhoto, Consultation, Branch, Dealer
from chaficial.platform.service import PlatformService

def run_boundary_matrix_test():
    print("=======================================================")
    print("  DIRECTIVE 067 P0: 혼합 데이터 공개 승인 경계 회귀 검증")
    print("=======================================================")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        test_db_path = tmp.name

    engine = create_engine(f"sqlite:///{test_db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 0. 거점 및 딜러 생성
        branch = Branch(id=str(uuid.uuid4()), name="장한평 거점", region="서울 동대문구")
        dealer = Dealer(id=str(uuid.uuid4()), name="홍길동", dealership_name="차마트 운영본부", phone="010-1234-5678", branch=branch)
        db.add_all([branch, dealer])
        db.commit()

        # 1. 5대 혼합 데이터 구성
        # 1-1. V_VALID_PROD: 모든 공개 조건 충족한 실차
        v_valid_prod = Vehicle(
            id="VEH-VALID-PROD",
            plate_number="12가3456",
            model_name="현대 그랜저 IG 2.4 프리미엄",
            manufacturer="현대",
            year=2019,
            mileage=54000,
            target_price=2150,
            status="AVAILABLE",
            ownership_type="CHAMART_OWNED",
            is_public=True,
            is_demo=False,
            dealer=dealer,
            branch=branch,
        )
        p_valid = VehiclePhoto(
            id=str(uuid.uuid4()),
            vehicle_id="VEH-VALID-PROD",
            photo_url="/uploads/valid_real.jpg",
            is_primary=True,
            category="EXTERIOR",
            verification_status="VERIFIED_REAL_ASSET",
            usage_rights_status="CONFIRMED_COMMERCIAL",
            photo_source="FIELD_INSPECTION_PHOTO",
            original_file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        )

        # 1-2. V_UNPUBLISHED: 비공개 차량 (is_public=False)
        v_unpublished = Vehicle(
            id="VEH-UNPUBLISHED",
            plate_number="34나5678",
            model_name="기아 K5 2.0 노블레스",
            manufacturer="기아",
            year=2020,
            mileage=42000,
            target_price=2300,
            status="AVAILABLE",
            ownership_type="CHAMART_OWNED",
            is_public=False,  # 비공개
            is_demo=False,
            dealer=dealer,
            branch=branch,
        )
        p_unpub = VehiclePhoto(
            id=str(uuid.uuid4()),
            vehicle_id="VEH-UNPUBLISHED",
            photo_url="/uploads/unpub.jpg",
            is_primary=True,
            verification_status="VERIFIED_REAL_ASSET",
            usage_rights_status="CONFIRMED_COMMERCIAL",
            photo_source="FIELD_INSPECTION_PHOTO",
            original_file_hash="a"*64,
        )

        # 1-3. V_DEMO: 시연용 데모 차량 (is_demo=True)
        v_demo = Vehicle(
            id="VEH-DEMO",
            plate_number="56다7890",
            model_name="제네시스 G80 3.5T 스포츠",
            manufacturer="제네시스",
            year=2023,
            mileage=15000,
            target_price=5800,
            status="AVAILABLE",
            ownership_type="CHAMART_OWNED",
            is_public=True,
            is_demo=True,  # 데모 차량
            dealer=dealer,
            branch=branch,
        )
        p_demo = VehiclePhoto(
            id=str(uuid.uuid4()),
            vehicle_id="VEH-DEMO",
            photo_url="/uploads/demo.jpg",
            is_primary=True,
            verification_status="UNVERIFIED_DEMO",
            usage_rights_status="DEMO_ONLY",
            photo_source="DEMO_GRAPHIC",
            original_file_hash="b"*64,
        )

        # 1-4. V_UNVERIFIED_PHOTO: 실차이나 사진 검증 원장 미충족 (UNVERIFIED)
        v_unverified_photo = Vehicle(
            id="VEH-UNVERIFIED-PHOTO",
            plate_number="78라1234",
            model_name="르노코리아 QM6 2.0 LPe",
            manufacturer="르노코리아",
            year=2021,
            mileage=38000,
            target_price=1850,
            status="AVAILABLE",
            ownership_type="CHAMART_OWNED",
            is_public=True,
            is_demo=False,
            dealer=dealer,
            branch=branch,
        )
        p_unver = VehiclePhoto(
            id=str(uuid.uuid4()),
            vehicle_id="VEH-UNVERIFIED-PHOTO",
            photo_url="/uploads/unverified.jpg",
            is_primary=True,
            verification_status="UNVERIFIED",  # 미검증
            usage_rights_status="PENDING",     # 미승인
            photo_source="UNKNOWN",
            original_file_hash=None,
        )

        db.add_all([v_valid_prod, p_valid, v_unpublished, p_unpub, v_demo, p_demo, v_unverified_photo, p_unver])
        db.commit()
        print("[*] 5종 혼합 데이터 구성 완료")

        # -------------------------------------------------------------
        # 2. 운영 목록 조회 검증: 오직 V_VALID_PROD 1건만 노출되어야 함!
        # -------------------------------------------------------------
        prod_list = PlatformService.get_chamart_public_vehicles(db, mode="prod")
        assert len(prod_list) == 1, f"운영 목록 건수 오류: {len(prod_list)} != 1"
        assert prod_list[0]["id"] == "VEH-VALID-PROD", f"노출된 차량 ID 오류: {prod_list[0]['id']}"
        print("[*] [PASS] 운영 목록: 오직 V_VALID_PROD(공개 실차) 1건만 정상 노출됨 확인")

        # -------------------------------------------------------------
        # 3. 상세 조회 검증 (운영 모드)
        # -------------------------------------------------------------
        detail_valid = PlatformService.get_chamart_public_vehicle_detail(db, "VEH-VALID-PROD", mode="prod")
        assert detail_valid is not None and detail_valid["id"] == "VEH-VALID-PROD", "공개 실차 상세 조회 실패"

        detail_unpub = PlatformService.get_chamart_public_vehicle_detail(db, "VEH-UNPUBLISHED", mode="prod")
        assert detail_unpub is None, "비공개 차량이 운영 상세에서 노출됨!"

        detail_demo = PlatformService.get_chamart_public_vehicle_detail(db, "VEH-DEMO", mode="prod")
        assert detail_demo is None, "데모 차량이 운영 상세에서 노출됨!"

        detail_unver = PlatformService.get_chamart_public_vehicle_detail(db, "VEH-UNVERIFIED-PHOTO", mode="prod")
        assert detail_unver is None, "사진 미검증 차량이 운영 상세에서 노출됨!"

        detail_notfound = PlatformService.get_chamart_public_vehicle_detail(db, "VEH-NOT-FOUND", mode="prod")
        assert detail_notfound is None, "미존재 차량이 운영 상세에서 노출됨!"
        print("[*] [PASS] 운영 상세: 공개 실차만 200 반환, 비공개/데모/미검증/미존재는 전부 None(404) 차단 확인")

        # -------------------------------------------------------------
        # 4. 상담 신청 및 DB 레코드 생성 여부 검증
        # -------------------------------------------------------------
        initial_cons_count = db.query(Consultation).count()

        # 4-1. 공개 실차에 대한 상담 신청: 정상 접수 및 DB 레코드 생성 확인
        req_valid = {
            "name": "홍길동",
            "phone": "010-1111-2222",
            "vehicle_id": "VEH-VALID-PROD",
            "privacy_agreed": True
        }
        res_valid = PlatformService.create_chamart_public_consultation(db, req_valid)
        assert res_valid.get("success") is True
        assert db.query(Consultation).count() == initial_cons_count + 1, "정상 상담 DB 레코드 미생성"
        print("[*] [PASS] 공개 실차 상담 신청: 정상 200 접수 및 DB 레코드 정상 1건 생성 확인")

        # 4-2. 비공개 차량에 대한 상담 신청: 거절 및 DB 미생성 확인
        req_unpub = {"name": "김철수", "phone": "010-3333-4444", "vehicle_id": "VEH-UNPUBLISHED", "privacy_agreed": True}
        try:
            PlatformService.create_chamart_public_consultation(db, req_unpub)
            assert False, "비공개 차량 상담이 통과됨!"
        except ValueError as e:
            assert "현재 판매 공개 중인 실차 매물에 대해서만" in str(e)
        assert db.query(Consultation).count() == initial_cons_count + 1, "거절된 상담으로 DB 레코드가 생성됨!"

        # 4-3. 데모 차량에 대한 상담 신청: 거절 및 DB 미생성 확인
        req_demo = {"name": "이영희", "phone": "010-5555-6666", "vehicle_id": "VEH-DEMO", "privacy_agreed": True}
        try:
            PlatformService.create_chamart_public_consultation(db, req_demo)
            assert False, "데모 차량 상담이 통과됨!"
        except ValueError as e:
            assert "현재 판매 공개 중인 실차 매물에 대해서만" in str(e)
        assert db.query(Consultation).count() == initial_cons_count + 1, "거절된 상담으로 DB 레코드가 생성됨!"

        # 4-4. 사진 미검증 차량에 대한 상담 신청: 거절 및 DB 미생성 확인
        req_unver = {"name": "박민수", "phone": "010-7777-8888", "vehicle_id": "VEH-UNVERIFIED-PHOTO", "privacy_agreed": True}
        try:
            PlatformService.create_chamart_public_consultation(db, req_unver)
            assert False, "사진 미검증 차량 상담이 통과됨!"
        except ValueError as e:
            assert "현재 판매 공개 중인 실차 매물에 대해서만" in str(e)
        assert db.query(Consultation).count() == initial_cons_count + 1, "거절된 상담으로 DB 레코드가 생성됨!"

        # 4-5. 미존재 차량에 대한 상담 신청: 거절 및 DB 미생성 확인
        req_notfound = {"name": "최동욱", "phone": "010-9999-0000", "vehicle_id": "VEH-NOT-FOUND", "privacy_agreed": True}
        try:
            PlatformService.create_chamart_public_consultation(db, req_notfound)
            assert False, "미존재 차량 상담이 통과됨!"
        except ValueError as e:
            assert "존재하지 않는 차량" in str(e)
        assert db.query(Consultation).count() == initial_cons_count + 1, "거절된 상담으로 DB 레코드가 생성됨!"

        print("[*] [PASS] 상담 신청 가드: 비공개/데모/미검증/미존재는 모두 거절되며 DB 레코드 생성 0건 확인")

        # -------------------------------------------------------------
        # 5. 파라미터 변조 테스트 (mode 생략, prod, demo, 임의값)
        # -------------------------------------------------------------
        for m in ["", "prod", "xyz", "invalid_mode"]:
            res = PlatformService.get_chamart_public_vehicles(db, mode=m)
            assert len(res) == 1 and res[0]["id"] == "VEH-VALID-PROD", f"변조 mode='{m}'에서 노출 왜곡 발생"

        print("[*] [PASS] 파라미터 변조 방어: 임의 파라미터에서도 공개 범위 확대 없음 확인")

        # -------------------------------------------------------------
        # 6. 스테이징 전용 모드(mode='demo')에서는 데모 차량도 제공됨 확인
        # -------------------------------------------------------------
        staging_list = PlatformService.get_chamart_public_vehicles(db, mode="demo")
        staging_ids = {x["id"] for x in staging_list}
        assert "VEH-VALID-PROD" in staging_ids and "VEH-DEMO" in staging_ids
        print("[*] [PASS] 스테이징 격리 모드: 데모 차량 정상 제공 확인")

        print("\n=======================================================")
        print("  DIRECTIVE 067 P0 경계 검증 매트릭스: 100% ALL PASS!")
        print("=======================================================")
        return True

    finally:
        db.close()
        if os.path.exists(test_db_path):
            os.remove(test_db_path)

if __name__ == "__main__":
    ok = run_boundary_matrix_test()
    sys.exit(0 if ok else 1)
