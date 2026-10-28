export async function onRequestPost(context) {
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
    const v = await db.prepare('SELECT is_public FROM vehicles WHERE id = ?').bind(vehicleId).first();
    if (!v) {
      return new Response(JSON.stringify({ error: '차량을 찾을 수 없습니다.' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const nextPublic = v.is_public ? 0 : 1;
    const nextStatus = nextPublic ? 'APPROVED' : 'DRAFT';
    const now = new Date().toISOString();

    await db.prepare(`
      UPDATE vehicles SET
        is_public = ?,
        publishing_status = ?,
        updated_at = ?
      WHERE id = ?
    `).bind(nextPublic, nextStatus, now, vehicleId).run();

    return new Response(JSON.stringify({
      success: true,
      vehicle_id: vehicleId,
      is_public: !!nextPublic,
      publishing_status: nextStatus,
      message: nextPublic ? '차량이 공개 승인되었습니다. 고객용 사이트에 즉시 노출됩니다.' : '차량이 비공개(초안)로 전환되었습니다.'
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
