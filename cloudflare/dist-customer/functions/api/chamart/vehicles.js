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
        primary_photo_url: photos[0] || v.primary_photo_url || '/static/img/sample_car.jpg',
        photos: photos,
        photo_count: photos.length || 5,
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
