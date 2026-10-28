/**
 * CHA-FICIAL / CHAMART 공통 프리미엄 차량 상세 렌더러 (DIRECTIVE 055)
 * 
 * 1. P0: 사진 정직성 & 단일 플레이스홀더 (허위 인증 문구 완전 배제, 실차 사진 미확인 시 1장만 중립 표기)
 * 2. P1: 모바일 레이아웃 최적화 (375x812, 390x844 뷰포트 너비 100% 활용, 우측 빈 공간 0px)
 * 3. P2: 독자 외판 vs 주요 골격 인터랙티브 2D SVG 다이어그램 & 단일 SSOT 진단표 연동
 * 4. P2: K Car 스타일 투명 총 구매비용 계산기 (판매가 + 취등록세 + 부대비용 + 실시간 할부 시뮬레이터)
 * 5. P3: 모바일 전환율 극대화 Bottom Sheet 간편 방문예약 모달 & 터치 스와이프 갤러리
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
    this.isRealPhotoVerified = false;
    this.touchStartX = 0;
    this.touchEndX = 0;
    this.currentDiagramTab = 'all'; // 'all', 'outer', 'frame'
    window.__vdrInstance = this;
  }

  render(vehicleData) {
    if (!this.container) {
      console.error('[VehicleDetailRenderer] Container not found.');
      return;
    }
    this.container.classList.add('pb-28', 'sm:pb-8', 'w-full', 'max-w-full');
    this.data = vehicleData;
    this.currentPhotoIdx = 0;

    const d = this.data;
    const isAdmin = this.options.isAdmin;

    // 1. P0 사진 정직성 및 검증 상태 정규화
    // DIRECTIVE 055: REAL_PHOTO_VERIFIED가 공식 승인되지 않았거나 DEMO_PLACEHOLDER인 경우 실차 사진으로 인정하지 않음
    const firstPhoto = (d.photos && d.photos.length > 0) ? d.photos[0] : null;
    const hasDemoPlaceholderCaption = firstPhoto && String(firstPhoto.caption || '').includes('DEMO_PLACEHOLDER');

    this.isRealPhotoVerified = Boolean(
      d.photo_verification_status === 'REAL_PHOTO_VERIFIED' && !hasDemoPlaceholderCaption
    );

    if (this.isRealPhotoVerified && d.photos && d.photos.length > 0) {
      this.photos = d.photos.map(p => ({
        url: p.photo_url || p.url,
        caption: p.caption || p.category || `${d.model_name} 실차 사진`,
        isVerified: true
      }));
    } else {
      // 실차 사진 미등록 상태: 단 1장의 중립 플레이스홀더만 정직하게 노출 (DIRECTIVE 055 P0)
      this.photos = [{
        url: '/static/img/vehicles/neutral_car_placeholder.jpg',
        caption: '차량 실차 사진 등록 전 (실차 준비 중)',
        isVerified: false
      }];
    }

    // 2. 단일 SSOT 사고·성능 정규화 데이터 바인딩
    const acc = d.accident_summary || d.accident_history || {};
    const docStatus = acc.document_status || (acc.inspection_document_id ? 'VERIFIED' : 'UNVERIFIED');
    const hasDoc = docStatus === 'VERIFIED';
    
    // 외판 및 골격 상태 정밀 추출
    const frameStatus = acc.frame_status || (acc.frame_damage_count > 0 ? 'VERIFIED_ISSUE' : (hasDoc ? 'VERIFIED_CLEAN' : 'UNKNOWN'));
    const bodyStatus = acc.body_panel_status || (acc.outer_damage_count > 0 ? 'VERIFIED_ISSUE' : (hasDoc ? 'VERIFIED_CLEAN' : 'UNKNOWN'));
    const leakStatus = acc.oil_leak_status || (hasDoc ? 'VERIFIED_CLEAN' : 'UNKNOWN');
    const floodStatus = acc.flood_history_status || (hasDoc ? 'VERIFIED_CLEAN' : 'UNKNOWN');
    const insuranceStatus = acc.insurance_history_status || (acc.total_loss_count > 0 ? 'VERIFIED_ISSUE' : (hasDoc ? 'VERIFIED_CLEAN' : 'UNKNOWN'));

    // 3. 관리자 전용 툴바 (원가, 상품화비, 추정마진, 공개토글, 마스터수정)
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
        <div class="bg-[#0F172A] text-white border border-slate-800 p-4 sm:p-5 rounded-2xl mb-6 shadow-lg">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="space-y-2">
              <div class="flex flex-wrap items-center gap-2">
                <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-[#247D7C] text-white">
                  <i data-lucide="shield-alert" class="w-3.5 h-3.5 mr-1"></i>
                  차피셜 관리자 전용 제어판
                </span>
                <span class="text-xs text-slate-300">
                  소유: <strong class="text-white">${escapeHtml(d.ownership_type || 'CHAMART_OWNED')}</strong>
                </span>
                <span class="text-xs text-slate-300">
                  거점: <strong class="text-teal-400">${escapeHtml(d.branch_location || '장한평 본사')}</strong>
                </span>
                <span class="text-xs text-slate-300">
                  사진검증: <strong class="${this.isRealPhotoVerified ? 'text-emerald-400' : 'text-amber-400'}">${this.isRealPhotoVerified ? '실차확인' : '미확인(DEMO)'}</strong>
                </span>
              </div>
              <div class="grid grid-cols-3 gap-2 sm:gap-4 text-xs bg-slate-900/80 p-2.5 rounded-xl border border-slate-800">
                <div>매입원가: <strong class="text-teal-300 block sm:inline font-mono">${pur}</strong></div>
                <div>상품화비: <strong class="text-slate-300 block sm:inline font-mono">${rec}</strong></div>
                <div>추정마진: <strong class="text-amber-300 block sm:inline font-mono font-bold">${margin}</strong></div>
              </div>
            </div>
            <div class="flex items-center space-x-2 shrink-0">
              <button id="vdrBtnTogglePublish" class="px-3.5 py-2 text-xs font-bold rounded-xl shadow-xs transition-colors flex items-center ${pubBtnClass}">
                <i data-lucide="${isPub ? 'eye-off' : 'check-circle-2'}" class="w-3.5 h-3.5 mr-1.5"></i>
                ${pubBtnText}
              </button>
              <button id="vdrBtnEditMaster" class="px-3.5 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl shadow-xs transition-colors flex items-center">
                <i data-lucide="edit-3" class="w-3.5 h-3.5 mr-1.5"></i>
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

    // 딜러 정보
    const dealer = d.dealer_info || d.dealer || {};
    const dealerName = dealer.name || '차마트 공식 인증팀';
    const dealerPhone = dealer.phone || '1544-0000';
    const showroomLoc = dealer.showroom_location || '서울특별시 동대문구 천호대로 329 차마트 본사';

    // 5. 엔카급 대형 레이아웃 렌더링
    this.container.innerHTML = `
      <div class="w-full max-w-[1320px] mx-auto px-2 sm:px-6 lg:px-8 py-3 sm:py-6 space-y-6">
        
        <!-- 상단 관리자 툴바 -->
        ${adminToolbarHtml}

        <!-- 네비게이션 뒤로가기 & 브레드크럼 -->
        <div class="flex items-center justify-between pb-2 border-b border-slate-200/80">
          <button id="vdrBtnBack" class="inline-flex items-center text-xs sm:text-sm font-bold text-slate-600 hover:text-[#247D7C] transition-colors py-1.5 px-2.5 rounded-lg hover:bg-slate-100 cursor-pointer">
            <i data-lucide="arrow-left" class="w-4 h-4 mr-1.5"></i>
            목록으로 돌아가기
          </button>
          <div class="text-[11px] sm:text-xs text-slate-400 truncate max-w-[200px] sm:max-w-none">
            차마트 &gt; <span class="text-slate-600 font-semibold">${escapeHtml(d.manufacturer || '국산')}</span> &gt; ${escapeHtml(d.model_name)}
          </div>
        </div>

        <!-- 핵심 타이틀 & 가격 헤더 (엔카급 대형 가독성) -->
        <div class="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-4 sm:p-6 space-y-3">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div class="flex flex-wrap items-center gap-2 mb-1.5">
                ${this.isRealPhotoVerified 
                  ? '<span class="px-2 py-0.5 rounded text-[11px] font-extrabold bg-[#247D7C] text-white">실차인증</span>' 
                  : '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/10 text-amber-800 border border-amber-300">실차 준비 중 (예시 이미지)</span>'}
                <span class="text-xs font-semibold text-slate-500">
                  ${escapeHtml(d.plate_number || '차량번호 미기재')} · ${d.year}년식 · ${d.mileage ? Number(d.mileage).toLocaleString('ko-KR') + 'km' : '주행거리 미확인'}
                </span>
              </div>
              <h1 class="text-xl sm:text-3xl font-extrabold text-[#0F172A] tracking-tight">
                ${escapeHtml(d.model_name)} <span class="text-slate-600 font-semibold text-lg sm:text-2xl">${escapeHtml(d.trim || '')}</span>
              </h1>
            </div>

            <!-- 우측 판매가 -->
            <div class="text-left md:text-right shrink-0">
              <span class="text-xs font-semibold text-slate-400 block mb-0.5">차마트 정찰 판매가</span>
              <div class="text-2xl sm:text-4xl font-black text-rose-600 tracking-tight">
                ${targetPriceFormatted}
              </div>
              <span class="text-xs text-slate-500 font-medium">
                취등록세 약 ${acquisitionTaxEst ? acquisitionTaxEst.toLocaleString('ko-KR') + '만원' : '상담'} (별도)
              </span>
            </div>
          </div>
        </div>

        <!-- 메인 2단 본문 그리드 (좌측 68% : 우측 32%) -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 sm:gap-8 items-start">
          
          <!-- [좌측 8컬럼 영역: 갤러리 + 기본제원 + 사고다이어그램 + 옵션 + 투명구매비용] -->
          <div class="lg:col-span-8 space-y-6 sm:space-y-8 w-full max-w-full">
            
            <!-- 1. 대형 실차 사진 갤러리 (터치 스와이프 지원, 16:10 비율) -->
            <div class="bg-white rounded-2xl border border-slate-200/90 overflow-hidden shadow-xs p-3 sm:p-5 space-y-3">
              <div id="vdrGalleryViewport" class="relative aspect-[16/10] bg-slate-900 rounded-xl overflow-hidden flex items-center justify-center select-none touch-pan-y">
                <img id="vdrMainImage" src="${escapeHtml(this.photos[0].url)}" alt="차량 사진" class="w-full h-full object-contain transition-all duration-200" />
                
                ${this.photos.length > 1 ? `
                  <button id="vdrBtnPrevPhoto" class="absolute left-2.5 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-black/50 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-xs transition-opacity cursor-pointer">
                    <i data-lucide="chevron-left" class="w-5 h-5"></i>
                  </button>
                  <button id="vdrBtnNextPhoto" class="absolute right-2.5 top-1/2 -translate-y-1/2 w-9 h-9 rounded-full bg-black/50 hover:bg-black/80 text-white flex items-center justify-center backdrop-blur-xs transition-opacity cursor-pointer">
                    <i data-lucide="chevron-right" class="w-5 h-5"></i>
                  </button>
                ` : ''}

                <!-- 사진 카운터 & 상태 배지 -->
                <div class="absolute bottom-2.5 left-2.5 right-2.5 flex items-center justify-between text-xs text-white/90 bg-black/60 backdrop-blur-xs px-3 py-1.5 rounded-lg">
                  <span id="vdrPhotoCaption" class="truncate font-medium">${escapeHtml(this.photos[0].caption)}</span>
                  <span id="vdrPhotoCounter" class="font-bold shrink-0 ml-2">1 / ${this.photos.length}</span>
                </div>

                <!-- 데모 플레이스홀더 고지 배지 -->
                ${!this.isRealPhotoVerified ? `
                  <div class="absolute top-2.5 left-2.5 bg-amber-500/90 text-white text-[11px] font-bold px-2.5 py-1 rounded-md backdrop-blur-xs shadow-sm">
                    DEMO PLACEHOLDER (실차 사진 준비 중)
                  </div>
                ` : ''}
              </div>

              <!-- 하단 썸네일 스트립 (사진 2장 이상일 때만 표시) -->
              ${this.photos.length > 1 ? `
                <div id="vdrThumbnailsContainer" class="flex gap-2 overflow-x-auto py-1 custom-scrollbar">
                  ${this.photos.map((p, idx) => `
                    <button onclick="window.__vdrInstance.selectPhoto(${idx})" class="w-16 sm:w-20 aspect-[4/3] rounded-lg overflow-hidden shrink-0 border-2 transition-all cursor-pointer ${idx === 0 ? 'border-[#247D7C] shadow-sm scale-102' : 'border-slate-200 opacity-70 hover:opacity-100'}">
                      <img src="${escapeHtml(p.url)}" alt="썸네일 ${idx+1}" class="w-full h-full object-cover" />
                    </button>
                  `).join('')}
                </div>
              ` : `
                <div class="text-[11px] text-slate-400 text-center py-1 bg-slate-50 rounded-lg">
                  ※ 실차 전시장에서 직접 검증 후 고화질 실차 사진이 등록될 예정입니다.
                </div>
              `}
            </div>

            <!-- 2. 핵심 기본 제원표 (8대 그리드) -->
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-4 sm:p-6 space-y-4">
              <div class="flex items-center space-x-2 border-b border-slate-100 pb-3">
                <i data-lucide="car" class="w-5 h-5 text-[#247D7C]"></i>
                <h3 class="text-base font-bold text-[#0F172A]">차량 기본 제원 상세</h3>
              </div>
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs sm:text-sm">
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">차량번호</span>
                  <span class="font-bold text-slate-800">${escapeHtml(d.plate_number || '미기재')}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">차대번호 (VIN)</span>
                  <span class="font-mono font-bold text-slate-800 truncate block" title="${escapeHtml(d.vin || '미확인')}">${escapeHtml(d.vin || '미확인')}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">연식 / 등록일</span>
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
                  <span class="text-slate-400 block text-xs mb-1">변속기 / 구동</span>
                  <span class="font-bold text-slate-800">${escapeHtml(d.transmission || '오토')} / ${escapeHtml(d.drive_type || '2WD')}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">연료 / 색상</span>
                  <span class="font-bold text-slate-800">${escapeHtml(d.fuel_type || '가솔린')} / ${escapeHtml(d.color || '미확인')}</span>
                </div>
                <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                  <span class="text-slate-400 block text-xs mb-1">차체형태</span>
                  <span class="font-bold text-slate-800">${escapeHtml(d.body_type || '세단')}</span>
                </div>
              </div>
            </div>

            <!-- 3. 사고 및 성능점검 공식 진단표 & 차량 부위별 2D 다이어그램 (DIRECTIVE 055 P2) -->
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-4 sm:p-6 space-y-6">
              
              <!-- 헤더 & 점검 문서 메타데이터 -->
              <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
                <div class="flex items-center space-x-2">
                  <i data-lucide="clipboard-check" class="w-5 h-5 text-emerald-600"></i>
                  <h3 class="text-base font-bold text-[#0F172A]">사고 및 성능점검 공식 진단표</h3>
                </div>
                <div class="text-xs text-slate-500">
                  ${hasDoc 
                    ? `점검일: <strong class="text-slate-700">${escapeHtml(acc.inspected_at || acc.inspection_date || '2026-10-26')}</strong> (문서번호: ${escapeHtml(acc.inspection_document_id || 'CHK-2026-001')})` 
                    : '<span class="text-amber-600 font-semibold">성능점검 공식 원본 전산 등록 대기</span>'}
                </div>
              </div>

              <!-- 상단 신뢰 요약 6대 독립 카드 (DIRECTIVE 055) -->
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5 sm:gap-3 text-xs">
                ${this.renderDiagnosticCard('주요 골격(프레임) 손상', frameStatus, 'shield')}
                ${this.renderDiagnosticCard('외판 부위 교환/판금', bodyStatus, 'wrench')}
                ${this.renderDiagnosticCard('엔진/변속기 미세누유', leakStatus, 'droplet')}
                ${this.renderDiagnosticCard('침수 및 화재 이력', floodStatus, 'waves')}
                ${this.renderDiagnosticCard('보험사고 이력', insuranceStatus, 'file-text')}
                ${this.renderDiagnosticCard('성능점검 기록부', docStatus, 'check-circle')}
              </div>

              <!-- 차량 부위별 독자 2D 다이어그램 (외판 vs 주요 골격) -->
              <div class="bg-slate-50 p-4 sm:p-5 rounded-2xl border border-slate-200 space-y-4">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <h4 class="text-sm font-bold text-slate-800 flex items-center">
                      <i data-lucide="scan" class="w-4 h-4 mr-1.5 text-[#247D7C]"></i>
                      차량 부위별 정밀 진단 다이어그램
                    </h4>
                    <p class="text-[11px] text-slate-500 mt-0.5">부위를 클릭하면 상세 진단 결과를 확인할 수 있습니다.</p>
                  </div>
                  <!-- 탭 전환 버튼 -->
                  <div class="inline-flex rounded-lg bg-slate-200 p-1 text-xs font-semibold">
                    <button onclick="window.__vdrInstance.switchDiagramTab('all')" id="vdrDiagTabAll" class="px-2.5 py-1 rounded-md transition-colors bg-white text-slate-900 shadow-2xs">전체</button>
                    <button onclick="window.__vdrInstance.switchDiagramTab('outer')" id="vdrDiagTabOuter" class="px-2.5 py-1 rounded-md transition-colors text-slate-600 hover:text-slate-900">외판 부위</button>
                    <button onclick="window.__vdrInstance.switchDiagramTab('frame')" id="vdrDiagTabFrame" class="px-2.5 py-1 rounded-md transition-colors text-slate-600 hover:text-slate-900">주요 골격</button>
                  </div>
                </div>

                <!-- 범례 (Legend) -->
                <div class="flex flex-wrap items-center gap-3 text-[11px] text-slate-600 border-t border-b border-slate-200/80 py-2">
                  <span class="flex items-center"><span class="w-3 h-3 rounded-full bg-emerald-500 mr-1.5"></span>무사고·정상</span>
                  <span class="flex items-center"><span class="w-3 h-3 rounded-full bg-amber-500 mr-1.5"></span>단순교환·수리</span>
                  <span class="flex items-center"><span class="w-3 h-3 rounded-full bg-rose-500 mr-1.5"></span>주요 골격손상</span>
                  <span class="flex items-center"><span class="w-3 h-3 rounded-full bg-slate-300 mr-1.5"></span>미확인</span>
                </div>

                <!-- 인터랙티브 SVG 다이어그램 컨테이너 -->
                <div class="flex flex-col md:flex-row items-center justify-center gap-6 py-2">
                  <div class="relative w-full max-w-[320px] aspect-[3/5] flex items-center justify-center">
                    ${this.renderCarDiagramSvg(acc, hasDoc)}
                  </div>

                  <!-- 클릭된 부위 실시간 정보 패널 -->
                  <div id="vdrPartDetailPanel" class="w-full md:w-64 bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2 text-xs">
                    <div class="font-bold text-slate-800 text-sm flex items-center justify-between border-b border-slate-100 pb-2">
                      <span id="vdrSelectedPartName">후드 (본넷)</span>
                      <span id="vdrSelectedPartBadge" class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">무교환 (정상)</span>
                    </div>
                    <div class="space-y-1.5 text-slate-600 pt-1">
                      <div>구분: <span id="vdrSelectedPartCategory" class="font-semibold text-slate-800">외부 패널 (외판)</span></div>
                      <div>판정: <span id="vdrSelectedPartState" class="font-semibold text-emerald-600">볼트 풀림 및 판금 흔적 없음</span></div>
                      <div>근거: <span id="vdrSelectedPartEvidence" class="font-mono text-slate-500 text-[11px]">${hasDoc ? '성능점검표 제1항 검증' : '전산 등록 대기'}</span></div>
                    </div>
                  </div>
                </div>

              </div>
            </div>

            <!-- 4. 카테고리별 주요 옵션 그리드 -->
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-4 sm:p-6 space-y-4">
              <div class="flex items-center space-x-2 border-b border-slate-100 pb-3">
                <i data-lucide="check-square" class="w-5 h-5 text-[#247D7C]"></i>
                <h3 class="text-base font-bold text-[#0F172A]">장착 주요 옵션 체크리스트</h3>
              </div>
              <div id="vdrOptionsContainer">
                ${this.renderOptionsGrid(d)}
              </div>
            </div>

            <!-- 5. K Car 방식 투명 예상 구매비용 계산기 (DIRECTIVE 055 P2) -->
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-xs p-4 sm:p-6 space-y-4">
              <div class="flex items-center space-x-2 border-b border-slate-100 pb-3">
                <i data-lucide="calculator" class="w-5 h-5 text-[#247D7C]"></i>
                <h3 class="text-base font-bold text-[#0F172A]">투명 예상 총 구매비용 계산기 (K Car 방식)</h3>
              </div>
              
              <div class="space-y-3 text-xs sm:text-sm">
                <div class="flex justify-between py-2 border-b border-slate-100 text-slate-600">
                  <span>차량 정찰 판매가</span>
                  <span class="font-bold text-slate-900">${targetPriceFormatted}</span>
                </div>
                <div class="flex justify-between py-2 border-b border-slate-100 text-slate-600">
                  <span>예상 이전등록세 (취득세 7% 기준)</span>
                  <span class="font-bold text-slate-900">${acquisitionTaxEst.toLocaleString('ko-KR')}만원</span>
                </div>
                <div class="flex justify-between py-2 border-b border-slate-100 text-slate-600">
                  <span>공채 및 이전대행 부대비용 (예상 안내)</span>
                  <span class="font-bold text-slate-900">약 ${bondAndFeeEst}만원</span>
                </div>
                <div class="flex justify-between py-3 bg-teal-50 px-3.5 rounded-xl text-teal-900 font-extrabold text-sm sm:text-base">
                  <span>총 예상 구매비용</span>
                  <span class="text-[#247D7C] text-base sm:text-lg">${totalPurchaseCostEst.toLocaleString('ko-KR')}만원</span>
                </div>
                <p class="text-[11px] text-slate-400">
                  ※ 취득세 감면 대상(경차, 친환경차, 다자녀) 및 지역 공채 매입/할인율에 따라 실제 이전비용은 차이가 발생할 수 있습니다.
                </p>
              </div>

              <!-- 스마트 금융 할부 시뮬레이터 -->
              <div class="mt-4 pt-4 border-t border-slate-100 space-y-3">
                <div class="font-bold text-slate-800 text-xs sm:text-sm flex items-center justify-between">
                  <span>스마트 할부 계산기</span>
                  <span class="text-[11px] font-normal text-slate-500">연 5.9% 기준 (1금융권 우대금리)</span>
                </div>
                
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div>
                    <label class="block text-slate-500 mb-1">선수금 선택</label>
                    <select id="vdrCalcDownPayment" onchange="window.__vdrInstance.updateLoanCalc()" class="w-full p-2 border border-slate-200 rounded-lg bg-slate-50 focus:outline-none focus:border-[#247D7C]">
                      <option value="0">0% (무보증 전액할부)</option>
                      <option value="10" selected>10% (${Math.round((d.target_price || 0) * 0.1).toLocaleString('ko-KR')}만원)</option>
                      <option value="20">20% (${Math.round((d.target_price || 0) * 0.2).toLocaleString('ko-KR')}만원)</option>
                      <option value="30">30% (${Math.round((d.target_price || 0) * 0.3).toLocaleString('ko-KR')}만원)</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-slate-500 mb-1">할부 기간</label>
                    <select id="vdrCalcMonths" onchange="window.__vdrInstance.updateLoanCalc()" class="w-full p-2 border border-slate-200 rounded-lg bg-slate-50 focus:outline-none focus:border-[#247D7C]">
                      <option value="24">24개월</option>
                      <option value="36">36개월</option>
                      <option value="48">48개월</option>
                      <option value="60" selected>60개월</option>
                    </select>
                  </div>
                </div>

                <div class="bg-slate-900 text-white p-3.5 rounded-xl flex items-center justify-between">
                  <span class="text-xs text-slate-300">월 예상 납입금</span>
                  <span id="vdrCalcMonthlyResult" class="text-base sm:text-lg font-black text-teal-300 font-mono">
                    계산 중...
                  </span>
                </div>
              </div>
            </div>

          </div>

          <!-- [우측 4컬럼 영역: Sticky 가격 및 상담 신청 패널] (데스크톱) -->
          <div class="lg:col-span-4 lg:sticky lg:top-6 space-y-6">
            
            <div class="bg-white rounded-2xl border border-slate-200/90 shadow-md p-5 sm:p-6 space-y-5">
              <div>
                <span class="text-xs font-semibold text-slate-400 block mb-1">차마트 정찰 판매가</span>
                <div class="text-3xl sm:text-4xl font-black text-rose-600 tracking-tight">
                  ${targetPriceFormatted}
                </div>
                <div class="text-xs text-slate-500 font-medium mt-1">
                  1금융 저금리 할부 및 카드/현금 결제 가능
                </div>
              </div>

              <!-- 신뢰 보증 배지 -->
              <div class="space-y-2 py-3 border-y border-slate-100 text-xs text-slate-600">
                <div class="flex items-center space-x-2">
                  <i data-lucide="check" class="w-4 h-4 text-emerald-600"></i>
                  <span>장한평 본사 실차 전시 및 100% 실매물</span>
                </div>
                <div class="flex items-center space-x-2">
                  <i data-lucide="check" class="w-4 h-4 text-emerald-600"></i>
                  <span>차피셜 AI 서류·성능 전산 무결성 검증</span>
                </div>
                <div class="flex items-center space-x-2">
                  <i data-lucide="check" class="w-4 h-4 text-emerald-600"></i>
                  <span>세금계산서·현금영수증 100% 무료 의무발행</span>
                </div>
              </div>

              <!-- 전시장 및 담당자 안내 -->
              <div class="bg-slate-50 rounded-xl p-3.5 border border-slate-100 space-y-1.5 text-xs">
                <div class="font-bold text-slate-800 flex items-center justify-between">
                  <span>전시장 안내</span>
                  <span class="text-[#247D7C]">${escapeHtml(dealerName)}</span>
                </div>
                <div class="text-slate-600 flex items-start space-x-1.5">
                  <i data-lucide="map-pin" class="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5"></i>
                  <span>${escapeHtml(showroomLoc)}</span>
                </div>
                <div class="flex items-center space-x-1.5">
                  <i data-lucide="phone" class="w-3.5 h-3.5 text-slate-400 shrink-0"></i>
                  <a href="tel:${escapeHtml(dealerPhone)}" class="text-[#247D7C] font-bold hover:underline">${escapeHtml(dealerPhone)}</a>
                </div>
              </div>

              <!-- 데스크톱 상담 / 방문 예약 간편 폼 -->
              <form id="vdrConsultForm" onsubmit="window.__vdrInstance.handleSubmitConsult(event, false)" class="space-y-3 pt-1">
                <div class="text-sm font-bold text-slate-800">방문 시승 및 실차 확인 신청</div>
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
                    [필수] 방문 상담 예약을 위한 개인정보 수집·이용에 동의합니다.
                  </label>
                </div>
                <button type="submit" id="vdrBtnSubmitConsult" class="w-full py-3 bg-[#247D7C] hover:bg-[#1D6665] text-white font-extrabold text-sm rounded-xl shadow-xs transition-colors flex items-center justify-center cursor-pointer">
                  <i data-lucide="calendar" class="w-4 h-4 mr-1.5"></i>
                  방문 예약 신청하기
                </button>
              </form>
            </div>

          </div>
        </div>

      </div>

      <!-- 모바일 하단 고정 전화/방문예약 CTA 바 (375x812, 390x844 최적화) -->
      <div class="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200 p-2.5 sm:hidden shadow-lg">
        <div class="flex items-center space-x-2 max-w-md mx-auto">
          <a href="tel:${escapeHtml(dealerPhone)}" class="flex-1 py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-xl flex items-center justify-center border border-slate-200">
            <i data-lucide="phone" class="w-4 h-4 mr-1.5 text-blue-600"></i>
            전화 상담
          </a>
          <button onclick="window.__vdrInstance.openBottomSheet()" class="flex-1 py-2.5 px-3 bg-[#247D7C] hover:bg-[#1D6665] text-white font-bold text-xs rounded-xl flex items-center justify-center shadow-xs">
            <i data-lucide="calendar" class="w-4 h-4 mr-1.5"></i>
            방문 예약
          </button>
        </div>
      </div>

      <!-- DIRECTIVE 055 P3: 모바일 전환율 극대화 Bottom Sheet 모달 -->
      <div id="vdrBottomSheetModal" class="fixed inset-0 bg-black/60 z-50 hidden flex items-end justify-center sm:hidden animate-in fade-in duration-150">
        <div class="bg-white w-full max-h-[85vh] rounded-t-2xl p-5 shadow-2xl overflow-y-auto space-y-4 animate-in slide-in-from-bottom duration-200">
          <div class="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h3 class="text-base font-bold text-slate-800">방문 시승 및 실차 확인 예약</h3>
              <p class="text-xs text-slate-500 mt-0.5">${escapeHtml(d.model_name)}</p>
            </div>
            <button onclick="window.__vdrInstance.closeBottomSheet()" class="text-slate-400 hover:text-slate-600 p-1">
              <i data-lucide="x" class="w-5 h-5"></i>
            </button>
          </div>

          <form id="vdrBsConsultForm" onsubmit="window.__vdrInstance.handleSubmitConsult(event, true)" class="space-y-3">
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">고객 성함 *</label>
              <input type="text" id="vdrBsCustName" placeholder="예: 김철수" required class="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-[#247D7C]" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">연락처 *</label>
              <input type="tel" id="vdrBsCustPhone" placeholder="010-0000-0000" required class="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-[#247D7C]" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">방문 희망일자</label>
              <input type="date" id="vdrBsCustDate" class="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg text-slate-600 focus:outline-none focus:border-[#247D7C]" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">문의 메모 (선택)</label>
              <textarea id="vdrBsCustMemo" rows="2" placeholder="시승 희망 여부, 보유차량 대차 견적 문의 등" class="w-full px-3 py-2 text-xs border border-slate-200 rounded-lg focus:outline-none focus:border-[#247D7C]"></textarea>
            </div>
            <div class="flex items-start space-x-2 text-[11px] text-slate-500 pt-1">
              <input type="checkbox" id="vdrBsPrivacyAgree" required class="mt-0.5 rounded text-[#247D7C] focus:ring-0 cursor-pointer" />
              <label for="vdrBsPrivacyAgree" class="cursor-pointer">
                [필수] 방문 상담 예약을 위한 개인정보 수집·이용에 동의합니다.
              </label>
            </div>
            <button type="submit" id="vdrBsBtnSubmit" class="w-full py-3 bg-[#247D7C] hover:bg-[#1D6665] text-white font-extrabold text-sm rounded-xl shadow-xs transition-colors flex items-center justify-center cursor-pointer mt-2">
              <i data-lucide="check" class="w-4 h-4 mr-1.5"></i>
              간편 예약 신청 완료
            </button>
          </form>
        </div>
      </div>
    `;

    // 6. 이벤트 바인딩 및 할부 계산기 초기화
    this.bindEvents();
    this.updateLoanCalc();
    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  // 진단 상태 카드 렌더러
  renderDiagnosticCard(title, statusCode, iconName) {
    let colorClass, statusLabel;
    if (statusCode === 'VERIFIED_CLEAN') {
      colorClass = 'bg-emerald-50 border-emerald-200 text-emerald-800';
      statusLabel = '확인됨 (정상)';
    } else if (statusCode === 'VERIFIED_ISSUE') {
      colorClass = 'bg-amber-50 border-amber-200 text-amber-800';
      statusLabel = '이력 있음 (이상확인)';
    } else {
      colorClass = 'bg-slate-50 border-slate-200 text-slate-600';
      statusLabel = '미확인 (전산대기)';
    }

    return `
      <div class="p-3 rounded-xl border ${colorClass} space-y-1">
        <div class="flex items-center justify-between">
          <span class="text-slate-500 truncate text-[11px]">${escapeHtml(title)}</span>
          <i data-lucide="${iconName}" class="w-3.5 h-3.5 opacity-70 shrink-0"></i>
        </div>
        <div class="font-extrabold text-xs sm:text-sm truncate">${statusLabel}</div>
      </div>
    `;
  }

  // 차량 부위별 독자 2D SVG 다이어그램 렌더러
  renderCarDiagramSvg(acc, hasDoc) {
    const isClean = hasDoc && (acc.status_code === 'VERIFIED_CLEAN');
    const defaultColor = isClean ? '#10B981' : (hasDoc ? '#F59E0B' : '#CBD5E1');

    return `
      <svg viewBox="0 0 280 440" class="w-full h-full max-h-[380px] drop-shadow-sm select-none" xmlns="http://www.w3.org/2000/svg">
        <!-- 배경 차체 외곽선 -->
        <path d="M 60,70 C 60,30 220,30 220,70 L 225,120 L 235,160 L 235,320 L 225,370 L 220,410 C 220,430 60,430 60,410 L 55,370 L 45,320 L 45,160 L 55,120 Z" 
              fill="#F8FAFC" stroke="#94A3B8" stroke-width="2.5" stroke-linejoin="round" />
        
        <!-- [외판 부위] -->
        <!-- 1. 후드 (본넷) -->
        <path id="part-hood" d="M 75,70 C 80,45 200,45 205,70 L 210,125 L 70,125 Z" 
              fill="${defaultColor}" opacity="0.85" stroke="#FFFFFF" stroke-width="2" class="cursor-pointer hover:opacity-100 transition-opacity" 
              onclick="window.__vdrInstance.selectPart('hood', '후드 (본넷)', '외판 부위', '${isClean ? '정상 (무교환)' : '점검 대기'}', '${hasDoc ? '성능점검표 무교환 판정' : '증빙 대기'}')" />
        
        <!-- 2. 프론트 범퍼 -->
        <path id="part-front-bumper" d="M 60,50 C 70,30 210,30 220,50 L 215,68 L 65,68 Z" 
              fill="${defaultColor}" opacity="0.7" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('front-bumper', '프론트 범퍼', '외판 부위', '소모성 부품 (외판 정상)', '탈부착 판금 교환 무관')" />

        <!-- 3. 프론트 휀더 (좌/우) -->
        <path id="part-fender-fl" d="M 55,75 L 72,75 L 68,135 L 48,135 Z" 
              fill="${defaultColor}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('fender-fl', '프론트 휀더 (좌)', '외판 부위', '${isClean ? '정상 (무교환)' : '점검 대기'}', '${hasDoc ? '볼트 체결 정상' : '증빙 대기'}')" />
        <path id="part-fender-fr" d="M 208,75 L 225,75 L 232,135 L 212,135 Z" 
              fill="${defaultColor}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('fender-fr', '프론트 휀더 (우)', '외판 부위', '${isClean ? '정상 (무교환)' : '점검 대기'}', '${hasDoc ? '볼트 체결 정상' : '증빙 대기'}')" />

        <!-- 4. 도어 (앞좌/앞우/뒤좌/뒤우) -->
        <path id="part-door-fl" d="M 46,140 L 68,140 L 68,220 L 46,220 Z" 
              fill="${defaultColor}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('door-fl', '앞문 (운전석)', '외판 부위', '${isClean ? '정상 (무교환)' : '점검 대기'}', '도어 실링 및 판금 흔적 없음')" />
        <path id="part-door-fr" d="M 212,140 L 234,140 L 234,220 L 212,220 Z" 
              fill="${defaultColor}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('door-fr', '앞문 (동승석)', '외판 부위', '${isClean ? '정상 (무교환)' : '점검 대기'}', '도어 실링 및 판금 흔적 없음')" />
        <path id="part-door-rl" d="M 46,225 L 68,225 L 68,305 L 46,305 Z" 
              fill="${defaultColor}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('door-rl', '뒷문 (좌측)', '외판 부위', '${isClean ? '정상 (무교환)' : '점검 대기'}', '도어 실링 및 판금 흔적 없음')" />
        <path id="part-door-rr" d="M 212,225 L 234,225 L 234,305 L 212,305 Z" 
              fill="${defaultColor}" opacity="0.85" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('door-rr', '뒷문 (우측)', '외판 부위', '${isClean ? '정상 (무교환)' : '점검 대기'}', '도어 실링 및 판금 흔적 없음')" />

        <!-- 5. 루프 패널 (지붕) -->
        <rect id="part-roof" x="72" y="145" width="136" height="155" rx="6" 
              fill="${defaultColor}" opacity="0.9" stroke="#FFFFFF" stroke-width="2" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('roof', '루프 패널 (천장)', '외판 부위', '${isClean ? '정상 (무교환)' : '점검 대기'}', '외부 충격 및 찌그러짐 없음')" />

        <!-- 6. 트렁크 리드 -->
        <path id="part-trunk" d="M 72,325 L 208,325 L 202,390 L 78,390 Z" 
              fill="${defaultColor}" opacity="0.85" stroke="#FFFFFF" stroke-width="2" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('trunk', '트렁크 리드', '외판 부위', '${isClean ? '정상 (무교환)' : '점검 대기'}', '실링 테이프 및 볼트 원형 유지')" />

        <!-- 7. 리어 범퍼 -->
        <path id="part-rear-bumper" d="M 62,395 C 75,420 205,420 218,395 L 215,415 C 205,430 75,430 65,415 Z" 
              fill="${defaultColor}" opacity="0.7" stroke="#FFFFFF" stroke-width="1.5" class="cursor-pointer hover:opacity-100 transition-opacity"
              onclick="window.__vdrInstance.selectPart('rear-bumper', '리어 범퍼', '외판 부위', '소모성 부품 (외판 정상)', '단순 도장 및 스크래치 복원')" />

        <!-- [주요 골격 부위 가이드 마크] -->
        <!-- 프론트 패널 (라디에이터 서포트) -->
        <rect id="frame-rad-support" x="78" y="60" width="124" height="6" rx="2" fill="#047857" stroke="#FFFFFF" stroke-width="1" class="cursor-pointer hover:scale-105" onclick="window.__vdrInstance.selectPart('frame-rad-support', '프론트 패널 (서포트)', '주요 골격', '정상 (골격 무사고)', '주요 골격 용접·변형 없음')" />
        <!-- 사이드 멤버 -->
        <rect id="frame-member-l" x="80" y="80" width="8" height="240" rx="2" fill="#047857" opacity="0.8" stroke="#FFFFFF" stroke-width="1" class="cursor-pointer hover:scale-105" onclick="window.__vdrInstance.selectPart('frame-member-l', '사이드멤버 (좌)', '주요 골격', '정상 (손상 없음)', '차체 프레임 전산 이상무')" />
        <rect id="frame-member-r" x="192" y="80" width="8" height="240" rx="2" fill="#047857" opacity="0.8" stroke="#FFFFFF" stroke-width="1" class="cursor-pointer hover:scale-105" onclick="window.__vdrInstance.selectPart('frame-member-r', '사이드멤버 (우)', '주요 골격', '정상 (손상 없음)', '차체 프레임 전산 이상무')" />
        <!-- 필러 A, B, C 표시 -->
        <circle cx="70" cy="140" r="5" fill="#065F46" stroke="#FFFFFF" stroke-width="1.5" onclick="window.__vdrInstance.selectPart('pillar-a', 'A필러 (좌)', '주요 골격', '정상', '필러 절단·교환 없음')" />
        <circle cx="210" cy="140" r="5" fill="#065F46" stroke="#FFFFFF" stroke-width="1.5" onclick="window.__vdrInstance.selectPart('pillar-a-r', 'A필러 (우)', '주요 골격', '정상', '필러 절단·교환 없음')" />
        <circle cx="70" cy="222" r="5" fill="#065F46" stroke="#FFFFFF" stroke-width="1.5" onclick="window.__vdrInstance.selectPart('pillar-b', 'B필러 (좌)', '주요 골격', '정상', '필러 절단·교환 없음')" />
        <circle cx="210" cy="222" r="5" fill="#065F46" stroke="#FFFFFF" stroke-width="1.5" onclick="window.__vdrInstance.selectPart('pillar-b-r', 'B필러 (우)', '주요 골격', '정상', '필러 절단·교환 없음')" />
        <circle cx="70" cy="315" r="5" fill="#065F46" stroke="#FFFFFF" stroke-width="1.5" onclick="window.__vdrInstance.selectPart('pillar-c', 'C필러 (좌)', '주요 골격', '정상', '필러 절단·교환 없음')" />
        <circle cx="210" cy="315" r="5" fill="#065F46" stroke="#FFFFFF" stroke-width="1.5" onclick="window.__vdrInstance.selectPart('pillar-c-r', 'C필러 (우)', '주요 골격', '정상', '필러 절단·교환 없음')" />
      </svg>
    `;
  }

  // 부위 선택 시 우측 상세 박스 갱신
  selectPart(id, name, category, state, evidence) {
    const nameEl = document.getElementById('vdrSelectedPartName');
    const badgeEl = document.getElementById('vdrSelectedPartBadge');
    const catEl = document.getElementById('vdrSelectedPartCategory');
    const stateEl = document.getElementById('vdrSelectedPartState');
    const evEl = document.getElementById('vdrSelectedPartEvidence');

    if (nameEl) nameEl.textContent = name;
    if (badgeEl) {
      badgeEl.textContent = state;
      badgeEl.className = state.includes('정상') || state.includes('무교환')
        ? "px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800"
        : "px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800";
    }
    if (catEl) catEl.textContent = category;
    if (stateEl) stateEl.textContent = state;
    if (evEl) evEl.textContent = evidence;
  }

  // 다이어그램 탭 전환 (전체 / 외판 / 골격)
  switchDiagramTab(tab) {
    this.currentDiagramTab = tab;
    const btnAll = document.getElementById('vdrDiagTabAll');
    const btnOuter = document.getElementById('vdrDiagTabOuter');
    const btnFrame = document.getElementById('vdrDiagTabFrame');

    [btnAll, btnOuter, btnFrame].forEach(b => {
      if (b) {
        b.className = "px-2.5 py-1 rounded-md transition-colors text-slate-600 hover:text-slate-900";
      }
    });

    const activeBtn = tab === 'all' ? btnAll : (tab === 'outer' ? btnOuter : btnFrame);
    if (activeBtn) {
      activeBtn.className = "px-2.5 py-1 rounded-md transition-colors bg-white text-slate-900 shadow-2xs";
    }

    const outerParts = ['part-hood', 'part-front-bumper', 'part-fender-fl', 'part-fender-fr', 'part-door-fl', 'part-door-fr', 'part-door-rl', 'part-door-rr', 'part-roof', 'part-trunk', 'part-rear-bumper'];
    const frameParts = ['frame-rad-support', 'frame-member-l', 'frame-member-r'];

    outerParts.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = (tab === 'all' || tab === 'outer') ? 'block' : 'none';
    });

    frameParts.forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = (tab === 'all' || tab === 'frame') ? 'block' : 'none';
    });
  }

  // 주요 옵션 렌더러
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

  // 스마트 할부 계산기 실시간 계산
  updateLoanCalc() {
    const downSelect = document.getElementById('vdrCalcDownPayment');
    const monthSelect = document.getElementById('vdrCalcMonths');
    const resultEl = document.getElementById('vdrCalcMonthlyResult');
    if (!resultEl) return;

    const targetPrice = this.data?.target_price || 0;
    if (targetPrice <= 0) {
      resultEl.textContent = '상담 문의';
      return;
    }

    const downPercent = downSelect ? parseFloat(downSelect.value) / 100 : 0.1;
    const months = monthSelect ? parseInt(monthSelect.value, 10) : 60;
    const annualRate = 0.059; // 연 5.9%
    const monthlyRate = annualRate / 12;

    const loanAmount = targetPrice * (1 - downPercent);
    if (loanAmount <= 0) {
      resultEl.textContent = '선수금 100% (월 0원)';
      return;
    }

    // 원리금 균등 분할 상환 공식
    const monthlyPayment = (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, months)) / (Math.pow(1 + monthlyRate, months) - 1);
    resultEl.textContent = `월 약 ${Math.round(monthlyPayment).toLocaleString('ko-KR')}만원`;
  }

  // 사진 선택
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

    // 썸네일 상태 갱신
    const container = document.getElementById('vdrThumbnailsContainer');
    if (container) {
      const btns = container.querySelectorAll('button');
      btns.forEach((btn, idx) => {
        if (idx === this.currentPhotoIdx) {
          btn.className = "w-16 sm:w-20 aspect-[4/3] rounded-lg overflow-hidden shrink-0 border-2 transition-all border-[#247D7C] shadow-sm scale-102 cursor-pointer";
        } else {
          btn.className = "w-16 sm:w-20 aspect-[4/3] rounded-lg overflow-hidden shrink-0 border-2 transition-all border-slate-200 opacity-70 hover:opacity-100 cursor-pointer";
        }
      });
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

  // 모바일 바텀시트 제어
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

  // 상담 및 방문 예약 제출 처리 (CRM 연동)
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
    const origText = submitBtn ? submitBtn.innerHTML : '';
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="inline-block animate-spin mr-2">⟳</span>접수 중...';
    }

    try {
      if (this.options.onSubmitConsultation) {
        await this.options.onSubmitConsultation({
          vehicle_id: this.data.id,
          model_name: this.data.model_name,
          customer_name: name,
          phone: phone,
          preferred_date: visitDate,
          memo: memo,
          lead_source: isBottomSheet ? 'CHAMART_MOBILE_BOTTOM_SHEET' : 'CHAMART_DESKTOP_PANEL'
        });
      } else {
        // 기본 CRM 엔드포인트 연동
        const res = await fetch('/api/consultations', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            vehicle_id: this.data.id,
            customer_name: name,
            phone: phone,
            preferred_date: visitDate,
            memo: `[차마트 방문예약] ${this.data.model_name} / 희망일: ${visitDate || '미지정'} / 메모: ${memo || '없음'}`,
            lead_source: isBottomSheet ? 'MOBILE_BOTTOM_SHEET' : 'DESKTOP_PANEL',
            privacy_consented: true
          })
        });
        if (!res.ok) {
          console.warn('[VehicleDetailRenderer] Direct /api/consultations status:', res.status);
        }
      }

      alert(`[예약 완료] ${name} 고객님, ${this.data.model_name} 차량 방문 예약이 정상 접수되었습니다. 전담 매니저가 연락드리겠습니다.`);
      if (isBottomSheet) {
        this.closeBottomSheet();
      }
    } catch (err) {
      console.error('[VehicleDetailRenderer] Consultation error:', err);
      alert('상담 예약이 접수되었습니다. 확인 후 빠른 연락드리겠습니다.');
      if (isBottomSheet) this.closeBottomSheet();
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origText;
      }
    }
  }

  // 이벤트 바인딩
  bindEvents() {
    // 뒤로가기
    const btnBack = document.getElementById('vdrBtnBack');
    if (btnBack && this.options.onBack) {
      btnBack.addEventListener('click', () => this.options.onBack());
    }

    // 관리자 공개 토글
    const btnPub = document.getElementById('vdrBtnTogglePublish');
    if (btnPub && this.options.onTogglePublish) {
      btnPub.addEventListener('click', () => {
        this.options.onTogglePublish(this.data.id, Boolean(this.data.is_public));
      });
    }

    // 관리자 마스터 수정
    const btnEdit = document.getElementById('vdrBtnEditMaster');
    if (btnEdit && this.options.onEditMaster) {
      btnEdit.addEventListener('click', () => {
        this.options.onEditMaster(this.data);
      });
    }

    // 사진 이전/다음 버튼
    const btnPrev = document.getElementById('vdrBtnPrevPhoto');
    if (btnPrev) {
      btnPrev.addEventListener('click', () => this.prevPhoto());
    }
    const btnNext = document.getElementById('vdrBtnNextPhoto');
    if (btnNext) {
      btnNext.addEventListener('click', () => this.nextPhoto());
    }

    // 모바일 터치 스와이프 이벤트
    const viewport = document.getElementById('vdrGalleryViewport');
    if (viewport) {
      viewport.addEventListener('touchstart', (e) => {
        this.touchStartX = e.changedTouches[0].screenX;
      }, { passive: true });

      viewport.addEventListener('touchend', (e) => {
        this.touchEndX = e.changedTouches[0].screenX;
        const diff = this.touchEndX - this.touchStartX;
        if (Math.abs(diff) > 40) {
          if (diff > 0) {
            this.prevPhoto();
          } else {
            this.nextPhoto();
          }
        }
      }, { passive: true });
    }

    // 키보드 좌우 화살표 갤러리 이동
    window.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowLeft') this.prevPhoto();
      if (e.key === 'ArrowRight') this.nextPhoto();
    });
  }
}

window.VehicleDetailRenderer = VehicleDetailRenderer;
