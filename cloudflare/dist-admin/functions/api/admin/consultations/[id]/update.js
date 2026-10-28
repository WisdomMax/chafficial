export async function onRequestPost(context) {
  const { request, params, env } = context;
  const consultationId = params.id;
  const db = env.DB;

  if (!db) {
    return new Response(JSON.stringify({ error: 'Database binding DB not found' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const body = await request.json();
    const { status, staff_name, notes } = body;

    const consultation = await db.prepare('SELECT customer_id FROM consultations WHERE id = ?').bind(consultationId).first();

    if (!consultation) {
      return new Response(JSON.stringify({ error: '상담 내역을 찾을 수 없습니다.' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    if (staff_name) {
      await db.prepare('UPDATE consultations SET staff_name = ? WHERE id = ?').bind(staff_name, consultationId).run();
    }

    if (status || notes) {
      let updateSql = 'UPDATE customers SET ';
      const updateParams = [];
      if (status) {
        updateSql += 'status = ?, ';
        updateParams.push(status);
      }
      if (notes) {
        updateSql += 'notes = COALESCE(notes || "\n", "") || ?, ';
        updateParams.push(notes);
      }
      updateSql = updateSql.slice(0, -2) + ' WHERE id = ?';
      updateParams.push(consultation.customer_id);

      await db.prepare(updateSql).bind(...updateParams).run();
    }

    return new Response(JSON.stringify({
      success: true,
      consultation_id: consultationId,
      customer_id: consultation.customer_id,
      status: status,
      message: '상담 상태가 성공적으로 갱신되었습니다.'
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
