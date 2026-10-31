
INSERT INTO vehicles (
    id, branch_id, plate_number, model_name, year, mileage, fuel_type, 
    transmission, color, purchase_price, target_price, status, is_demo, 
    timeline_json, created_at, updated_at, ownership_type, vin, 
    first_registration_date, drive_type, primary_photo_url, 
    manufacturer, trim, body_type, publishing_status, is_public, 
    listing_ownership_type, is_priority_exposure, priority_rank
) VALUES (
    'e6670a2e-c532-435e-b34a-b4a3ff9a677c', '61fea9a4-58f0-42bd-862c-14fd16d0d21c', '64노3143', '랜드로버 디스커버리 스포츠', 2018, 125428, '경유',
    '오토', '화이트', 0, 1090, 'FOR_SALE', 0,
    '[{"event": "DIRECTIVE_132_A_STAGING", "timestamp": "2026-10-31T11:25:07.793220+09:00", "note": "제시번호:2026099548 실매물 비공개 대기 등록"}]',
    '2026-10-31T11:25:07.793220+09:00', '2026-10-31T11:25:07.793220+09:00', 'EXTERNAL', 'SALCA2BN5JH761441',
    '2018-09-14', null, 'https://img.carmanager.co.kr/temp/photo/20260909/0CAD6BE080CDA63FE5F689D30327DD6A4164F8FB68FFD2B387143B1E5AA3F415.jpg',
    '랜드로버', '디스커버리 스포츠 2.0 TD4 SE', 'SUV', 'PENDING_REVIEW', 0,
    'EXTERNAL', 0, 0
);


INSERT INTO vehicle_listings (
    id, vehicle_id, platform, listing_id, listing_url, advertised_price, 
    listing_status, first_observed_at, last_observed_at, region, 
    is_janghanpyeong, data_confidence, observation_notes, raw_seller_name, 
    raw_seller_location, is_demo
) VALUES (
    'listing-a79c2748', 'e6670a2e-c532-435e-b34a-b4a3ff9a677c', 'CARMANAGER', '2026099548', 
    'https://www.carmanager.co.kr/MyPageCar/Edit/114204774', 1090, 
    'FOR_SALE', '2026-10-31T11:25:07.793220+09:00', '2026-10-31T11:25:07.793220+09:00', '서울 장한평', 
    1, 0.98, '제시번호: 2026099548 (주)더쿨모터스 위탁 실매물', 
    '(주)더쿨모터스', '성동구/장안모터프라', 0
);


INSERT INTO vehicle_photos (
    id, vehicle_id, photo_url, category, sort_order, is_primary, 
    allow_video_use, created_at, verification_status, photo_source, 
    public_visibility, approval_status
) VALUES (
    'b04917ad-3ef3-4a46-b669-98148efd1a54', 'e6670a2e-c532-435e-b34a-b4a3ff9a677c', 'https://img.carmanager.co.kr/temp/photo/20260909/0CAD6BE080CDA63FE5F689D30327DD6A4164F8FB68FFD2B387143B1E5AA3F415.jpg', 'EXTERIOR', 1, 1, 
    1, '2026-10-31T11:25:07.793220+09:00', 'VERIFIED', 'CARMANAGER', 
    'PRIVATE', 'PENDING'
);


INSERT INTO vehicle_photos (
    id, vehicle_id, photo_url, category, sort_order, is_primary, 
    allow_video_use, created_at, verification_status, photo_source, 
    public_visibility, approval_status
) VALUES (
    'aa664567-f5bf-4bbe-9a91-feb4b4d857e6', 'e6670a2e-c532-435e-b34a-b4a3ff9a677c', 'https://img.carmanager.co.kr/temp/photo/20260909/4853A188B7DA6CD5C94FE2860E1AEA420F4075314D156D717483511B1D17D80D.jpg', 'EXTERIOR', 2, 0, 
    1, '2026-10-31T11:25:07.793220+09:00', 'VERIFIED', 'CARMANAGER', 
    'PRIVATE', 'PENDING'
);


INSERT INTO vehicle_photos (
    id, vehicle_id, photo_url, category, sort_order, is_primary, 
    allow_video_use, created_at, verification_status, photo_source, 
    public_visibility, approval_status
) VALUES (
    '6713e8df-30a5-46b8-a6ab-4ccddff6c09c', 'e6670a2e-c532-435e-b34a-b4a3ff9a677c', 'https://img.carmanager.co.kr/temp/photo/20260909/832063D2D5C2ACE60E763B994091811D89F767989B4943D2420E1A5C6B62705E.jpg', 'EXTERIOR', 3, 0, 
    1, '2026-10-31T11:25:07.793220+09:00', 'VERIFIED', 'CARMANAGER', 
    'PRIVATE', 'PENDING'
);


INSERT INTO vehicle_photos (
    id, vehicle_id, photo_url, category, sort_order, is_primary, 
    allow_video_use, created_at, verification_status, photo_source, 
    public_visibility, approval_status
) VALUES (
    '4fbceb0a-36e0-48f6-abe2-bbc17f82a5cf', 'e6670a2e-c532-435e-b34a-b4a3ff9a677c', 'https://img.carmanager.co.kr/temp/photo/20260909/68FF1F19B4E51EC196EA617DAB10AED32FD4D0CD51C7AF671D836FFCFDF935F2.jpg', 'EXTERIOR', 4, 0, 
    1, '2026-10-31T11:25:07.793220+09:00', 'VERIFIED', 'CARMANAGER', 
    'PRIVATE', 'PENDING'
);


INSERT INTO vehicle_photos (
    id, vehicle_id, photo_url, category, sort_order, is_primary, 
    allow_video_use, created_at, verification_status, photo_source, 
    public_visibility, approval_status
) VALUES (
    '300e4f6e-99d1-4fdb-a997-7472398c1df0', 'e6670a2e-c532-435e-b34a-b4a3ff9a677c', 'https://img.carmanager.co.kr/temp/photo/20260909/5D97EDACCAAC548FF48880BAFCA1FA36A24896712DC3DADE32AFBC21CF57825F.jpg', 'EXTERIOR', 5, 0, 
    1, '2026-10-31T11:25:07.793220+09:00', 'VERIFIED', 'CARMANAGER', 
    'PRIVATE', 'PENDING'
);


INSERT INTO vehicle_photos (
    id, vehicle_id, photo_url, category, sort_order, is_primary, 
    allow_video_use, created_at, verification_status, photo_source, 
    public_visibility, approval_status
) VALUES (
    '89bc4db7-3ab8-40e4-8829-bdd87c226c24', 'e6670a2e-c532-435e-b34a-b4a3ff9a677c', 'https://img.carmanager.co.kr/temp/photo/20260909/810901E10873104CF5E76905334D90B0A3098EDEC1412D23D7377F78BD564262.jpg', 'EXTERIOR', 6, 0, 
    1, '2026-10-31T11:25:07.793220+09:00', 'VERIFIED', 'CARMANAGER', 
    'PRIVATE', 'PENDING'
);


INSERT INTO vehicle_photos (
    id, vehicle_id, photo_url, category, sort_order, is_primary, 
    allow_video_use, created_at, verification_status, photo_source, 
    public_visibility, approval_status
) VALUES (
    'd650879f-e6b5-42f1-9f0a-9a2e7fad3e03', 'e6670a2e-c532-435e-b34a-b4a3ff9a677c', 'https://img.carmanager.co.kr/temp/photo/20260909/AF0B7252F643FD2BF6A1669DCC0ADD36C1C41A42AD983347444CF858984B9779.jpg', 'EXTERIOR', 7, 0, 
    1, '2026-10-31T11:25:07.793220+09:00', 'VERIFIED', 'CARMANAGER', 
    'PRIVATE', 'PENDING'
);


INSERT INTO vehicle_photos (
    id, vehicle_id, photo_url, category, sort_order, is_primary, 
    allow_video_use, created_at, verification_status, photo_source, 
    public_visibility, approval_status
) VALUES (
    'f9cc555d-e906-45a4-a899-f3dd42c859df', 'e6670a2e-c532-435e-b34a-b4a3ff9a677c', 'https://img.carmanager.co.kr/temp/photo/20260909/27058443325C4AEE09F67B9D67EA4067966D901D294736908A11CAF54EB8ED9F.jpg', 'EXTERIOR', 8, 0, 
    1, '2026-10-31T11:25:07.793220+09:00', 'VERIFIED', 'CARMANAGER', 
    'PRIVATE', 'PENDING'
);


INSERT INTO vehicle_photos (
    id, vehicle_id, photo_url, category, sort_order, is_primary, 
    allow_video_use, created_at, verification_status, photo_source, 
    public_visibility, approval_status
) VALUES (
    'c57feea2-69c3-4bf6-adb5-9f5098ff29c1', 'e6670a2e-c532-435e-b34a-b4a3ff9a677c', 'https://img.carmanager.co.kr/temp/photo/20260909/985AEDD0B201DC738D201F28A38D9A29A7349A273CB425CECCFBC69C510F021E.jpg', 'EXTERIOR', 9, 0, 
    1, '2026-10-31T11:25:07.793220+09:00', 'VERIFIED', 'CARMANAGER', 
    'PRIVATE', 'PENDING'
);
