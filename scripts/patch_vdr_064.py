#!/usr/bin/env python3
"""DIRECTIVE 064: vehicle_detail_renderer.js 패치 스크립트."""

with open('src/chaficial/platform/ui/static/js/vehicle_detail_renderer.js', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. dealerPhone 1544-0000 제거
target_dealer = """    // 딜러 정보
    const dealer = d.dealer_info || d.dealer || {};
    const dealerName = dealer.name || '차마트 공식 인증팀';
    const dealerPhone = dealer.phone || '1544-0000';
    const showroomLoc = dealer.showroom_location || '서울특별시 동대문구 천호대로 329 (장한평 매매단지 가온모터스)';"""

replace_dealer = """    // 딜러 정보 (DIRECTIVE 064: 1544-0000 임시번호 전수 제거 및 제휴 전시장 정직화)
    const dealer = d.dealer_info || d.dealer || {};
    const dealerName = dealer.name || '차마트 제휴 전시장 (장한평)';
    const rawPhone = (dealer.phone || '').trim();
    const dealerPhone = (rawPhone && !rawPhone.includes('1544') && rawPhone.length >= 8) ? rawPhone : null;
    const showroomLoc = dealer.showroom_location || '서울특별시 성동구 자동차시장1길 70 (용답동) 장한평 자동차매매단지';"""

# 2. 전화번호 표시부 수정
target_phone_ui = """                <div class="flex items-center space-x-1.5 pt-0.5">
                  <i data-lucide="phone" class="w-3.5 h-3.5 text-slate-400 shrink-0"></i>
                  <a href="tel:${escapeHtml(dealerPhone)}" class="text-[#171B1E] font-bold hover:underline">${escapeHtml(dealerPhone)}</a>
                </div>"""

replace_phone_ui = """                <div class="flex items-center space-x-1.5 pt-0.5">
                  <i data-lucide="phone" class="w-3.5 h-3.5 text-slate-400 shrink-0"></i>
                  ${dealerPhone ? `
                    <a href="tel:${escapeHtml(dealerPhone)}" class="text-[#171B1E] font-bold hover:underline">${escapeHtml(dealerPhone)}</a>
                  ` : `
                    <span class="text-slate-500 font-medium">1:1 온라인 방문 예약 접수 후 안내</span>
                  `}
                </div>"""

# 3. CHAMART MOBILITY -> 차마트 모빌리티
target_chamart_mob = '<span class="text-xs font-bold text-slate-500">CHAMART MOBILITY</span>'
replace_chamart_mob = '<span class="text-xs font-bold text-slate-500">차마트 모빌리티</span>'

# 4. 길찾기 모달 '공식 실측' 배지 및 무료주차 제거
target_wayfinding_body = """            <!-- 공식 도로명 주소 및 실측 좌표 안내 (DIRECTIVE 063) -->
            <div class="bg-slate-50 p-3.5 rounded-lg border border-[#E7E9E5] space-y-1.5 text-xs">
              <div class="flex items-center justify-between">
                <span class="font-bold text-[#171B1E] text-sm">차마트 장한평 본사 전시장</span>
                <span class="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-1.5 py-0.5 rounded border border-emerald-200">공식 실측</span>
              </div>
              <div class="text-slate-800 font-medium">서울특별시 성동구 자동차시장1길 70 (용답동)</div>
              <div class="text-[11px] text-slate-500 font-mono">공식 좌표: 37.56191°N, 127.06424°E</div>
              <div class="text-[11px] text-slate-400 pt-0.5">※ 지하철 5호선 장한평역 5·6번 출구 도보 3분 / 고객 전용 무료 주차장</div>
            </div>

            <!-- 공식 지도 앱 바로가기 버튼들 -->
            <div class="space-y-2 pt-1">
              <a href="https://map.kakao.com/link/to/차마트장한평본사전시장,37.56191,127.06424" target="_blank" rel="noopener noreferrer" 
                 class="w-full py-2.5 px-4 bg-[#FEE500] hover:bg-[#FADA0A] text-[#191919] font-bold text-xs rounded-lg flex items-center justify-between cursor-pointer transition-colors shadow-2xs">
                <span class="flex items-center">
                  <i data-lucide="map-pin" class="w-4 h-4 mr-2 text-[#191919]"></i>
                  카카오맵 길찾기 바로가기
                </span>
                <i data-lucide="chevron-right" class="w-4 h-4"></i>
              </a>

              <a href="https://map.naver.com/v5/directions/-/127.06424,37.56191,차마트장한평본사전시장/-/car" target="_blank" rel="noopener noreferrer"
                 class="w-full py-2.5 px-4 bg-[#03C75A] hover:bg-[#02B351] text-white font-bold text-xs rounded-lg flex items-center justify-between cursor-pointer transition-colors shadow-2xs">
                <span class="flex items-center">
                  <i data-lucide="map" class="w-4 h-4 mr-2 text-white"></i>
                  네이버지도 길찾기 바로가기
                </span>
                <i data-lucide="chevron-right" class="w-4 h-4"></i>
              </a>

              <a href="tmap://route?goalname=차마트장한평본사전시장&goalx=127.06424&goaly=37.56191" 
                 class="w-full py-2 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs rounded-lg flex items-center justify-between cursor-pointer transition-colors">
                <span class="flex items-center">
                  <i data-lucide="navigation-2" class="w-3.5 h-3.5 mr-2 text-slate-600"></i>
                  티맵(TMAP) 내비게이션 실행
                </span>
                <span class="text-[10px] text-slate-400">모바일 전용</span>
              </a>
            </div>"""

replace_wayfinding_body = """            <!-- 공식 도로명 주소 및 실측 좌표 안내 (DIRECTIVE 064: 정직한 제휴 전시장) -->
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
            </div>"""

# 5. updateLoanCalc 및 openEstimateModal 단일 순수 함수 연동
target_loan_calc = """  updateLoanCalc() {
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

    const downPercent = downSelect ? parseFloat(downSelect.value) / 100 : 0.1;
    const months = monthSelect ? parseInt(monthSelect.value, 10) : 60;
    const annualRate = rateSelect ? parseFloat(rateSelect.value) : 0.059;
    const monthlyRate = annualRate / 12;

    const loanAmount = targetPrice * (1 - downPercent);
    if (loanAmount <= 0) {
      resultEl.textContent = '선수금 100% (월 0원)';
      if (totalEl) totalEl.textContent = '총 납부 이자: 0원';
      return;
    }

    const monthlyPayment = (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, months)) / (Math.pow(1 + monthlyRate, months) - 1);
    const totalRepay = monthlyPayment * months;
    const totalInterest = totalRepay - loanAmount;

    resultEl.textContent = `월 약 ${Math.round(monthlyPayment).toLocaleString('ko-KR')}만원`;
    if (totalEl) {
      totalEl.textContent = `예상 이자: 약 ${Math.round(totalInterest).toLocaleString('ko-KR')}만원 / 총 상환액: 약 ${Math.round(totalRepay).toLocaleString('ko-KR')}만원`;
    }
  }"""

replace_loan_calc = """  updateLoanCalc() {
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
  }"""

target_open_estimate = """  openEstimateModal() {
    const downSelect = document.getElementById('vdrCalcDownPayment');
    const monthSelect = document.getElementById('vdrCalcMonths');
    const rateSelect = document.getElementById('vdrCalcRate');
    const targetPrice = this.data?.target_price || 0;

    const downPercent = downSelect ? parseFloat(downSelect.value) / 100 : 0.1;
    const downValWon = Math.round(targetPrice * downPercent);
    const months = monthSelect ? parseInt(monthSelect.value, 10) : 60;
    const annualRate = rateSelect ? parseFloat(rateSelect.value) : 0.059;
    const monthlyRate = annualRate / 12;
    const loanAmount = targetPrice * (1 - downPercent);

    let monthlyPayment = 0;
    let totalInterest = 0;
    let totalRepay = targetPrice;

    if (loanAmount > 0 && monthlyRate > 0) {
      monthlyPayment = (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, months)) / (Math.pow(1 + monthlyRate, months) - 1);
      totalRepay = monthlyPayment * months;
      totalInterest = totalRepay - loanAmount;
    }

    const estDown = document.getElementById('vdrEstDownText');
    const estMonths = document.getElementById('vdrEstMonthsText');
    const estRate = document.getElementById('vdrEstRateText');
    const estMonthly = document.getElementById('vdrEstMonthlyText');
    const estPrincipal = document.getElementById('vdrEstPrincipalText');
    const estInterest = document.getElementById('vdrEstInterestText');

    if (estDown) estDown.textContent = `${Math.round(downPercent * 100)}% (${downValWon.toLocaleString('ko-KR')}만원)`;
    if (estPrincipal) estPrincipal.textContent = `${Math.round(loanAmount).toLocaleString('ko-KR')}만원`;
    if (estMonths) estMonths.textContent = `${months}개월`;
    if (estRate) estRate.textContent = `연 ${(annualRate * 100).toFixed(1)}%`;
    if (estMonthly) estMonthly.textContent = `월 약 ${Math.round(monthlyPayment).toLocaleString('ko-KR')}만원`;
    if (estInterest) estInterest.textContent = `약 ${Math.round(totalInterest).toLocaleString('ko-KR')}만원`;

    const modal = document.getElementById('vdrEstimatePrintModal');
    if (modal) {
      modal.classList.remove('hidden');
      document.body.style.overflow = 'hidden';
      if (window.lucide) window.lucide.createIcons();
    }
  }"""

replace_open_estimate = """  openEstimateModal() {
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
  }"""

# 6. handleKakaoConsult 1544-0000 제거
target_kakao_alert = "alert('현재 차마트 카카오톡 1:1 전용 채널 개설 준비 중입니다. 방문 예약 신청 또는 대표번호(1544-0000)를 이용해 주시기 바랍니다.');"
replace_kakao_alert = "alert('현재 차마트 카카오톡 1:1 전용 채널 개설 준비 중입니다. 1:1 방문 예약 및 구매 상담 신청 폼을 이용해 주시기 바랍니다.');"

items = [
    (target_dealer, replace_dealer),
    (target_phone_ui, replace_phone_ui),
    (target_chamart_mob, replace_chamart_mob),
    (target_wayfinding_body, replace_wayfinding_body),
    (target_loan_calc, replace_loan_calc),
    (target_open_estimate, replace_open_estimate),
    (target_kakao_alert, replace_kakao_alert),
]

for idx, (old, new) in enumerate(items):
    if old not in code:
        print(f"FAILED on item {idx}: {old[:60]}...")
        raise ValueError(f"Target not found: item {idx}")
    code = code.replace(old, new, 1)

with open('src/chaficial/platform/ui/static/js/vehicle_detail_renderer.js', 'w', encoding='utf-8') as f:
    f.write(code)

print("Successfully applied DIRECTIVE 064 updates to vehicle_detail_renderer.js")
