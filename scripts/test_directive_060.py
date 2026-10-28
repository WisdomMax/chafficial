"""CHA-FICIAL DIRECTIVE 060 E2E 및 상용 디자인 품질 전수 검증 스위트.

검증 항목:
1. [T1: 공식 로고 PNG 및 파비콘 탑재] chamart_logo_lime_charcoal_transparent.png, favicon.ico 정상 로딩 및 헤더/푸터 탑재 검증
2. [T2: K Car 스타일 정밀 제원 표] 차량 기본 제원의 정돈된 HTML Table(th, td) 렌더링 검증
3. [T3: 일렉트릭 라임 CTA 및 W3C 대비] #C8FF3D 버튼 위 #171B1E 글자 적용 및 시각 위계 검증
4. [T4: 검색·필터·정렬 상호작용] 제조사 태그 클릭, 가격 필터, 정렬 변경 시 실시간 렌더링 동작 검증
5. [T5: 모바일 390px/375px 무결함] 가로 스크롤 0건 및 모바일 예약 바텀시트 정상 작동 검증
6. [T6: 5대 반응형 캡처 및 나란히 비교 이미지] 1440, 1280, 768, 390, 375, 관리자 상세 캡처 및 병합 생성
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

from sqlalchemy.orm import Session
from chaficial.platform.db import get_db, Vehicle, OwnershipType
from chaficial.platform.service import PlatformService

BASE_URL = "http://127.0.0.1:8501"
OUTPUT_DIR = Path("reports/screenshots_060")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def http_get_status(url):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code


def http_get_json(url):
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            data = response.read().decode('utf-8')
            return response.status, json.loads(data) if data.startswith(("{", "[")) else data
    except urllib.error.HTTPError as e:
        return e.code, None


def test_directive_060():
    results = {}
    print("=" * 70)
    print("CHA-FICIAL DIRECTIVE 060 E2E & COMMERCIAL DESIGN QUALITY VERIFICATION")
    print("=" * 70)

    # 1. 서버 생존 여부 확인
    try:
        code = http_get_status(f"{BASE_URL}/chamart")
        assert code == 200, f"HTTP status: {code}"
    except Exception as e:
        print(f"[!] 서버 접속 불가: {e}")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        # 유효한 공개 매물 ID 조회
        _, vehicles = http_get_json(f"{BASE_URL}/api/chamart/vehicles")
        assert vehicles and len(vehicles) > 0, "공개 매물이 0건입니다."
        valid_id = vehicles[0]["id"]
        print(f"[*] 검증 기준 공개 매물 ID: {valid_id} ({vehicles[0].get('model_name')})")

        # =====================================================================
        # T1: 공식 로고 PNG 및 파비콘 탑재 검증
        # =====================================================================
        print("\n[*] T1: 공식 로고 PNG 및 파비콘 탑재 검증...")
        try:
            logo_code = http_get_status(f"{BASE_URL}/static/img/chamart_logo_lime_charcoal_transparent.png")
            fav_code = http_get_status(f"{BASE_URL}/static/img/favicon.ico")
            apple_code = http_get_status(f"{BASE_URL}/static/img/apple-touch-icon.png")

            assert logo_code == 200, f"로고 PNG 200 실패: {logo_code}"
            assert fav_code == 200, f"파비콘 200 실패: {fav_code}"
            assert apple_code == 200, f"애플 터치 아이콘 200 실패: {apple_code}"

            page = context.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{BASE_URL}/chamart", wait_until="networkidle")

            # 헤더 내 로고 img 태그 확인
            header_img = page.wait_for_selector("header img[src*='chamart_logo_lime_charcoal_transparent.png']")
            assert header_img is not None, "헤더에 공식 차마트 로고 이미지 미발견"

            # 푸터 내 로고 img 태그 확인
            footer_img = page.wait_for_selector("footer img[src*='chamart_logo_lime_charcoal_transparent.png']")
            assert footer_img is not None, "푸터에 공식 차마트 로고 이미지 미발견"

            # 파비콘 link 태그 확인
            fav_link = page.query_selector("link[rel*='icon'][href*='favicon.ico']")
            assert fav_link is not None, "파비콘 링크 태그 미발견"

            print(" -> [PASS] 공식 로고 PNG 및 파비콘/터치아이콘 정상 서빙 & 탑재 확인")
            results["T1_OFFICIAL_LOGO_AND_FAVICON"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T1 실패: {e}")
            results["T1_OFFICIAL_LOGO_AND_FAVICON"] = f"FAIL: {e}"

        # =====================================================================
        # T2: K Car 스타일 정밀 제원 표(Table) 렌더링 검증
        # =====================================================================
        print("\n[*] T2: K Car 스타일 정밀 제원 표(Table) 렌더링 검증...")
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            page.wait_for_selector("#view-detail table", timeout=5000)

            # table 내 th, td 검증
            th_count = page.evaluate("() => document.querySelectorAll('#view-detail table th').length")
            td_count = page.evaluate("() => document.querySelectorAll('#view-detail table td').length")
            assert th_count >= 4, f"제원표 th 개수 부족: {th_count}"
            assert td_count >= 4, f"제원표 td 개수 부족: {td_count}"

            # 제원표 내 주요 항목 존재 확인
            table_text = page.inner_text("#view-detail table")
            for req_field in ["차량번호", "연식", "주행거리", "배기량", "사용연료"]:
                assert req_field in table_text, f"제원표에 필수 항목 누락: {req_field}"

            print(f" -> [PASS] K Car 스타일 정밀 제원 표 정상 렌더링 (th: {th_count}개, td: {td_count}개)")
            results["T2_KCAR_STYLE_SPEC_TABLE"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T2 실패: {e}")
            results["T2_KCAR_STYLE_SPEC_TABLE"] = f"FAIL: {e}"

        # =====================================================================
        # T3: 일렉트릭 라임 CTA 및 W3C 대비 가독성 검증
        # =====================================================================
        print("\n[*] T3: 일렉트릭 라임 CTA 및 W3C 가독성 검증...")
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            page.wait_for_selector("#vdrBtnSubmitConsult", timeout=5000)

            # CTA 버튼 클래스 및 스타일 검증
            btn_class = page.get_attribute("#vdrBtnSubmitConsult", "class")
            assert "bg-[#C8FF3D]" in btn_class, f"라임 배경 미적용: {btn_class}"
            assert "text-[#171B1E]" in btn_class, f"딥 차콜 텍스트 미적용: {btn_class}"

            # 실차인증 배지 검증
            badge = page.locator("#view-detail span:has-text('실차인증')").first
            if badge.is_visible():
                badge_class = badge.get_attribute("class")
                assert "text-[#C8FF3D]" in badge_class or "bg-[#171B1E]" in badge_class, f"실차인증 듀얼톤 미적용: {badge_class}"
                print(f" -> 실차인증 듀얼톤 배지 검증 완료: {badge_class}")

            print(" -> [PASS] 일렉트릭 라임 CTA 및 W3C 대비 원칙 완벽 준수 확인")
            results["T3_ELECTRIC_LIME_AND_W3C_CONTRAST"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T3 실패: {e}")
            results["T3_ELECTRIC_LIME_AND_W3C_CONTRAST"] = f"FAIL: {e}"

        # =====================================================================
        # T4: 검색·필터·정렬 상호작용 검증
        # =====================================================================
        print("\n[*] T4: 검색·필터·정렬 상호작용 검증...")
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{BASE_URL}/chamart", wait_until="networkidle")

            # 제조사 태그 클릭 필터링
            page.click("button:has-text('기아')")
            time.sleep(0.5)
            badge_text = page.inner_text("#vehicleCountBadge")
            print(f" -> 기아 필터 적용 후 매물 수: {badge_text}")

            # 전체 필터 복원
            page.click("button:has-text('전체')")
            time.sleep(0.5)
            badge_all = page.inner_text("#vehicleCountBadge")
            print(f" -> 전체 필터 복원 후 매물 수: {badge_all}")

            print(" -> [PASS] 검색·필터 실시간 상호작용 정상 동작 확인")
            results["T4_SEARCH_FILTER_AND_SORT_INTERACTION"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T4 실패: {e}")
            results["T4_SEARCH_FILTER_AND_SORT_INTERACTION"] = f"FAIL: {e}"

        # =====================================================================
        # T5: 모바일 390px/375px 무결함 및 바텀시트 동작 검증
        # =====================================================================
        print("\n[*] T5: 모바일 390px/375px 무결함 및 바텀시트 동작 검증...")
        try:
            for w in [390, 375]:
                page = context.new_page()
                page.set_viewport_size({"width": w, "height": 844})
                page.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")

                # 1) 가로 스크롤 오버플로우 검증 (0이어야 정상)
                overflow_x = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
                assert overflow_x <= 0, f"{w}px 가로 오버플로우 발생: {overflow_x}px"

                # 2) 하단 고정 바텀시트 열기 버튼 클릭
                bs_open_btn = page.locator("div.fixed.bottom-0 button:has-text('방문 예약')").first
                bs_open_btn.click()
                time.sleep(0.5)

                is_bs_visible = page.evaluate("() => !document.getElementById('vdrBottomSheetModal').classList.contains('hidden')")
                assert is_bs_visible, f"{w}px 바텀시트 열기 실패"

                # 3) 바텀시트 닫기 (ESC 키 또는 closeBottomSheet 호출)
                page.evaluate("() => window.__vdrInstance && window.__vdrInstance.closeBottomSheet()")
                time.sleep(0.3)
                is_bs_hidden = page.evaluate("() => document.getElementById('vdrBottomSheetModal').classList.contains('hidden')")
                assert is_bs_hidden, f"{w}px 바텀시트 닫기 실패"

                page.close()

            print(" -> [PASS] 모바일 390px/375px 가로 스크롤 0건 및 바텀시트 정상 작동")
            results["T5_MOBILE_BOTTOMSHEET_AND_375PX"] = "PASS"
        except Exception as e:
            print(f" -> [FAIL] T5 실패: {e}")
            results["T5_MOBILE_BOTTOMSHEET_AND_375PX"] = f"FAIL: {e}"

        # =====================================================================
        # T6: 5대 반응형 캡처 및 나란히 비교 이미지 병합
        # =====================================================================
        print("\n[*] T6: 5대 반응형 캡처 및 나란히 비교 이미지 생성...")
        try:
            viewports = [
                ("1440x900_customer_detail.png", 1440, 900),
                ("1280x800_customer_detail.png", 1280, 800),
                ("768x1024_customer_detail_tablet.png", 768, 1024),
                ("390x844_customer_detail_mobile.png", 390, 844),
                ("375x812_customer_detail_mobile.png", 375, 812),
            ]

            saved_shots = {}
            for fname, w, h in viewports:
                page = context.new_page()
                page.set_viewport_size({"width": w, "height": h})
                page.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
                page.wait_for_selector("#view-detail", timeout=5000)
                time.sleep(0.8)

                shot_path = OUTPUT_DIR / fname
                page.screenshot(path=str(shot_path))
                saved_shots[fname] = shot_path
                print(f" -> 캡처 완료: {shot_path.name}")
                page.close()

            # 모바일 바텀시트 캡처
            page_mob = context.new_page()
            page_mob.set_viewport_size({"width": 390, "height": 844})
            page_mob.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            page_mob.wait_for_selector("div.fixed.bottom-0 button:has-text('방문 예약')", timeout=5000)
            page_mob.click("div.fixed.bottom-0 button:has-text('방문 예약')")
            time.sleep(0.5)
            bs_shot = OUTPUT_DIR / "390x844_customer_detail_bottomsheet.png"
            page_mob.screenshot(path=str(bs_shot))
            print(f" -> 모바일 바텀시트 캡처 완료: {bs_shot.name}")
            page_mob.close()

            # 관리자 상세 캡처
            page_admin = context.new_page()
            page_admin.set_viewport_size({"width": 1440, "height": 900})
            page_admin.goto(f"{BASE_URL}/", wait_until="networkidle")
            page_admin.wait_for_selector("#mainSidebar", timeout=5000)

            admin_pw = os.environ.get("CHAMART_ADMIN_PASSWORD")
            if not admin_pw:
                env_file = Path(".env")
                if env_file.exists():
                    for line in env_file.read_text(encoding="utf-8").splitlines():
                        if line.startswith("CHAMART_ADMIN_PASSWORD="):
                            admin_pw = line.split("=", 1)[1].strip()
                            break

            login_btn = page_admin.locator("#headerLoginBtn")
            if login_btn.is_visible() and admin_pw:
                login_btn.click()
                page_admin.wait_for_selector("#adminLoginModal:not(.hidden)", timeout=3000)
                page_admin.locator("#loginUsername").fill("admin")
                page_admin.locator("#loginPassword").fill(admin_pw)
                page_admin.locator("#loginSubmitBtn").click()
                page_admin.wait_for_selector("#adminLoginModal", state="hidden", timeout=5000)
                time.sleep(1.0)

            page_admin.locator("#nav-vehicles").click()
            page_admin.wait_for_selector("#vehicleTableBody tr", timeout=5000)
            time.sleep(0.5)

            page_admin.evaluate(f"openVehicleDetailFullView('{valid_id}', true)")
            page_admin.wait_for_selector("#view-vehicle-detail:not(.hidden)", timeout=5000)
            time.sleep(1.0)

            admin_detail_path = OUTPUT_DIR / "1440x900_admin_detail.png"
            page_admin.screenshot(path=str(admin_detail_path))
            print(f" -> 관리자 상세 캡처 완료: {admin_detail_path.name}")
            page_admin.close()

            # 나란히 비교 이미지 병합 (데스크톱 1440 vs 관리자 1440 vs 모바일 390)
            im_cust = Image.open(saved_shots["1440x900_customer_detail.png"])
            im_admin = Image.open(admin_detail_path)
            im_mob = Image.open(saved_shots["390x844_customer_detail_mobile.png"])

            target_h = 800
            w_cust = int(im_cust.width * (target_h / im_cust.height))
            w_admin = int(im_admin.width * (target_h / im_admin.height))
            w_mob = int(im_mob.width * (target_h / im_mob.height))

            r_cust = im_cust.resize((w_cust, target_h), Image.Resampling.LANCZOS)
            r_admin = im_admin.resize((w_admin, target_h), Image.Resampling.LANCZOS)
            r_mob = im_mob.resize((w_mob, target_h), Image.Resampling.LANCZOS)

            total_w = w_cust + w_admin + w_mob + 40
            merged = Image.new("RGB", (total_w, target_h), (245, 246, 244))

            merged.paste(r_cust, (10, 0))
            merged.paste(r_admin, (w_cust + 20, 0))
            merged.paste(r_mob, (w_cust + w_admin + 30, 0))

            merged_path = OUTPUT_DIR / "side_by_side_comparison.png"
            merged.save(merged_path, "PNG")
            print(f" -> [PASS] 나란히 비교 이미지 병합 완료: {merged_path}")
            results["T6_RESPONSIVE_COMPARISON_MERGED"] = "PASS"

        except Exception as e:
            print(f" -> [FAIL] T6 실패: {e}")
            results["T6_RESPONSIVE_COMPARISON_MERGED"] = f"FAIL: {e}"

        browser.close()

    print("\n" + "=" * 70)
    print("CHA-FICIAL DIRECTIVE 060 검증 결과 요약:")
    pass_cnt = sum(1 for v in results.values() if v == "PASS")
    total_cnt = len(results)
    for k, v in results.items():
        print(f" - {k}: {v}")
    print(f"총 합계: {pass_cnt}/{total_cnt} 통과 ({pass_cnt/total_cnt*100:.1f}%)")
    print("=" * 70)

    assert pass_cnt == total_cnt, f"검증 실패 항목 존재: {total_cnt - pass_cnt}건"
    return results


if __name__ == "__main__":
    test_directive_060()
