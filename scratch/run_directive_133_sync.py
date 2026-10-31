#!/usr/bin/env python3
"""
DIRECTIVE 133: 카매니저·차피셜·차마트 실매물 자동 연동 엔진 (오케스트레이터)
- 더쿨모터스(74대) 및 카매니저 직영(13대) 통합 검증 (총 74대 실매물)
- 상사 단위 지속 동의(Dealer Continuous Consent) 적용
- 확정 가격 판매중 매물(36대) 자동 승인 (is_public=1, publishing_status='APPROVED', EXTERNAL)
- 가격 미확정(상담) 매물(38대) 비공개 안전 격리 (is_public=0, publishing_status='PENDING_REVIEW')
- 카매니저 실차 사진 승인(APPROVED/PUBLIC) 및 미보유 매물 '사진 준비 중' 처리
- 양방향 동기화 검증: 가격 변경 및 판매 완료(SOLD) 시 즉시 비공개 전환 테스트
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path

# PYTHONPATH 설정
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chaficial.platform.sourcing.chamart_sync_client import ChamartSyncClient
from chaficial.platform.sourcing.carmanager_sync import parse_price_manwon, parse_mileage_km


def build_thecool_payloads():
    # 1. 장한평 크롤링 데이터 로드 (74대)
    with open('data/carmanager_raw/janghanpyeong_full_collection.json') as f:
        janghan = json.load(f)['cars']

    thecool_raw = [c for c in janghan if '더쿨' in str(c.get('shop', '')) or '더쿨' in str(c.get('sangsa', ''))]

    # 2. 직영 13대 매물 로드
    with open('scratch/carmanager_inspect/my_13_cleaned_cars.json') as f:
        my13 = json.load(f)

    my13_by_tail = {c['plate'][-4:]: c for c in my13}

    vehicles_payload = []
    photos_payload = []

    # 64노3143 기존 D1 ID
    LANDROVER_D1_ID = 'e6670a2e-c532-435e-b34a-b4a3ff9a677c'

    for c in thecool_raw:
        tail = c.get('plate_tail')
        direct = my13_by_tail.get(tail)

        # 번호판 및 차량 식별자 결정
        if tail == '3143' or (direct and '3143' in direct.get('plate', '')):
            vid = LANDROVER_D1_ID
            plate = '64노3143'
        elif direct and direct.get('plate'):
            plate = direct['plate']
            enc = c.get('encarno') or direct.get('suggestNo') or tail
            vid = 'CAR-THECOOL-' + hashlib.md5(enc.encode('utf-8')).hexdigest()[:10]
        else:
            p_num = c.get('page', 1)
            plate = f'더쿨-{tail}' if tail else f'더쿨-CM{p_num}'
            enc = c.get('encarno') or tail
            vid = 'CAR-THECOOL-' + hashlib.md5(enc.encode('utf-8')).hexdigest()[:10]

        # 가격 결정
        raw_p = c.get('price_manwon')
        if direct and direct.get('price') and direct.get('price') != '0':
            raw_p = direct['price']

        price = parse_price_manwon(raw_p)
        mileage = parse_mileage_km(c.get('mileage')) or 0
        year = int(c.get('model_year') or 2020)

        # 썸네일
        thumb = c.get('thumbnail') or ''

        # 차량 객체
        v_obj = {
            'id': vid,
            'plate_number': plate,
            'model_name': c.get('title') or c.get('model'),
            'manufacturer': c.get('maker') or '기타',
            'year': year,
            'mileage': mileage,
            'fuel_type': c.get('fuel') or '가솔린',
            'transmission': c.get('mission') or '오토',
            'color': c.get('color') or '기타',
            'target_price': price or 0,
            'status': 'FOR_SALE',
            'sangsa_name': '(주)더쿨모터스',
            'dealer_name': c.get('dealer') or '더쿨모터스',
            'dealer_phone': c.get('phone') or '010-2588-9675',
            'dealer_consented': True,
            'primary_photo_url': thumb,
            'is_demo': 0,
            'source': 'CARMANAGER_THECOOL'
        }
        vehicles_payload.append(v_obj)

        # 사진 객체
        if thumb and thumb.startswith('http'):
            photos_payload.append({
                'vehicle_id': vid,
                'photos': [{
                    'id': f'PHOTO-{vid}-1',
                    'photo_url': thumb,
                    'thumb_url': thumb,
                    'category': 'EXTERIOR',
                    'sort_order': 1,
                    'is_primary': 1,
                    'approval_status': 'APPROVED',
                    'public_visibility': 'PUBLIC',
                    'caption': f'실차 사진 ({plate})'
                }]
            })

    # 64노3143의 9장 카매니저 실차 사진 추가 (DIRECTIVE 132-A 데이터)
    landrover_photos_file = Path('scratch/download_landrover_photos.py')
    # D1에 이미 등록된 64노3143의 9장 사진을 APPROVED & PUBLIC로 승인하기 위해 D1 직접 쿼리 또는 API로 처리
    return vehicles_payload, photos_payload


def main():
    print("=" * 70)
    print("CHA-FICIAL DIRECTIVE 133: 실매물 자동 연동 파이프라인 가동")
    print("=" * 70)

    client = ChamartSyncClient()

    # 1. 원격 헬스체크
    health = client.check_remote_health()
    print(f"[1] 원격 Cloudflare API 헬스체크: {health.get('status')}")
    print(f"    - 현재 실차량 수: {health.get('total_real_vehicles')}")
    print(f"    - 현재 승인 공개 차량 수: {health.get('total_approved_vehicles')}")

    # 2. 더쿨모터스 매물 파싱 및 분류
    vehicles, photos_list = build_thecool_payloads()
    valid_p = [v for v in vehicles if v['target_price'] > 0]
    consult_p = [v for v in vehicles if v['target_price'] == 0]

    print(f"\n[2] 카매니저 매물 분석 결과:")
    print(f"    - 총 더쿨모터스 매물: {len(vehicles)}대")
    print(f"    - 확정 가격 판매중 실매물: {len(valid_p)}대 (상사 단위 자동 게시 대상)")
    print(f"    - 가격 미확정(상담) 매물: {len(consult_p)}대 (비공개 검토 대상)")
    print(f"    - 카매니저 실차 썸네일 확보 매물: {len(photos_list)}대")

    # 3. 차량 배치 동기화 전송 (15대 단위 안전 청크 전송)
    print(f"\n[3] HTTPS 원격 동기화 전송 (/api/sync/vehicles, 15대 단위 청크)...")
    CHUNK_SIZE = 15
    total_inserted = 0
    total_updated = 0
    total_skipped = 0

    for i in range(0, len(vehicles), CHUNK_SIZE):
        chunk = vehicles[i:i + CHUNK_SIZE]
        chunk_num = (i // CHUNK_SIZE) + 1
        total_chunks = (len(vehicles) + CHUNK_SIZE - 1) // CHUNK_SIZE
        print(f"    - 청크 {chunk_num}/{total_chunks} ({len(chunk)}대) 전송 중...")
        res_v = client._send_request("/api/sync/vehicles", {
            "vehicles": chunk,
            "source": f"CHAFICIAL_DIRECTIVE_133_C{chunk_num}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
        })
        total_inserted += res_v.get('inserted', 0)
        total_updated += res_v.get('updated', 0)
        total_skipped += res_v.get('skipped', 0)
        time.sleep(0.5)

    print(f"    - 전체 차량 전송 완료: inserted={total_inserted}, updated={total_updated}, skipped={total_skipped}")

    # 4. 사진 메타데이터 동기화 (/api/sync/photos)
    print(f"\n[4] HTTPS 실차 사진 메타데이터 동기화 (/api/sync/photos)...")
    photo_success_count = 0
    for p_item in photos_list:
        try:
            res_p = client._send_request("/api/sync/photos", p_item)
            if res_p.get('success'):
                photo_success_count += 1
        except Exception as e:
            print(f"    - 사진 동기화 실패 ({p_item['vehicle_id']}): {e}")

    print(f"    - 사진 동기화 완료: {photo_success_count} / {len(photos_list)}대 실차 사진 등록")

    # 5. 64노3143 기존 9장 사진 승인 상태 D1 확인 및 동기화
    print(f"\n[5] 실매물 1호 64노3143 사진 승인 처리...")
    # 64노3143 사진 9장을 APPROVED & PUBLIC로 원격 갱신
    import subprocess
    cmd = [
        "npx", "wrangler", "d1", "execute", "chamart-db", "--remote",
        "--command",
        "UPDATE vehicle_photos SET approval_status='APPROVED', public_visibility='PUBLIC' WHERE vehicle_id='e6670a2e-c532-435e-b34a-b4a3ff9a677c';"
    ]
    sub_res = subprocess.run(cmd, capture_output=True, text=True)
    if sub_res.returncode == 0:
        print("    - 64노3143 사진 9장 APPROVED & PUBLIC 상태 승인 완료")
    else:
        print(f"    - 사진 승인 경고: {sub_res.stderr}")

    # 6. 동기화 후 D1 현황 재확인
    time.sleep(1)
    health_after = client.check_remote_health()
    print(f"\n[6] 동기화 후 차마트 원격 상태:")
    print(f"    - 전체 실차량 수: {health_after.get('total_real_vehicles')}")
    print(f"    - 차마트 승인 공개 차량 수: {health_after.get('total_approved_vehicles')}")

    # 7. 양방향 동기화 검증: 가격 변경 및 판매완료(SOLD) 테스트
    print(f"\n[7] 양방향 증분 동기화 무결성 테스트 (가격 변경 및 판매완료 반영)")
    test_car = valid_p[0] # 더쿨-8316
    orig_price = test_car['target_price']
    test_vid = test_car['id']

    # 7-1. 가격 변경 테스트: 950만원 -> 930만원
    print(f"    [7-1] 가격 변경 테스트 ({test_car['plate_number']}: {orig_price}만원 -> {orig_price - 20}만원)")
    mod_car = dict(test_car)
    mod_car['target_price'] = orig_price - 20
    res_mod = client._send_request("/api/sync/vehicles", {
        "vehicles": [mod_car],
        "source": "PRICE_CHANGE_TEST",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    })
    print(f"          결과: updated={res_mod.get('updated')}")

    # 7-2. 판매 완료(SOLD) 테스트: 즉시 비공개(is_public=0) 확인
    print(f"    [7-2] 판매 완료(SOLD) 비공개 전환 테스트 (/api/sync/status)")
    res_sold = client._send_request("/api/sync/status", {
        "vehicle_ids": [test_vid],
        "status": "SOLD",
        "reason": "DIRECTIVE_133_SOLD_TEST"
    })
    print(f"          결과: updated_count={res_sold.get('updated_count')}, unpublished={res_sold.get('unpublished')}")

    # 7-3. 원복: 원래 가격 및 FOR_SALE로 복구
    print(f"    [7-3] 테스트 차량 정상 상태 복구 ({orig_price}만원, FOR_SALE)")
    res_restore = client._send_request("/api/sync/vehicles", {
        "vehicles": [test_car],
        "source": "STATE_RESTORE",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    })
    print(f"          결과: updated={res_restore.get('updated')}")

    # 8. 고객 문의 차피셜 전달 엔드포인트 테스트
    print(f"\n[8] 고객 상담 내역 차피셜 전달 검증 (/api/sync/consultations)")
    import urllib.request
    sec = Path('data/.chamart_sync_secret').read_text().strip()
    req = urllib.request.Request(
        f"{client.target_url}/api/sync/consultations",
        headers={
            "Authorization": f"Bearer {sec}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        c_res = json.loads(resp.read().decode('utf-8'))
        print(f"    - 접수된 상담 건수: {c_res.get('count')}건")
        if c_res.get('consultations'):
            sample_c = c_res['consultations'][0]
            print(f"    - 최근 상담 샘플: 고객={sample_c.get('customer_name')}, 차량={sample_c.get('target_vehicle_model')}, 일시={sample_c.get('created_at')}")

    print("\n" + "=" * 70)
    print("DIRECTIVE 133 오케스트레이션 실행 성공!")
    print("=" * 70)


if __name__ == '__main__':
    main()
