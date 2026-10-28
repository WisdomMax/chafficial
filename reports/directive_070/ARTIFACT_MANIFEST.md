# CHA-FICIAL DIRECTIVE 070: 산출물 매니페스트 (Artifact Manifest)

## 1. 개요
- **목적**: 100대 엔카 스타일 가상 매물 구축 및 UI 디자인 벤치마크 검증 산출물 목록
- **기준 커밋**: `0ba58f9`
- **검증 일시**: 2026-10-29 04:18 KST

## 2. 생성 및 수정된 코드 파일
| 파일 경로 | 구분 | 설명 |
|---|---|---|
| [`reports/ui_fixtures/chamart_100.json`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/ui_fixtures/chamart_100.json) | 신규 | 100대 가상 매물 순수 JSON Fixture (아반떼 35, 레이 25, 모닝 25, 캐스퍼 10, K3 5) |
| [`reports/ui_fixtures/photo_manifest.json`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/ui_fixtures/photo_manifest.json) | 신규 | 21장 5:3 정규화 실차 사진 매니페스트 |
| [`scripts/build_ui_photo_assets.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/scripts/build_ui_photo_assets.py) | 신규 | 위키미디어 코먼스 실차 사진 21장 수집 및 5:3(800x480) 크롭/리사이즈 |
| [`scripts/generate_chamart_ui_100.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/scripts/generate_chamart_ui_100.py) | 신규 | 100대 가상 매물 제원 및 정찰가, 월납입금, 옵션 데이터 생성기 |
| [`scripts/verify_directive_070_playwright.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/scripts/verify_directive_070_playwright.py) | 신규 | Playwright 기반 12종 시나리오 자동 검증 및 대시보드 합성기 |
| [`src/chaficial/platform/app.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platform/app.py) | 수정 | `/api/staging/ui-fixtures/vehicles` 및 단일 상세 엔드포인트 격리 서빙 |
| [`src/chaficial/platform/ui/chamart_staging.html`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platform/ui/chamart_staging.html) | 수정 | 100대 API 연동, 20대 단위 페이지네이션, 동적 모델 필터 및 카운트 연동 |
| [`src/chaficial/platform/ui/static/css/chamart-listing-v2.css`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platform/ui/static/css/chamart-listing-v2.css) | 수정 | 엔카 스타일 `.cm-pagination-wrapper`, `.cm-page-btn` 스타일 추가 |

## 3. 검수 스크린샷 에셋 (12종 + 1종 대시보드)
| 파일명 | 해상도 | 주요 검증 내용 |
|---|---|---|
| `01_pc_1440_list_100_page1.png` | 1440×900 | 100대 PC 기본 가로 리스트형 (1페이지 20대 노출, 238px 좌측 필터) |
| `02_pc_avante_filter_35.png` | 1440×900 | 현대 아반떼 필터 선택 시 35대 즉시 필터링 |
| `03_pc_ray_filter_25.png` | 1440×900 | 기아 레이 필터 선택 시 25대 즉시 필터링 |
| `04_pc_morning_filter_25.png` | 1440×900 | 기아 모닝 필터 선택 시 25대 즉시 필터링 |
| `05_pc_1440_album_grid.png` | 1440×900 | 3열 앨범형 그리드 전환 (20대 정렬) |
| `06_pc_vehicle_detail_1440.png` | 1440×900 | 단일 차량 상세 뷰 (UI-0001 아반떼 실차 사진 및 상담 패널) |
| `07_mobile_390_list.png` | 390×844 | 모바일 수직 리스트형 (가로스크롤 0px) |
| `08_mobile_vehicle_detail_390.png` | 390×844 | 모바일 단일 차량 상세 (가로스크롤 0px) |
| `09_mobile_filter_bottomsheet.png` | 390×844 | 모바일 상세 필터 바텀시트 및 모델 칩 |
| `10_compare_modal_3cars.png` | 1440×900 | 최대 3대 차량 상세 제원 비교 모달 |
| `11_pc_pagination_page5.png` | 1440×900 | 100대 중 5페이지 이동 (81~100번째 매물 노출) |
| `12_empty_search_result.png` | 1440×900 | 검색 결과 0건 시 친절한 안내 및 리셋 가이드 |
| `side_by_side_comparison_070.png` | 1480×1540 | 대표 6개 화면 통합 검수 대시보드 |
