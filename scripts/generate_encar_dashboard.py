import os
from PIL import Image, ImageDraw, ImageFont

def create_encar_dashboard():
    base_dir = "/Users/wisdom/.gemini/antigravity/brain/9c682aef-6bb4-4339-9f02-f135b6a8f8c6/reports"
    out_path = f"{base_dir}/encar_design_showcase_dashboard.png"
    
    # 6개 이미지 로드 및 리사이즈
    images = [
        ("PC 1440px 앨범형 그리드 (5:3 실차 사진 + 좌측 270px 정밀 다단계 필터 + 우측 퀵바)", f"{base_dir}/encar_1440_staging_grid.png"),
        ("PC 1440px 리스트형 와이드 보기 (엔카 가로목록 뷰 스위처 동작)", f"{base_dir}/encar_1440_staging_list.png"),
        ("PC 1440px 실차 상세 페이지 (5:3 대형 갤러리 + 딥 틸/네이비 디자인 시스템)", f"{base_dir}/encar_1440_detail_fixed.png"),
        ("태블릿 1024px 반응형 뷰 (2열 여유 그리드 + 글자 쪼개짐 원천 차단)", f"{base_dir}/encar_1024_staging.png"),
        ("모바일 390px 콤팩트 뷰 (원클릭 필터 시트 + 1열 단일 카드)", f"{base_dir}/encar_390_staging_mobile.png"),
        ("운영 쇼룸 1440px (미입고 시 '실차 검증 입고 준비 중' 정직한 안내 및 격리 원칙)", f"{base_dir}/encar_1440_production_clean.png"),
    ]
    
    # 2열 x 3행 배치
    card_w = 800
    card_h = 500
    gap = 40
    header_h = 100
    
    total_w = card_w * 2 + gap * 3
    total_h = header_h + (card_h + 50) * 3 + gap * 2 + 40
    
    dash = Image.new("RGB", (total_w, total_h), color="#0F172A")
    draw = ImageDraw.Draw(dash)
    
    # 헤더 텍스트
    # 폰트 로드 시도
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 36)
        font_sub = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
        font_label = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = font_title
        font_label = font_title
        
    draw.text((gap, 30), "차마트(CHAMART) × 엔카(Encar) 표준 2단 레이아웃 및 UX 전면 개편 종합 대시보드", fill="#38BDF8", font=font_title)
    draw.text((gap, 72), "좌측 정밀 다단계 필터 + 5:3 앨범/리스트 뷰 전환 + 우측 플로팅 퀵바 + 딥 틸/네이비 브랜드 컬러 시스템 정립", fill="#94A3B8", font=font_sub)
    
    positions = [
        (0, 0), (1, 0),
        (0, 1), (1, 1),
        (0, 2), (1, 2)
    ]
    
    for idx, (label, img_file) in enumerate(images):
        col, row = positions[idx]
        x = gap + col * (card_w + gap)
        y = header_h + row * (card_h + 50 + gap)
        
        # 라벨 바
        draw.rectangle([x, y, x + card_w, y + 36], fill="#1E293B")
        draw.text((x + 12, y + 8), f"[{idx+1}] {label}", fill="#F8FAFC", font=font_label)
        
        # 이미지 삽입
        if os.path.exists(img_file):
            im = Image.open(img_file).convert("RGB")
            # 비율 유지 또는 크롭
            im.thumbnail((card_w, card_h), Image.Resampling.LANCZOS)
            
            # 카드 배경
            card_bg = Image.new("RGB", (card_w, card_h), color="#1E293B")
            # 중앙 배치
            offset_x = (card_w - im.width) // 2
            offset_y = (card_h - im.height) // 2
            card_bg.paste(im, (offset_x, offset_y))
            dash.paste(card_bg, (x, y + 36))
            
            # 외곽 테두리
            draw.rectangle([x, y, x + card_w, y + 36 + card_h], outline="#334155", width=2)
            
    dash.save(out_path, quality=95)
    print(f"Generated dashboard: {out_path}")

if __name__ == "__main__":
    create_encar_dashboard()
