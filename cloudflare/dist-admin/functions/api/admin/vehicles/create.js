export async function onRequestPost(context) {
  const { request, env } = context;
  const db = env.DB;

  if (!db) {
    return new Response(JSON.stringify({ error: 'Database binding DB not found' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const body = await request.json();
    const {
      plate_number, model_name, manufacturer, trim, year, mileage,
      fuel_type, transmission, color, purchase_price, target_price,
      listing_ownership_type, is_priority_exposure, is_public,
      primary_photo_url, body_type, displacement_cc, options
    } = body;

    if (!plate_number || !model_name) {
      return new Response(JSON.stringify({ error: '차량 번호와 모델명은 필수 입력 항목입니다.' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const ownership = listing_ownership_type || ({ CHAMART_OWNED: 'OWNED', PARTNER_APPROVED: 'PARTNER_CONFIRMED', PARTNER_CANDIDATE: 'EXTERNAL', MARKET_OBSERVED: 'EXTERNAL' }[body.ownership_type] || 'UNKNOWN');
    const vehicleId = crypto.randomUUID();
    const now = new Date().toISOString();
    const branchId = '61fea9a4-58f0-42bd-862c-14fd16d0d21c'; // 장한평 본사
    const optionsJson = JSON.stringify(options || ['스마트키', '내비게이션', '후방카메라', '열선시트']);
    const timelineJson = JSON.stringify([{
      event: 'REGISTERED',
      timestamp: now,
      note: '관리자 신규 차량 등록 (Cloudflare D1)'
    }]);

    await db.prepare(`
      INSERT INTO vehicles (
        id, branch_id, plate_number, model_name, manufacturer, trim, year, mileage,
        fuel_type, transmission, color, purchase_price, target_price,
        status, is_demo, timeline_json, created_at, updated_at,
        listing_ownership_type, is_priority_exposure, priority_rank,
        is_public, publishing_status, primary_photo_url, body_type, displacement_cc,
        options_json
      ) VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        'AVAILABLE', 0, ?, ?, ?,
        ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?
      )
    `).bind(
      vehicleId, branchId, plate_number, model_name,
      manufacturer || '현대',
      trim || '기본형',
      parseInt(year || '2023', 10),
      parseInt(mileage || '30000', 10),
      fuel_type || '가솔린',
      transmission || '오토',
      color || '화이트',
      parseInt(purchase_price || '1500', 10),
      parseInt(target_price || '1800', 10),
      timelineJson, now, now,
      ownership,
      is_priority_exposure ? 1 : 0,
      is_priority_exposure ? 100 : 0,
      is_public ? 1 : 0,
      is_public ? 'APPROVED' : 'DRAFT',
      primary_photo_url || '/static/img/sample_car.jpg',
      body_type || '세단',
      parseInt(displacement_cc || '1999', 10),
      optionsJson
    ).run();

    // Insert primary photo record if provided
    if (primary_photo_url) {
      const photoId = crypto.randomUUID();
      await db.prepare(`
        INSERT INTO vehicle_photos (
          id, vehicle_id, photo_url, slot_code, category_code, display_order, is_primary, approval_status, created_at
        ) VALUES (?, ?, ?, 'EXT_FRONT', 'EXTERIOR', 1, 1, 'APPROVED', ?)
      `).bind(photoId, vehicleId, primary_photo_url, now).run();
    }

    return new Response(JSON.stringify({
      success: true,
      vehicle_id: vehicleId,
      message: '차량이 성공적으로 등록되었습니다.'
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
