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
    const v = await db.prepare('SELECT is_priority_exposure FROM vehicles WHERE id = ?').bind(vehicleId).first();
    if (!v) {
      return new Response(JSON.stringify({ error: '차량을 찾을 수 없습니다.' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const nextPriority = v.is_priority_exposure ? 0 : 1;
    const rank = nextPriority ? 100 : 0;
    const reason = nextPriority ? '관리자 지정 차마트 직영 우선추천' : null;
    const now = new Date().toISOString();

    await db.prepare(`
      UPDATE vehicles SET
        is_priority_exposure = ?,
        priority_rank = ?,
        priority_reason = ?,
        updated_at = ?
      WHERE id = ?
    `).bind(nextPriority, rank, reason, now, vehicleId).run();

    return new Response(JSON.stringify({
      success: true,
      vehicle_id: vehicleId,
      is_priority_exposure: !!nextPriority,
      priority_rank: rank,
      message: nextPriority ? '차마트 추천 우선노출 매물로 지정되었습니다.' : '우선노출이 해제되었습니다.'
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
