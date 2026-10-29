은 좌우 여백을 없앤다.

권장 시작 구조:

<main class="mx-auto w-full max-w-[1480px] px-4 md:px-6 xl:px-8">
  <div class="grid grid-cols-1 gap-6 lg:grid-cols-[264px_minmax(0,1fr)]">

    <aside id="searchSidebar"
           class="hidden min-w-0 lg:block">
      <!-- 제조사, 모델, 가격, 연식, 연료, 검증 조건 -->
    </aside>

    <section id="vehicleResults" class="min-w-0">
      <!-- 검색결과 및 정렬 -->

      <div id="vehicleGrid"
           class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        <!-- 차량 카드 -->
      </div>
    </section>

  </div>
</main>

이는 레이아웃 예시다. 기존 068의 ID, 이벤트 핸들러, 실제 데이터 연결을 유지하면서 적용한다. 실제 카드 수와 브레이크포인트는 비교 캡처를 통해 결정한다.

2-2. 시각적 위계

검색결과 개수와 정렬 메뉴를 같은 컨트롤 영역에 배치한다.

좌측 필터는 섹션 제목, 선택 상태, 구분선, 여백을 일관되게 구성한다.

차량 이미지가 화면에서 가장 먼저 인지되도록 한다.

카드마다 차량명, 사양, 가격의 시각적 위계를 통일한다.

불필요한 그림자, 두꺼운 테두리, 과도한 라운딩을 제거한다.

페이지 전체의 제목 크기, 버튼 높이, 여백 규칙을 통일한다.

권장 기본 디자인 토큰:

:root {
  --brand-primary: #176B68;
  --brand-hover: #125653;
  --brand-navy: #101A2A;

  --text-primary: #18212B;
  --text-secondary: #64748B;

  --surface: #FFFFFF;
  --page-bg: #F7F8FA;
  --border: #E5E7EB;

  --radius-card: 10px;
  --radius-control: 6px;
}

장식적인 색상 사용을 줄이고, 가격과 중요한 구매 행동만 강하게 강조한다.

TASK 3. 차량 카드 및 상세 페이지 완성도 개선 (P0)

3-1. 차량 카드

앨범형과 리스트형에서 동일한 정보 배열을 유지한다.

권장 정보 순서:

차량 사진

제조사 + 모델명 + 세부 트림

연식 · 주행거리 · 연료

판매 지역

확인된 차량 상태 및 성능기록 정보

정찰 판매가

관심 차량 및 비교 기능

차량명은 충분히 읽히도록 표시하고, 정찰 판매가는 카드에서 가장 명확한 숫자로 표현한다.

사진 비율은 전 카드에서 통일하고, 로딩 중 레이아웃이 흔들리지 않도록 aspect-ratio를 지정한다.

.vehicle-photo {
  width: 100%;
  aspect-ratio: 5 / 3;
  object-fit: cover;
  object-position: center;
  background: #F1F3F5;
}

.vehicle-title {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.4;
}

.vehicle-spec {
  font-size: 13px;
  color: var(--text-secondary);
}

.vehicle-price {
  font-size: 23px;
  font-weight: 800;
  color: var(--text-primary);
}

5:3은 차마트의 설계 선택이며, 엔카의 공식 고정 규격이라고 단정하지 않는다.

3-2. 상세 페이지

현재 vehicle_detail_renderer.js의 기존 데이터 연결과 구매 기능을 보존하면서 개선한다.

데스크톱에서는 대형 사진 갤러리와 우측 구매정보 패널을 명확하게 분리한다.

우측 패널에는 차량명, 가격, 기본 사양, 검증 상태, 상담 또는 문의 버튼을 배치한다.

차량 상태 정보, 성능점검기록부, 사고·보험 관련 정보, 옵션 정보는 아래쪽에서 명확하게 구획한다.

모바일에서는 사진, 가격, 핵심 정보가 먼저 보이고 하단에 상담 CTA가 접근 가능하도록 한다.

중요: 실제 검증 근거가 없는 차량에는 '무사고', '인증', '보증'이라는 문구를 자동 부여하지 않는다. 모든 상태 라벨은 확인된 데이터와 연결한다.

TASK 4. 검색 UX 및 반응형 품질 확보 (P0)

다음 기능이 모두 동일한 필터 상태를 사용해야 한다.

PC 사이드바

모바일 필터 바텀시트

적용된 필터 칩

검색결과 건수

URL 검색 파라미터

제조사 변경 시 모델 선택이 정상 초기화되어야 하며, 필터 한 개를 해제해도 다른 선택값은 보존되어야 한다.

가격 미확인 차량이 '1,500만원 이하' 등의 가격 검색에 잘못 포함되지 않도록 테스트한다.

화면 폭은 최소 360, 390, 768, 1024, 1440, 1920px에서 확인한다.

필수 기준:

가로 스크롤 발생 0건

가격 및 버튼 잘림 0건

이미지 비율 붕괴 0건

카드 겹침 0건

필터 적용 결과 불일치 0건

모바일 주요 터치 영역 44px 이상 권장

기본 텍스트 대비 WCAG AA 기준 검토

키보드 조작 및 모달 포커스 이동 검증

TASK 5. 디자인 검수 자동화 (P0)

Playwright를 활용해 실제 브라우저에서 증거를 생성한다. DOM 구조만 분석하거나 CSS 규칙만 검사하는 것으로 통과 처리하지 않는다.

최소 자동화 코드 예시:

from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8501"
OUT = Path("reports/directive_069")
OUT.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    (1920, 1080),
    (1440, 900),
    (1024, 768),
    (768, 1024),
    (390, 844),
    (360, 800),
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    for width, height in VIEWPORTS:
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=1
        )

        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        page.goto(
            f"{BASE}/staging/chamart",
            wait_until="networkidle"
        )

        page.locator("#vehicleGrid").wait_for(
            state="visible"
        )

        overflow = page.evaluate("""
            document.documentElement.scrollWidth >
            document.documentElement.clientWidth
        """)

        assert not overflow, f"Horizontal overflow: {width}"
        assert not errors, f"JS errors: {errors}"

        page.screenshot(
            path=str(OUT / f"staging_{width}x{height}.png"),
            full_page=True
        )

        page.close()

    browser.close()

이 코드는 기본 뷰포트·오버플로·JS 오류 검증의 출발점이다. 추가로 앨범/리스트 전환, 필터, 찜, 3대 비교, 상세 진입, 모바일 바텀시트, 운영 0대 상태를 실제 클릭하는 회귀 테스트를 작성한다.

스크린샷은 로딩 완료 후 촬영하고, 브라우저 예외 및 API 실패 기록을 함께 보존한다.

TASK 6. 실제 엔카와 차마트 나란히 비교 (P0)

동일하거나 비교 가능한 화면 크기에서 다음 화면을 비교한다.

엔카 실제 PC 검색결과 vs 차마트 PC 검색결과

엔카 차량 카드 vs 차마트 차량 카드

엔카 상세 정보 배치 vs 차마트 상세 정보 배치

모바일 검색 UI 및 차량 카드 정보 위계

아래 다섯 요소를 중심으로 개선한다.

정보 밀도

차량 사진의 크기와 비중

타이포그래피와 여백

검색 필터의 직관성

구매 문의까지의 이동 편의성

단순히 이미지를 나란히 붙이는 것으로 끝내지 않는다.

각 항목마다 차이점을 기록하고, 차마트 코드에서 어떤 부분을 수정했는지 설명한다.

엔카 원본을 자동 수집할 수 없는 경우에는 공개된 공식 자료 또는 수동 확보한 적법한 참고 화면을 사용한다. 확보하지 못한 원본을 임의로 생성하여 실제 엔카 화면이라고 표시하지 않는다.

TASK 7. 기존 기능 및 공개 데이터 경계 보존 (P0)

디자인 수정으로 기존 기능을 망가뜨리는 것은 금지한다.

반드시 보존할 기능:

운영 쇼룸의 승인된 실차만 공개하는 정책

스테이징 데이터와 운영 데이터의 논리적 공개 경계

상담 접수 및 데이터 저장

관심 차량과 최대 3대 비교

차량 상세 갤러리 및 성능점검 정보

A4 단일 페이지 견적서

기존 API 및 DB 스키마의 호환성

운영과 스테이징은 현재 애플리케이션 계층의 논리적 격리 상태이므로, 이를 물리적 격리라고 표현하지 않는다.

또한 데이터로 전달된 차량명과 기타 텍스트를 innerHTML에 삽입하는 경우 적절한 이스케이프 또는 안전한 DOM API를 사용한다.

TASK 8. 제출 및 승인 조건

다음 증거를 반드시 제출한다.

GitHub 최신 커밋 SHA 및 변경 파일 목록

PC 1920/1440px 앨범형 전체 화면

PC 1440px 리스트형 전체 화면

차량 상세 PC 화면

1024px / 768px 반응형 화면

모바일 390px / 360px 화면

모바일 필터를 실제로 연 화면

비교함 및 찜 기능 동작 화면

운영 쇼룸 0대 상태

엔카 참고 화면과 차마트의 비교 이미지

Playwright 테스트 및 기존 P0 회귀 테스트 결과

결과 파일은 reports/directive_069/에 보관한다.

최종 평가 배점:

평가 항목	배점
엔카 기준 구조 및 시각적 완성도	40
차량 정보의 위계와 가독성	20
모바일 및 태블릿 UX	15
필터·비교·상담 동작 품질	15
데이터 무결성 및 운영 안정성	10
합계	100

합격 조건은 독립 검수 85점 이상 및 P0 결함 0건이다. 자체 보고서의 자평 점수를 최종 점수로 사용하지 않는다.

최종 명령

기능을 많이 만든 웹사이트가 아니라, 실제 고객이 중고차를 사고 싶어지는 웹사이트를 만들어라.

디자인을 검수하면서 부족한 부분이 발견되면 자체 수정하되, 근거 없이 '엔카 수준 완벽 구현'이라고 선언하지 말 것.

최신 코드와 원본 스크린샷을 원격 저장소에 제출한 후, ChatGPT 총괄 디자인 감독에게 독립적인 최종 평가를 요청하라.

DIRECTIVE 069 발령.

이번에는 특히 예쁜 화면 한 장이 아니라 실제 고객이 클릭해서 차량을 찾고 구매 문의까지 가는 화면 전체를 검사하도록 했습니다.

다음 보고에서 069의 실제 캡처와 코드를 확인할 수 있으면, 디자인 합격 여부뿐 아니라 어디가 촌스럽고 무엇이 부족한지까지 화면별로 구체적으로 지적하겠습니다.

ChatGPT는 실수할 수 있습니다. 중요한 정보는 확인하세요.
최신 응답




추론 수준
High
⋮⋮
⋮⋮