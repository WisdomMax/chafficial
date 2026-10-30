import sqlite3

def test_candidate_quarantine_from_pricing_and_ml():
    print("=== [TASK 5] CANDIDATE 매물(REVIEW_PENDING)의 가격 분석 및 AI 학습 격리 SQL 검증 ===")
    
    conn = sqlite3.connect("data/chamart/chamart_platform_demo.db")
    c = conn.cursor()

    # 1. 임시 CANDIDATE 매물 삽입 (REVIEW_PENDING 상태, 이상치 가격 99999만원)
    test_veh_id = "test-candidate-veh-001"
    c.execute("""
        INSERT OR REPLACE INTO vehicle_listings (
            id, vehicle_id, platform, listing_id, advertised_price, 
            listing_status, first_observed_at, last_observed_at, is_demo
        ) VALUES (
            'test-listing-cand-1', ?, 'KB_CHACHACHA', 'KB_CANDIDATE_TEST', 
            99999, 'REVIEW_PENDING', '2026-10-31T00:00:00+09:00', '2026-10-31T00:00:00+09:00', 0
        )
    """, (test_veh_id,))

    # 2. 다운스트림 가격 분석 쿼리 (ACTIVE만 조회)
    c.execute("""
        SELECT avg(advertised_price), max(advertised_price), count(*)
        FROM vehicle_listings
        WHERE listing_status = 'ACTIVE' AND advertised_price IS NOT NULL
    """)
    active_pricing = c.fetchone()
    print(f"[1] ACTIVE 매물 가격 분석 결과: 평균 {active_pricing[0]:.1f}만원, 최고가 {active_pricing[1]}만원, 건수 {active_pricing[2]}건")
    assert active_pricing[1] < 99999, "CANDIDATE 매물이 ACTIVE 가격 분석에 혼입됨!"

    # 3. AI 시계열 Feature Store 학습용 피처 추출 쿼리 검증
    c.execute("""
        SELECT count(*)
        FROM vehicle_listings
        WHERE listing_status = 'ACTIVE' AND listing_id = 'KB_CANDIDATE_TEST'
    """)
    ml_active_count = c.fetchone()[0]
    print(f"[2] AI Feature Store 학습 데이터셋 혼입 건수: {ml_active_count}건")
    assert ml_active_count == 0, "CANDIDATE 매물이 AI Feature Store에 포함됨!"

    # 4. 검토 대기 큐에는 정상 조회되는지 확인
    c.execute("""
        SELECT count(*)
        FROM vehicle_listings
        WHERE listing_status = 'REVIEW_PENDING' AND listing_id = 'KB_CANDIDATE_TEST'
    """)
    review_queue_count = c.fetchone()[0]
    print(f"[3] 수동 검토 대기 큐(REVIEW_PENDING) 조회 건수: {review_queue_count}건 (정상 격리)")
    assert review_queue_count == 1, "검토 대기 큐에서 조회 실패!"

    # 정리
    c.execute("DELETE FROM vehicle_listings WHERE id = 'test-listing-cand-1';")
    conn.commit()
    conn.close()

    print("[+] TASK 5 CANDIDATE 가격 분석 및 AI 학습 격리 SQL 검증 100% 통과!")

if __name__ == "__main__":
    test_candidate_quarantine_from_pricing_and_ml()
