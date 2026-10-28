#!/usr/bin/env python3
"""DIRECTIVE 064: chamart.html 프런트엔드 패치 스크립트."""

with open('src/chaficial/platform/ui/chamart.html', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. 헤더 우측 1544-0000 제거 및 모드 스위처 추가
target_header_right = """            <!-- 우측: 고객센터 및 방문상담 안내 -->
            <div class="flex items-center space-x-4">
                <a href="tel:1544-0000" class="text-xs sm:text-sm font-bold text-slate-800 hover:text-black flex items-center space-x-1.5 transition-colors">
                    <i data-lucide="phone-call" class="w-4 h-4 text-[#171B1E]"></i>
                    <span class="hidden sm:inline font-normal text-slate-500">고객센터</span>
                    <span class="text-[#171B1E] font-bold">1544-0000</span>
                </a>
                <button onclick="scrollToConsultation()" class="hidden sm:inline-flex items-center text-xs font-bold bg-[#C8FF3D] hover:bg-[#B5F028] text-[#171B1E] px-3.5 py-2 rounded-lg transition-colors cursor-pointer border border-[#AEEB20]/60 shadow-xs">
                    <i data-lucide="calendar" class="w-3.5 h-3.5 mr-1.5 text-[#171B1E]"></i>
                    방문 시승 예약
                </button>
            </div>"""

replace_header_right = """            <!-- 우측: 모드 스위처 & 1:1 방문상담 안내 (DIRECTIVE 064: 1544-0000 임시번호 전수 제거) -->
            <div class="flex items-center space-x-2 sm:space-x-3">
                <!-- 운영 실차 vs 데모 검수 모드 토글 스위치 -->
                <button type="button" onclick="toggleShowroomMode()" id="btnModeToggle" class="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-700 flex items-center space-x-1.5 transition-colors cursor-pointer" title="실차 운영 모드와 UI 디자인 검수 모드를 전환합니다.">
                    <span id="modeStatusDot" class="w-2 h-2 rounded-full bg-slate-400"></span>
                    <span id="modeStatusText">운영 모드</span>
                </button>
                <button onclick="scrollToConsultation()" class="inline-flex items-center text-xs font-bold bg-[#C8FF3D] hover:bg-[#B5F028] text-[#171B1E] px-3 py-2 rounded-lg transition-colors cursor-pointer border border-[#AEEB20]/60 shadow-xs">
                    <i data-lucide="calendar" class="w-3.5 h-3.5 mr-1.5 text-[#171B1E]"></i>
                    1:1 방문 예약
                </button>
            </div>"""

# 2. 헤더 아래에 데모 모드 배너 추가
target_header_end = '</header>'
replace_header_end = """</header>
    <!-- 데모/디자인 검수 모드 고정 안내 배너 (DIRECTIVE 064: 운영 실차와 UI 검수 데모 분리) -->
    <div id="demoModeBanner" class="hidden bg-[#171B1E] text-white py-2 px-4 text-xs border-b border-[#C8FF3D]/40">
        <div class="max-w-[1280px] mx-auto flex items-center justify-between">
            <div class="flex items-center space-x-2">
                <span class="bg-[#C8FF3D] text-[#171B1E] text-[10px] font-bold px-1.5 py-0.5 rounded">UI 검수 모드</span>
                <span class="text-slate-300">현재 화면은 엔카·K Car 기준 UI/UX 레이아웃 검수용 시연 모드입니다. (실제 판매 차량이 아님)</span>
            </div>
            <button onclick="setMode('prod')" class="text-[11px] text-[#C8FF3D] hover:underline cursor-pointer">
                실차 운영 모드로 전환 (0대) ➔
            </button>
        </div>
    </div>"""

# 3. 검색 Hero 박스 상하 여백 슬림화 (PC 1440x900 최적화)
target_hero = """            <!-- 단정한 검색 및 쇼룸 헤더 (AI 템플릿 제거, 실제 자동차 포털 구조) -->
            <div class="bg-white rounded-xl border border-[#E2E6EA] p-6 sm:p-8 space-y-6">
                <div class="max-w-2xl space-y-2">
                    <div class="inline-flex items-center space-x-1.5 text-xs font-bold text-[#171B1E] bg-[#C8FF3D]/25 px-2.5 py-1 rounded border border-[#C8FF3D]/60">
                        <i data-lucide="shield-check" class="w-3.5 h-3.5 text-[#171B1E]"></i>
                        <span>소유권 및 성능기록부 100% 대조 인증</span>
                    </div>
                    <h1 class="text-2xl sm:text-3xl font-bold text-[#171B1E] tracking-tight">
                        장한평 전시장 실차 매물 검색
                    </h1>
                    <p class="text-xs sm:text-sm text-slate-600 leading-relaxed">
                        허위 매물 없이 실제 전시장에 입고된 직영 및 제휴 승인 차량만을 정직하게 공개합니다.
                    </p>
                </div>"""

replace_hero = """            <!-- 단정한 검색 및 쇼룸 헤더 (DIRECTIVE 064: PC 1440x900 화면 위계 압축 최적화) -->
            <div class="bg-white rounded-xl border border-[#E2E6EA] p-4 sm:p-5 space-y-4">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div>
                        <h1 class="text-xl sm:text-2xl font-bold text-[#171B1E] tracking-tight flex items-center gap-2">
                            <span>장한평 전시장 실차 매물 검색</span>
                            <span class="text-[11px] font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">정찰제</span>
                        </h1>
                        <p class="text-xs text-slate-500 mt-0.5">
                            허위 매물 없이 실제 전시장에 입고된 실차 매물만을 정직하게 공개합니다.
                        </p>
                    </div>
                    <div class="hidden sm:inline-flex items-center space-x-1.5 text-xs font-semibold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200 shrink-0">
                        <i data-lucide="shield-check" class="w-3.5 h-3.5 text-emerald-600"></i>
                        <span>소유권·성능 100% 대조</span>
                    </div>
                </div>"""

# 4. 비교 모달 가로스크롤 안내 인디케이터 추가
target_compare_scroll = """            <!-- 비교 테이블 컨테이너 -->
            <div class="flex-1 overflow-y-auto overflow-x-auto py-4 custom-scrollbar">
                <div id="compareTableContainer" class="min-w-[620px]">
                    <!-- 동적 렌더링 영역 -->
                </div>
            </div>"""

replace_compare_scroll = """            <!-- 비교 테이블 컨테이너 (DIRECTIVE 064: 모바일 가로스크롤 힌트 추가) -->
            <div class="relative flex-1 overflow-hidden flex flex-col">
                <!-- 모바일 가로스크롤 유도 힌트 바 -->
                <div class="sm:hidden flex items-center justify-between px-2 py-1.5 bg-slate-100 border-b border-slate-200 text-[11px] text-slate-600">
                    <span class="flex items-center font-medium">
                        <i data-lucide="chevrons-right" class="w-3.5 h-3.5 text-slate-500 mr-1 animate-pulse"></i>
                        좌우로 밀어서 3대 차량 상세 비교
                    </span>
                    <span class="text-[10px] text-slate-400">가로 스크롤 가능 ➔</span>
                </div>
                <div class="flex-1 overflow-y-auto overflow-x-auto py-2 custom-scrollbar">
                    <div id="compareTableContainer" class="min-w-[620px]">
                        <!-- 동적 렌더링 영역 -->
                    </div>
                </div>
            </div>"""

# 5. loadPublicVehicles 모드 파라미터 연동 및 모드 관리 스크립트
target_load_func = """        // 고객용 공개 실차 목록 로드 및 필터 렌더링
        async function loadPublicVehicles() {
            try {
                const res = await fetch('/api/chamart/vehicles');
                if (!res.ok) throw new Error('매물 목록 조회 실패');
                publicVehicles = await res.json();

                // URL 쿼리 파라미터로부터 필터 복원
                initFiltersFromUrl();
                renderVehiclesList();
                renderMbFilterChips();
                renderMbModelChips();
                updateFilterBadge();
                updateAllFavoritesUi();
                updateCompareFloatingBar();
            } catch (err) {
                const grid = document.getElementById('vehicleGrid');
                if (grid) {
                    grid.innerHTML = `
                        <div class="col-span-full py-12 text-center text-rose-500 bg-white rounded-xl border border-rose-200">
                            <p class="font-bold text-sm">매물 데이터를 불러오는 중 오류가 발생했습니다.</p>
                            <p class="text-xs text-slate-500 mt-1">${err.message}</p>
                        </div>
                    `;
                }
            }
        }"""

replace_load_func = """        // DIRECTIVE 064: 모드 관리 (운영 prod vs 데모 demo)
        window.currentShowroomMode = new URLSearchParams(window.location.search).get('mode') === 'demo' ? 'demo' : 'prod';

        function updateModeSwitcherUi() {
            const isDemo = window.currentShowroomMode === 'demo';
            const dot = document.getElementById('modeStatusDot');
            const txt = document.getElementById('modeStatusText');
            const banner = document.getElementById('demoModeBanner');

            if (dot) {
                dot.className = isDemo ? 'w-2 h-2 rounded-full bg-[#C8FF3D] ring-2 ring-[#C8FF3D]/40' : 'w-2 h-2 rounded-full bg-emerald-500';
            }
            if (txt) {
                txt.textContent = isDemo ? 'UI 검수 모드 (3대)' : '실차 운영 모드 (0대)';
            }
            if (banner) {
                banner.classList.toggle('hidden', !isDemo);
            }
        }

        function setMode(mode) {
            window.currentShowroomMode = mode;
            updateModeSwitcherUi();
            const url = new URL(window.location.href);
            if (mode === 'demo') {
                url.searchParams.set('mode', 'demo');
            } else {
                url.searchParams.delete('mode');
            }
            window.history.replaceState({}, '', url.toString());
            loadPublicVehicles();
        }

        function toggleShowroomMode() {
            const nextMode = window.currentShowroomMode === 'demo' ? 'prod' : 'demo';
            setMode(nextMode);
        }

        // 고객용 공개 실차 목록 로드 및 필터 렌더링 (DIRECTIVE 064: mode 파라미터 전송)
        async function loadPublicVehicles() {
            try {
                updateModeSwitcherUi();
                const res = await fetch(`/api/chamart/vehicles?mode=${window.currentShowroomMode}`);
                if (!res.ok) throw new Error('매물 목록 조회 실패');
                publicVehicles = await res.json();

                // URL 쿼리 파라미터로부터 필터 복원
                initFiltersFromUrl();
                renderVehiclesList();
                renderMbFilterChips();
                renderMbModelChips();
                updateFilterBadge();
                updateAllFavoritesUi();
                updateCompareFloatingBar();
            } catch (err) {
                const grid = document.getElementById('vehicleGrid');
                if (grid) {
                    grid.innerHTML = `
                        <div class="col-span-full py-12 text-center text-rose-500 bg-white rounded-xl border border-rose-200">
                            <p class="font-bold text-sm">매물 데이터를 불러오는 중 오류가 발생했습니다.</p>
                            <p class="text-xs text-slate-500 mt-1">${err.message}</p>
                        </div>
                    `;
                }
            }
        }"""

# 6. renderVehiclesList 0대 빈 상태 및 데모 배지 개선
target_render_empty = """            if (filtered.length === 0) {
                grid.innerHTML = `
                    <div class="col-span-full py-16 text-center text-slate-500 bg-white rounded-xl border border-[#E5E8EC]">
                        <i data-lucide="car" class="w-10 h-10 mx-auto text-slate-300 mb-2"></i>
                        <h4 class="font-bold text-slate-700 text-sm">조건에 맞는 실차 매물이 없습니다.</h4>
                        <p class="text-xs text-slate-400 mt-1">선택하신 조건의 실차 매물이 현재 준비 중이거나 판매 완료되었습니다.</p>
                        <button onclick="resetMobileFilters()" class="mt-4 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg cursor-pointer">
                            검색 조건 초기화
                        </button>
                    </div>
                `;
                if (window.lucide) window.lucide.createIcons();
                return;
            }"""

replace_render_empty = """            if (filtered.length === 0) {
                if (window.currentShowroomMode === 'prod') {
                    // DIRECTIVE 064: 운영 실차 검증 등록 대기 정직한 Zero-Inventory 안내
                    grid.innerHTML = `
                        <div class="col-span-full py-14 px-6 text-center bg-white rounded-xl border border-[#E2E6EA] space-y-4 shadow-2xs">
                            <div class="inline-flex items-center space-x-1.5 text-xs font-bold text-slate-700 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
                                <i data-lucide="shield-check" class="w-4 h-4 text-emerald-600"></i>
                                <span>정직한 100% 실차 검증 원칙</span>
                            </div>
                            <h3 class="text-xl sm:text-2xl font-bold text-[#171B1E] tracking-tight">
                                현재 실차 검증 기준을 통과한 매물을 등록 준비 중입니다.
                            </h3>
                            <p class="text-xs sm:text-sm text-slate-600 max-w-xl mx-auto leading-relaxed">
                                차마트는 실차 현장 촬영본, 원부 대조, 성능점검 실사 기록이 100% 완료된 매물만 정직하게 등록합니다.<br class="hidden sm:inline">
                                가짜 사진이나 합성 카드를 실차로 둔갑시켜 등록하지 않습니다.
                            </p>
                            <div class="pt-2 flex flex-wrap items-center justify-center gap-3">
                                <button onclick="scrollToConsultation()" class="px-5 py-2.5 bg-[#171B1E] hover:bg-black text-white text-xs font-bold rounded-lg transition-colors cursor-pointer shadow-xs">
                                    1:1 원하는 차량 맞춤 소싱 의뢰
                                </button>
                                <button onclick="setMode('demo')" class="px-5 py-2.5 bg-[#C8FF3D] hover:bg-[#B7ED2E] text-[#171B1E] text-xs font-bold rounded-lg transition-colors cursor-pointer border border-[#AEEB20]/60 shadow-xs">
                                    UI 디자인 및 쇼핑 기능 체험하기 (데모 모드) ➔
                                </button>
                            </div>
                        </div>
                    `;
                } else {
                    grid.innerHTML = `
                        <div class="col-span-full py-16 text-center text-slate-500 bg-white rounded-xl border border-[#E5E8EC]">
                            <i data-lucide="car" class="w-10 h-10 mx-auto text-slate-300 mb-2"></i>
                            <h4 class="font-bold text-slate-700 text-sm">조건에 맞는 실차 매물이 없습니다.</h4>
                            <p class="text-xs text-slate-400 mt-1">선택하신 조건의 실차 매물이 현재 준비 중이거나 판매 완료되었습니다.</p>
                            <button onclick="resetMobileFilters()" class="mt-4 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold rounded-lg cursor-pointer">
                                검색 조건 초기화
                            </button>
                        </div>
                    `;
                }
                if (window.lucide) window.lucide.createIcons();
                return;
            }"""

# 7. 카드 상단 실차인증 vs UI 검수용 배지
target_card_badge = """                            <span class="absolute top-3 left-3 bg-[#171B1E] text-[#C8FF3D] border border-[#C8FF3D]/40 text-[11px] font-bold px-2.5 py-0.5 rounded shadow-2xs">
                                실차인증
                            </span>"""

replace_card_badge = """                            <span class="absolute top-3 left-3 bg-[#171B1E] text-[#C8FF3D] border border-[#C8FF3D]/40 text-[11px] font-bold px-2.5 py-0.5 rounded shadow-2xs">
                                ${v.is_demo_asset ? 'UI 검수용' : '실차인증'}
                            </span>"""

items = [
    (target_header_right, replace_header_right),
    (target_header_end, replace_header_end),
    (target_hero, replace_hero),
    (target_compare_scroll, replace_compare_scroll),
    (target_load_func, replace_load_func),
    (target_render_empty, replace_render_empty),
    (target_card_badge, replace_card_badge),
]

for idx, (old, new) in enumerate(items):
    if old not in code:
        print(f"FAILED on item {idx}: {old[:60]}...")
        raise ValueError(f"Target not found: item {idx}")
    code = code.replace(old, new, 1)

with open('src/chaficial/platform/ui/chamart.html', 'w', encoding='utf-8') as f:
    f.write(code)

print("Successfully applied DIRECTIVE 064 updates to chamart.html")
