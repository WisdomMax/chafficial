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

// DIRECTIVE 136-SEC P0 보안 보정:
// 1) 하드코딩 기본 토큰 영구 완전 폐기
// 2) ?token= URL 쿼리 파라미터 인증 완전 차단 (오직 Authorization: Bearer 및 헤더 인증만 허용)
// 3) Cloudflare Secret 미설정 시 즉시 401 차단
// 4) 동기화 토큰(CHAMART_SYNC_TOKEN / SYNC_API_KEY)과 관리자 토큰(CHAMART_ADMIN_TOKEN) 분리

function constantTimeEqual(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

function verifySyncAuth(request, env) {
  const allowedTokens = [env.CHAMART_SYNC_TOKEN, env.SYNC_API_KEY].filter(t => t && typeof t === 'string' && t.length >= 16);
  if (allowedTokens.length === 0) {
    return false;
  }
  const auth = (request.headers.get('Authorization') || '').trim();
  const bearerToken = auth.match(/^Bearer\s+(.+)$/i)?.[1]?.trim() || '';
  const headerToken = (request.headers.get('X-Chamart-Sync-Key') || request.headers.get('X-Sync-Token') || '').trim();
  const token = bearerToken || headerToken;
  if (!token) return false;
  return allowedTokens.some(expected => constantTimeEqual(token, expected));
}

function verifyAdminAuth(request, env) {
  const expected = env.CHAMART_ADMIN_TOKEN;
  if (!expected || typeof expected !== 'string' || expected.length < 16) {
    return false;
  }
  const auth = (request.headers.get('Authorization') || '').trim();
  const bearerToken = auth.match(/^Bearer\s+(.+)$/i)?.[1]?.trim() || '';
  const headerToken = (request.headers.get('X-Chamart-Admin-Key') || request.headers.get('X-Admin-Token') || '').trim();
  const token = bearerToken || headerToken;
  if (!token) return false;
  return constantTimeEqual(token, expected);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // =========================================================================
    // 0. DIRECTIVE 136-SEC: 인증된 관리자 전용 실매물 상세 조회 API (D1 실시간 데이터 1:1 반환)
    //    - 오직 Authorization: Bearer / X-Chamart-Admin-Key 헤더만 허용 (?token= 완전 차단)
    //    - CHAMART_ADMIN_TOKEN 분리 검증 (Secret 미설정 시 즉시 401 차단)
    //    - 반환 정보 최소화 (SELECT v.* 제거, 필수 제원 및 사진만)
    // =========================================================================
    if (pathname.startsWith('/api/admin/vehicles/') && request.method === 'GET') {
      if (!verifyAdminAuth(request, env)) {
        return new Response(JSON.stringify({ 
          error: 'UNAUTHORIZED_ADMIN_ACCESS',
          message: '유효한 관리자 인증 토큰이 필요합니다. Authorization: Bearer 헤더를 사용하세요.'
        }), {
          status: 401,
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
        });
      }

      const vid = decodeURIComponent(pathname.split('/').pop());
      const db = env.DB;
      if (!db) {
        return new Response(JSON.stringify({ error: 'DB binding not found' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
        });
      }

      try {
        const vehicle = await db.prepare(`
          SELECT 
            v.id, v.plate_number, v.model_name, v.manufacturer, v.trim, v.year, v.mileage,
            v.fuel_type, v.transmission, v.color, v.target_price,
            v.listing_ownership_type, v.is_priority_exposure, v.priority_rank,
            v.status, v.publishing_status, v.is_public, v.is_demo,
            v.created_at, v.updated_at,
            (SELECT vl.raw_seller_name FROM vehicle_listings vl WHERE vl.vehicle_id = v.id LIMIT 1) as seller_company_name
          FROM vehicles v
          WHERE v.id = ? OR v.plate_number = ?
          LIMIT 1
        `).bind(vid, vid).first();

        if (!vehicle) {
          return new Response(JSON.stringify({ error: 'VEHICLE_NOT_FOUND', queried_id: vid }), {
            status: 404,
            headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
          });
        }

        // 연결된 사진 목록 조회 (필수 컬럼만)
        const photosRes = await db.prepare(`
          SELECT id, photo_url, thumb_url, category, sort_order, is_primary, public_visibility, approval_status
          FROM vehicle_photos
          WHERE vehicle_id = ?
          ORDER BY sort_order ASC, id ASC
          LIMIT 20
        `).bind(vehicle.id).all();

        const photos = (photosRes.results || []).map(p => ({
          id: p.id,
          url: p.photo_url,
          thumb_url: p.thumb_url || p.photo_url,
          category: p.category,
          sort_order: p.sort_order,
          public_visibility: p.public_visibility,
          approval_status: p.approval_status
        }));

        const responseData = {
          id: vehicle.id,
          plate_number: vehicle.plate_number,
          model_name: vehicle.model_name,
          manufacturer: vehicle.manufacturer,
          trim: vehicle.trim,
          year: vehicle.year,
          mileage: vehicle.mileage,
          fuel_type: vehicle.fuel_type,
          transmission: vehicle.transmission,
          color: vehicle.color,
          target_price: vehicle.target_price,
          listing_ownership_type: vehicle.listing_ownership_type,
          is_priority_exposure: vehicle.is_priority_exposure,
          priority_rank: vehicle.priority_rank,
          status: vehicle.status,
          publishing_status: vehicle.publishing_status,
          is_public: vehicle.is_public,
          is_demo: vehicle.is_demo,
          seller_company_name: vehicle.seller_company_name,
          photos: photos,
          photo_count: photos.length,
          _source: 'CLOUDFLARE_D1_REAL_RECORD',
          _verified_at: new Date().toISOString()
        };

        return new Response(JSON.stringify(responseData), {
          status: 200,
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: 'ADMIN_API_ERROR', details: String(err && err.message ? err.message : err) }), {
          status: 500,
          headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
        });
      }
    }

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

        // DIRECTIVE 131 TASK 2 & DIRECTIVE 132-A TASK 3: 고객 공개 정보 및 승인 사진 엄격 검증
        // 1) is_public = 1 필수
        // 2) is_demo = 0 필수
        // 3) publishing_status 승인 상태 필수
        // 4) status IN ('AVAILABLE', 'FOR_SALE') 필수 (판매완료/중지/삭제 원천 차단)
        // 5) 승인된 실차 사진(approval_status='APPROVED' & public_visibility='PUBLIC')만 집계/채택
        // 6) 제휴 상사명(raw_seller_name) 연동
        let sql = `SELECT 
          id, plate_number, model_name, manufacturer, trim, year, mileage, 
          fuel_type, transmission, color, target_price, 
          listing_ownership_type, is_priority_exposure, priority_rank, 
          status, publishing_status, options_json,
          (SELECT vl.raw_seller_name 
           FROM vehicle_listings vl 
           WHERE vl.vehicle_id = vehicles.id 
           LIMIT 1) as seller_company_name,
          (SELECT vp.photo_url 
           FROM vehicle_photos vp 
           WHERE vp.vehicle_id = vehicles.id 
             AND vp.approval_status = 'APPROVED' 
             AND vp.public_visibility = 'PUBLIC'
             AND (vp.photo_url LIKE 'http://%' OR vp.photo_url LIKE 'https://%')
             AND vp.photo_url NOT LIKE '%placeholder%'
             AND vp.photo_url NOT LIKE '%no_photo%'
             AND vp.photo_url NOT LIKE '%unsplash%'
             AND vp.photo_url NOT LIKE '%ui_fixtures%'
             AND vp.photo_url NOT LIKE '%demo%'
           ORDER BY vp.is_primary DESC, vp.sort_order ASC 
           LIMIT 1) as approved_primary_photo_url,
          (SELECT COUNT(*) 
           FROM vehicle_photos vp 
           WHERE vp.vehicle_id = vehicles.id 
             AND vp.approval_status = 'APPROVED' 
             AND vp.public_visibility = 'PUBLIC'
             AND (vp.photo_url LIKE 'http://%' OR vp.photo_url LIKE 'https://%')
             AND vp.photo_url NOT LIKE '%placeholder%'
             AND vp.photo_url NOT LIKE '%no_photo%'
             AND vp.photo_url NOT LIKE '%unsplash%'
             AND vp.photo_url NOT LIKE '%ui_fixtures%'
             AND vp.photo_url NOT LIKE '%demo%') as approved_photo_count
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

        // DIRECTIVE 130 & DIRECTIVE 132-A TASK 3: 4단계 우선 노출 정렬 (승인된 사진 기준으로만 계산)
        // 1. 차마트 소속 + 승인 실사진 있음
        // 2. 차마트 소속 + 사진 없음
        // 3. 타사 차량 + 승인 실사진 있음
        // 4. 타사 차량 + 사진 없음
        const hasApprovedPhotoSubquery = `EXISTS (
          SELECT 1 FROM vehicle_photos vp 
          WHERE vp.vehicle_id = vehicles.id 
            AND vp.approval_status = 'APPROVED' 
            AND vp.public_visibility = 'PUBLIC'
            AND (vp.photo_url LIKE 'http://%' OR vp.photo_url LIKE 'https://%')
            AND vp.photo_url NOT LIKE '%placeholder%'
            AND vp.photo_url NOT LIKE '%no_photo%'
            AND vp.photo_url NOT LIKE '%unsplash%'
            AND vp.photo_url NOT LIKE '%ui_fixtures%'
            AND vp.photo_url NOT LIKE '%demo%'
        )`;

        const tierOrderClause = `
          (CASE 
            WHEN (listing_ownership_type = 'OWNED' OR listing_ownership_type = 'CHAMART_OWNED') 
                 AND ${hasApprovedPhotoSubquery} THEN 1
            WHEN (listing_ownership_type = 'OWNED' OR listing_ownership_type = 'CHAMART_OWNED') THEN 2
            WHEN ${hasApprovedPhotoSubquery} THEN 3
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

          // DIRECTIVE 132-A TASK 3: 승인된 사진만 채택, 미승인/부재 시 예외 없이 no_photo.svg 강제
          const hasRealPhoto = (v.approved_photo_count > 0) && isValidPhoto(v.approved_primary_photo_url);
          const finalPhoto = hasRealPhoto ? v.approved_primary_photo_url : NO_PHOTO_FALLBACK;

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
            photo_count: v.approved_photo_count || 0,
            options: options,
            listing_ownership_type: v.listing_ownership_type || 'UNKNOWN',
            is_chamart_owned: (v.listing_ownership_type === 'OWNED' || v.listing_ownership_type === 'CHAMART_OWNED'),
            seller_company: v.seller_company_name || ((v.listing_ownership_type === 'OWNED' || v.listing_ownership_type === 'CHAMART_OWNED') ? '차마트 직영' : '제휴 상사'),
            is_priority_exposure: !!v.is_priority_exposure,
            priority_rank: v.priority_rank || 0,
            status: v.status || 'AVAILABLE',
            publishing_status: v.publishing_status || 'APPROVED',
            branch_name: (v.listing_ownership_type === 'OWNED' || v.listing_ownership_type === 'CHAMART_OWNED') 
              ? '차마트 장한평 본사 직영점' 
              : (v.seller_company_name ? `${v.seller_company_name} (제휴 상사)` : '차마트 제휴 상사')
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

        // DIRECTIVE 132-A TASK 3: 승인된 공개 사진만 조회 (approval_status='APPROVED' & public_visibility='PUBLIC')
        // 미승인 사진이나 임의 대체 사진은 100% 제외
        const photosRes = await db.prepare(`
          SELECT * FROM vehicle_photos 
          WHERE vehicle_id = ? 
            AND approval_status = 'APPROVED' 
            AND public_visibility = 'PUBLIC'
          ORDER BY is_primary DESC, sort_order ASC
        `).bind(vehicleId).all();

        // 실제 유효한 사진만 매핑 (가상 사진 및 미승인 사진 일절 금지)
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
            total_loss: null, // 실제 보험개발원 카히스토리 연동 전까지 가상 false 금지
            flood: null,      // 가상 0% 보증 금지
            inspection_status: v.inspection_record_url ? '성능점검부 확인 완료' : '성능점검 서류 확인 대기',
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
          seller_company: sellerName,
          seller_company_name: sellerName,
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
          const totalApproved = await db.prepare("SELECT count(*) as count FROM vehicles WHERE is_public = 1 AND publishing_status IN ('APPROVED', 'PUBLISHED') AND (is_demo = 0 OR is_demo IS NULL)").first();

          return new Response(JSON.stringify({
            status: 'HEALTHY',
            total_real_vehicles: totalVehicles?.count || 0,
            total_owned_vehicles: totalOwned?.count || 0,
            total_approved_vehicles: totalApproved?.count || 0,
            recent_sync_events: lastAudit.results || []
          }), { headers: { 'Content-Type': 'application/json' } });
        } catch (err) {
          return new Response(JSON.stringify({ error: err.message }), { status: 500 });
        }
      }

      // 4-0-1. 고객 문의 조회 (TASK 3: 차마트 고객 상담 차피셜 운영 관리 전달)
      if (pathname === '/api/sync/consultations' && request.method === 'GET') {
        try {
          const limit = parseInt(url.searchParams.get('limit') || '50', 10);
          const items = await db.prepare(`
            SELECT c.id, c.customer_id, c.channel, c.content, c.staff_name, c.created_at, c.inquiry_source,
                   cust.name as customer_name, cust.phone as customer_phone, cust.target_vehicle_model
            FROM consultations c
            LEFT JOIN customers cust ON c.customer_id = cust.id
            ORDER BY c.created_at DESC
            LIMIT ?
          `).bind(limit).all();
          return new Response(JSON.stringify({
            success: true,
            count: items.results ? items.results.length : 0,
            consultations: items.results || []
          }), { headers: { 'Content-Type': 'application/json; charset=utf-8' } });
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

      // 4-1. 차량 증분 동기화: POST /api/sync/vehicles (DIRECTIVE 133 Compliant)
      if (pathname === '/api/sync/vehicles' && request.method === 'POST') {
        try {
          const vehicles = body.vehicles || [];
          let inserted = 0;
          let updated = 0;
          let skipped = 0;
          const now = new Date().toISOString();

          for (const v of vehicles) {
            // DIRECTIVE 135 TASK 3: 고유 ID 기반 61대 비공개 연결 (전체 번호판 부재 시에도 식별 ID로 적재 허용)
            if (!v.id) {
              skipped++;
              continue;
            }

            // DIRECTIVE 134 TASK 1: 운영 환경 테스트/프로브 식별자 원천 차단
            const testIdentifierRegex = /^(TEST|PROBE|DEMO|MOCK|TEMP)-/i;
            if (testIdentifierRegex.test(v.id) || testIdentifierRegex.test(v.plate_number || '') || testIdentifierRegex.test(v.registration_number || '')) {
              return new Response(JSON.stringify({
                error: '테스트/프로브 식별자는 운영 환경에 동기화할 수 없습니다.',
                code: 'TEST_IDENTIFIER_PROHIBITED_IN_PROD',
                rejected_id: v.id,
                rejected_plate: v.plate_number
              }), { status: 400, headers: { 'Content-Type': 'application/json' } });
            }

            // DIRECTIVE 134 TASK 1: 서버 기반 상사 동의 및 증빙 검증 (ACTIVE + marketing_consent_verified = 1)
            const sangsaName = (v.sangsa_name || '').trim();
            let isAuthorizedDealer = false;
            if (sangsaName) {
              const dealer = await db.prepare(
                "SELECT id, dealership_name, partnership_status, marketing_consent_verified FROM dealers WHERE (dealership_name = ? OR name = ?) AND partnership_status = 'ACTIVE' AND marketing_consent_verified = 1"
              ).bind(sangsaName, sangsaName).first();
              if (dealer) {
                isAuthorizedDealer = true;
              }
            }

            // DIRECTIVE 133-R & 134 & 135: 실제 전체 번호판 정규식 엄격 검증
            // 유효한 전체 번호판이 없으면 DB에는 엄격히 NULL 저장 (가상 번호판 날조 원천 차단)
            const cleanPlate = (v.plate_number || '').replace(/\s+/g, '');
            const plateRegex = /^\d{2,3}[가-힣]\d{4}$/;
            const hasValidFullPlate = plateRegex.test(cleanPlate);
            const dbPlate = hasValidFullPlate ? cleanPlate : null;

            // DIRECTIVE 134 TASK 4 & 135: 사용자 최종 승인 전까지 모든 차량 비공개 게이트 보호
            // 64노3143 및 신규 동기화 매물은 최종 사용자 승인 전까지 PENDING_REVIEW 유지
            const isGateProtectedVehicle = (cleanPlate === '64노3143' || v.id === 'e6670a2e-c532-435e-b34a-b4a3ff9a677c');

            const targetPrice = parseInt(v.target_price || 0, 10);
            const hasValidPrice = targetPrice > 0;
            const status = String(v.status || 'FOR_SALE').toUpperCase();
            const isForSale = (status === 'FOR_SALE' || status === 'AVAILABLE');
            const isSoldOrSuspended = (status === 'SOLD' || status === 'SUSPENDED' || status === 'DELETED' || status === 'INACTIVE');
            const isDemo = (v.is_demo === 1 || v.is_demo === true) ? 1 : 0;

            // DIRECTIVE 134 & 135: 사용자 최종 승인 게이트 원칙에 따라 신규/동기화 매물은 비공개(PENDING_REVIEW)로 안전 적재
            // (상사 동의 및 전체 번호판 검증 완료 시에도 사용자 최종 승인이 있어야 APPROVED로 전환)
            const shouldAutoPublish = false;

            // 미확인 제원 임의 기본값 금지 (DIRECTIVE 133-R TASK 3)
            const vYear = v.year ? parseInt(v.year, 10) : null;
            const vMileage = (typeof v.mileage === 'number' && v.mileage >= 0) ? v.mileage : null;
            const vFuel = v.fuel_type || null;
            const vTransmission = v.transmission || null;
            const vColor = v.color || null;

            // 기존 차량 확인 (번호판 유효 시 번호판 또는 ID로 대조, 미보유 시 ID로만 대조)
            let existing = null;
            if (dbPlate) {
              existing = await db.prepare('SELECT id, target_price, is_public, status, listing_ownership_type, publishing_status FROM vehicles WHERE id = ? OR plate_number = ?')
                .bind(v.id, dbPlate).first();
            } else {
              existing = await db.prepare('SELECT id, target_price, is_public, status, listing_ownership_type, publishing_status FROM vehicles WHERE id = ?')
                .bind(v.id).first();
            }

            if (existing) {
              const targetId = existing.id;

              // DIRECTIVE 133-R TASK 3: SOLD 상태 전이 가드 (단순 원본 재전송으로 판매완료/비공개 매물 재공개 절대 차단)
              if (existing.status === 'SOLD' || existing.publishing_status === 'UNPUBLISHED') {
                if (!isSoldOrSuspended) {
                  // 이미 판매완료 또는 비공개된 차량은 관리자 승인 없이 동기화로 재공개하지 않고 메타데이터만 갱신
                  await db.prepare(`
                    UPDATE vehicles SET
                      model_name = COALESCE(?, model_name),
                      updated_at = ?
                    WHERE id = ?
                  `).bind(v.model_name || null, now, targetId).run();
                  updated++;
                  continue;
                }
              }

              if (isSoldOrSuspended) {
                // 판매완료/광고중지 시 자동 비공개 전환 (DIRECTIVE 133 & 136 TASK 1)
                await db.prepare(`
                  UPDATE vehicles SET
                    status = ?,
                    is_public = 0,
                    publishing_status = 'UNPUBLISHED',
                    updated_at = ?
                  WHERE id = ?
                `).bind(status, now, targetId).run();
              } else {
                // DIRECTIVE 136 TASK 1: 관리자 공개 승인 상태 영구 보존
                // 1) 64노3143은 사용자 명시적 최종 승인 전까지 PENDING_REVIEW 및 비공개 엄격 보호
                // 2) 기존에 관리자가 승인(APPROVED)하여 공개(is_public=1) 중이던 차량은 가격/제원 업데이트 후에도 APPROVED 및 is_public=1 유지
                // 3) 그 외 미승인 차량은 기존 비공개 상태 유지 (신규 차량은 PENDING_REVIEW)
                let finalPub = 'PENDING_REVIEW';
                let finalPublic = 0;

                if (isGateProtectedVehicle) {
                  finalPub = 'PENDING_REVIEW';
                  finalPublic = 0;
                } else if (existing.publishing_status === 'APPROVED' && (existing.is_public === 1 || existing.is_public === true)) {
                  finalPub = 'APPROVED';
                  finalPublic = 1;
                } else {
                  finalPub = existing.publishing_status || 'PENDING_REVIEW';
                  finalPublic = (existing.is_public === 1 || existing.is_public === true) ? 1 : 0;
                }

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
                    target_price = CASE WHEN ? > 0 THEN ? ELSE target_price END,
                    status = COALESCE(?, status),
                    is_public = ?,
                    publishing_status = ?,
                    primary_photo_url = CASE WHEN ? != '' AND ? IS NOT NULL THEN ? ELSE primary_photo_url END,
                    updated_at = ?
                  WHERE id = ?
                `).bind(
                  v.model_name || null, vYear, vMileage, vFuel, vTransmission, vColor,
                  v.manufacturer || null, v.trim || null, targetPrice, targetPrice, status,
                  finalPublic, finalPub,
                  v.primary_photo_url || '', v.primary_photo_url || '', v.primary_photo_url || '',
                  now, targetId
                ).run();
              }

              // 제휴 상사 정보 연동 (vehicle_listings)
              if (v.sangsa_name || v.dealer_name) {
                const listingId = 'LISTING-' + targetId;
                const origListingId = v.registration_number || targetId;
                await db.prepare(`
                  INSERT OR REPLACE INTO vehicle_listings (
                    id, vehicle_id, platform, listing_id, advertised_price, listing_status,
                    first_observed_at, last_observed_at, region, is_janghanpyeong,
                    raw_seller_name, location_category, is_demo
                  ) VALUES (
                    ?, ?, 'CARMANAGER', ?, ?, ?,
                    ?, ?, '성동구/장안모터프라', 1,
                    ?, 'JANGHANPYEONG', 0
                  )
                `).bind(
                  listingId, targetId, origListingId, targetPrice, status,
                  now, now,
                  v.sangsa_name || '(주)더쿨모터스'
                ).run();
              }
              updated++;
            } else {
              // 신규 등록: 전체 번호판 및 상사 인가 검증 충족 시에만 APPROVED, 미충족 시 무조건 PENDING_REVIEW & is_public=0
              const pubStatus = shouldAutoPublish ? 'APPROVED' : 'PENDING_REVIEW';
              const isPublic = shouldAutoPublish ? 1 : 0;
              const ownershipType = isAuthorizedDealer ? 'EXTERNAL' : 'MARKET_OBSERVED';

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
                  ?, ?, 0, 0,
                  ?, ?, ?
                )
              `).bind(
                v.id, dbPlate, v.model_name || '차량', vYear, vMileage, vFuel,
                vTransmission, vColor, v.purchase_price || 0,
                targetPrice, status,
                v.vin || null, v.displacement_cc || null, v.first_registration_date || null,
                v.drive_type || null, v.interior_color || null,
                v.options_json || '[]', v.primary_photo_url || '',
                v.manufacturer || null, v.trim || null, v.body_type || null,
                isPublic, ownershipType,
                pubStatus, now, now
              ).run();

              if (v.sangsa_name || v.dealer_name) {
                const listingId = 'LISTING-' + v.id;
                const origListingId = v.registration_number || v.id;
                await db.prepare(`
                  INSERT OR REPLACE INTO vehicle_listings (
                    id, vehicle_id, platform, listing_id, advertised_price, listing_status,
                    first_observed_at, last_observed_at, region, is_janghanpyeong,
                    raw_seller_name, location_category, is_demo
                  ) VALUES (
                    ?, ?, 'CARMANAGER', ?, ?, ?,
                    ?, ?, '성동구/장안모터프라', 1,
                    ?, 'JANGHANPYEONG', 0
                  )
                `).bind(
                  listingId, v.id, origListingId, targetPrice, status,
                  now, now,
                  v.sangsa_name || '(주)더쿨모터스'
                ).run();
              }
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

      // 4-2. 사진 메타데이터 동기화: POST /api/sync/photos (DIRECTIVE 133 Compliant: APPROVED & PUBLIC 자동 부여)
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
            const approvalStatus = p.approval_status || 'APPROVED';
            const publicVisibility = p.public_visibility || 'PUBLIC';

            await db.prepare(`
              INSERT OR REPLACE INTO vehicle_photos (
                id, vehicle_id, photo_url, thumb_url, category, sort_order, is_primary,
                allow_video_use, caption, view_code, display_label, approval_status, public_visibility, created_at
              ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
            `).bind(
              photoId, vehicle_id, p.photo_url, p.thumb_url || p.photo_url,
              p.category || 'EXTERIOR', p.sort_order || 0, p.is_primary ? 1 : 0,
              p.caption || '실차 사진', p.view_code || 'EXT_FRONT', p.display_label || '실차 사진',
              approvalStatus, publicVisibility,
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
