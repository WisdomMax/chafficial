export async function onRequestPost(context) {
  const { request, env } = context;
  const db = env.DB;

  if (!db) {
    return new Response(JSON.stringify({ error: 'Database binding DB not found' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const body = await request.json();
    const { name, phone, message, target_vehicle_id, target_vehicle_model, budget_max, branch_id } = body;

    if (!name || !phone) {
      return new Response(JSON.stringify({ error: '이름과 연락처는 필수 항목입니다.' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const customerId = 'CUST-' + crypto.randomUUID().slice(0, 8);
    const consultationId = 'CONS-' + crypto.randomUUID().slice(0, 8);
    const now = new Date().toISOString();
    const branchId = branch_id || '61fea9a4-58f0-42bd-862c-14fd16d0d21c'; // 장한평 본사

    // 1. 고객 정보 등록 (동일 전화번호 고객 있으면 업데이트)
    const existingCust = await db.prepare('SELECT id FROM customers WHERE phone = ?').bind(phone).first();
    let finalCustId = customerId;

    if (existingCust) {
      finalCustId = existingCust.id;
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
      `).bind(
        customerId, branchId, name, phone, 
        target_vehicle_model || '차마트 문의 차량',
        budget_max || null,
        message || '웹사이트 간편 상담 신청',
        now
      ).run();
    }

    // 2. 상담 내역 저장
    const inquiryContent = `[차마트 웹사이트 실시간 접수] 고객명: ${name}, 연락처: ${phone}, 문의차량: ${target_vehicle_model || target_vehicle_id || '일반 문의'}, 상담내용: ${message || '상담 희망'}`;

    await db.prepare(`
      INSERT INTO consultations (
        id, customer_id, channel, content, staff_name, created_at, inquiry_source
      ) VALUES (?, ?, 'CHAMART_WEB', ?, '차마트 상담팀', ?, 'CHAMART_WEB_FORM')
    `).bind(consultationId, finalCustId, inquiryContent, now).run();

    return new Response(JSON.stringify({
      success: true,
      message: '상담 신청이 정상 접수되었습니다. 차마트 전담 상담원이 신속히 연락드리겠습니다.',
      consultation_id: consultationId,
      customer_id: finalCustId
    }), {
      headers: {
        'Content-Type': 'application/json'
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}
