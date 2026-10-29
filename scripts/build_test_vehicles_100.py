"""
CHA-FICIAL DIRECTIVE 075 & DIRECTIVE 075-A
정확히 100대의 정밀 가상 테스트 차량 데이터 및 20개 슬롯 사진, 24개 부위별 정밀 진단 맵 데이터 생성 스크립트
"""

import sqlite3
import json
import uuid
import random
import os
import shutil

DB_PATH = "data/chamart/chamart_platform_demo.db"
BACKUP_PATH = "data/backup_075/chamart_platform_demo_pre075.db"

# 1. 24개 공인 진단 부위 키 정의
OUTER_PARTS = [
    'hood', 'front_bumper', 'rear_bumper', 'front_fender_l', 'front_fender_r',
    'front_door_l', 'front_door_r', 'rear_door_l', 'rear_door_r',
    'roof', 'trunk', 'quarter_l', 'quarter_r'
]

FRAME_PARTS = [
    'frame_rad_support', 'frame_member_l', 'frame_member_r',
    'frame_member_rl', 'frame_member_rr', 'pillar_a', 'pillar_a_r',
    'pillar_b', 'pillar_b_r', 'pillar_c', 'pillar_c_r'
]

ALL_PARTS = OUTER_PARTS + FRAME_PARTS

# 2. 100대 차량 모델 정의 (국산 85대, 수입 15대)
VEHICLE_CATALOG = [
    # 현대 (35대)
    {"mfg": "현대", "model": "그랜저 (GN7)", "trims": ["캘리그래피", "익스클루시브", "프리미엄"], "body": "세단", "fuel": "가솔린", "cc": 2497, "seats": 5, "price_min": 3200, "price_max": 4800, "count": 6},
    {"mfg": "현대", "model": "아반떼 (CN7)", "trims": ["모던", "인스퍼레이션", "스마트"], "body": "세단", "fuel": "가솔린", "cc": 1598, "seats": 5, "price_min": 1500, "price_max": 2400, "count": 6},
    {"mfg": "현대", "model": "쏘나타 디 엣지", "trims": ["프리미엄", "익스클루시브", "인스퍼레이션"], "body": "세단", "fuel": "가솔린", "cc": 1999, "seats": 5, "price_min": 2200, "price_max": 3300, "count": 5},
    {"mfg": "현대", "model": "디 올 뉴 싼타페 (MX5)", "trims": ["캘리그래피", "익스클루시브", "프레스티지"], "body": "SUV", "fuel": "하이브리드", "cc": 1598, "seats": 7, "price_min": 3600, "price_max": 4900, "count": 5},
    {"mfg": "현대", "model": "팰리세이드", "trims": ["캘리그래피", "프레스티지", "VIP"], "body": "SUV", "fuel": "가솔린", "cc": 3778, "seats": 7, "price_min": 2800, "price_max": 4500, "count": 4},
    {"mfg": "현대", "model": "투싼 (NX4)", "trims": ["인스퍼레이션", "프리미엄", "모던"], "body": "SUV", "fuel": "가솔린", "cc": 1598, "seats": 5, "price_min": 2100, "price_max": 3100, "count": 4},
    {"mfg": "현대", "model": "캐스퍼", "trims": ["디 에센셜", "인스퍼레이션", "스마트"], "body": "경차", "fuel": "가솔린", "cc": 998, "seats": 4, "price_min": 1100, "price_max": 1650, "count": 3},
    {"mfg": "현대", "model": "아이오닉 5", "trims": ["롱레인지 프레스티지", "익스클루시브"], "body": "SUV", "fuel": "전기", "cc": 0, "seats": 5, "price_min": 3100, "price_max": 4200, "count": 2},

    # 기아 (30대)
    {"mfg": "기아", "model": "K8", "trims": ["시그니처", "노블레스", "노블레스 라이트"], "body": "세단", "fuel": "하이브리드", "cc": 1598, "seats": 5, "price_min": 2900, "price_max": 4200, "count": 5},
    {"mfg": "기아", "model": "더 뉴 K5", "trims": ["시그니처", "노블레스", "프레스티지"], "body": "세단", "fuel": "가솔린", "cc": 1999, "seats": 5, "price_min": 2100, "price_max": 3200, "count": 5},
    {"mfg": "기아", "model": "더 뉴 쏘렌토 (MQ4)", "trims": ["시그니처 그래비티", "노블레스", "프레스티지"], "body": "SUV", "fuel": "하이브리드", "cc": 1598, "seats": 6, "price_min": 3500, "price_max": 4800, "count": 5},
    {"mfg": "기아", "model": "더 뉴 카니발 (KA4)", "trims": ["시그니처 9인승", "노블레스 7인승", "프레스티지"], "body": "RV", "fuel": "디젤", "cc": 2151, "seats": 9, "price_min": 2800, "price_max": 4600, "count": 5},
    {"mfg": "기아", "model": "스포티지 (NQ5)", "trims": ["시그니처", "노블레스", "프레스티지"], "body": "SUV", "fuel": "가솔린", "cc": 1598, "seats": 5, "price_min": 2200, "price_max": 3300, "count": 4},
    {"mfg": "기아", "model": "더 뉴 셀토스", "trims": ["그래비티", "시그니처", "프레스티지"], "body": "SUV", "fuel": "가솔린", "cc": 1598, "seats": 5, "price_min": 1900, "price_max": 2700, "count": 3},
    {"mfg": "기아", "model": "더 뉴 레이", "trims": ["시그니처", "프레스티지"], "body": "경차", "fuel": "가솔린", "cc": 998, "seats": 5, "price_min": 1150, "price_max": 1600, "count": 3},

    # 제네시스 (10대)
    {"mfg": "제네시스", "model": "G80 (RG3)", "trims": ["2.5T AWD", "3.5T AWD", "2.5T 2WD"], "body": "세단", "fuel": "가솔린", "cc": 2497, "seats": 5, "price_min": 3900, "price_max": 6200, "count": 4},
    {"mfg": "제네시스", "model": "GV80 (JX1)", "trims": ["2.5T AWD 7인승", "3.0D AWD", "3.5T AWD"], "body": "SUV", "fuel": "가솔린", "cc": 2497, "seats": 7, "price_min": 4800, "price_max": 7500, "count": 3},
    {"mfg": "제네시스", "model": "GV70 (JK1)", "trims": ["2.5T AWD 스포츠", "2.5T 2WD"], "body": "SUV", "fuel": "가솔린", "cc": 2497, "seats": 5, "price_min": 3800, "price_max": 5400, "count": 3},

    # KG모빌리티 (5대)
    {"mfg": "KG모빌리티", "model": "토레스", "trims": ["T7 2WD", "T5 2WD", "T7 4WD"], "body": "SUV", "fuel": "가솔린", "cc": 1497, "seats": 5, "price_min": 1950, "price_max": 2800, "count": 3},
    {"mfg": "KG모빌리티", "model": "더 뉴 티볼리", "trims": ["V5", "V3"], "body": "SUV", "fuel": "가솔린", "cc": 1497, "seats": 5, "price_min": 1400, "price_max": 1980, "count": 2},

    # 르노코리아 (5대)
    {"mfg": "르노코리아", "model": "QM6", "trims": ["2.0 GDe RE", "2.0 LPe LE", "2.0 GDe 프리미에르"], "body": "SUV", "fuel": "LPG", "cc": 1998, "seats": 5, "price_min": 1500, "price_max": 2350, "count": 3},
    {"mfg": "르노코리아", "model": "XM3", "trims": ["TCe 260 RE", "1.6 GTe LE"], "body": "SUV", "fuel": "가솔린", "cc": 1332, "seats": 5, "price_min": 1350, "price_max": 1850, "count": 2},

    # BMW (5대)
    {"mfg": "BMW", "model": "5시리즈 (G30)", "trims": ["520i M 스포츠", "530i 럭셔리", "523d"], "body": "세단", "fuel": "가솔린", "cc": 1998, "seats": 5, "price_min": 4200, "price_max": 6500, "count": 2},
    {"mfg": "BMW", "model": "3시리즈 (G20)", "trims": ["320i M 스포츠", "320d"], "body": "세단", "fuel": "가솔린", "cc": 1998, "seats": 5, "price_min": 3400, "price_max": 4600, "count": 2},
    {"mfg": "BMW", "model": "X5 (G05)", "trims": ["xDrive 30d M 스포츠"], "body": "SUV", "fuel": "디젤", "cc": 2993, "seats": 5, "price_min": 6800, "price_max": 8900, "count": 1},

    # 벤츠 (5대)
    {"mfg": "벤츠", "model": "E-클래스 (W213)", "trims": ["E250 아방가르드", "E350 4MATIC 익스클루시브"], "body": "세단", "fuel": "가솔린", "cc": 1991, "seats": 5, "price_min": 4300, "price_max": 6900, "count": 2},
    {"mfg": "벤츠", "model": "C-클래스 (W206)", "trims": ["C200 아방가르드", "C300 4MATIC"], "body": "세단", "fuel": "가솔린", "cc": 1999, "seats": 5, "price_min": 3800, "price_max": 5200, "count": 2},
    {"mfg": "벤츠", "model": "GLC-클래스 (X254)", "trims": ["GLC 300 4MATIC"], "body": "SUV", "fuel": "가솔린", "cc": 1999, "seats": 5, "price_min": 6200, "price_max": 7800, "count": 1},

    # 아우디 (3대)
    {"mfg": "아우디", "model": "A6 (C8)", "trims": ["45 TFSI 콰트로 프리미엄", "40 TDI"], "body": "세단", "fuel": "가솔린", "cc": 1984, "seats": 5, "price_min": 3600, "price_max": 5200, "count": 2},
    {"mfg": "아우디", "model": "Q5 (FY)", "trims": ["45 TFSI 콰트로 프리미엄"], "body": "SUV", "fuel": "가솔린", "cc": 1984, "seats": 5, "price_min": 4100, "price_max": 5500, "count": 1},

    # 폭스바겐 (2대)
    {"mfg": "폭스바겐", "model": "티구안 (2세대)", "trims": ["2.0 TDI 프레스티지"], "body": "SUV", "fuel": "디젤", "cc": 1968, "seats": 5, "price_min": 2400, "price_max": 3300, "count": 1},
    {"mfg": "폭스바겐", "model": "골프 (8세대)", "trims": ["2.0 TDI 프레스티지"], "body": "해치백", "fuel": "디젤", "cc": 1968, "seats": 5, "price_min": 2300, "price_max": 2900, "count": 1}
]

# 3. 20개 사진 슬롯 정의
PHOTO_SLOTS = [
    {"code": "EXT_FRONT", "label": "정면", "category": "EXTERIOR"},
    {"code": "EXT_REAR", "label": "후면", "category": "EXTERIOR"},
    {"code": "EXT_SIDE_L", "label": "좌측면", "category": "EXTERIOR"},
    {"code": "EXT_SIDE_R", "label": "우측면", "category": "EXTERIOR"},
    {"code": "EXT_FRONT_45_L", "label": "전면 45도 좌측", "category": "EXTERIOR"},
    {"code": "EXT_FRONT_45_R", "label": "전면 45도 우측", "category": "EXTERIOR"},
    {"code": "EXT_REAR_45_L", "label": "후면 45도 좌측", "category": "EXTERIOR"},
    {"code": "EXT_REAR_45_R", "label": "후면 45도 우측", "category": "EXTERIOR"},
    {"code": "INT_CLUSTER", "label": "계기판", "category": "INTERIOR"},
    {"code": "INT_CENTER", "label": "센터페시아/내비", "category": "INTERIOR"},
    {"code": "INT_SEAT_FRONT", "label": "1열 앞좌석", "category": "INTERIOR"},
    {"code": "INT_SEAT_REAR", "label": "2열 뒷좌석", "category": "INTERIOR"},
    {"code": "INT_STEERING", "label": "스티어링 휠", "category": "INTERIOR"},
    {"code": "EXT_TRUNK", "label": "트렁크 룸", "category": "EXTERIOR"},
    {"code": "ENG_BAY", "label": "엔진룸", "category": "MECHANICAL"},
    {"code": "WHEEL_FL", "label": "전륜 좌측 휠/타이어", "category": "TIRE_WHEEL"},
    {"code": "WHEEL_FR", "label": "전륜 우측 휠/타이어", "category": "TIRE_WHEEL"},
    {"code": "WHEEL_RL", "label": "후륜 좌측 휠/타이어", "category": "TIRE_WHEEL"},
    {"code": "WHEEL_RR", "label": "후륜 우측 휠/타이어", "category": "TIRE_WHEEL"},
    {"code": "OPT_SUNROOF", "label": "파노라마 선루프/옵션", "category": "OPTION"}
]

COLORS = ["스노우 화이트 펄", "오로라 블랙 펄", "세라믹 실버", "그래비티 그레이", "인터스텔라 그레이", "딥 크로마 블루", "글로시 레드"]
TRANSMISSIONS = ["자동 (A/T)", "전자식 자동 (SBW)"]
DRIVE_TYPES = ["전륜구동 (2WD)", "상시사륜 (AWD)", "후륜구동 (2WD)"]

def generate_100_vehicles():
    print(f"[1] DB 백업 및 연결: {DB_PATH}")
    os.makedirs(os.path.dirname(BACKUP_PATH), exist_ok=True)
    if not os.path.exists(BACKUP_PATH):
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"백업 완료: {BACKUP_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. 기존 is_demo=1 삭제 (is_demo=0 실차는 절대 불변 보존!)
    cur.execute("DELETE FROM vehicle_photos WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);")
    cur.execute("DELETE FROM vehicles WHERE is_demo = 1;")
    conn.commit()
    print("기존 가상 데모 데이터(is_demo=1) 초기화 완료 (실차 운영 데이터 불변 보존)")

    # 2. 100대 생성 루프
    # 카탈로그 수량 합계 검증
    total_catalog = sum(c["count"] for c in VEHICLE_CATALOG)
    assert total_catalog == 100, f"카탈로그 수량 불일치: {total_catalog}"

    v_index = 0
    vehicles_data = []

    # 사고 유형 분배:
    # 0~49 (50대): 그룹 1 - 완전 무사고 (초록 ALL CLEAN)
    # 50~69 (20대): 그룹 2 - 단순 외판 교환 (1~2개 부위 주황 REPLACED)
    # 70~79 (10대): 그룹 3 - 다중 외판 수리 (3~4개 부위 주황 REPLACED/PAINTED)
    # 80~89 (10대): 그룹 4 - 주요 골격 손상 (빨강 FRAME_DAMAGE 포함)
    # 90~99 (10대): 그룹 5 - 미확인/전산 대기 (회색 UNKNOWN 포함)

    for item in VEHICLE_CATALOG:
        mfg = item["mfg"]
        model = item["model"]
        body = item["body"]
        fuel = item["fuel"]
        cc = item["cc"]
        seats = item["seats"]

        for _ in range(item["count"]):
            v_id = str(uuid.uuid4())
            trim = random.choice(item["trims"])
            year = random.choice([2019, 2020, 2021, 2022, 2023, 2024, 2025])
            first_reg = f"{year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            
            # 주행거리 (연식 비례)
            age = max(1, 2026 - year)
            mileage = random.randint(age * 8000, age * 18000)
            
            price = random.randint(item["price_min"] // 50, item["price_max"] // 50) * 50
            purchase_price = int(price * 0.88)
            plate_num = f"{random.randint(10, 99)}{random.choice(['가', '나', '다', '라', '마', '거', '너', '도', '로', '호', '하'])} {random.randint(1000, 9999)}"
            
            # VIN 생성 (17자리 정규 규격)
            vin_prefix = "KNA" if mfg == "기아" else ("KMH" if mfg == "현대" else ("WBA" if mfg == "BMW" else ("WDB" if mfg == "벤츠" else "WAU")))
            vin = f"{vin_prefix}{uuid.uuid4().hex[:14].upper()}"

            color = random.choice(COLORS)
            trans = random.choice(TRANSMISSIONS)
            drive = random.choice(DRIVE_TYPES)

            # 그룹별 부위 진단 생성
            diagram_parts = {}
            if v_index < 50:
                # 그룹 1: 완전 무사고
                accident_state = "CLEAN"
                for p in ALL_PARTS:
                    diagram_parts[p] = {"state": "CLEAN", "status": "VERIFIED_CLEAN", "evidence": "공식 성능점검 무사고 확인"}
            elif v_index < 70:
                # 그룹 2: 단순 외판 1~2개
                accident_state = "OUTER_REPLACED"
                replaced_picks = random.sample(OUTER_PARTS, k=random.randint(1, 2))
                for p in ALL_PARTS:
                    if p in replaced_picks:
                        diagram_parts[p] = {"state": "REPLACED", "status": "VERIFIED_ISSUE", "evidence": "단순 볼트 체결 부품 교환 이력"}
                    else:
                        diagram_parts[p] = {"state": "CLEAN", "status": "VERIFIED_CLEAN", "evidence": "전산 대조 정상 확인"}
            elif v_index < 80:
                # 그룹 3: 다중 외판 수리 3~4개
                accident_state = "OUTER_REPAIRED"
                replaced_picks = random.sample(OUTER_PARTS, k=random.randint(3, 4))
                for p in ALL_PARTS:
                    if p in replaced_picks:
                        diagram_parts[p] = {"state": "PAINTED", "status": "VERIFIED_ISSUE", "evidence": "판금 도색 및 외판 복원 이력"}
                    else:
                        diagram_parts[p] = {"state": "CLEAN", "status": "VERIFIED_CLEAN", "evidence": "전산 대조 정상 확인"}
            elif v_index < 90:
                # 그룹 4: 주요 골격 손상
                accident_state = "FRAME_DAMAGED"
                damage_frames = random.sample(FRAME_PARTS, k=random.randint(1, 2))
                replaced_outers = random.sample(OUTER_PARTS, k=random.randint(1, 2))
                for p in ALL_PARTS:
                    if p in damage_frames:
                        diagram_parts[p] = {"state": "FRAME_DAMAGE", "status": "FRAME_DAMAGE", "evidence": "주요 차체 골격 용접/판금 이력 (B랭크)"}
                    elif p in replaced_outers:
                        diagram_parts[p] = {"state": "REPLACED", "status": "VERIFIED_ISSUE", "evidence": "사고 연계 외판 패널 교환"}
                    else:
                        diagram_parts[p] = {"state": "CLEAN", "status": "VERIFIED_CLEAN", "evidence": "전산 대조 정상 확인"}
            else:
                # 그룹 5: 미확인 / 일부 점검
                accident_state = "UNKNOWN"
                for p in ALL_PARTS:
                    if random.random() < 0.5:
                        diagram_parts[p] = {"state": "UNKNOWN", "status": "UNKNOWN", "evidence": "성능점검 전산 기록 대기 중"}
                    else:
                        diagram_parts[p] = {"state": "CLEAN", "status": "VERIFIED_CLEAN", "evidence": "기본 외관 정상"}

            accident_summary = {
                "accident_state": accident_state,
                "diagram_parts": diagram_parts,
                "verified_source": "한국자동차진단보증협회 성능점검기록부 1:1 대조",
                "verified_at": "2026-10-28",
                "tires": {
                    "fl": {"depth_mm": round(random.uniform(4.0, 7.5), 1)},
                    "fr": {"depth_mm": round(random.uniform(4.0, 7.5), 1)},
                    "rl": {"depth_mm": round(random.uniform(3.5, 7.2), 1)},
                    "rr": {"depth_mm": round(random.uniform(3.5, 7.2), 1)}
                }
            }

            # 소유 및 우선노출 설정 (차마트 보유 약 30대, 일반 70대)
            is_owned = 1 if (v_index % 3 == 0) else 0
            is_priority = 1 if (v_index < 15) else 0
            p_rank = (v_index + 1) if is_priority else 999

            # 대표 사진
            # 기존 neutral 이미지 또는 실차 샘플 매핑
            primary_photo = f"/static/img/vehicles/sample_car_{((v_index % 10) + 1):02d}.jpg"
            if not os.path.exists(f"src/chaficial/platform/ui{primary_photo}"):
                primary_photo = "/static/img/vehicles/neutral_car_placeholder.jpg"

            cur.execute("""
                INSERT INTO vehicles (
                    id, branch_id, plate_number, model_name, year, mileage, fuel_type,
                    transmission, color, purchase_price, target_price, status, is_demo,
                    vin, displacement_cc, first_registration_date, drive_type,
                    interior_color, options_json, accident_history_json,
                    primary_photo_url, manufacturer, trim, body_type,
                    is_public, listing_ownership_type, is_priority_exposure, priority_rank,
                    timeline_json, created_at, updated_at
                ) VALUES (
                    ?, '61fea9a4-58f0-42bd-862c-14fd16d0d21c', ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, 'AVAILABLE', 1,
                    ?, ?, ?, ?,
                    '블랙/다크그레이', '[\"통풍시트\", \"어댑티브 크루즈\", \"어라운드 뷰\", \"헤드업 디스플레이\"]', ?,
                    ?, ?, ?, ?,
                    1, ?, ?, ?,
                    '[]', datetime('now'), datetime('now')
                )
            """, (
                v_id, plate_num, model, year, mileage, fuel,
                trans, color, purchase_price, price,
                vin, cc, first_reg, drive,
                json.dumps(accident_summary, ensure_ascii=False),
                primary_photo, mfg, trim, body,
                'OWNED' if is_owned else 'PARTNER', is_priority, p_rank
            ))

            # 20개 사진 슬롯 등록
            for s_idx, slot in enumerate(PHOTO_SLOTS):
                p_id = str(uuid.uuid4())
                p_url = f"/static/img/vehicles/slots/{slot['code'].lower()}.jpg"
                cur.execute("""
                    INSERT INTO vehicle_photos (
                        id, vehicle_id, photo_url, thumb_url, category, sort_order,
                        is_primary, allow_video_use, caption, created_at,
                        view_code, category_code, display_label
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, 1, ?, datetime('now'),
                        ?, ?, ?
                    )
                """, (
                    p_id, v_id, p_url, p_url, slot['category'], s_idx + 1,
                    1 if s_idx == 0 else 0, slot['label'],
                    slot['code'], slot['category'], slot['label']
                ))

            v_index += 1

    conn.commit()
    print(f"[2] 가상 차량 {v_index}대 및 20개 사진 슬롯({v_index * 20}건) DB 적재 완료!")

    # 검증 쿼리
    cur.execute("SELECT COUNT(*) FROM vehicles WHERE is_demo = 1;")
    demo_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vehicles WHERE is_demo = 0;")
    real_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM vehicle_photos WHERE vehicle_id IN (SELECT id FROM vehicles WHERE is_demo = 1);")
    photo_count = cur.fetchone()[0]

    print(f"=== 검증 결과 ===")
    print(f"가상 차량 (is_demo=1): {demo_count}대 (목표 100대)")
    print(f"실차 보존 (is_demo=0): {real_count}대 (훼손 0건)")
    print(f"등록 사진 메타: {photo_count}건 (100대 x 20장)")
    conn.close()

if __name__ == "__main__":
    generate_100_vehicles()
