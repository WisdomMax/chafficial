export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const pathname = url.pathname;
    const db = env.DB;

    // 1. Dashboard Stats API
    if (pathname === '/api/admin/dashboard') {
      if (!db) return new Response(JSON.stringify({ error: 'DB binding not found' }), { status: 500 });
      try {
        const totalVehicles = await db.prepare('SELECT COUNT(*) as cnt FROM vehicles').first();
        const publicVehicles = await db.prepare('SELECT COUNT(*) as cnt FROM vehicles WHERE is_public = 1').first();
        const ownedVehicles = await db.prepare("SELECT COUNT(*) as cnt FROM vehicles WHERE listing_ownership_type = 'OWNED'").first();
        const priorityVehicles = await db.prepare('SELECT COUNT(*) as cnt FROM vehicles WHERE is_priority_exposure = 1').first();
        const soldVehicles = await db.prepare("SELECT COUNT(*) as cnt FROM vehicles WHERE status = 'SOLD'").first();
        const totalConsultations = await db.prepare('SELECT COUNT(*) as cnt FROM consultations').first();
        const newConsultations = await db.prepare("SELECT COUNT(*) as cnt FROM customers WHERE status = 'NEW'").first();

        const recentVehicles = await db.prepare(
          'SELECT id, plate_number, model_name, target_price, year, mileage, is_public, is_priority_exposure, listing_ownership_type, created_at FROM vehicles ORDER BY created_at DESC LIMIT 5'
        ).all();

        const recentConsultations = await db.prepare(`
          SELECT c.id, c.content, c.created_at, cust.name as customer_name, cust.phone, cust.status, cust.target_vehicle_model
          FROM consultations c
          LEFT JOIN customers cust ON c.customer_id = cust.id
          ORDER BY c.created_at DESC LIMIT 5
        `).all();

        return new Response(JSON.stringify({
          metrics: {
            total_vehicles: totalVehicles ? totalVehicles.cnt : 0,
            public_vehicles: publicVehicles ? publicVehicles.cnt : 0,
            owned_vehicles: ownedVehicles ? ownedVehicles.cnt : 0,
            priority_exposure_count: priorityVehicles ? priorityVehicles.cnt : 0,
            sold_vehicles: soldVehicles ? soldVehicles.cnt : 0,
            total_consultations: totalConsultations ? totalConsultations.cnt : 0,
            new_inquiries: newConsultations ? newConsultations.cnt : 0
          },
          recent_vehicles: recentVehicles.results || [],
          recent_consultations: recentConsultations.results || []
        }), {
          headers: { 'Content-Type': 'application/json; charset=utf-8' }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 2. Vehicle List API: /api/admin/vehicles
    if (pathname === '/api/admin/vehicles' && request.method === 'GET') {
      if (!db) return new Response(JSON.stringify({ error: 'DB binding not found' }), { status: 500 });
      try {
        const search = url.searchParams.get('q') || url.searchParams.get('search') || '';
        const status = url.searchParams.get('status') || '';
        const ownership = url.searchParams.get('ownership') || '';
        const isPublic = url.searchParams.get('is_public');
        const limit = parseInt(url.searchParams.get('limit') || '50', 10);

        let sql = 'SELECT * FROM vehicles WHERE 1=1';
        let countSql = 'SELECT COUNT(*) as total FROM vehicles WHERE 1=1';
        const params = [];
        const countParams = [];

        if (search.trim()) {
          const s = '%' + search.trim() + '%';
          const cond = ' AND (model_name LIKE ? OR plate_number LIKE ? OR manufacturer LIKE ?)';
          sql += cond; countSql += cond;
          params.push(s, s, s); countParams.push(s, s, s);
        }

        if (status.trim()) {
          sql += ' AND status = ?'; countSql += ' AND status = ?';
          params.push(status.trim()); countParams.push(status.trim());
        }

        if (ownership.trim()) {
          sql += ' AND listing_ownership_type = ?'; countSql += ' AND listing_ownership_type = ?';
          params.push(ownership.trim()); countParams.push(ownership.trim());
        }

        if (isPublic !== null && isPublic !== undefined && isPublic !== '') {
          const pubInt = (isPublic === '1' || isPublic === 'true') ? 1 : 0;
          sql += ' AND is_public = ?'; countSql += ' AND is_public = ?';
          params.push(pubInt); countParams.push(pubInt);
        }

        sql += ' ORDER BY created_at DESC LIMIT ?';
        params.push(limit);

        const totalRes = await db.prepare(countSql).bind(...countParams).first();
        const { results } = await db.prepare(sql).bind(...params).all();

        return new Response(JSON.stringify({
          total: totalRes ? totalRes.total : 0,
          items: results || []
        }), {
          headers: { 'Content-Type': 'application/json; charset=utf-8' }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 3. Vehicle Create API: /api/admin/vehicles/create
    if (pathname === '/api/admin/vehicles/create' && request.method === 'POST') {
      if (!db) return new Response(JSON.stringify({ error: 'DB binding not found' }), { status: 500 });
      try {
        const body = await request.json();
        const {
          plate_number, model_name, manufacturer, trim, year, mileage,
          fuel_type, transmission, color, purchase_price, target_price,
          listing_ownership_type, is_priority_exposure, is_public,
          primary_photo_url
        } = body;

        if (!plate_number || !model_name) {
          return new Response(JSON.stringify({ error: '차량 번호와 모델명을 입력해주세요.' }), { status: 400 });
        }

        const ownership = listing_ownership_type || ({ CHAMART_OWNED: 'OWNED', PARTNER_APPROVED: 'PARTNER_CONFIRMED', PARTNER_CANDIDATE: 'EXTERNAL', MARKET_OBSERVED: 'EXTERNAL' }[body.ownership_type] || 'UNKNOWN');
        const vehicleId = crypto.randomUUID();
        const now = new Date().toISOString();
        const branchId = '61fea9a4-58f0-42bd-862c-14fd16d0d21c';
        const optionsJson = JSON.stringify(['스마트키', '내비게이션', '후방카메라', '통풍시트', '열선시트']);
        const timelineJson = JSON.stringify([{ event: 'REGISTERED', timestamp: now, note: '관리자 신규 등록 (D1)' }]);

        await db.prepare(`
          INSERT INTO vehicles (
            id, branch_id, plate_number, model_name, manufacturer, trim, year, mileage,
            fuel_type, transmission, color, purchase_price, target_price,
            status, is_demo, timeline_json, created_at, updated_at,
            listing_ownership_type, is_priority_exposure, priority_rank,
            is_public, publishing_status, primary_photo_url, body_type, displacement_cc, options_json
          ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            'AVAILABLE', 0, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, '세단', 1999, ?
          )
        `).bind(
          vehicleId, branchId, plate_number, model_name,
          manufacturer || '현대', trim || '기본형',
          parseInt(year || '2024', 10), parseInt(mileage || '25000', 10),
          fuel_type || '가솔린', transmission || '오토', color || '화이트',
          parseInt(purchase_price || '2000', 10), parseInt(target_price || '2300', 10),
          timelineJson, now, now,
          ownership,
          is_priority_exposure ? 1 : 0, is_priority_exposure ? 100 : 0,
          is_public ? 1 : 0, is_public ? 'APPROVED' : 'DRAFT',
          primary_photo_url || '/static/img/sample_car.jpg',
          optionsJson
        ).run();

        // Primary photo record
        if (primary_photo_url) {
          await db.prepare(`
            INSERT INTO vehicle_photos (id, vehicle_id, photo_url, view_code, category_code, sort_order, is_primary, approval_status, created_at)
            VALUES (?, ?, ?, 'EXT_FRONT', 'EXTERIOR', 1, 1, 'APPROVED', ?)
          `).bind(crypto.randomUUID(), vehicleId, primary_photo_url, now).run();
        }

        return new Response(JSON.stringify({
          success: true,
          vehicle_id: vehicleId,
          message: '차량이 성공적으로 D1에 등록되었습니다.'
        }), {
          headers: { 'Content-Type': 'application/json; charset=utf-8' }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 4. Toggle Publish API: /api/admin/vehicles/:id/toggle-publish
    if (pathname.includes('/toggle-publish') && request.method === 'POST') {
      const vehicleId = pathname.split('/')[4];
      if (!db) return new Response(JSON.stringify({ error: 'DB not found' }), { status: 500 });
      try {
        const v = await db.prepare('SELECT is_public FROM vehicles WHERE id = ?').bind(vehicleId).first();
        if (!v) return new Response(JSON.stringify({ error: '차량 없음' }), { status: 404 });

        const nextPub = v.is_public ? 0 : 1;
        const nextStatus = nextPub ? 'APPROVED' : 'DRAFT';
        const now = new Date().toISOString();

        await db.prepare('UPDATE vehicles SET is_public = ?, publishing_status = ?, updated_at = ? WHERE id = ?')
          .bind(nextPub, nextStatus, now, vehicleId).run();

        return new Response(JSON.stringify({
          success: true,
          is_public: !!nextPub,
          message: nextPub ? '고객 공개 승인 완료 (chamart.cc에 노출됨)' : '비공개(초안) 전환 완료'
        }), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 5. Toggle Priority API: /api/admin/vehicles/:id/toggle-priority
    if (pathname.includes('/toggle-priority') && request.method === 'POST') {
      const vehicleId = pathname.split('/')[4];
      if (!db) return new Response(JSON.stringify({ error: 'DB not found' }), { status: 500 });
      try {
        const v = await db.prepare('SELECT is_priority_exposure FROM vehicles WHERE id = ?').bind(vehicleId).first();
        if (!v) return new Response(JSON.stringify({ error: '차량 없음' }), { status: 404 });

        const nextPrio = v.is_priority_exposure ? 0 : 1;
        const rank = nextPrio ? 100 : 0;
        const reason = nextPrio ? '관리자 지정 차마트 직영 우선추천' : null;
        const now = new Date().toISOString();

        await db.prepare('UPDATE vehicles SET is_priority_exposure = ?, priority_rank = ?, priority_reason = ?, updated_at = ? WHERE id = ?')
          .bind(nextPrio, rank, reason, now, vehicleId).run();

        return new Response(JSON.stringify({
          success: true,
          is_priority_exposure: !!nextPrio,
          message: nextPrio ? '차마트 우선추천 매물로 지정되었습니다.' : '우선노출이 해제되었습니다.'
        }), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 6. Mark Sold API: /api/admin/vehicles/:id/mark-sold
    if (pathname.includes('/mark-sold') && request.method === 'POST') {
      const vehicleId = pathname.split('/')[4];
      if (!db) return new Response(JSON.stringify({ error: 'DB not found' }), { status: 500 });
      try {
        const now = new Date().toISOString();
        await db.prepare("UPDATE vehicles SET status = 'SOLD', is_public = 0, publishing_status = 'SOLD', updated_at = ? WHERE id = ?")
          .bind(now, vehicleId).run();
        return new Response(JSON.stringify({ success: true, message: '판매 완료 처리되었습니다.' }), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 7. Photo Matrix API: /api/admin/vehicles/:id/photo-matrix
    if (pathname.includes('/photo-matrix')) {
      const vehicleId = pathname.split('/')[4];
      if (!db) return new Response(JSON.stringify({ error: 'DB not found' }), { status: 500 });

      if (request.method === 'GET') {
        try {
          const photosRes = await db.prepare('SELECT * FROM vehicle_photos WHERE vehicle_id = ? ORDER BY is_primary DESC, sort_order ASC').bind(vehicleId).all();
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

          const slots = standardSlots.map((s, idx) => ({
            view_code: s.code,
            display_label: s.label,
            category_code: s.category,
            sort_order: idx + 1,
            is_uploaded: !!uploadedMap[s.code],
            photo_url: uploadedMap[s.code] || null
          }));

          return new Response(JSON.stringify({
            vehicle_id: vehicleId,
            total_slots: 45,
            configured_slots: standardSlots.length,
            uploaded_count: Object.keys(uploadedMap).length,
            slots: slots
          }), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
        } catch (err) {
          return new Response(JSON.stringify({ error: err.message }), { status: 500 });
        }
      }

      if (request.method === 'POST') {
        try {
          const body = await request.json();
          const { view_code, photo_url } = body;
          const photoId = 'PHO-' + crypto.randomUUID().slice(0, 8);
          const now = new Date().toISOString();
          const isPrimary = view_code === 'EXT_FRONT' ? 1 : 0;

          const existing = await db.prepare('SELECT id FROM vehicle_photos WHERE vehicle_id = ? AND view_code = ?')
            .bind(vehicleId, view_code).first();

          if (existing) {
            await db.prepare('UPDATE vehicle_photos SET photo_url = ? WHERE id = ?').bind(photo_url, existing.id).run();
          } else {
            await db.prepare(`
              INSERT INTO vehicle_photos (id, vehicle_id, photo_url, view_code, category_code, sort_order, is_primary, approval_status, created_at)
              VALUES (?, ?, ?, ?, 'EXTERIOR', 1, ?, 'APPROVED', ?)
            `).bind(photoId, vehicleId, photo_url, view_code, isPrimary, now).run();
          }

          if (isPrimary) {
            await db.prepare('UPDATE vehicles SET primary_photo_url = ? WHERE id = ?').bind(photo_url, vehicleId).run();
          }

          return new Response(JSON.stringify({ success: true, message: '슬롯 사진이 성공적으로 등록되었습니다.' }), {
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
          });
        } catch (err) {
          return new Response(JSON.stringify({ error: err.message }), { status: 500 });
        }
      }
    }

    // 8. Consultations List API: /api/admin/consultations
    if (pathname === '/api/admin/consultations' && request.method === 'GET') {
      if (!db) return new Response(JSON.stringify({ error: 'DB not found' }), { status: 500 });
      try {
        const { results } = await db.prepare(`
          SELECT 
            c.id, c.customer_id, c.channel, c.content, c.staff_name, c.created_at,
            cust.name as customer_name, cust.phone, cust.status as customer_status, cust.target_vehicle_model
          FROM consultations c
          LEFT JOIN customers cust ON c.customer_id = cust.id
          ORDER BY c.created_at DESC LIMIT 50
        `).all();

        return new Response(JSON.stringify(results || []), {
          headers: { 'Content-Type': 'application/json; charset=utf-8' }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 9. Consultation Status Update API: /api/admin/consultations/:id/update
    if (pathname.includes('/api/admin/consultations/') && pathname.endsWith('/update') && request.method === 'POST') {
      const parts = pathname.split('/');
      const consultationId = parts[4];
      if (!db) return new Response(JSON.stringify({ error: 'DB not found' }), { status: 500 });
      try {
        const body = await request.json();
        const { status } = body;
        const c = await db.prepare('SELECT customer_id FROM consultations WHERE id = ?').bind(consultationId).first();
        if (c && status) {
          await db.prepare('UPDATE customers SET status = ? WHERE id = ?').bind(status, c.customer_id).run();
        }
        return new Response(JSON.stringify({ success: true, message: '상담 상태가 업데이트되었습니다.' }), {
          headers: { 'Content-Type': 'application/json; charset=utf-8' }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // Static Assets Fallback
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
