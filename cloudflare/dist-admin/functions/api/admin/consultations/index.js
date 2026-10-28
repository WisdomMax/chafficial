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
    const status = url.searchParams.get('status') || '';
    const search = url.searchParams.get('q') || '';

    let sql = `
      SELECT 
        c.id, c.customer_id, c.channel, c.content, c.staff_name, c.created_at, c.inquiry_source,
        cust.name as customer_name, cust.phone, cust.status as customer_status,
        cust.target_vehicle_model, cust.notes, cust.budget_max
      FROM consultations c
      LEFT JOIN customers cust ON c.customer_id = cust.id
      WHERE 1=1
    `;
    const params = [];

    if (status.trim()) {
      sql += ' AND cust.status = ?';
      params.push(status.trim());
    }

    if (search.trim()) {
      const s = '%' + search.trim() + '%';
      sql += ' AND (cust.name LIKE ? OR cust.phone LIKE ? OR c.content LIKE ?)';
      params.push(s, s, s);
    }

    sql += ' ORDER BY c.created_at DESC LIMIT 100';

    const { results } = await db.prepare(sql).bind(...params).all();

    return new Response(JSON.stringify(results || []), {
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
