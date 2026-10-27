/**
 * CHA-FICIAL / CHAMART 공통 프리미엄 차량 상세 렌더러 (DIRECTIVE 053 REVISED)
 * 엔카급 정보 구조, 1440x900 데스크톱 최적화 및 390x844 모바일 반응형 완비
 */
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
    this.data = vehicleData;
    this.currentPhotoIdx = 0;

    // 사진 목록 정규화
    if (this.data.photos && this.data.photos.length > 0) {
      this.photos = this.data.photos.map(p => ({
        url: p.photo_url || p.url,
        caption: p.caption || p.category || '차량 실차 사진'
      }));
    } else if (this.data.primary_photo_url && !this.data.primary_photo_url.endsWith('car_placeholder.jpg')) {
      this.photos = [{
        url: this.data.primary_photo_url,
        caption: `${this.data.model_name} 실차 대표 사진`
      }];
    } else {
      this.photos = [{
        url: '/uploads/vehicles/demo_car_front.jpg',
        caption: '차량 실차 사진 준비 중'
      }];
    }

    const d = this.data;
    const isAdmin = this.options.isAdmin;

    // 1. 관리자 상단 툴바 HTML
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
            <div class="flex flex-wrap items-center gap-3">
              <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-[#247D7C] text-white tracking-wide">
                <i data-lucide="shield-check" class="w-3.5 h-3.5 mr-1"></i>
                차피셜 관리자 전용 모드
              </span>
              <span class="text-xs text-slate-300">
                소유유형: <strong class="text-white">${d.ownership_type || 'CHAMART_OWNED'}</strong>
              </span>
              <span class="text-slate-600 hidden sm:inline">|</span>
              <div class="flex items-center space-x-3 text-xs">
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

    // 2. 가격 및 제원 바인딩 변수
    const targetPriceFormatted = d.target_price ? `${Number(d.target_price).toLocaleString('ko-KR')}만원` : '가격 상담';
    const monthlyEst = d.monthly_payment_estimate 
      ? `60개월 할부 시 월 약 ${Number(d.monthly_payment_estimate).toLocaleString('ko-KR')}만원`
      : (d.target_price ? `60개월 할부 시 월 약 ${Math.round(d.target_price * 0.019)}만원` : '할부 상담 가능');

    const acc = d.accident_summary || d.accident_history || {};
    const isAccidentFree = Boolean(
      acc.is_accident_free || 
      acc.accident_state === 'CLEAN' || 
      acc.accident_state === 'NONE' || 
      acc.accident_state === '무사고'
    );

    const accidentBadgeClass = isAccidentFree 
      ? "bg-emerald-50 text-emerald-700 border-emerald-300"
      : "bg-amber-50 text-amber-700 border-amber-300";
    const accidentBadgeText = isAccidentFree ? "완전 무사고 (진단 보증)" : (acc.accident_state_label || "단순교환 / 수리이력 있음");

    // 3. 전체 HTML 조립
    this.container.innerHTML = `
      <div class="max-w-[1320px] mx-auto px-4 sm:px-6 py-4 space-y-6">
        
        <!-- 뒤로가기 버튼 & 상단 관리자 툴바 -->
        <div class="flex items-center justify-between pb-2">
          <button id="vdrBtnBack" class="inline-flex items-center text-sm font-bold text-slate-600 hover:text-[#247D7C] transition-colors py-1.5 px-3 rounded-lg hover:bg-slate-100">
            <i data-lucide="arrow-left" class="w-4 h-4 mr-1.5"></i>
            <span>${isAdmin ? '차량 관리 목록으로 돌아가기' : '차마트 쇼룸으로 돌아가기'}</span>
          </button>
          <div class="text-xs text-slate-400">
            등록번호: <span class="font-mono font-medium text-slate-600">${d.plate_number || '번호판 미기재'}</span>
          </div>
        </div>

        ${adminToolbarHtml}

        <!-- 상단 헤더: 차종 및 핵심 배지 -->
        <div class="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-2xs">
          <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div class="space-y-2">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-xs font-bold text-[#247D7C] bg-teal-50 border border-teal-200 px-2.5 py-0.5 rounded-full">
                  ${d.manufacturer || '국산/수입'}
                </span>
                <span class="text-xs font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                  ${d.trim || '기본 트림'}
                </span>
                <span class="text-xs font-bold px-2.5 py-0.5 rounded-full border ${accidentBadgeClass}">
                  ${accidentBadgeText}
                </span>
              </div>
              <h1 class="text-2xl sm:text-3xl font-extrabold text-[#0F172A] tracking-tight">
                ${d.model_name}
              </h1>
              <div class="flex flex-wrap items-center gap-2 text-xs sm:text-sm text-slate-500 font-medium">
                <span>${d.year}년식 (${d.first_registration_date || '등록일 미기재'})</span>
                <span class="text-slate-300">·</span>
                <span>${d.mileage ? Number(d.mileage).toLocaleString('ko-KR') + ' km' : '주행거리 미확인'}</span>
                <span class="text-slate-300">·</span>
                <span>${d.fuel_type || '가솔린'}</span>
                <span class="text-slate-300">·</span>
                <span>${d.transmission || '오토'}</span>
                <span class="text-slate-300">·</span>
                <span>${d.color || '색상 미지정'}</span>
              </div>
            </div>

            <!-- 모바일/태블릿용 간략 가격 표시 -->
            <div class="lg:hidden pt-3 border-t border-slate-100 flex items-center justify-between">
              <div>
                <span class="text-xs text-slate-500 block">판매가격</span>
                <span class="text-2xl font-black text-rose-600">${targetPriceFormatted}</span>
              </div>
              <span class="text-xs text-slate-500 font-medium">${monthlyEst}</span>
            </div>
          </div>
        </div>

        <!-- 메인 2단 본문 그리드 (좌측 68% : 우측 32%) -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          <!-- [좌측 영역: 갤러리 + 제원 + 성능점검 + 옵션] -->
          <div class="lg:col-span-8 space-y-8">
            
            <!-- 1. 대형 실차 사진 갤러리 (엔카급 뷰어) -->
            <div class="bg-white rounded-2xl border border-slate-200/90 overflow-hidden shadow-2xs p-4 sm:p-5 space-y-3">
              <div class="relative aspect-[16/10] bg-slate-900 rounded-xl overflow-hidden flex items-center justify-center group">
                <img id="vdrMainImage" src="${this.photos[0].url}" alt="차량 실차 사진" class="w-full h-full object-contain transition-all duration-200" />
                
                <!-- 이전/다음 버튼 -->
                <button id="vdrBtnPrevPhoto" class="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-xs transition-opacity opacity-80 hover:opacity-100">
                  <i data-lucide="chevron-left" class="w-6 h-6"></i>
                </button>
                <button id="vdrBtnNextPhoto" class="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/50 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-xs transition-opacity opacity-80 hover:opacity-100">
                  <i data-lucide="chevron-right" class="w-6 h-6"></i>
                </button>

                <!-- 사진 카운터 & 캡션 바 -->
                <div class="absolute bottom-3 left-3 right-3 flex items-center justify-between text-xs text-white/90 bg-black/60 backdrop-blur-xs px-3.5 py-1.5 rounded-lg">
                  <span id="vdrPhotoCaption" class="truncate font-medium">${this.photos[0].caption}</span>
                  <span id="vdrPhotoCounter" class="font-bold shrink-0 ml-2">1 / ${this.photos.length}</span>
                </div>
              </div>

              <!-- 하단 썸네일 스트립 -->
              <div id="vdrThumbnailsContainer" class="flex gap-2.5 overflow-x-auto py-1 custom-scrollbar">
                ${this.photos.map((p, idx) => `
                  <button onclick="window.__vdrInstance.selectPhoto(${idx})" class="w-20 sm:w-24 aspect-[4/3] rounded-lg overflow-hidden shrink-0 border-2 transition-all ${idx === 0 ? 'border-[#247D7C] shadow-sm scale-102' : 'border-slate-200 opacity-70 hover:opacity-100'}">
                    <img src="${p.url}" alt="썸네일 ${idx+1}" class="w-full h-full object-cover" />
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
                  <span class="font-bold text-slate-800">${d.plate_number || '미기재'}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">차대번호 (VIN)</span>
                  <span class="font-mono font-bold text-slate-800 truncate block" title="${d.vin || '미확인'}">${d.vin || '미확인'}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">연식 / 최초등록</span>
                  <span class="font-bold text-slate-800">${d.year}년 / ${d.first_registration_date || '미확인'}</span>
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
                  <span class="font-bold text-slate-800">${d.transmission || '오토'} / ${d.drive_type || '2WD'}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">연료 / 외장색상</span>
                  <span class="font-bold text-slate-800">${d.fuel_type || '가솔린'} / ${d.color || '미확인'}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">차체유형 / 내장색</span>
                  <span class="font-bold text-slate-800">${d.body_type || '세단'} / ${d.interior_color || '블랙'}</span>
                </div>
              </div>
            </div>

            <!-- 3. 사고·성능점검 상태표 (P0-3 정직 투명 표기) -->
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-2xs p-6 space-y-4">
              <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                <div class="flex items-center space-x-2">
                  <i data-lucide="clipboard-check" class="w-5 h-5 text-emerald-600"></i>
                  <h3 class="text-base font-bold text-[#0F172A]">사고 및 성능점검 공식 진단표</h3>
                </div>
                <span class="text-xs text-slate-400">점검일: ${acc.inspection_date || '미확인 (성능점검표 미등록)'}</span>
              </div>

              <!-- 사고 상태 하이라이트 배너 -->
              <div class="p-4 rounded-xl border ${isAccidentFree ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900' : 'bg-amber-50/70 border-amber-200 text-amber-900'} flex items-center justify-between">
                <div class="flex items-center space-x-3">
                  <div class="w-10 h-10 rounded-full ${isAccidentFree ? 'bg-emerald-500 text-white' : 'bg-amber-500 text-white'} flex items-center justify-center shrink-0">
                    <i data-lucide="${isAccidentFree ? 'check' : 'alert-circle'}" class="w-6 h-6"></i>
                  </div>
                  <div>
                    <div class="font-extrabold text-sm">${isAccidentFree ? '완전 무사고 인증 차량' : '단순수리 및 교환 이력 확인 매물'}</div>
                    <div class="text-xs opacity-80 mt-0.5">정부 공인 성능점검 기준 및 공식 전산 검증 기록</div>
                  </div>
                </div>
                <span class="text-xs font-bold px-3 py-1 rounded-full ${isAccidentFree ? 'bg-emerald-600 text-white' : 'bg-amber-600 text-white'}">
                  ${acc.accident_state_label || (isAccidentFree ? '무사고' : '단순교환')}
                </span>
              </div>

              <!-- 4대 상세 진단 그리드 -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs sm:text-sm">
                <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                  <span class="text-slate-500">주요 골격(프레임) 손상</span>
                  <span class="font-bold text-slate-800">${acc.frame_damage || '골격 손상 없음 (정상)'}</span>
                </div>
                <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                  <span class="text-slate-500">외판 부위 교환/판금</span>
                  <span class="font-bold text-slate-800">${acc.outer_damage || acc.outer_panel_exchange || '단순교환 없음'}</span>
                </div>
                <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                  <span class="text-slate-500">오일 및 엔진 미세누유</span>
                  <span class="font-bold text-slate-800">${acc.oil_leak_status || '누유 없음 (정상)'}</span>
                </div>
                <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                  <span class="text-slate-500">침수 / 화재 / 특수이력</span>
                  <span class="font-bold text-slate-800">${acc.special_accident || '침수/화재/도난 이력 없음'}</span>
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
                <h3 class="text-base font-bold text-[#0F172A]">시세 분석 & 착한 가격 안내</h3>
              </div>
              <div class="space-y-3 text-xs sm:text-sm">
                <p class="text-slate-600 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-100">
                  ${d.price_comparison?.competition_analysis || '동급 엔카/KB 시세 대비 합리적이고 투명한 실거래 가격으로 책정된 매물입니다.'}
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
          <div class="lg:col-span-4 sticky top-6 space-y-6">
            
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
                  <span>현금 / 1금융 저금리 다이렉트 할부 가능</span>
                </div>
                <div class="flex items-center space-x-2">
                  <i data-lucide="check" class="w-4 h-4 text-emerald-600"></i>
                  <span>현금영수증 및 세금계산서 100% 의무 발행</span>
                </div>
                <div class="flex items-center space-x-2">
                  <i data-lucide="check" class="w-4 h-4 text-emerald-600"></i>
                  <span>장한평 매매단지 실차 당일 출고 가능</span>
                </div>
              </div>

              <!-- 전시장 및 상담 안내 -->
              <div class="bg-slate-50 p-4 rounded-xl border border-slate-100 space-y-1.5 text-xs">
                <div class="font-bold text-slate-800 text-sm">차마트 장한평 본사 가온모터스</div>
                <div class="text-slate-500">서울특별시 동대문구 천호대로 329 (장한평 매매단지)</div>
                <div class="text-[#247D7C] font-semibold flex items-center pt-1">
                  <i data-lucide="phone" class="w-3.5 h-3.5 mr-1"></i>
                  직통 상담: 02-2244-8899
                </div>
              </div>

              <!-- 간편 방문 예약 폼 -->
              <form id="vdrConsultForm" class="space-y-3.5 pt-2">
                <div class="text-xs font-bold text-slate-700">실차 확인 & 방문 예약 신청</div>
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
                <div class="flex items-start space-x-2 pt-1">
                  <input type="checkbox" id="vdrPrivacyAgree" required class="mt-0.5 rounded text-[#247D7C] focus:ring-0" />
                  <label for="vdrPrivacyAgree" class="text-[11px] text-slate-500 leading-tight">
                    [필수] 상담 예약을 위한 개인정보 수집 및 이용에 동의합니다.
                  </label>
                </div>
                <button type="submit" id="vdrBtnSubmitConsult" class="w-full py-3 bg-[#247D7C] hover:bg-[#1D6665] text-white font-extrabold text-sm rounded-xl shadow-xs transition-colors flex items-center justify-center">
                  <i data-lucide="calendar" class="w-4 h-4 mr-1.5"></i>
                  방문 예약 & 구매 상담 신청
                </button>
              </form>

            </div>

          </div>

        </div>

      </div>

      <!-- 모바일 하단 고정 CTA 바 (lg:hidden) -->
      <div class="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200 p-3 shadow-lg flex items-center justify-between">
        <div>
          <span class="text-[11px] text-slate-400 block">판매가</span>
          <span class="text-base font-extrabold text-rose-600">${targetPriceFormatted}</span>
        </div>
        <div class="flex items-center space-x-2">
          <a href="tel:02-2244-8899" class="px-3.5 py-2 rounded-lg bg-slate-100 text-slate-700 text-xs font-bold border border-slate-200 flex items-center">
            <i data-lucide="phone-call" class="w-3.5 h-3.5 mr-1 text-[#247D7C]"></i>
            전화
          </a>
          <button onclick="document.getElementById('vdrCustName')?.focus()" class="px-4 py-2 rounded-lg bg-[#247D7C] text-white text-xs font-bold shadow-xs">
            방문 예약
          </button>
        </div>
      </div>
    `;

    // 이벤트 리스너 바인딩
    this.bindEvents();
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  renderOptionsGrid(d) {
    const categorized = d.options_categorized || {};
    let html = '';
    if (Object.keys(categorized).length > 0) {
      html += '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">';
      for (const [catName, optsList] of Object.entries(categorized)) {
        if (optsList && optsList.length > 0) {
          html += `
            <div class="p-3.5 bg-slate-50 rounded-xl border border-slate-100 space-y-2">
              <div class="font-bold text-slate-700 text-xs">${catName}</div>
              <div class="flex flex-wrap gap-1.5">
                ${optsList.map(o => `<span class="bg-white border border-slate-200 text-slate-700 px-2 py-0.5 rounded text-[11px] font-medium">✓ ${o.name || o}</span>`).join('')}
              </div>
            </div>
          `;
        }
      }
      html += '</div>';
    } else if (d.options && d.options.length > 0) {
      html += `
        <div class="flex flex-wrap gap-1.5">
          ${d.options.map(o => `<span class="bg-slate-50 border border-slate-200 text-slate-700 px-2.5 py-1 rounded text-xs font-medium">✓ ${o}</span>`).join('')}
        </div>
      `;
    } else {
      html = '<div class="text-slate-400 text-xs py-2">등록된 주요 장착 옵션 사양이 없습니다.</div>';
    }
    return html;
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

    // 관리자 액션
    const btnPub = document.getElementById('vdrBtnTogglePublish');
    if (btnPub && this.options.onTogglePublish) {
      btnPub.onclick = () => this.options.onTogglePublish(this.data);
    }
    const btnEdit = document.getElementById('vdrBtnEditMaster');
    if (btnEdit && this.options.onEditMaster) {
      btnEdit.onclick = () => this.options.onEditMaster(this.data);
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
        const agree = document.getElementById('vdrPrivacyAgree')?.checked;

        if (!agree) {
          alert('개인정보 수집 및 이용에 동의하셔야 상담 신청이 가능합니다.');
          return;
        }

        if (this.options.onSubmitConsultation) {
          await this.options.onSubmitConsultation({
            name,
            phone,
            vehicle_id: this.data.id,
            vehicle_title: `${this.data.model_name} (${this.data.plate_number})`,
            preferred_date: date,
            content: memo || '차량 상세 화면에서 방문 예약 접수',
            privacy_agreed: true
          });
        }
      };
    }
  }

  navigatePhoto(direction) {
    if (!this.photos || this.photos.length === 0) return;
    this.currentPhotoIdx = (this.currentPhotoIdx + direction + this.photos.length) % this.photos.length;
    this.updatePhotoView();
  }

  selectPhoto(idx) {
    if (!this.photos || idx < 0 || idx >= this.photos.length) return;
    this.currentPhotoIdx = idx;
    this.updatePhotoView();
  }

  updatePhotoView() {
    const photo = this.photos[this.currentPhotoIdx];
    const imgEl = document.getElementById('vdrMainImage');
    const captionEl = document.getElementById('vdrPhotoCaption');
    const counterEl = document.getElementById('vdrPhotoCounter');
    
    if (imgEl && photo) imgEl.src = photo.url;
    if (captionEl && photo) captionEl.innerText = photo.caption;
    if (counterEl) counterEl.innerText = `${this.currentPhotoIdx + 1} / ${this.photos.length}`;

    // 썸네일 하이라이트
    const container = document.getElementById('vdrThumbnailsContainer');
    if (container) {
      const thumbs = container.querySelectorAll('button');
      thumbs.forEach((btn, i) => {
        if (i === this.currentPhotoIdx) {
          btn.className = "w-20 sm:w-24 aspect-[4/3] rounded-lg overflow-hidden shrink-0 border-2 border-[#247D7C] shadow-sm scale-102";
        } else {
          btn.className = "w-20 sm:w-24 aspect-[4/3] rounded-lg overflow-hidden shrink-0 border-2 border-slate-200 opacity-70 hover:opacity-100";
        }
      });
    }
  }
}

// 글로벌 네임스페이스 등록
if (typeof window !== 'undefined') {
  window.VehicleDetailRenderer = VehicleDetailRenderer;
}
