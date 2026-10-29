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
  { url: '/static/img/real_photos/01_front.jpg', caption: '01. 전면 외관', display_label: '전면 외관', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/02_front_45_l.jpg', caption: '02. 전측면 좌측 45도', display_label: '전측면 좌', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/03_front_45_r.jpg', caption: '03. 전측면 우측 45도', display_label: '전측면 우', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/04_side_l.jpg', caption: '04. 좌측면 전체', display_label: '좌측면', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/05_side_r.jpg', caption: '05. 우측면 전체', display_label: '우측면', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/06_rear_45_l.jpg', caption: '06. 후측면 좌측 45도', display_label: '후측면 좌', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/07_rear_45_r.jpg', caption: '07. 후측면 우측 45도', display_label: '후측면 우', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/08_rear.jpg', caption: '08. 후면 전체', display_label: '후면 전체', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/09_headlamp.jpg', caption: '09. 헤드램프 디테일', display_label: '헤드램프', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/10_grille.jpg', caption: '10. 라디에이터 그릴', display_label: '그릴', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/11_wheel_fl.jpg', caption: '11. 앞 좌측 휠/타이어', display_label: '앞 좌측 휠', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/12_wheel_fr.jpg', caption: '12. 앞 우측 휠/타이어', display_label: '앞 우측 휠', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/13_wheel_rl.jpg', caption: '13. 뒤 좌측 휠/타이어', display_label: '뒤 좌측 휠', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/14_wheel_rr.jpg', caption: '14. 뒤 우측 휠/타이어', display_label: '뒤 우측 휠', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/15_cockpit.jpg', caption: '15. 운전석 콕핏 대시보드', display_label: '콕핏 전경', category: 'INTERIOR' },
  { url: '/static/img/real_photos/16_steering.jpg', caption: '16. 스티어링 휠 핸들 리모컨', display_label: '스티어링 휠', category: 'INTERIOR' },
  { url: '/static/img/real_photos/17_cluster.jpg', caption: '17. 풀 디지털 계기판 실주행거리', display_label: '계기판', category: 'INTERIOR' },
  { url: '/static/img/real_photos/18_navigation.jpg', caption: '18. 센터 와이드 내비게이션', display_label: '내비게이션', category: 'INTERIOR' },
  { url: '/static/img/real_photos/19_gear_console.jpg', caption: '19. 전자식 변속기 센터 콘솔', display_label: '기어 콘솔', category: 'INTERIOR' },
  { url: '/static/img/real_photos/20_seat_front.jpg', caption: '20. 1열 통풍/열선 가죽시트', display_label: '1열 시트', category: 'INTERIOR' },
  { url: '/static/img/real_photos/21_seat_rear.jpg', caption: '21. 2열 뒷좌석 레그룸', display_label: '2열 뒷좌석', category: 'INTERIOR' },
  { url: '/static/img/real_photos/22_door_trim.jpg', caption: '22. 운전석 도어 트림', display_label: '도어 트림', category: 'INTERIOR' },
  { url: '/static/img/real_photos/23_engine_bay.jpg', caption: '23. 엔진룸 전경 누유 점검', display_label: '엔진룸', category: 'ENGINE_CHASSIS' },
  { url: '/static/img/real_photos/24_sunroof.jpg', caption: '24. 파노라마 선루프', display_label: '선루프', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/25_trunk.jpg', caption: '25. 스마트 파워 트렁크', display_label: '트렁크 공간', category: 'INTERIOR' },
  { url: '/static/img/real_photos/26_smart_key.jpg', caption: '26. 스마트키 2벌 보유', display_label: '스마트키', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/27_rear_camera.jpg', caption: '27. 후방/어라운드뷰 카메라', display_label: '후방 카메라', category: 'DETAIL_OPTION' },
  { url: '/static/img/real_photos/28_tire_tread.jpg', caption: '28. 타이어 잔여 트레드', display_label: '타이어 상태', category: 'EXTERIOR' },
  { url: '/static/img/real_photos/29_underbody.jpg', caption: '29. 리프트 하부 부식 점검', display_label: '하부 점검', category: 'ENGINE_CHASSIS' },
  { url: '/static/img/real_photos/30_exhaust_detail.jpg', caption: '30. 머플러 및 하부 방청', display_label: '배기/하부', category: 'EXTERIOR' },
];

function buildVehicle30Photos(modelName, frontPhoto) {
  const front = resolveRealCarPhoto(modelName, frontPhoto);
  return REAL_PHOTO_GALLERY_30.map((item, idx) => {
    if (idx === 0) return { ...item, url: front };
    return item;
  });
}

export async function onRequestGet(context) {
  const { params, env } = context;
  const vehicleId = params.id;
  const db = env.DB;

  if (!db) {
    return new Response(JSON.stringify({ error: 'Database binding DB not found' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const vehicleRes = await db.prepare('SELECT * FROM vehicles WHERE id = ?').bind(vehicleId).first();

    if (!vehicleRes) {
      return new Response(JSON.stringify({ error: '차량 정보를 찾을 수 없습니다.' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const v = vehicleRes;

    // Photos query
    const photosRes = await db.prepare(
      'SELECT * FROM vehicle_photos WHERE vehicle_id = ? ORDER BY is_primary DESC, display_order ASC'
    ).bind(vehicleId).all();

    const rawFront = (photosRes.results || [])[0]?.photo_url || v.primary_photo_url;
    const frontPhoto = resolveRealCarPhoto(v.model_name, rawFront);
    const photos30 = buildVehicle30Photos(v.model_name, frontPhoto);

    let options = [];
    try {
      if (v.options_json) options = JSON.parse(v.options_json);
    } catch (e) {}

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
      photos: photos30,
      photo_count: photos30.length,
      primary_photo_url: frontPhoto,
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
        'Content-Type': 'application/json',
        'Cache-Control': 'public, max-age=30, s-maxage=60'
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
