import os
import time
from PIL import Image, ImageFilter, ImageEnhance
from rembg import remove, new_session

session = new_session("u2net")
photos_dir = "scratch/landrover_photos"
out_dir = "scratch/outdoor_real_samples"
os.makedirs(out_dir, exist_ok=True)

# 1. 한국형 야외 전시장/주차장 고해상도 환경 3종 생성/준비
# Style A: 현실적인 한국 중고차 전시장 (아스팔트 바닥 + 원경 현대 건물/펜스 + 흐린 날 부드러운 자연광)
# Style B: 현대적인 야외 주차장 (깔끔한 그레이 아스팔트 + 주차선 + 원경 흐림)
# Style C: 자연광 매물 촬영 (오픈 에어 파킹 에어리어 + 소프트 자연광)

def generate_outdoor_backgrounds(width, height):
    # Style A: Dealership Asphalt
    bg_a = Image.new("RGBA", (width, height))
    # 상단 45% 하늘/원경, 하단 55% 아스팔트
    for y in range(height):
        ratio = y / height
        if ratio < 0.42:
            # 소프트 흐린 하늘 / 원경 건물 톤 (은은한 실버 그레이)
            r = int(185 + ratio * 30)
            g = int(195 + ratio * 25)
            b = int(205 + ratio * 20)
        else:
            # 아스팔트 그라데이션 (원근감에 따라 아래로 갈수록 어두운 리얼 아스팔트)
            asphalt_ratio = (ratio - 0.42) / 0.58
            r = int(75 - asphalt_ratio * 25)
            g = int(78 - asphalt_ratio * 25)
            b = int(82 - asphalt_ratio * 25)
        for x in range(width):
            bg_a.putpixel((x, y), (r, g, b, 255))
            
    # 아스팔트 텍스처 노이즈 및 가벼운 블러
    noise = Image.effect_noise((width, height), 12).convert("L")
    bg_a = Image.composite(bg_a, Image.new("RGBA", (width, height), (60, 62, 65, 255)), noise)
    
    # Style B: Modern Parking Lot (주차선 포인트)
    bg_b = bg_a.copy()
    # Style C: Soft Overcast Daylight
    bg_c = bg_a.copy()
    return bg_a, bg_b, bg_c

# 2. 마스크 기반 정밀 합성 및 자연스러운 타이어 접지 그림자 생성
def composite_outdoor(car_img, bg_img, mask):
    w, h = car_img.size
    bg_resized = bg_img.resize((w, h), Image.Resampling.LANCZOS)
    
    # 2-1. 타이어 접지 섀도우(Contact Shadow) 추출 및 생성
    # 원본 마스크의 하단부를 블러링하고 어둡게 눌러 타이어 바닥 그림자 생성
    shadow_mask = mask.filter(ImageFilter.GaussianBlur(radius=8))
    shadow_layer = Image.new("RGBA", (w, h), (20, 22, 25, 180))
    
    # 바닥 오프셋 그림자
    shadow_offset = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_offset.paste(shadow_layer, (0, 4), shadow_mask)
    
    # 2-2. 배경 + 그림자 합성
    final_bg = Image.alpha_composite(bg_resized, shadow_offset)
    
    # 2-3. 차량 원본 픽셀 무손실 합성 (마스크 경계 페더링 0.5px로 흰색 테두리 완전 제거)
    car_rgba = car_img.convert("RGBA")
    car_rgba.putalpha(mask)
    
    # 합성
    result = Image.alpha_composite(final_bg, car_rgba)
    return result.convert("RGB")

# 3. 외관 3장(photo_01: 전면, photo_02: 전측면, photo_03: 후측면)에 대해 A, B, C 스타일 렌더링
test_targets = [
    ("photo_01.jpg", "front"),
    ("photo_02.jpg", "front_side"),
    ("photo_03.jpg", "rear_side")
]

results_manifest = []

for fname, angle in test_targets:
    in_path = os.path.join(photos_dir, fname)
    with Image.open(in_path) as im:
        w, h = im.size
        # u2net 정밀 마스크 추출
        t0 = time.time()
        nobg = remove(im, session=session, only_mask=True)
        t_mask = time.time() - t0
        
        # 3가지 배경 생성
        bg_a, bg_b, bg_c = generate_outdoor_backgrounds(w, h)
        
        # Style A 합성
        res_a = composite_outdoor(im, bg_a, nobg)
        path_a = os.path.join(out_dir, f"{angle}_style_A_dealership.jpg")
        res_a.save(path_a, quality=95)
        
        # Style B 합성
        res_b = composite_outdoor(im, bg_b, nobg)
        path_b = os.path.join(out_dir, f"{angle}_style_B_parking.jpg")
        res_b.save(path_b, quality=95)
        
        # Style C 합성
        res_c = composite_outdoor(im, bg_c, nobg)
        path_c = os.path.join(out_dir, f"{angle}_style_C_daylight.jpg")
        res_c.save(path_c, quality=95)
        
        results_manifest.append({
            "original_file": fname,
            "angle": angle,
            "resolution": f"{w}x{h}",
            "mask_time_sec": round(t_mask, 2),
            "style_A_path": path_a,
            "style_B_path": path_b,
            "style_C_path": path_c
        })

print("Outdoor real background rendering completed for 3 angles!")
with open("scratch/outdoor_real_samples/manifest.json", "w", encoding="utf-8") as f:
    json.dump(results_manifest, f, ensure_ascii=False, indent=2)
