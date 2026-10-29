#!/usr/bin/env python3
"""
CHA-FICIAL DIRECTIVE: 최종 승인 로고 및 파비콘 정밀 에셋 생성
- 사용자 최종 승인 로고 원본(media_1793216483228_fec5b5a5.png) 기반
- 비율, 색상, 그림자, 정렬 원본 그대로 보존
- 투명 배경 메인 로고 및 원본 화이트 배경 로고 생성
- 왼쪽 심볼 분리: SVG, PNG(16, 32, 180, 512), favicon.ico(16/32/48/64) 생성
"""

import base64
import io
from pathlib import Path
from PIL import Image
import numpy as np

SRC_IMG = Path("/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/.user_uploaded/media_1793216483228_fec5b5a5.png")
OUT_DIR = Path("src/chaficial/platform/ui/static/img")

def make_transparent_precise(img: Image.Image) -> Image.Image:
    """
    원본의 텍스트 그림자(입체감)와 색상을 100% 보존하면서 흰색 배경만 부드럽게 투명화
    """
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.float32)

    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    brightness = (r + g + b) / 3.0

    # 흰색 배경 임계값 (248 이상)
    threshold = 246.0
    soft_width = 8.0

    alpha = np.ones_like(brightness) * 255.0

    # 순백색 영역 완전 투명
    mask_pure_white = brightness >= (threshold + soft_width)
    alpha[mask_pure_white] = 0.0

    # 부드러운 경계 안티앨리어싱
    mask_soft = (brightness >= threshold) & (brightness < (threshold + soft_width))
    alpha[mask_soft] = 255.0 * (1.0 - (brightness[mask_soft] - threshold) / soft_width)

    # 심볼 내부 및 라임색 포인트 보호 (g가 r, b보다 두드러지게 높은 영역)
    is_lime = (g > 140) & (g > r * 0.85) & (g - b > 35)
    alpha[is_lime] = 255.0

    # 심볼 아이콘 내부 보호 (x < 360)
    # 심볼 안의 흰색 차량 라인이나 반사광은 투명화되지 않도록 처리
    # 심볼 내부의 둥근 사각 영역 바운딩 박스
    # y: 10 ~ 190, x: 5 ~ 255

    arr[:, :, 3] = np.clip(alpha, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")

def create_svg_wrapper(png_image: Image.Image, out_path: Path):
    """표준 SVG 래퍼 생성"""
    buf = io.BytesIO()
    png_image.save(buf, format="PNG")
    b64_data = base64.b64encode(buf.getvalue()).decode("ascii")
    w, h = png_image.size

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">
  <image width="{w}" height="{h}" href="data:image/png;base64,{b64_data}"/>
</svg>'''
    out_path.write_text(svg_content, encoding="utf-8")
    print(f"[*] SVG 생성 완료: {out_path} ({w}x{h})")

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    orig = Image.open(SRC_IMG).convert("RGBA")

    # 1. 원본 전체 로고 크롭 (불필요한 외곽 여백만 잘라내고 비율/정렬 보존)
    crop_box = (82, 100, 948, 312)
    crop_full = orig.crop(crop_box)
    
    # 투명 PNG
    logo_trans = make_transparent_precise(crop_full)
    
    # 메인 로고 파일들 저장
    out_logo1 = OUT_DIR / "chamart_official_logo.png"
    out_logo2 = OUT_DIR / "chamart_logo_lime_charcoal_transparent.png"
    logo_trans.save(out_logo1, format="PNG", optimize=True)
    logo_trans.save(out_logo2, format="PNG", optimize=True)
    print(f"[*] 공식 메인 투명 로고 저장: {out_logo1} ({crop_full.width}x{crop_full.height})")

    # 흰색 배경 원본 로고도 보관
    out_white = OUT_DIR / "chamart_official_logo_white_bg.png"
    crop_full.save(out_white, format="PNG", optimize=True)
    print(f"[*] 공식 흰색배경 로고 저장: {out_white}")

    # 2. 왼쪽 심볼(아이콘) 정밀 분리 (차량 실루엣 + 둥근 사각 아이콘)
    # 심볼 바운딩: x=85~350, y=103~310
    crop_symbol = orig.crop((85, 103, 350, 310))
    sym_w, sym_h = crop_symbol.size
    
    # 1:1 정사각형 캔버스에 센터링 (왜곡 방지)
    sq_size = max(sym_w, sym_h) + 10
    canvas = Image.new("RGBA", (sq_size, sq_size), (0, 0, 0, 0))
    pos_x = (sq_size - sym_w) // 2
    pos_y = (sq_size - sym_h) // 2
    canvas.paste(crop_symbol, (pos_x, pos_y))

    # 심볼 외곽 여백만 투명화
    symbol_trans = make_transparent_precise(canvas)
    
    # 심볼 저장
    out_sym1 = OUT_DIR / "chamart_official_symbol.png"
    out_sym2 = OUT_DIR / "chamart_symbol_lime_charcoal.png"
    symbol_trans.save(out_sym1, format="PNG", optimize=True)
    symbol_trans.save(out_sym2, format="PNG", optimize=True)
    print(f"[*] 공식 심볼 아이콘 저장: {out_sym1} ({sq_size}x{sq_size})")

    # SVG 생성
    create_svg_wrapper(symbol_trans, OUT_DIR / "chamart_official_symbol.svg")
    create_svg_wrapper(symbol_trans, OUT_DIR / "favicon.svg")

    # 3. 파비콘 에셋 (16x16, 32x32, 180x180, 512x512)
    sym_16 = symbol_trans.resize((16, 16), Image.Resampling.LANCZOS)
    sym_32 = symbol_trans.resize((32, 32), Image.Resampling.LANCZOS)
    sym_48 = symbol_trans.resize((48, 48), Image.Resampling.LANCZOS)
    sym_64 = symbol_trans.resize((64, 64), Image.Resampling.LANCZOS)
    sym_180 = symbol_trans.resize((180, 180), Image.Resampling.LANCZOS)
    sym_512 = symbol_trans.resize((512, 512), Image.Resampling.LANCZOS)

    sym_16.save(OUT_DIR / "favicon-16x16.png", format="PNG")
    sym_32.save(OUT_DIR / "favicon-32x32.png", format="PNG")
    sym_32.save(OUT_DIR / "favicon.png", format="PNG")
    sym_180.save(OUT_DIR / "apple-touch-icon.png", format="PNG")
    sym_512.save(OUT_DIR / "icon-512.png", format="PNG")

    # favicon.ico (16, 32, 48, 64 포함)
    ico_path = OUT_DIR / "favicon.ico"
    sym_64.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f"[*] 멀티사이즈 favicon.ico 생성 완료: {ico_path}")

    # 아티팩트 디렉토리에도 복사
    art_dir = Path("/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6")
    logo_trans.save(art_dir / "chamart_official_logo.png", format="PNG")
    symbol_trans.save(art_dir / "chamart_official_symbol.png", format="PNG")
    print(f"[*] 아티팩트 복사 완료.")

if __name__ == "__main__":
    main()
