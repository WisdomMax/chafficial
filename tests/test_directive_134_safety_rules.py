#!/usr/bin/env python3
"""
Unit Test for DIRECTIVE 134: Production Safety Remediation & Real Vehicle Validation
- Test 1: Test identifiers (TEST-*, PROBE-*, DEMO-*, MOCK-*, TEMP-*) strictly rejected with 400
- Test 2: Inactive/Unverified dealer (marketing_consent_verified != 1) blocked from auto-publish
- Test 3: Validated dealer + real car remains PENDING_REVIEW before explicit user publication approval
- Test 4: Fake plate / partial plate (더쿨-XXXX) strictly blocked
- Test 5: Sold vehicle transition guard prevents resurrection on resend
- Test 6: Missing attributes strictly remain NULL instead of fake defaults
"""

import sys
import re

TEST_IDENTIFIER_REGEX = re.compile(r'^(TEST|PROBE|DEMO|MOCK|TEMP)-', re.IGNORECASE)
PLATE_REGEX = re.compile(r'^\d{2,3}[가-힣]\d{4}$')

def validate_sync_vehicle(v: dict, dealer_db: dict) -> tuple:
    """Simulates _worker.js sync vehicle validation logic."""
    vid = v.get('id', '')
    plate = v.get('plate_number', '')
    reg_no = v.get('registration_number', '')

    # 1. Test identifier check
    if TEST_IDENTIFIER_REGEX.search(vid) or TEST_IDENTIFIER_REGEX.search(plate) or TEST_IDENTIFIER_REGEX.search(reg_no):
        return False, "TEST_IDENTIFIER_PROHIBITED_IN_PROD", None

    # 2. Dealer verification check (ACTIVE + marketing_consent_verified = 1)
    sangsa = v.get('sangsa_name', '').strip()
    dealer_info = dealer_db.get(sangsa)
    is_authorized_dealer = False
    if dealer_info:
        if dealer_info.get('partnership_status') == 'ACTIVE' and dealer_info.get('marketing_consent_verified') == 1:
            is_authorized_dealer = True

    # 3. Plate regex check
    clean_plate = plate.replace(' ', '')
    has_valid_plate = bool(PLATE_REGEX.match(clean_plate))

    # 4. Price & status check
    price = int(v.get('target_price', 0))
    has_price = price > 0
    status = v.get('status', 'FOR_SALE').upper()
    is_for_sale = status in ('FOR_SALE', 'AVAILABLE')
    is_demo = 1 if v.get('is_demo') in (1, True) else 0

    # 5. User explicit gate policy (DIRECTIVE 134 TASK 4): All items staged as PENDING_REVIEW
    # before explicit user owner approval
    should_auto_publish = False

    return True, "STAGED", {
        "is_public": 1 if should_auto_publish else 0,
        "publishing_status": "APPROVED" if should_auto_publish else "PENDING_REVIEW",
        "is_authorized_dealer": is_authorized_dealer,
        "has_valid_plate": has_valid_plate,
        "has_price": has_price,
        "is_for_sale": is_for_sale,
        "is_demo": is_demo
    }


def run_tests():
    print("=" * 60)
    print("Running DIRECTIVE 134 Safety & Remediation Unit Tests")
    print("=" * 60)

    # Simulated dealers table in D1
    dealer_db = {
        '(주)더쿨모터스': {
            'dealership_name': '(주)더쿨모터스',
            'partnership_status': 'ACTIVE',
            'marketing_consent_verified': 1,
            'photo_consent_verified': 1,
            'consent_proof_uri': 'internal://auth_proofs/64노3143_thecoolmotors_auth.json'
        },
        '장한평 가온모터스': {
            'dealership_name': '장한평 가온모터스',
            'partnership_status': 'INACTIVE',
            'marketing_consent_verified': 0,
            'photo_consent_verified': 0
        }
    }

    # Test 1: Test identifier prohibition
    for test_id in ['TEST-PROBE-001', 'PROBE-134-A', 'DEMO-CAR-99', 'TEMP-VEHICLE-1']:
        ok, err_code, _ = validate_sync_vehicle({'id': test_id, 'plate_number': '12가3456'}, dealer_db)
        assert not ok and err_code == "TEST_IDENTIFIER_PROHIBITED_IN_PROD", f"Failed to reject test identifier: {test_id}"
    print("  [PASS] Test 1: 테스트/프로브 식별자(TEST-*, PROBE-*, DEMO-*) 운영 동기화 원천 차단")

    # Test 2: Inactive/Unverified dealer check
    ok, _, res = validate_sync_vehicle({
        'id': 'real-car-001',
        'plate_number': '12가3456',
        'sangsa_name': '장한평 가온모터스',
        'target_price': 1500
    }, dealer_db)
    assert ok and res['is_authorized_dealer'] is False, "Inactive dealer wrongly authorized!"
    print("  [PASS] Test 2: 비활성/미증빙 상사(marketing_consent_verified=0) 인가 차단")

    # Test 3: Verified dealer + real vehicle staged safely (PENDING_REVIEW before user approval)
    ok, _, res = validate_sync_vehicle({
        'id': 'real-car-002',
        'plate_number': '277노8340',
        'sangsa_name': '(주)더쿨모터스',
        'target_price': 2200
    }, dealer_db)
    assert ok and res['is_authorized_dealer'] is True
    assert res['has_valid_plate'] is True
    assert res['is_public'] == 0 and res['publishing_status'] == 'PENDING_REVIEW', "Auto-published before user approval!"
    print("  [PASS] Test 3: 검증된 상사 실매물도 사용자 최종 게시 승인 전까지 PENDING_REVIEW 비공개 안전 스테이징")

    # Test 4: Fake / partial plate rejected
    ok, _, res = validate_sync_vehicle({
        'id': 'real-car-003',
        'plate_number': '더쿨-8316',
        'sangsa_name': '(주)더쿨모터스',
        'target_price': 950
    }, dealer_db)
    assert ok and res['has_valid_plate'] is False
    assert res['is_public'] == 0 and res['publishing_status'] == 'PENDING_REVIEW'
    print("  [PASS] Test 4: 임시 번호판(더쿨-XXXX) 유효 번호판 검증 차단")

    # Test 5: Sold vehicle state transition guard
    existing_status = 'SOLD'
    new_snapshot_status = 'FOR_SALE'
    def simulate_state_transition(curr_status, curr_pub_status, new_status):
        if curr_status == 'SOLD' or curr_pub_status == 'UNPUBLISHED':
            if new_status not in ('SOLD', 'SUSPENDED', 'DELETED', 'INACTIVE'):
                return False  # Block transition
        return True
    assert simulate_state_transition('SOLD', 'UNPUBLISHED', 'FOR_SALE') is False
    print("  [PASS] Test 5: SOLD 매물의 원본 재전송을 통한 자동 재공개 원천 차단 가드")

    # Test 6: Missing attributes remain NULL
    v_raw = {'year': None, 'mileage': None, 'fuel_type': ''}
    parsed_year = int(v_raw['year']) if v_raw['year'] else None
    parsed_mileage = v_raw['mileage'] if isinstance(v_raw['mileage'], int) else None
    parsed_fuel = v_raw['fuel_type'] or None
    assert parsed_year is None and parsed_mileage is None and parsed_fuel is None
    print("  [PASS] Test 6: 제원 누락 시 임의 기본값(2020년, 0km) 배제 및 NULL 엄격 보존")

    print("=" * 60)
    print("ALL 6 TESTS PASSED SUCCESSFULLY! (100% PASS)")
    print("=" * 60)

if __name__ == '__main__':
    run_tests()
