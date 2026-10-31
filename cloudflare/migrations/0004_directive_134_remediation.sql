-- DIRECTIVE 134: Remediation for dealer authorization, consent proof, and dummy deactivation

-- 1. Add verification proof columns to dealers table if not exist
ALTER TABLE dealers ADD COLUMN marketing_consent_verified INTEGER DEFAULT 0;
ALTER TABLE dealers ADD COLUMN photo_consent_verified INTEGER DEFAULT 0;
ALTER TABLE dealers ADD COLUMN consent_proof_uri TEXT;

-- 2. Deactivate unverified dummy dealers to prevent any unintended sync or classification
UPDATE dealers
SET partnership_status = 'INACTIVE'
WHERE id != 'dealer-thecool-motors';

-- 3. Correct (주)더쿨모터스 record with truthful verified metadata
UPDATE dealers
SET 
    name = '유동호',
    phone = '확인대기',
    partnership_status = 'ACTIVE',
    marketing_consent_verified = 1,
    photo_consent_verified = 1,
    consent_proof_uri = 'internal://auth_proofs/64노3143_thecoolmotors_auth.json'
WHERE id = 'dealer-thecool-motors';
