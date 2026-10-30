import sqlite3
from sqlalchemy.orm import Session
from chaficial.platform.db import SessionLocal, Vehicle, VehiclePhoto
from chaficial.platform.service import PlatformService

def test_photo_access_control():
    db: Session = SessionLocal()
    
    # 1. 비공개 사진(PRIVATE)이 연결된 외부 차량 1대 조회
    external_vehicle = db.query(Vehicle).join(VehiclePhoto).filter(
        VehiclePhoto.public_visibility == "PRIVATE"
    ).first()
    
    assert external_vehicle is not None, "비공개 사진이 있는 외부 차량이 존재해야 함"
    
    # DB 원장 상의 전체 사진 수 확인
    total_raw_photos = db.query(VehiclePhoto).filter(VehiclePhoto.vehicle_id == external_vehicle.id).count()
    private_raw_photos = db.query(VehiclePhoto).filter(
        VehiclePhoto.vehicle_id == external_vehicle.id,
        VehiclePhoto.public_visibility == "PRIVATE"
    ).count()
    
    print(f"[*] Testing External Vehicle ID: {external_vehicle.id}")
    print(f"    - Raw Total Photos in DB: {total_raw_photos}")
    print(f"    - Raw PRIVATE Photos in DB: {private_raw_photos}")
    
    # 2. 공개 서비스 레이어(get_vehicle_detail) 호출 결과 검증
    detail = PlatformService.get_vehicle_detail(db, external_vehicle.id)
    served_photos = detail["photos"]
    
    print(f"    - Photos Served by Public API: {len(served_photos)}")
    
    # 검증: 공개 API를 통해 서빙된 사진 목록에 비공개 사진이 단 1장도 포함되지 않아야 함!
    for p in served_photos:
        assert p.get("public_visibility") != "PRIVATE", "PRIVATE 사진이 공개 서빙되어서는 안 됨"
    
    assert len(served_photos) == (total_raw_photos - private_raw_photos), "서빙된 사진 수는 오직 공개/승인된 사진만이어야 함"
    print("[+] ACCESS CONTROL VERIFIED: 100% of PRIVATE photos were BLOCKED from public API.")
    
    # 3. 공개 승인된 자사 차량의 사진은 정상 서빙되는지 확인
    internal_vehicle = db.query(Vehicle).join(VehiclePhoto).filter(
        VehiclePhoto.public_visibility == "PUBLIC",
        VehiclePhoto.approval_status == "APPROVED"
    ).first()
    
    if internal_vehicle:
        int_detail = PlatformService.get_vehicle_detail(db, internal_vehicle.id)
        int_served_photos = int_detail["photos"]
        print(f"[+] Internal Vehicle (PUBLIC photos): {len(int_served_photos)} photos correctly served.")
        assert len(int_served_photos) > 0, "공개 승인 사진은 정상 서빙되어야 함"

    db.close()
    print("\n================================================================================")
    print("[+] TASK 1-③ Photo Access Control Enforcement: 100% PASS")
    print("================================================================================")

if __name__ == "__main__":
    test_photo_access_control()
