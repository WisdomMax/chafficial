#!/usr/bin/env python3
"""차마트(CHAMART) 상용 브랜드 고해상도 PNG 로고 및 파비콘 생성기.

화이트 80% / 딥 차콜 15% / 일렉트릭 라임 5% 컬러 토큰 및
한글 'ㅊ'과 전진 도로를 결합한 기하학적 모빌리티 심벌 적용.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

STATIC_IMG_DIR = Path("src/chaficial/platform/ui/static/img")
STATIC_IMG_DIR.mkdir(parents=True, exist_ok=True)

# 디자인 컬러 토큰
COLOR_DEEP_CHARCOAL = (23, 27, 30, 255)  # #171B1E
COLOR_ELECTRIC_LIME = (200, 255, 61, 255)  # #C8FF3D
COLOR_WHITE = (255, 255, 255, 255)
COLOR_TRANSPARENT = (0, 0, 0, 0)
COLOR_MUTED_GRAY = (100, 107, 107, 255)  # #646B6B

FONT_PATH = "/Library/Fonts/Pretendard-Bold.otf"
if not Path(FONT_PATH).exists():
    FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"


def draw_chamart_symbol(size=512, bg_color=None):
    """독자적 한글 'ㅊ' 도로 전진 모빌리티 심벌 생성."""
    img = Image.new("RGBA", (size, size), bg_color or COLOR_TRANSPARENT)
    draw = ImageDraw.Draw(img)

    scale = size / 512.0

    # 1. 배경 서피스 둥근 사각형 (딥 차콜)
    margin = 32 * scale
    radius = 110 * scale
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=COLOR_DEEP_CHARCOAL
    )

    # 2. 'ㅊ' 상단 포인트: 일렉트릭 라임 다이아몬드 (전진하는 미래의 나침반)
    diamond_cy = 135 * scale
    diamond_r = 38 * scale
    diamond_pts = [
        (size / 2, diamond_cy - diamond_r),
        (size / 2 + diamond_r, diamond_cy),
        (size / 2, diamond_cy + diamond_r),
        (size / 2 - diamond_r, diamond_cy),
    ]
    draw.polygon(diamond_pts, fill=COLOR_ELECTRIC_LIME)

    # 3. 'ㅊ' 가로 축: 일렉트릭 라임 수평 바
    bar_y1 = 205 * scale
    bar_y2 = 238 * scale
    bar_margin = 110 * scale
    draw.rounded_rectangle(
        [bar_margin, bar_y1, size - bar_margin, bar_y2],
        radius=12 * scale,
        fill=COLOR_ELECTRIC_LIME
    )

    # 4. 'ㅊ' 하단: 원근감으로 뻗어나가는 2차선 도로 (모빌리티 고속도로)
    # 좌측 차선
    left_road_pts = [
        (size / 2 - 25 * scale, 260 * scale),
        (size / 2 - 5 * scale, 260 * scale),
        (130 * scale, 405 * scale),
        (90 * scale, 405 * scale),
    ]
    draw.polygon(left_road_pts, fill=COLOR_WHITE)

    # 우측 차선
    right_road_pts = [
        (size / 2 + 5 * scale, 260 * scale),
        (size / 2 + 25 * scale, 260 * scale),
        (size - 90 * scale, 405 * scale),
        (size - 130 * scale, 405 * scale),
    ]
    draw.polygon(right_road_pts, fill=COLOR_WHITE)

    # 중앙 분리선 (대시 포인트 - 라임 액센트)
    center_y1 = 285 * scale
    center_y2 = 365 * scale
    draw.line(
        [(size / 2, center_y1), (size / 2, center_y2)],
        fill=COLOR_ELECTRIC_LIME,
        width=int(10 * scale)
    )

    return img


def draw_chamart_horizontal_logo(width=900, height=220):
    """가로형 공식 브랜드 로고 (심벌 + 차마트 워드마크)."""
    img = Image.new("RGBA", (width, height), COLOR_TRANSPARENT)
    draw = ImageDraw.Draw(img)

    # 1. 좌측 심벌 삽입 (크기 170x170, 패딩 25)
    sym_size = 170
    sym_img = draw_chamart_symbol(size=sym_size)
    img.paste(sym_img, (20, int((height - sym_size) / 2)), sym_img)

    # 2. 우측 한글 '차마트' 단독 워드마크 렌더링
    text_x = 220
    text_y = int(height * 0.22)

    try:
        font_large = ImageFont.truetype(FONT_PATH, 100)
        font_sub = ImageFont.truetype(FONT_PATH, 28)
    except Exception:
        font_large = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # 메인 워드마크 '차마트'
    draw.text((text_x, text_y), "차마트", fill=COLOR_DEEP_CHARCOAL, font=font_large)

    # 보조 영문 표기 'CHAMART MOBILITY'
    sub_y = text_y + 105
    draw.text((text_x + 6, sub_y), "CHAMART MOBILITY", fill=COLOR_MUTED_GRAY, font=font_sub)

    return img


def main():
    print("[*] 차마트 상용 브랜드 공식 PNG 및 파비콘 생성 시작...")

    # 1. 독립 심벌 (512x512 투명)
    symbol_512 = draw_chamart_symbol(512)
    sym_path = STATIC_IMG_DIR / "chamart_symbol_lime_charcoal.png"
    symbol_512.save(sym_path, "PNG")
    print(f" -> 독립 심벌 저장 완료: {sym_path}")

    # 2. 가로형 투명 로고 (900x220)
    logo_horiz = draw_chamart_horizontal_logo(900, 220)
    logo_path = STATIC_IMG_DIR / "chamart_logo_lime_charcoal_transparent.png"
    logo_horiz.save(logo_path, "PNG")
    print(f" -> 가로형 로고 저장 완료: {logo_path}")

    # 3. 파비콘 및 앱 아이콘 (180x180, 64x64, 32x32)
    apple_icon = draw_chamart_symbol(180)
    apple_path = STATIC_IMG_DIR / "apple-touch-icon.png"
    apple_icon.save(apple_path, "PNG")

    favicon_64 = draw_chamart_symbol(64)
    fav_path = STATIC_IMG_DIR / "favicon.png"
    favicon_64.save(fav_path, "PNG")

    # .ico 변환 저장
    ico_path = STATIC_IMG_DIR / "favicon.ico"
    symbol_512.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    print(f" -> 파비콘 & 앱 아이콘 저장 완료: {ico_path}, {fav_path}, {apple_path}")


if __name__ == "__main__":
    main()
