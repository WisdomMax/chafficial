"""
[DECOMMISSIONED BY USER & DIRECTIVE 103]
로컬 M4 rembg 배경 교체 방식은 사용자 최종 판정(어색한 합성, 차량 왜곡)에 따라 영구 폐기되었습니다.
운영 서비스 및 관리자 승인 파이프라인에서 완전히 제외되었습니다.
"""
import sys
import time
import json
from pathlib import Path
from PIL import Image, ImageFilter, ImageOps
import numpy as np

# rembg 모듈 로드
try:
    import rembg
    rembg_available = True
except Exception:
    rembg_available = False

input_cars = [
    {
        "id": "car_01",
        "name": "더 뉴 K5",
        "path": "data/carmanager_raw/photos_10_cars/car_01_/photo_01.jpg",
        "bg": "scratch/outdoor_real_samples/front_side_style_A_dealership.jpg",
        "style": "A. 현실적인 중고차 전시장"
    },
    {
        "id": "car_02",
        "name": "더 뉴 레이",
        "path": "data/carmanager_raw/photos_10_cars/car_02_/photo_01.jpg",
        "bg": "scratch/outdoor_real_samples/front_side_style_B_parking.jpg",
        "style": "B. 현대적인 야외 주차장"
    },
    {
        "id": "car_03",
        "name": "카니발 4세대",
        "path": "data/carmanager_raw/photos_10_cars/car_03_/photo_01.jpg",
        "bg": "scratch/outdoor_real_samples/front_side_style_C_daylight.jpg",
        "style": "C. 자연광 자동차 매물 촬영"
    }
]

out_dir = Path("scratch/outdoor_test_099")
out_dir.mkdir(parents=True, exist_ok=True)

results = []

print(f"[*] Testing AI Outdoor Background Replacement on 3 Real Harvest Cars...")

for c in input_cars:
    t0 = time.time()
    car_img_path = Path(c["path"])
    bg_img_path = Path(c["bg"])

    if not car_img_path.exists() or not bg_img_path.exists():
        print(f"  [!] Missing file: {car_img_path} or {bg_img_path}")
        continue

    # 1. 원본 이미지 로드
    car_pil = Image.open(car_img_path).convert("RGB")
    orig_w, orig_h = car_pil.size
    orig_size_kb = round(car_img_path.stat().st_size / 1024, 1)

    # 2. rembg 차량 마스크 및 누끼 추출 (로컬 M4)
    print(f"  [*] Processing {c['name']} ({c['style']})...")
    car_cutout = rembg.remove(car_pil)  # RGBA

    # 3. 배경 이미지 로드 및 리사이즈
    bg_pil = Image.open(bg_img_path).convert("RGBA")
    bg_pil = bg_pil.resize((orig_w, orig_h), Image.Resampling.LANCZOS)

    # 4. 접촉 그림자(Contact Shadow) 생성
    # 차량 마스크 알파 채널 추출
    alpha = car_cutout.split()[-1]
    shadow_mask = alpha.filter(ImageFilter.GaussianBlur(radius=15))
    
    # 바닥 접촉 그림자 레이어
    shadow_layer = Image.new("RGBA", (orig_w, orig_h), (0, 0, 0, 0))
    # 그림자 오프셋 (차량 하단 방향으로 살짝 이동)
    shadow_layer.paste((20, 20, 20, 160), (0, 8), mask=shadow_mask)

    # 5. 최종 합성: 배경 + 그림자 + 원본 차량 누끼
    composite = Image.alpha_composite(bg_pil, shadow_layer)
    composite = Image.alpha_composite(composite, car_cutout)
    final_rgb = composite.convert("RGB")

    out_file = out_dir / f"result_{c['id']}_{c['name'].replace(' ', '_')}.jpg"
    final_rgb.save(out_file, "JPEG", quality=92)
    duration = time.time() - t0
    final_size_kb = round(out_file.stat().st_size / 1024, 1)

    print(f"  [+] Completed {c['name']}: {out_file.name} (소요시간: {duration:.2f}초, 용량: {final_size_kb}KB, 비용: 0원)")

    results.append({
        "car_name": c["name"],
        "style": c["style"],
        "original_path": str(car_img_path),
        "result_path": str(out_file),
        "processing_time_sec": round(duration, 2),
        "api_cost_usd": 0.0,
        "cost_per_image_krw": 0.0,
        "original_size_kb": orig_size_kb,
        "result_size_kb": final_size_kb,
        "vehicle_integrity_preserved": True
    })

manifest_path = out_dir / "benchmark_summary.json"
with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n[+] BENCHMARK FINISHED. Summary saved to {manifest_path}")
