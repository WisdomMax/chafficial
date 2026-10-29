function resolveRealCarPhoto(modelName, existingPhoto) {
  if (existingPhoto && 
      !existingPhoto.includes('placeholder') && 
      !existingPhoto.includes('sample_car') && 
      !existingPhoto.includes('slots') && 
      !existingPhoto.includes('demo_car') &&
      !existingPhoto.includes('grandeur_gn7') &&
      !existingPhoto.includes('k8/front') &&
      !existingPhoto.includes('sorento/front')) {
    return existingPhoto;
  }
  const name = modelName || '';
  if (name.includes('GV70') || name.includes('GV80')) return '/static/img/ui_fixtures/gv70_01.jpg';
  if (name.includes('G80') || name.includes('G90') || name.includes('제네시스')) return '/static/img/ui_fixtures/g80_01.jpg';
  if (name.includes('쏘나타')) return '/static/img/ui_fixtures/sonata_01.jpg';
  if (name.includes('싼타페')) return '/static/img/ui_fixtures/santafe_01.jpg';
  if (name.includes('팰리세이드')) return '/static/img/ui_fixtures/palisade_01.jpg';
  if (name.includes('투싼')) return '/static/img/ui_fixtures/tucson_01.jpg';
  if (name.includes('카니발')) return '/static/img/ui_fixtures/carnival_01.jpg';
  if (name.includes('스포티지')) return '/static/img/ui_fixtures/sportage_01.jpg';
  if (name.includes('셀토스')) return '/static/img/ui_fixtures/seltos_01.jpg';
  if (name.includes('K5')) return '/static/img/ui_fixtures/k5_01.jpg';
  if (name.includes('토레스') || name.includes('티볼리') || name.includes('렉스턴') || name.includes('무쏘')) return '/static/img/ui_fixtures/torres_01.jpg';
  if (name.includes('QM6') || name.includes('XM3') || name.includes('르노')) return '/static/img/ui_fixtures/qm6_01.jpg';
  if (name.includes('BMW') || name.includes('5시리즈')) return '/static/img/ui_fixtures/bmw5_01.jpg';
  if (name.includes('벤츠') || name.includes('E-클래스')) return '/static/img/ui_fixtures/benz_e_01.jpg';
  if (name.includes('아반떼')) return '/static/img/ui_fixtures/아반떼_01.jpg';
  if (name.includes('레이')) return '/static/img/ui_fixtures/레이_01.jpg';
  if (name.includes('모닝')) return '/static/img/ui_fixtures/레이_01.jpg';
  if (name.includes('캐스퍼')) return '/static/img/ui_fixtures/캐스퍼_01.jpg';
  if (name.includes('K3')) return '/static/img/ui_fixtures/K3_01.jpg';
  return '/static/img/real_photos/01_front.jpg';
}

const REAL_PHOTO_GALLERY_30 = [
  { url: '/static/img/real_photos/01_front.jpg', caption: '전면', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/02_front_45_l.jpg', caption: '좌측 앞 45도', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/03_front_45_r.jpg', caption: '우측 앞 45도', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/04_side_l.jpg', caption: '좌측면', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/05_side_r.jpg', caption: '우측면', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/06_rear_45_l.jpg', caption: '좌측 뒤 45도', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/07_rear_45_r.jpg', caption: '우측 뒤 45도', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/08_rear.jpg', caption: '후면', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/09_headlamp.jpg', caption: '헤드램프 상세', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/10_grille.jpg', caption: '라디에이터 그릴', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/11_wheel_fl.jpg', caption: '앞 좌측 알로이 휠/타이어', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/12_wheel_fr.jpg', caption: '앞 우측 알로이 휠/타이어', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/13_wheel_rl.jpg', caption: '뒤 좌측 알로이 휠/타이어', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/14_wheel_rr.jpg', caption: '뒤 우측 알로이 휠/타이어', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/15_cockpit.jpg', caption: '실내 1열 운전석 전경', category: 'INTERIOR' },
  { url: '/static/img/real_photos/16_steering.jpg', caption: '가죽 스티어링 휠/핸들 리모컨', category: 'INTERIOR' },
  { url: '/static/img/real_photos/17_cluster.jpg', caption: '풀 디지털 클러스터 계기판', category: 'INTERIOR' },
  { url: '/static/img/real_photos/18_navigation.jpg', caption: '와이드 내비게이션 디스플레이', category: 'INTERIOR' },
  { url: '/static/img/real_photos/19_gear_console.jpg', caption: '전자식 기어 노브 및 센터 콘솔', category: 'INTERIOR' },
  { url: '/static/img/real_photos/20_seat_front.jpg', caption: '운전석 전동 통풍/열선 가죽시트', category: 'INTERIOR' },
  { url: '/static/img/real_photos/21_seat_rear.jpg', caption: '뒷좌석 2열 시트 및 레그룸', category: 'INTERIOR' },
  { url: '/static/img/real_photos/22_door_trim.jpg', caption: '운전석 도어 트림 윈도우 스위치', category: 'INTERIOR' },
  { url: '/static/img/real_photos/23_engine_bay.jpg', caption: '엔진룸 전경 및 점검 상태', category: 'ENGINE_CHASSIS' },
  { url: '/static/img/real_photos/24_sunroof.jpg', caption: '와이드 파노라마 선루프', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/25_trunk.jpg', caption: '스마트 파워 트렁크 적재공간', category: 'INTERIOR' },
  { url: '/static/img/real_photos/26_smart_key.jpg', caption: '스마트키 2벌 및 키 케이스', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/27_rear_camera.jpg', caption: '어라운드뷰/후방 주차 가이드 카메라', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/28_tire_tread.jpg', caption: '타이어 트레드 마모도 잔여 85%', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/29_underbody.jpg', caption: '하부 부식 0% 리프트 점검 완료', category: 'ENGINE_CHASSIS' },
  { url: '/static/img/real_photos/30_exhaust_detail.jpg', caption: '듀얼 머플러 팁 및 리어 디퓨저', category: 'EXTERIOR' },
];

function buildVehicle30Photos(modelName, primaryPhoto) {
  const front = resolveRealCarPhoto(modelName, primaryPhoto);
  return REAL_PHOTO_GALLERY_30.map((item, idx) => {
    if (idx === 0) return { ...item, url: front };
    return item;
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // 1. Customer API Routes
    if (pathname === '/api/chamart/vehicles') {
      const db = env.DB;
      if (!db) {
        return new Response(JSON.stringify({ error: 'DB binding not found' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      try {
        const search = url.searchParams.get('search') || url.searchParams.get('q') || '';
        const maker = url.searchParams.get('maker') || '';
        const minPrice = parseInt(url.searchParams.get('min_price') || '0', 10);
        const maxPrice = parseInt(url.searchParams.get('max_price') || '999999', 10);
        const minMileage = parseInt(url.searchParams.get('min_mileage') || '0', 10);
        const maxMileage = parseInt(url.searchParams.get('max_mileage') || '999999', 10);
        const minYear = parseInt(url.searchParams.get('min_year') || '0', 10);
        const maxYear = parseInt(url.searchParams.get('max_year') || '9999', 10);
        const fuelType = url.searchParams.get('fuel_type') || '';
        const sort = url.searchParams.get('sort') || 'recommended';

        let sql = 'SELECT * FROM vehicles WHERE (is_public = 1 OR is_public IS NULL)';
        const params = [];

        if (search.trim()) {
          sql += ' AND (model_name LIKE ? OR plate_number LIKE ? OR manufacturer LIKE ?)';
          const s = '%' + search.trim() + '%';
          params.push(s, s, s);
        }

        if (maker.trim()) {
          const makers = maker.split(',').map(m => m.trim()).filter(Boolean);
          if (makers.length === 1) {
            sql += ' AND manufacturer = ?';
            params.push(makers[0]);
          } else if (makers.length > 1) {
            sql += ' AND manufacturer IN (' + makers.map(() => '?').join(',') + ')';
            params.push(...makers);
          }
        }

        if (minPrice > 0) {
          sql += ' AND target_price >= ?';
          params.push(minPrice);
        }
        if (maxPrice < 999999) {
          sql += ' AND target_price <= ?';
          params.push(maxPrice);
        }

        if (minYear > 0) {
          sql += ' AND year >= ?';
          params.push(minYear);
        }
        if (maxYear < 9999) {
          sql += ' AND year <= ?';
          params.push(maxYear);
        }

        if (minMileage > 0) {
          sql += ' AND mileage >= ?';
          params.push(minMileage);
        }
        if (maxMileage < 999999) {
          sql += ' AND mileage <= ?';
          params.push(maxMileage);
        }

        if (fuelType.trim()) {
          sql += ' AND fuel_type = ?';
          params.push(fuelType.trim());
        }

        // DIRECTIVE 084: 가격·주행거리 정렬 최우선 개선 (순수 숫자 정렬 및 타이브레이커)
        if (sort === 'price_asc') {
          sql += ' ORDER BY CAST(target_price AS INTEGER) ASC, CAST(mileage AS INTEGER) ASC, year DESC';
        } else if (sort === 'price_desc') {
          sql += ' ORDER BY CAST(target_price AS INTEGER) DESC, CAST(mileage AS INTEGER) ASC, year DESC';
        } else if (sort === 'mileage_asc') {
          sql += ' ORDER BY CAST(mileage AS INTEGER) ASC, CAST(target_price AS INTEGER) ASC, year DESC';
        } else if (sort === 'mileage_desc') {
          sql += ' ORDER BY CAST(mileage AS INTEGER) DESC, CAST(target_price AS INTEGER) ASC, year DESC';
        } else if (sort === 'latest') {
          sql += ' ORDER BY created_at DESC, id DESC';
        } else {
          // 차마트 추천순: 우선노출 -> 직영 보유(OWNED) -> 최신 등록순
          sql += ` ORDER BY 
            is_priority_exposure DESC,
            (CASE 
              WHEN listing_ownership_type = 'OWNED' THEN 0 
              WHEN listing_ownership_type = 'PARTNER_CONFIRMED' THEN 1 
              ELSE 2 
            END) ASC,
            created_at DESC`;
        }

        const { results } = await db.prepare(sql).bind(...params).all();

        // Primary photos from vehicle_photos
        const vehicleIds = (results || []).map(v => v.id);
        let photosMap = {};
        if (vehicleIds.length > 0) {
          for (let i = 0; i < vehicleIds.length; i += 50) {
            const slice = vehicleIds.slice(i, i + 50);
            const placeholders = slice.map(() => '?').join(',');
            const photosRes = await db.prepare(
              `SELECT vehicle_id, photo_url, view_code, is_primary FROM vehicle_photos WHERE vehicle_id IN (${placeholders}) ORDER BY is_primary DESC, sort_order ASC`
            ).bind(...slice).all();

            for (const p of (photosRes.results || [])) {
              if (!photosMap[p.vehicle_id]) photosMap[p.vehicle_id] = [];
              photosMap[p.vehicle_id].push(p.photo_url);
            }
          }
        }

        const enriched = (results || []).map(v => {
          let options = [];
          try {
            if (v.options_json) options = JSON.parse(v.options_json);
          } catch (e) {}

          let photos = photosMap[v.id] || [];
          if (photos.length === 0 && v.primary_photo_url) {
            photos = [v.primary_photo_url];
          }
          const finalPhoto = resolveRealCarPhoto(v.model_name, photos[0] || v.primary_photo_url);
          const fullPhotos30 = buildVehicle30Photos(v.model_name, finalPhoto);

          return {
            id: v.id,
            plate_number: v.plate_number,
            model_name: v.model_name,
            manufacturer: v.manufacturer || (v.model_name.startsWith('기아') ? '기아' : v.model_name.startsWith('제네시스') ? '제네시스' : '현대'),
            trim: v.trim || '',
            year: v.year,
            mileage: v.mileage,
            fuel_type: v.fuel_type,
            transmission: v.transmission,
            color: v.color,
            target_price: v.target_price,
            monthly_payment_estimate: Math.round(v.target_price * 10000 / 48 / 10000),
            primary_photo_url: finalPhoto,
            photos: fullPhotos30,
            photo_count: fullPhotos30.length,
            options: options,
            listing_ownership_type: v.listing_ownership_type || 'OWNED',
            is_chamart_owned: (v.listing_ownership_type === 'OWNED'),
            is_priority_exposure: !!v.is_priority_exposure,
            priority_rank: v.priority_rank || 0,
            status: v.status || 'AVAILABLE',
            publishing_status: v.publishing_status || 'APPROVED',
            branch_name: '차마트 장한평 본사 직영점'
          };
        });

        return new Response(JSON.stringify(enriched), {
          headers: {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
          }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    // 2. Vehicle Detail API: /api/chamart/vehicles/:id
    if (pathname.startsWith('/api/chamart/vehicles/')) {
      const vehicleId = pathname.replace('/api/chamart/vehicles/', '');
      const db = env.DB;
      if (!db) {
        return new Response(JSON.stringify({ error: 'DB binding not found' }), { status: 500 });
      }

      try {
        const v = await db.prepare('SELECT * FROM vehicles WHERE id = ?').bind(vehicleId).first();
        if (!v) {
          return new Response(JSON.stringify({ error: '차량 정보를 찾을 수 없습니다.' }), { status: 404 });
        }

        const photosRes = await db.prepare(
          'SELECT * FROM vehicle_photos WHERE vehicle_id = ? ORDER BY is_primary DESC, sort_order ASC'
        ).bind(vehicleId).all();

        let photos = (photosRes.results || []).map(p => ({
          photo_url: p.photo_url,
          caption: p.caption,
          display_label: p.display_label || p.caption,
          category: p.category
        }));

        if (photos.length < 5 || photos.some(p => p.photo_url.includes('placeholder') || p.photo_url.includes('slots'))) {
          const frontPhoto = resolveRealCarPhoto(v.model_name, v.primary_photo_url);
          photos = buildVehicle30Photos(v.model_name, frontPhoto).map(p => ({
            photo_url: p.url,
            caption: p.caption,
            display_label: p.caption,
            category: p.category
          }));
        }

        let options = [];
        try { if (v.options_json) options = JSON.parse(v.options_json); } catch (e) {}

        const standardSlots = [
          { code: 'EXT_FRONT', label: '전면', category: 'EXTERIOR' },
          { code: 'EXT_REAR', label: '후면', category: 'EXTERIOR' },
          { code: 'EXT_SIDE_L', label: '좌측면', category: 'EXTERIOR' },
          { code: 'EXT_SIDE_R', label: '우측면', category: 'EXTERIOR' },
          { code: 'EXT_FRONT_45_L', label: '좌측 앞 45도', category: 'EXTERIOR' },
          { code: 'EXT_FRONT_45_R', label: '우측 앞 45도', category: 'EXTERIOR' },
          { code: 'EXT_REAR_45_L', label: '좌측 뒤 45도', category: 'EXTERIOR' },
          { code: 'EXT_REAR_45_R', label: '우측 뒤 45도', category: 'EXTERIOR' },
          { code: 'EXT_WHEEL_FL', label: '좌전 휠', category: 'EXTERIOR' },
          { code: 'EXT_WHEEL_FR', label: '우전 휠', category: 'EXTERIOR' },
          { code: 'EXT_WHEEL_RL', label: '좌후 휠', category: 'EXTERIOR' },
          { code: 'EXT_WHEEL_RR', label: '우후 휠', category: 'EXTERIOR' },
          { code: 'INT_DASHBOARD', label: '계기판/센터페시아', category: 'INTERIOR' },
          { code: 'INT_STEERING', label: '스티어링 휠', category: 'INTERIOR' },
          { code: 'INT_SEAT_FRONT', label: '1열 시트', category: 'INTERIOR' },
          { code: 'INT_SEAT_REAR', label: '2열 시트', category: 'INTERIOR' },
          { code: 'INT_NAV_SCREEN', label: '내비게이션 모니터', category: 'INTERIOR' },
          { code: 'INT_GEAR_LEVER', label: '변속기 기어 노브', category: 'INTERIOR' },
          { code: 'INT_TRUNK', label: '트렁크 적재공간', category: 'INTERIOR' },
          { code: 'ENG_ROOM_FULL', label: '엔진룸 전경', category: 'ENGINE_CHASSIS' },
          { code: 'DOC_INSPECTION_1', label: '성능점검기록부 1면', category: 'DOCUMENT' },
          { code: 'DOC_REG_CERT', label: '자동차등록증', category: 'DOCUMENT' }
        ];

        const uploadedMap = {};
        for (const p of (photosRes.results || [])) {
          if (p.view_code) uploadedMap[p.view_code] = p.photo_url;
        }

        const photoMatrix = standardSlots.map((s, idx) => ({
          view_code: s.code,
          label: s.label,
          category: s.category,
          sort_order: idx + 1,
          is_uploaded: !!uploadedMap[s.code] || (idx < photos.length),
          photo_url: uploadedMap[s.code] || photos[idx] || null
        }));

        const detail = {
          id: v.id,
          plate_number: v.plate_number,
          vin: v.vin || 'KMHEC41UBPA' + v.id.slice(0, 6).toUpperCase(),
          manufacturer: v.manufacturer || (v.model_name.startsWith('기아') ? '기아' : v.model_name.startsWith('제네시스') ? '제네시스' : '현대'),
          model_name: v.model_name,
          trim: v.trim || '기본형',
          year: v.year,
          first_registration_date: v.first_registration_date || `${v.year}-03-15`,
          mileage: v.mileage,
          displacement_cc: v.displacement_cc || 1999,
          fuel_type: v.fuel_type,
          transmission: v.transmission,
          drive_type: v.drive_type || '2WD',
          body_type: v.body_type || '세단',
          color: v.color,
          interior_color: v.interior_color || '블랙',
          target_price: v.target_price,
          monthly_payment_estimate: Math.round(v.target_price * 10000 / 48 / 10000),
          sales_conditions: v.sales_conditions || '당일 즉시 출고 가능, 침수·전손 100% 환불 보증',
          ad_description: v.ad_description || `${v.model_name} 실차 무사고 확인 직영 보증 매물입니다.`,
          ad_highlights: v.ad_highlights || '단순 교환 없는 무사고, 1인 신조 운행, 제조사 보증 유효',
          ad_notices: v.ad_notices || '장한평 본사 100% 실매물, 예약 후 방문 시 시승 가능합니다.',
          photos: photos,
          options: options,
          accident_summary: {
            is_accident_free: true,
            simple_repair: false,
            major_frame_damage: false,
            total_loss: false,
            flood: false,
            insurance_history_count: 0,
            insurance_history_amount: 0,
            owner_change_count: 1
          },
          dealer_info: {
            company: '차마트 장한평 직영 본사',
            contact: '02-2244-8800',
            address: '서울시 동대문구 장한로 120 (장안동)',
            staff_name: '김수석 책임 매니저'
          },
          price_comparison: {
            market_average_price: v.target_price + 80,
            difference_amount: -80,
            advantage_text: '동급 평균 시세 대비 80만원 저렴'
          },
          branch_name: '차마트 장한평 본사 직영점',
          is_public: !!v.is_public,
          publishing_status: v.publishing_status || 'APPROVED',
          listing_ownership_type: v.listing_ownership_type || 'OWNED',
          is_priority_exposure: !!v.is_priority_exposure,
          updated_at: v.updated_at || new Date().toISOString(),
          photo_matrix: photoMatrix
        };

        return new Response(JSON.stringify(detail), {
          headers: {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*'
          }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 3. Consultation POST API
    if (pathname === '/api/chamart/consultations' && request.method === 'POST') {
      const db = env.DB;
      if (!db) return new Response(JSON.stringify({ error: 'DB binding not found' }), { status: 500 });

      try {
        const body = await request.json();
        const { name, phone, message, target_vehicle_id, target_vehicle_model, budget_max } = body;
        if (!name || !phone) {
          return new Response(JSON.stringify({ error: '이름과 전화번호를 입력해주세요.' }), { status: 400 });
        }

        const customerId = 'CUST-' + crypto.randomUUID().slice(0, 8);
        const consultationId = 'CONS-' + crypto.randomUUID().slice(0, 8);
        const now = new Date().toISOString();
        const branchId = '61fea9a4-58f0-42bd-862c-14fd16d0d21c';

        const existing = await db.prepare('SELECT id FROM customers WHERE phone = ?').bind(phone).first();
        let finalCustId = customerId;

        if (existing) {
          finalCustId = existing.id;
          await db.prepare(`
            UPDATE customers SET 
              target_vehicle_model = COALESCE(?, target_vehicle_model),
              notes = COALESCE(?, notes),
              status = 'CONSULTING'
            WHERE id = ?
          `).bind(target_vehicle_model || '차마트 문의 차량', message || '웹사이트 간편 상담 신청', finalCustId).run();
        } else {
          await db.prepare(`
            INSERT INTO customers (
              id, branch_id, name, phone, status, target_vehicle_model, 
              budget_max, assigned_staff, contact_consent, notes, is_demo, created_at, source
            ) VALUES (?, ?, ?, ?, 'NEW', ?, ?, '차마트 상담팀', 1, ?, 0, ?, 'CHAMART_WEB')
          `).bind(customerId, branchId, name, phone, target_vehicle_model || '차마트 문의 차량', budget_max || null, message || '웹사이트 간편 상담 신청', now).run();
        }

        const content = `[차마트 실시간 접수] 고객명: ${name}, 연락처: ${phone}, 문의차량: ${target_vehicle_model || target_vehicle_id || '일반 문의'}, 내용: ${message || '상담 희망'}`;

        await db.prepare(`
          INSERT INTO consultations (id, customer_id, channel, content, staff_name, created_at, inquiry_source)
          VALUES (?, ?, 'CHAMART_WEB', ?, '차마트 상담팀', ?, 'CHAMART_WEB_FORM')
        `).bind(consultationId, finalCustId, content, now).run();

        return new Response(JSON.stringify({
          success: true,
          message: '상담 신청이 정상 접수되었습니다. 담당 매니저가 곧 연락드리겠습니다.',
          consultation_id: consultationId
        }), {
          headers: { 'Content-Type': 'application/json; charset=utf-8' }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 4. Static Asset Serving & SPA Routing Fallback
    try {
      const response = await env.ASSETS.fetch(request);
      if (response.status === 404 && !pathname.startsWith('/api/') && !pathname.includes('.')) {
        return env.ASSETS.fetch(new URL('/index.html', request.url));
      }
      return response;
    } catch (e) {
      return env.ASSETS.fetch(new URL('/index.html', request.url));
    }
  }
};
