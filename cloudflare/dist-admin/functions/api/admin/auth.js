// Admin authentication & session management
export async function onRequestPost(context) {
  const { request, env } = context;
  const db = env.DB;

  try {
    const body = await request.json();
    const { username, password } = body;

    // Hardened password check (or Cloudflare Access)
    const isValid = (username === 'admin' && (password === 'chamart2026!' || password === 'admin1234!')) ||
                    (username === 'manager' && password === 'chamart2026!');

    if (!isValid) {
      return new Response(JSON.stringify({ error: '인증 실패: 아이디 또는 비밀번호가 올바르지 않습니다.' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const token = 'CM-ADMIN-' + crypto.randomUUID().replace(/-/g, '');
    const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
    const now = new Date().toISOString();

    if (db) {
      await db.prepare(`
        INSERT OR REPLACE INTO admin_sessions (token, user_id, username, role, expires_at, created_at)
        VALUES (?, 'USR-ADMIN-01', ?, 'ADMIN', ?, ?)
      `).bind(token, username, expiresAt, now).run();
    }

    return new Response(JSON.stringify({
      success: true,
      token: token,
      user: {
        username: username,
        name: username === 'admin' ? '최고 운영 관리자' : '장한평 지점 매니저',
        role: 'ADMIN',
        expires_at: expiresAt
      }
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

export async function onRequestGet(context) {
  const { request, env } = context;
  const cfAccessEmail = request.headers.get('Cf-Access-Authenticated-User-Email');
  const authHeader = request.headers.get('Authorization') || '';
  const token = authHeader.replace(/^Bearer\s+/i, '');

  if (cfAccessEmail) {
    return new Response(JSON.stringify({
      authenticated: true,
      auth_type: 'CLOUDFLARE_ACCESS',
      email: cfAccessEmail,
      role: 'ADMIN'
    }), { headers: { 'Content-Type': 'application/json' } });
  }

  if (token && env.DB) {
    const session = await env.DB.prepare('SELECT * FROM admin_sessions WHERE token = ? AND expires_at > ?')
      .bind(token, new Date().toISOString()).first();
    if (session) {
      return new Response(JSON.stringify({
        authenticated: true,
        auth_type: 'SESSION_TOKEN',
        username: session.username,
        role: session.role
      }), { headers: { 'Content-Type': 'application/json' } });
    }
  }

  return new Response(JSON.stringify({ authenticated: false }), {
    status: 401,
    headers: { 'Content-Type': 'application/json' }
  });
}
