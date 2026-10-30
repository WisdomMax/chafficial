import sqlite3
from pathlib import Path

def test_candidate_quarantine_in_standalone_db():
    print("=== [TASK 5] 독립 테스트 DB 기반 CANDIDATE(REVIEW_PENDING) 격리 검증 (FK=ON) ===")
    
    test_db = "scratch/test_candidate_isolated.db"
    if Path(test_db).exists():
        Path(test_db).unlink()

    conn = sqlite3.connect(test_db)
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON;")

    # 스키마 구성 (실제 DB 스키마 반영)
    c.execute("""
        CREATE TABLE vehicles (
            id VARCHAR(36) PRIMARY KEY,
            model_name VARCHAR(100) NOT NULL,
            target_price INTEGER,
            status VARCHAR(30) NOT NULL DEFAULT 'AVAILABLE'
        );
    """)
    c.execute("""
        CREATE TABLE vehicle_listings (
            id VARCHAR(36) PRIMARY KEY,
            vehicle_id VARCHAR(36) NOT NULL,
            platform VARCHAR(30) NOT NULL,
            listing_id VARCHAR(50) NOT NULL,
            advertised_price INTEGER,
            listing_status VARCHAR(30) NOT NULL,
            first_observed_at DATETIME NOT NULL,
            last_observed_at DATETIME NOT NULL,
            FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
        );
    """)

    # 1. 실제 외래키를 만족하는 차량 마스터 2대 삽입
    c.execute("INSERT INTO vehicles (id, model_name, target_price) VALUES ('veh-active-01', '그랜저 IG', 2000);")
    c.execute("INSERT INTO vehicles (id, model_name, target_price) VALUES ('veh-candidate-02', '아반떼 AD', NULL);")

    # 2. 리스팅 삽입: veh-01은 ACTIVE, veh-02는 CANDIDATE(REVIEW_PENDING, 이상치 가격 99999만원)
    c.execute("""
        INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, advertised_price, listing_status, first_observed_at, last_observed_at)
        VALUES ('list-01', 'veh-active-01', 'CARMANAGER', 'CM_101', 2000, 'ACTIVE', '2026-10-31T00:00:00', '2026-10-31T00:00:00');
    """)
    c.execute("""
        INSERT INTO vehicle_listings (id, vehicle_id, platform, listing_id, advertised_price, listing_status, first_observed_at, last_observed_at)
        VALUES ('list-02', 'veh-candidate-02', 'KB_CHACHACHA', 'KB_CANDIDATE_202', 99999, 'REVIEW_PENDING', '2026-10-31T00:00:00', '2026-10-31T00:00:00');
    """)
    conn.commit()

    # 3. PRAGMA foreign_key_check로 외래키 유효성 검증
    c.execute("PRAGMA foreign_key_check;")
    fk_violations = c.fetchall()
    print(f"[1] FK 유효성 확인: {len(fk_violations)}건 위반 (정상)")
    assert len(fk_violations) == 0

    # 4. 다운스트림 시세 분석 쿼리 실행 (ACTIVE만 필터링)
    c.execute("""
        SELECT avg(advertised_price), max(advertised_price), count(*)
        FROM vehicle_listings
        WHERE listing_status = 'ACTIVE' AND advertised_price IS NOT NULL
    """)
    pricing_res = c.fetchone()
    print(f"[2] 다운스트림 시세 분석 통계: 평균={pricing_res[0]}만원, 최고가={pricing_res[1]}만원, 건수={pricing_res[2]}건")
    assert pricing_res[0] == 2000.0, "평균 가격 오염 발생!"
    assert pricing_res[1] == 2000, "최고 가격 오염 발생!"
    assert pricing_res[2] == 1, "CANDIDATE 매물이 시세 분석에 포함됨!"

    # 5. AI 학습용 Feature Store 추출 쿼리 실행
    c.execute("""
        SELECT v.id, v.model_name, l.advertised_price
        FROM vehicles v
        JOIN vehicle_listings l ON v.id = l.vehicle_id
        WHERE l.listing_status = 'ACTIVE'
    """)
    ml_rows = c.fetchall()
    print(f"[3] AI Feature Store 추출 건수: {len(ml_rows)}건 (ID: {ml_rows[0][0]}, Price: {ml_rows[0][2]}만원)")
    assert len(ml_rows) == 1
    assert ml_rows[0][0] == "veh-active-01", "CANDIDATE 차량이 Feature Store에 혼입됨!"

    conn.close()
    if Path(test_db).exists():
        Path(test_db).unlink()

    print("[+] TASK 5 독립 테스트 DB 기반 CANDIDATE 격리 검증 100% 통과!")

if __name__ == "__main__":
    test_candidate_quarantine_in_standalone_db()
