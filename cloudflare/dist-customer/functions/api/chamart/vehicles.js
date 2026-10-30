// Cloudflare Pages Function: /api/chamart/vehicles (DIRECTIVE 130 Compliant)
// Strict Real-Vehicle Only: 4-Tier Exposure Ranking, Zero Fabricated Photos

function isValidPhoto(url) {
  if (!url || typeof url !== 'string') return false;
  const u = url.trim().toLowerCase();
  if (!u) return false;
  if (u.includes('placeholder') || u.includes('slots') || u.includes('sample_car') || u.includes('no_photo')) return false;
  return true;
}

const NO_PHOTO_FALLBACK = '/static/img/no_photo.svg';

export async function onRequestGet({ request, env, waitUntil }) {
  const url = new URL(request.url);

  // 1. Edge Cache
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

    let sql = `SELECT 
      id, plate_number, model_name, manufacturer, trim, year, mileage, 
      fuel_type, transmission, color, target_price, primary_photo_url, 
      listing_ownership_type, is_priority_exposure, priority_rank, 
      status, publishing_status, options_json
    FROM vehicles 
    WHERE (is_public = 1 OR is_public IS NULL) 
      AND (is_demo = 0 OR is_demo IS NULL)
      AND (status IN ('AVAILABLE', 'FOR_SALE') OR status IS NULL)`;
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

    // DIRECTIVE 130 TASK 2: 4단계 노출 순위
    const tierOrderClause = `
      (CASE 
        WHEN (listing_ownership_type = 'OWNED' OR listing_ownership_type = 'CHAMART_OWNED') 
             AND (primary_photo_url IS NOT NULL AND primary_photo_url != '' AND primary_photo_url NOT LIKE '%placeholder%' AND primary_photo_url NOT LIKE '%no_photo%') THEN 1
        WHEN (listing_ownership_type = 'OWNED' OR listing_ownership_type = 'CHAMART_OWNED') THEN 2
        WHEN (primary_photo_url IS NOT NULL AND primary_photo_url != '' AND primary_photo_url NOT LIKE '%placeholder%' AND primary_photo_url NOT LIKE '%no_photo%') THEN 3
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
        'Cache-Control': 'public, max-age=60, s-maxage=120',
        'Access-Control-Allow-Origin': '*'
      }
    });

    if (waitUntil) {
      waitUntil(cache.put(cacheKey, resp.clone()));
    }
    return resp;
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), { status: 500 });
  }
}
