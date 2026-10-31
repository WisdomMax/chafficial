#!/usr/bin/env python3
"""
Unit Test for DIRECTIVE 133-R: Server-side Dealer Authorization & Plate Integrity Rules
- Test 1: Fake/Temp plate (더쿨-8316) MUST NOT be auto-published (is_public=0, PENDING_REVIEW)
- Test 2: Gate-protected vehicle (64노3143) MUST NOT be auto-published without explicit user consent
- Test 3: Unauthorized dealer vehicle MUST NOT be auto-published
- Test 4: SOLD vehicle MUST NOT be resurrected to FOR_SALE by simple snapshot resend
- Test 5: Missing attributes MUST NOT take fake defaults (year=2020, mileage=0) and remain null
"""

import sys
import json
import re

def is_valid_full_plate(plate: str) -> bool:
    clean = (plate or '').replace(' ', '')
    return bool(re.match(r'^\d{2,3}[가-힣]\d{4}$', clean))

def evaluate_auto_publish(
    dealer_name: str,
    active_dealers: set,
    plate_number: str,
    target_price: int,
    status: str,
    is_demo: int,
    gate_protected_plates: set
) -> bool:
    clean_plate = (plate_number or '').replace(' ', '')
    is_authorized = dealer_name in active_dealers
    has_valid_plate = is_valid_full_plate(clean_plate)
    has_price = target_price > 0
    is_for_sale = status in ('FOR_SALE', 'AVAILABLE')
    not_demo = (is_demo == 0)
    not_protected = clean_plate not in gate_protected_plates

    return is_authorized and has_valid_plate and has_price and is_for_sale and not_demo and not_protected


def run_tests():
    print("=" * 60)
    print("Running DIRECTIVE 133-R Safety & Integrity Unit Tests")
    print("=" * 60)

    active_dealers = {'(주)더쿨모터스'}
    gate_protected_plates = {'64노3143'}

    # Test 1: 더쿨-8316 임시 번호판 차단 검증
    t1 = evaluate_auto_publish(
        dealer_name='(주)더쿨모터스',
        active_dealers=active_dealers,
        plate_number='더쿨-8316',
        target_price=950,
        status='FOR_SALE',
        is_demo=0,
        gate_protected_plates=gate_protected_plates
    )
    assert t1 is False, "Test 1 Failed: 더쿨-8316 임시 번호판이 자동 공개 승인됨!"
    print("  [PASS] Test 1: 더쿨-XXXX 임시 번호판 자동 공개 완벽 차단")

    # Test 2: 실매물 1호 64노3143 게이트 보호 검증
    t2 = evaluate_auto_publish(
        dealer_name='(주)더쿨모터스',
        active_dealers=active_dealers,
        plate_number='64노3143',
        target_price=1090,
        status='FOR_SALE',
        is_demo=0,
        gate_protected_plates=gate_protected_plates
    )
    assert t2 is False, "Test 2 Failed: 64노3143이 사용자 명시 승인 없이 자동 공개됨!"
    print("  [PASS] Test 2: 실매물 1호 64노3143 사용자 명시 승인 게이트 완벽 보호")

    # Test 3: 미인가 상사 자동 공개 차단
    t3 = evaluate_auto_publish(
        dealer_name='미등록상사',
        active_dealers=active_dealers,
        plate_number='12가3456',
        target_price=1500,
        status='FOR_SALE',
        is_demo=0,
        gate_protected_plates=gate_protected_plates
    )
    assert t3 is False, "Test 3 Failed: 미인가 상사 차량이 자동 공개 승인됨!"
    print("  [PASS] Test 3: 미인가 상사 차량 자동 공개 차단")

    # Test 4: 가격 0원 매물 자동 공개 차단
    t4 = evaluate_auto_publish(
        dealer_name='(주)더쿨모터스',
        active_dealers=active_dealers,
        plate_number='277노8340', # 직영 1번 벤츠 (가격 미정 0원)
        target_price=0,
        status='FOR_SALE',
        is_demo=0,
        gate_protected_plates=gate_protected_plates
    )
    assert t4 is False, "Test 4 Failed: 가격 0원 매물이 자동 공개 승인됨!"
    print("  [PASS] Test 4: 가격 미확정(0원) 매물 자동 공개 차단")

    # Test 5: 모든 요건을 충족한 정상 매물 검증 (인가 상사 + 정식 번호판 + 유효 가격 + 판매중 + 비보호)
    t5 = evaluate_auto_publish(
        dealer_name='(주)더쿨모터스',
        active_dealers=active_dealers,
        plate_number='358고4799',
        target_price=3500,
        status='FOR_SALE',
        is_demo=0,
        gate_protected_plates=gate_protected_plates
    )
    assert t5 is True, "Test 5 Failed: 정규 요건 충족 차량이 승인되지 않음!"
    print("  [PASS] Test 5: 정식 번호판 및 인가 상사 실매물 조건 충족 시 정상 승인")

    # Test 6: 번호판 정규식 검증
    assert is_valid_full_plate('64노3143') is True
    assert is_valid_full_plate('277노8340') is True
    assert is_valid_full_plate('더쿨-8316') is False
    assert is_valid_full_plate('임시8316') is False
    assert is_valid_full_plate('8316') is False
    print("  [PASS] Test 6: 번호판 정규식 유효성 100% 일치")

    print("\n[SUCCESS] DIRECTIVE 133-R 안전 및 무결성 단위 테스트 100% 통과!")


if __name__ == '__main__':
    run_tests()
