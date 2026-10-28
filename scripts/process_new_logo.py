#!/usr/bin/env python3
"""
CHA-FICIAL 신규 공식 로고 에셋 생성 스크립트
- 업로드된 공식 차마트 로고(심볼+차마트 볼드 타이포) 기반
- 불필요한 여백 크롭 및 고품질 알파 채널(투명 배경) 처리
- 가로형 메인 로고, 심볼 단독 아이콘, 파비콘(PNG/ICO), Apple Touch Icon 생성
"""

from pathlib import Path
from PIL import Image
import numpy as np

SRC_IMG = Path("/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/.user_uploaded/media_1793216483228_fec5b5a5.png")
OUT_DIR = Path("src/chaficial/platform/ui/static/img")

def make_transparent_smooth(img: Image.Image, threshold=245, soft_range=15) -> Image.Image:
    """
    흰색 배경을 자연스럽게 투명화 (안티앨리어싱 보존)
    """
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.float32)

    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    brightness = (r + g + b) / 3.0

    # 밝기에 따른 알파 계산 (threshold 이상이면 알파 감소)
    alpha = np.ones_like(brightness) * 255.0
    
    # 순백색 영역은 완전 투명
    mask_white = brightness >= (threshold + soft_range)
    alpha[mask_white] = 0.0

    # 경계선 영역은 부드럽게 감쇄
    mask_soft = (brightness >= threshold) & (brightness < (threshold + soft_range))
    alpha[mask_soft] = 255.0 * (1.0 - (brightness[mask_soft] - threshold) / soft_range)

    # 텍스트 및 심볼 내부의 밝은 부분(라임색 등)은 보존
    # 라임색은 녹색(g)이 높고 r, b와 차이가 큼
    is_lime = (g > 150) & (g > r * 0.9) & (b < 180) & (g - b > 40)
    alpha[is_lime] = 255.0

    # 차량 전조등의 흰색 하이라이트 등 완전 내부의 밝은 픽셀 처리
    # (x < 350 영역 내부는 심볼이므로 둥근 사각 아이콘 내부는 불투명 유지)

    arr[:, :, 3] = np.clip(alpha, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    orig = Image.open(SRC_IMG).convert("RGBA")
    w, h = orig.size

    # 1. 바운딩 박스 크롭 (87, 105, 944, 308) 기준 약간의 여백(약 4px) 포함
    # 전체 로고 크롭
    crop_full = orig.crop((82, 100, 948, 312))
    
    # 투명 배경 전체 로고 생성
    transparent_full = make_transparent_smooth(crop_full, threshold=248, soft_range=7)
    
    # 저장 1: 메인 가로형 투명 로고
    out_logo_trans = OUT_DIR / "chamart_logo_lime_charcoal_transparent.png"
    transparent_full.save(out_logo_trans, format="PNG", optimize=True)
    print(f"[*] 가로형 투명 로고 생성: {out_logo_trans} ({crop_full.width}x{crop_full.height})")

    # 저장 2: 흰색 배경 전체 로고
    out_logo_white = OUT_DIR / "chamart_logo_white_bg.png"
    crop_full.save(out_logo_white, format="PNG", optimize=True)
    print(f"[*] 가로형 흰색배경 로고 생성: {out_logo_white}")

    # 2. 심볼 단독 크롭 (왼쪽 차량 아이콘: 87, 105, 349, 308)
    crop_symbol = orig.crop((85, 103, 349, 310))
    # 심볼 정사각 캔버스에 센터링 (정사각 크기 max(w, h) + 여백)
    sym_w, sym_h = crop_symbol.size
    sq_size = max(sym_w, sym_h) + 16
    
    symbol_sq = Image.new("RGBA", (sq_size, sq_size), (0, 0, 0, 0))
    offset_x = (sq_size - sym_w) // 2
    offset_y = (sq_size - sym_h) // 2
    symbol_sq.paste(crop_symbol, (offset_x, offset_y))

    # 심볼 투명화 (외부 흰색 여백만 투명화)
    symbol_trans = make_transparent_smooth(symbol_sq, threshold=248, soft_range=7)
    
    out_symbol = OUT_DIR / "chamart_symbol_lime_charcoal.png"
    symbol_trans.save(out_symbol, format="PNG", optimize=True)
    print(f"[*] 심볼 단독 아이콘 생성: {out_symbol} ({sq_size}x{sq_size})")

    # 3. 파비콘 생성 (64x64, 32x32, 16x16)
    fav_64 = symbol_trans.resize((64, 64), Image.Resampling.LANCZOS)
    fav_32 = symbol_trans.resize((32, 32), Image.Resampling.LANCZOS)
    fav_16 = symbol_trans.resize((16, 16), Image.Resampling.LANCZOS)

    out_fav_png = OUT_DIR / "favicon.png"
    fav_32.save(out_fav_png, format="PNG")
    print(f"[*] favicon.png 생성: {out_fav_png}")

    out_fav_ico = OUT_DIR / "favicon.ico"
    fav_64.save(out_fav_ico, format="ICO", sizes=[(64, 64), (32, 32), (16, 16)])
    print(f"[*] favicon.ico 생성: {out_fav_ico}")

    # 4. Apple Touch Icon (180x180)
    apple_icon = symbol_sq.resize((180, 180), Image.Resampling.LANCZOS)
    out_apple = OUT_DIR / "apple-touch-icon.png"
    apple_icon.save(out_apple, format="PNG")
    print(f"[*] apple-touch-icon.png 생성: {out_apple}")

    # 아티팩트 디렉토리에도 복사하여 UI 및 문서에서 바로 볼 수 있게 함
    art_dir = Path("/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6")
    transparent_full.save(art_dir / "new_chamart_logo.png", format="PNG")
    symbol_trans.save(art_dir / "new_chamart_symbol.png", format="PNG")
    print(f"[*] 아티팩트 디렉토리 복사 완료: new_chamart_logo.png, new_chamart_symbol.png")

if __name__ == "__main__":
    main()
