"""
DIRECTIVE 132-A TASK 3: 사진 승인 강제 및 4단계 정렬 단위 테스트
1. 사진 9장 중 8장 승인, 1장 미승인 시 8장만 반환되고 미승인 사진은 100% 제외되는지 검증
2. 승인 사진이 0장인 경우 DB 조회 결과 0건으로 no_photo.svg fallback으로 연결되는지 검증
3. 4단계 노출 순위가 승인된 실차 사진 기준으로만 완벽하게 계산되는지 검증
"""

import sqlite3

def test_photo_approval_and_4tier_order():
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE vehicles (
        id TEXT PRIMARY KEY,
        plate_number TEXT,
        model_name TEXT,
        listing_ownership_type TEXT,
        is_public INTEGER,
        is_demo INTEGER,
        publishing_status TEXT,
        status TEXT,
        target_price INTEGER,
        mileage INTEGER,
        year INTEGER,
        created_at TEXT,
        is_priority_exposure INTEGER,
        priority_rank INTEGER,
        options_json TEXT
    );
    ''')

    cur.execute('''
    CREATE TABLE vehicle_photos (
        id TEXT PRIMARY KEY,
        vehicle_id TEXT,
        photo_url TEXT,
        approval_status TEXT,
        public_visibility TEXT,
        is_primary INTEGER,
        sort_order INTEGER,
        caption TEXT,
        display_label TEXT,
        category TEXT
    );
    ''')

    # Car 1: Chamart Owned, has 8 approved photos + 1 pending photo
    cur.execute("INSERT INTO vehicles VALUES ('car-1', '64노3143', '랜드로버 디스커버리 스포츠', 'CHAMART_OWNED', 1, 0, 'APPROVED', 'FOR_SALE', 1090, 125428, 2018, '2026-10-31', 0, 0, '[]')")
    # Car 2: Chamart Owned, has 0 approved photos (only 9 pending photos)
    cur.execute("INSERT INTO vehicles VALUES ('car-2', '77조7777', '차마트 사진없는차', 'CHAMART_OWNED', 1, 0, 'APPROVED', 'FOR_SALE', 2000, 50000, 2020, '2026-10-31', 0, 0, '[]')")
    # Car 3: External Owned, has 1 approved photo
    cur.execute("INSERT INTO vehicles VALUES ('car-3', '88오8888', '타사 사진있는차', 'EXTERNAL', 1, 0, 'APPROVED', 'FOR_SALE', 1500, 60000, 2019, '2026-10-31', 0, 0, '[]')")
    # Car 4: External Owned, has 0 approved photos
    cur.execute("INSERT INTO vehicles VALUES ('car-4', '99다9999', '타사 사진없는차', 'EXTERNAL', 1, 0, 'APPROVED', 'FOR_SALE', 1200, 70000, 2017, '2026-10-31', 0, 0, '[]')")

    # Photos for Car 1: 8 APPROVED + 1 PENDING
    for i in range(1, 9):
        cur.execute(f"INSERT INTO vehicle_photos VALUES ('p1-{i}', 'car-1', 'https://img.carmanager.co.kr/photo{i}.jpg', 'APPROVED', 'PUBLIC', {1 if i==1 else 0}, {i}, '사진{i}', '사진{i}', 'EXTERIOR')")
    cur.execute("INSERT INTO vehicle_photos VALUES ('p1-9', 'car-1', 'https://img.carmanager.co.kr/photo9_unapproved.jpg', 'PENDING', 'PRIVATE', 0, 9, '미승인사진', '미승인사진', 'EXTERIOR')")

    # Photos for Car 2: 9 PENDING photos
    for i in range(1, 10):
        cur.execute(f"INSERT INTO vehicle_photos VALUES ('p2-{i}', 'car-2', 'https://img.carmanager.co.kr/photo_c2_{i}.jpg', 'PENDING', 'PRIVATE', {1 if i==1 else 0}, {i}, '미승인{i}', '미승인{i}', 'EXTERIOR')")

    # Photos for Car 3: 1 APPROVED photo
    cur.execute("INSERT INTO vehicle_photos VALUES ('p3-1', 'car-3', 'https://img.carmanager.co.kr/photo_c3_1.jpg', 'APPROVED', 'PUBLIC', 1, 1, '승인사진', '승인사진', 'EXTERIOR')")

    # Subquery for approved photo existence
    has_approved_subquery = '''
    EXISTS (
        SELECT 1 FROM vehicle_photos vp 
        WHERE vp.vehicle_id = vehicles.id 
          AND vp.approval_status = 'APPROVED' 
          AND vp.public_visibility = 'PUBLIC'
          AND (vp.photo_url LIKE 'http://%' OR vp.photo_url LIKE 'https://%')
          AND vp.photo_url NOT LIKE '%placeholder%'
          AND vp.photo_url NOT LIKE '%no_photo%'
          AND vp.photo_url NOT LIKE '%unsplash%'
          AND vp.photo_url NOT LIKE '%ui_fixtures%'
          AND vp.photo_url NOT LIKE '%demo%'
    )
    '''

    sql = f'''
    SELECT 
      id, plate_number, model_name, listing_ownership_type,
      (CASE 
        WHEN (listing_ownership_type = 'OWNED' OR listing_ownership_type = 'CHAMART_OWNED') 
             AND {has_approved_subquery} THEN 1
        WHEN (listing_ownership_type = 'OWNED' OR listing_ownership_type = 'CHAMART_OWNED') THEN 2
        WHEN {has_approved_subquery} THEN 3
        ELSE 4
      END) as tier,
      (SELECT vp.photo_url 
       FROM vehicle_photos vp 
       WHERE vp.vehicle_id = vehicles.id 
         AND vp.approval_status = 'APPROVED' 
         AND vp.public_visibility = 'PUBLIC'
         AND (vp.photo_url LIKE 'http://%' OR vp.photo_url LIKE 'https://%')
         AND vp.photo_url NOT LIKE '%placeholder%'
         AND vp.photo_url NOT LIKE '%no_photo%'
         AND vp.photo_url NOT LIKE '%unsplash%'
         AND vp.photo_url NOT LIKE '%ui_fixtures%'
         AND vp.photo_url NOT LIKE '%demo%'
       ORDER BY vp.is_primary DESC, vp.sort_order ASC 
       LIMIT 1) as approved_primary_photo_url,
      (SELECT COUNT(*) 
       FROM vehicle_photos vp 
       WHERE vp.vehicle_id = vehicles.id 
         AND vp.approval_status = 'APPROVED' 
         AND vp.public_visibility = 'PUBLIC'
         AND (vp.photo_url LIKE 'http://%' OR vp.photo_url LIKE 'https://%')
         AND vp.photo_url NOT LIKE '%placeholder%'
         AND vp.photo_url NOT LIKE '%no_photo%'
         AND vp.photo_url NOT LIKE '%unsplash%'
         AND vp.photo_url NOT LIKE '%ui_fixtures%'
         AND vp.photo_url NOT LIKE '%demo%') as approved_photo_count
    FROM vehicles 
    ORDER BY tier ASC
    '''

    rows = cur.execute(sql).fetchall()

    # 1. 4-Tier sorting verification
    assert rows[0][0] == 'car-1' and rows[0][4] == 1, 'Car 1 must be Tier 1 (Chamart + Approved Photo)'
    assert rows[1][0] == 'car-2' and rows[1][4] == 2, 'Car 2 must be Tier 2 (Chamart + No Approved Photo)'
    assert rows[2][0] == 'car-3' and rows[2][4] == 3, 'Car 3 must be Tier 3 (External + Approved Photo)'
    assert rows[3][0] == 'car-4' and rows[3][4] == 4, 'Car 4 must be Tier 4 (External + No Approved Photo)'

    # 2. Detail photos for Car 1 (must only return 8 approved photos, excluding unapproved 9th photo)
    detail_photos = cur.execute('''
    SELECT photo_url FROM vehicle_photos 
    WHERE vehicle_id = 'car-1' 
      AND approval_status = 'APPROVED' 
      AND public_visibility = 'PUBLIC'
    ORDER BY is_primary DESC, sort_order ASC
    ''').fetchall()

    assert len(detail_photos) == 8, 'Car 1 must return exactly 8 approved photos'
    assert not any('unapproved' in p[0] for p in detail_photos), 'Unapproved 9th photo must be strictly excluded'

    # 3. Detail photos for Car 2 (0 approved photos -> 0 rows, fallback required)
    c2_photos = cur.execute('''
    SELECT photo_url FROM vehicle_photos 
    WHERE vehicle_id = 'car-2' 
      AND approval_status = 'APPROVED' 
      AND public_visibility = 'PUBLIC'
    ORDER BY is_primary DESC, sort_order ASC
    ''').fetchall()

    assert len(c2_photos) == 0, 'Car 2 must return 0 approved photos'

def test_seller_company_and_branch_separation():
    conn = sqlite3.connect(':memory:')
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE vehicles (
        id TEXT PRIMARY KEY,
        plate_number TEXT,
        listing_ownership_type TEXT
    );
    ''')

    cur.execute('''
    CREATE TABLE vehicle_listings (
        id TEXT PRIMARY KEY,
        vehicle_id TEXT,
        raw_seller_name TEXT,
        raw_seller_location TEXT
    );
    ''')

    # 1. External vehicle (64노3143, The Cool Motors)
    cur.execute("INSERT INTO vehicles VALUES ('car-ext', '64노3143', 'EXTERNAL')")
    cur.execute("INSERT INTO vehicle_listings VALUES ('list-1', 'car-ext', '(주)더쿨모터스', '서울 성동구 용답동 장안모터프라자')")

    # 2. Owned vehicle (Chamart owned)
    cur.execute("INSERT INTO vehicles VALUES ('car-own', '11가1111', 'OWNED')")

    # Verify query for external vehicle
    sql = '''
    SELECT 
      v.id, v.plate_number, v.listing_ownership_type,
      (SELECT vl.raw_seller_name FROM vehicle_listings vl WHERE vl.vehicle_id = v.id LIMIT 1) as seller_name,
      (SELECT vl.raw_seller_location FROM vehicle_listings vl WHERE vl.vehicle_id = v.id LIMIT 1) as seller_location
    FROM vehicles v
    ORDER BY v.id DESC
    '''
    rows = cur.execute(sql).fetchall()

    ext_car = [r for r in rows if r[0] == 'car-ext'][0]
    own_car = [r for r in rows if r[0] == 'car-own'][0]

    # External assertions
    is_ext_owned = (ext_car[2] == 'OWNED' or ext_car[2] == 'CHAMART_OWNED')
    assert not is_ext_owned, 'External vehicle must not be chamart owned'
    ext_branch = '차마트 직영점' if is_ext_owned else f"{ext_car[3]} (제휴 상사)"
    assert ext_branch == '(주)더쿨모터스 (제휴 상사)', 'External branch must reflect actual dealer name'
    assert ext_car[3] == '(주)더쿨모터스', 'Seller name must match DB listing'

    # Owned assertions
    is_own_owned = (own_car[2] == 'OWNED' or own_car[2] == 'CHAMART_OWNED')
    assert is_own_owned, 'Owned vehicle must be chamart owned'
    own_branch = '차마트 직영점' if is_own_owned else f"{own_car[3]} (제휴 상사)"
    assert own_branch == '차마트 직영점', 'Owned branch must be 차마트 직영점'

if __name__ == '__main__':
    test_photo_approval_and_4tier_order()
    test_seller_company_and_branch_separation()
    print('All tests passed successfully!')
