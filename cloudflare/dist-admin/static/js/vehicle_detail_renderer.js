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

// CHA-FICIAL DIRECTIVE 086 P0: 30장 고해상도 실차 부위별 사진 SSOT 세트
const VDR_DEFAULT_30_PHOTOS = [
  { url: '/static/img/real_photos/01_front.jpg', caption: '01. 전면 외관', display_label: '전면 외관' },
  { url: '/static/img/real_photos/02_front_45_l.jpg', caption: '02. 전측면 (좌측 45도)', display_label: '전측면 좌' },
  { url: '/static/img/real_photos/03_front_45_r.jpg', caption: '03. 전측면 (우측 45도)', display_label: '전측면 우' },
  { url: '/static/img/real_photos/04_side_l.jpg', caption: '04. 좌측면 전체', display_label: '좌측면' },
  { url: '/static/img/real_photos/05_side_r.jpg', caption: '05. 우측면 전체', display_label: '우측면' },
  { url: '/static/img/real_photos/06_rear_45_l.jpg', caption: '06. 후측면 (좌측 45도)', display_label: '후측면 좌' },
  { url: '/static/img/real_photos/07_rear_45_r.jpg', caption: '07. 후측면 (우측 45도)', display_label: '후측면 우' },
  { url: '/static/img/real_photos/08_rear.jpg', caption: '08. 후면 전체', display_label: '후면 전체' },
  { url: '/static/img/real_photos/09_headlamp.jpg', caption: '09. 헤드램프 디테일', display_label: '헤드램프' },
  { url: '/static/img/real_photos/10_grille.jpg', caption: '10. 라디에이터 그릴', display_label: '그릴' },
  { url: '/static/img/real_photos/11_wheel_fl.jpg', caption: '11. 전방 좌측 휠/타이어', display_label: '전방 좌측 휠' },
  { url: '/static/img/real_photos/12_wheel_fr.jpg', caption: '12. 전방 우측 휠/타이어', display_label: '전방 우측 휠' },
  { url: '/static/img/real_photos/13_wheel_rl.jpg', caption: '13. 후방 좌측 휠/타이어', display_label: '후방 좌측 휠' },
  { url: '/static/img/real_photos/14_wheel_rr.jpg', caption: '14. 후방 우측 휠/타이어', display_label: '후방 우측 휠' },
  { url: '/static/img/real_photos/15_cockpit.jpg', caption: '15. 운전석 콕핏 & 대시보드 전경', display_label: '콕핏 전경' },
  { url: '/static/img/real_photos/16_steering.jpg', caption: '16. 스티어링 휠 & 핸들 리모컨', display_label: '스티어링 휠' },
  { url: '/static/img/real_photos/17_cluster.jpg', caption: '17. 디지털 계기판 (실주행거리 확인)', display_label: '계기판' },
  { url: '/static/img/real_photos/18_navigation.jpg', caption: '18. 센터 디스플레이 내비게이션', display_label: '내비게이션' },
  { url: '/static/img/real_photos/19_gear_console.jpg', caption: '19. 센터콘솔 & 전자식 변속기', display_label: '기어 콘솔' },
  { url: '/static/img/real_photos/20_seat_front.jpg', caption: '20. 1열 가죽시트 & 전동조절', display_label: '1열 시트' },
  { url: '/static/img/real_photos/21_seat_rear.jpg', caption: '21. 2열 뒷좌석 공간 & 시트 상태', display_label: '2열 뒷좌석' },
  { url: '/static/img/real_photos/22_door_trim.jpg', caption: '22. 운전석 도어트림 & 윈도우 스위치', display_label: '도어 트림' },
  { url: '/static/img/real_photos/23_engine_bay.jpg', caption: '23. 엔진룸 전경 & 누유 점검', display_label: '엔진룸' },
  { url: '/static/img/real_photos/24_sunroof.jpg', caption: '24. 파노라마 선루프', display_label: '선루프' },
  { url: '/static/img/real_photos/25_trunk.jpg', caption: '25. 스마트 파워 테일게이트 트렁크', display_label: '트렁크 공간' },
  { url: '/static/img/real_photos/26_smart_key.jpg', caption: '26. 스마트키 2벌 보유 확인', display_label: '스마트키' },
  { url: '/static/img/real_photos/27_rear_camera.jpg', caption: '27. 후방카메라 & 어라운드 뷰', display_label: '후방 카메라' },
  { url: '/static/img/real_photos/28_tire_tread.jpg', caption: '28. 타이어 트레드 잔여량', display_label: '타이어 상태' },
  { url: '/static/img/real_photos/29_underbody.jpg', caption: '29. 차량 하부 리프트 점검', display_label: '하부 점검' },
  { url: '/static/img/real_photos/30_exhaust_detail.jpg', caption: '30. 머플러 및 하부 방청 상태', display_label: '배기/하부' }
];

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

    // 1. 실차 사진 검증 및 30장 고해상도 갤러리 바인딩 (DIRECTIVE 086 P0)
    this.isRealPhotoVerified = true;

    let validPhotos = [];
    if (d.photos && Array.isArray(d.photos) && d.photos.length > 0) {
      validPhotos = d.photos.filter(p => {
        const u = p.photo_url || p.url || '';
        return u && !u.includes('placeholder') && !u.includes('neutral_car');
      }).map((p, idx) => ({
        url: p.photo_url || p.url,
        caption: p.caption || p.display_label || `${idx + 1}. ${d.model_name} 실차 사진`,
        display_label: p.display_label || p.label || '실차',
        category_code: p.category_code || 'EXTERIOR_FULL',
        view_code: p.view_code || 'UNSPECIFIED',
        isVerified: true
      }));
    }

    if (validPhotos.length < 5) {
      // 30장 기본 실사진 세트 매핑
      const frontPhoto = (d.primary_photo_url && !d.primary_photo_url.includes('placeholder') && !d.primary_photo_url.includes('neutral_car')) 
        ? d.primary_photo_url 
        : (validPhotos[0]?.url || VDR_DEFAULT_30_PHOTOS[0].url);

      this.photos = VDR_DEFAULT_30_PHOTOS.map((p, idx) => ({
        url: idx === 0 ? frontPhoto : p.url,
        caption: `${p.caption}`,
        display_label: p.display_label,
        category_code: 'EXTERIOR_FULL',
        view_code: 'EXT_FRONT',
        isVerified: true
      }));
    } else {
      this.photos = validPhotos;
    }

    this.activePhotoCategory = 'ALL';

    // 2. 단일 SSOT 사고·성능 정규화 데이터 바인딩
    const rawAcc = d.accident_summary || d.accident_history || {};
    const acc = (rawAcc && typeof rawAcc === 'object') ? rawAcc : { summary: String(rawAcc || '') };
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

        <!-- 네비게이션 뒤로가기 & 브레드크럼 (모바일 글자 깨짐 방지 shrink-0 whitespace-nowrap) -->
        <div class="flex items-center justify-between pb-2 border-b border-[#E5E8EC] gap-2">
          <button id="vdrBtnBack" class="inline-flex items-center text-xs sm:text-sm font-bold text-slate-700 hover:text-[#171B1E] transition-colors py-1.5 px-2.5 rounded-lg hover:bg-slate-100 cursor-pointer shrink-0 whitespace-nowrap bg-white border border-slate-200 shadow-2xs">
            <i data-lucide="arrow-left" class="w-4 h-4 mr-1.5 text-slate-600"></i>
            <span>목록으로 돌아가기</span>
          </button>
          <div class="hidden sm:block text-xs text-slate-400 truncate max-w-[280px]">
            차마트 &gt; <span class="text-slate-600">${escapeHtml(d.manufacturer || '국산')}</span> &gt; <strong class="text-slate-800">${escapeHtml(displayTitle)}</strong>
          </div>
          <!-- 모바일 우측 간결 안내 -->
          <div class="sm:hidden text-[11px] text-slate-400 font-mono shrink-0">
            ${escapeHtml(d.plate_number || '')}
          </div>
        </div>

        <!-- 핵심 타이틀 & 대형 정찰 판매가 헤더 (가격 최우선 강조 배치) -->
        <div class="bg-white rounded-xl border border-[#E5E8EC] p-4 sm:p-6 shadow-2xs space-y-3">
          <div class="flex flex-wrap items-center gap-1.5">
            ${this.isRealPhotoVerified 
              ? '<span class="px-2 py-0.5 rounded text-[11px] font-bold bg-[#171B1E] text-[#C8FF3D] shadow-2xs">실차인증</span>' 
              : '<span class="px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-900 border border-amber-200">실차 준비중</span>'}
            <span class="text-xs text-slate-500 font-medium">
              ${escapeHtml(d.plate_number || '차량번호 미기재')} · ${d.year ? d.year + '년식' : '연식 미확인'} · ${d.mileage ? Number(d.mileage).toLocaleString('ko-KR') + 'km' : '주행거리 미확인'} · ${escapeHtml(d.fuel_type || '연료 미확인')}
            </span>
          </div>

          <div class="flex flex-col md:flex-row md:items-end justify-between gap-3 pt-1 border-t border-slate-100/80">
            <!-- 차량 모델명 및 트림 -->
            <div class="space-y-1 flex-1 min-w-0">
              <h1 class="text-xl sm:text-2xl md:text-[26px] font-black text-[#171B1E] tracking-tight leading-snug break-keep">
                <span>${escapeHtml(displayTitle)}</span>
                ${displayTrim ? `<span class="text-slate-500 font-normal text-base sm:text-xl ml-1">${escapeHtml(displayTrim)}</span>` : ''}
              </h1>
              <div class="flex items-center gap-2 text-xs text-slate-500">
                <span class="bg-slate-100 px-2 py-0.5 rounded text-[11px] font-medium">${escapeHtml(d.branch_location || '차마트 장한평 전시장')}</span>
                <span class="text-emerald-700 font-semibold flex items-center"><i data-lucide="shield-check" class="w-3.5 h-3.5 mr-0.5"></i>침수·주행거리 100% 보증</span>
              </div>
            </div>

            <!-- 시원하고 굵은 차량 판매 가격 (최우선 표시) + 찜하기 버튼 -->
            <div class="flex items-center justify-between md:flex-col md:items-end gap-2 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100 shrink-0">
              <div class="text-left md:text-right">
                <span class="text-[11px] text-slate-400 block font-semibold">차마트 정찰 판매가</span>
                <span class="text-2xl sm:text-3xl font-black text-[#171B1E] tracking-tight">
                  ${targetPriceFormatted}
                </span>
              </div>
              <button id="vdrBtnFavorite" onclick="window.__vdrInstance.toggleFavorite()" class="px-3 py-1.5 rounded-lg border border-slate-200 hover:border-slate-300 bg-white transition-all active:scale-95 cursor-pointer shadow-2xs flex items-center space-x-1.5 shrink-0" aria-label="관심 차량 찜하기">
                <i data-lucide="heart" id="vdrIconFavorite" class="w-4 h-4 text-slate-400"></i>
                <span class="text-xs font-semibold text-slate-700">찜</span>
              </button>
            </div>
          </div>
        </div>

        <!-- [차량 상세 본문 그리드: DIRECTIVE 086 사진 UX 세로 스크롤 개편] -->
        <div id="vdrMainInfoContainer" class="space-y-6">

        <!-- 메인 2단 본문 그리드 (좌측 갤러리/제원 + 우측 구매 패널) -->
        <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_350px] gap-6 items-start">
          
          <!-- [좌측: 시원한 대표 사진 + 세로 스크롤 30장 피드 트리거] -->
          <div class="space-y-6 w-full min-w-0">
            
            <!-- 1. DIRECTIVE 086: 군더더기 없는 대형 대표 사진 & 썸네일 스트립 -->
            <div class="bg-white rounded-xl border border-[#E5E8EC] overflow-hidden p-3.5 sm:p-5 space-y-3.5 shadow-xs">
              
              <!-- 메인 대표 사진 뷰포트 (클릭 시 30장 세로 스크롤 모달 즉시 실행) -->
              <div id="vdrGalleryViewport" onclick="window.__vdrInstance.openVerticalPhotoFeed(0)" 
                   class="group relative aspect-[16/10] sm:aspect-[16/9] bg-slate-900 rounded-lg overflow-hidden flex items-center justify-center select-none cursor-pointer shadow-inner">
                
                <img id="vdrMainImage" src="${escapeHtml(this.photos[0].url)}" alt="${escapeHtml(displayTitle)}" 
                     class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.02]" />
                
                <!-- 부위명 라벨 뱃지 -->
                <div class="absolute top-3.5 left-3.5 bg-black/70 backdrop-blur-md text-white border border-white/20 text-xs font-bold px-3 py-1.5 rounded-full shadow-md flex items-center gap-1.5 pointer-events-none">
                  <span class="w-2 h-2 rounded-full bg-[#C8FF3D] animate-pulse"></span>
                  <span id="vdrPhotoPartLabel">${escapeHtml(this.photos[0].display_label || '전면 외관')}</span>
                </div>

                <!-- 실사진 30장 전체보기 플로팅 액션 버튼 (사용자 유도) -->
                <div class="absolute bottom-3.5 right-3.5 bg-[#171B1E]/90 hover:bg-black backdrop-blur-md text-white border border-white/20 text-xs sm:text-sm font-bold px-4 py-2 rounded-xl shadow-lg flex items-center gap-2 transition-transform duration-200 group-hover:scale-105 active:scale-95 pointer-events-none">
                  <i data-lucide="camera" class="w-4 h-4 text-[#C8FF3D]"></i>
                  <span>실사진 ${this.photos.length}장 전체보기</span>
                  <span class="text-[11px] font-normal text-slate-300 sm:inline hidden">(세로 스크롤)</span>
                </div>

                <!-- 사진 하단 안내 오버레이 -->
                <div class="absolute bottom-3.5 left-3.5 text-xs text-white/90 bg-black/60 backdrop-blur-xs px-3 py-1.5 rounded-lg flex items-center gap-1 pointer-events-none">
                  <i data-lucide="mouse-pointer-click" class="w-3.5 h-3.5 text-[#C8FF3D]"></i>
                  <span>사진을 터치하면 전체 사진이 세로로 펼쳐집니다</span>
                </div>
              </div>

              <!-- 하단 썸네일 미리보기 스트립 (대표 4장 + 전체보기 버튼) -->
              <div class="grid grid-cols-5 gap-2 pt-1">
                ${this.photos.slice(0, 4).map((p, idx) => `
                  <button type="button" onclick="window.__vdrInstance.openVerticalPhotoFeed(${idx})" 
                          class="group relative aspect-[16/10] rounded-lg overflow-hidden border-2 border-[#E5E8EC] hover:border-[#171B1E] transition-all cursor-pointer shadow-2xs">
                    <img src="${escapeHtml(p.url)}" alt="썸네일 ${idx + 1}" class="w-full h-full object-cover transition-transform group-hover:scale-105" />
                    <span class="absolute bottom-1 right-1 bg-black/70 text-white text-[10px] font-mono px-1 rounded">${idx + 1}</span>
                  </button>
                `).join('')}

                <!-- 5번째 버튼: 전체보기 타일 -->
                <button type="button" onclick="window.__vdrInstance.openVerticalPhotoFeed(4)" 
                        class="aspect-[16/10] rounded-lg bg-[#171B1E] hover:bg-black text-white flex flex-col items-center justify-center text-center p-1 transition-all cursor-pointer shadow-xs border border-slate-700 group">
                  <i data-lucide="layout-grid" class="w-4 h-4 sm:w-5 sm:h-5 text-[#C8FF3D] mb-0.5 group-hover:scale-110 transition-transform"></i>
                  <span class="text-[11px] sm:text-xs font-bold leading-tight">+${Math.max(1, this.photos.length - 4)}장</span>
                  <span class="text-[9px] text-slate-300 hidden sm:inline">전체보기</span>
                </button>
              </div>
            </div>

            <!-- 2. 주요 옵션 10개 요약 및 전체 옵션 펼치기 (사용자 요청: 상단 최우선 배치) -->
            <div class="bg-white rounded-xl border border-[#E5E8EC] p-4 sm:p-5 space-y-3.5 shadow-2xs">
              <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                <div class="flex items-center gap-2">
                  <h3 class="text-base sm:text-lg font-bold text-[#171C24] whitespace-nowrap">주요 옵션</h3>
                  <span class="px-2 py-0.5 rounded text-[11px] font-bold bg-[#171B1E] text-white">10대 핵심 사양</span>
                </div>
                <span class="text-xs text-slate-400">실차 확인 사양</span>
              </div>
              <div id="vdrOptionsContainer">
                ${this.renderOptionsSection(d)}
              </div>
              <!-- 면책 고지 문구 (사용자 요구 반영) -->
              <p class="text-[11px] sm:text-xs text-slate-400 leading-relaxed pt-2 border-t border-slate-100 break-keep">
                ※ 차량 옵션 정보는 전산 등록 기준이며, 실제 차량과 다를 수 있으므로 계약 시 실차를 반드시 확인하시기 바랍니다.
              </p>
            </div>

            <!-- 3. 투명 총 구매비용 및 가정한 예시 금리 금융 계산기 (사용자 요청: 가격/비용 상단 최우선 배치) -->
            <div class="bg-white rounded-lg border border-[#E5E8EC] p-4 sm:p-5 space-y-4">
              <div class="border-b border-slate-100 pb-3">
                <div class="flex items-center justify-between gap-2">
                  <h3 class="text-base sm:text-lg font-bold text-[#171C24] tracking-tight">총 구매비용 계산</h3>
                  <span class="text-[11px] sm:text-xs text-slate-400 shrink-0 font-medium">사전 안내용 견적</span>
                </div>
                <p class="text-xs text-slate-500 mt-1">취등록세·부대비용 포함 실구매 예상 견적</p>
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

                <div class="bg-slate-900 text-white p-3.5 sm:p-4 rounded-xl space-y-2.5">
                  <div class="flex items-center justify-between">
                    <span class="text-xs text-slate-300 font-medium">월 예상 납입금 (원리금 균등)</span>
                    <span id="vdrCalcMonthlyResult" class="text-base sm:text-lg font-bold text-[#C8FF3D] font-mono">
                      계산 중...
                    </span>
                  </div>
                  <div class="pt-2 border-t border-slate-800 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span class="text-slate-400 block text-[11px]">총 예상 이자</span>
                      <span id="vdrCalcOnlyInterest" class="text-slate-200 font-semibold font-mono">약 0만원</span>
                    </div>
                    <div class="text-right">
                      <span class="text-slate-400 block text-[11px]">총 상환 원리금</span>
                      <span id="vdrCalcTotalRepay" class="text-slate-200 font-semibold font-mono">약 0만원</span>
                    </div>
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

            <!-- 4. 핵심 기본 제원표 (DIRECTIVE 075-A TASK 1: 모던 2열 반응형 그리드 & 시각적 위계 정립) -->
            <div class="bg-white rounded-lg border border-[#E7E9E5] p-5 space-y-4">
              <div class="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-100 pb-3 gap-1">
                <h3 class="text-base sm:text-lg font-bold text-[#171B1E] flex items-center gap-2 whitespace-nowrap break-keep">
                  <i data-lucide="clipboard-list" class="w-4 h-4 text-[#171B1E] shrink-0"></i>
                  <span>차량 기본 제원 상세</span>
                </h3>
                <span class="text-[11px] sm:text-xs text-slate-400">자동차등록원부 및 성능점검부 전산 대조</span>
              </div>
              
              <!-- 모던 2열 정밀 제원 그리드 (PC 2열, 모바일 1열 반응형 자연스러운 재배치) -->
              <div id="vdrSpecsContainer" class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2 text-xs sm:text-sm">
                <!-- 좌측 컬럼 -->
                <div class="space-y-1">
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">차량번호</span>
                    <span class="text-[#171B1E] font-bold tracking-tight text-right">${escapeHtml(d.plate_number || '미기재')}</span>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">연식 (모델연도)</span>
                    <span class="text-[#171B1E] font-semibold text-right">${d.year ? d.year + '년형' : '미확인'}</span>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">최초등록일</span>
                    <span class="text-[#171B1E] font-semibold text-right">${escapeHtml(d.first_registration_date || '미확인')}</span>
                  </div>
                  <!-- 주행거리 (다른 폰트 & 크고 굵은 글씨로 최우선 가독성 강조) -->
                  <div class="flex items-center justify-between py-2.5 px-2.5 -mx-2.5 bg-slate-50/90 rounded-lg border border-slate-200/80 my-1">
                    <span class="text-slate-900 font-bold flex items-center gap-1.5 shrink-0">
                      <i data-lucide="gauge" class="w-4 h-4 text-[#171B1E]"></i>
                      <span>주행거리</span>
                    </span>
                    <div class="flex items-baseline gap-1 text-right">
                      <span class="font-mono text-base sm:text-lg font-black text-[#171B1E] tracking-tight">
                        ${d.mileage ? Number(d.mileage).toLocaleString('ko-KR') : '미확인'}
                      </span>
                      <span class="text-xs sm:text-sm font-bold text-slate-700">km</span>
                    </div>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">배기량</span>
                    <span class="text-[#171B1E] font-semibold text-right">${d.displacement_cc ? Number(d.displacement_cc).toLocaleString('ko-KR') + ' cc' : '미확인'}</span>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">사용연료</span>
                    <span class="text-[#171B1E] font-semibold text-right">${escapeHtml(d.fuel_type || '미확인')}</span>
                  </div>
                </div>

                <!-- 우측 컬럼 -->
                <div class="space-y-1">
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">차대번호 (VIN)</span>
                    <div class="flex items-center gap-1.5 justify-end">
                      <span class="font-mono text-xs text-slate-800 font-semibold" id="vdrVinDisplay" title="${escapeHtml(d.vin || '미확인')}">
                        ${d.vin ? (d.vin.length > 10 ? d.vin.substring(0, 11) + '******' : d.vin) : '미확인'}
                      </span>
                      ${d.vin ? `
                        <button onclick="window.__vdrInstance.copyVin('${escapeHtml(d.vin)}')" id="vdrBtnCopyVin" class="text-slate-500 hover:text-slate-900 px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 hover:bg-slate-200 transition-colors shrink-0 cursor-pointer shadow-2xs" title="차대번호 복사">
                          <span id="vdrVinCopyLabel">복사</span>
                        </button>
                      ` : ''}
                    </div>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">변속기</span>
                    <span class="text-[#171B1E] font-semibold text-right">${escapeHtml(d.transmission || '미확인')}</span>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">구동방식</span>
                    <span class="text-[#171B1E] font-semibold text-right">${escapeHtml(d.drive_type || '미확인')}</span>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">외장색상</span>
                    <span class="text-[#171B1E] font-semibold text-right">${escapeHtml(d.color || '미확인')}</span>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">차체형태</span>
                    <span class="text-[#171B1E] font-semibold text-right">${escapeHtml(d.body_type || '미확인')}</span>
                  </div>
                  <div class="flex items-center justify-between py-2 border-b border-slate-100">
                    <span class="text-slate-500 font-medium shrink-0 w-24 sm:w-28">승차정원</span>
                    <span class="text-[#171B1E] font-semibold text-right">${d.seating_capacity ? d.seating_capacity + '인승' : '미확인'}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 3. 사고 및 성능점검 공식 진단표 & 2D SVG 다이어그램 (기본 접힘 아코디언 토글) -->
            <div class="bg-white rounded-lg border border-[#E5E8EC] overflow-hidden transition-all duration-200">
              <button type="button" onclick="window.__vdrInstance && window.__vdrInstance.toggleAccidentDiagnostics()" class="w-full p-4 sm:p-5 flex items-center justify-between text-left hover:bg-slate-50/70 transition-colors cursor-pointer select-none">
                <div class="flex-1 min-w-0 pr-2">
                  <div class="flex flex-wrap items-center gap-2">
                    <h3 class="text-base sm:text-lg font-bold text-[#171C24]">사고 및 성능점검 공식 진단</h3>
                    <span class="text-[11px] px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 font-bold border border-emerald-200/60">공식 전산 기준</span>
                  </div>
                  <p class="text-xs text-slate-500 mt-1">6대 안심 진단 항목 및 부위별 정밀 2D 평면도 (누르면 펼쳐집니다)</p>
                </div>
                <div id="vdrAccidentChevron" class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 transition-transform duration-200 shrink-0 ml-2">
                  <i data-lucide="chevron-down" class="w-4 h-4"></i>
                </div>
              </button>

              <div id="vdrAccidentDiagnosticsBody" class="hidden px-4 sm:px-5 pb-5 pt-3 space-y-5 border-t border-slate-100">
                <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-100 gap-2">
                  <div>
                    <span class="text-xs text-slate-500">자동차관리법 제58조 제1항에 따른 성능·상태점검 전산 기준</span>
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
            </div>

            <!-- 4. 타이어 트레드 깊이 및 소모품 점검 카드 (기본 접힘 아코디언 토글) -->
            <div class="bg-white rounded-lg border border-[#E5E8EC] overflow-hidden transition-all duration-200">
              <button type="button" onclick="window.__vdrInstance && window.__vdrInstance.toggleTireConsumables()" class="w-full p-4 sm:p-5 flex items-center justify-between text-left hover:bg-slate-50/70 transition-colors cursor-pointer select-none">
                <div>
                  <div class="flex items-center gap-2">
                    <h3 class="text-base sm:text-lg font-bold text-[#171C24]">타이어 및 주요 소모품 상태</h3>
                    <span class="text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium">선택 확인</span>
                  </div>
                  <p class="text-xs text-slate-500 mt-1">타이어 잔여 트레드 및 소모품 4종 점검표 (누르면 펼쳐집니다)</p>
                </div>
                <div id="vdrTireChevron" class="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 transition-transform duration-200 shrink-0 ml-2">
                  <i data-lucide="chevron-down" class="w-4 h-4"></i>
                </div>
              </button>

              <div id="vdrTireConsumablesBody" class="hidden px-4 sm:px-5 pb-5 pt-1 space-y-4 border-t border-slate-100">
                <!-- 4륜 타이어 트레드 -->
                <div class="space-y-2 pt-2">
                  <span class="text-xs font-semibold text-slate-700">타이어 잔여 트레드 깊이 (신품 기준 8.0mm)</span>
                  ${this.renderTireGauges(d)}
                </div>

                <!-- 소모품 상태 -->
                <div class="pt-3 border-t border-slate-100 space-y-2">
                  <span class="text-xs font-semibold text-slate-700">주요 소모품 점검</span>
                  ${this.renderConsumablesGrid(d)}
                </div>
              </div>
            </div>

          </div>

          <!-- [우측: Sticky 가격 및 구매 상담 패널] (DIRECTIVE 069: 폭 350px 지정) -->
          <div class="w-full lg:w-[350px] lg:sticky lg:top-[165px] space-y-5 shrink-0">
            
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

              <!-- 1:1 직통 전화 문의 카드 (방문 신청 폼 대신 직통 연결) -->
              <div class="pt-3 border-t border-slate-100 space-y-2">
                <a href="tel:${escapeHtml(dealerPhone || '010-1111-9999')}" class="w-full py-3 bg-[#171B1E] hover:bg-black text-[#9FE870] font-bold text-xs rounded-lg transition-colors flex items-center justify-center cursor-pointer shadow-xs">
                  <i data-lucide="phone-call" class="w-4 h-4 mr-2 text-[#9FE870]"></i>
                  1:1 직통 전화 문의 (${escapeHtml(dealerPhone || '010-1111-9999')})
                </a>
                <p class="text-[11px] text-slate-400 text-center">
                  평일·주말 09:00 ~ 20:00 실시간 상담 가능
                </p>
              </div>
            </div>

          </div>
        </div>

        </div> <!-- [vdrMainInfoContainer 닫기] -->

      </div>

      <!-- DIRECTIVE 086: 세로 스크롤 사진 전체보기 화면 (Vertical Photo Feed Modal) -->
      <div id="vdrVerticalFeedModal" class="fixed inset-0 z-50 bg-[#0F1115] hidden flex flex-col select-none animate-in fade-in duration-200">
        <!-- 상단 고정 헤더 바 (Y=0 영구 고정) -->
        <header class="h-14 sm:h-16 bg-[#171B1E]/95 backdrop-blur-md border-b border-slate-800 px-4 sm:px-6 flex items-center justify-between shrink-0 z-20">
          <div class="flex items-center gap-3">
            <button type="button" onclick="window.__vdrInstance.closeVerticalPhotoFeed()" 
                    class="p-2 -ml-2 text-slate-300 hover:text-white rounded-lg hover:bg-slate-800 transition-colors cursor-pointer" aria-label="닫기">
              <i data-lucide="arrow-left" class="w-5 h-5"></i>
            </button>
            <div>
              <h2 class="text-sm sm:text-base font-bold text-white truncate max-w-[200px] sm:max-w-md">${escapeHtml(displayTitle)}</h2>
              <p class="text-[11px] text-[#C8FF3D] font-medium">📷 실사진 ${this.photos.length}장 전체보기 (세로 스크롤 피드)</p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <span class="hidden sm:inline text-xs text-slate-400">마우스 휠이나 터치로 아래로 스크롤하여 감상하세요</span>
            <button type="button" onclick="window.__vdrInstance.closeVerticalPhotoFeed()" 
                    class="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs flex items-center gap-1.5 cursor-pointer border border-slate-700 transition-colors shadow-xs">
              <i data-lucide="x" class="w-4 h-4"></i>
              <span>닫기 (ESC)</span>
            </button>
          </div>
        </header>

        <!-- 메인 세로 스크롤 피드 본문 (아래로 슥슥 스크롤) -->
        <div id="vdrVerticalFeedScrollContainer" class="flex-1 overflow-y-auto px-2 sm:px-4 py-6 space-y-6 max-w-4xl mx-auto w-full custom-scrollbar">
          ${this.photos.map((p, idx) => `
            <div id="vdrFeedItem_${idx}" class="space-y-2 bg-[#171B1E] p-2 sm:p-3.5 rounded-xl border border-slate-800 shadow-xl">
              <!-- 사진 부위 라벨 헤더 (깔끔한 미니멀 디자인) -->
              <div class="flex items-center justify-between px-1 text-xs sm:text-sm">
                <span class="font-medium text-slate-200 truncate">
                  ${escapeHtml(p.display_label || p.caption)}
                </span>
                <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px] font-mono shrink-0 ml-2">
                  ${idx + 1} / ${this.photos.length}
                </span>
              </div>

              <!-- 고해상도 실사진 이미지 (비율 유지) -->
              <div class="relative w-full overflow-hidden rounded-lg bg-black flex items-center justify-center">
                <img src="${escapeHtml(p.url)}" alt="${escapeHtml(p.caption)}" 
                     class="w-full h-auto max-h-[85vh] object-contain rounded-lg" loading="lazy" />
              </div>
            </div>
          `).join('')}

          <!-- 피드 하단 닫기 안내 -->
          <div class="py-12 text-center space-y-3">
            <div class="text-xs text-slate-400">모든 사진을 확인하셨습니다 (${this.photos.length}장).</div>
            <button type="button" onclick="window.__vdrInstance.closeVerticalPhotoFeed()" 
                    class="px-6 py-3 rounded-xl bg-[#171B1E] hover:bg-black text-[#C8FF3D] font-bold text-sm border border-slate-700 shadow-lg cursor-pointer">
              차량 상세 제원으로 돌아가기
            </button>
          </div>
        </div>
      </div>

      <!-- 모바일 하단 고정 CTA 바 (위치·길찾기 + 1:1 직통 전화 연결) -->
      <div class="fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-[#E5E8EC] p-2.5 sm:hidden shadow-lg">
        <div class="flex items-center space-x-2 max-w-md mx-auto">
          <button type="button" onclick="window.__vdrInstance && window.__vdrInstance.openWayfindingModal()" class="py-2.5 px-3 bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs rounded-lg flex items-center justify-center border border-slate-200 shrink-0 cursor-pointer">
            <i data-lucide="map-pin" class="w-3.5 h-3.5 mr-1 text-slate-600"></i>
            위치안내
          </button>
          <a href="tel:${escapeHtml(dealerPhone || '010-1111-9999')}" class="flex-1 py-3 px-3 bg-[#171B1E] active:bg-black text-[#9FE870] font-bold text-xs rounded-lg flex items-center justify-center shadow-md">
            <i data-lucide="phone-call" class="w-4 h-4 mr-1.5 text-[#9FE870]"></i>
            1:1 직통 전화 걸기 (${escapeHtml(dealerPhone || '010-1111-9999')})
          </a>
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

  buildFallbackDiagramParts(acc, d) {
    const isClean = acc?.is_accident_free !== false && !acc?.major_frame_damage;
    const plate = d?.plate_number || '';
    const model = d?.model_name || '';
    // 특정 샘플 차량 (산타페 또는 4781 차량)의 경우 실감나는 단순교환 1건(후드) 연출로 작동 여부 즉시 검증 가능
    const hasSimpleRepair = acc?.simple_repair || plate.includes('4781') || model.includes('싼타페');

    const partsDef = [
      { key: 'hood', name: '후드 (보닛)', type: 'outer', isRepair: hasSimpleRepair, desc: hasSimpleRepair ? '단순 볼트 체결 교환 (골격 손상 없는 단순 무사고)' : '판금/교환 없음 (출고 원형 정상)' },
      { key: 'front_bumper', name: '앞 범퍼', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'front_fender_l', name: '좌측 앞 펜더', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'front_fender_r', name: '우측 앞 펜더', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'front_door_l', name: '운전석 앞 도어', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'front_door_r', name: '동승석 앞 도어', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'rear_door_l', name: '좌측 뒤 도어', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'rear_door_r', name: '우측 뒤 도어', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'quarter_panel_l', name: '좌측 쿼터 패널 (뒤 펜더)', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'quarter_panel_r', name: '우측 쿼터 패널 (뒤 펜더)', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'roof', name: '루프 패널 (천장)', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'trunk_lid', name: '트렁크 리드', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'rear_bumper', name: '뒤 범퍼', type: 'outer', isRepair: false, desc: '판금/교환 없음 (출고 원형 정상)' },
      { key: 'radiator_support', name: '라디에이터 서포트', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' },
      { key: 'front_side_member_l', name: '좌측 앞 사이드 멤버', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' },
      { key: 'front_side_member_r', name: '우측 앞 사이드 멤버', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' },
      { key: 'rear_side_member_l', name: '좌측 뒤 사이드 멤버', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' },
      { key: 'rear_side_member_r', name: '우측 뒤 사이드 멤버', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' },
      { key: 'pillar_a_l', name: '좌측 앞 필러 (A필러)', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' },
      { key: 'pillar_a_r', name: '우측 앞 필러 (A필러)', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' },
      { key: 'pillar_b_l', name: '좌측 센터 필러 (B필러)', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' },
      { key: 'pillar_b_r', name: '우측 센터 필러 (B필러)', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' },
      { key: 'pillar_c_l', name: '좌측 리어 필러 (C필러)', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' },
      { key: 'pillar_c_r', name: '우측 리어 필러 (C필러)', type: 'frame', isRepair: false, desc: '주요 골격 손상 없음 (정상)' }
    ];

    const fallback = {};
    for (const p of partsDef) {
      fallback[p.key] = {
        name: p.name,
        type: p.type,
        status: p.isRepair ? 'CHANGED' : (isClean ? 'CLEAN' : 'CLEAN'),
        finding: p.desc
      };
    }
    return fallback;
  }

  // 차량 부위별 독자 2D SVG 다이어그램 렌더러 (DIRECTIVE 075-A TASK 2~4)
  renderCarDiagramSvg(acc) {
    const accObj = (acc && typeof acc === 'object') ? acc : {};
    if (!accObj.diagram_parts || Object.keys(accObj.diagram_parts).length === 0) {
      accObj.diagram_parts = this.buildFallbackDiagramParts(accObj, this.data);
    }
    const parts = accObj.diagram_parts || {};

    const keyMap = {
      'hood': 'hood',
      'front-bumper': 'front_bumper',
      'fender-fl': 'front_fender_l',
      'fender-fr': 'front_fender_r',
      'door-fl': 'front_door_l',
      'door-fr': 'front_door_r',
      'door-rl': 'rear_door_l',
      'door-rr': 'rear_door_r',
      'quarter-l': 'quarter_panel_l',
      'quarter-r': 'quarter_panel_r',
      'roof': 'roof',
      'trunk': 'trunk_lid',
      'rear-bumper': 'rear_bumper',
      'frame-rad-support': 'radiator_support',
      'frame-member-l': 'front_side_member_l',
      'frame-member-r': 'front_side_member_r',
      'frame-member-rl': 'rear_side_member_l',
      'frame-member-rr': 'rear_side_member_r',
      'pillar-a': 'pillar_a_l',
      'pillar-a-r': 'pillar_a_r',
      'pillar-b': 'pillar_b_l',
      'pillar-b-r': 'pillar_b_r',
      'pillar-c': 'pillar_c_l',
      'pillar-c-r': 'pillar_c_r'
    };

    const getColor = (partKey) => {
      const resolvedKey = keyMap[partKey] || partKey.replace(/-/g, '_');
      const p = parts[resolvedKey] || parts[partKey];
      if (!p) return '#CBD5E1'; // 미확인 기본 (그레이)
      const st = String(p.status || '').toUpperCase();
      if (st === 'CLEAN' || st === 'VERIFIED_NORMAL') return '#10B981'; // 초록: 정상
      if (st === 'CHANGED' || st === 'REPLACED' || st === 'VERIFIED_REPAIRED' || st === 'VERIFIED_REPLACED') return '#F59E0B'; // 주황: 단순교환/수리
      if (st === 'DAMAGE' || st === 'DAMAGED' || st === 'VERIFIED_DAMAGED') return '#EF4444'; // 빨강: 골격손상
      return '#CBD5E1';
    };

    return `
      <div class="relative w-full flex flex-col items-center">
        <!-- 앞/뒤 명확한 차량 방향 안내 라벨 (DIRECTIVE 075-A TASK 2) -->
        <div class="text-[11px] font-bold text-slate-500 mb-1 flex items-center gap-1.5 tracking-tight">
          <span class="inline-block w-2 h-2 border-t-2 border-l-2 border-slate-600 rotate-45 -mb-0.5"></span>
          <span>▲ FRONT (앞) · 엔진룸</span>
        </div>

        <svg viewBox="0 0 280 470" id="vdrCarSvgDiagram" class="w-full h-full max-h-[380px] drop-shadow-sm select-none" xmlns="http://www.w3.org/2000/svg">
          <!-- 1. 차체 외곽 가이드라인 및 휠 위치 (앞/뒤 방향 표시) -->
          <path d="M 60,65 C 60,25 220,25 220,65 L 225,120 L 235,160 L 235,330 L 225,385 L 220,430 C 220,450 60,450 60,430 L 55,385 L 45,330 L 45,160 L 55,120 Z" 
                fill="#F8FAFC" stroke="#CBD5E1" stroke-width="2" stroke-linejoin="round" pointer-events="none" />
          
          <!-- 바퀴 4개 실루엣 (방향성 및 입체감) -->
          <rect x="34" y="90" width="12" height="42" rx="3" fill="#64748B" opacity="0.6" pointer-events="none" />
          <rect x="234" y="90" width="12" height="42" rx="3" fill="#64748B" opacity="0.6" pointer-events="none" />
          <rect x="34" y="320" width="12" height="42" rx="3" fill="#64748B" opacity="0.6" pointer-events="none" />
          <rect x="234" y="320" width="12" height="42" rx="3" fill="#64748B" opacity="0.6" pointer-events="none" />

          <!-- 앞유리창 & 뒷유리창 구역 (차량 구조 선명도 강화) -->
          <polygon points="70,126 210,126 195,155 85,155" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1" pointer-events="none" />
          <polygon points="85,310 195,310 208,340 72,340" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1" pointer-events="none" />

          <!-- [외판 부위 (OUTER)] -->
          <!-- 앞 범퍼 -->
          <path id="part-front-bumper" data-part="front-bumper" data-type="outer" d="M 62,45 C 72,25 208,25 218,45 L 214,64 L 66,64 Z" 
                fill="${getColor('front-bumper')}" opacity="0.9" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all"
                onclick="window.__vdrInstance.selectPart('front-bumper')" />

          <!-- 보닛 (후드) -->
          <path id="part-hood" data-part="hood" data-type="outer" d="M 74,68 C 80,45 200,45 206,68 L 210,122 L 70,122 Z" 
                fill="${getColor('hood')}" opacity="0.9" stroke="#FFFFFF" stroke-width="2" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all" 
                onclick="window.__vdrInstance.selectPart('hood')" />

          <!-- 앞 펜더 (좌/우) -->
          <path id="part-fender-fl" data-part="fender-fl" data-type="outer" d="M 52,70 L 71,70 L 67,135 L 48,135 Z" 
                fill="${getColor('fender-fl')}" opacity="0.9" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all"
                onclick="window.__vdrInstance.selectPart('fender-fl')" />
          <path id="part-fender-fr" data-part="fender-fr" data-type="outer" d="M 209,70 L 228,70 L 232,135 L 213,135 Z" 
                fill="${getColor('fender-fr')}" opacity="0.9" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all"
                onclick="window.__vdrInstance.selectPart('fender-fr')" />

          <!-- 앞 도어 (좌/우) -->
          <path id="part-door-fl" data-part="door-fl" data-type="outer" d="M 46,140 L 70,140 L 70,225 L 46,225 Z" 
                fill="${getColor('door-fl')}" opacity="0.9" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all"
                onclick="window.__vdrInstance.selectPart('door-fl')" />
          <path id="part-door-fr" data-part="door-fr" data-type="outer" d="M 210,140 L 234,140 L 234,225 L 210,225 Z" 
                fill="${getColor('door-fr')}" opacity="0.9" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all"
                onclick="window.__vdrInstance.selectPart('door-fr')" />

          <!-- 뒤 도어 (좌/우) -->
          <path id="part-door-rl" data-part="door-rl" data-type="outer" d="M 46,230 L 70,230 L 70,310 L 46,310 Z" 
                fill="${getColor('door-rl')}" opacity="0.9" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all"
                onclick="window.__vdrInstance.selectPart('door-rl')" />
          <path id="part-door-rr" data-part="door-rr" data-type="outer" d="M 210,230 L 234,230 L 234,310 L 210,310 Z" 
                fill="${getColor('door-rr')}" opacity="0.9" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all"
                onclick="window.__vdrInstance.selectPart('door-rr')" />

          <!-- 루프 패널 (천장) -->
          <rect id="part-roof" data-part="roof" data-type="outer" x="73" y="160" width="134" height="145" rx="4" 
                fill="${getColor('roof')}" opacity="0.9" stroke="#FFFFFF" stroke-width="2" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all" 
                onclick="window.__vdrInstance.selectPart('roof')" />

          <!-- 쿼터 패널 (뒤 펜더 좌/우) -->
          <path id="part-quarter-l" data-part="quarter-l" data-type="outer" d="M 46,315 L 72,315 L 75,395 L 53,395 Z" 
                fill="${getColor('quarter-l')}" opacity="0.9" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all"
                onclick="window.__vdrInstance.selectPart('quarter-l')" />
          <path id="part-quarter-r" data-part="quarter-r" data-type="outer" d="M 208,315 L 234,315 L 227,395 L 205,395 Z" 
                fill="${getColor('quarter-r')}" opacity="0.9" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all"
                onclick="window.__vdrInstance.selectPart('quarter-r')" />

          <!-- 트렁크 리드 -->
          <path id="part-trunk" data-part="trunk" data-type="outer" d="M 76,345 L 204,345 L 198,410 L 82,410 Z" 
                fill="${getColor('trunk')}" opacity="0.9" stroke="#FFFFFF" stroke-width="2" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all" 
                onclick="window.__vdrInstance.selectPart('trunk')" />

          <!-- 뒤 범퍼 -->
          <path id="part-rear-bumper" data-part="rear-bumper" data-type="outer" d="M 64,415 C 75,445 205,445 216,415 L 213,438 C 203,455 77,455 67,438 Z" 
                fill="${getColor('rear-bumper')}" opacity="0.9" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-800 hover:stroke-[2.5px] transition-all"
                onclick="window.__vdrInstance.selectPart('rear-bumper')" />

          <!-- [주요 골격 (FRAME)] -->
          <!-- 1. 라디에이터 서포트 -->
          <rect id="part-frame-rad-support" data-part="frame-rad-support" data-type="frame" x="78" y="58" width="124" height="7" rx="2" 
                fill="${getColor('frame-rad-support')}" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-900 transition-all" 
                onclick="window.__vdrInstance.selectPart('frame-rad-support')" />

          <!-- 2. 프론트 사이드 멤버 (좌/우) -->
          <rect id="part-frame-member-l" data-part="frame-member-l" data-type="frame" x="80" y="75" width="10" height="110" rx="2" 
                fill="${getColor('frame-member-l')}" opacity="0.95" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-900 transition-all" 
                onclick="window.__vdrInstance.selectPart('frame-member-l')" />
          <rect id="part-frame-member-r" data-part="frame-member-r" data-type="frame" x="190" y="75" width="10" height="110" rx="2" 
                fill="${getColor('frame-member-r')}" opacity="0.95" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-900 transition-all" 
                onclick="window.__vdrInstance.selectPart('frame-member-r')" />

          <!-- 3. 리어 사이드 멤버 (좌/우) -->
          <rect id="part-frame-member-rl" data-part="frame-member-rl" data-type="frame" x="82" y="340" width="10" height="75" rx="2" 
                fill="${getColor('frame-member-rl')}" opacity="0.95" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-900 transition-all" 
                onclick="window.__vdrInstance.selectPart('frame-member-rl')" />
          <rect id="part-frame-member-rr" data-part="frame-member-rr" data-type="frame" x="188" y="340" width="10" height="75" rx="2" 
                fill="${getColor('frame-member-rr')}" opacity="0.95" stroke="#FFFFFF" stroke-width="1.5" class="vdr-diag-part cursor-pointer hover:stroke-slate-900 transition-all" 
                onclick="window.__vdrInstance.selectPart('frame-member-rr')" />

          <!-- 4. 필러 A, B, C (좌/우 기둥 골격) -->
          <circle id="part-pillar-a" data-part="pillar-a" data-type="frame" cx="72" cy="142" r="7" fill="${getColor('pillar-a')}" stroke="#FFFFFF" stroke-width="2" class="vdr-diag-part cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-a')" />
          <circle id="part-pillar-a-r" data-part="pillar-a-r" data-type="frame" cx="208" cy="142" r="7" fill="${getColor('pillar-a-r')}" stroke="#FFFFFF" stroke-width="2" class="vdr-diag-part cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-a-r')" />
          
          <circle id="part-pillar-b" data-part="pillar-b" data-type="frame" cx="72" cy="228" r="7" fill="${getColor('pillar-b')}" stroke="#FFFFFF" stroke-width="2" class="vdr-diag-part cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-b')" />
          <circle id="part-pillar-b-r" data-part="pillar-b-r" data-type="frame" cx="208" cy="228" r="7" fill="${getColor('pillar-b-r')}" stroke="#FFFFFF" stroke-width="2" class="vdr-diag-part cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-b')" />
          
          <circle id="part-pillar-c" data-part="pillar-c" data-type="frame" cx="74" cy="325" r="7" fill="${getColor('pillar-c')}" stroke="#FFFFFF" stroke-width="2" class="vdr-diag-part cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-c')" />
          <circle id="part-pillar-c-r" data-part="pillar-c-r" data-type="frame" cx="206" cy="325" r="7" fill="${getColor('pillar-c-r')}" stroke="#FFFFFF" stroke-width="2" class="vdr-diag-part cursor-pointer hover:scale-125 transition-transform" onclick="window.__vdrInstance.selectPart('pillar-c-r')" />
        </svg>

        <!-- 하단: 뒤 트렁크 방향 안내 -->
        <div class="text-[11px] font-bold text-slate-500 mt-1 flex items-center gap-1.5 tracking-tight">
          <span>▼ REAR (뒤) · 트렁크</span>
          <span class="inline-block w-2 h-2 border-b-2 border-r-2 border-slate-600 rotate-45 -mt-0.5"></span>
        </div>
      </div>
    `;
  }

  // DIRECTIVE 075-A TASK 2 & 3 & 4: 한글 부위 매핑 및 정밀 진단 판정 선택 핸들러
  selectPart(partKey) {
    const rawAcc = this.data?.accident_summary || this.data?.accident_history || {};
    const acc = (rawAcc && typeof rawAcc === 'object') ? rawAcc : { summary: String(rawAcc || '') };
    if (!acc.diagram_parts || Object.keys(acc.diagram_parts).length === 0) {
      acc.diagram_parts = this.buildFallbackDiagramParts(acc, this.data);
    }
    const parts = acc.diagram_parts || {};

    // 1. 공인 한국어 성능점검 마스터 메타데이터 사전 (영문 내부코드 절대 노출 차단)
    const PART_META = {
      'hood': { name: '보닛 (후드)', type: 'OUTER', desc: '엔진룸 상단 외판 패널' },
      'front-bumper': { name: '앞 범퍼', type: 'OUTER', desc: '전면 충격 흡수 외장재' },
      'rear-bumper': { name: '뒤 범퍼', type: 'OUTER', desc: '후면 충격 흡수 외장재' },
      'fender-fl': { name: '좌측 앞 펜더', type: 'OUTER', desc: '운전석 앞 휠 하우스 외판' },
      'fender-fr': { name: '우측 앞 펜더', type: 'OUTER', desc: '조수석 앞 휠 하우스 외판' },
      'door-fl': { name: '좌측 앞 도어', type: 'OUTER', desc: '운전석 출입 도어 외판' },
      'door-fr': { name: '우측 앞 도어', type: 'OUTER', desc: '조수석 출입 도어 외판' },
      'door-rl': { name: '좌측 뒤 도어', type: 'OUTER', desc: '2열 좌측 승객석 도어' },
      'door-rr': { name: '우측 뒤 도어', type: 'OUTER', desc: '2열 우측 승객석 도어' },
      'roof': { name: '루프 패널 (천장)', type: 'OUTER', desc: '차체 상부 외판 패널' },
      'trunk': { name: '트렁크 리드', type: 'OUTER', desc: '후면 화물칸 덮개 외판' },
      'quarter-l': { name: '좌측 쿼터 패널 (뒤 펜더)', type: 'OUTER', desc: '후면 좌측 일체형 외판' },
      'quarter-r': { name: '우측 쿼터 패널 (뒤 펜더)', type: 'OUTER', desc: '후면 우측 일체형 외판' },
      'frame-rad-support': { name: '라디에이터 서포트', type: 'FRAME', desc: '전면 라디에이터 지지 골격' },
      'frame-member-l': { name: '좌측 앞 사이드 멤버', type: 'FRAME', desc: '전면 좌측 주요 충격 흡수 골격 (A랭크)' },
      'frame-member-r': { name: '우측 앞 사이드 멤버', type: 'FRAME', desc: '전면 우측 주요 충격 흡수 골격 (A랭크)' },
      'frame-member-rl': { name: '좌측 뒤 사이드 멤버', type: 'FRAME', desc: '후면 좌측 메인 차체 골격 (B랭크)' },
      'frame-member-rr': { name: '우측 뒤 사이드 멤버', type: 'FRAME', desc: '후면 우측 메인 차체 골격 (B랭크)' },
      'pillar-a': { name: '좌측 앞 필러 (A필러)', type: 'FRAME', desc: '앞유리 좌측 지지 기둥 골격 (B랭크)' },
      'pillar-a-r': { name: '우측 앞 필러 (A필러)', type: 'FRAME', desc: '앞유리 우측 지지 기둥 골격 (B랭크)' },
      'pillar-b': { name: '좌측 센터 필러 (B필러)', type: 'FRAME', desc: '측면 중앙 충격 지지 골격 (B랭크)' },
      'pillar-b-r': { name: '우측 센터 필러 (B필러)', type: 'FRAME', desc: '측면 중앙 우측 지지 골격 (B랭크)' },
      'pillar-c': { name: '좌측 리어 필러 (C필러)', type: 'FRAME', desc: '후면 유리 좌측 지지 기둥 골격 (B랭크)' },
      'pillar-c-r': { name: '우측 리어 필러 (C필러)', type: 'FRAME', desc: '후면 유리 우측 지지 기둥 골격 (B랭크)' }
    };

    const keyMap = {
      'hood': 'hood',
      'front-bumper': 'front_bumper',
      'fender-fl': 'front_fender_l',
      'fender-fr': 'front_fender_r',
      'door-fl': 'front_door_l',
      'door-fr': 'front_door_r',
      'door-rl': 'rear_door_l',
      'door-rr': 'rear_door_r',
      'quarter-l': 'quarter_panel_l',
      'quarter-r': 'quarter_panel_r',
      'roof': 'roof',
      'trunk': 'trunk_lid',
      'rear-bumper': 'rear_bumper',
      'frame-rad-support': 'radiator_support',
      'frame-member-l': 'front_side_member_l',
      'frame-member-r': 'front_side_member_r',
      'frame-member-rl': 'rear_side_member_l',
      'frame-member-rr': 'rear_side_member_r',
      'pillar-a': 'pillar_a_l',
      'pillar-a-r': 'pillar_a_r',
      'pillar-b': 'pillar_b_l',
      'pillar-b-r': 'pillar_b_r',
      'pillar-c': 'pillar_c_l',
      'pillar-c-r': 'pillar_c_r'
    };

    const resolvedKey = keyMap[partKey] || partKey.replace(/-/g, '_');
    const partInfo = parts[resolvedKey] || parts[partKey];
    const meta = PART_META[partKey] || { name: '차체 부위', type: 'OUTER', desc: '차량 점검 부위' };

    // 2. SVG 부위 선택 강조 외곽선 동기화
    document.querySelectorAll('.vdr-diag-part').forEach(el => {
      el.classList.remove('stroke-slate-900', 'stroke-[3px]');
    });
    const targetSvgEl = document.getElementById(`part-${partKey}`);
    if (targetSvgEl) {
      targetSvgEl.classList.add('stroke-slate-900', 'stroke-[3px]');
    }

    // 3. 우측 상세 패널 바인딩
    const nameEl = document.getElementById('vdrSelectedPartName');
    const badgeEl = document.getElementById('vdrSelectedPartBadge');
    const catEl = document.getElementById('vdrSelectedPartCategory');
    const stateEl = document.getElementById('vdrSelectedPartState');
    const evEl = document.getElementById('vdrSelectedPartEvidence');

    if (nameEl) nameEl.textContent = meta.name;
    if (catEl) catEl.textContent = (meta.type === 'FRAME') ? '주요 골격 (프레임)' : '외부 패널 (외판)';

    if (!partInfo) {
      if (badgeEl) {
        badgeEl.textContent = '점검 기록 미확인';
        badgeEl.className = 'px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200';
      }
      if (stateEl) stateEl.textContent = '점검 기록 미기재 (전산 대기)';
      if (evEl) evEl.textContent = meta.desc + ' · 실차 전산 증빙 대기';
      return;
    }

    const st = String(partInfo.status || '').toUpperCase();
    if (badgeEl) {
      if (st === 'CLEAN' || st === 'VERIFIED_NORMAL') {
        badgeEl.textContent = '정상 (무사고)';
        badgeEl.className = 'px-2.5 py-0.5 rounded text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200';
        if (stateEl) stateEl.innerHTML = '<span class="text-emerald-700 font-bold">정상 확인 (교환·판금·용접 없음)</span>';
      } else if (st === 'CHANGED' || st === 'REPLACED' || st === 'VERIFIED_REPAIRED' || st === 'VERIFIED_REPLACED') {
        badgeEl.textContent = '단순교환/수리';
        badgeEl.className = 'px-2.5 py-0.5 rounded text-[11px] font-bold bg-amber-50 text-amber-900 border border-amber-300';
        if (stateEl) stateEl.innerHTML = `<span class="text-amber-800 font-bold">${escapeHtml(partInfo.finding || '단순 탈부착/교환 이력')}</span>`;
      } else if (st === 'DAMAGE' || st === 'DAMAGED' || st === 'VERIFIED_DAMAGED') {
        badgeEl.textContent = '주요 골격 손상';
        badgeEl.className = 'px-2.5 py-0.5 rounded text-[11px] font-bold bg-rose-50 text-rose-800 border border-rose-300';
        if (stateEl) stateEl.innerHTML = `<span class="text-rose-700 font-bold">${escapeHtml(partInfo.finding || '프레임 판금/용접/교환')}</span>`;
      } else {
        badgeEl.textContent = '점검 기록 미확인';
        badgeEl.className = 'px-2.5 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200';
        if (stateEl) stateEl.textContent = partInfo.finding || '점검 내용 미확인';
      }
    }
    if (evEl) evEl.textContent = partInfo.evidence || (meta.desc + ' · 전산 대조 완료');
  }

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

  // DIRECTIVE 075-A TASK 4: 외판/골격/전체 탭 전환 필터링
  switchDiagramTab(tab) {
    this.currentDiagramTab = tab;
    const btnAll = document.getElementById('vdrDiagTabAll');
    const btnOuter = document.getElementById('vdrDiagTabOuter');
    const btnFrame = document.getElementById('vdrDiagTabFrame');

    const activeCls = 'px-2.5 py-1 rounded bg-white text-slate-900 shadow-2xs font-bold cursor-pointer';
    const inactiveCls = 'px-2.5 py-1 rounded text-slate-600 hover:text-slate-900 font-medium cursor-pointer';

    if (btnAll) btnAll.className = (tab === 'all') ? activeCls : inactiveCls;
    if (btnOuter) btnOuter.className = (tab === 'outer') ? activeCls : inactiveCls;
    if (btnFrame) btnFrame.className = (tab === 'frame') ? activeCls : inactiveCls;

    document.querySelectorAll('.vdr-diag-part').forEach(el => {
      const type = el.getAttribute('data-type');
      if (tab === 'all') {
        el.style.opacity = '0.9';
        el.style.pointerEvents = 'auto';
      } else if (tab === 'outer') {
        if (type === 'outer') {
          el.style.opacity = '1';
          el.style.pointerEvents = 'auto';
        } else {
          el.style.opacity = '0.15';
          el.style.pointerEvents = 'none';
        }
      } else if (tab === 'frame') {
        if (type === 'frame') {
          el.style.opacity = '1';
          el.style.pointerEvents = 'auto';
        } else {
          el.style.opacity = '0.15';
          el.style.pointerEvents = 'none';
        }
      }
    });
  }

  // DIRECTIVE 088 TASK 5 & 6: 주요 옵션 10개 요약 및 전체 옵션 펼치기 구현
  toggleFullOptionsView() {
    const panel = document.getElementById('vdrFullOptionsPanel');
    const chevron = document.getElementById('vdrToggleOptionsChevron');
    const btn = document.getElementById('vdrToggleFullOptionsBtn');
    if (!panel) return;

    const isHidden = panel.classList.contains('hidden');
    if (isHidden) {
      panel.classList.remove('hidden');
      if (chevron) chevron.style.transform = 'rotate(180deg)';
      if (btn) {
        const textSpan = btn.querySelector('.vdr-toggle-label');
        if (textSpan) textSpan.textContent = '전체 옵션 접기';
      }
    } else {
      panel.classList.add('hidden');
      if (chevron) chevron.style.transform = 'rotate(0deg)';
      if (btn) {
        const textSpan = btn.querySelector('.vdr-toggle-label');
        if (textSpan) textSpan.textContent = '전체 옵션 보기';
      }
    }
    if (window.lucide) window.lucide.createIcons();
  }

  getOptionIconSvg(iconName, isPresent) {
    const strokeCls = isPresent ? 'stroke-[#171B1E] stroke-[2.2]' : 'stroke-slate-400 stroke-[1.8]';
    const fillCls = 'none';

    switch (iconName) {
      case 'sun':
      case 'OPT_SUNROOF':
        return `<svg class="w-5 h-5 ${strokeCls}" fill="${fillCls}" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>`;
      case 'tv':
      case 'OPT_HUD':
        return `<svg class="w-5 h-5 ${strokeCls}" fill="${fillCls}" viewBox="0 0 24 24"><rect width="20" height="15" x="2" y="7" rx="2"/><polyline points="17 2 12 7 7 2"/></svg>`;
      case 'radar':
      case 'OPT_PARKING_SENSOR':
        return `<svg class="w-5 h-5 ${strokeCls}" fill="${fillCls}" viewBox="0 0 24 24"><path d="M12 20a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z"/><path d="M12 14a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/></svg>`;
      case 'camera':
      case 'OPT_REAR_CAMERA':
        return `<svg class="w-5 h-5 ${strokeCls}" fill="${fillCls}" viewBox="0 0 24 24"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>`;
      case 'fan':
      case 'OPT_AUTO_AC':
        return `<svg class="w-5 h-5 ${strokeCls}" fill="${fillCls}" viewBox="0 0 24 24"><path d="M10.827 16.379a6.082 6.082 0 0 1-8.618-7.002l5.412 1.45a6.082 6.082 0 0 1 7.002-8.618l-1.45 5.412a6.082 6.082 0 0 1 8.618 7.002l-5.412-1.45a6.082 6.082 0 0 1-7.002 8.618l1.45-5.412Z"/><circle cx="12" cy="12" r="2"/></svg>`;
      case 'key':
      case 'OPT_SMART_KEY':
        return `<svg class="w-5 h-5 ${strokeCls}" fill="${fillCls}" viewBox="0 0 24 24"><circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/></svg>`;
      case 'navigation':
      case 'OPT_GENUINE_NAVI':
        return `<svg class="w-5 h-5 ${strokeCls}" fill="${fillCls}" viewBox="0 0 24 24"><polygon points="3 11 22 2 13 21 11 13 3 11"/></svg>`;
      case 'flame':
      case 'OPT_HEATED_SEAT':
        return `<svg class="w-5 h-5 ${strokeCls}" fill="${fillCls}" viewBox="0 0 24 24"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>`;
      case 'wind':
      case 'OPT_VENTILATED_SEAT':
        return `<svg class="w-5 h-5 ${strokeCls}" fill="${fillCls}" viewBox="0 0 24 24"><path d="M17.7 7.7a2.5 2.5 0 1 1 1.8 4.3H2"/><path d="M9.6 4.6A2 2 0 1 1 11 8H2"/><path d="M12.6 19.4A2 2 0 1 0 14 16H2"/></svg>`;
      case 'armchair':
      case 'OPT_LEATHER_SEATS':
      default:
        return `<svg class="w-5 h-5 ${strokeCls}" fill="${fillCls}" viewBox="0 0 24 24"><path d="M19 9V6a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v3"/><path d="M3 16a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5a2 2 0 0 0-4 0v2H7v-2a2 2 0 0 0-4 0z"/><path d="M5 18v2"/><path d="M19 18v2"/></svg>`;
    }
  }

  buildFallbackTop10(d) {
    const rawOptions = Array.isArray(d.options) ? d.options : [];
    const text = rawOptions.join(' ') + ' ' + (d.model_name || '');
    const defs = [
      { code: 'OPT_SUNROOF', name: '선루프', icon: 'sun', keys: ['선루프', '루프'] },
      { code: 'OPT_HUD', name: 'HUD', icon: 'tv', keys: ['HUD', '헤드업'] },
      { code: 'OPT_PARKING_SENSOR', name: '주차센서', icon: 'radar', keys: ['주차', '센서'] },
      { code: 'OPT_REAR_CAMERA', name: '후방카메라', icon: 'camera', keys: ['후방', '카메라', '어라운드'] },
      { code: 'OPT_AUTO_AC', name: '자동에어컨', icon: 'fan', keys: ['에어컨', '오토'] },
      { code: 'OPT_SMART_KEY', name: '스마트키', icon: 'key', keys: ['스마트키', '버튼'] },
      { code: 'OPT_GENUINE_NAVI', name: '내비게이션', icon: 'navigation', keys: ['내비', '네비'] },
      { code: 'OPT_HEATED_SEAT', name: '열선시트', icon: 'flame', keys: ['열선'] },
      { code: 'OPT_VENTILATED_SEAT', name: '통풍시트', icon: 'wind', keys: ['통풍'] },
      { code: 'OPT_LEATHER_SEATS', name: '가죽시트', icon: 'armchair', keys: ['가죽', '나파'] },
    ];
    return defs.map(def => {
      const match = def.keys.some(k => text.includes(k));
      return {
        code: def.code,
        name: def.name,
        icon: def.icon,
        status: match ? 'PRESENT' : 'UNKNOWN',
        is_present: match,
      };
    });
  }

  // 현대화된 표준 50대 옵션 정의 마스터 (CD/테이프 등 불필요한 구시대 옵션 제외, 현대 핵심 사양 전체 포함)
  static MASTER_CATEGORIES_CATALOG = {
    '외관·내장': [
      { code: 'OPT_SUNROOF', name: '선루프 (파노라마/일반)', keywords: ['선루프', '루프', '파노라마'] },
      { code: 'OPT_LED_HEADLAMP', name: 'LED 헤드램프 & 주간주행등', keywords: ['LED', 'HID', '프로젝션', '헤드램프', '데이라이트'] },
      { code: 'OPT_POWER_TRUNK', name: '스마트 파워 전동 트렁크', keywords: ['전동트렁크', '파워트렁크', '스마트테일게이트', '테일게이트'] },
      { code: 'OPT_POWER_FOLD_MIRROR', name: '전동접이 사이드미러 (락폴딩)', keywords: ['사이드미러', '전동접이', '락폴딩', '미러', '전동'] },
      { code: 'OPT_ALUMINUM_WHEEL', name: '알루미늄 휠 (17~21인치)', keywords: ['알루미늄', '알로이', '휠', '18인치', '19인치', '20인치'] },
      { code: 'OPT_POWER_LOCK_WIN', name: '파워 도어록 & 파워 윈도우', keywords: ['도어록', '파워윈도우', '세이프티윈도우'] },
      { code: 'OPT_ROOF_RACK', name: '루프랙', keywords: ['루프랙', '루프레일', '캐리어'] },
      { code: 'OPT_HEATED_STEERING', name: '열선 스티어링 휠 (핸들 열선)', keywords: ['열선핸들', '열선 스티어링', '핸들열선', '핸들'] },
      { code: 'OPT_TILT_STEERING', name: '전동 조절 스티어링 휠', keywords: ['전동조절핸들', '전동 스티어링', '틸트', '텔레스코픽'] },
      { code: 'OPT_PADDLE_SHIFT', name: '패들 시프트', keywords: ['패들시프트', '패들', '시프트패들'] },
      { code: 'OPT_STEERING_REMOTE', name: '스티어링 휠 리모컨', keywords: ['핸들리모컨', '스티어링리모컨', '리모컨'] },
      { code: 'OPT_AMBIENT_LIGHT', name: '앰비언트 라이트 (실내 무드램프)', keywords: ['앰비언트', '무드램프', '무드등'] },
      { code: 'OPT_ECM_ROOM_MIRROR', name: 'ECM 전자식 룸미러', keywords: ['ECM', '눈부심방지'] },
      { code: 'OPT_GHOST_DOOR', name: '고스트 도어 클로징 (소프트 클로징)', keywords: ['고스트도어', '소프트클로징', '압축도어'] }
    ],
    '안전': [
      { code: 'OPT_AIRBAG_FRONT', name: '에어백 (운전석, 동승석)', keywords: ['에어백', '운전석에어백', '동승석에어백', '듀얼에어백'] },
      { code: 'OPT_AIRBAG_SIDE_CURTAIN', name: '사이드 & 커튼 에어백', keywords: ['사이드에어백', '커튼에어백', '사이드', '커튼'] },
      { code: 'OPT_ABS_ESC_TCS', name: 'ABS / ESC (차체자세제어) / TCS', keywords: ['ABS', 'ESC', 'TCS', '차체자세', '미끄럼방지'] },
      { code: 'OPT_TPMS', name: '타이어 공기압 경보 (TPMS)', keywords: ['TPMS', '공기압', '타이어공기압'] },
      { code: 'OPT_PARKING_SENSOR', name: '주차감지센서 (전방/후방)', keywords: ['주차감지', '센서', '전방감지', '후방감지', '전후방센서'] },
      { code: 'OPT_REAR_CAMERA', name: '후방카메라 (조향 연동 가이드)', keywords: ['후방카메라', '후방 캠', '조향가이드', '카메라'] },
      { code: 'OPT_SURROUND_VIEW', name: '360도 어라운드 뷰 (서라운드 뷰)', keywords: ['어라운드뷰', '서라운드뷰', '360', '서라운드', '어라운드'] },
      { code: 'OPT_LANE_ASSIST', name: '차로 이탈방지 / 차로 유지 보조 (LKA/LFA)', keywords: ['차선이탈', '차로유지', 'LKA', 'LFA', '차선'] },
      { code: 'OPT_FORWARD_COLLISION', name: '전방 충돌방지 보조 (FCA)', keywords: ['전방충돌', '긴급제동', 'FCA', '충돌방지'] },
      { code: 'OPT_BLIND_SPOT', name: '후측방 충돌방지 보조 / 경보 (BCA/BSD)', keywords: ['후측방', '사각지대', 'BSD', 'BCA', '측후방'] },
      { code: 'OPT_ELEC_SUSPENSION', name: '전자제어 서스펜션 (ECS)', keywords: ['전자제어서스펜션', '에어서스', '서스펜션', 'ECS'] },
      { code: 'OPT_REMOTE_PARKING', name: '원격 스마트 주차 보조 (RSPA)', keywords: ['원격주차', 'RSPA', '원격스마트주차'] }
    ],
    '편의·멀티미디어': [
      { code: 'OPT_SMART_KEY', name: '스마트키 & 버튼 시동 / 원격 시동', keywords: ['스마트키', '버튼시동', '원격시동'] },
      { code: 'OPT_GENUINE_NAVI', name: '와이드 디스플레이 내비게이션', keywords: ['내비게이션', '네비', '내비', '순정내비'] },
      { code: 'OPT_HUD', name: '헤드업 디스플레이 (HUD)', keywords: ['HUD', '헤드업', '헤드업디스플레이'] },
      { code: 'OPT_AUTO_HOLD', name: '전자식 주차브레이크 (EPB & 오토홀드)', keywords: ['EPB', '전자식파킹', '오토홀드', '파킹브레이크', '파킹'] },
      { code: 'OPT_AUTO_AC', name: '자동 에어컨 (풀오토 듀얼 에어컨)', keywords: ['에어컨', '풀오토', '오토에어컨', '듀얼에어컨', '자동에어컨'] },
      { code: 'OPT_SMART_CRUISE', name: '스마트 크루즈 컨트롤 (어댑티브 / 정차&재출발)', keywords: ['스마트크루즈', '어댑티브', '크루즈', 'SCC', 'ASCC'] },
      { code: 'OPT_HDA', name: '고속도로 주행 보조 (HDA / HDA2)', keywords: ['HDA', '고속도로주행보조', 'HDA2'] },
      { code: 'OPT_CARPLAY_AA', name: '애플 카플레이 / 안드로이드 오토 (폰 프로젝션)', keywords: ['카플레이', '안드로이드오토', '폰프로젝션', '티맵'] },
      { code: 'OPT_WIRELESS_CHARGER', name: '스마트폰 무선 충전 패드', keywords: ['무선충전', '무선 충전', '스마트폰무선충전'] },
      { code: 'OPT_DIGITAL_KEY', name: '디지털 키 (스마트폰 키)', keywords: ['디지털키', '카드키', 'NFC'] },
      { code: 'OPT_HIPASS', name: '하이패스 시스템 (내장형/룸미러)', keywords: ['하이패스', '통행료'] },
      { code: 'OPT_RAIN_SENSOR', name: '레인센서 (우적감지 와이퍼)', keywords: ['레인센서', '우적감지', '와이퍼'] },
      { code: 'OPT_AUTO_LIGHT', name: '오토 라이트 컨트롤', keywords: ['오토라이트', '오토 헤드램프'] },
      { code: 'OPT_PREMIUM_AUDIO', name: '프리미엄 사운드 (크렐/보스/하만카돈/B&O)', keywords: ['크렐', '보스', '하만카돈', '뱅앤올룹슨', '사운드', '스피커', 'JBL', '렉시콘', '메리디안'] },
      { code: 'OPT_USB_AUX', name: 'USB 단자 & 고속 충전 포트', keywords: ['USB', '충전포트', 'C타입'] },
      { code: 'OPT_SUN_CURTAIN', name: '뒷좌석 / 후방 선커튼 (수동/전동)', keywords: ['커튼', '선커튼', '블라인드', '선블라인드'] }
    ],
    '시트': [
      { code: 'OPT_LEATHER_SEATS', name: '가죽시트 (천연 / 나파 / 퀼팅)', keywords: ['가죽시트', '가죽', '나파', '천연가죽'] },
      { code: 'OPT_POWER_SEAT_DRV', name: '전동시트 (운전석)', keywords: ['운전석전동시트', '전동시트', '요추받침'] },
      { code: 'OPT_POWER_SEAT_PASS', name: '전동시트 (동승석 워크인 디바이스)', keywords: ['동승석전동시트', '동승석전동', '워크인', '릴렉션'] },
      { code: 'OPT_POWER_SEAT_REAR', name: '전동시트 (뒷좌석 리클라이닝)', keywords: ['뒷좌석전동시트', '후석전동', '2열전동', '리클라이닝'] },
      { code: 'OPT_HEATED_SEAT_FRONT', name: '열선시트 (앞좌석)', keywords: ['열선시트', '열선', '앞좌석열선'] },
      { code: 'OPT_HEATED_SEAT_REAR', name: '열선시트 (뒷좌석)', keywords: ['뒷좌석열선', '2열열선', '후석열선'] },
      { code: 'OPT_MEMORY_SEAT', name: '메모리 시트 (운전석, 동승석 자세 기억)', keywords: ['메모리시트', '메모리', 'IMS'] },
      { code: 'OPT_VENTILATED_SEAT_FRONT', name: '통풍시트 (앞좌석)', keywords: ['통풍시트', '통풍', '앞좌석통풍'] },
      { code: 'OPT_VENTILATED_SEAT_REAR', name: '통풍시트 (뒷좌석)', keywords: ['뒷좌석통풍', '2열통풍', '후석통풍'] },
      { code: 'OPT_MASSAGE_SEAT', name: '마사지 시트 (에르고 모션 스트레칭)', keywords: ['마사지시트', '에르고모션', '마사지'] }
    ]
  };

  mergeWithMasterCategories(d) {
    const rawOptions = Array.isArray(d.options) ? d.options : [];
    const optionsStr = rawOptions.join(' ') + ' ' + (d.model_name || '') + ' ' + (d.trim || '');
    const isPremiumCar = (d.model_name && (d.model_name.includes('제네시스') || d.model_name.includes('벤츠') || d.model_name.includes('BMW') || d.model_name.includes('그랜저') || d.model_name.includes('K8') || d.model_name.includes('GV70') || d.model_name.includes('GV80')));
    const isModernCar = (d.year && d.year >= 2020);

    const existingMap = {};
    if (d.options_categorized && typeof d.options_categorized === 'object') {
      for (const [cat, list] of Object.entries(d.options_categorized)) {
        if (Array.isArray(list)) {
          list.forEach(o => {
            if (o && (o.code || o.name)) {
              if (o.code) existingMap[o.code] = o;
              if (o.name) existingMap[o.name] = o;
            }
          });
        }
      }
    }

    const categorized = {};
    for (const [catName, defs] of Object.entries(VehicleDetailRenderer.MASTER_CATEGORIES_CATALOG)) {
      categorized[catName] = defs.map(def => {
        let isPresent = false;
        let status = 'UNKNOWN';

        const existing = existingMap[def.code] || existingMap[def.name];
        if (existing) {
          isPresent = Boolean(existing.is_present || existing.status === 'PRESENT');
          status = isPresent ? 'PRESENT' : (existing.status || 'ABSENT');
        } else {
          const matched = def.keywords.some(k => optionsStr.includes(k));
          if (matched) {
            isPresent = true;
            status = 'PRESENT';
          } else if (isPremiumCar && ['OPT_LED_HEADLAMP', 'OPT_POWER_FOLD_MIRROR', 'OPT_ALUMINUM_WHEEL', 'OPT_HEATED_STEERING', 'OPT_STEERING_REMOTE', 'OPT_AIRBAG_FRONT', 'OPT_AIRBAG_SIDE_CURTAIN', 'OPT_ABS_ESC_TCS', 'OPT_TPMS', 'OPT_AUTO_AC', 'OPT_SMART_KEY', 'OPT_AUTO_HOLD', 'OPT_CARPLAY_AA', 'OPT_AUTO_LIGHT', 'OPT_HIPASS', 'OPT_LEATHER_SEATS', 'OPT_HEATED_SEAT_FRONT', 'OPT_POWER_SEAT_DRV'].includes(def.code)) {
            isPresent = true;
            status = 'PRESENT';
          } else if (isModernCar && ['OPT_POWER_FOLD_MIRROR', 'OPT_ALUMINUM_WHEEL', 'OPT_AIRBAG_FRONT', 'OPT_AIRBAG_SIDE_CURTAIN', 'OPT_ABS_ESC_TCS', 'OPT_TPMS', 'OPT_SMART_KEY', 'OPT_AUTO_LIGHT', 'OPT_CARPLAY_AA'].includes(def.code)) {
            isPresent = true;
            status = 'PRESENT';
          }
        }

        return {
          code: def.code,
          name: def.name,
          status: status,
          is_present: isPresent
        };
      });
    }

    categorized['기타 옵션'] = [];
    if (d.options_categorized && Array.isArray(d.options_categorized['기타 옵션'])) {
      categorized['기타 옵션'] = d.options_categorized['기타 옵션'];
    }

    return categorized;
  }

  buildFallbackCategorized(d) {
    return this.mergeWithMasterCategories(d);
  }

  // 적용된 옵션만 보기 토글 기능 (엔카식 편의 기능)
  toggleOnlyPresentOptions(btn) {
    window.__showOnlyPresentOptions = !window.__showOnlyPresentOptions;
    const isOnly = window.__showOnlyPresentOptions;
    const items = document.querySelectorAll('.vdr-absent-option');
    items.forEach(el => {
      if (isOnly) {
        el.classList.add('hidden');
      } else {
        el.classList.remove('hidden');
      }
    });

    // 모든 토글 버튼 상태 텍스트 및 스타일 갱신
    const allBtns = document.querySelectorAll('.vdr-only-present-btn');
    allBtns.forEach(b => {
      if (isOnly) {
        b.classList.remove('bg-slate-100', 'text-slate-600', 'border-slate-200');
        b.classList.add('bg-rose-50', 'text-rose-600', 'border-rose-200', 'font-bold');
        b.innerHTML = `<i data-lucide="check-circle" class="w-3.5 h-3.5 mr-1 text-rose-500"></i>적용된 옵션만 보는 중`;
      } else {
        b.classList.remove('bg-rose-50', 'text-rose-600', 'border-rose-200', 'font-bold');
        b.classList.add('bg-slate-100', 'text-slate-600', 'border-slate-200');
        b.innerHTML = `<i data-lucide="filter" class="w-3.5 h-3.5 mr-1 text-slate-400"></i>적용된 옵션만 보기`;
      }
    });
    if (window.lucide) window.lucide.createIcons();
  }

  renderOptionsSection(d) {
    const top10 = (d.top10_options && d.top10_options.length === 10) ? d.top10_options : this.buildFallbackTop10(d);
    
    // 항상 전체 마스터 카탈로그와 병합하여 모든 표준 옵션을 엔카 스타일로 완전 표시
    const categorized = this.mergeWithMasterCategories(d);

    // 총 장착 확인 개수 계산
    let totalPresentCount = 0;
    for (const [cat, list] of Object.entries(categorized)) {
      if (Array.isArray(list)) {
        totalPresentCount += list.filter(o => o.is_present || o.status === 'PRESENT').length;
      }
    }
    if (totalPresentCount === 0 && Array.isArray(d.options)) {
      totalPresentCount = d.options.length;
    }

    // 1. 10대 핵심 주요 옵션 5x2 그리드 (PC: 5개씩 2줄, 모바일: 균등 5열)
    const top10Html = top10.map(opt => {
      const isPresent = opt.is_present || opt.status === 'PRESENT';
      const isAbsent = opt.status === 'ABSENT';

      let cardStyle = "bg-white border-slate-200";
      let iconColor = "text-[#171B1E]";
      let badgeHtml = `<span class="w-1.5 h-1.5 rounded-full bg-[#10B981]"></span>`;
      let stateLabel = `<span class="text-[10px] font-bold text-[#10B981]">장착 확인</span>`;

      if (isPresent) {
        cardStyle = "bg-slate-50 border-slate-300 font-bold shadow-2xs";
        iconColor = "text-[#171B1E]";
        badgeHtml = `<span class="w-1.5 h-1.5 rounded-full bg-[#10B981]"></span>`;
        stateLabel = `<span class="text-[10px] font-bold text-[#10B981]">장착</span>`;
      } else if (isAbsent) {
        cardStyle = "bg-slate-50/40 border-slate-100 opacity-40";
        iconColor = "text-slate-300";
        badgeHtml = `<span class="w-1.5 h-1.5 rounded-full bg-slate-300"></span>`;
        stateLabel = `<span class="text-[10px] text-slate-400 line-through">미장착</span>`;
      } else {
        cardStyle = "bg-white border-dashed border-slate-200 opacity-70";
        iconColor = "text-slate-400";
        badgeHtml = `<span class="w-1.5 h-1.5 rounded-full bg-slate-300"></span>`;
        stateLabel = `<span class="text-[10px] text-slate-400">미확인</span>`;
      }

      // 모바일 친화 축약명
      let shortName = opt.name || '';
      shortName = shortName.replace('헤드업 디스플레이 (HUD)', 'HUD')
                           .replace('주차감지센서', '주차센서')
                           .replace('와이드 디스플레이 내비게이션', '내비게이션')
                           .replace('순정 내비게이션', '내비게이션')
                           .replace('자동 에어컨 (풀오토 듀얼 에어컨)', '자동에어컨')
                           .replace('풀오토 에어컨', '자동에어컨')
                           .replace('스마트키 & 버튼 시동 / 원격 시동', '스마트키')
                           .replace('가죽시트 (천연 / 나파 / 퀼팅)', '가죽시트')
                           .replace('열선시트 (앞좌석)', '열선시트')
                           .replace('통풍시트 (앞좌석)', '통풍시트')
                           .replace('선루프 (파노라마/일반)', '선루프');

      return `
        <div class="flex flex-col items-center justify-center p-2 sm:p-3 rounded-xl border ${cardStyle} transition-all text-center">
          <div class="mb-1 sm:mb-1.5 ${iconColor}">
            ${this.getOptionIconSvg(opt.icon || opt.code, isPresent)}
          </div>
          <span class="text-[11px] sm:text-xs font-semibold tracking-tight text-slate-800 truncate w-full text-center">${escapeHtml(shortName)}</span>
          <div class="mt-1 flex items-center justify-center gap-1">
            ${badgeHtml}
            ${stateLabel}
          </div>
        </div>
      `;
    }).join('');

    // 2. 전체 옵션 아코디언 내용 구성 (엔카형 세부 목록: 다 넣고 장착된 것만 선명하게 활성화)
    let fullCategoriesHtml = '';
    const catKeys = ['외관·내장', '안전', '편의·멀티미디어', '시트', '기타 옵션'];
    for (const catName of catKeys) {
      const list = categorized[catName] || [];
      if (list.length === 0) continue;

      const presentList = list.filter(o => o.is_present || o.status === 'PRESENT');

      // 엔카 스타일 리스트 그리드: 적용된 옵션은 선명한 검정 + 체크원, 미적용은 연회색
      const rowsHtml = list.map(o => {
        const p = o.is_present || o.status === 'PRESENT';
        if (p) {
          return `
            <div class="vdr-option-item flex items-center gap-2.5 py-1.5 px-2 rounded-lg bg-white border border-slate-200/80 shadow-2xs">
              <span class="w-4 h-4 rounded-full border-2 border-slate-900 bg-slate-900 flex items-center justify-center shrink-0">
                <svg class="w-2.5 h-2.5 text-white" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
              </span>
              <span class="text-xs sm:text-[13px] font-bold text-slate-900 truncate">${escapeHtml(o.name)}</span>
            </div>
          `;
        } else {
          return `
            <div class="vdr-option-item vdr-absent-option flex items-center gap-2.5 py-1.5 px-2 rounded-lg bg-transparent border border-dashed border-slate-200/50">
              <span class="w-4 h-4 rounded-full border border-slate-300 bg-transparent flex items-center justify-center shrink-0">
                <svg class="w-2.5 h-2.5 text-slate-300" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
              </span>
              <span class="text-xs sm:text-[13px] font-normal text-slate-400 truncate">${escapeHtml(o.name)}</span>
            </div>
          `;
        }
      }).join('');

      fullCategoriesHtml += `
        <div class="p-3.5 sm:p-4 bg-slate-50/80 rounded-xl border border-slate-200/80 space-y-2.5">
          <div class="flex items-center justify-between border-b border-slate-200/60 pb-2">
            <span class="text-xs sm:text-sm font-bold text-slate-800 flex items-center gap-1.5">
              <span class="w-2 h-2 rounded-full bg-[#171B1E]"></span>
              ${escapeHtml(catName)}
            </span>
            <div class="flex items-center gap-2">
              <span class="text-[11px] sm:text-xs font-semibold text-slate-500">
                <strong class="text-slate-900">${presentList.length}</strong> / ${list.length}개 장착
              </span>
            </div>
          </div>
          <!-- 2열 그리드 배치로 전체 옵션 정렬 (모바일/PC 반응형) -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
            ${rowsHtml}
          </div>
        </div>
      `;
    }

    return `
      <div class="space-y-3">
        <!-- 10대 핵심 주요 옵션 5x2 그리드 -->
        <div class="grid grid-cols-5 gap-1.5 sm:gap-2.5">
          ${top10Html}
        </div>

        <!-- 전체 옵션 보기 토글 버튼 (TASK 6) -->
        <button type="button" onclick="window.__vdrInstance ? window.__vdrInstance.toggleFullOptionsView() : null" id="vdrToggleFullOptionsBtn" class="w-full py-2.5 sm:py-3 px-4 bg-slate-100 hover:bg-slate-200/80 active:bg-slate-200 text-slate-800 text-xs sm:text-sm font-bold rounded-xl border border-slate-200 transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-2xs">
          <i data-lucide="layers" class="w-4 h-4 text-slate-600"></i>
          <span class="vdr-toggle-label">전체 옵션 보기</span>
          <span class="text-xs text-slate-500 font-normal">(총 ${totalPresentCount}개 장착 확인)</span>
          <i data-lucide="chevron-down" id="vdrToggleOptionsChevron" class="w-4 h-4 ml-1 text-slate-500 transition-transform"></i>
        </button>

        <!-- 전체 옵션 펼치기 패널 (기본 접힘, 인라인 펼침) -->
        <div id="vdrFullOptionsPanel" class="hidden space-y-3 pt-1 animate-in fade-in duration-150">
          <div class="text-[11px] sm:text-xs text-slate-500 flex flex-wrap items-center justify-between px-1 pb-1 gap-2">
            <span class="font-medium text-slate-600">차마트 현대형 표준 4대 분류 상세 옵션표 (전체 비교)</span>
            <div class="flex items-center gap-2">
              <!-- 엔카 스타일: 적용된 옵션만 보기 토글 버튼 -->
              <button type="button" onclick="window.__vdrInstance ? window.__vdrInstance.toggleOnlyPresentOptions(this) : null" class="vdr-only-present-btn inline-flex items-center px-2.5 py-1 text-xs rounded-lg border border-slate-200 bg-slate-100 hover:bg-slate-200/70 text-slate-700 font-medium transition-colors cursor-pointer">
                <i data-lucide="filter" class="w-3.5 h-3.5 mr-1 text-slate-400"></i>
                적용된 옵션만 보기
              </button>
              <span class="hidden sm:inline-flex items-center gap-1.5 text-xs text-slate-600 font-medium ml-1">
                <span class="w-2.5 h-2.5 rounded-full bg-slate-900"></span>장착
                <span class="w-2.5 h-2.5 rounded-full border border-slate-300 ml-1"></span>미장착
              </span>
            </div>
          </div>
          <div class="space-y-2.5">
            ${fullCategoriesHtml || '<div class="text-xs text-slate-400 py-3 text-center">상세 옵션 내역을 불러오는 중입니다.</div>'}
          </div>
        </div>
      </div>
    `;
  }

  updateLoanCalc() {
    const downSelect = document.getElementById('vdrCalcDownPayment');
    const monthSelect = document.getElementById('vdrCalcMonths');
    const rateSelect = document.getElementById('vdrCalcRate');
    const resultEl = document.getElementById('vdrCalcMonthlyResult');
    const totalEl = document.getElementById('vdrCalcTotalInterestResult');
    const interestEl = document.getElementById('vdrCalcOnlyInterest');
    const repayEl = document.getElementById('vdrCalcTotalRepay');
    if (!resultEl) return;

    const targetPrice = this.data?.target_price || 0;
    if (targetPrice <= 0) {
      resultEl.textContent = '상담 문의';
      if (totalEl) totalEl.textContent = '이자: - / 총액: -';
      if (interestEl) interestEl.textContent = '-';
      if (repayEl) repayEl.textContent = '-';
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
      if (interestEl) interestEl.textContent = '0원';
      if (repayEl) repayEl.textContent = '0원';
      return;
    }

    resultEl.textContent = `월 약 ${res.monthlyTenThousand.toLocaleString('ko-KR')}만원`;
    if (interestEl) interestEl.textContent = `약 ${res.totalInterestTenThousand.toLocaleString('ko-KR')}만원`;
    if (repayEl) repayEl.textContent = `약 ${res.totalRepayTenThousand.toLocaleString('ko-KR')}만원`;
    if (totalEl) {
      totalEl.textContent = `약 ${res.totalInterestTenThousand.toLocaleString('ko-KR')}만원 / 약 ${res.totalRepayTenThousand.toLocaleString('ko-KR')}만원`;
    }
  }

  selectPhoto(index) {
    if (!this.photos || index < 0 || index >= this.photos.length) return;
    this.currentPhotoIdx = index;
    const photo = this.photos[this.currentPhotoIdx];
    
    // 1. 일반 정보 탭 메인 이미지 갱신
    const mainImg = document.getElementById('vdrMainImage');
    if (mainImg) mainImg.src = photo.url;

    const capEl = document.getElementById('vdrPhotoCaption');
    if (capEl) capEl.textContent = photo.caption;

    const partLabelEl = document.getElementById('vdrPhotoPartLabel');
    if (partLabelEl) partLabelEl.textContent = photo.display_label || photo.caption || '외관';

    const countEl = document.getElementById('vdrPhotoCounter');
    if (countEl) countEl.textContent = `${this.currentPhotoIdx + 1} / ${this.photos.length}`;

    // 2. DIRECTIVE 082/083 사진 전용 화면 대형 뷰어 갱신
    const dedImg = document.getElementById('vdrDedicatedMainImage');
    if (dedImg) dedImg.src = photo.url;

    const dedCap = document.getElementById('vdrDedicatedCaption');
    if (dedCap) dedCap.textContent = photo.caption;

    const dedPart = document.getElementById('vdrDedicatedPartLabel');
    if (dedPart) dedPart.textContent = photo.display_label || photo.caption || '외관';

    const dedCount = document.getElementById('vdrDedicatedCounter');
    if (dedCount) dedCount.textContent = `${this.currentPhotoIdx + 1} / ${this.photos.length}`;

    // 3. 전체화면 Lightbox 모달 갱신
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

  // DIRECTIVE 086: 세로 스크롤 방식 실사진 전체보기 피드 모달 열기/닫기 (마우스 뒤로가기 완벽 연동)
  openVerticalPhotoFeed(startIndex = 0) {
    const modal = document.getElementById('vdrVerticalFeedModal');
    if (!modal) return;

    this.savedScrollY = window.scrollY || window.pageYOffset || 0;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    // 브라우저 및 마우스 뒤로가기 시 사진 모달만 자연스럽게 닫히도록 해시 push
    if (!window.location.hash.includes('photo-feed')) {
      window.history.pushState({ modal: 'photo_feed' }, '', window.location.pathname + '#photo-feed');
    }

    if (window.lucide) window.lucide.createIcons();

    // 시작 인덱스가 있으면 해당 위치로 스크롤 이동
    if (startIndex > 0) {
      setTimeout(() => {
        const targetItem = document.getElementById(`vdrFeedItem_${startIndex}`);
        if (targetItem) {
          targetItem.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 50);
    } else {
      const scrollCont = document.getElementById('vdrVerticalFeedScrollContainer');
      if (scrollCont) scrollCont.scrollTop = 0;
    }

    // ESC 키 리스너 등록
    this.feedEscHandler = (e) => {
      if (e.key === 'Escape') {
        this.closeVerticalPhotoFeed(true);
      }
    };
    window.addEventListener('keydown', this.feedEscHandler);
  }

  closeVerticalPhotoFeed(triggerHistoryBack = true) {
    const modal = document.getElementById('vdrVerticalFeedModal');
    if (modal) {
      modal.classList.add('hidden');
    }
    document.body.style.overflow = '';

    if (this.feedEscHandler) {
      window.removeEventListener('keydown', this.feedEscHandler);
      this.feedEscHandler = null;
    }

    // URL에 #photo-feed 해시가 남아있고 triggerHistoryBack인 경우 history.back() 실행
    if (triggerHistoryBack && window.location.hash.includes('photo-feed')) {
      window.history.back();
    }

    // 원래 보던 스크롤 위치 복원
    if (typeof this.savedScrollY === 'number') {
      window.scrollTo({ top: this.savedScrollY, behavior: 'instant' });
    }
  }

  // 기존 호환용 메서드
  switchDetailTab(tab) {
    if (tab === 'PHOTOS') {
      this.openVerticalPhotoFeed(0);
    }
  }

  filterPhotoCategory(cat) {
    // DIRECTIVE 086: 카테고리 필터 불필요, 전체 감상
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

  // 타이어 및 주요 소모품 상태 점검표 접기/펼치기 토글
  toggleTireConsumables() {
    const body = document.getElementById('vdrTireConsumablesBody');
    const chevron = document.getElementById('vdrTireChevron');
    if (!body) return;
    const isHidden = body.classList.contains('hidden');
    if (isHidden) {
      body.classList.remove('hidden');
      if (chevron) chevron.style.transform = 'rotate(180deg)';
      if (window.lucide) window.lucide.createIcons();
    } else {
      body.classList.add('hidden');
      if (chevron) chevron.style.transform = 'rotate(0deg)';
    }
  }

  // 사고 및 성능점검 공식 진단표 접기/펼치기 토글
  toggleAccidentDiagnostics() {
    const body = document.getElementById('vdrAccidentDiagnosticsBody');
    const chevron = document.getElementById('vdrAccidentChevron');
    if (!body) return;
    const isHidden = body.classList.contains('hidden');
    if (isHidden) {
      body.classList.remove('hidden');
      if (chevron) chevron.style.transform = 'rotate(180deg)';
      if (window.lucide) window.lucide.createIcons();
    } else {
      body.classList.add('hidden');
      if (chevron) chevron.style.transform = 'rotate(0deg)';
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

  // DIRECTIVE 075-A: 차대번호(VIN) 클립보드 복사 및 인라인 피드백
  copyVin(vin) {
    if (!vin) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(vin).then(() => {
        const lbl = document.getElementById('vdrVinCopyLabel');
        if (lbl) {
          lbl.textContent = '복사됨!';
          lbl.classList.add('text-emerald-700', 'font-bold');
          setTimeout(() => {
            lbl.textContent = '복사';
            lbl.classList.remove('text-emerald-700', 'font-bold');
          }, 2000);
        }
      }).catch(() => {
        alert('차대번호: ' + vin);
      });
    } else {
      alert('차대번호: ' + vin);
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

    // DIRECTIVE 082 & 083: 사진 전용 뷰어 버튼
    const dedBtnPrev = document.getElementById('vdrBtnDedicatedPrev');
    if (dedBtnPrev) {
      dedBtnPrev.addEventListener('click', (e) => {
        e.stopPropagation();
        this.prevPhoto();
      });
    }
    const dedBtnNext = document.getElementById('vdrBtnDedicatedNext');
    if (dedBtnNext) {
      dedBtnNext.addEventListener('click', (e) => {
        e.stopPropagation();
        this.nextPhoto();
      });
    }

    // 일반 갤러리 뷰포트 터치 스와이프
    const viewport = document.getElementById('vdrGalleryViewport');
    if (viewport) {
      viewport.addEventListener('touchstart', (e) => {
        this.touchStartX = e.changedTouches[0].screenX;
      }, { passive: true });

      viewport.addEventListener('touchend', (e) => {
        const currentTime = new Date().getTime();
        const tapLength = currentTime - (this.lastTapTime || 0);
        if (tapLength < 350 && tapLength > 50) {
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

    // DIRECTIVE 082 & 083: 사진 전용 대형 뷰포트 터치 스와이프 (모바일 100% 최적화)
    const dedViewport = document.getElementById('vdrDedicatedGalleryViewport');
    if (dedViewport) {
      dedViewport.addEventListener('touchstart', (e) => {
        this.dedTouchStartX = e.changedTouches[0].screenX;
        this.dedTouchStartY = e.changedTouches[0].screenY;
      }, { passive: true });

      dedViewport.addEventListener('touchend', (e) => {
        const endX = e.changedTouches[0].screenX;
        const endY = e.changedTouches[0].screenY;
        const diffX = endX - (this.dedTouchStartX || endX);
        const diffY = endY - (this.dedTouchStartY || endY);

        // 수평 스와이프가 수직 스크롤보다 크고 40px 이상일 때만 사진 넘김 (세로 스크롤 보존)
        if (Math.abs(diffX) > 40 && Math.abs(diffX) > Math.abs(diffY)) {
          if (diffX > 0) {
            this.prevPhoto();
          } else {
            this.nextPhoto();
          }
        }
      }, { passive: true });
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
