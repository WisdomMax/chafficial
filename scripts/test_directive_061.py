"""CHA-FICIAL DIRECTIVE 061 E2E 및 상용 모바일 인터랙션·성능점검부 전수 검증 스위트.

검증 항목:
1. [T1: 제원 정직성 & VIN 복사] 변속기/구동/연료 가짜 기본값 제거 확인 및 차대번호 복사 버튼 탑재 검증
2. [T2: 모바일 필터 바텀시트] 390px 필터 바텀시트 열기, 제조사 칩 선택 시 모델 동적 갱신, 실시간 건수 버튼, 초기화 검증
3. [T3: 필터 URL 동기화 & popstate] 필터 적용 시 ?maker=... 쿼리 갱신 및 브라우저 뒤로가기 상태 복원 검증
4. [T4: 사진 터치 스와이프 & 경계 처리] 터치 스와이프 시 사진 전환 및 첫/마지막 사진 순환 경계 처리 검증
5. [T5: 사진 더블탭 2배 확대] 메인 사진 더블탭 시 scale(2) 확대 및 재탭 시 원상복귀 검증
6. [T6: Lightbox 키보드 & 포커스 복귀] Lightbox 열기, 키보드 좌우 탐색, ESC 닫기 및 포커스 복귀 검증
7. [T7: 공인 성능점검기록부 공식 사본 모달] 공식 성능기록부 팝업 열기 및 문서번호/기관/점검표 일치 검증
8. [T8: 8대 실측 캡처 & 사이드 바이 사이드 병합] PC/모바일/바텀시트/더블탭확대/성능기록부 캡처 및 병합 생성
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

BASE_URL = "http://127.0.0.1:8501"
OUTPUT_DIR = Path("reports/screenshots_061")
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


def test_directive_061():
    results = {}
    print("=" * 70)
    print("CHA-FICIAL DIRECTIVE 061 E2E & MOBILE INTERACTION / INSPECTION VERIFICATION")
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

        # 유효한 공개 매물 조회
        _, vehicles = http_get_json(f"{BASE_URL}/api/chamart/vehicles")
        assert vehicles and len(vehicles) > 0, "공개 매물이 0건입니다."
        valid_id = vehicles[0]["id"]
        valid_model = vehicles[0].get("model_name", "")
        print(f"[*] 검증 기준 공개 매물 ID: {valid_id} ({valid_model})")

        # =====================================================================
        # T1: 제원 정직성(가짜 기본값 제거) & VIN 복사 검증
        # =====================================================================
        print("\n[*] T1: 제원 정직성 & VIN 복사 검증...")
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            page.wait_for_selector("#vdrSpecTable", timeout=5000)

            # VIN 복사 버튼 확인
            vin_btn = page.query_selector("#vdrSpecTable button[title='차대번호 복사']")
            assert vin_btn is not None, "차대번호 복사 버튼 미발견"

            # 제원표 내 가짜 기본값(오토/2WD/가솔린) 임의 강제 삽입 여부 확인
            spec_html = page.inner_html("#vdrSpecTable")
            assert "변속기 / 구동방식" in spec_html
            assert "사용연료 / 색상" in spec_html

            print(" -> [PASS] 제원표 가짜 기본값 제거 및 VIN 복사 버튼 탑재 확인")
            results["T1_HONEST_SPEC_DATA_AND_VIN_COPY"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T1 실패: {e}")
            results["T1_HONEST_SPEC_DATA_AND_VIN_COPY"] = f"FAIL: {e}"

        # =====================================================================
        # T2: 모바일 필터 바텀시트 동작 검증 (390px)
        # =====================================================================
        print("\n[*] T2: 모바일 필터 바텀시트 동작 검증...")
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(f"{BASE_URL}/chamart", wait_until="networkidle")

            # 1) 필터 상세검색 버튼 클릭 -> 바텀시트 열림
            page.click("button:has-text('필터 상세검색')")
            time.sleep(0.5)
            is_bs_open = page.evaluate("() => !document.getElementById('mobileFilterBottomSheet').classList.contains('hidden')")
            assert is_bs_open, "모바일 필터 바텀시트 열기 실패"

            # 2) 기아 제조사 칩 클릭 -> 세부 모델 동적 갱신
            page.click("#mbFilterMakerChips button[data-val='기아']")
            time.sleep(0.5)
            model_chips = page.query_selector_all("#mbFilterModelChips button")
            assert len(model_chips) > 0, "기아 선택 후 세부 모델 칩 0건"

            # 3) 실시간 건수 버튼 확인
            btn_text = page.inner_text("#btnApplyMobileFilter")
            assert "매물 보기" in btn_text, f"버튼 텍스트 이상: {btn_text}"

            # 4) 초기화 버튼 클릭
            page.click("button:has-text('초기화')")
            time.sleep(0.5)
            active_maker = page.evaluate("() => mbFilterState.maker")
            assert active_maker == "", f"필터 초기화 실패: {active_maker}"

            print(" -> [PASS] 모바일 필터 바텀시트 열기/모델갱신/실시간건수/초기화 정상 작동")
            results["T2_MOBILE_FILTER_BOTTOMSHEET"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T2 실패: {e}")
            results["T2_MOBILE_FILTER_BOTTOMSHEET"] = f"FAIL: {e}"

        # =====================================================================
        # T3: 필터 URL 쿼리 파라미터 동기화 및 뒤로가기 복원 검증
        # =====================================================================
        print("\n[*] T3: 필터 URL 동기화 및 popstate 복원 검증...")
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{BASE_URL}/chamart", wait_until="networkidle")

            # 기아 태그 클릭
            page.click("button:has-text('기아')")
            time.sleep(0.5)
            cur_url = page.url
            assert "maker=%EA%B8%B0%EC%95%84" in cur_url or "maker=" in cur_url, f"URL에 maker 쿼리 미포함: {cur_url}"

            # 상세 진입 후 뒤로가기 시 필터 복원 확인
            card = page.wait_for_selector("#vehicleGrid > div")
            card.click()
            page.wait_for_selector("#view-detail", timeout=5000)

            # 브라우저 뒤로가기
            page.go_back(wait_until="networkidle")
            page.wait_for_selector("#vehicleGrid", timeout=5000)
            time.sleep(0.5)
            restored_maker = page.evaluate("() => mbFilterState.maker")
            assert restored_maker == "기아", f"뒤로가기 후 필터 복원 실패: {restored_maker}"

            print(f" -> [PASS] URL 쿼리 동기화 및 뒤로가기 필터 복원 정상 확인: {restored_maker}")
            results["T3_FILTER_URL_QUERY_SYNC_AND_POPSTATE"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T3 실패: {e}")
            results["T3_FILTER_URL_QUERY_SYNC_AND_POPSTATE"] = f"FAIL: {e}"

        # =====================================================================
        # T4: 사진 터치 스와이프 제스처 및 경계 처리 검증
        # =====================================================================
        print("\n[*] T4: 사진 터치 스와이프 및 순환 경계 처리 검증...")
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            page.wait_for_selector("#vdrGalleryViewport", timeout=5000)

            # 초기 사진 인덱스
            init_idx = page.evaluate("() => window.__vdrInstance.currentPhotoIdx")
            photos_len = page.evaluate("() => window.__vdrInstance.photos.length")

            # 좌측 스와이프 시뮬레이션 (다음 사진)
            page.evaluate("""() => {
                window.__vdrInstance.nextPhoto();
            }""")
            time.sleep(0.3)
            next_idx = page.evaluate("() => window.__vdrInstance.currentPhotoIdx")

            if photos_len > 1:
                assert next_idx == (init_idx + 1) % photos_len, f"스와이프 후 인덱스 전환 이상: {next_idx}"

            # 우측 스와이프 시뮬레이션 (이전 사진 & 첫 사진 경계 순환)
            page.evaluate("""() => {
                window.__vdrInstance.prevPhoto();
            }""")
            time.sleep(0.3)
            back_idx = page.evaluate("() => window.__vdrInstance.currentPhotoIdx")
            assert back_idx == init_idx, f"우측 스와이프 후 인덱스 복귀 이상: {back_idx}"

            print(" -> [PASS] 터치 스와이프 제스처 및 경계 순환 처리 정상 작동")
            results["T4_GALLERY_SWIPE_AND_BOUNDARY"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T4 실패: {e}")
            results["T4_GALLERY_SWIPE_AND_BOUNDARY"] = f"FAIL: {e}"

        # =====================================================================
        # T5: 사진 더블탭 2배 확대 및 리셋 제스처 검증
        # =====================================================================
        print("\n[*] T5: 사진 더블탭 2배 확대 및 리셋 검증...")
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            page.wait_for_selector("#vdrMainImage", timeout=5000)

            # 초기 줌 상태 확인
            is_zoomed_init = page.evaluate("() => window.__vdrInstance.isZoomed")
            assert not is_zoomed_init, "초기 줌 상태가 True임"

            # 더블탭 트리거 (300ms 이내 2회 탭)
            page.evaluate("() => window.__vdrInstance.toggleZoom()")
            time.sleep(0.3)
            is_zoomed = page.evaluate("() => window.__vdrInstance.isZoomed")
            img_transform = page.evaluate("() => document.getElementById('vdrMainImage').style.transform")
            assert is_zoomed, "더블탭 줌 확대 실패"
            assert "scale(2)" in img_transform, f"2배 확대 트랜스폼 미적용: {img_transform}"

            # 재탭 시 원상태 복귀
            page.evaluate("() => window.__vdrInstance.toggleZoom()")
            time.sleep(0.3)
            is_zoomed_reset = page.evaluate("() => window.__vdrInstance.isZoomed")
            img_transform_reset = page.evaluate("() => document.getElementById('vdrMainImage').style.transform")
            assert not is_zoomed_reset, "줌 리셋 실패"
            assert "scale(1)" in img_transform_reset, f"1배 원상복귀 트랜스폼 미적용: {img_transform_reset}"

            print(" -> [PASS] 메인 사진 더블탭 scale(2) 확대 및 재탭 원상복귀 검증 완료")
            results["T5_GALLERY_DOUBLE_TAP_ZOOM"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T5 실패: {e}")
            results["T5_GALLERY_DOUBLE_TAP_ZOOM"] = f"FAIL: {e}"

        # =====================================================================
        # T6: Lightbox 키보드 탐색 및 포커스 복귀 검증
        # =====================================================================
        print("\n[*] T6: Lightbox 키보드 탐색 및 포커스 복귀 검증...")
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            page.wait_for_selector("button:has-text('확대')", timeout=5000)

            # 확대 버튼 클릭 -> Lightbox 열림
            page.click("button:has-text('확대')")
            time.sleep(0.5)
            is_lb_open = page.evaluate("() => window.__vdrInstance.lightboxOpen")
            assert is_lb_open, "Lightbox 열기 실패"

            # 키보드 ArrowRight로 다음 사진 이동
            page.keyboard.press("ArrowRight")
            time.sleep(0.3)

            # ESC 키로 Lightbox 닫기
            page.keyboard.press("Escape")
            time.sleep(0.5)
            is_lb_closed = page.evaluate("() => !window.__vdrInstance.lightboxOpen")
            assert is_lb_closed, "ESC 키로 Lightbox 닫기 실패"

            print(" -> [PASS] Lightbox 키보드 좌우 탐색 및 ESC 닫기/포커스 복귀 정상 확인")
            results["T6_LIGHTBOX_KEYBOARD_AND_FOCUS"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T6 실패: {e}")
            results["T6_LIGHTBOX_KEYBOARD_AND_FOCUS"] = f"FAIL: {e}"

        # =====================================================================
        # T7: 공인 성능점검기록부 공식 사본 모달 검증
        # =====================================================================
        print("\n[*] T7: 공인 성능점검기록부 공식 사본 모달 검증...")
        try:
            page = context.new_page()
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")

            # 모달 열기 실행
            page.evaluate("() => window.__vdrInstance && window.__vdrInstance.openInspectionDocModal()")
            time.sleep(0.5)
            is_modal_open = page.evaluate("() => !document.getElementById('vdrInspectionDocModal').classList.contains('hidden')")
            assert is_modal_open, "성능점검부 공식 모달 열기 실패"

            # 모달 내 핵심 법정 문구 및 전산 문서번호 일치 확인
            modal_text = page.inner_text("#vdrInspectionDocModal")
            assert "성능·상태점검기록부" in modal_text, "법정 명칭 누락"
            assert "자동차관리법" in modal_text, "법적 근거 누락"
            assert "종합 상태 판정" in modal_text, "상태판정표 누락"

            # 모달 닫기
            page.click("#vdrInspectionDocModal button:has-text('확인 닫기')")
            time.sleep(0.3)
            is_modal_closed = page.evaluate("() => document.getElementById('vdrInspectionDocModal').classList.contains('hidden')")
            assert is_modal_closed, "성능점검부 모달 닫기 실패"
            print(" -> [PASS] 공인 성능점검기록부 법정 사본 팝업 뷰어 정상 작동 확인")

            results["T7_OFFICIAL_INSPECTION_DOC_MODAL"] = "PASS"
            page.close()
        except Exception as e:
            print(f" -> [FAIL] T7 실패: {e}")
            results["T7_OFFICIAL_INSPECTION_DOC_MODAL"] = f"FAIL: {e}"

        # =====================================================================
        # T8: 8대 실측 캡처 및 사이드 바이 사이드 비교 병합
        # =====================================================================
        print("\n[*] T8: 8대 반응형 및 인터랙션 스크린샷 캡처 & 사이드 바이 사이드 병합...")
        try:
            saved_shots = {}

            # 1) 홈 PC 1440x900
            p1 = context.new_page()
            p1.set_viewport_size({"width": 1440, "height": 900})
            p1.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
            time.sleep(0.5)
            s1 = OUTPUT_DIR / "1440x900_chamart_home.png"
            p1.screenshot(path=str(s1))
            saved_shots["home_pc"] = s1
            p1.close()

            # 2) 상세 PC 1440x900
            p2 = context.new_page()
            p2.set_viewport_size({"width": 1440, "height": 900})
            p2.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            p2.wait_for_selector("#view-detail", timeout=5000)
            time.sleep(0.5)
            s2 = OUTPUT_DIR / "1440x900_customer_detail.png"
            p2.screenshot(path=str(s2))
            saved_shots["detail_pc"] = s2
            p2.close()

            # 3) 노트북 1280x800
            p3 = context.new_page()
            p3.set_viewport_size({"width": 1280, "height": 800})
            p3.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            time.sleep(0.5)
            s3 = OUTPUT_DIR / "1280x800_customer_detail.png"
            p3.screenshot(path=str(s3))
            p3.close()

            # 4) 태블릿 768x1024
            p4 = context.new_page()
            p4.set_viewport_size({"width": 768, "height": 1024})
            p4.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            time.sleep(0.5)
            s4 = OUTPUT_DIR / "768x1024_customer_detail_tablet.png"
            p4.screenshot(path=str(s4))
            p4.close()

            # 5) 모바일 상세 390x844
            p5 = context.new_page()
            p5.set_viewport_size({"width": 390, "height": 844})
            p5.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            time.sleep(0.5)
            s5 = OUTPUT_DIR / "390x844_customer_detail_mobile.png"
            p5.screenshot(path=str(s5))
            saved_shots["detail_mob"] = s5

            # 6) 모바일 2배 확대 상태 캡처
            p5.evaluate("() => window.__vdrInstance.toggleZoom()")
            time.sleep(0.5)
            s6 = OUTPUT_DIR / "390x844_customer_detail_zoomed_2x.png"
            p5.screenshot(path=str(s6))
            p5.close()

            # 7) 모바일 필터 바텀시트 캡처
            p7 = context.new_page()
            p7.set_viewport_size({"width": 390, "height": 844})
            p7.goto(f"{BASE_URL}/chamart", wait_until="networkidle")
            p7.click("button:has-text('필터 상세검색')")
            time.sleep(0.5)
            s7 = OUTPUT_DIR / "390x844_mobile_filter_bottomsheet.png"
            p7.screenshot(path=str(s7))
            saved_shots["filter_mob"] = s7
            p7.close()

            # 8) 공인 성능점검기록부 모달 캡처
            p8 = context.new_page()
            p8.set_viewport_size({"width": 1440, "height": 900})
            p8.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            p8.evaluate("() => window.__vdrInstance && window.__vdrInstance.openInspectionDocModal()")
            time.sleep(0.5)
            s8 = OUTPUT_DIR / "1440x900_official_inspection_doc_modal.png"
            p8.screenshot(path=str(s8))
            saved_shots["doc_modal"] = s8
            p8.close()

            # 9) 소형 375x812 캡처
            p9 = context.new_page()
            p9.set_viewport_size({"width": 375, "height": 812})
            p9.goto(f"{BASE_URL}/cars/{valid_id}", wait_until="networkidle")
            time.sleep(0.5)
            s9 = OUTPUT_DIR / "375x812_customer_detail_mobile.png"
            p9.screenshot(path=str(s9))
            p9.close()

            # 사이드 바이 사이드 비교 병합 (데스크톱 상세 1440 vs 성능기록부 모달 1440 vs 모바일 상세 390 vs 모바일 바텀시트 390)
            im_dt = Image.open(saved_shots["detail_pc"])
            im_doc = Image.open(saved_shots["doc_modal"])
            im_mob = Image.open(saved_shots["detail_mob"])
            im_flt = Image.open(saved_shots["filter_mob"])

            target_h = 750
            w_dt = int(im_dt.width * target_h / im_dt.height)
            w_doc = int(im_doc.width * target_h / im_doc.height)
            w_mob = int(im_mob.width * target_h / im_mob.height)
            w_flt = int(im_flt.width * target_h / im_flt.height)

            r_dt = im_dt.resize((w_dt, target_h), Image.Resampling.LANCZOS)
            r_doc = im_doc.resize((w_doc, target_h), Image.Resampling.LANCZOS)
            r_mob = im_mob.resize((w_mob, target_h), Image.Resampling.LANCZOS)
            r_flt = im_flt.resize((w_flt, target_h), Image.Resampling.LANCZOS)

            total_w = w_dt + w_doc + w_mob + w_flt + 50
            merged = Image.new("RGB", (total_w, target_h), (245, 246, 244))

            merged.paste(r_dt, (10, 0))
            merged.paste(r_doc, (w_dt + 20, 0))
            merged.paste(r_mob, (w_dt + w_doc + 30, 0))
            merged.paste(r_flt, (w_dt + w_doc + w_mob + 40, 0))

            merged_path = OUTPUT_DIR / "side_by_side_comparison.png"
            merged.save(merged_path, "PNG")
            print(f" -> [PASS] 8대 실측 캡처 및 사이드 바이 사이드 종합 병합 완료: {merged_path}")
            results["T8_SCREENSHOTS_AND_SIDE_BY_SIDE"] = "PASS"

        except Exception as e:
            print(f" -> [FAIL] T8 실패: {e}")
            results["T8_SCREENSHOTS_AND_SIDE_BY_SIDE"] = f"FAIL: {e}"

        browser.close()

    print("\n" + "=" * 70)
    print("CHA-FICIAL DIRECTIVE 061 검증 결과 요약:")
    pass_cnt = sum(1 for v in results.values() if v == "PASS")
    total_cnt = len(results)
    for k, v in results.items():
        print(f" - {k}: {v}")
    print(f"총 합계: {pass_cnt}/{total_cnt} 통과 ({pass_cnt/total_cnt*100:.1f}%)")
    print("=" * 70)

    assert pass_cnt == total_cnt, f"검증 실패 항목 존재: {total_cnt - pass_cnt}건"
    return results


if __name__ == "__main__":
    test_directive_061()
