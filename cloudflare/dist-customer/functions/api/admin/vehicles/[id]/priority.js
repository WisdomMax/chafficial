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
    const { is_priority_exposure, listing_ownership_type, priority_rank, priority_reason } = body;

    const rank = is_priority_exposure ? (priority_rank || 100) : 0;
    const reason = priority_reason || (is_priority_exposure ? '관리자 지정 차마트 직영 우선추천' : null);
    const ownership = listing_ownership_type || 'OWNED';
    const isPriorityInt = is_priority_exposure ? 1 : 0;
    const now = new Date().toISOString();

    await db.prepare(`
      UPDATE vehicles SET
        is_priority_exposure = ?,
        priority_rank = ?,
        priority_reason = ?,
        listing_ownership_type = ?,
        updated_at = ?
      WHERE id = ?
    `).bind(isPriorityInt, rank, reason, ownership, now, vehicleId).run();

    return new Response(JSON.stringify({
      success: true,
      vehicle_id: vehicleId,
      is_priority_exposure: !!is_priority_exposure,
      listing_ownership_type: ownership,
      priority_rank: rank,
      message: '차마트 우선노출 및 보유 상태가 성공적으로 저장되었습니다.'
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
