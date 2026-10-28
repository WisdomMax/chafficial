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
    const search = url.searchParams.get('q') || url.searchParams.get('search') || '';
    const status = url.searchParams.get('status') || '';
    const ownership = url.searchParams.get('ownership') || '';
    const isPublic = url.searchParams.get('is_public');
    const page = parseInt(url.searchParams.get('page') || '1', 10);
    const limit = parseInt(url.searchParams.get('limit') || '30', 10);
    const offset = (page - 1) * limit;

    let sql = 'SELECT * FROM vehicles WHERE 1=1';
    let countSql = 'SELECT COUNT(*) as total FROM vehicles WHERE 1=1';
    const params = [];
    const countParams = [];

    if (search.trim()) {
      const s = '%' + search.trim() + '%';
      const cond = ' AND (model_name LIKE ? OR plate_number LIKE ? OR manufacturer LIKE ?)';
      sql += cond;
      countSql += cond;
      params.push(s, s, s);
      countParams.push(s, s, s);
    }

    if (status.trim()) {
      sql += ' AND status = ?';
      countSql += ' AND status = ?';
      params.push(status.trim());
      countParams.push(status.trim());
    }

    if (ownership.trim()) {
      sql += ' AND listing_ownership_type = ?';
      countSql += ' AND listing_ownership_type = ?';
      params.push(ownership.trim());
      countParams.push(ownership.trim());
    }

    if (isPublic !== null && isPublic !== undefined && isPublic !== '') {
      const pubInt = (isPublic === '1' || isPublic === 'true') ? 1 : 0;
      sql += ' AND is_public = ?';
      countSql += ' AND is_public = ?';
      params.push(pubInt);
      countParams.push(pubInt);
    }

    sql += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
    params.push(limit, offset);

    const totalRes = await db.prepare(countSql).bind(...countParams).first();
    const total = totalRes ? totalRes.total : 0;

    const { results } = await db.prepare(sql).bind(...params).all();

    return new Response(JSON.stringify({
      total: total,
      page: page,
      limit: limit,
      total_pages: Math.ceil(total / limit),
      items: results || []
    }), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store'
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
