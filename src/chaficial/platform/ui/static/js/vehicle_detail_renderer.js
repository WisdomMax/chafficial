/**
 * CHA-FICIAL / CHAMART 공통 프리미엄 차량 상세 렌더러 (DIRECTIVE 057 FINAL)
 * 
 * 1. 디자인 시스템: 차마트 공식 상용 웹사이트 프리미엄 디자인 시스템
 * 2. 타이포그래피: 차량명 26px(700), 가격 32px(700 차콜 #171C24), 섹션 22px(700), 본문 15~16px(400~500)
 * 3. 컬러/레이아웃: #F7F8FA 배경, #E5E8EC 보더, 절제된 radius(8~10px) 및 그림자, 평면적 화이트 패널
 * 4. 갤러리: 5:3 비율 대형 실차 사진(좌측 68%), 썸네일 스트립 및 Lightbox
 * 5. 우측 구매 영역: 32% Sticky 패널, 가격/전시장/간편예약/카카오톡 정돈된 배치
 * 6. 데이터 무결성: P0 정직한 상담 API, SVG 다이어그램 1:1 연동, 타이어 4륜 게이지, 가정한 예시 금리 시뮬레이터 100% 보존
 */

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * DIRECTIVE 064 P1: 차량 할부 금융 단일 순수 계산 함수
 * 내부 연산 단위를 원(KRW)으로 정밀 계산하여 독립 수학 결과와 100% 일치 보장
 */
function calculateVehicleLoanPure({ priceWon, downRate, annualRate, months }) {
  const pWon = Math.max(0, Number(priceWon) || 0);
  const dRate = Math.min(100, Math.max(0, Number(downRate) || 0));
  const aRate = Math.max(0, Number(annualRate) || 0);
  const nMonths = Math.max(1, parseInt(months, 10) || 36);

  const downWon = Math.round(pWon * (dRate / 100));
  const principalWon = Math.max(0, pWon - downWon);

  let monthlyWon = 0;
  let totalInterestWon = 0;

  if (pWon === 0 || principalWon === 0) {
    monthlyWon = 0;
    totalInterestWon = 0;
  } else if (aRate === 0) {
    monthlyWon = Math.round(principalWon / nMonths);
    totalInterestWon = 0;
  } else {
    const monthlyRate = (aRate / 100) / 12;
    const factor = Math.pow(1 + monthlyRate, nMonths);
    monthlyWon = Math.round((principalWon * monthlyRate * factor) / (factor - 1));
    totalInterestWon = Math.max(0, (monthlyWon * nMonths) - principalWon);
  }

  const totalRepayWon = (monthlyWon * nMonths);

  return {
    priceWon: pWon,
    downRate: dRate,
    downWon: downWon,
    downTenThousand: Math.round(downWon / 10000),
    principalWon: principalWon,
    principalTenThousand: Math.round(principalWon / 10000),
    annualRate: aRate,
    months: nMonths,
    monthlyWon: monthlyWon,
    monthlyTenThousand: Math.round(monthlyWon / 10000),
    totalInterestWon: totalInterestWon,
    totalInterestTenThousand: Math.round(totalInterestWon / 10000),
    totalRepayWon: totalRepayWon,
    totalRepayTenThousand: Math.round(totalRepayWon / 10000),
  };
}
window.calculateVehicleLoanPure = calculateVehicleLoanPure;

class VehicleDetailRenderer {
  constructor(containerId, options = {}) {
    this.container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
    this.options = {
      isAdmin: false,
      onBack: null,
      onTogglePublish: null,
      onEditMaster: null,
      onSubmitConsultation: null,
      ...options
    };
    this.data = null;
    this.photos = [];
    this.currentPhotoIdx = 0;
    this.isRealPhotoVerified = false;
    this.touchStartX = 0;
    this.touchEndX = 0;
    this.currentDiagramTab = 'all'; // 'all', 'outer', 'frame'
    this.lightboxOpen = false;
    this.isZoomed = false;
    this.lastTapTime = 0;
    this.lightboxTriggerEl = null;
    this.docTriggerEl = null;
    window.__vdrInstance = this;
  }

  render(vehicleData) {
    if (!this.container) {
      console.error('[VehicleDetailRenderer] Container not found.');
      return;
    }
    this.container.classList.add('pb-24', 'sm:pb-8', 'w-full', 'max-w-full');
    this.data = vehicleData;
    this.currentPhotoIdx = 0;

    const d = this.data;
    const isAdmin = this.options.isAdmin;

    // 1. 실차 사진 검증 및 갤러리 소스 정규화 (DIRECTIVE 056/057 P0 & DIRECTIVE 070)
    const firstPhoto = (d.photos && d.photos.length > 0) ? d.photos[0] : null;
    const hasDemoPlaceholderCaption = firstPhoto && String(firstPhoto.caption || '').includes('DEMO_PLACEHOLDER');
    const hasRealPhotos = Boolean(d.photos && d.photos.length > 0 && (d.photos[0].photo_url || d.photos[0].url));
    const isFixtureOrDemo = Boolean(d.is_demo_asset || d.gallery_status === 'STAGING_EXAMPLE' || (d.id && String(d.id).startsWith('UI-')));

    this.isRealPhotoVerified = Boolean(
      (d.photo_verification_status === 'REAL_PHOTO_VERIFIED' || isFixtureOrDemo) && !hasDemoPlaceholderCaption && hasRealPhotos
    );

    if ((this.isRealPhotoVerified || isFixtureOrDemo) && hasRealPhotos) {
      this.photos = d.photos.map(p => ({
        url: p.photo_url || p.url,
        caption: p.caption || p.display_label || `${d.model_name} 실차 사진`,
        display_label: p.display_label || p.label || '외관',
        category_code: p.category_code || (p.category ? `${p.category}_FULL` : 'EXTERIOR_FULL'),
        view_code: p.view_code || 'UNSPECIFIED',
        isVerified: Boolean(d.photo_verification_status === 'REAL_PHOTO_VERIFIED' || isFixtureOrDemo)
      }));
    } else {
      this.photos = [{
        url: '/static/img/vehicles/neutral_car_placeholder.jpg',
        caption: '차량 실차 사진 등록 전 (전시장 준비 중)',
        display_label: '준비 중',
        category_code: 'EXTERIOR_FULL',
        view_code: 'EXT_FRONT',
        isVerified: false
      }];
    }

    this.activePhotoCategory = 'ALL';

    // 2. 단일 SSOT 사고·성능 정규화 데이터 바인딩
    const acc = d.accident_summary || d.accident_history || {};
    const docStatus = acc.document_status || (acc.inspection_document_id ? 'VERIFIED' : 'UNVERIFIED');
    const hasDoc = docStatus === 'VERIFIED';
    
    const frameStatus = acc.frame_status || (acc.frame_damage_count > 0 ? 'VERIFIED_ISSUE' : (hasDoc ? 'VERIFIED_CLEAN' : 'UNKNOWN'));
    const bodyStatus = acc.body_panel_status || (acc.outer_damage_count > 0 ? 'VERIFIED_ISSUE' : (hasDoc ? 'VERIFIED_CLEAN' : 'UNKNOWN'));
    const leakStatus = acc.oil_leak_status || (hasDoc ? 'VERIFIED_CLEAN' : 'UNKNOWN');
    const floodStatus = acc.flood_history_status || (hasDoc ? 'VERIFIED_CLEAN' : 'UNKNOWN');
    const insuranceStatus = acc.insurance_history_status || (acc.total_loss_count > 0 ? 'VERIFIED_ISSUE' : (acc.insurance_checked ? 'VERIFIED_CLEAN' : 'UNKNOWN'));

    // 3. 관리자 전용 제어 툴바 (isAdmin 시에만 상단에 단정하게 배치)
    let adminToolbarHtml = '';
    if (isAdmin) {
      const pur = d.purchase_price ? `${Number(d.purchase_price).toLocaleString('ko-KR')}만원` : '미확인';
      const rec = d.recon_cost ? `${Number(d.recon_cost).toLocaleString('ko-KR')}만원` : '0만원';
      const margin = (d.target_price && d.purchase_price) 
        ? `${Number(d.target_price - d.purchase_price - (d.recon_cost || 0)).toLocaleString('ko-KR')}만원`
        : '-';

      const isPub = Boolean(d.is_public);
      const pubBtnClass = isPub 
        ? "bg-rose-600 hover:bg-rose-700 text-white" 
        : "bg-emerald-600 hover:bg-emerald-700 text-white";
      const pubBtnText = isPub ? "차마트 공개 취소" : "차마트 게시 승인";

      adminToolbarHtml = `
        <div class="bg-[#152B3C] text-white border border-slate-700 p-4 rounded-lg mb-6 shadow-xs">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
            <div class="flex flex-wrap items-center gap-3">
              <span class="inline-flex items-center px-2 py-0.5 rounded font-bold bg-[#171B1E] text-white">
                <i data-lucide="shield" class="w-3.5 h-3.5 mr-1 text-teal-400"></i>차피셜 관리자 제어판
              </span>
              <span class="text-slate-300">소유: <strong class="text-white">${escapeHtml(d.ownership_type || 'CHAMART_OWNED')}</strong></span>
              <span class="text-slate-300">거점: <strong class="text-teal-300">${escapeHtml(d.branch_location || '장한평 본사')}</strong></span>
              <span class="text-slate-300">매입원가: <strong class="text-teal-300 font-mono">${pur}</strong></span>
              <span class="text-slate-300">상품화비: <strong class="text-slate-200 font-mono">${rec}</strong></span>
              <span class="text-slate-300">추정마진: <strong class="text-amber-300 font-mono font-bold">${margin}</strong></span>
            </div>
            <div class="flex items-center space-x-2 shrink-0">
              <button id="vdrBtnTogglePublish" class="px-3 py-1.5 font-bold rounded shadow-2xs transition-colors flex items-center cursor-pointer ${pubBtnClass}">
                <i data-lucide="${isPub ? 'eye-off' : 'check'}" class="w-3.5 h-3.5 mr-1"></i>
                ${pubBtnText}
              </button>
              <button id="vdrBtnEditMaster" class="px-3 py-1.5 font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-600 rounded transition-colors flex items-center cursor-pointer">
                <i data-lucide="edit-3" class="w-3.5 h-3.5 mr-1"></i>
                제원 수정
              </button>
            </div>
          </div>
        </div>
      `;
    }

    // 4. 가격 포맷팅 및 금융 계산 전제
    const targetPriceFormatted = d.target_price ? `${Number(d.target_price).toLocaleString('ko-KR')}만원` : '가격 상담';
    const acquisitionTaxEst = d.target_price ? Math.round(d.target_price * 0.07) : 0;
    const bondAndFeeEst = d.target_price ? 15 : 0; // 공채 및 대행 부대비용 약 15만원
    const totalPurchaseCostEst = d.target_price ? (d.target_price + acquisitionTaxEst + bondAndFeeEst) : 0;

    // 딜러 정보 (DIRECTIVE 064: 임시 대표번호 전수 제거 및 제휴 전시장 정직화)
    const dealer = d.dealer_info || d.dealer || {};
    const dealerName = dealer.name || '차마트 제휴 전시장 (장한평)';
    const rawPhone = (dealer.phone || '').trim();
    const dealerPhone = (rawPhone && !rawPhone.includes('1544') && rawPhone.length >= 8) ? rawPhone : null;
    const showroomLoc = dealer.showroom_location || '서울특별시 성동구 자동차시장1길 70 (용답동) 장한평 자동차매매단지';

    // DIRECTIVE 058: 카카오 상담 채널 정직성 - 공식 채널 ID가 명시적으로 설정된 경우에만 버튼 노출
    const kakaoChannelId = d.kakao_channel_id || window.__CHAMART_KAKAO_CHANNEL_ID || '';

    // DIRECTIVE 059 P0: 차량명 및 트림 중복 렌더링 방지 정규화
    const rawModel = (d.model_name || '').trim();
    const rawTrim = (d.trim || '').trim();
    let displayTitle = rawModel;
    let displayTrim = rawTrim;
    if (rawTrim && rawModel.toLowerCase().includes(rawTrim.toLowerCase())) {
      displayTrim = '';
    } else if (rawTrim && rawTrim.toLowerCase().startsWith(rawModel.toLowerCase())) {
      displayTitle = rawModel;
      displayTrim = rawTrim.slice(rawModel.length).trim();
    }

    // 5. 차마트 직영 공식 상용 레이아웃 마운트 (White 80% / Deep Charcoal 15% / Electric Lime 5%)
    this.container.innerHTML = `
      <div class="w-full max-w-[1280px] mx-auto px-2 sm:px-4 py-3 sm:py-5 space-y-6">
        
        <!-- 상단 관리자 툴바 (isAdmin 시) -->
        ${adminToolbarHtml}

        <!-- 네비게이션 뒤로가기 & 브레드크럼 -->
        <div class="flex items-center justify-between pb-2 border-b border-[#E5E8EC]">
          <button id="vdrBtnBack" class="inline-flex items-center text-xs sm:text-sm font-semibold text-slate-600 hover:text-[#171B1E] transition-colors py-1 px-2 rounded hover:bg-slate-100 cursor-pointer">
            <i data-lucide="arrow-left" class="w-4 h-4 mr-1.5"></i>
            매물 목록으로 돌아가기
          </button>
          <div class="text-xs text-slate-400 truncate max-w-[220px] sm:max-w-none">
            차마트 &gt; <span class="text-slate-600">${escapeHtml(d.manufacturer || '국산')}</span> &gt; <strong class="text-slate-800">${escapeHtml(displayTitle)}</strong>
          </div>
        </div>

        <!-- 핵심 타이틀 헤더 (DIRECTIVE 069: 상단 중복 가격 제거, 차량명 및 핵심 제원 집중) -->
        <div class="bg-white rounded-lg border border-[#E5E8EC] p-5 sm:p-6">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="space-y-2">
              <div class="flex flex-wrap items-center gap-2">
                ${this.isRealPhotoVerified 
                  ? '<span class="px-2.5 py-0.5 rounded text-[11px] font-bold bg-[#171B1E] text-[#C8FF3D] shadow-xs">실차인증</span>' 
                  : '<span class="px-2.5 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-900 border border-amber-200">실차 준비 중 (예시 자료)</span>'}
                <span class="text-xs text-slate-500 font-medium">
                  ${escapeHtml(d.plate_number || '차량번호 미기재')} · ${d.year ? d.year + '년식' : '연식 미확인'} · ${d.mileage ? Number(d.mileage).toLocaleString('ko-KR') + 'km' : '주행거리 미확인'} · ${escapeHtml(d.fuel_type || '연료 미확인')}
                </span>
              </div>
              <h1 class="text-2xl sm:text-[26px] font-bold text-[#171B1E] tracking-tight leading-snug">
                ${escapeHtml(displayTitle)} ${displayTrim ? `<span class="text-slate-500 font-normal text-xl sm:text-2xl">${escapeHtml(displayTrim)}</span>` : ''}
              </h1>
            </div>

            <!-- 우측 보조 액션 (찜하기 및 거점 안내) -->
            <div class="flex items-center space-x-3 shrink-0 pt-2 md:pt-0">
              <span class="text-xs text-slate-500 bg-slate-50 border border-slate-200 px-3 py-1.5 rounded font-medium">
                ${escapeHtml(d.branch_location || '차마트 장한평 전시장')}
              </span>
              <button id="vdrBtnFavorite" onclick="window.__vdrInstance.toggleFavorite()" class="p-2.5 rounded-lg border border-slate-200 hover:border-slate-300 bg-white transition-all active:scale-95 cursor-pointer shadow-2xs flex items-center space-x-1.5" aria-label="관심 차량 찜하기">
                <i data-lucide="heart" id="vdrIconFavorite" class="w-4 h-4 text-slate-400"></i>
                <span class="text-xs font-semibold text-slate-700">찜</span>
              </button>
            </div>
          </div>
        </div>

        <!-- 메인 2단 본문 그리드 (DIRECTIVE 069: 좌측 유연 영역 + 우측 350px 고정 구매 패널) -->
        <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_350px] gap-6 items-start">
          
          <!-- [좌측: 5:3 대형 갤러리 + 기본제원표 + 사고진단 + 소모품 + 옵션 + 구매비용] -->
          <div class="space-y-6 w-full min-w-0">
            
            <!-- 1. 5:3 비율 대형 실차 사진 갤러리 (차마트 5:3 공식 와이드 규격 & DIRECTIVE 071 부위별 탐색) -->
            <div class="bg-white rounded-lg border border-[#E5E8EC] overflow-hidden p-4 space-y-3">
              <!-- 부위별 카테고리 탭 (DIRECTIVE 071 TASK 6) -->
              <div class="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-slate-100 text-xs font-semibold custom-scrollbar">
                <button type="button" onclick="window.__vdrInstance.filterPhotoCategory('ALL')" id="vdrTabCatALL" class="px-3 py-1.5 rounded-full transition-all bg-[#171B1E] text-white font-bold cursor-pointer shrink-0 shadow-2xs">
                  전체 (${this.photos.length})
                </button>
                <button type="button" onclick="window.__vdrInstance.filterPhotoCategory('EXTERIOR_FULL')" id="vdrTabCatEXTERIOR_FULL" class="px-3 py-1.5 rounded-full transition-all bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer shrink-0">
                  외관 전체
                </button>
                <button type="button" onclick="window.__vdrInstance.filterPhotoCategory('EXTERIOR_PANEL')" id="vdrTabCatEXTERIOR_PANEL" class="px-3 py-1.5 rounded-full transition-all bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer shrink-0">
                  외판 상세
                </button>
                <button type="button" onclick="window.__vdrInstance.filterPhotoCategory('INTERIOR')" id="vdrTabCatINTERIOR" class="px-3 py-1.5 rounded-full transition-all bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer shrink-0">
                  실내
                </button>
                <button type="button" onclick="window.__vdrInstance.filterPhotoCategory('ENGINE_MECHANICAL')" id="vdrTabCatENGINE_MECHANICAL" class="px-3 py-1.5 rounded-full transition-all bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer shrink-0">
                  엔진·하부
                </button>
                <button type="button" onclick="window.__vdrInstance.filterPhotoCategory('OPTION_FEATURE')" id="vdrTabCatOPTION_FEATURE" class="px-3 py-1.5 rounded-full transition-all bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer shrink-0">
                  옵션·특이사항
                </button>
                <button type="button" onclick="window.__vdrInstance.filterPhotoCategory('DOCUMENT')" id="vdrTabCatDOCUMENT" class="px-3 py-1.5 rounded-full transition-all bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer shrink-0">
                  성능점검 서류
                </button>
              </div>

              <div id="vdrGalleryViewport" class="relative aspect-[5/3] bg-slate-900 rounded overflow-hidden flex items-center justify-center select-none touch-pan-y cursor-zoom-in">
                <img id="vdrMainImage" src="${escapeHtml(this.photos[0].url)}" alt="차량 사진" class="w-full h-full object-contain transition-all duration-200" onclick="window.__vdrInstance.openLightbox()" />
                
                ${this.photos.length > 1 ? `
                  <button id="vdrBtnPrevPhoto" class="absolute left-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-black/40 hover:bg-black/70 text-white flex items-center justify-center transition-opacity cursor-pointer">
                    <i data-lucide="chevron-left" class="w-5 h-5"></i>
                  </button>
                  <button id="vdrBtnNextPhoto" class="absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-black/40 hover:bg-black/70 text-white flex items-center justify-center transition-opacity cursor-pointer">
                    <i data-lucide="chevron-right" class="w-5 h-5"></i>
                  </button>
                ` : ''}

                <!-- 한글 부위명 라벨 뱃지 (DIRECTIVE 071 TASK 6) -->
                <div class="absolute top-3 right-3 bg-black/75 backdrop-blur-xs text-[#C8FF3D] border border-[#C8FF3D]/40 text-xs font-bold px-3 py-1 rounded-full shadow-sm flex items-center gap-1.5">
                  <span class="w-1.5 h-1.5 rounded-full bg-[#C8FF3D]"></span>
                  <span id="vdrPhotoPartLabel">${escapeHtml(this.photos[0].display_label || '외관')}</span>
                </div>

                <!-- 사진 카운터 & 상태 배지 -->
                <div class="absolute bottom-3 left-3 right-3 flex items-center justify-between text-xs text-white/90 bg-black/60 px-3 py-1.5 rounded">
                  <span id="vdrPhotoCaption" class="truncate font-medium">${escapeHtml(this.photos[0].caption)}</span>
                  <div class="flex items-center space-x-2 shrink-0 ml-2">
                    <button onclick="window.__vdrInstance.openLightbox()" class="text-[11px] bg-white/20 hover:bg-white/30 px-2 py-0.5 rounded cursor-pointer flex items-center">
                      <i data-lucide="maximize-2" class="w-3 h-3 mr-1"></i>확대
                    </button>
                    <span id="vdrPhotoCounter" class="font-bold">1 / ${this.photos.length}</span>
                  </div>
                </div>

                ${!this.isRealPhotoVerified ? `
                  <div class="absolute top-3 left-3 bg-amber-600/90 text-white text-[11px] font-semibold px-2.5 py-1 rounded shadow-sm">
                    실차 사진 준비 중
                  </div>
                ` : ''}
              </div>

              <!-- 하단 썸네일 스트립 (5:3 비율) -->
              ${this.photos.length > 1 ? `
                <div id="vdrThumbnailsContainer" class="flex gap-2 overflow-x-auto py-1 custom-scrollbar">
                  ${this.photos.map((p, idx) => `
                    <button onclick="window.__vdrInstance.selectPhoto(${idx})" data-cat="${escapeHtml(p.category_code)}" class="vdr-thumb-btn w-20 aspect-[5/3] rounded overflow-hidden shrink-0 border-2 transition-all cursor-pointer ${idx === 0 ? 'border-[#171B1E] ring-1 ring-[#171B1E]' : 'border-[#E5E8EC] opacity-70 hover:opacity-100'}">
                      <img src="${escapeHtml(p.url)}" alt="썸네일 ${idx+1}" class="w-full h-full object-cover" />
                    </button>
                  `).join('')}
                </div>
              ` : `
                <div class="text-xs text-slate-400 text-center py-2 bg-slate-50 rounded">
                  ※ 전시장 직접 검증 후 고해상도 실차 사진이 등록될 예정입니다.
                </div>
              `}
            </div>

            <!-- 2. 핵심 기본 제원표 (K Car 스타일 정밀 표 규격) -->
            <div class="bg-white rounded-lg border border-[#E7E9E5] p-5 space-y-4">
              <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 class="text-lg font-bold text-[#171B1E]">차량 기본 제원 상세</h3>
                <span class="text-xs text-[#646B6B]">자동차등록원부 및 성능점검부 기준 공시</span>
              </div>
              
              <!-- K Car 정밀 표 구조 (단일 표준 반응형 4열 테이블) -->
              <div class="border border-[#E7E9E5] rounded-lg overflow-hidden">
                <table id="vdrSpecTable" class="w-full text-xs sm:text-sm border-collapse">
                  <tbody>
                    <tr class="border-b border-[#E7E9E5]">
                      <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">차량번호</th>
                      <td class="bg-white text-[#171B1E] font-semibold px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">${escapeHtml(d.plate_number || '미기재')}</td>
                      <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">차대번호 (VIN)</th>
                      <td class="bg-white text-[#171B1E] font-mono text-xs px-3.5 py-2.5 w-1/4">
                        <div class="flex items-center justify-between gap-1">
                          <span class="truncate" title="${escapeHtml(d.vin || '미확인')}">${escapeHtml(d.vin || '미확인')}</span>
                          ${d.vin ? `
                            <button onclick="navigator.clipboard.writeText('${escapeHtml(d.vin)}'); alert('차대번호가 복사되었습니다: ' + '${escapeHtml(d.vin)}');" class="text-slate-400 hover:text-slate-700 px-1 py-0.5 rounded text-[10px] bg-slate-100 hover:bg-slate-200 shrink-0 cursor-pointer" title="차대번호 복사">
                              복사
                            </button>
                          ` : ''}
                        </div>
                      </td>
                    </tr>
                    <tr class="border-b border-[#E7E9E5]">
                      <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">연식 / 최초등록</th>
                      <td class="bg-white text-[#171B1E] font-semibold px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">${d.year ? d.year + '년식' : '미확인'} / ${escapeHtml(d.first_registration_date || '미확인')}</td>
                      <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">주행거리</th>
                      <td class="bg-white text-[#171B1E] font-semibold px-3.5 py-2.5 w-1/4">${d.mileage ? Number(d.mileage).toLocaleString('ko-KR') + ' km' : '미확인'}</td>
                    </tr>
                    <tr class="border-b border-[#E7E9E5]">
                      <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">배기량</th>
                      <td class="bg-white text-[#171B1E] font-semibold px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">${d.displacement_cc ? Number(d.displacement_cc).toLocaleString('ko-KR') + ' cc' : '미확인'}</td>
                      <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">변속기 / 구동방식</th>
                      <td class="bg-white text-[#171B1E] font-semibold px-3.5 py-2.5 w-1/4">${escapeHtml(d.transmission || '미확인')} / ${escapeHtml(d.drive_type || '미확인')}</td>
                    </tr>
                    <tr>
                      <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">사용연료 / 색상</th>
                      <td class="bg-white text-[#171B1E] font-semibold px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">${escapeHtml(d.fuel_type || '미확인')} / ${escapeHtml(d.color || '미확인')}</td>
                      <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left px-3.5 py-2.5 w-1/4 border-r border-[#E7E9E5]">차체형태 / 인승</th>
                      <td class="bg-white text-[#171B1E] font-semibold px-3.5 py-2.5 w-1/4">${escapeHtml(d.body_type || '미확인')} ${d.seating_capacity ? `(${d.seating_capacity}인승)` : ''}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- 3. 사고 및 성능점검 공식 진단표 & 2D SVG 다이어그램 (DIRECTIVE 062 P0: 허위 증빙 완전 제거) -->
            <div class="bg-white rounded-lg border border-[#E5E8EC] p-5 space-y-5">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
                <div>
                  <h3 class="text-lg font-bold text-[#171C24]">사고 및 성능점검 공식 진단</h3>
                  <p class="text-xs text-slate-500 mt-0.5">자동차관리법 제58조 제1항에 따른 성능·상태점검 전산 기준</p>
                </div>
                <div class="flex items-center space-x-2 text-xs">
                  ${(acc.inspection_document_id && acc.inspection_document_url) 
                    ? `
                      <span class="text-slate-600 hidden sm:inline">문서번호: <strong class="font-mono text-slate-800">${escapeHtml(acc.inspection_document_id)}</strong></span>
                      <a href="${escapeHtml(acc.inspection_document_url)}" target="_blank" rel="noopener noreferrer" class="px-3 py-1.5 rounded bg-slate-900 hover:bg-black text-white font-bold text-xs flex items-center cursor-pointer transition-colors shadow-2xs">
                        <i data-lucide="file-text" class="w-3.5 h-3.5 mr-1 text-teal-400"></i>
                        검증된 성능기록부 원본
                      </a>
                    ` 
                    : '<span id="vdrInspectionPendingBadge" class="text-slate-600 font-medium bg-slate-100 px-2.5 py-1 rounded border border-slate-200">성능·상태점검기록부 확인 중</span>'}
                </div>
              </div>

              <!-- 상단 6대 신뢰 요약 (단정한 사각형 박스) -->
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
                ${this.renderDiagnosticCard('주요 골격(프레임) 손상', frameStatus, 'shield')}
                ${this.renderDiagnosticCard('외판 부위 교환/판금', bodyStatus, 'wrench')}
                ${this.renderDiagnosticCard('엔진/변속기 미세누유', leakStatus, 'droplet')}
                ${this.renderDiagnosticCard('침수 및 화재 이력', floodStatus, 'waves')}
                ${this.renderDiagnosticCard('보험사고 이력', insuranceStatus, 'file-text')}
                ${this.renderDiagnosticCard('성능점검 기록부', docStatus, 'check-circle')}
              </div>

              <!-- 차량 부위별 독자 2D 다이어그램 (외판 vs 주요 골격, diagram_parts 바인딩) -->
              <div class="bg-slate-50 p-4 rounded-lg border border-[#E5E8EC] space-y-4">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <span class="text-xs font-bold text-slate-800">차량 부위별 정밀 진단 평면도 (클릭 시 세부 판정 확인)</span>
                  <div class="inline-flex rounded bg-slate-200 p-0.5 text-xs font-medium">
                    <button onclick="window.__vdrInstance.switchDiagramTab('all')" id="vdrDiagTabAll" class="px-2.5 py-1 rounded bg-white text-slate-900 shadow-2xs cursor-pointer">전체</button>
                    <button onclick="window.__vdrInstance.switchDiagramTab('outer')" id="vdrDiagTabOuter" class="px-2.5 py-1 rounded text-slate-600 hover:text-slate-900 cursor-pointer">외판 부위</button>
                    <button onclick="window.__vdrInstance.switchDiagramTab('frame')" id="vdrDiagTabFrame" class="px-2.5 py-1 rounded text-slate-600 hover:text-slate-900 cursor-pointer">주요 골격</button>
                  </div>
                </div>

                <!-- 범례 -->
                <div class="flex flex-wrap items-center gap-4 text-xs text-slate-500 py-1 border-t border-b border-slate-200/70">
                  <span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full bg-emerald-500 mr-1.5"></span>무사고·정상</span>
                  <span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full bg-amber-500 mr-1.5"></span>단순교환/수리</span>
                  <span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full bg-rose-500 mr-1.5"></span>주요 골격손상</span>
                  <span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full bg-slate-300 mr-1.5"></span>미확인</span>
                </div>

                <!-- SVG 및 우측 상세 패널 -->
                <div class="flex flex-col md:flex-row items-center justify-center gap-6 py-2">
                  <div class="relative w-full max-w-[300px] aspect-[3/5] flex items-center justify-center">
                    ${this.renderCarDiagramSvg(acc)}
                  </div>

                  <div id="vdrPartDetailPanel" class="w-full md:w-64 bg-white p-4 rounded-lg border border-[#E5E8EC] space-y-2 text-xs">
                    <div class="font-bold text-slate-800 text-sm flex items-center justify-between border-b border-slate-100 pb-2">
                      <span id="vdrSelectedPartName">부위를 선택하세요</span>
                      <span id="vdrSelectedPartBadge" class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">선택 대기</span>
                    </div>
                    <div class="space-y-1.5 text-slate-600 pt-1">
                      <div>구분: <span id="vdrSelectedPartCategory" class="font-medium text-slate-800">-</span></div>
                      <div>판정: <span id="vdrSelectedPartState" class="font-medium text-slate-700">-</span></div>
                      <div>근거: <span id="vdrSelectedPartEvidence" class="font-mono text-slate-500 text-[11px]">-</span></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 4. 타이어 트레드 깊이 및 소모품 점검 카드 (DIRECTIVE 056 보존) -->
            <div class="bg-white rounded-lg border border-[#E5E8EC] p-5 space-y-4">
              <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 class="text-lg font-bold text-[#171C24]">타이어 및 주요 소모품 상태</h3>
                <span class="text-xs text-slate-400">정밀 디지털 게이지 측정치</span>
              </div>

              <!-- 4륜 타이어 트레드 -->
              <div class="space-y-2">
                <span class="text-xs font-semibold text-slate-700">타이어 잔여 트레드 깊이 (신품 기준 8.0mm)</span>
                ${this.renderTireGauges(d)}
              </div>

              <!-- 소모품 상태 -->
              <div class="pt-3 border-t border-slate-100 space-y-2">
                <span class="text-xs font-semibold text-slate-700">주요 소모품 점검</span>
                ${this.renderConsumablesGrid(d)}
              </div>
            </div>

            <!-- 5. 장착 주요 옵션 체크리스트 -->
            <div class="bg-white rounded-lg border border-[#E5E8EC] p-5 space-y-4">
              <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 class="text-lg font-bold text-[#171C24]">장착 주요 옵션 체크리스트</h3>
                <span class="text-xs text-slate-400">실차 확인 사양</span>
              </div>
              <div id="vdrOptionsContainer">
                ${this.renderOptionsGrid(d)}
              </div>
            </div>

            <!-- 6. K Car 스타일 투명 총 구매비용 및 가정한 예시 금리 금융 계산기 -->
            <div class="bg-white rounded-lg border border-[#E5E8EC] p-5 space-y-4">
              <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                <h3 class="text-lg font-bold text-[#171C24]">투명 총 구매비용 및 금융 시뮬레이터</h3>
                <span class="text-xs text-slate-400">사전 안내용 투명 견적</span>
              </div>
              
              <div class="space-y-2 text-xs sm:text-sm">
                <div class="flex justify-between py-1.5 border-b border-slate-100 text-slate-600">
                  <span>차량 정찰 판매가</span>
                  <span class="font-bold text-slate-900">${targetPriceFormatted}</span>
                </div>
                <div class="flex justify-between py-1.5 border-b border-slate-100 text-slate-600">
                  <span>예상 이전등록세 (취득세 7% 기준 예시)</span>
                  <span class="font-bold text-slate-900">${acquisitionTaxEst.toLocaleString('ko-KR')}만원</span>
                </div>
                <div class="flex justify-between py-1.5 border-b border-slate-100 text-slate-600">
                  <span>공채 및 이전대행 부대비용 (미확정 예상 안내)</span>
                  <span class="font-bold text-slate-900">약 ${bondAndFeeEst}만원</span>
                </div>
                <div class="flex justify-between py-2.5 bg-slate-50 px-3 rounded text-slate-900 font-bold text-sm sm:text-base border border-slate-200">
                  <span>총 예상 구매비용</span>
                  <span class="text-[#171B1E] text-base sm:text-lg font-bold">${totalPurchaseCostEst.toLocaleString('ko-KR')}만원</span>
                </div>
                <p class="text-[11px] text-slate-400">
                  ※ 취득세 감면 대상 및 지역별 공채 할인율에 따라 실제 이전비용은 차이가 발생할 수 있는 미확정 비용입니다.
                </p>
              </div>

              <!-- 스마트 금융 할부 시뮬레이터 -->
              <div class="mt-4 pt-4 border-t border-slate-100 space-y-3">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
                  <span class="font-bold text-slate-800">스마트 할부 계산기</span>
                  <span class="text-amber-700 font-medium">※ 가정한 예시 금리 기준 시뮬레이션</span>
                </div>
                
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div>
                    <label class="block text-slate-500 mb-1">선수금 비율</label>
                    <select id="vdrCalcDownPayment" onchange="window.__vdrInstance.updateLoanCalc()" class="w-full p-2 border border-[#E5E8EC] rounded bg-slate-50 text-slate-800 focus:outline-none focus:border-[#171B1E]">
                      <option value="0">0% (무보증 전액할부)</option>
                      <option value="10" selected>10% (${Math.round((d.target_price || 0) * 0.1).toLocaleString('ko-KR')}만원)</option>
                      <option value="20">20% (${Math.round((d.target_price || 0) * 0.2).toLocaleString('ko-KR')}만원)</option>
                      <option value="30">30% (${Math.round((d.target_price || 0) * 0.3).toLocaleString('ko-KR')}만원)</option>
                      <option value="50">50% (${Math.round((d.target_price || 0) * 0.5).toLocaleString('ko-KR')}만원)</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-slate-500 mb-1">할부 기간</label>
                    <select id="vdrCalcMonths" onchange="window.__vdrInstance.updateLoanCalc()" class="w-full p-2 border border-[#E5E8EC] rounded bg-slate-50 text-slate-800 focus:outline-none focus:border-[#171B1E]">
                      <option value="24">24개월</option>
                      <option value="36">36개월</option>
                      <option value="48">48개월</option>
                      <option value="60" selected>60개월</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-slate-500 mb-1">가정한 예시 금리</label>
                    <select id="vdrCalcRate" onchange="window.__vdrInstance.updateLoanCalc()" class="w-full p-2 border border-[#E5E8EC] rounded bg-slate-50 text-slate-800 focus:outline-none focus:border-[#171B1E]">
                      <option value="0.045">연 4.5% (최저 우대금리 가정)</option>
                      <option value="0.055">연 5.5% (우대금리 가정)</option>
                      <option value="0.059" selected>연 5.9% (표준 예시금리)</option>
                      <option value="0.069">연 6.9% (일반 예시금리)</option>
                      <option value="0.079">연 7.9% (예시금리)</option>
                      <option value="0.099">연 9.9% (예시금리)</option>
                    </select>
                  </div>
                </div>

                <div class="bg-slate-900 text-white p-4 rounded space-y-2">
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-slate-300">월 예상 납입금 (원리금 균등)</span>
                    <span id="vdrCalcMonthlyResult" class="text-base sm:text-lg font-bold text-teal-300 font-mono">
                      계산 중...
                    </span>
                  </div>
                  <div class="flex items-center justify-between pt-2 border-t border-slate-800 text-xs">
                    <span class="text-slate-400">총 납부 이자 / 총 상환액</span>
                    <span id="vdrCalcTotalInterestResult" class="text-slate-300 font-mono">
                      이자: - / 총액: -
                    </span>
                  </div>
                </div>

                <!-- 예상 구매비용 안내서 인쇄·저장 버튼 (DIRECTIVE 062 P2) -->
                <div class="pt-2 flex justify-end">
                  <button id="vdrBtnOpenEstimate" onclick="window.__vdrInstance.openEstimateModal()" class="px-3.5 py-2 rounded-lg bg-white hover:bg-slate-50 text-[#171B1E] border border-[#CBD5E1] text-xs font-bold inline-flex items-center cursor-pointer transition-colors shadow-2xs">
                    <i data-lucide="file-spreadsheet" class="w-4 h-4 mr-1.5 text-slate-700"></i>
                    예상 구매비용 안내서 저장·인쇄
                  </button>
                </div>
              </div>
            </div>

          </div>

          <!-- [우측: Sticky 가격 및 구매 상담 패널] (DIRECTIVE 069: 폭 350px 지정) -->
          <div class="w-full lg:w-[350px] lg:sticky lg:top-20 space-y-5 shrink-0">
            
            <div class="bg-white rounded-lg border border-[#E5E8EC] p-5 space-y-5">
              <div>
                <span class="text-xs text-slate-400 block mb-0.5">차마트 정찰 판매가</span>
                <div class="text-3xl font-bold text-[#171C24] tracking-tight">
                  ${targetPriceFormatted}
                </div>
                <div class="text-xs text-slate-500 mt-1">
                  현금 / 카드 / 1금융 저금리 할부 심사 가능
                </div>
              </div>

              <!-- 신뢰 보증 안내 목록 (정직한 서비스 고지) -->
              <div class="space-y-2 py-3 border-y border-slate-100 text-xs text-slate-600">
                <div class="flex items-center space-x-2">
                  <i data-lucide="check" class="w-4 h-4 text-[#171B1E]"></i>
                  <span>장한평 실차 전시장 입고 및 실매물 확인</span>
                </div>
                <div class="flex items-center space-x-2">
                  <i data-lucide="check" class="w-4 h-4 text-[#171B1E]"></i>
                  <span>성능·상태점검기록부 실물 1:1 대조 확인</span>
                </div>
                <div class="flex items-center space-x-2">
                  <i data-lucide="check" class="w-4 h-4 text-[#171B1E]"></i>
                  <span>세금계산서·현금영수증 의무 발행 (추가 수수료 없음)</span>
                </div>
              </div>

              <!-- 전시장 및 담당 매니저 -->
              <div class="bg-slate-50 rounded p-3.5 border border-[#E5E8EC] space-y-2 text-xs">
                <div class="font-bold text-slate-800 flex items-center justify-between">
                  <span>전시장 위치</span>
                  <span class="text-[#171B1E] font-bold">${escapeHtml(dealerName)}</span>
                </div>
                <div class="text-slate-600 flex items-start space-x-1.5">
                  <i data-lucide="map-pin" class="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5"></i>
                  <span id="vdrShowroomAddress">${escapeHtml(showroomLoc)}</span>
                </div>
                <div class="flex items-center space-x-1.5 pt-0.5">
                  <i data-lucide="phone" class="w-3.5 h-3.5 text-slate-400 shrink-0"></i>
                  ${dealerPhone ? `
                    <a href="tel:${escapeHtml(dealerPhone)}" class="text-[#171B1E] font-bold hover:underline">${escapeHtml(dealerPhone)}</a>
                  ` : `
                    <span class="text-slate-500 font-medium">1:1 온라인 방문 예약 접수 후 안내</span>
                  `}
                </div>
                <!-- 주소 복사 & 공식 지도 길찾기 버튼 (DIRECTIVE 062 P3) -->
                <div class="pt-2 border-t border-slate-200/70 flex items-center justify-between">
                  <button type="button" onclick="window.__vdrInstance.copyShowroomAddress()" class="text-[11px] text-slate-500 hover:text-slate-800 flex items-center cursor-pointer transition-colors">
                    <i data-lucide="copy" class="w-3 h-3 mr-1"></i><span id="vdrBtnCopyAddrText">주소 복사</span>
                  </button>
                  <button type="button" id="vdrBtnOpenWayfinding" onclick="window.__vdrInstance.openWayfindingModal()" class="px-2.5 py-1 rounded bg-[#101A2A] hover:bg-black text-white font-bold text-xs flex items-center cursor-pointer transition-colors shadow-2xs">
                    <i data-lucide="navigation" class="w-3.5 h-3.5 mr-1 text-teal-400"></i>
                    길찾기
                  </button>
                </div>
              </div>

              <!-- 카카오톡 1:1 빠른 상담 (DIRECTIVE 058: 공식 채널 ID 설정 시에만 정직하게 노출, 미설정 시 완전 숨김) -->
              ${kakaoChannelId ? `
              <button onclick="window.__vdrInstance.handleKakaoConsult('${escapeHtml(kakaoChannelId)}')" class="w-full py-2.5 bg-[#FEE500] hover:bg-[#FADA0A] text-[#191919] font-bold text-xs rounded transition-colors flex items-center justify-center cursor-pointer shadow-2xs">
                <i data-lucide="message-circle" class="w-4 h-4 mr-1.5 text-[#191919]"></i>
                카카오톡 1:1 빠른 상담
              </button>
              ` : ''}

              <!-- 데스크톱 방문 예약 간편 폼 (차마트 공식 딥 차콜 CTA) -->
              <form id="vdrConsultForm" onsubmit="window.__vdrInstance.handleSubmitConsult(event, false)" class="space-y-3 pt-1">
                <div class="text-xs font-bold text-slate-800">방문 시승 및 실차 확인 신청</div>
                <div>
                  <input type="text" id="vdrCustName" placeholder="고객 성함 *" required class="w-full px-3 py-2 text-xs border border-[#E5E8EC] rounded focus:outline-none focus:border-[#171B1E]" />
                </div>
                <div>
                  <input type="tel" id="vdrCustPhone" placeholder="연락처 * (010-0000-0000)" required class="w-full px-3 py-2 text-xs border border-[#E5E8EC] rounded focus:outline-none focus:border-[#171B1E]" />
                </div>
                <div>
                  <input type="date" id="vdrCustDate" class="w-full px-3 py-2 text-xs border border-[#E5E8EC] rounded text-slate-600 focus:outline-none focus:border-[#171B1E]" />
                </div>
                <div>
                  <textarea id="vdrCustMemo" rows="2" placeholder="문의 사항 (예: 시승 예약, 대차 상담 등)" class="w-full px-3 py-2 text-xs border border-[#E5E8EC] rounded focus:outline-none focus:border-[#171B1E]"></textarea>
                </div>
                <div class="flex items-start space-x-2 text-[11px] text-slate-500">
                  <input type="checkbox" id="vdrPrivacyAgree" required class="mt-0.5 rounded text-[#171B1E] focus:ring-0 cursor-pointer" />
                  <label for="vdrPrivacyAgree" class="cursor-pointer">
                    [필수] 방문 상담 예약을 위한 개인정보 수집·이용에 동의합니다.
                  </label>
                </div>
                <button type="submit" id="vdrBtnSubmitConsult" class="w-full py-2.5 bg-[#171B1E] hover:bg-[#000000] text-white font-bold text-xs rounded transition-colors flex items-center justify-center cursor-pointer shadow-xs">
                  <i data-lucide="calendar" class="w-3.5 h-3.5 mr-1.5 text-white"></i>
                  방문 예약 신청하기
                </button>
              </form>
            </div>

          </div>
        </div>

      </div>

      <!-- 모바일 하단 고정 CTA 바 (전화상담 + 방문예약, 390x844 / 375x812 최적화) -->
      <div class="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-[#E5E8EC] p-2 sm:hidden shadow-md">
        <div class="flex items-center space-x-2 max-w-md mx-auto">
          <a href="tel:${escapeHtml(dealerPhone)}" class="flex-1 py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded flex items-center justify-center border border-slate-200">
            <i data-lucide="phone" class="w-3.5 h-3.5 mr-1 text-[#171B1E]"></i>
            전화 상담
          </a>
          <button onclick="window.__vdrInstance.openBottomSheet()" class="flex-1 py-2.5 px-3 bg-[#171B1E] hover:bg-[#000000] text-white font-bold text-xs rounded flex items-center justify-center shadow-xs cursor-pointer">
            <i data-lucide="calendar" class="w-3.5 h-3.5 mr-1 text-white"></i>
            방문 예약
          </button>
        </div>
      </div>

      <!-- 모바일 방문예약 Bottom Sheet 모달 -->
      <div id="vdrBottomSheetModal" class="fixed inset-0 bg-black/60 z-50 hidden flex items-end justify-center sm:hidden animate-in fade-in duration-150">
        <div class="bg-white w-full max-h-[85vh] rounded-t-xl p-5 shadow-2xl overflow-y-auto space-y-4 animate-in slide-in-from-bottom duration-200">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 class="text-base font-bold text-slate-800">방문 시승 및 실차 확인 예약</h3>
              <p class="text-xs text-slate-500 mt-0.5">${escapeHtml(displayTitle)}</p>
            </div>
            <button onclick="window.__vdrInstance.closeBottomSheet()" class="text-slate-400 hover:text-slate-600 p-1 cursor-pointer">
              <i data-lucide="x" class="w-5 h-5"></i>
            </button>
          </div>

          <form id="vdrBsConsultForm" onsubmit="window.__vdrInstance.handleSubmitConsult(event, true)" class="space-y-3">
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">고객 성함 *</label>
              <input type="text" id="vdrBsCustName" placeholder="예: 김철수" required class="w-full px-3 py-2 text-xs border border-[#E5E8EC] rounded focus:outline-none focus:border-[#171B1E]" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">연락처 *</label>
              <input type="tel" id="vdrBsCustPhone" placeholder="010-0000-0000" required class="w-full px-3 py-2 text-xs border border-[#E5E8EC] rounded focus:outline-none focus:border-[#171B1E]" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">방문 희망일자</label>
              <input type="date" id="vdrBsCustDate" class="w-full px-3 py-2 text-xs border border-[#E5E8EC] rounded text-slate-600 focus:outline-none focus:border-[#171B1E]" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">문의 메모 (선택)</label>
              <textarea id="vdrBsCustMemo" rows="2" placeholder="시승 희망 여부, 보유차량 대차 견적 문의 등" class="w-full px-3 py-2 text-xs border border-[#E5E8EC] rounded focus:outline-none focus:border-[#171B1E]"></textarea>
            </div>
            <div class="flex items-start space-x-2 text-[11px] text-slate-500 pt-1">
              <input type="checkbox" id="vdrBsPrivacyAgree" required class="mt-0.5 rounded text-[#171B1E] focus:ring-0 cursor-pointer" />
              <label for="vdrBsPrivacyAgree" class="cursor-pointer">
                [필수] 방문 상담 예약을 위한 개인정보 수집·이용에 동의합니다.
              </label>
            </div>
            <button type="submit" id="vdrBsBtnSubmit" class="w-full py-2.5 bg-[#171B1E] hover:bg-[#000000] text-white font-bold text-xs rounded shadow-xs transition-colors flex items-center justify-center cursor-pointer mt-2">
              <i data-lucide="check" class="w-4 h-4 mr-1 text-white"></i>
              간편 예약 신청 완료
            </button>
          </form>
        </div>
      </div>

      <!-- 전체화면 Lightbox 모달 -->
      <div id="vdrLightboxModal" class="fixed inset-0 bg-black/95 z-50 hidden flex flex-col items-center justify-between p-4 select-none">
        <div class="w-full flex items-center justify-between text-white py-2 px-4 max-w-5xl">
          <span id="vdrLightboxCaption" class="text-sm font-semibold truncate"></span>
          <div class="flex items-center space-x-4">
            <span id="vdrLightboxCounter" class="text-xs text-slate-400 font-mono"></span>
            <button onclick="window.__vdrInstance.closeLightbox()" class="text-white hover:text-slate-300 p-1 cursor-pointer">
              <i data-lucide="x" class="w-6 h-6"></i>
            </button>
          </div>
        </div>
        <div class="relative flex-1 w-full flex items-center justify-center max-w-5xl overflow-hidden">
          <img id="vdrLightboxImage" src="" alt="확대 사진" class="max-w-full max-h-[80vh] object-contain" />
          <button onclick="window.__vdrInstance.prevPhoto()" class="absolute left-2 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center cursor-pointer">
            <i data-lucide="chevron-left" class="w-6 h-6"></i>
          </button>
          <button onclick="window.__vdrInstance.nextPhoto()" class="absolute right-2 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-black/60 hover:bg-black/90 text-white flex items-center justify-center cursor-pointer">
            <i data-lucide="chevron-right" class="w-6 h-6"></i>
          </button>
        </div>
        <div class="text-slate-400 text-xs py-2">
          키보드 좌우 화살표(← / →)로 이동 가능하며 ESC를 누르면 닫힙니다.
        </div>
      </div>

      <!-- 예상 구매비용 안내서 (견적서) 인쇄/저장 모달 (DIRECTIVE 062) -->
      <div id="vdrEstimatePrintModal" class="fixed inset-0 bg-black/75 z-50 hidden flex items-center justify-center p-3 sm:p-6 animate-in fade-in duration-150">
        <div class="bg-white rounded-xl max-w-2xl w-full max-h-[92vh] flex flex-col p-6 shadow-2xl space-y-4 overflow-hidden border border-[#E7E9E5]">
          <!-- 모달 상단 헤더 (화면용 / 인쇄 시 숨김) -->
          <div class="flex items-center justify-between border-b border-slate-200 pb-3 no-print">
            <div class="flex items-center space-x-2">
              <i data-lucide="calculator" class="w-5 h-5 text-[#171B1E]"></i>
              <div>
                <h3 class="text-base sm:text-lg font-bold text-[#171B1E]">실차 예상 구매비용 안내서</h3>
                <p class="text-xs text-slate-500">투명 정찰가 기준 예산 산출 안내서 (사전 안내용)</p>
              </div>
            </div>
            <button onclick="window.__vdrInstance.closeEstimateModal()" class="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 cursor-pointer">
              <i data-lucide="x" class="w-5 h-5"></i>
            </button>
          </div>

          <!-- A4 인쇄 대상 본문 영역 -->
          <div id="vdrPrintableEstimateSheet" class="flex-1 overflow-y-auto custom-scrollbar space-y-3.5 text-xs text-slate-700 pr-1 p-2 bg-white">
            <div class="border-b-2 border-[#171B1E] pb-3 flex justify-between items-end">
              <div>
                <div class="flex items-center space-x-2 mb-1">
                  <span class="text-xs font-bold text-slate-500">차마트</span>
                  <span class="inline-block bg-[#101A2A] text-white font-mono text-[10px] font-bold px-2 py-0.5 rounded border border-slate-700">[시연용 견적서]</span>
                </div>
                <h2 class="text-xl font-bold text-[#171B1E] mt-0.5 leading-snug">${escapeHtml(displayTitle)} ${displayTrim ? escapeHtml(displayTrim) : ''}</h2>
                <span class="text-xs text-slate-500">${escapeHtml(d.plate_number || '차량번호 미기재')} · ${d.year ? d.year + '년식' : '연식미확인'} · ${d.mileage ? Number(d.mileage).toLocaleString('ko-KR') + 'km' : '주행거리 미확인'}</span>
              </div>
              <div class="text-right">
                <span class="text-[11px] text-slate-400 block">발급일자</span>
                <span class="font-mono text-xs font-semibold text-slate-700">${new Date().toISOString().slice(0, 10)}</span>
              </div>
            </div>

            <!-- 비용 세부 산출 내역표 -->
            <div class="border border-[#E7E9E5] rounded-lg overflow-hidden">
              <table class="w-full text-xs border-collapse">
                <tbody>
                  <tr class="border-b border-[#E7E9E5]">
                    <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left p-3 w-1/2">1. 차량 정찰 판매가 (차량 대금)</th>
                    <td class="p-3 text-right font-bold text-[#171B1E] text-sm w-1/2">${targetPriceFormatted}</td>
                  </tr>
                  <tr class="border-b border-[#E7E9E5]">
                    <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left p-3 w-1/2">2. 예상 취득세 (7% 기준 추정치)</th>
                    <td class="p-3 text-right font-semibold text-slate-800 w-1/2">${acquisitionTaxEst.toLocaleString('ko-KR')}만원</td>
                  </tr>
                  <tr class="border-b border-[#E7E9E5]">
                    <th class="bg-[#F5F6F4] text-[#646B6B] font-medium text-left p-3 w-1/2">3. 공채 및 이전대행 부대비용 (예상 안내)</th>
                    <td class="p-3 text-right font-semibold text-slate-800 w-1/2">약 ${bondAndFeeEst}만원</td>
                  </tr>
                  <tr class="bg-[#F5F6F4] font-bold text-slate-900 border-t border-[#171B1E]">
                    <th class="p-3.5 text-left text-sm text-[#171B1E]">총 예상 구매비용 합계</th>
                    <td class="p-3.5 text-right text-base sm:text-lg text-[#171B1E]">${totalPurchaseCostEst.toLocaleString('ko-KR')}만원</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- 시뮬레이션 할부 조건 요약 (DIRECTIVE 063: 실시간 계산 수치 완전 반영) -->
            <div id="vdrEstimateLoanSummary" class="bg-slate-50 p-3.5 rounded-lg border border-[#E7E9E5] space-y-2 text-xs">
              <div class="font-bold text-slate-800 flex justify-between">
                <span>금융 할부 시뮬레이션 예시</span>
                <span class="text-amber-800 font-normal">※ 금융사 사전 심사에 따른 참고 예시</span>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-600">
                <div>선수금: <strong id="vdrEstDownText" class="text-slate-800 font-mono">-</strong></div>
                <div>할부 원금: <strong id="vdrEstPrincipalText" class="text-slate-800 font-mono">-</strong></div>
                <div>할부 기간: <strong id="vdrEstMonthsText" class="text-slate-800 font-mono">-</strong></div>
                <div>예시 금리: <strong id="vdrEstRateText" class="text-slate-800 font-mono">-</strong></div>
              </div>
              <div class="pt-2 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between text-xs gap-1">
                <div class="text-[11px] text-slate-500">
                  총 예상 이자: <strong id="vdrEstInterestText" class="text-slate-700 font-mono">-</strong>
                </div>
                <div class="flex items-center space-x-1.5">
                  <span class="font-semibold text-slate-700">월 예상 납입금:</span>
                  <span id="vdrEstMonthlyText" class="font-bold text-[#171B1E] text-sm sm:text-base font-mono">-</span>
                </div>
              </div>
            </div>

            <!-- 투명 고지 문구 (DIRECTIVE 066 P1: 시연용 고지 명시 및 내용 보존) -->
            <div class="text-[11px] text-slate-500 leading-relaxed bg-[#F5F6F4] p-3 rounded space-y-1 border border-[#E7E9E5]">
              <p class="font-bold text-red-600">※ [시연용 안내] 본 견적서는 화면 검수용 시연 데이터이며 실제 판매 계약 효력이 없습니다.</p>
              <p>※ 본 안내서는 고객님의 구매 예산 수립을 돕기 위해 공식 정찰가와 표준 취득세율을 기초로 산출된 실차 사전 예상 구매비용 안내서입니다.</p>
              <p>※ 취득세 감면 대상 여부 및 지자체별 공채 할인율에 따라 세금·공채·부대비용 변동 가능성이 있습니다.</p>
              <p>※ 금융 할부 시뮬레이션은 표준 예시 조건이며, 실제 금융사 심사 결과와 다를 수 있습니다.</p>
            </div>
          </div>

          <!-- 모달 하단 액션 버튼 (화면용 / 인쇄 시 숨김) -->
          <div class="pt-3 border-t border-slate-200 flex items-center justify-between no-print">
            <span class="text-xs text-slate-400">문의: ${escapeHtml(showroomLoc || '차마트 온라인 고객상담')}</span>
            <div class="flex items-center space-x-2">
              <button onclick="window.__vdrInstance.closeEstimateModal()" class="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold cursor-pointer">
                닫기
              </button>
              <button onclick="window.print()" class="px-4 py-2 rounded-lg bg-[#171B1E] hover:bg-[#000000] text-white text-xs font-bold cursor-pointer transition-colors flex items-center shadow-xs">
                <i data-lucide="printer" class="w-3.5 h-3.5 mr-1.5 text-white"></i>
                안내서 인쇄 / PDF 저장
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 오프라인 쇼룸 공식 지도 길찾기 모달 (DIRECTIVE 062) -->
      <div id="vdrWayfindingModal" class="fixed inset-0 bg-black/70 z-50 hidden flex items-center justify-center p-4 animate-in fade-in duration-150">
        <div class="bg-white rounded-xl max-w-md w-full p-5 shadow-2xl space-y-4 border border-[#E7E9E5]">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div class="flex items-center space-x-2">
              <i data-lucide="navigation" class="w-5 h-5 text-[#171B1E]"></i>
              <h3 class="text-base font-bold text-[#171B1E]">전시장 오시는 길 (길찾기)</h3>
            </div>
            <button onclick="window.__vdrInstance.closeWayfindingModal()" class="text-slate-400 hover:text-slate-600 p-1 cursor-pointer">
              <i data-lucide="x" class="w-5 h-5"></i>
            </button>
          </div>

          <div class="space-y-3 text-xs text-slate-700">
            <!-- 공식 도로명 주소 및 실측 좌표 안내 (DIRECTIVE 064: 정직한 제휴 전시장) -->
            <div class="bg-slate-50 p-3.5 rounded-lg border border-[#E7E9E5] space-y-1.5 text-xs">
              <div class="flex items-center justify-between">
                <span class="font-bold text-[#171B1E] text-sm">차마트 제휴 전시장 (장한평)</span>
                <span class="text-[10px] bg-slate-200 text-slate-700 font-medium px-1.5 py-0.5 rounded">제휴 매매단지</span>
              </div>
              <div class="text-slate-800 font-medium">서울특별시 성동구 자동차시장1길 70 (용답동)</div>
              <div class="text-[11px] text-slate-500 font-mono">참고 좌표: 37.56191°N, 127.06424°E</div>
              <div class="text-[11px] text-slate-400 pt-0.5">※ 지하철 5호선 장한평역 5·6번 출구 인근 (방문 전 1:1 방문 예약 필수)</div>
            </div>

            <!-- 공식 지도 앱 바로가기 버튼들 -->
            <div class="space-y-2 pt-1">
              <a href="https://map.kakao.com/link/to/차마트제휴전시장,37.56191,127.06424" target="_blank" rel="noopener noreferrer" 
                 class="w-full py-2.5 px-4 bg-[#FEE500] hover:bg-[#FADA0A] text-[#191919] font-bold text-xs rounded-lg flex items-center justify-between cursor-pointer transition-colors shadow-2xs">
                <span class="flex items-center">
                  <i data-lucide="map-pin" class="w-4 h-4 mr-2 text-[#191919]"></i>
                  카카오맵 길찾기 바로가기
                </span>
                <i data-lucide="chevron-right" class="w-4 h-4"></i>
              </a>

              <a href="https://map.naver.com/v5/directions/-/127.06424,37.56191,차마트제휴전시장/-/car" target="_blank" rel="noopener noreferrer"
                 class="w-full py-2.5 px-4 bg-[#03C75A] hover:bg-[#02B351] text-white font-bold text-xs rounded-lg flex items-center justify-between cursor-pointer transition-colors shadow-2xs">
                <span class="flex items-center">
                  <i data-lucide="map" class="w-4 h-4 mr-2 text-white"></i>
                  네이버지도 길찾기 바로가기
                </span>
                <i data-lucide="chevron-right" class="w-4 h-4"></i>
              </a>

              <a href="tmap://route?goalname=차마트제휴전시장&goalx=127.06424&goaly=37.56191" 
                 class="w-full py-2 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-lg flex items-center justify-between cursor-pointer transition-colors">
                <span class="flex items-center">
                  <i data-lucide="navigation-2" class="w-3.5 h-3.5 mr-2 text-slate-600"></i>
                  티맵(TMAP) 내비게이션 실행
                </span>
                <span class="text-[10px] text-slate-400">모바일 전용</span>
              </a>
            </div>
          </div>

          <div class="pt-2 border-t border-slate-100 text-right">
            <button onclick="window.__vdrInstance.closeWayfindingModal()" class="px-4 py-2 bg-slate-900 hover:bg-black text-white text-xs font-semibold rounded-lg cursor-pointer">
              확인 닫기
            </button>
          </div>
        </div>
      </div>
    `;

    // 6. 이벤트 바인딩 및 할부 계산기 초기화
    this.bindEvents();
    this.updateLoanCalc();
    this.selectPart('hood');
    this.updateFavoriteUi();

    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  // 진단 상태 요약 박스 렌더러
  renderDiagnosticCard(title, statusCode, iconName) {
    let colorClass, statusLabel;
    if (statusCode === 'VERIFIED_CLEAN') {
      colorClass = 'bg-emerald-50/70 border-emerald-200 text-emerald-800';
      statusLabel = '확인됨 (정상)';
    } else if (statusCode === 'VERIFIED_ISSUE') {
      colorClass = 'bg-amber-50/70 border-amber-200 text-amber-800';
      statusLabel = '이력 있음 (이상확인)';
    } else {
      colorClass = 'bg-slate-50 border-slate-200 text-slate-600';
      statusLabel = '미확인 (전산대기)';
    }

    return `
      <div class="p-3 rounded border ${colorClass} space-y-1">
        <div class="flex items-center justify-between">
          <span class="text-slate-500 truncate text-[11px]">${escapeHtml(title)}</span>
          <i data-lucide="${iconName}" class="w-3.5 h-3.5 opacity-70 shrink-0"></i>
        </div>
        <div class="font-bold text-xs truncate">${statusLabel}</div>
      </div>
    `;
  }

  // 차량 부위별 독자 2D SVG 다이어그램 렌더러
  renderCarDiagramSvg(acc) {
    const parts = acc.diagram_parts || {};

    const keyMap = {
      'hood': 'hood',
      'front-bumper': 'hood',
      'fender-fl': 'front_fender_l',
      'fender-fr': 'front_fender_r',
      'door-fl': 'front_door_l',
      'door-fr': 'front_door_r',
      'door-rl': 'rear_door_l',
      'door-rr': 'rear_door_r',
      'roof': 'roof',
      'trunk': 'trunk_lid',
      'rear-bumper': 'trunk_lid',
      'frame-rad-support': 'radiator_support',
      'frame-member-l': 'front_side_member',
      'frame-member-r': 'front_side_member',
      'pillar-a': 'pillar_a',
      'pillar-a-r': 'pillar_a',
      'pillar-b': 'pillar_b',
      'pillar-b-r': 'pillar_b',
      'pillar-c': 'pillar_c',
      'pillar-c-r': 'pillar_c'
    };

    const getColor = (partKey) => {
      const resolvedKey = keyMap[partKey] || partKey.replace(/-/g, '_');
      const p = parts[resolvedKey] || parts[partKey];
      if (!p) return '#CBD5E1';
      const st = String(p.status || '').toUpperCase();
      if (st === 'CLEAN' || st === 'VERIFIED_NORMAL') return '#10B981';
      if (st === 'CHANGED' || st === 'REPLACED' || st === 'VERIFIED_REPAIRED' || st === 'VERIFIED_REPLACED') return '#F59E0B';
      if (st === 'DAMAGE' || st === 'DAMAGED' || st === 'VERIFIED_DAMAGED') return '#EF4444';
      return '#CBD5E1';
    };

    return `
      <svg viewBox="0 0 280 440" class="w-full h-full max-h-[360px] drop-shadow-2xs select-none" xmlns="http://www.w3.org/2000/svg">
        <!-- 배경 차체 외곽선 -->
        <path d="M 60,70 C 60,30 220,30 220,70 L 225,120 L 235,160 L 235,320 L 225,370 L 220,410 C 220,430 60,430 60,410 L 55,370 L 45,320 L 45,160 L 55,120 Z" 
              fill="#F8FAFC" stroke="#94A3B8" stroke-width="2" stroke-linejoin="round" />
        
        <!-- [외판 부위] -->
        <path id="part-hood" d="M 75,70 C 80,45 200,45 205,70 L 210,125 L 70,125 Z" 
              fill="${getColor('hood')}" opacity="0.85" stroke="#FFFFFF" stroke-width="2" class="cursor-pointer hover:opacity-100 transition-opacity" 
              onclick="window.__vdrInstance.selectPart('hood')" />
        
        <path id="part-front-bumper" d="M 60,50 C 70,30 210,30 220,50 L 215,68 L 65,68 Z" 
              fill="${getColor('front-bumper')}" opacity="0.8" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('front-bumper')" />

        <path id="part-fender-fl" d="M 55,75 L 72,75 L 68,135 L 48,135 Z" 
              fill="${getColor('fender-fl')}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('fender-fl')" />
        <path id="part-fender-fr" d="M 208,75 L 225,75 L 232,135 L 212,135 Z" 
              fill="${getColor('fender-fr')}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('fender-fr')" />

        <path id="part-door-fl" d="M 46,140 L 68,140 L 68,220 L 46,220 Z" 
              fill="${getColor('door-fl')}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('door-fl')" />
        <path id="part-door-fr" d="M 212,140 L 234,140 L 234,220 L 212,220 Z" 
              fill="${getColor('door-fr')}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('door-fr')" />
        <path id="part-door-rl" d="M 46,225 L 68,225 L 68,305 L 46,305 Z" 
              fill="${getColor('door-rl')}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('door-rl')" />
        <path id="part-door-rr" d="M 212,225 L 234,225 L 234,305 L 212,305 Z" 
              fill="${getColor('door-rr')}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('door-rr')" />

        <rect id="part-roof" x="72" y="145" width="136" height="155" rx="4" 
              fill="${getColor('roof')}" opacity="0.9" stroke="#FFFFFF" stroke-width="2" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('roof')" />

        <path id="part-trunk" d="M 72,325 L 208,325 L 202,390 L 78,390 Z" 
              fill="${getColor('trunk')}" opacity="0.85" stroke="#FFFFFF" stroke-width="2" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('trunk')" />

        <path id="part-rear-bumper" d="M 62,395 C 75,420 205,420 218,395 L 215,415 C 205,430 75,430 65,415 Z" 
              fill="${getColor('rear-bumper')}" opacity="0.8" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('rear-bumper')" />

        <!-- [주요 골격] -->
        <rect id="frame-rad-support" x="78" y="60" width="124" height="6" rx="2" fill="${getColor('frame-rad-support')}" stroke="#FFFFFF" stroke-width="1" class="cursor-pointer hover:scale-105" onclick="window.__vdrInstance.selectPart('frame-rad-support')" />
        <rect id="frame-member-l" x="80" y="80" width="8" height="240" rx="2" fill="${getColor('frame-member-l')}" opacity="0.85" stroke="#FFFFFF" stroke-width="1" class="cursor-pointer hover:scale-105" onclick="window.__vdrInstance.selectPart('frame-member-l')" />
        <rect id="frame-member-r" x="192" y="80" width="8" height="240" rx="2" fill="${getColor('frame-member-r')}" opacity="0.85" stroke="#FFFFFF" stroke-width="1" class="cursor-pointer hover:scale-105" onclick="window.__vdrInstance.selectPart('frame-member-r')" />

        <!-- 필러 A, B, C 표시 -->
        <circle id="part-pillar-a" cx="70" cy="140" r="6" fill="${getColor('pillar-a')}" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-a')" />
        <circle id="part-pillar-a-r" cx="210" cy="140" r="6" fill="${getColor('pillar-a-r')}" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-a-r')" />
        <circle id="part-pillar-b" cx="70" cy="222" r="6" fill="${getColor('pillar-b')}" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-b')" />
        <circle id="part-pillar-b-r" cx="210" cy="222" r="6" fill="${getColor('pillar-b-r')}" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-b-r')" />
        <circle id="part-pillar-c" cx="70" cy="315" r="6" fill="${getColor('pillar-c')}" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-c')" />
        <circle id="part-pillar-c-r" cx="210" cy="315" r="6" fill="${getColor('pillar-c-r')}" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-c-r')" />
      </svg>
    `;
  }

  selectPart(partKey) {
    const acc = this.data?.accident_summary || this.data?.accident_history || {};
    const parts = acc.diagram_parts || {};

    const keyMap = {
      'hood': 'hood',
      'front-bumper': 'hood',
      'fender-fl': 'front_fender_l',
      'fender-fr': 'front_fender_r',
      'door-fl': 'front_door_l',
      'door-fr': 'front_door_r',
      'door-rl': 'rear_door_l',
      'door-rr': 'rear_door_r',
      'roof': 'roof',
      'trunk': 'trunk_lid',
      'rear-bumper': 'trunk_lid',
      'frame-rad-support': 'radiator_support',
      'frame-member-l': 'front_side_member',
      'frame-member-r': 'front_side_member',
      'pillar-a': 'pillar_a',
      'pillar-a-r': 'pillar_a',
      'pillar-b': 'pillar_b',
      'pillar-b-r': 'pillar_b',
      'pillar-c': 'pillar_c',
      'pillar-c-r': 'pillar_c'
    };

    const resolvedKey = keyMap[partKey] || partKey.replace(/-/g, '_');
    const partInfo = parts[resolvedKey] || parts[partKey];

    const nameEl = document.getElementById('vdrSelectedPartName');
    const badgeEl = document.getElementById('vdrSelectedPartBadge');
    const catEl = document.getElementById('vdrSelectedPartCategory');
    const stateEl = document.getElementById('vdrSelectedPartState');
    const evEl = document.getElementById('vdrSelectedPartEvidence');

    if (!partInfo) {
      if (nameEl) nameEl.textContent = partKey;
      if (badgeEl) {
        badgeEl.textContent = '미확인 (전산대기)';
        badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600';
      }
      if (catEl) catEl.textContent = '부위 정보 없음';
      if (stateEl) stateEl.textContent = '점검 기록 미기재';
      if (evEl) evEl.textContent = '실차 전산 원본 확인 필요';
      return;
    }

    const partDisplayName = partInfo.name || partInfo.part_name || partKey;
    if (nameEl) nameEl.textContent = partDisplayName;
    if (catEl) catEl.textContent = (partInfo.type === 'FRAME') ? '주요 골격 (프레임)' : '외부 패널 (외판)';
    if (stateEl) stateEl.textContent = partInfo.finding || '점검 내용 확인';
    if (evEl) evEl.textContent = partInfo.evidence || '실차 전산 증빙 대기';

    if (badgeEl) {
      const st = String(partInfo.status || '').toUpperCase();
      if (st === 'CLEAN' || st === 'VERIFIED_NORMAL') {
        badgeEl.textContent = '정상 (무사고)';
        badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-100 text-emerald-800';
      } else if (st === 'CHANGED' || st === 'REPLACED' || st === 'VERIFIED_REPAIRED' || st === 'VERIFIED_REPLACED') {
        badgeEl.textContent = '단순교환/수리';
        badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800';
      } else if (st === 'DAMAGE' || st === 'DAMAGED' || st === 'VERIFIED_DAMAGED') {
        badgeEl.textContent = '골격손상';
        badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-800';
      } else {
        badgeEl.textContent = '미확인 (증빙대기)';
        badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600';
      }
    }
  }

  // 타이어 4개 바퀴 게이지
  renderTireGauges(d) {
    const tires = d.accident_summary?.tires || d.tires || d.consumables_status?.tires || {};
    const positions = [
      { key: 'fl', label: '전륜 운전석 (FL)', val: tires.fl },
      { key: 'fr', label: '전륜 동승석 (FR)', val: tires.fr },
      { key: 'rl', label: '후륜 좌측 (RL)', val: tires.rl },
      { key: 'rr', label: '후륜 우측 (RR)', val: tires.rr }
    ];

    return `
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        ${positions.map(pos => {
          const depth = (pos.val && typeof pos.val.depth_mm === 'number') ? pos.val.depth_mm : null;
          const percent = depth ? Math.min(100, Math.round((depth / 8.0) * 100)) : null;
          const barColor = percent > 60 ? 'bg-emerald-500' : (percent > 30 ? 'bg-amber-500' : 'bg-rose-500');

          return `
            <div class="bg-slate-50 p-2.5 rounded border border-[#E5E8EC] space-y-1.5">
              <div class="flex items-center justify-between text-xs">
                <span class="font-medium text-slate-700">${escapeHtml(pos.label)}</span>
                <span class="font-mono font-semibold ${depth ? 'text-slate-900' : 'text-slate-400'}">
                  ${depth ? `${depth.toFixed(1)} mm` : '미측정'}
                </span>
              </div>
              <div class="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                ${percent !== null 
                  ? `<div class="${barColor} h-full rounded-full transition-all duration-300" style="width: ${percent}%;"></div>` 
                  : '<div class="bg-slate-300 h-full w-0"></div>'}
              </div>
              <div class="flex items-center justify-between text-[10px] text-slate-400">
                <span>마모한계 1.6mm</span>
                <span>${depth ? `신품대비 약 ${percent}%` : '실차 확인 필요'}</span>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  // 소모품 상태 그리드
  renderConsumablesGrid(d) {
    const cs = d.consumables_status || {};
    const items = [
      { name: '브레이크 패드', val: cs.brake_pads?.status || (cs.brake_pads ? '양호' : null), detail: cs.brake_pads?.detail || '마모 잔량 적정', icon: 'disc' },
      { name: '엔진 오일 / 필터', val: cs.engine_oil?.status || (cs.engine_oil ? '양호' : null), detail: cs.engine_oil?.detail || '적정 레벨 및 점도 유지', icon: 'droplet' },
      { name: '시동 배터리', val: cs.battery?.status || (cs.battery ? '정상' : null), detail: cs.battery?.detail || '12.5V 이상 충전상태 양호', icon: 'battery' },
      { name: '냉각수 / 부동액', val: cs.coolant?.status || (cs.coolant ? '적정' : null), detail: cs.coolant?.detail || '적정 수위 및 비중 확인', icon: 'activity' }
    ];

    return `
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
        ${items.map(it => {
          const isVerified = Boolean(it.val);
          return `
            <div class="bg-slate-50 p-2.5 rounded border border-[#E5E8EC] space-y-1">
              <div class="flex items-center justify-between text-slate-500">
                <span class="text-[11px] truncate">${escapeHtml(it.name)}</span>
                <i data-lucide="${it.icon}" class="w-3.5 h-3.5 opacity-60 shrink-0"></i>
              </div>
              <div class="font-bold ${isVerified ? 'text-slate-800' : 'text-slate-400'}">
                ${isVerified ? escapeHtml(it.val) : '미확인'}
              </div>
              <div class="text-[10px] text-slate-400 truncate">
                ${isVerified ? escapeHtml(it.detail) : '실차 점검 대기'}
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  switchDiagramTab(tab) {
    this.currentDiagramTab = tab;
    const btnAll = document.getElementById('vdrDiagTabAll');
    const btnOuter = document.getElementById('vdrDiagTabOuter');
    const btnFrame = document.getElementById('vdrDiagTabFrame');

    [btnAll, btnOuter, btnFrame].forEach(b => {
      if (b) b.className = "px-2.5 py-1 rounded text-slate-600 hover:text-slate-900 cursor-pointer";
    });

    const activeBtn = tab === 'all' ? btnAll : (tab === 'outer' ? btnOuter : btnFrame);
    if (activeBtn) activeBtn.className = "px-2.5 py-1 rounded bg-white text-slate-900 shadow-2xs cursor-pointer";

    const outerParts = ['part-hood', 'part-front-bumper', 'part-fender-fl', 'part-fender-fr', 'part-door-fl', 'part-door-fr', 'part-door-rl', 'part-door-rr', 'part-roof', 'part-trunk', 'part-rear-bumper'];
    const frameParts = ['frame-rad-support', 'frame-member-l', 'frame-member-r', 'part-pillar-a', 'part-pillar-a-r', 'part-pillar-b', 'part-pillar-b-r', 'part-pillar-c', 'part-pillar-c-r'];

    outerParts.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = (tab === 'all' || tab === 'outer') ? 'block' : 'none';
    });

    frameParts.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = (tab === 'all' || tab === 'frame') ? 'block' : 'none';
    });
  }

  renderOptionsGrid(d) {
    const categorized = d.options_categorized || {};
    if (Object.keys(categorized).length > 0) {
      let html = '';
      for (const [catName, list] of Object.entries(categorized)) {
        if (list && list.length > 0) {
          const badges = list.map(o => `
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-normal bg-slate-100 text-slate-700 border border-slate-200">
              <i data-lucide="check" class="w-3 h-3 mr-1 text-[#171B1E]"></i>
              ${escapeHtml(o.name || o)}
            </span>
          `).join(' ');
          html += `
            <div class="space-y-1.5">
              <div class="text-xs font-semibold text-slate-500">${escapeHtml(catName)}</div>
              <div class="flex flex-wrap gap-1.5">${badges}</div>
            </div>
          `;
        }
      }
      return html || '<div class="text-xs text-slate-400">장착 옵션 사양을 정리 중입니다.</div>';
    } else if (d.options && d.options.length > 0) {
      const badges = d.options.map(o => `
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-normal bg-slate-100 text-slate-700 border border-slate-200">
          <i data-lucide="check" class="w-3 h-3 mr-1 text-[#171B1E]"></i>
          ${escapeHtml(o)}
        </span>
      `).join(' ');
      return `<div class="flex flex-wrap gap-1.5">${badges}</div>`;
    }
    return '<div class="text-xs text-slate-400">확인된 주요 옵션 사양을 정리 중입니다.</div>';
  }

  updateLoanCalc() {
    const downSelect = document.getElementById('vdrCalcDownPayment');
    const monthSelect = document.getElementById('vdrCalcMonths');
    const rateSelect = document.getElementById('vdrCalcRate');
    const resultEl = document.getElementById('vdrCalcMonthlyResult');
    const totalEl = document.getElementById('vdrCalcTotalInterestResult');
    if (!resultEl) return;

    const targetPrice = this.data?.target_price || 0;
    if (targetPrice <= 0) {
      resultEl.textContent = '상담 문의';
      if (totalEl) totalEl.textContent = '이자: - / 총액: -';
      return;
    }

    const downRate = downSelect ? parseFloat(downSelect.value) : 10;
    const months = monthSelect ? parseInt(monthSelect.value, 10) : 60;
    const annualRate = rateSelect ? parseFloat(rateSelect.value) * 100 : 5.9;

    const res = calculateVehicleLoanPure({
      priceWon: targetPrice * 10000,
      downRate: downRate,
      annualRate: annualRate,
      months: months
    });

    if (res.principalWon === 0) {
      resultEl.textContent = '선수금 100% (월 0원)';
      if (totalEl) totalEl.textContent = '총 납부 이자: 0원 / 총 상환액: 0원';
      return;
    }

    resultEl.textContent = `월 약 ${res.monthlyTenThousand.toLocaleString('ko-KR')}만원`;
    if (totalEl) {
      totalEl.textContent = `예상 이자: 약 ${res.totalInterestTenThousand.toLocaleString('ko-KR')}만원 / 총 상환액: 약 ${res.totalRepayTenThousand.toLocaleString('ko-KR')}만원`;
    }
  }

  selectPhoto(index) {
    if (!this.photos || index < 0 || index >= this.photos.length) return;
    this.currentPhotoIdx = index;
    const photo = this.photos[this.currentPhotoIdx];
    
    const mainImg = document.getElementById('vdrMainImage');
    if (mainImg) mainImg.src = photo.url;

    const capEl = document.getElementById('vdrPhotoCaption');
    if (capEl) capEl.textContent = photo.caption;

    // 한글 부위 라벨 갱신 (DIRECTIVE 071)
    const partLabelEl = document.getElementById('vdrPhotoPartLabel');
    if (partLabelEl) partLabelEl.textContent = photo.display_label || photo.caption || '외관';

    const countEl = document.getElementById('vdrPhotoCounter');
    if (countEl) countEl.textContent = `${this.currentPhotoIdx + 1} / ${this.photos.length}`;

    if (this.lightboxOpen) {
      const lbImg = document.getElementById('vdrLightboxImage');
      const lbCap = document.getElementById('vdrLightboxCaption');
      const lbCount = document.getElementById('vdrLightboxCounter');
      if (lbImg) lbImg.src = photo.url;
      if (lbCap) lbCap.textContent = photo.caption;
      if (lbCount) lbCount.textContent = `${this.currentPhotoIdx + 1} / ${this.photos.length}`;
    }

    const container = document.getElementById('vdrThumbnailsContainer');
    if (container) {
      const btns = container.querySelectorAll('.vdr-thumb-btn');
      btns.forEach((btn, idx) => {
        if (idx === this.currentPhotoIdx) {
          btn.className = "vdr-thumb-btn w-20 aspect-[5/3] rounded overflow-hidden shrink-0 border-2 transition-all border-[#171B1E] ring-1 ring-[#171B1E] cursor-pointer";
        } else {
          btn.className = "vdr-thumb-btn w-20 aspect-[5/3] rounded overflow-hidden shrink-0 border-2 transition-all border-[#E5E8EC] opacity-70 hover:opacity-100 cursor-pointer";
        }
      });
    }
  }

  filterPhotoCategory(cat) {
    this.activePhotoCategory = cat;
    
    // 카테고리 탭 버튼 스타일 갱신
    const cats = ['ALL', 'EXTERIOR_FULL', 'EXTERIOR_PANEL', 'INTERIOR', 'ENGINE_MECHANICAL', 'OPTION_FEATURE', 'DOCUMENT'];
    cats.forEach(c => {
      const btn = document.getElementById(`vdrTabCat${c}`);
      if (btn) {
        if (c === cat) {
          btn.className = "px-3 py-1.5 rounded-full transition-all bg-[#171B1E] text-white font-bold cursor-pointer shrink-0 shadow-2xs";
        } else {
          btn.className = "px-3 py-1.5 rounded-full transition-all bg-slate-100 hover:bg-slate-200 text-slate-700 cursor-pointer shrink-0";
        }
      }
    });

    // 썸네일 스트립 필터링 표시/숨김
    const container = document.getElementById('vdrThumbnailsContainer');
    let firstMatchIdx = -1;
    if (container) {
      const btns = container.querySelectorAll('.vdr-thumb-btn');
      btns.forEach((btn, idx) => {
        const itemCat = btn.getAttribute('data-cat') || 'EXTERIOR_FULL';
        if (cat === 'ALL' || itemCat === cat) {
          btn.classList.remove('hidden');
          if (firstMatchIdx === -1) firstMatchIdx = idx;
        } else {
          btn.classList.add('hidden');
        }
      });
    }

    if (firstMatchIdx !== -1) {
      this.selectPhoto(firstMatchIdx);
    }
  }

  prevPhoto() {
    const nextIdx = (this.currentPhotoIdx - 1 + this.photos.length) % this.photos.length;
    this.selectPhoto(nextIdx);
  }

  nextPhoto() {
    const nextIdx = (this.currentPhotoIdx + 1) % this.photos.length;
    this.selectPhoto(nextIdx);
  }

  openLightbox(triggerEl) {
    this.lightboxTriggerEl = triggerEl || document.activeElement;
    const lb = document.getElementById('vdrLightboxModal');
    if (!lb) return;
    this.lightboxOpen = true;
    lb.classList.remove('hidden');
    this.selectPhoto(this.currentPhotoIdx);
    if (window.lucide) window.lucide.createIcons();
    const closeBtn = lb.querySelector('button');
    if (closeBtn) closeBtn.focus();
  }

  closeLightbox() {
    const lb = document.getElementById('vdrLightboxModal');
    if (lb) lb.classList.add('hidden');
    this.lightboxOpen = false;
    if (this.lightboxTriggerEl && typeof this.lightboxTriggerEl.focus === 'function') {
      this.lightboxTriggerEl.focus();
    }
  }

  toggleZoom() {
    const img = document.getElementById('vdrMainImage');
    if (!img) return;
    this.isZoomed = !this.isZoomed;
    img.style.transform = this.isZoomed ? 'scale(2)' : 'scale(1)';
    img.style.zIndex = this.isZoomed ? '30' : '1';
    img.style.transition = 'transform 0.25s ease';
  }

  // DIRECTIVE 063: 견적서(실차 예상 구매비용 안내서) 모달 제어 및 실시간 계산값 동기화
  openEstimateModal() {
    const downSelect = document.getElementById('vdrCalcDownPayment');
    const monthSelect = document.getElementById('vdrCalcMonths');
    const rateSelect = document.getElementById('vdrCalcRate');
    const targetPrice = this.data?.target_price || 0;

    const downRate = downSelect ? parseFloat(downSelect.value) : 10;
    const months = monthSelect ? parseInt(monthSelect.value, 10) : 60;
    const annualRate = rateSelect ? parseFloat(rateSelect.value) * 100 : 5.9;

    const res = calculateVehicleLoanPure({
      priceWon: targetPrice * 10000,
      downRate: downRate,
      annualRate: annualRate,
      months: months
    });

    const estDown = document.getElementById('vdrEstDownText');
    const estMonths = document.getElementById('vdrEstMonthsText');
    const estRate = document.getElementById('vdrEstRateText');
    const estMonthly = document.getElementById('vdrEstMonthlyText');
    const estPrincipal = document.getElementById('vdrEstPrincipalText');
    const estInterest = document.getElementById('vdrEstInterestText');

    if (estDown) estDown.textContent = `${Math.round(res.downRate)}% (${res.downTenThousand.toLocaleString('ko-KR')}만원)`;
    if (estPrincipal) estPrincipal.textContent = `${res.principalTenThousand.toLocaleString('ko-KR')}만원`;
    if (estMonths) estMonths.textContent = `${res.months}개월`;
    if (estRate) estRate.textContent = `연 ${res.annualRate.toFixed(1)}%`;
    if (estMonthly) estMonthly.textContent = `월 약 ${res.monthlyTenThousand.toLocaleString('ko-KR')}만원`;
    if (estInterest) estInterest.textContent = `약 ${res.totalInterestTenThousand.toLocaleString('ko-KR')}만원`;

    const modal = document.getElementById('vdrEstimatePrintModal');
    if (modal) {
      modal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
      if (window.lucide) window.lucide.createIcons();
    }
  }

  closeEstimateModal() {
    const modal = document.getElementById('vdrEstimatePrintModal');
    if (modal) {
      modal.classList.add('hidden');
      document.body.style.overflow = '';
    }
  }

  // DIRECTIVE 062: 공식 지도 길찾기 모달 제어
  openWayfindingModal() {
    const modal = document.getElementById('vdrWayfindingModal');
    if (modal) {
      modal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
      if (window.lucide) window.lucide.createIcons();
    }
  }

  closeWayfindingModal() {
    const modal = document.getElementById('vdrWayfindingModal');
    if (modal) {
      modal.classList.add('hidden');
      document.body.style.overflow = '';
    }
  }

  // DIRECTIVE 063: 전시장 공식 도로명 주소 원클릭 클립보드 복사
  copyShowroomAddress() {
    const addr = this.data?.branch_location || '서울특별시 성동구 자동차시장1길 70 (용답동) 장한평 자동차매매단지';
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(addr).then(() => {
        const textSpan = document.getElementById('vdrBtnCopyAddrText');
        if (textSpan) {
          textSpan.textContent = '복사 완료!';
          setTimeout(() => { textSpan.textContent = '주소 복사'; }, 2000);
        }
      }).catch(() => {
        alert('주소: ' + addr);
      });
    } else {
      alert('전시장 주소: ' + addr);
    }
  }

  // DIRECTIVE 062: 관심 차량 찜(하트) 토글 및 localStorage 동기화
  toggleFavorite() {
    if (!this.data || !this.data.id) return;
    try {
      const stored = JSON.parse(localStorage.getItem('chamart_favorites') || '[]');
      const index = stored.indexOf(this.data.id);
      if (index >= 0) {
        stored.splice(index, 1);
      } else {
        stored.push(this.data.id);
      }
      localStorage.setItem('chamart_favorites', JSON.stringify(stored));
      this.updateFavoriteUi();
      
      // 전역 찜 카운트나 목록과 동기화
      if (typeof window.updateAllFavoritesUi === 'function') {
        window.updateAllFavoritesUi();
      }
    } catch (err) {
      console.warn('[VehicleDetailRenderer] Favorite toggle error:', err);
    }
  }

  updateFavoriteUi() {
    if (!this.data || !this.data.id) return;
    try {
      const stored = JSON.parse(localStorage.getItem('chamart_favorites') || '[]');
      const isFav = stored.includes(this.data.id);
      const icon = document.getElementById('vdrIconFavorite');
      const btn = document.getElementById('vdrBtnFavorite');
      if (icon) {
        if (isFav) {
          icon.classList.remove('text-slate-400');
          icon.classList.add('text-rose-500', 'fill-rose-500');
          if (btn) btn.setAttribute('title', '관심 차량에서 제거');
        } else {
          icon.classList.remove('text-rose-500', 'fill-rose-500');
          icon.classList.add('text-slate-400');
          if (btn) btn.setAttribute('title', '관심 차량으로 찜');
        }
      }
    } catch (err) {
      // 무시
    }
  }

  openInspectionDocModal(triggerEl) {
    // DIRECTIVE 062: 허위 공인 문서 모달이 제거되었으므로 실제 URL이 있는 경우에만 새 창 오픈
    if (this.data && this.data.accident_history && this.data.accident_history.inspection_document_url) {
      window.open(this.data.accident_history.inspection_document_url, '_blank');
    }
  }

  closeInspectionDocModal() {
    // 안전한 호환용 빈 구현
  }

  openBottomSheet() {
    const bs = document.getElementById('vdrBottomSheetModal');
    if (bs) {
      bs.classList.remove('hidden');
      if (window.lucide) window.lucide.createIcons();
    }
  }

  closeBottomSheet() {
    const bs = document.getElementById('vdrBottomSheetModal');
    if (bs) bs.classList.add('hidden');
  }

  handleKakaoConsult(channelId) {
    const validId = channelId || this.data?.kakao_channel_id || window.__CHAMART_KAKAO_CHANNEL_ID;
    if (!validId) {
      alert('현재 차마트 카카오톡 1:1 전용 채널 개설 준비 중입니다. 1:1 방문 예약 및 구매 상담 신청 폼을 이용해 주시기 바랍니다.');
      return;
    }
    window.open(`https://pf.kakao.com/_${validId}/chat`, '_blank');
  }

  async handleSubmitConsult(e, isBottomSheet = false) {
    e.preventDefault();
    const prefix = isBottomSheet ? 'vdrBs' : 'vdr';
    const name = document.getElementById(`${prefix}CustName`)?.value.trim();
    const phone = document.getElementById(`${prefix}CustPhone`)?.value.trim();
    const visitDate = document.getElementById(`${prefix}CustDate`)?.value;
    const memo = document.getElementById(`${prefix}CustMemo`)?.value.trim();
    const agree = document.getElementById(`${prefix}PrivacyAgree`)?.checked;

    if (!name || !phone || !agree) {
      alert('성함, 연락처 및 개인정보 수집 동의는 필수입니다.');
      return;
    }

    const submitBtn = document.getElementById(isBottomSheet ? 'vdrBsBtnSubmit' : 'vdrBtnSubmitConsult');
    const origHtml = submitBtn ? submitBtn.innerHTML : '';
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⟳</span>접수 처리 중...';
    }

    const payload = {
      vehicle_id: this.data.id,
      name: name,
      phone: phone,
      preferred_date: visitDate || null,
      content: memo || `[차마트 방문예약] ${this.data.model_name}`,
      privacy_agreed: true,
      lead_source: isBottomSheet ? 'CHAMART_MOBILE_BOTTOM_SHEET' : 'CHAMART_DESKTOP_PANEL'
    };

    try {
      if (this.options.onSubmitConsultation) {
        await this.options.onSubmitConsultation(payload);
      } else {
        const res = await fetch('/api/chamart/consultations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await res.json().catch(() => ({}));

        if (!res.ok || !data.success) {
          const errMsg = data.detail || data.message || `서버 오류 (HTTP ${res.status})`;
          alert(`[상담 접수 실패] ${errMsg}\n입력하신 내용을 확인 후 다시 시도해 주세요.`);
          return;
        }

        const consultId = data.consultation_id || '접수완료';
        alert(`[방문 예약 정상 접수]\n${name} 고객님, ${this.data.model_name} 차량 방문 예약이 접수되었습니다.\n\n접수번호: #${consultId}\n차마트 장한평 본사 전담 매니저가 확인 후 연락드리겠습니다.`);
        
        const form = document.getElementById(isBottomSheet ? 'vdrBsConsultForm' : 'vdrConsultForm');
        if (form) form.reset();
        if (isBottomSheet) this.closeBottomSheet();
      }
    } catch (err) {
      console.error('[VehicleDetailRenderer] Consultation error:', err);
      alert(`[상담 접수 오류] 네트워크 또는 서버와 통신 중 문제가 발생했습니다: ${err.message}`);
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origHtml;
      }
    }
  }

  bindEvents() {
    const btnBack = document.getElementById('vdrBtnBack');
    if (btnBack && this.options.onBack) {
      btnBack.addEventListener('click', () => this.options.onBack());
    }

    const btnPub = document.getElementById('vdrBtnTogglePublish');
    if (btnPub && this.options.onTogglePublish) {
      btnPub.addEventListener('click', () => {
        this.options.onTogglePublish(this.data.id, Boolean(this.data.is_public));
      });
    }

    const btnEdit = document.getElementById('vdrBtnEditMaster');
    if (btnEdit && this.options.onEditMaster) {
      btnEdit.addEventListener('click', () => {
        this.options.onEditMaster(this.data);
      });
    }

    const btnPrev = document.getElementById('vdrBtnPrevPhoto');
    if (btnPrev) {
      btnPrev.addEventListener('click', (e) => {
        e.stopPropagation();
        this.prevPhoto();
      });
    }
    const btnNext = document.getElementById('vdrBtnNextPhoto');
    if (btnNext) {
      btnNext.addEventListener('click', (e) => {
        e.stopPropagation();
        this.nextPhoto();
      });
    }

    const viewport = document.getElementById('vdrGalleryViewport');
    if (viewport) {
      viewport.addEventListener('touchstart', (e) => {
        this.touchStartX = e.changedTouches[0].screenX;
      }, { passive: true });

      viewport.addEventListener('touchend', (e) => {
        const currentTime = new Date().getTime();
        const tapLength = currentTime - (this.lastTapTime || 0);
        if (tapLength < 350 && tapLength > 50) {
          // 더블탭 감지 -> 2배 확대 토글
          e.preventDefault();
          this.toggleZoom();
          this.lastTapTime = 0;
          return;
        }
        this.lastTapTime = currentTime;

        this.touchEndX = e.changedTouches[0].screenX;
        const diff = this.touchEndX - this.touchStartX;
        if (Math.abs(diff) > 40) {
          if (diff > 0) {
            this.prevPhoto();
          } else {
            this.nextPhoto();
          }
        }
      }, { passive: false });
    }

    window.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') this.prevPhoto();
      if (e.key === 'ArrowRight') this.nextPhoto();
      if (e.key === 'Escape') {
        if (this.lightboxOpen) this.closeLightbox();
        this.closeBottomSheet();
        this.closeEstimateModal();
        this.closeWayfindingModal();
        this.closeInspectionDocModal();
      }
    });
  }
}

window.VehicleDetailRenderer = VehicleDetailRenderer;
