// Cloudflare Pages Function: /api/chamart/vehicles/:id (DIRECTIVE 130 Compliant)
// Strict Real-Vehicle Detail: No fabricated 30 photos, real photos only

function isValidPhoto(url) {
  if (!url || typeof url !== 'string') return false;
  const u = url.trim().toLowerCase();
  if (!u) return false;
  if (u.includes('placeholder') || u.includes('slots') || u.includes('sample_car') || u.includes('no_photo')) return false;
  return true;
}

const NO_PHOTO_FALLBACK = '/static/img/no_photo.svg';

export async function onRequestGet({ request, params, env }) {
  const vehicleId = params.id;
  const db = env.DB;
  if (!db) {
    return new Response(JSON.stringify({ error: 'DB binding not found' }), { status: 500 });
  }

  try {
    // DIRECTIVE 131 TASK 2: 상세 조회 엄격 검증 (공개승인 1, 실차 0, 판매중 매물 필수, 그 외 무조건 404)
    const v = await db.prepare(`
      SELECT * FROM vehicles 
      WHERE id = ? 
        AND is_public = 1 
        AND is_demo = 0 
        AND publishing_status IN ('APPROVED', 'PUBLISHED')
        AND status IN ('AVAILABLE', 'FOR_SALE')
    `).bind(vehicleId).first();

    if (!v) {
      return new Response(JSON.stringify({ error: '공개된 차량 정보를 찾을 수 없거나 판매가 중지되었습니다.' }), { 
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // DIRECTIVE 132-A TASK 3: 승인된 공개 사진만 조회 (approval_status='APPROVED' & public_visibility='PUBLIC')
    // 미승인 사진이나 임의 대체 사진은 100% 제외
    const photosRes = await db.prepare(`
      SELECT * FROM vehicle_photos 
      WHERE vehicle_id = ? 
        AND approval_status = 'APPROVED' 
        AND public_visibility = 'PUBLIC'
      ORDER BY is_primary DESC, sort_order ASC
    `).bind(vehicleId).all();

    let validPhotos = (photosRes.results || [])
      .filter(p => isValidPhoto(p.photo_url))
      .map(p => ({
        photo_url: p.photo_url,
        caption: p.caption || '실차 사진',
        display_label: p.display_label || p.caption || '실차 사진',
        category: p.category || 'EXTERIOR'
      }));

    // 승인된 실차 사진이 전무한 경우 정직한 '사진 준비 중' 1장 설정 (미승인 primary_photo_url 우회 절대 금지)
    if (validPhotos.length === 0) {
      validPhotos.push({
        photo_url: NO_PHOTO_FALLBACK,
        caption: '실차 사진 준비 중',
        display_label: '사진 준비 중',
        category: 'PREPARING'
      });
    }

    let options = [];
    try { if (v.options_json) options = JSON.parse(v.options_json); } catch (e) {}

    // DIRECTIVE 132-A FINAL CLOSEOUT TASK 1: 실제 판매 상사 정보 및 플랫폼 역할 구분
    const listing = await db.prepare(
      'SELECT * FROM vehicle_listings WHERE vehicle_id = ? LIMIT 1'
    ).bind(vehicleId).first();

    const isChamartOwned = (v.listing_ownership_type === 'OWNED' || v.listing_ownership_type === 'CHAMART_OWNED');
    const sellerName = isChamartOwned ? '차마트 직영' : (listing?.raw_seller_name || '제휴 상사');
    const sellerLocation = isChamartOwned 
      ? '서울특별시 성동구 용답동 장한평 자동차매매단지' 
      : (listing?.raw_seller_location || '소재지 확인 대기');
    const branchName = isChamartOwned ? '차마트 장한평 본사 직영점' : `${sellerName} (제휴 상사)`;

    const detail = {
      id: v.id,
      plate_number: v.plate_number,
      vin: v.vin || null,
      manufacturer: v.manufacturer || (v.model_name.startsWith('기아') ? '기아' : v.model_name.startsWith('제네시스') ? '제네시스' : '현대'),
      model_name: v.model_name,
      trim: v.trim || null,
      year: v.year,
      first_registration_date: v.first_registration_date || null,
      mileage: v.mileage,
      displacement_cc: v.displacement_cc || null,
      fuel_type: v.fuel_type,
      transmission: v.transmission,
      drive_type: v.drive_type || null,
      body_type: v.body_type || null,
      color: v.color,
      interior_color: v.interior_color || null,
      target_price: v.target_price,
      monthly_payment_estimate: Math.round((v.target_price || 0) * 10000 / 48 / 10000),
      sales_conditions: v.sales_conditions || '실차 진단 및 상세 조건 확인 대기',
      ad_description: v.ad_description || `${v.model_name} 실매물 차량입니다.`,
      ad_highlights: v.ad_highlights || '실차 등록 정보 확인 대기',
      ad_notices: v.ad_notices || '방문 예약 후 현장에서 실차 확인이 가능합니다.',
      photos: validPhotos,
      photo_count: validPhotos.length,
      has_real_photos: validPhotos.some(p => p.photo_url !== NO_PHOTO_FALLBACK),
      options: options,
      // DIRECTIVE 130 P0 진실성 보정: 허위 가상 보증/사고이력/시세차액 날조 완전 폐기
      accident_summary: {
        is_accident_free: v.accident_desc ? (v.accident_desc.includes('무사고') ? true : false) : null,
        simple_repair: v.accident_desc ? v.accident_desc.includes('단순수리') : null,
        major_frame_damage: v.accident_desc ? v.accident_desc.includes('프레임') : null,
        total_loss: null,
        flood: null,
        inspection_status: v.inspection_record_url ? '성능점검부 확인 완료' : '성능점검 서류 확인 대기',
        mortgage_status: '자동차등록원부(을부) 조회 대기 (현장 실차 확인 시 열람 가능)',
        insurance_history_count: null,
        owner_change_count: null
      },
      dealer_info: {
        company: sellerName,
        role: isChamartOwned ? '차마트 직영 판매' : '제휴 상사 위탁 판매',
        platform_role: '차마트 온라인 중개 플랫폼 (실차 정보 중개 및 방문 예약)',
        contact: null, // DIRECTIVE 132-A: 임의 가짜 전화번호 02-2244-8800 영구 삭제! 고객센터 또는 방문 예약 이용
        address: sellerLocation
      },
      price_comparison: {
        market_average_price: null,
        difference_amount: null,
        advantage_text: '실차 진단 및 정밀 시세 분석 대기'
      },
      branch_name: branchName,
      is_public: !!v.is_public,
      publishing_status: v.publishing_status || 'APPROVED',
      listing_ownership_type: v.listing_ownership_type || 'UNKNOWN',
      is_chamart_owned: isChamartOwned,
      is_priority_exposure: !!v.is_priority_exposure,
      updated_at: v.updated_at || new Date().toISOString()
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
