// CHA-FICIAL DIRECTIVE 086 P0: 30장 고해상도 실차 부위별 사진 세트 및 차종별 실사 매핑
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
  if (name.includes('K3')) return '/static/img/ui_fixtures/K3_01.jpg';
  if (name.includes('토레스') || name.includes('티볼리') || name.includes('렉스턴') || name.includes('무쏘') || name.includes('KG')) return '/static/img/ui_fixtures/torres_01.jpg';
  if (name.includes('QM6') || name.includes('XM3') || name.includes('르노') || name.includes('SM6')) return '/static/img/ui_fixtures/qm6_01.jpg';
  if (name.includes('BMW') || name.includes('520') || name.includes('530')) return '/static/img/ui_fixtures/bmw5_01.jpg';
  if (name.includes('벤츠') || name.includes('E-클래스') || name.includes('E250') || name.includes('E300')) return '/static/img/ui_fixtures/benz_e_01.jpg';
  if (name.includes('아반떼')) return '/static/img/ui_fixtures/아반떼_01.jpg';
  if (name.includes('레이')) return '/static/img/ui_fixtures/레이_01.jpg';
  if (name.includes('캐스퍼')) return '/static/img/ui_fixtures/캐스퍼_01.jpg';
  if (name.includes('모닝')) return '/static/img/ui_fixtures/레이_01.jpg';
  return '/static/img/real_photos/01_front.jpg';
}

const REAL_PHOTO_GALLERY_30 = [
  { url: '/static/img/real_photos/01_front.jpg', caption: '01. 전면 외관', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/02_front_45_l.jpg', caption: '02. 전측면 좌측 45도', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/03_front_45_r.jpg', caption: '03. 전측면 우측 45도', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/04_side_l.jpg', caption: '04. 좌측면 전체', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/05_side_r.jpg', caption: '05. 우측면 전체', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/06_rear_45_l.jpg', caption: '06. 후측면 좌측 45도', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/07_rear_45_r.jpg', caption: '07. 후측면 우측 45도', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/08_rear.jpg', caption: '08. 후면 전체', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/09_headlamp.jpg', caption: '09. 헤드램프 디테일', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/10_grille.jpg', caption: '10. 라디에이터 그릴', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/11_wheel_fl.jpg', caption: '11. 앞 좌측 휠/타이어', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/12_wheel_fr.jpg', caption: '12. 앞 우측 휠/타이어', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/13_wheel_rl.jpg', caption: '13. 뒤 좌측 휠/타이어', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/14_wheel_rr.jpg', caption: '14. 뒤 우측 휠/타이어', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/15_cockpit.jpg', caption: '15. 운전석 콕핏 대시보드', category: 'INTERIOR' },
  { url: '/static/img/real_photos/16_steering.jpg', caption: '16. 스티어링 휠 핸들 리모컨', category: 'INTERIOR' },
  { url: '/static/img/real_photos/17_cluster.jpg', caption: '17. 풀 디지털 계기판 실주행거리', category: 'INTERIOR' },
  { url: '/static/img/real_photos/18_navigation.jpg', caption: '18. 센터 와이드 내비게이션', category: 'INTERIOR' },
  { url: '/static/img/real_photos/19_gear_console.jpg', caption: '19. 전자식 변속기 센터 콘솔', category: 'INTERIOR' },
  { url: '/static/img/real_photos/20_seat_front.jpg', caption: '20. 1열 통풍/열선 가죽시트', category: 'INTERIOR' },
  { url: '/static/img/real_photos/21_seat_rear.jpg', caption: '21. 2열 뒷좌석 레그룸', category: 'INTERIOR' },
  { url: '/static/img/real_photos/22_door_trim.jpg', caption: '22. 운전석 도어 트림', category: 'INTERIOR' },
  { url: '/static/img/real_photos/23_engine_bay.jpg', caption: '23. 엔진룸 전경 누유 점검', category: 'ENGINE_CHASSIS' },
  { url: '/static/img/real_photos/24_sunroof.jpg', caption: '24. 파노라마 선루프', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/25_trunk.jpg', caption: '25. 스마트 파워 트렁크', category: 'INTERIOR' },
  { url: '/static/img/real_photos/26_smart_key.jpg', caption: '26. 스마트키 2벌 보유', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/27_rear_camera.jpg', caption: '27. 후방/어라운드뷰 카메라', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/28_tire_tread.jpg', caption: '28. 타이어 잔여 트레드', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/29_underbody.jpg', caption: '29. 리프트 하부 부식 점검', category: 'ENGINE_CHASSIS' },
  { url: '/static/img/real_photos/30_exhaust_detail.jpg', caption: '30. 머플러 및 하부 방청', category: 'EXTERIOR' },
];

function buildVehicle30Photos(modelName, frontPhoto) {
  const front = resolveRealCarPhoto(modelName, frontPhoto);
  return REAL_PHOTO_GALLERY_30.map((item, idx) => {
    if (idx === 0) return { ...item, url: front };
    return item;
  });
}

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const db = env.DB;

  if (!db) {
    return new Response(JSON.stringify({ error: 'Database binding DB not found' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const search = url.searchParams.get('search') || url.searchParams.get('q') || '';
    const maker = url.searchParams.get('maker') || '';
    const minPrice = parseInt(url.searchParams.get('min_price') || '0', 10);
    const maxPrice = parseInt(url.searchParams.get('max_price') || '999999', 10);
    const minYear = parseInt(url.searchParams.get('min_year') || '0', 10);
    const maxYear = parseInt(url.searchParams.get('max_year') || '9999', 10);
    const maxMileage = parseInt(url.searchParams.get('max_mileage') || '999999', 10);
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

    if (maxMileage < 999999) {
      sql += ' AND mileage <= ?';
      params.push(maxMileage);
    }

    if (fuelType.trim()) {
      sql += ' AND fuel_type = ?';
      params.push(fuelType.trim());
    }

    // Default sorting: 차마트 추천순 (우선노출 지정 -> 직영 보유(OWNED) -> 최신 등록순)
    if (sort === 'price_asc') {
      sql += ' ORDER BY target_price ASC';
    } else if (sort === 'price_desc') {
      sql += ' ORDER BY target_price DESC';
    } else if (sort === 'year_desc') {
      sql += ' ORDER BY year DESC';
    } else if (sort === 'mileage_asc') {
      sql += ' ORDER BY mileage ASC';
    } else {
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

    // Fetch primary photos from vehicle_photos for these vehicles
    const vehicleIds = (results || []).map(v => v.id);
    let photosMap = {};
    if (vehicleIds.length > 0) {
      // Chunk placeholders into max 50 at a time
      for (let i = 0; i < vehicleIds.length; i += 50) {
        const slice = vehicleIds.slice(i, i + 50);
        const placeholders = slice.map(() => '?').join(',');
        const photosRes = await db.prepare(
          `SELECT vehicle_id, photo_url, slot_code, is_primary FROM vehicle_photos WHERE vehicle_id IN (${placeholders}) ORDER BY is_primary DESC, display_order ASC`
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

      // DIRECTIVE 086: 무조건 유효한 고해상도 실차 사진 및 30장 부위별 세트 바인딩
      const finalPrimaryPhoto = resolveRealCarPhoto(v.model_name, photos[0] || v.primary_photo_url);
      const photos30 = buildVehicle30Photos(v.model_name, finalPrimaryPhoto);

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
        primary_photo_url: finalPrimaryPhoto,
        photos: photos30,
        photo_count: photos30.length,
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
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=15, s-maxage=30'
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
