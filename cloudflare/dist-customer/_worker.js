// Cloudflare Pages Worker for Chamart (DIRECTIVE 130 Compliant)
// Strict Real-Vehicle Only: Zero Fabricated Photos, 4-Tier Exposure Ranking, Sync API

function isValidRealVehiclePhoto(url) {
  if (!url || typeof url !== 'string') return false;
  const u = url.trim().toLowerCase();
  if (!u) return false;
  if (
    u.includes('placeholder') ||
    u.includes('slots') ||
    u.includes('sample_car') ||
    u.includes('demo_car') ||
    u.includes('demo_graphic') ||
    u.includes('ui_fixtures') ||
    u.includes('no_photo') ||
    u.includes('unsplash.com') ||
    u.startsWith('/static/img/vehicles/') ||
    u.startsWith('/static/img/real_photos/') ||
    u.startsWith('/static/img/ui_fixtures/')
  ) {
    return false;
  }
  if (u.startsWith('http://') || u.startsWith('https://')) {
    return true;
  }
  return false;
}

function isValidPhoto(url) {
  return isValidRealVehiclePhoto(url);
}

const NO_PHOTO_FALLBACK = '/static/img/no_photo.svg';

// DIRECTIVE 130 P0 보안 보정: 하드코딩된 기본 토큰 전면 폐기, Cloudflare Secret(SYNC_API_KEY) 엄격 필수 검증
function verifySyncAuth(request, env) {
  const auth = request.headers.get('Authorization') || '';
  const token = auth.replace(/^Bearer\s+/i, '').trim();
  const expected = env.SYNC_API_KEY;
  if (!expected || typeof expected !== 'string' || expected.length < 16) {
    // 환경변수 미설정 시 어떠한 요청도 허용하지 않고 즉시 차단
    return false;
  }
  return token === expected;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // =========================================================================
    // 1. Customer API Routes (초고속 엣지 캐시 + 4단계 우선 노출 정렬)
    // =========================================================================
    if (pathname === '/api/chamart/vehicles') {
      const cache = caches.default;
      const cacheKey = new Request(url.toString(), request);
      const cached = await cache.match(cacheKey);
      if (cached) {
        const h = new Headers(cached.headers);
        h.set('X-Chamart-Cache', 'HIT');
        return new Response(cached.body, { status: cached.status, headers: h });
      }

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

        // DIRECTIVE 131 TASK 2: 고객 공개 정보 엄격 진실성 보장
        // 1) is_public = 1 필수
        // 2) is_demo = 0 필수
        // 3) publishing_status 승인 상태 필수
        // 4) status IN ('AVAILABLE', 'FOR_SALE') 필수 (판매완료/중지/삭제 원천 차단)
        let sql = `SELECT 
          id, plate_number, model_name, manufacturer, trim, year, mileage, 
          fuel_type, transmission, color, target_price, primary_photo_url, 
          listing_ownership_type, is_priority_exposure, priority_rank, 
          status, publishing_status, options_json
        FROM vehicles 
        WHERE is_public = 1 
          AND is_demo = 0
          AND publishing_status IN ('APPROVED', 'PUBLISHED')
          AND status IN ('AVAILABLE', 'FOR_SALE')`;
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

        // DIRECTIVE 130 TASK 2: 4단계 우선 노출 정렬
        // 1. 차마트 소속 + 실제 사진 있음
        // 2. 차마트 소속 + 사진 없음
        // 3. 타사 차량 + 실제 사진 있음
        // 4. 타사 차량 + 사진 없음
        const tierOrderClause = `
          (CASE 
            WHEN (listing_ownership_type = 'OWNED' OR listing_ownership_type = 'CHAMART_OWNED') 
                 AND (primary_photo_url LIKE 'http://%' OR primary_photo_url LIKE 'https://%')
                 AND primary_photo_url NOT LIKE '%placeholder%'
                 AND primary_photo_url NOT LIKE '%no_photo%'
                 AND primary_photo_url NOT LIKE '%unsplash%'
                 AND primary_photo_url NOT LIKE '%ui_fixtures%'
                 AND primary_photo_url NOT LIKE '%demo%' THEN 1
            WHEN (listing_ownership_type = 'OWNED' OR listing_ownership_type = 'CHAMART_OWNED') THEN 2
            WHEN (primary_photo_url LIKE 'http://%' OR primary_photo_url LIKE 'https://%')
                 AND primary_photo_url NOT LIKE '%placeholder%'
                 AND primary_photo_url NOT LIKE '%no_photo%'
                 AND primary_photo_url NOT LIKE '%unsplash%'
                 AND primary_photo_url NOT LIKE '%ui_fixtures%'
                 AND primary_photo_url NOT LIKE '%demo%' THEN 3
            ELSE 4
          END) ASC`;

        if (sort === 'price_asc') {
          sql += ` ORDER BY ${tierOrderClause}, CAST(target_price AS INTEGER) ASC, CAST(mileage AS INTEGER) ASC, year DESC`;
        } else if (sort === 'price_desc') {
          sql += ` ORDER BY ${tierOrderClause}, CAST(target_price AS INTEGER) DESC, CAST(mileage AS INTEGER) ASC, year DESC`;
        } else if (sort === 'mileage_asc') {
          sql += ` ORDER BY ${tierOrderClause}, CAST(mileage AS INTEGER) ASC, CAST(target_price AS INTEGER) ASC, year DESC`;
        } else if (sort === 'mileage_desc') {
          sql += ` ORDER BY ${tierOrderClause}, CAST(mileage AS INTEGER) DESC, CAST(target_price AS INTEGER) ASC, year DESC`;
        } else if (sort === 'latest') {
          sql += ` ORDER BY ${tierOrderClause}, created_at DESC, id DESC`;
        } else {
          // 추천순: 4단계 티어 -> 관리자 우선노출 -> 우선순위 랭크 -> 최신 등록순
          sql += ` ORDER BY 
            ${tierOrderClause},
            is_priority_exposure DESC,
            priority_rank ASC,
            created_at DESC`;
        }

        const { results } = await db.prepare(sql).bind(...params).all();

        const enriched = (results || []).map(v => {
          let options = [];
          try {
            if (v.options_json) options = JSON.parse(v.options_json);
          } catch (e) {}

          const hasRealPhoto = isValidPhoto(v.primary_photo_url);
          const finalPhoto = hasRealPhoto ? v.primary_photo_url : NO_PHOTO_FALLBACK;

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
            monthly_payment_estimate: Math.round((v.target_price || 0) * 10000 / 48 / 10000),
            primary_photo_url: finalPhoto,
            has_real_photo: hasRealPhoto,
            photo_count: hasRealPhoto ? 1 : 0,
            options: options,
            listing_ownership_type: v.listing_ownership_type || 'UNKNOWN',
            is_chamart_owned: (v.listing_ownership_type === 'OWNED' || v.listing_ownership_type === 'CHAMART_OWNED'),
            is_priority_exposure: !!v.is_priority_exposure,
            priority_rank: v.priority_rank || 0,
            status: v.status || 'AVAILABLE',
            publishing_status: v.publishing_status || 'APPROVED',
            branch_name: '차마트 장한평 본사 직영점'
          };
        });

        const resp = new Response(JSON.stringify(enriched), {
          headers: {
            'Content-Type': 'application/json; charset=utf-8',
            'Cache-Control': 'public, max-age=0, must-revalidate',
            'Access-Control-Allow-Origin': '*'
          }
        });

        ctx.waitUntil(cache.put(cacheKey, resp.clone()));
        return resp;
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // =========================================================================
    // 2. Vehicle Detail API: /api/chamart/vehicles/:id (정직한 실차 사진 매핑)
    // =========================================================================
    if (pathname.startsWith('/api/chamart/vehicles/')) {
      const vehicleId = pathname.replace('/api/chamart/vehicles/', '');
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

        const photosRes = await db.prepare(
          'SELECT * FROM vehicle_photos WHERE vehicle_id = ? ORDER BY is_primary DESC, sort_order ASC'
        ).bind(vehicleId).all();

        // 실제 유효한 사진만 매핑 (가상 사진 일괄 생성 금지)
        let validPhotos = (photosRes.results || [])
          .filter(p => isValidPhoto(p.photo_url))
          .map(p => ({
            photo_url: p.photo_url,
            caption: p.caption || '실차 사진',
            display_label: p.display_label || p.caption || '실차 사진',
            category: p.category || 'EXTERIOR'
          }));

        // DB에 사진 행이 없지만 primary_photo_url이 유효한 경우 반영
        if (validPhotos.length === 0 && isValidPhoto(v.primary_photo_url)) {
          validPhotos.push({
            photo_url: v.primary_photo_url,
            caption: '실차 전면',
            display_label: '전면',
            category: 'EXTERIOR'
          });
        }

        // 사진이 전무한 경우 정직한 '사진 준비 중' 1장 설정
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
            total_loss: null, // 실제 보험개발원 카히스토리 연동 전까지 가상 false 금지
            flood: null,      // 가상 0% 보증 금지
            inspection_status: v.inspection_record_url ? '성능점검부 확인 완료' : '성능점검 서류 확인 대기',
            insurance_history_count: null,
            owner_change_count: null
          },
          dealer_info: {
            company: v.branch_name || '차마트 제휴/직영 상사',
            contact: '02-2244-8800',
            address: '서울시 성동구·동대문구 장한평 매매단지'
          },
          price_comparison: {
            market_average_price: null,
            difference_amount: null,
            advantage_text: '실차 진단 및 정밀 시세 분석 대기'
          },
          branch_name: '차마트 장한평 본사 직영점',
          is_public: !!v.is_public,
          publishing_status: v.publishing_status || 'APPROVED',
          listing_ownership_type: v.listing_ownership_type || 'UNKNOWN',
          is_chamart_owned: (v.listing_ownership_type === 'OWNED' || v.listing_ownership_type === 'CHAMART_OWNED'),
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

    // =========================================================================
    // 3. Consultation POST API
    // =========================================================================
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

    // =========================================================================
    // 4. TASK 1 & 3: 원자적 멱등성 보장 및 안전한 HTTPS 동기화 API
    // =========================================================================
    if (pathname.startsWith('/api/sync/')) {
      if (!verifySyncAuth(request, env)) {
        return new Response(JSON.stringify({ error: '인증 실패: 유효한 Sync API 토큰이 필요합니다.' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' }
        });
      }

      const db = env.DB;
      if (!db) return new Response(JSON.stringify({ error: 'DB binding not found' }), { status: 500 });

      // 4-0. 상태 조회는 멱등성 키 검사 예외
      if (pathname === '/api/sync/status' && request.method === 'GET') {
        try {
          const lastAudit = await db.prepare(
            "SELECT * FROM admin_audit_logs WHERE action LIKE '%SYNC%' ORDER BY created_at DESC LIMIT 5"
          ).all();
          const totalVehicles = await db.prepare("SELECT count(*) as count FROM vehicles WHERE (is_demo = 0 OR is_demo IS NULL)").first();
          const totalOwned = await db.prepare("SELECT count(*) as count FROM vehicles WHERE (listing_ownership_type = 'OWNED' OR listing_ownership_type = 'CHAMART_OWNED') AND (is_demo = 0 OR is_demo IS NULL)").first();

          return new Response(JSON.stringify({
            status: 'HEALTHY',
            total_real_vehicles: totalVehicles?.count || 0,
            total_owned_vehicles: totalOwned?.count || 0,
            recent_sync_events: lastAudit.results || []
          }), { headers: { 'Content-Type': 'application/json' } });
        } catch (err) {
          return new Response(JSON.stringify({ error: err.message }), { status: 500 });
        }
      }

      // 변경 요청(POST)에 대한 원자적 멱등성 검증 (TASK 1)
      const idempotencyKey = (request.headers.get('Idempotency-Key') || '').trim();
      if (!idempotencyKey) {
        return new Response(JSON.stringify({
          error: '멱등성 키 누락: 모든 데이터 변경 요청은 Idempotency-Key 헤더가 필수입니다.',
          code: 'MISSING_IDEMPOTENCY_KEY'
        }), { status: 400, headers: { 'Content-Type': 'application/json' } });
      }

      // 페이로드 본문 및 SHA-256 해시 계산
      const bodyText = await request.text();
      let body;
      try {
        body = JSON.parse(bodyText);
      } catch (e) {
        return new Response(JSON.stringify({ error: '유효하지 않은 JSON 본문입니다.' }), { status: 400 });
      }

      const encoder = new TextEncoder();
      const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(bodyText));
      const currentPayloadHash = Array.from(new Uint8Array(hashBuffer)).map(b => b.toString(16).padStart(2, '0')).join('');
      const nowIso = new Date().toISOString();

      // 원자적 멱등성 락 획득 (INSERT PK 충돌 제약 활용)
      let activeLockUpdatedAt = nowIso;
      try {
        await db.prepare(`
          INSERT INTO sync_idempotency_keys (idempotency_key, endpoint, payload_hash, status, created_at, updated_at)
          VALUES (?, ?, ?, 'IN_PROGRESS', ?, ?)
        `).bind(idempotencyKey, pathname, currentPayloadHash, nowIso, nowIso).run();
      } catch (insertErr) {
        // 이미 동일한 키가 존재함: 상태 및 페이로드 해시 검증
        const existingKey = await db.prepare(
          "SELECT endpoint, payload_hash, status, response_json FROM sync_idempotency_keys WHERE idempotency_key = ?"
        ).bind(idempotencyKey).first();

        if (existingKey) {
          // 1) 엔드포인트 상이 -> 409 거부
          if (existingKey.endpoint !== pathname) {
            return new Response(JSON.stringify({
              error: '멱등성 키 충돌: 동일한 Idempotency-Key가 다른 엔드포인트에서 사용되었습니다.',
              code: 'IDEMPOTENCY_ENDPOINT_MISMATCH'
            }), { status: 409, headers: { 'Content-Type': 'application/json' } });
          }

          // 2) 페이로드 불일치 -> 409 Conflict 거부
          if (existingKey.payload_hash !== currentPayloadHash) {
            return new Response(JSON.stringify({
              error: '멱등성 키 충돌: 동일한 Idempotency-Key로 다른 페이로드가 전송되었습니다.',
              code: 'IDEMPOTENCY_PAYLOAD_MISMATCH'
            }), { status: 409, headers: { 'Content-Type': 'application/json' } });
          }

          // 3) 이미 완료된 동일 요청 -> 저장된 결과 즉시 리플레이
          if (existingKey.status === 'COMPLETED' && existingKey.response_json) {
            return new Response(existingKey.response_json, {
              status: 200,
              headers: { 
                'Content-Type': 'application/json',
                'X-Idempotent-Replay': 'true'
              }
            });
          }

          // 4) 실패(FAILED)한 경우 -> 안전한 재시도 허용 (status = 'IN_PROGRESS'로 원자적 재선점)
          if (existingKey.status === 'FAILED') {
            const reacquire = await db.prepare(
              "UPDATE sync_idempotency_keys SET status = 'IN_PROGRESS', response_json = NULL, updated_at = ? WHERE idempotency_key = ? AND status = 'FAILED'"
            ).bind(nowIso, idempotencyKey).run();
            if (reacquire.meta.changes === 0) {
              return new Response(JSON.stringify({
                error: '동일한 멱등성 키를 가진 재시도 요청이 이미 처리 중입니다.',
                code: 'IDEMPOTENCY_CONCURRENT_RETRY'
              }), { status: 409, headers: { 'Content-Type': 'application/json' } });
            }
            activeLockUpdatedAt = nowIso;
          } else if (existingKey.status === 'IN_PROGRESS') {
            // 5) 60초 초과 Stale Lock 타임아웃 재선점
            const updatedAt = new Date(existingKey.updated_at || existingKey.created_at).getTime();
            const nowTime = new Date().getTime();
            if (nowTime - updatedAt > 60000) {
              const reclaimStale = await db.prepare(
                "UPDATE sync_idempotency_keys SET status = 'IN_PROGRESS', response_json = NULL, updated_at = ? WHERE idempotency_key = ? AND status = 'IN_PROGRESS' AND updated_at = ?"
              ).bind(nowIso, idempotencyKey, existingKey.updated_at).run();
              if (reclaimStale.meta.changes === 0) {
                return new Response(JSON.stringify({
                  error: '동일한 멱등성 키를 가진 요청이 현재 처리 중입니다 (동시 요청 방어).',
                  code: 'IDEMPOTENCY_IN_PROGRESS'
                }), { status: 409, headers: { 'Content-Type': 'application/json' } });
              }
              activeLockUpdatedAt = nowIso;
            } else {
              return new Response(JSON.stringify({
                error: '동일한 멱등성 키를 가진 요청이 현재 처리 중입니다 (동시 요청 방어).',
                code: 'IDEMPOTENCY_IN_PROGRESS'
              }), { status: 409, headers: { 'Content-Type': 'application/json' } });
            }
          }
        }
      }

      // 4-1. 차량 증분 동기화: POST /api/sync/vehicles
      if (pathname === '/api/sync/vehicles' && request.method === 'POST') {
        try {
          const vehicles = body.vehicles || [];
          let inserted = 0;
          let updated = 0;
          let skipped = 0;
          const now = new Date().toISOString();

          for (const v of vehicles) {
            if (!v.id || !v.plate_number) {
              skipped++;
              continue;
            }

            // 기존 차량 확인
            const existing = await db.prepare('SELECT id, target_price, is_public, listing_ownership_type FROM vehicles WHERE id = ? OR plate_number = ?')
              .bind(v.id, v.plate_number).first();

            if (existing) {
              // DIRECTIVE 131 TASK 3: 차마트 관리자 필드 소유권 엄격 보호
              // target_price, is_public, listing_ownership_type은 차피셜 동기화에서 일체 수정 불가!
              await db.prepare(`
                UPDATE vehicles SET
                  model_name = COALESCE(?, model_name),
                  year = COALESCE(?, year),
                  mileage = COALESCE(?, mileage),
                  fuel_type = COALESCE(?, fuel_type),
                  transmission = COALESCE(?, transmission),
                  color = COALESCE(?, color),
                  manufacturer = COALESCE(?, manufacturer),
                  trim = COALESCE(?, trim),
                  primary_photo_url = CASE WHEN ? != '' AND ? IS NOT NULL THEN ? ELSE primary_photo_url END,
                  status = COALESCE(?, status),
                  updated_at = ?
                WHERE id = ?
              `).bind(
                v.model_name, v.year, v.mileage, v.fuel_type, v.transmission, v.color,
                v.manufacturer, v.trim, v.primary_photo_url, v.primary_photo_url, v.primary_photo_url,
                v.status, now, existing.id
              ).run();
              updated++;
            } else {
              // 신규 등록 (DIRECTIVE 131 TASK 2 & 3: 무조건 비공개 is_public=0, MARKET_OBSERVED 강제)
              await db.prepare(`
                INSERT INTO vehicles (
                  id, branch_id, plate_number, model_name, year, mileage, fuel_type,
                  transmission, color, purchase_price, target_price, status, is_demo,
                  vin, displacement_cc, first_registration_date, drive_type, interior_color,
                  options_json, timeline_json, primary_photo_url, manufacturer, trim, body_type,
                  is_public, listing_ownership_type, is_priority_exposure, priority_rank,
                  publishing_status, created_at, updated_at
                ) VALUES (
                  ?, '61fea9a4-58f0-42bd-862c-14fd16d0d21c', ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?, 0,
                  ?, ?, ?, ?, ?,
                  ?, '[]', ?, ?, ?, ?,
                  0, 'MARKET_OBSERVED', 0, 0,
                  'PENDING_REVIEW', ?, ?
                )
              `).bind(
                v.id, v.plate_number, v.model_name, v.year, v.mileage, v.fuel_type,
                v.transmission || '오토', v.color || '화이트', v.purchase_price || 0,
                v.target_price || 0, v.status || 'FOR_SALE',
                v.vin || null, v.displacement_cc || null, v.first_registration_date || null,
                v.drive_type || null, v.interior_color || null,
                v.options_json || '[]', v.primary_photo_url || '',
                v.manufacturer || null, v.trim || null, v.body_type || null,
                now, now
              ).run();
              inserted++;
            }
          }

          // 감사 로그 기록
          const logId = 'AUDIT-' + crypto.randomUUID().slice(0, 8);
          await db.prepare(`
            INSERT INTO admin_audit_logs (id, user_id, action, target_type, target_id, details_json, created_at)
            VALUES (?, 'SYSTEM_SYNC', 'CHAFICIAL_SYNC_VEHICLES', 'VEHICLES_BATCH', ?, ?, ?)
          `).bind(logId, idempotencyKey, JSON.stringify({ inserted, updated, skipped, total: vehicles.length, source: body.source || 'CHAFICIAL', idempotency_key: idempotencyKey }), now).run();

          const resultObj = {
            success: true,
            inserted,
            updated,
            skipped,
            total: vehicles.length,
            idempotency_key: idempotencyKey,
            timestamp: now
          };

          // 멱등성 테이블 COMPLETED 업데이트
          const completeRes = await db.prepare(
            "UPDATE sync_idempotency_keys SET status = 'COMPLETED', response_json = ?, updated_at = ? WHERE idempotency_key = ? AND status = 'IN_PROGRESS' AND updated_at = ?"
          ).bind(JSON.stringify(resultObj), now, idempotencyKey, activeLockUpdatedAt).run();

          if (completeRes.meta.changes === 0) {
            return new Response(JSON.stringify({
              error: '멱등성 임대 만료: 처리 도중 락 소유권이 만료되어 작업 결과가 무효화되었습니다.',
              code: 'IDEMPOTENCY_LEASE_EXPIRED'
            }), { status: 409, headers: { 'Content-Type': 'application/json' } });
          }

          return new Response(JSON.stringify(resultObj), { headers: { 'Content-Type': 'application/json' } });
        } catch (err) {
          await db.prepare(
            "UPDATE sync_idempotency_keys SET status = 'FAILED', response_json = ?, updated_at = ? WHERE idempotency_key = ? AND status = 'IN_PROGRESS' AND updated_at = ?"
          ).bind(JSON.stringify({ error: err.message }), new Date().toISOString(), idempotencyKey, activeLockUpdatedAt).run();
          return new Response(JSON.stringify({ error: err.message }), { status: 500 });
        }
      }

      // 4-2. 사진 메타데이터 동기화: POST /api/sync/photos
      if (pathname === '/api/sync/photos' && request.method === 'POST') {
        try {
          const { vehicle_id, photos } = body;
          if (!vehicle_id || !Array.isArray(photos)) {
            return new Response(JSON.stringify({ error: 'vehicle_id and photos array required' }), { status: 400 });
          }

          let photoInserted = 0;
          const now = new Date().toISOString();

          for (const p of photos) {
            if (!isValidPhoto(p.photo_url)) continue;
            const photoId = p.id || 'PHOTO-' + crypto.randomUUID().slice(0, 8);
            await db.prepare(`
              INSERT OR REPLACE INTO vehicle_photos (
                id, vehicle_id, photo_url, thumb_url, category, sort_order, is_primary,
                caption, view_code, display_label, created_at
              ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `).bind(
              photoId, vehicle_id, p.photo_url, p.thumb_url || p.photo_url,
              p.category || 'EXTERIOR', p.sort_order || 0, p.is_primary ? 1 : 0,
              p.caption || '실차 사진', p.view_code || 'EXT_FRONT', p.display_label || '실차 사진',
              now
            ).run();
            photoInserted++;
          }

          const resultObj = { success: true, vehicle_id, photo_count: photoInserted, idempotency_key: idempotencyKey };

          const completeRes = await db.prepare(
            "UPDATE sync_idempotency_keys SET status = 'COMPLETED', response_json = ?, updated_at = ? WHERE idempotency_key = ? AND status = 'IN_PROGRESS' AND updated_at = ?"
          ).bind(JSON.stringify(resultObj), now, idempotencyKey, activeLockUpdatedAt).run();

          if (completeRes.meta.changes === 0) {
            return new Response(JSON.stringify({
              error: '멱등성 임대 만료: 처리 도중 락 소유권이 만료되어 작업 결과가 무효화되었습니다.',
              code: 'IDEMPOTENCY_LEASE_EXPIRED'
            }), { status: 409, headers: { 'Content-Type': 'application/json' } });
          }

          return new Response(JSON.stringify(resultObj), { headers: { 'Content-Type': 'application/json' } });
        } catch (err) {
          await db.prepare(
            "UPDATE sync_idempotency_keys SET status = 'FAILED', response_json = ?, updated_at = ? WHERE idempotency_key = ? AND status = 'IN_PROGRESS' AND updated_at = ?"
          ).bind(JSON.stringify({ error: err.message }), new Date().toISOString(), idempotencyKey, activeLockUpdatedAt).run();
          return new Response(JSON.stringify({ error: err.message }), { status: 500 });
        }
      }

      // 4-3. 상태 동기화 (판매완료/광고중지): POST /api/sync/status
      if (pathname === '/api/sync/status' && request.method === 'POST') {
        try {
          const { vehicle_ids, status, reason } = body;
          if (!Array.isArray(vehicle_ids) || !status) {
            return new Response(JSON.stringify({ error: 'vehicle_ids array and status required' }), { status: 400 });
          }

          // DIRECTIVE 131: 허용 상태 화이트리스트 검증
          const allowedStatuses = ['AVAILABLE', 'FOR_SALE', 'RESERVED', 'SOLD', 'SUSPENDED', 'DELETED', 'INACTIVE'];
          const normStatus = String(status).toUpperCase();
          if (!allowedStatuses.includes(normStatus)) {
            return new Response(JSON.stringify({ 
              error: `허용되지 않는 상태값입니다. 허용값: ${allowedStatuses.join(', ')}`,
              status: 400 
            }), { status: 400, headers: { 'Content-Type': 'application/json' } });
          }

          const now = new Date().toISOString();
          let count = 0;

          // 판매완료, 광고중지, 삭제 상태일 경우 is_public을 0으로 강제 내려서 노출 즉시 차단
          const unpublishStatuses = ['SOLD', 'SUSPENDED', 'DELETED', 'INACTIVE'];
          const shouldUnpublish = unpublishStatuses.includes(normStatus);

          for (const vid of vehicle_ids) {
            if (shouldUnpublish) {
              await db.prepare(`
                UPDATE vehicles 
                SET status = ?, is_public = 0, updated_at = ? 
                WHERE id = ?
              `).bind(normStatus, now, vid).run();
            } else {
              await db.prepare(`
                UPDATE vehicles 
                SET status = ?, updated_at = ? 
                WHERE id = ?
              `).bind(normStatus, now, vid).run();
            }
            count++;
          }

          // 감사 로그 기록
          const logId = 'AUDIT-' + crypto.randomUUID().slice(0, 8);
          await db.prepare(`
            INSERT INTO admin_audit_logs (id, user_id, action, target_type, target_id, details_json, created_at)
            VALUES (?, 'SYSTEM_SYNC', 'CHAFICIAL_SYNC_STATUS', 'STATUS_BATCH', ?, ?, ?)
          `).bind(logId, idempotencyKey, JSON.stringify({ count, vehicle_ids, status: normStatus, reason, unpublished: shouldUnpublish, idempotency_key: idempotencyKey }), now).run();

          const resultObj = { 
            success: true, 
            updated_count: count, 
            status: normStatus,
            unpublished: shouldUnpublish,
            idempotency_key: idempotencyKey
          };

          await db.prepare(
            "UPDATE sync_idempotency_keys SET status = 'COMPLETED', response_json = ?, updated_at = ? WHERE idempotency_key = ? AND status = 'IN_PROGRESS' AND updated_at = ?"
          ).bind(JSON.stringify(resultObj), now, idempotencyKey, activeLockUpdatedAt).run();

          return new Response(JSON.stringify(resultObj), { headers: { 'Content-Type': 'application/json' } });
        } catch (err) {
          await db.prepare(
            "UPDATE sync_idempotency_keys SET status = 'FAILED', response_json = ?, updated_at = ? WHERE idempotency_key = ?"
          ).bind(JSON.stringify({ error: err.message }), new Date().toISOString(), idempotencyKey).run();
          return new Response(JSON.stringify({ error: err.message }), { status: 500 });
        }
      }
    }

    // =========================================================================
    // 5. Static Asset Serving & SPA Routing Fallback (HTML 캐시 방지 적용)
    // =========================================================================
    try {
      let response = await env.ASSETS.fetch(request);
      if (response.status === 404 && !pathname.startsWith('/api/') && !pathname.includes('.')) {
        response = await env.ASSETS.fetch(new URL('/index.html', request.url));
      }

      // HTML 문서는 항상 최신 변경사항을 즉시 반영하도록 no-cache 헤더 강제 주입
      const contentType = response.headers.get('content-type') || '';
      if (pathname === '/' || pathname === '/index.html' || pathname === '/chamart.html' || contentType.includes('text/html')) {
        const h = new Headers(response.headers);
        h.set('Cache-Control', 'no-cache, no-store, must-revalidate');
        h.set('Pragma', 'no-cache');
        h.set('Expires', '0');
        return new Response(response.body, { status: response.status, headers: h });
      }

      return response;
    } catch (e) {
      const res = await env.ASSETS.fetch(new URL('/index.html', request.url));
      const h = new Headers(res.headers);
      h.set('Cache-Control', 'no-cache, no-store, must-revalidate');
      return new Response(res.body, { status: res.status, headers: h });
    }
  }
};
