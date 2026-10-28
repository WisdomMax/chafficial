#!/usr/bin/env python3
"""
CHA-FICIAL DIRECTIVE 070: 100대 가상 UI Fixture 생성 스크립트
- 아반떼(35), 레이(25), 모닝(25), 캐스퍼(10), K3(5) 총 100대
- 엔카 기준 정보 구조(제조사, 차종, 트림, 연식, 주행거리, 정찰가, 옵션, 상세 제원) 완비
- 운영 DB와 완전 격리된 순수 JSON Fixture
"""

import json
import random
from pathlib import Path

# 재현성을 위한 고정 시드
rng = random.Random(20261029)

MODELS = [
    ("현대", "아반떼", 35, 2018, 2025, 650, 2600, ["스마트", "모던", "인스퍼레이션"]),
    ("기아", "레이", 25, 2018, 2025, 450, 1900, ["스탠다드", "프레스티지", "시그니처"]),
    ("기아", "모닝", 25, 2018, 2025, 350, 1700, ["트렌디", "프레스티지", "시그니처"]),
    ("현대", "캐스퍼", 10, 2022, 2025, 900, 2200, ["스마트", "모던", "인스퍼레이션"]),
    ("기아", "K3", 5, 2019, 2024, 650, 2100, ["트렌디", "프레스티지", "시그니처"]),
]

COLORS = ["화이트", "블랙", "실버", "그레이", "블루", "레드", "베이지", "카키"]

DEFAULT_OPTIONS = [
    {"name": "스마트키/버튼시동", "category": "편의/안전"},
    {"name": "내비게이션(정품)", "category": "미디어"},
    {"name": "후방카메라/감지센서", "category": "안전"},
    {"name": "앞좌석 열선시트", "category": "시트"},
    {"name": "앞좌석 통풍시트", "category": "시트"},
    {"name": "차선이탈 경고/유지", "category": "주행보조"},
    {"name": "블루투스 핸즈프리", "category": "미디어"},
    {"name": "가죽 스티어링 휠(열선)", "category": "편의"},
    {"name": "LED 헤드램프", "category": "외관/휠"},
    {"name": "하이패스/ECM 룸미러", "category": "편의"},
]

def main():
    manifest_path = Path("reports/ui_fixtures/photo_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    vehicles = []

    for maker, model, count, y_min, y_max, p_min, p_max, trims in MODELS:
        photos = manifest.get(model, [])
        for _ in range(count):
            year = rng.randint(y_min, y_max)
            age = 2026 - year

            # 연식에 따른 자연스러운 주행거리 (3,000 ~ 170,000km)
            mileage = rng.randint(
                max(3000, age * 4000),
                min(170000, age * 18000 + 35000)
            )

            price = rng.randint(p_min, p_max)
            vehicle_id = f"UI-{len(vehicles) + 1:04d}"

            # 사진 매핑
            if photos:
                primary_photo = photos[len(vehicles) % len(photos)]
                gallery_photos = [{"photo_url": p, "caption": f"{model} 디자인 시안용 예시 사진"} for p in photos]
            else:
                primary_photo = f"/static/img/ui_fixtures/{model}_demo_front.jpg"
                gallery_photos = [{"photo_url": primary_photo, "caption": f"{model} 디자인 시안용 예시 사진"}]

            # 월 납입금 추산 (60개월, 5.9% 원리금 균등)
            price_won = price * 10000
            r = 0.059 / 12
            n = 60
            monthly_est = int((price_won * r * ((1 + r) ** n)) / (((1 + r) ** n) - 1) / 10000)

            # 무작위 옵션 5~8개 선택
            sampled_opts = rng.sample(DEFAULT_OPTIONS, k=rng.randint(5, 8))

            vehicle_record = {
                "id": vehicle_id,
                "manufacturer": maker,
                "model_name": f"{maker} {model}",
                "trim": rng.choice(trims),
                "year": year,
                "mileage": mileage,
                "fuel_type": "가솔린",
                "transmission": "오토",
                "color": rng.choice(COLORS),
                "target_price": price,
                "monthly_payment_estimate": monthly_est,
                "primary_photo_url": primary_photo,
                "photos": gallery_photos,
                "branch_name": "차마트 제휴 전시장 (장한평)",
                "status": "FOR_SALE",
                "publishing_status": "PUBLISHED",
                "is_demo_asset": True,
                "demo_notice": "UI 디자인 검수용 100대 시연 데이터",
                "gallery_status": "STAGING_EXAMPLE",
                "inspection_status": "DEMO_UNVERIFIED",
                "plate_number": None,
                "vin": None,
                "options": [opt["name"] for opt in sampled_opts],
                "options_structured": sampled_opts,
                "accident_summary": {
                    "document_status": "DEMO",
                    "frame_status": "UNKNOWN",
                    "body_panel_status": "UNKNOWN",
                    "outer_damage_count": 0,
                    "frame_damage_count": 0,
                    "oil_leak_status": "UNKNOWN",
                    "flood_history_status": "UNKNOWN",
                    "insurance_history_status": "UNKNOWN",
                    "note": "디자인 시안용 가상 제원"
                },
                "dealer_info": {
                    "name": "차마트 제휴 전시장 (장한평)",
                    "showroom_location": "서울특별시 성동구 자동차시장1길 70 (용답동) 장한평 자동차매매단지",
                    "phone": None
                }
            }
            vehicles.append(vehicle_record)

    # 100대 검증
    assert len(vehicles) == 100, f"Expected 100 vehicles, got {len(vehicles)}"
    assert len({v["id"] for v in vehicles}) == 100, "Duplicate vehicle IDs found!"

    # 모델별 건수 검증
    model_counts = {}
    for v in vehicles:
        m = v["model_name"].split()[1]
        model_counts[m] = model_counts.get(m, 0) + 1

    print("모델별 생성 건수:", model_counts)
    assert model_counts.get("아반떼") == 35
    assert model_counts.get("레이") == 25
    assert model_counts.get("모닝") == 25
    assert model_counts.get("캐스퍼") == 10
    assert model_counts.get("K3") == 5

    out_file = Path("reports/ui_fixtures/chamart_100.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(vehicles, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[*] 100대 UI Fixture JSON 생성 완료: {out_file} ({out_file.stat().st_size:,} bytes)")

if __name__ == "__main__":
    main()
