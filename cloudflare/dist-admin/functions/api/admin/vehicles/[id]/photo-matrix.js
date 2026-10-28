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
    const photosRes = await db.prepare(
      'SELECT * FROM vehicle_photos WHERE vehicle_id = ? ORDER BY is_primary DESC, display_order ASC'
    ).bind(vehicleId).all();

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
      if (p.slot_code) {
        uploadedMap[p.slot_code] = {
          photo_id: p.id,
          photo_url: p.photo_url
        };
      }
    }

    const slots = standardSlots.map((s, idx) => {
      const match = uploadedMap[s.code];
      return {
        slot_code: s.code,
        display_label: s.label,
        category_code: s.category,
        display_order: idx + 1,
        is_uploaded: !!match,
        photo_id: match ? match.photo_id : null,
        photo_url: match ? match.photo_url : null
      };
    });

    return new Response(JSON.stringify({
      vehicle_id: vehicleId,
      total_slots: 45,
      configured_slots: standardSlots.length,
      uploaded_count: Object.keys(uploadedMap).length,
      slots: slots
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

export async function onRequestPost(context) {
  const { request, params, env } = context;
  const vehicleId = params.id;
  const db = env.DB;

  if (!db) {
    return new Response(JSON.stringify({ error: 'Database binding DB not found' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const body = await request.json();
    const { slot_code, photo_url, category_code, display_label } = body;

    if (!slot_code || !photo_url) {
      return new Response(JSON.stringify({ error: 'slot_code와 photo_url은 필수입니다.' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const photoId = 'PHO-' + crypto.randomUUID().slice(0, 8);
    const now = new Date().toISOString();
    const isPrimary = slot_code === 'EXT_FRONT' ? 1 : 0;

    // Check if slot already has photo
    const existing = await db.prepare(
      'SELECT id FROM vehicle_photos WHERE vehicle_id = ? AND slot_code = ?'
    ).bind(vehicleId, slot_code).first();

    if (existing) {
      await db.prepare(`
        UPDATE vehicle_photos SET
          photo_url = ?,
          approval_status = 'APPROVED'
        WHERE id = ?
      `).bind(photo_url, existing.id).run();
    } else {
      await db.prepare(`
        INSERT INTO vehicle_photos (
          id, vehicle_id, photo_url, slot_code, category_code, display_order, is_primary, approval_status, created_at
        ) VALUES (?, ?, ?, ?, ?, 1, ?, 'APPROVED', ?)
      `).bind(photoId, vehicleId, photo_url, slot_code, category_code || 'EXTERIOR', isPrimary, now).run();
    }

    // If primary, also update vehicle primary_photo_url
    if (isPrimary) {
      await db.prepare('UPDATE vehicles SET primary_photo_url = ? WHERE id = ?').bind(photo_url, vehicleId).run();
    }

    return new Response(JSON.stringify({
      success: true,
      vehicle_id: vehicleId,
      slot_code: slot_code,
      photo_url: photo_url,
      message: '부위별 사진 슬롯이 성공적으로 등록되었습니다.'
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
