import sys

path = 'src/chaficial/platform/ui/static/js/vehicle_detail_renderer.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old_start = '  renderCarDiagramSvg(acc) {'
old_end = '  // 타이어 4개 바퀴 게이지'

start_idx = content.find(old_start)
end_idx = content.find(old_end)

if start_idx == -1 or end_idx == -1:
    print(f'Error finding markers: start={start_idx}, end={end_idx}')
    sys.exit(1)

new_code = '''  // 차량 부위별 독자 2D SVG 다이어그램 렌더러 (DIRECTIVE 075-A TASK 2~4)
  renderCarDiagramSvg(acc) {
    const parts = acc.diagram_parts || {};

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
                fill="#F8FAFC" stroke="#CBD5E1" stroke-width="2" stroke-linejoin="round" />
          
          <!-- 바퀴 4개 실루엣 (방향성 및 입체감) -->
          <rect x="34" y="90" width="12" height="42" rx="3" fill="#64748B" opacity="0.6" />
          <rect x="234" y="90" width="12" height="42" rx="3" fill="#64748B" opacity="0.6" />
          <rect x="34" y="320" width="12" height="42" rx="3" fill="#64748B" opacity="0.6" />
          <rect x="234" y="320" width="12" height="42" rx="3" fill="#64748B" opacity="0.6" />

          <!-- 앞유리창 & 뒷유리창 구역 (차량 구조 선명도 강화) -->
          <polygon points="70,126 210,126 195,155 85,155" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1" />
          <polygon points="85,310 195,310 208,340 72,340" fill="#E2E8F0" stroke="#CBD5E1" stroke-width="1" />

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
    const acc = this.data?.accident_summary || this.data?.accident_history || {};
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

'''

content = content[:start_idx] + new_code + content[end_idx:]
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print('Successfully updated vehicle_detail_renderer.js')
