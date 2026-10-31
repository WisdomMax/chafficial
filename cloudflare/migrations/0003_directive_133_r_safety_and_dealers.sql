-- DIRECTIVE 133-R: D1 안전 복원 및 제휴 상사 공식 인가 마이그레이션

-- 1. 64노3143 비공개 안전 복원
UPDATE vehicles 
SET is_public = 0, publishing_status = 'PENDING_REVIEW', updated_at = datetime('now')
WHERE id = 'e6670a2e-c532-435e-b34a-b4a3ff9a677c' OR plate_number = '64노3143';

-- 64노3143 사진 9장/10장 PENDING / PRIVATE 복원
UPDATE vehicle_photos 
SET approval_status = 'PENDING', public_visibility = 'PRIVATE'
WHERE vehicle_id = 'e6670a2e-c532-435e-b34a-b4a3ff9a677c';

-- 2. 임시 번호판(더쿨-XXXX) 매물 35대 비공개 안전 격리
UPDATE vehicles 
SET is_public = 0, publishing_status = 'PENDING_REVIEW', updated_at = datetime('now')
WHERE plate_number LIKE '더쿨-%';

-- 3. (주)더쿨모터스 공식 제휴 상사 등록
INSERT OR REPLACE INTO dealers (
  id, branch_id, name, dealership_name, phone, partnership_status, contract_date, created_at
) VALUES (
  'dealer-thecool-motors',
  '61fea9a4-58f0-42bd-862c-14fd16d0d21c',
  '이오덕',
  '(주)더쿨모터스',
  '010-2588-9675',
  'ACTIVE',
  '2026-10-01',
  datetime('now')
);
