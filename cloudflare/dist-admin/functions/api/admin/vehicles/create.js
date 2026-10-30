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
    
    // DIRECTIVE 095: 가짜 기본값 전면 폐기 - 입력값 없을 시 빈 상태/NULL 유지
    const optionsJson = options && Array.isArray(options) ? JSON.stringify(options) : '[]';
    const timelineJson = JSON.stringify([{
      event: 'REGISTERED',
      timestamp: now,
      note: '관리자 신규 차량 등록 (Cloudflare D1)'
    }]);

    const finalYear = year ? parseInt(year, 10) : null;
    const finalMileage = mileage ? parseInt(mileage, 10) : null;
    const finalPurchasePrice = purchase_price ? parseInt(purchase_price, 10) : 0;
    const finalTargetPrice = target_price ? parseInt(target_price, 10) : 0;
    const finalPhotoUrl = primary_photo_url && primary_photo_url.trim() ? primary_photo_url.trim() : null;

    const canPublish = is_public && finalTargetPrice > 0 && finalPhotoUrl;
    const publishingStatus = canPublish ? 'APPROVED' : 'DRAFT';
    const isPublicInt = canPublish ? 1 : 0;

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
      manufacturer ? manufacturer.trim() : '미분류',
      trim ? trim.trim() : '',
      finalYear,
      finalMileage,
      fuel_type ? fuel_type.trim() : '미확인',
      transmission ? transmission.trim() : '미확인',
      color ? color.trim() : '미확인',
      finalPurchasePrice,
      finalTargetPrice,
      timelineJson, now, now,
      ownership,
      is_priority_exposure ? 1 : 0,
      is_priority_exposure ? 100 : 0,
      isPublicInt,
      publishingStatus,
      finalPhotoUrl,
      body_type ? body_type.trim() : '미확인',
      displacement_cc ? parseInt(displacement_cc, 10) : null,
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
