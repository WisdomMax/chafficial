/**
 * CHA-FICIAL / CHAMART 공통 프리미엄 차량 상세 렌더러 (DIRECTIVE 054)
 * 엔카급 1320px 대형 갤러리, 8대 핵심 스펙 그리드, 단일 SSOT 투명 성능점검표,
 * XSS 방어 인코딩, 관리자 콜백 계약 일치 및 390x844 모바일 반응형 완비
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
  }

  render(vehicleData) {
    if (!this.container) {
      console.error('[VehicleDetailRenderer] Container not found.');
      return;
    }
    this.container.classList.add('pb-28', 'sm:pb-8');
    this.data = vehicleData;
    this.currentPhotoIdx = 0;

    // 1. 사진 목록 정규화 (1:1 실차 사진 매핑 및 중립 플레이스홀더 보장)
    if (this.data.photos && this.data.photos.length > 0) {
      this.photos = this.data.photos.map(p => ({
        url: p.photo_url || p.url,
        caption: p.caption || p.category || `${this.data.model_name} 실차 사진`
      }));
    } else if (this.data.primary_photo_url && !this.data.primary_photo_url.includes('placeholder')) {
      this.photos = [{
        url: this.data.primary_photo_url,
        caption: `${this.data.model_name} 대표 실차 사진`
      }];
    } else {
      this.photos = [{
        url: '/static/img/vehicles/neutral_car_placeholder.jpg',
        caption: '차량 실차 사진 촬영 및 검증 대기 중'
      }];
    }

    const d = this.data;
    const isAdmin = this.options.isAdmin;

    // 2. 관리자 상단 툴바 HTML (XSS 방어 및 반응형 정렬)
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
        <div class="bg-[#0F172A] text-white border-b border-slate-800 px-4 sm:px-6 py-3 rounded-2xl mb-6 shadow-md">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div class="flex flex-wrap items-center gap-2 sm:gap-3">
              <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-[#247D7C] text-white tracking-wide shrink-0">
                <i data-lucide="shield-check" class="w-3.5 h-3.5 mr-1"></i>
                차피셜 관리자 전용 모드
              </span>
              <span class="text-xs text-slate-300">
                소유유형: <strong class="text-white">${escapeHtml(d.ownership_type || 'CHAMART_OWNED')}</strong>
              </span>
              <span class="text-slate-600 hidden sm:inline">|</span>
              <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                <span>매입원가: <strong class="text-teal-300">${pur}</strong></span>
                <span>상품화: <strong class="text-slate-300">${rec}</strong></span>
                <span>추정마진: <strong class="text-amber-300 font-bold">${margin}</strong></span>
              </div>
            </div>
            <div class="flex items-center space-x-2 shrink-0">
              <button id="vdrBtnTogglePublish" class="px-3 py-1.5 text-xs font-bold rounded-lg shadow-xs transition-colors flex items-center ${pubBtnClass}">
                <i data-lucide="${isPub ? 'eye-off' : 'check-circle-2'}" class="w-3.5 h-3.5 mr-1"></i>
                ${pubBtnText}
              </button>
              <button id="vdrBtnEditMaster" class="px-3 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg shadow-xs transition-colors flex items-center">
                <i data-lucide="edit-3" class="w-3.5 h-3.5 mr-1"></i>
                마스터 제원 수정
              </button>
            </div>
          </div>
        </div>
      `;
    }

    // 3. 가격 및 제원 바인딩 변수
    const targetPriceFormatted = d.target_price ? `${Number(d.target_price).toLocaleString('ko-KR')}만원` : '가격 상담';
    const monthlyEst = d.monthly_payment_estimate 
      ? `월 약 ${Number(d.monthly_payment_estimate).toLocaleString('ko-KR')}만원 (60개월 할부 기준)`
      : `월 약 ${Math.round((d.target_price || 0) * 0.019)}만원 (60개월 할부 추정)`;

    // 4. 단일 SSOT 사고 상태 정규화 바인딩 (DIRECTIVE 054)
    const acc = d.accident_summary || d.accident_history || {};
    const statusCode = acc.status_code || (acc.is_accident_free === true ? 'VERIFIED_CLEAN' : (acc.is_accident_free === false ? 'VERIFIED_ISSUE' : 'UNKNOWN'));

    let accidentBannerClass, accidentBadgeClass, accidentTitleText, accidentBadgeText;
    if (statusCode === 'VERIFIED_CLEAN') {
      accidentBannerClass = "bg-emerald-50/70 border-emerald-200 text-emerald-900";
      accidentBadgeClass = "bg-emerald-600 text-white";
      accidentTitleText = "완전 무사고 인증 실차";
      accidentBadgeText = escapeHtml(acc.accident_state_label || "완전 무사고 (단순교환 없음)");
    } else if (statusCode === 'VERIFIED_ISSUE') {
      accidentBannerClass = "bg-amber-50/70 border-amber-200 text-amber-900";
      accidentBadgeClass = "bg-amber-600 text-white";
      accidentTitleText = "단순수리 및 교환 이력 확인 매물";
      accidentBadgeText = escapeHtml(acc.accident_state_label || "단순교환 / 수리이력 있음");
    } else {
      accidentBannerClass = "bg-slate-100 border-slate-200 text-slate-700";
      accidentBadgeClass = "bg-slate-600 text-white";
      accidentTitleText = "성능점검 정보 확인 대기 중";
      accidentBadgeText = "미확인 (성능점검표 미등록)";
    }

    // 딜러 및 전시장 정보
    const dealer = d.dealer_info || d.dealer || {};
    const dealerName = dealer.name || '차마트 인증 상담팀';
    const dealerPhone = dealer.phone || '1544-0000';
    const showroomLoc = dealer.showroom_location || '서울특별시 동대문구 천호대로 329';

    // 5. 엔카급 1320px 전체 레이아웃 마크업 렌더링
    this.container.innerHTML = `
      <div class="max-w-[1320px] mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 pb-28 sm:pb-8">
        
        <!-- 상단 관리자 툴바 -->
        ${adminToolbarHtml}

        <!-- 네비게이션 뒤로가기 & 브레드크럼 -->
        <div class="flex items-center justify-between pb-2 border-b border-slate-200">
          <button id="vdrBtnBack" class="inline-flex items-center text-sm font-bold text-slate-600 hover:text-[#247D7C] transition-colors py-1.5 px-3 rounded-lg hover:bg-slate-100 cursor-pointer">
            <i data-lucide="arrow-left" class="w-4 h-4 mr-1.5"></i>
            목록으로 돌아가기
          </button>
          <div class="text-xs text-slate-400">
            차마트 인증 실매물 &gt; <span class="text-slate-600 font-semibold">${escapeHtml(d.manufacturer || '국산')}</span> &gt; ${escapeHtml(d.model_name)}
          </div>
        </div>

        <!-- 핵심 타이틀 & 가격 헤더 (엔카급 대형 가독성) -->
        <div class="bg-white rounded-2xl border border-slate-200/90 shadow-2xs p-6 space-y-3">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div class="flex items-center space-x-2 mb-1">
                <span class="px-2 py-0.5 rounded text-[11px] font-extrabold bg-[#247D7C] text-white">
                  실차인증
                </span>
                <span class="text-xs font-semibold text-slate-400">
                  ${escapeHtml(d.plate_number || '번호판 미기재')} · ${d.year}년식
                </span>
              </div>
              <h1 class="text-2xl sm:text-3xl font-extrabold text-[#0F172A] tracking-tight">
                ${escapeHtml(d.model_name)} ${escapeHtml(d.trim || '')}
              </h1>
            </div>

            <!-- 우측 가격 하이라이트 -->
            <div class="text-left md:text-right shrink-0">
              <div class="text-2xl sm:text-3xl font-black text-rose-600">
                ${targetPriceFormatted}
              </div>
              <span class="text-xs text-slate-500 font-medium">${monthlyEst}</span>
            </div>
          </div>
        </div>

        <!-- 메인 2단 본문 그리드 (좌측 68% : 우측 32%) -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          <!-- [좌측 영역: 갤러리 + 제원 + 성능점검 + 옵션] -->
          <div class="lg:col-span-8 space-y-8">
            
            <!-- 1. 대형 실차 사진 갤러리 (엔카급 뷰어: 16:10 비율) -->
            <div class="bg-white rounded-2xl border border-slate-200/90 overflow-hidden shadow-2xs p-4 sm:p-5 space-y-3">
              <div class="relative aspect-[16/10] bg-slate-900 rounded-xl overflow-hidden flex items-center justify-center group">
                <img id="vdrMainImage" src="${escapeHtml(this.photos[0].url)}" alt="차량 실차 사진" class="w-full h-full object-contain transition-all duration-200" />
                
                <!-- 이전/다음 버튼 -->
                <button id="vdrBtnPrevPhoto" class="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-xs transition-opacity opacity-80 hover:opacity-100 cursor-pointer">
                  <i data-lucide="chevron-left" class="w-6 h-6"></i>
                </button>
                <button id="vdrBtnNextPhoto" class="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-xs transition-opacity opacity-80 hover:opacity-100 cursor-pointer">
                  <i data-lucide="chevron-right" class="w-6 h-6"></i>
                </button>

                <!-- 사진 카운터 & 캡션 바 -->
                <div class="absolute bottom-3 left-3 right-3 flex items-center justify-between text-xs text-white/90 bg-black/60 backdrop-blur-xs px-3.5 py-1.5 rounded-lg">
                  <span id="vdrPhotoCaption" class="truncate font-medium">${escapeHtml(this.photos[0].caption)}</span>
                  <span id="vdrPhotoCounter" class="font-bold shrink-0 ml-2">1 / ${this.photos.length}</span>
                </div>
              </div>

              <!-- 하단 썸네일 스트립 -->
              <div id="vdrThumbnailsContainer" class="flex gap-2.5 overflow-x-auto py-1 custom-scrollbar">
                ${this.photos.map((p, idx) => `
                  <button onclick="window.__vdrInstance.selectPhoto(${idx})" class="w-20 sm:w-24 aspect-[4/3] rounded-lg overflow-hidden shrink-0 border-2 transition-all cursor-pointer ${idx === 0 ? 'border-[#247D7C] shadow-sm scale-102' : 'border-slate-200 opacity-70 hover:opacity-100'}">
                    <img src="${escapeHtml(p.url)}" alt="썸네일 ${idx+1}" class="w-full h-full object-cover" />
                  </button>
                `).join('')}
              </div>
            </div>

            <!-- 2. 핵심 기본 제원표 (엔카식 8대 그리드) -->
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-2xs p-6 space-y-4">
              <div class="flex items-center space-x-2 border-b border-slate-100 pb-3">
                <i data-lucide="car" class="w-5 h-5 text-[#247D7C]"></i>
                <h3 class="text-base font-bold text-[#0F172A]">차량 기본 제원 상세</h3>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs sm:text-sm">
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">차량번호</span>
                  <span class="font-bold text-slate-800">${escapeHtml(d.plate_number || '미기재')}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">차대번호 (VIN)</span>
                  <span class="font-mono font-bold text-slate-800 truncate block" title="${escapeHtml(d.vin || '미확인')}">${escapeHtml(d.vin || '미확인')}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">연식 / 최초등록</span>
                  <span class="font-bold text-slate-800">${d.year}년 / ${escapeHtml(d.first_registration_date || '미확인')}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">주행거리</span>
                  <span class="font-bold text-slate-800">${d.mileage ? Number(d.mileage).toLocaleString('ko-KR') + ' km' : '미확인'}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">배기량</span>
                  <span class="font-bold text-slate-800">${d.displacement_cc ? Number(d.displacement_cc).toLocaleString('ko-KR') + ' cc' : '미확인'}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">변속기 / 구동방식</span>
                  <span class="font-bold text-slate-800">${escapeHtml(d.transmission || '오토')} / ${escapeHtml(d.drive_type || '2WD')}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">연료 / 외장색상</span>
                  <span class="font-bold text-slate-800">${escapeHtml(d.fuel_type || '가솔린')} / ${escapeHtml(d.color || '미확인')}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">차체유형 / 내장색</span>
                  <span class="font-bold text-slate-800">${escapeHtml(d.body_type || '세단')} / ${escapeHtml(d.interior_color || '블랙')}</span>
                </div>
              </div>
            </div>

            <!-- 3. 사고·성능점검 상태표 (단일 SSOT 투명 표기) -->
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-2xs p-6 space-y-4">
              <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                <div class="flex items-center space-x-2">
                  <i data-lucide="clipboard-check" class="w-5 h-5 text-emerald-600"></i>
                  <h3 class="text-base font-bold text-[#0F172A]">사고 및 성능점검 공식 진단표</h3>
                </div>
                <span class="text-xs text-slate-400">점검일: ${escapeHtml(acc.inspection_date || '미확인')}</span>
              </div>

              <!-- 사고 상태 하이라이트 배너 -->
              <div class="p-4 rounded-xl border ${accidentBannerClass} flex items-center justify-between">
                <div class="flex items-center space-x-3">
                  <div class="w-10 h-10 rounded-full ${accidentBadgeClass} flex items-center justify-center shrink-0">
                    <i data-lucide="${statusCode === 'VERIFIED_CLEAN' ? 'check' : 'alert-circle'}" class="w-6 h-6"></i>
                  </div>
                  <div>
                    <div class="font-extrabold text-sm">${accidentTitleText}</div>
                    <div class="text-xs opacity-80 mt-0.5">정부 공인 성능점검 기준 및 공식 전산 검증 기록</div>
                  </div>
                </div>
                <span class="text-xs font-bold px-3 py-1 rounded-full ${accidentBadgeClass}">
                  ${accidentBadgeText}
                </span>
              </div>

              <!-- 4대 상세 진단 그리드 -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm">
                <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                  <span class="text-slate-500">주요 골격(프레임) 손상</span>
                  <span class="font-bold text-slate-800">${escapeHtml(acc.frame_damage || '골격 손상 없음 (정상)')}</span>
                </div>
                <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                  <span class="text-slate-500">외판 부위 교환/판금</span>
                  <span class="font-bold text-slate-800">${escapeHtml(acc.outer_damage || '무교환')}</span>
                </div>
                <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                  <span class="text-slate-500">오일 및 엔진 미세누유</span>
                  <span class="font-bold text-slate-800">${escapeHtml(acc.oil_leak_status || '누유 없음 (정상)')}</span>
                </div>
                <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                  <span class="text-slate-500">침수 / 화재 / 특수이력</span>
                  <span class="font-bold text-slate-800">${escapeHtml(acc.special_accident || '침수/화재/도난 이력 없음')}</span>
                </div>
              </div>
            </div>

            <!-- 4. 카테고리별 주요 옵션 그리드 -->
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-2xs p-6 space-y-4">
              <div class="flex items-center space-x-2 border-b border-slate-100 pb-3">
                <i data-lucide="check-square" class="w-5 h-5 text-[#247D7C]"></i>
                <h3 class="text-base font-bold text-[#0F172A]">장착 주요 옵션 체크리스트</h3>
              </div>
              <div id="vdrOptionsContainer" class="space-y-4">
                ${this.renderOptionsGrid(d)}
              </div>
            </div>

            <!-- 5. 시세 분석 & 부대비용 가이드 -->
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-2xs p-6 space-y-4">
              <div class="flex items-center space-x-2 border-b border-slate-100 pb-3">
                <i data-lucide="trending-down" class="w-5 h-5 text-teal-600"></i>
                <h3 class="text-base font-bold text-[#0F172A]">시세 분석 & 부대비용 가이드</h3>
              </div>
              <div class="space-y-3 text-xs sm:text-sm">
                <p class="text-slate-600 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-100">
                  ${escapeHtml(d.price_comparison?.competition_analysis || '동급 실거래 시세 정밀 비교 분석 중')}
                </p>
                <div class="flex justify-between py-2 border-b border-slate-100 text-slate-600">
                  <span>예상 이전등록세 (취등록세 약 7%)</span>
                  <span class="font-bold text-slate-800">
                    약 ${d.target_price ? Number(Math.round(d.target_price * 0.07)).toLocaleString('ko-KR') : '0'}만원
                  </span>
                </div>
              </div>
            </div>

          </div>

          <!-- [우측 영역: Sticky 가격 및 방문 상담 패널] (32%) -->
          <div class="lg:col-span-4 lg:sticky lg:top-6 space-y-6">
            
            <!-- 구매 및 가격 패널 -->
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-md p-6 space-y-6">
              <div>
                <span class="text-xs font-semibold text-slate-400 block mb-1">차마트 공식 광고 판매가</span>
                <div class="text-3xl sm:text-4xl font-black text-rose-600 tracking-tight">
                  ${targetPriceFormatted}
                </div>
                <div class="text-xs sm:text-sm text-slate-600 font-medium mt-1">
                  ${monthlyEst}
                </div>
              </div>

              <!-- 판매 조건 배지 -->
              <div class="space-y-2 py-3 border-y border-slate-100 text-xs text-slate-600">
                <div class="flex items-center space-x-2">
                  <i data-lucide="check" class="w-4 h-4 text-emerald-600"></i>
                  <span>현금 / 1금융 저금리 할부 / 세금계산서 100% 발행</span>
                </div>
                <div class="flex items-center space-x-2">
                  <i data-lucide="check" class="w-4 h-4 text-emerald-600"></i>
                  <span>장한평 매매단지 실차 전시 및 당일 시승 가능</span>
                </div>
              </div>

              <!-- 전시장 및 전문 딜러 안내 -->
              <div class="bg-slate-50 rounded-xl p-4 border border-slate-100 space-y-2">
                <div class="text-xs font-bold text-slate-800 flex items-center justify-between">
                  <span>전시장 안내</span>
                  <span class="text-[#247D7C]">${escapeHtml(dealerName)}</span>
                </div>
                <div class="text-xs text-slate-600">
                  <div class="flex items-start space-x-1.5 mt-1">
                    <i data-lucide="map-pin" class="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5"></i>
                    <span>${escapeHtml(showroomLoc)}</span>
                  </div>
                  <div class="flex items-center space-x-1.5 mt-1">
                    <i data-lucide="phone" class="w-3.5 h-3.5 text-slate-400 shrink-0"></i>
                    <a href="tel:${escapeHtml(dealerPhone)}" class="text-[#247D7C] font-bold hover:underline">${escapeHtml(dealerPhone)}</a>
                  </div>
                </div>
              </div>

              <!-- 고객 상담 / 방문 예약 간편 폼 -->
              <form id="vdrConsultForm" class="space-y-3.5 pt-2">
                <div class="text-sm font-bold text-slate-800">방문 시승 및 차량 상담 신청</div>
                <div>
                  <input type="text" id="vdrCustName" placeholder="고객 성함" required class="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-[#247D7C]" />
                </div>
                <div>
                  <input type="tel" id="vdrCustPhone" placeholder="연락처 (010-0000-0000)" required class="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-[#247D7C]" />
                </div>
                <div>
                  <input type="date" id="vdrCustDate" class="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg text-slate-600 focus:outline-none focus:border-[#247D7C]" />
                </div>
                <div>
                  <textarea id="vdrCustMemo" rows="2" placeholder="문의 사항 (예: 시승 예약, 대차 상담 등)" class="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-[#247D7C]"></textarea>
                </div>
                <div class="flex items-start space-x-2 text-[11px] text-slate-500">
                  <input type="checkbox" id="vdrPrivacyAgree" required class="mt-0.5 rounded text-[#247D7C] focus:ring-0 cursor-pointer" />
                  <label for="vdrPrivacyAgree" class="cursor-pointer">
                    [필수] 차량 상담 및 방문 예약을 위한 개인정보 수집·이용에 동의합니다.
                  </label>
                </div>
                <button type="submit" id="vdrBtnSubmitConsult" class="w-full py-3 bg-[#247D7C] hover:bg-[#1D6665] text-white font-extrabold text-sm rounded-xl shadow-xs transition-colors flex items-center justify-center cursor-pointer">
                  <i data-lucide="calendar" class="w-4 h-4 mr-1.5"></i>
                  방문 예약 및 상담 신청하기
                </button>
              </form>
            </div>

          </div>
        </div>

      </div>

      <!-- 모바일 하단 고정 전화/상담 CTA 바 (390x844 최적화) -->
      <div class="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200 p-3 sm:hidden shadow-lg">
        <div class="flex items-center space-x-2 max-w-md mx-auto">
          <a href="tel:${escapeHtml(dealerPhone)}" class="flex-1 py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl flex items-center justify-center border border-slate-200">
            <i data-lucide="phone" class="w-4 h-4 mr-1.5 text-blue-600"></i>
            전화 상담
          </a>
          <button onclick="document.getElementById('vdrConsultForm')?.scrollIntoView({ behavior: 'smooth' })" class="flex-1 py-2.5 px-3 bg-[#247D7C] hover:bg-[#1D6665] text-white font-bold text-xs rounded-xl flex items-center justify-center shadow-xs">
            <i data-lucide="calendar" class="w-4 h-4 mr-1.5"></i>
            방문 예약
          </button>
        </div>
      </div>
    `;

    // 6. 이벤트 바인딩
    this.bindEvents();
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  renderOptionsGrid(d) {
    const categorized = d.options_categorized || {};
    if (Object.keys(categorized).length > 0) {
      let html = '';
      for (const [catName, list] of Object.entries(categorized)) {
        if (list && list.length > 0) {
          const badges = list.map(o => `
            <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
              <i data-lucide="check" class="w-3 h-3 mr-1 text-[#247D7C]"></i>
              ${escapeHtml(o.name || o)}
            </span>
          `).join(' ');
          html += `
            <div class="space-y-1.5">
              <div class="text-xs font-bold text-slate-500">${escapeHtml(catName)}</div>
              <div class="flex flex-wrap gap-1.5">${badges}</div>
            </div>
          `;
        }
      }
      return html || '<div class="text-xs text-slate-400">장착 옵션 사양을 정리 중입니다.</div>';
    } else if (d.options && d.options.length > 0) {
      const badges = d.options.map(o => `
        <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">
          <i data-lucide="check" class="w-3 h-3 mr-1 text-[#247D7C]"></i>
          ${escapeHtml(o)}
        </span>
      `).join(' ');
      return `<div class="flex flex-wrap gap-1.5">${badges}</div>`;
    }
    return '<div class="text-xs text-slate-400">확인된 주요 옵션 사양을 정리 중입니다.</div>';
  }

  selectPhoto(index) {
    if (!this.photos || index < 0 || index >= this.photos.length) return;
    this.currentPhotoIdx = index;
    const photo = this.photos[this.currentPhotoIdx];
    
    const mainImg = document.getElementById('vdrMainImage');
    if (mainImg) mainImg.src = photo.url;

    const capEl = document.getElementById('vdrPhotoCaption');
    if (capEl) capEl.textContent = photo.caption;

    const countEl = document.getElementById('vdrPhotoCounter');
    if (countEl) countEl.textContent = `${this.currentPhotoIdx + 1} / ${this.photos.length}`;

    // 썸네일 액티브 상태 갱신
    const container = document.getElementById('vdrThumbnailsContainer');
    if (container) {
      const btns = container.querySelectorAll('button');
      btns.forEach((btn, idx) => {
        if (idx === this.currentPhotoIdx) {
          btn.className = "w-20 sm:w-24 aspect-[4/3] rounded-lg overflow-hidden shrink-0 border-2 transition-all border-[#247D7C] shadow-sm scale-102 cursor-pointer";
        } else {
          btn.className = "w-20 sm:w-24 aspect-[4/3] rounded-lg overflow-hidden shrink-0 border-2 transition-all border-slate-200 opacity-70 hover:opacity-100 cursor-pointer";
        }
      });
    }
  }

  navigatePhoto(direction) {
    if (!this.photos || this.photos.length <= 1) return;
    const nextIdx = (this.currentPhotoIdx + direction + this.photos.length) % this.photos.length;
    this.selectPhoto(nextIdx);
  }

  bindEvents() {
    window.__vdrInstance = this;

    // 뒤로가기
    const btnBack = document.getElementById('vdrBtnBack');
    if (btnBack && this.options.onBack) {
      btnBack.onclick = () => this.options.onBack();
    }

    // 사진 이전/다음
    const btnPrev = document.getElementById('vdrBtnPrevPhoto');
    const btnNext = document.getElementById('vdrBtnNextPhoto');
    if (btnPrev) btnPrev.onclick = () => this.navigatePhoto(-1);
    if (btnNext) btnNext.onclick = () => this.navigatePhoto(1);

    // 관리자 액션 (콜백 인자 계약 일치화: id, is_public, data)
    const btnPub = document.getElementById('vdrBtnTogglePublish');
    if (btnPub && this.options.onTogglePublish) {
      btnPub.onclick = () => this.options.onTogglePublish(this.data.id, Boolean(this.data.is_public), this.data);
    }
    const btnEdit = document.getElementById('vdrBtnEditMaster');
    if (btnEdit && this.options.onEditMaster) {
      btnEdit.onclick = () => this.options.onEditMaster(this.data.id, this.data);
    }

    // 상담 신청 폼
    const form = document.getElementById('vdrConsultForm');
    if (form) {
      form.onsubmit = async (e) => {
        e.preventDefault();
        const name = document.getElementById('vdrCustName')?.value.trim();
        const phone = document.getElementById('vdrCustPhone')?.value.trim();
        const date = document.getElementById('vdrCustDate')?.value;
        const memo = document.getElementById('vdrCustMemo')?.value.trim();
        const privacy = document.getElementById('vdrPrivacyAgree')?.checked;

        if (!privacy) {
          alert('개인정보 수집 및 이용에 동의해야 상담 신청이 가능합니다.');
          return;
        }
        if (!name || !phone) {
          alert('고객 성함과 연락처를 입력해 주세요.');
          return;
        }

        const payload = {
          name,
          phone,
          vehicle_id: this.data.id,
          vehicle_title: this.data.model_name,
          preferred_date: date,
          content: memo || '차마트 차량 상세페이지 방문 예약 상담',
          privacy_agreed: Boolean(privacy)
        };

        if (typeof this.options.onSubmitConsultation === 'function') {
          await this.options.onSubmitConsultation(payload);
        } else {
          // 기본 폴백 API 전송
          try {
            const res = await fetch('/api/chamart/consultations', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload)
            });
            const ret = await res.json();
            if (res.ok) {
              alert(ret.message || '상담 예약이 정상 접수되었습니다.');
              form.reset();
            } else {
              alert(ret.detail || '상담 신청 중 오류가 발생했습니다.');
            }
          } catch (err) {
            alert('상담 신청 서버 통신에 실패했습니다.');
          }
        }
      };
    }
  }
}

window.VehicleDetailRenderer = VehicleDetailRenderer;
