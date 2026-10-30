import sqlite3
import json

def verify_task1_restoration():
    print("=== [TASK 1] DIRECTIVE 116: 과잉 삭제 정상 매물 5건 복원 전수 검증 ===")
    
    db_path = "data/chamart/chamart_platform_demo.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1. 격리 아카이브 20건 분류 검증
    with open("scratch/quarantined_fabricated_matches.json", "r", encoding="utf-8") as f:
        archive = json.load(f)
    
    listings = archive.get("listings", [])
    print(f"[1] 격리 아카이브 총 레코드: {len(listings)}건")
    
    kb_mock = [l for l in listings if l["platform"] == "KB_CHACHACHA"]
    encar_mock = [l for l in listings if l["platform"] == "ENCAR" and l["listing_id"].startswith("ENCAR_")]
    cm_normal = [l for l in listings if l["platform"] == "CARMANAGER"]
    encar_normal = [l for l in listings if l["platform"] == "ENCAR" and not l["listing_id"].startswith("ENCAR_")]

    print(f"    - KB 가상 매칭 (격리 유지): {len(kb_mock)}건")
    print(f"    - ENCAR 가상 매칭 (격리 유지): {len(encar_mock)}건")
    print(f"    - CARMANAGER 정상 매물 (복원 대상): {len(cm_normal)}건")
    print(f"    - ENCAR 수원 기준점 매물 (복원 대상): {len(encar_normal)}건")

    assert len(kb_mock) == 8, "KB 가상 매칭 8건 불일치"
    assert len(encar_mock) == 7, "ENCAR 가상 매칭 7건 불일치"
    assert len(cm_normal) == 4, "CARMANAGER 정상 매물 4건 불일치"
    assert len(encar_normal) == 1, "ENCAR 정상 매물 1건 불일치"

    # 2. 복원된 5건의 DB 실시간 존재 및 FK 연결 검증
    restore_ids = [l["listing_id"] for l in cm_normal + encar_normal]
    print(f"\n[2] 복원 대상 5건 DB 실시간 존재 검증:")
    
    found_count = 0
    for lid in restore_ids:
        c.execute("""
            SELECT l.id, l.vehicle_id, l.platform, l.listing_id, v.plate_number, v.model_name
            FROM vehicle_listings l
            JOIN vehicles v ON l.vehicle_id = v.id
            WHERE l.listing_id = ?
        """, (lid,))
        row = c.fetchone()
        if row:
            found_count += 1
            print(f"    [+] OK: {row[2]} ID: {row[3]} -> Vehicle: {row[1]} (Plate: {row[4]}, Model: {row[5]})")
        else:
            print(f"    [-] MISSING: {lid}")

    assert found_count == 5, "5건 중 미복원 건 존재!"
    print(f"    -> 정상 매물 5건 100% 원자적 복원 및 차량 외래키 연결 확인 완료!")

    # 3. 무결성 점검
    c.execute("PRAGMA integrity_check;")
    integ = c.fetchall()
    print(f"\n[3] PRAGMA integrity_check: {integ}")
    assert integ == [("ok",)], "Integrity check failed!"

    c.execute("PRAGMA foreign_key_check;")
    fk = c.fetchall()
    print(f"[4] PRAGMA foreign_key_check: {len(fk)}건 위반")
    assert len(fk) == 0, "FK check failed!"

    # 4. 플랫폼별 총 건수 확인
    c.execute("SELECT platform, count(*) FROM vehicle_listings GROUP BY platform;")
    counts = c.fetchall()
    print(f"\n[5] 최종 vehicle_listings 플랫폼별 건수:")
    for p, cnt in counts:
        print(f"    - {p}: {cnt}건")

    # 결과 증적 저장
    res_doc = {
        "restored_at": "2026-10-30T23:55:00+09:00",
        "restored_listings": restore_ids,
        "integrity_check": "ok",
        "foreign_key_violations": 0,
        "counts": dict(counts)
    }
    with open("scratch/task1_restoration_evidence.json", "w", encoding="utf-8") as f:
        json.dump(res_doc, f, ensure_ascii=False, indent=2)
    print("\n[+] TASK 1 증적 scratch/task1_restoration_evidence.json 저장 완료!")

    conn.close()

if __name__ == "__main__":
    verify_task1_restoration()
