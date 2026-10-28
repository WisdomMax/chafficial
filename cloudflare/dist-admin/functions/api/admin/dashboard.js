export async function onRequestGet(context) {
  const { env } = context;
  const db = env.DB;

  if (!db) {
    return new Response(JSON.stringify({ error: 'Database binding DB not found' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const totalVehicles = await db.prepare('SELECT COUNT(*) as cnt FROM vehicles').first();
    const publicVehicles = await db.prepare('SELECT COUNT(*) as cnt FROM vehicles WHERE is_public = 1').first();
    const ownedVehicles = await db.prepare("SELECT COUNT(*) as cnt FROM vehicles WHERE listing_ownership_type = 'OWNED'").first();
    const priorityVehicles = await db.prepare('SELECT COUNT(*) as cnt FROM vehicles WHERE is_priority_exposure = 1').first();
    const soldVehicles = await db.prepare("SELECT COUNT(*) as cnt FROM vehicles WHERE status = 'SOLD'").first();
    const totalConsultations = await db.prepare('SELECT COUNT(*) as cnt FROM consultations').first();
    const newConsultations = await db.prepare("SELECT COUNT(*) as cnt FROM customers WHERE status = 'NEW'").first();

    const recentVehicles = await db.prepare(
      'SELECT id, plate_number, model_name, target_price, year, mileage, is_public, is_priority_exposure, listing_ownership_type, created_at FROM vehicles ORDER BY created_at DESC LIMIT 5'
    ).all();

    const recentConsultations = await db.prepare(`
      SELECT c.id, c.content, c.created_at, cust.name as customer_name, cust.phone, cust.status, cust.target_vehicle_model
      FROM consultations c
      LEFT JOIN customers cust ON c.customer_id = cust.id
      ORDER BY c.created_at DESC LIMIT 5
    `).all();

    return new Response(JSON.stringify({
      metrics: {
        total_vehicles: totalVehicles ? totalVehicles.cnt : 0,
        public_vehicles: publicVehicles ? publicVehicles.cnt : 0,
        owned_vehicles: ownedVehicles ? ownedVehicles.cnt : 0,
        priority_exposure_count: priorityVehicles ? priorityVehicles.cnt : 0,
        sold_vehicles: soldVehicles ? soldVehicles.cnt : 0,
        total_consultations: totalConsultations ? totalConsultations.cnt : 0,
        new_inquiries: newConsultations ? newConsultations.cnt : 0
      },
      recent_vehicles: recentVehicles.results || [],
      recent_consultations: recentConsultations.results || []
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
