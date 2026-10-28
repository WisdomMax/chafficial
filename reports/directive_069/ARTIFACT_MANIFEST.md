# CHA-FICIAL DIRECTIVE 069: 산출물 매니페스트 (Artifact Manifest)

본 매니페스트는 DIRECTIVE 069 (엔카급 고객 쇼룸 전면 재구축 및 품질 합격 검증) 작업으로 생성된 모든 산출물 파일의 경로와 규격을 명시합니다.

---

## 1. 이미지 및 스크린샷 산출물 (`reports/directive_069/`)

| 파일명 | 해상도 / 규격 | 설명 |
| :--- | :---: | :--- |
| [`side_by_side_comparison_069.png`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/side_by_side_comparison_069.png) | 1920 × 1080 | **[필수] 전/후 1:1 종합 대시보드 비교 이미지** (PC 리스트, PC 상세, PC 앨범, 모바일) |
| [`chamart_1440_list.png`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/chamart_1440_list.png) | 1440 × 900 | **PC 기본 뷰 (가로 리스트형)**: 첫 화면 매물 3대 이상 직접 노출 |
| [`chamart_1440_album.png`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/chamart_1440_album.png) | 1440 × 900 | **PC 선택 뷰 (3열 앨범형 그리드)**: 5:3 비율 대형 카드 전환 |
| [`chamart_1440_detail.png`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/chamart_1440_detail.png) | 1440 × 900 | **PC 상세 페이지**: 상단 중복 가격 제거 & 우측 350px 고정 구매 패널 |
| [`chamart_390_mobile_list.png`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/chamart_390_mobile_list.png) | 390 × 844 | **모바일 표준 뷰 (목록형)**: 132px 썸네일 기반 2열 반응형 |
| [`chamart_390_mobile_detail.png`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/chamart_390_mobile_detail.png) | 390 × 844 | **모바일 상세 뷰**: 하단 고정 전화/예약 CTA 및 최적화 레이아웃 |
| [`chamart_390_mobile_compare.png`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/chamart_390_mobile_compare.png) | 390 × 844 | **모바일 2대 차량 비교 모달**: 가로 스크롤 테이블 및 제원 대조 |
| [`chamart_1024_tablet.png`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/chamart_1024_tablet.png) | 1024 × 768 | **태블릿 가로 뷰**: 200px 썸네일 축소 및 오버플로 0건 검증 |
| [`chamart_prod_1440_empty.png`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/chamart_prod_1440_empty.png) | 1440 × 900 | **운영 쇼룸 (/chamart)**: 승인 실차 0대 정직한 준비 중 안내 상태 |

---

## 2. 실차 스튜디오 사진 자산 (`src/chaficial/platform/ui/static/img/vehicles/`)

| 파일명 | 해상도 / 크기 | 대상 차종 및 스튜디오 뷰 |
| :--- | :---: | :--- |
| [`grandeur_gn7/front.jpg`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platform/ui/static/img/vehicles/grandeur_gn7/front.jpg) | 600 KB (5:3) | 현대 디 올 뉴 그랜저 GN7 어비스 블랙 펄, 3/4 정밀 스튜디오 촬영 |
| [`k8/front.jpg`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platform/ui/static/img/vehicles/k8/front.jpg) | 612 KB (5:3) | 기아 K8 2.5 가솔린 스노우 화이트 펄, 다이아몬드 그릴 스튜디오 촬영 |
| [`sorento/front.jpg`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/src/chaficial/platform/ui/static/img/vehicles/sorento/front.jpg) | 645 KB (5:3) | 기아 쏘렌토 4세대 HEV 스노우 화이트 펄, 쇼룸 조명 촬영 |

---

## 3. 리포트 및 자동화 테스트 산출물

- [`VERIFICATION.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/VERIFICATION.md): DIRECTIVE 069 종합 검증 보고서
- [`ENCAR_BENCHMARK_COMPARISON.md`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/ENCAR_BENCHMARK_COMPARISON.md): 엔카 공식 보도자료 1:1 대조 분석
- [`TEST_RESULTS.txt`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/reports/directive_069/TEST_RESULTS.txt): Playwright 반응형 뷰포트 오버플로 전수 검사 로그 (100% ALL PASS)
- [`scripts/verify_directive_069_playwright.py`](file:///Volumes/NVME/7.AI_vibe_coding/20261021_Used_Car_AI/scripts/verify_directive_069_playwright.py): 자동화 검증 및 캡처 스크립트
