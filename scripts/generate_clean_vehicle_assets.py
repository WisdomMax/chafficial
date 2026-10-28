#!/usr/bin/env python3
"""CHA-FICIAL DIRECTIVE 055: 정직한 개발·시연용 플레이스홀더 자산 생성 및 DB 매핑 스크립트.

원칙:
1. 가짜 '실차 촬영본', 'SHA-256 Verified', '100% 동일 차종 일치 보증' 등 허위 과장 문구를 전면 삭제합니다.
2. 개발·시연용 그래픽 자산임을 투명하게 명시합니다 ('DEMO_PLACEHOLDER' / '예시 이미지').
3. 실차 사진이 없는 매물에는 중립 단일 플레이스홀더('실차 사진 등록 전')를 매핑합니다.
"""

from __future__ import annotations

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from chaficial.platform.db import SessionLocal, Vehicle, VehiclePhoto

IMG_DIR = Path("src/chaficial/platform/ui/static/img/vehicles")
IMG_DIR.mkdir(parents=True, exist_ok=True)


def get_fonts():
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 48)
        font_medium = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 30)
        font_small = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 20)
    except Exception:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    return font_large, font_medium, font_small


font_l, font_m, font_s = get_fonts()


def create_demo_placeholder_image(
    file_path: Path,
    model_name: str,
    plate_number: str,
    category_name: str,
    desc: str,
    bg_color: tuple[int, int, int] = (30, 41, 59),
):
    """정직한 개발 시연용 플레이스홀더 이미지 생성."""
    w, h = 1600, 1000
    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    # 1. 미세 그리드 배경
    for x in range(0, w, 80):
        draw.line([(x, 0), (x, h)], fill=(bg_color[0] + 8, bg_color[1] + 8, bg_color[2] + 8), width=1)
    for y in range(0, h, 80):
        draw.line([(0, y), (w, y)], fill=(bg_color[0] + 8, bg_color[1] + 8, bg_color[2] + 8), width=1)

    # 2. 상단 정직한 안내 배지 (가짜 실차 인증 삭제)
    draw.rectangle([(60, 60), (450, 110)], fill=(71, 85, 105))
    draw.text((80, 74), "개발·시연용 예시 이미지 (DEMO)", fill=(241, 245, 249), font=font_s)

    # 3. 중앙 차량 정보 및 부위 안내
    draw.text((60, 360), model_name, fill=(255, 255, 255), font=font_l)
    draw.text((60, 430), f"차량번호: {plate_number} · 부위: {category_name}", fill=(148, 163, 184), font=font_m)
    draw.text((60, 490), f"※ 참고 정보: {desc}", fill=(203, 213, 225), font=font_s)

    # 4. 하단 정직성 워터마크 고지
    draw.line([(60, 880), (w - 60, 880)], fill=(51, 65, 85), width=2)
    draw.text(
        (60, 910),
        "본 그래픽은 UI 레이아웃 및 기능 시연을 위한 가상 플레이스홀더입니다. 실제 촬영된 실차 사진이 아닙니다.",
        fill=(148, 163, 184),
        font=font_s,
    )
    draw.text((w - 380, 910), "[ DEMO PLACEHOLDER ]", fill=(234, 179, 8), font=font_s)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(file_path, quality=92)
    print(f"[+] 생성 완료 (정직성 고지 완비): {file_path}")


def create_neutral_pending_placeholder(file_path: Path):
    """실차 사진 등록 전 단일 중립 플레이스홀더 생성."""
    w, h = 1600, 1000
    bg_color = (15, 23, 42)
    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    for x in range(0, w, 80):
        draw.line([(x, 0), (x, h)], fill=(25, 35, 60), width=1)
    for y in range(0, h, 80):
        draw.line([(0, y), (w, y)], fill=(25, 35, 60), width=1)

    # 중앙 아이콘 및 안내 문구
    draw.rectangle([(w // 2 - 200, h // 2 - 120), (w // 2 + 200, h // 2 - 60)], fill=(51, 65, 85))
    draw.text((w // 2 - 170, h // 2 - 105), "실차 사진 등록 전 (차량 준비 중)", fill=(248, 250, 252), font=font_m)

    draw.text(
        (w // 2 - 260, h // 2),
        "현재 차량 입고 및 성능점검·광택 상품화가 진행 중입니다.",
        fill=(148, 163, 184),
        font=font_s,
    )
    draw.text(
        (w // 2 - 220, h // 2 + 40),
        "실차 촬영 검증이 완료된 공식 사진만 고객 화면에 등록됩니다.",
        fill=(100, 116, 139),
        font=font_s,
    )

    file_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(file_path, quality=92)
    print(f"[+] 중립 준비중 플레이스홀더 생성: {file_path}")


def main():
    print("[*] DIRECTIVE 055: 정직한 플레이스홀더 자산 갱신 시작...")

    # 1. 중립 단일 플레이스홀더 생성
    create_neutral_pending_placeholder(IMG_DIR / "neutral_car_placeholder.jpg")

    # 2. 그랜저 GN7 데모 플레이스홀더 (가짜 인증 문구 완전 삭제)
    gn7_dir = IMG_DIR / "grandeur_gn7"
    gn7_photos = [
        ("front.jpg", "EXTERIOR", "전면 외관 예시", "현대 디 올 뉴 그랜저 (GN7) 전면 디자인 시연 레이아웃"),
        ("rear.jpg", "EXTERIOR", "후면 외관 예시", "현대 디 올 뉴 그랜저 (GN7) 후면 디자인 시연 레이아웃"),
        ("side.jpg", "EXTERIOR", "측면 외관 예시", "현대 디 올 뉴 그랜저 (GN7) 측면 휠 및 바디라인 시연"),
        ("interior.jpg", "INTERIOR", "실내 운전석 예시", "현대 디 올 뉴 그랜저 (GN7) 실내 콕핏 디스플레이 시연"),
        ("cluster.jpg", "INTERIOR", "계기판 클러스터 예시", "현대 디 올 뉴 그랜저 (GN7) 디지털 클러스터 시연"),
        ("engine.jpg", "ENGINE", "엔진룸 예시", "현대 스마트스트림 2.5 가솔린 엔진룸 시연 레이아웃"),
    ]
    for fn, cat, cap, desc in gn7_photos:
        create_demo_placeholder_image(gn7_dir / fn, "현대 디 올 뉴 그랜저 (GN7)", "88오 5001", cap, desc, (24, 30, 42))

    # 3. K8 데모 플레이스홀더
    k8_dir = IMG_DIR / "k8"
    k8_photos = [
        ("front.jpg", "EXTERIOR", "전면 외관 예시", "기아 K8 2.5 가솔린 전면부 시연"),
        ("rear.jpg", "EXTERIOR", "후면 외관 예시", "기아 K8 2.5 가솔린 후면부 시연"),
        ("side.jpg", "EXTERIOR", "측면 외관 예시", "기아 K8 2.5 가솔린 측면부 시연"),
        ("interior.jpg", "INTERIOR", "실내 대시보드 예시", "기아 K8 노블레스 실내 시연"),
        ("engine.jpg", "ENGINE", "엔진룸 예시", "기아 K8 2.5 엔진룸 시연"),
    ]
    for fn, cat, cap, desc in k8_photos:
        create_demo_placeholder_image(k8_dir / fn, "기아 K8 2.5 가솔린 노블레스", "77조 7788", cap, desc, (18, 25, 36))

    # 4. 쏘렌토 데모 플레이스홀더
    sorento_dir = IMG_DIR / "sorento"
    sorento_photos = [
        ("front.jpg", "EXTERIOR", "전면 외관 예시", "기아 쏘렌토 4세대 하이브리드 전면부 시연"),
        ("rear.jpg", "EXTERIOR", "후면 외관 예시", "기아 쏘렌토 4세대 하이브리드 후면부 시연"),
        ("side.jpg", "EXTERIOR", "측면 외관 예시", "기아 쏘렌토 4세대 하이브리드 측면부 시연"),
        ("interior.jpg", "INTERIOR", "실내 공간 예시", "기아 쏘렌토 4세대 6인승 독립시트 시연"),
    ]
    for fn, cat, cap, desc in sorento_photos:
        create_demo_placeholder_image(sorento_dir / fn, "기아 쏘렌토 하이브리드 4세대", "99수 9900", cap, desc, (20, 32, 28))

    # 5. DB 정비: caption 및 카테고리에 DEMO_PLACEHOLDER 및 정직한 예시 명시
    db = SessionLocal()
    try:
        target_vid = "ce67fd58-311b-4449-b575-45edb9c4537a"
        v = db.query(Vehicle).filter(Vehicle.id == target_vid).first()
        if v:
            db.query(VehiclePhoto).filter(VehiclePhoto.vehicle_id == target_vid).delete()
            for idx, (fn, cat, cap, desc) in enumerate(gn7_photos):
                photo = VehiclePhoto(
                    vehicle_id=target_vid,
                    photo_url=f"/static/img/vehicles/grandeur_gn7/{fn}",
                    category=cat,
                    sort_order=idx + 1,
                    is_primary=(idx == 0),
                    caption=f"{cap} [DEMO_PLACEHOLDER]",
                )
                db.add(photo)
            db.commit()
            print(f"[+] 그랜저 GN7({target_vid}) 사진 6장 정직한 DEMO_PLACEHOLDER 매핑 완료")
    finally:
        db.close()

    print("[*] DIRECTIVE 055 정직한 자산 생성 및 DB 정비 완료!")


if __name__ == "__main__":
    main()
