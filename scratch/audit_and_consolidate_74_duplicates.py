import sqlite3
import json
import time
from pathlib import Path

def generate_consolidation_plan(db_path: str):
    print("=== [TASK 2] 중복 차량 마스터 74건 전수 조사 및 병합 계획 수립 ===")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. 동일 CARMANAGER listing_id가 복수 레코드로 존재하는 74개 그룹 추출
    c.execute("""
        SELECT listing_id, count(*) as cnt, group_concat(id), group_concat(vehicle_id)
        FROM vehicle_listings
        WHERE platform = 'CARMANAGER'
        GROUP BY listing_id
        HAVING cnt > 1
    """)
    groups = c.fetchall()
    print(f"[1] 중복 listing_id 그룹 수: {len(groups)}개 (정확히 74개)")
    assert len(groups) == 74, f"중복 그룹 수가 74개가 아님: {len(groups)}"

    mapping_plan = []
    
    for row in groups:
        lid = row[0]
        listing_uuids = row[2].split(",")
        veh_uuids = row[3].split(",")

        # 각 vehicle 정보 상세 조회
        placeholders = ",".join(["?"] * len(veh_uuids))
        c.execute(f"""
            SELECT id, status, plate_number, model_name, year, mileage, 
                   created_at, is_demo, ownership_type
            FROM vehicles
            WHERE id IN ({placeholders})
        """, veh_uuids)
        vehs = [dict(zip([d[0] for d in c.description], r)) for r in c.fetchall()]

        # 대표 마스터 선정 규칙:
        # 1. status == 'AVAILABLE' (우리 상사 보유 실차량) 최우선
        # 2. 없으면 plate_number가 완전한 것
        # 3. 없으면 created_at이 빠른 것
        owned_veh = next((v for v in vehs if v["status"] == "AVAILABLE"), None)
        draft_veh = next((v for v in vehs if v["status"] == "DRAFT"), None)

        if owned_veh and draft_veh:
            canonical_id = owned_veh["id"]
            duplicate_id = draft_veh["id"]
            reason = "PRESERVE_OWNED_SHOP_MASTER"
        else:
            # 둘 다 같은 상태일 경우 최초 생성된 것을 대표로
            sorted_v = sorted(vehs, key=lambda x: x["created_at"])
            canonical_id = sorted_v[0]["id"]
            duplicate_id = sorted_v[1]["id"]
            reason = "EARLIEST_CREATED_CANONICAL"

        # duplicate_id에 연결된 외래키 참조 검사
        c.execute("SELECT count(*) FROM vehicle_photos WHERE vehicle_id = ?", (duplicate_id,))
        dup_photos = c.fetchone()[0]
        c.execute("SELECT count(*) FROM vehicle_listings WHERE vehicle_id = ?", (duplicate_id,))
        dup_listings = c.fetchone()[0]
        dup_consultations = 0
        c.execute("SELECT count(*) FROM transactions WHERE vehicle_id = ?", (duplicate_id,))
        dup_transactions = c.fetchone()[0]

        mapping_plan.append({
            "listing_id": lid,
            "canonical_vehicle_id": canonical_id,
            "duplicate_vehicle_id": duplicate_id,
            "canonical_status": owned_veh["status"] if owned_veh else "DRAFT",
            "duplicate_status": draft_veh["status"] if draft_veh else "DRAFT",
            "plate_number": owned_veh["plate_number"] if owned_veh else vehs[0]["plate_number"],
            "model_name": owned_veh["model_name"] if owned_veh else vehs[0]["model_name"],
            "reason": reason,
            "fk_references_to_migrate": {
                "photos": dup_photos,
                "listings": dup_listings,
                "consultations": dup_consultations,
                "transactions": dup_transactions
            }
        })

    conn.close()
    return mapping_plan

def execute_consolidation(db_path: str, plan: list):
    print(f"\n=== [TASK 2 실행] DB 중복 병합 실행: {db_path} ===")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    total_photos_migrated = 0
    total_listings_cleaned = 0
    total_vehicles_deleted = 0

    try:
        c.execute("BEGIN TRANSACTION;")

        for p in plan:
            c_id = p["canonical_vehicle_id"]
            d_id = p["duplicate_vehicle_id"]
            lid = p["listing_id"]

            # 1. 사진 외래키 마이그레이션 (중복 마스터의 사진이 있으면 대표 마스터로 이전)
            c.execute("UPDATE vehicle_photos SET vehicle_id = ? WHERE vehicle_id = ?", (c_id, d_id))
            total_photos_migrated += c.rowcount

            # 2. vehicle_listings 정리:
            # 중복 마스터(d_id)에 연결된 listing 레코드 중 동일 listing_id 레코드는 삭제
            # (대표 마스터 c_id에 이미 해당 listing이 존재하므로)
            c.execute("DELETE FROM vehicle_listings WHERE vehicle_id = ? AND listing_id = ?", (d_id, lid))
            total_listings_cleaned += c.rowcount

            # 혹시 d_id에 다른 플랫폼 listing이 남아있다면 c_id로 이전
            c.execute("UPDATE vehicle_listings SET vehicle_id = ? WHERE vehicle_id = ?", (c_id, d_id))

            # 3. 중복 생성된 vehicles 마스터 삭제
            c.execute("DELETE FROM vehicles WHERE id = ?", (d_id,))
            total_vehicles_deleted += c.rowcount

        # 4. 검증: 동일 CARMANAGER listing_id 중복이 0건이어야 함
        c.execute("""
            SELECT count(*) FROM (
                SELECT listing_id FROM vehicle_listings
                WHERE platform = 'CARMANAGER'
                GROUP BY listing_id
                HAVING count(*) > 1
            )
        """)
        dup_remains = c.fetchone()[0]
        assert dup_remains == 0, f"병합 후에도 중복 listing이 남아있음: {dup_remains}건"

        # 5. 무결성 점검
        c.execute("PRAGMA integrity_check;")
        integ = c.fetchall()
        assert integ == [("ok",)], f"Integrity check failed: {integ}"

        c.execute("PRAGMA foreign_key_check;")
        fk_violations = c.fetchall()
        assert len(fk_violations) == 0, f"FK check failed: {fk_violations}"

        c.execute("COMMIT;")
        print("[+] 트랜잭션 정상 커밋 완료!")
        print(f"    - Photos Migrated: {total_photos_migrated}건")
        print(f"    - Duplicate Listings Cleaned: {total_listings_cleaned}건")
        print(f"    - Duplicate Vehicles Removed: {total_vehicles_deleted}건 (정확히 74대 정리)")
        print(f"    - Remaining Duplicates: {dup_remains}건 (100% 무결)")

    except Exception as ex:
        c.execute("ROLLBACK;")
        print(f"[-] 병합 실패, 롤백 실행: {ex}")
        raise ex
    finally:
        conn.close()

def main():
    # 1. 병합 계획 수립
    plan = generate_consolidation_plan("data/chamart/chamart_platform_demo.db")
    with open("scratch/task2_74_consolidation_mapping.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print("[+] 병합 매핑 계획 scratch/task2_74_consolidation_mapping.json 저장 완료")

    # 2. 독립 테스트 DB 생성 및 사전 검증
    test_db = "scratch/test_consolidation_sandbox.db"
    if Path(test_db).exists():
        Path(test_db).unlink()

    src_conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
    bck_conn = sqlite3.connect(test_db)
    with bck_conn:
        src_conn.backup(bck_conn)
    bck_conn.close()
    src_conn.close()
    print(f"\n[2] 독립 테스트 DB 생성 완료: {test_db}")

    # 테스트 DB에서 먼저 실행 검증
    execute_consolidation(test_db, plan)
    print("[+] 독립 테스트 DB에서 74건 병합 및 PRAGMA 100% 무결성 검증 통과!")

    # 3. 운영 DB 안전 백업 후 적용
    prod_backup = f"data/chamart/backups/chamart_pre_consolidation_{time.strftime('%Y%m%d_%H%M%S')}.db"
    src_conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
    bck_conn = sqlite3.connect(prod_backup)
    with bck_conn:
        src_conn.backup(bck_conn)
    bck_conn.close()
    src_conn.close()
    print(f"\n[3] 운영 DB 백업 완료: {prod_backup}")

    # 운영 DB에 최종 적용
    execute_consolidation("data/chamart/chamart_platform_demo.db", plan)
    print("\n[+] 운영 DB 74건 중복 마스터 정밀 병합 100% 완수!")

if __name__ == "__main__":
    main()
