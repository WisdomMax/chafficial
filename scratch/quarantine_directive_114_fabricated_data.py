import sqlite3
import json
import time
from pathlib import Path

def main():
    db_path = "data/chamart/chamart_platform_demo.db"
    backup_dir = Path("data/chamart/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"chamart_online_backup_directive115_{ts}.db"

    print("=== [TASK 1] 가상 교차 매칭 데이터 긴급 격리 파이프라인 ===")
    
    # 1. SQLite Online Backup API로 안전한 백업본 생성
    src_conn = sqlite3.connect(db_path)
    bck_conn = sqlite3.connect(str(backup_path))
    with bck_conn:
        src_conn.backup(bck_conn)
    bck_conn.close()
    print(f"[1] SQLite Online Backup 완료: {backup_path} ({backup_path.stat().st_size / (1024*1024):.2f} MB)")

    c = src_conn.cursor()

    # 사전 무결성 점검
    c.execute("PRAGMA integrity_check;")
    print(f"    - PRAGMA integrity_check (사전): {c.fetchall()}")
    c.execute("PRAGMA foreign_key_check;")
    fk_pre = c.fetchall()
    print(f"    - PRAGMA foreign_key_check (사전): {len(fk_pre)}건 위반")

    # 2. 가상 데이터 식별 및 백업
    c.execute("""
        SELECT id, vehicle_id, platform, listing_id, advertised_price, observation_notes
        FROM vehicle_listings
        WHERE observation_notes LIKE '%MatchStatus:%'
           OR listing_id LIKE 'KB_%'
           OR listing_id LIKE 'ENCAR_%'
    """)
    fabricated_listings = [
        {
            "id": r[0], "vehicle_id": r[1], "platform": r[2], 
            "listing_id": r[3], "advertised_price": r[4], "notes": r[5]
        }
        for r in c.fetchall()
    ]
    print(f"[2] 식별된 가상 vehicle_listings: {len(fabricated_listings)}건")

    c.execute("""
        SELECT id, vehicle_id, photo_url, photo_source, public_visibility, approval_status
        FROM vehicle_photos
        WHERE photo_url LIKE '%sample_%_1.jpg%' 
           OR photo_url LIKE '%sample_%_2.jpg%'
           OR photo_url LIKE '%sample_%'
    """)
    fabricated_photos = [
        {
            "id": r[0], "vehicle_id": r[1], "photo_url": r[2],
            "photo_source": r[3], "public_visibility": r[4], "approval_status": r[5]
        }
        for r in c.fetchall()
    ]
    print(f"[3] 식별된 가상 vehicle_photos: {len(fabricated_photos)}건")

    # 격리 데이터 JSON 아카이브
    quarantine_payload = {
        "quarantined_at": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
        "reason": "CHA-FICIAL DIRECTIVE 115 Fabricated Match Quarantine",
        "listings_count": len(fabricated_listings),
        "photos_count": len(fabricated_photos),
        "listings": fabricated_listings,
        "photos": fabricated_photos
    }
    with open("scratch/quarantined_fabricated_matches.json", "w", encoding="utf-8") as f:
        json.dump(quarantine_payload, f, ensure_ascii=False, indent=2)
    print("    - 격리 데이터 아카이브 완료: scratch/quarantined_fabricated_matches.json")

    # 3. 운영 DB에서 가상 데이터 삭제 격리
    c.execute("""
        DELETE FROM vehicle_listings
        WHERE observation_notes LIKE '%MatchStatus:%'
           OR listing_id LIKE 'KB_%'
           OR listing_id LIKE 'ENCAR_%'
    """)
    deleted_listings = c.rowcount

    c.execute("""
        DELETE FROM vehicle_photos
        WHERE photo_url LIKE '%sample_%_1.jpg%' 
           OR photo_url LIKE '%sample_%_2.jpg%'
           OR photo_url LIKE '%sample_%'
    """)
    deleted_photos = c.rowcount

    src_conn.commit()
    print(f"[4] 운영 DB 삭제 완료: Listings {deleted_listings}건, Photos {deleted_photos}건")

    # 사후 무결성 점검
    c.execute("PRAGMA integrity_check;")
    print(f"[5] PRAGMA integrity_check (사후): {c.fetchall()}")
    c.execute("PRAGMA foreign_key_check;")
    fk_post = c.fetchall()
    print(f"    - PRAGMA foreign_key_check (사후): {len(fk_post)}건 위반")

    # 정상 핵심 데이터 보존 확인
    c.execute("SELECT count(*) FROM vehicles;")
    total_vehicles = c.fetchone()[0]
    c.execute("SELECT count(*) FROM vehicle_listings WHERE platform = 'CARMANAGER';")
    cm_listings = c.fetchone()[0]
    c.execute("SELECT count(*) FROM customers;")
    total_customers = c.fetchone()[0]
    c.execute("SELECT count(*) FROM consultations;")
    total_consultations = c.fetchone()[0]
    c.execute("SELECT count(*) FROM transactions;")
    total_transactions = c.fetchone()[0]

    print(f"[6] 핵심 운영 데이터 무결성 보존 확인:")
    print(f"    - Total Vehicles: {total_vehicles}대")
    print(f"    - CarManager Listings: {cm_listings}건")
    print(f"    - Customers: {total_customers}명")
    print(f"    - Consultations: {total_consultations}건")
    print(f"    - Transactions: {total_transactions}건")

    src_conn.close()
    print("[+] TASK 1 가상 데이터 격리 및 운영 DB 정화 100% 완료!")

if __name__ == "__main__":
    main()
