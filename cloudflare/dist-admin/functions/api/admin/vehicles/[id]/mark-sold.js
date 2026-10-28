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
    const now = new Date().toISOString();
    await db.prepare(`
      UPDATE vehicles SET
        status = 'SOLD',
        is_public = 0,
        publishing_status = 'SOLD',
        updated_at = ?
      WHERE id = ?
    `).bind(now, vehicleId).run();

    return new Response(JSON.stringify({
      success: true,
      vehicle_id: vehicleId,
      status: 'SOLD',
      message: '차량이 판매 완료 처리되었습니다.'
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
