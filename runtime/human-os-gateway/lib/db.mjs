import pg from 'pg';
import { randomToken, sha256 } from './security.mjs';

let pool;
export function db() {
  if (!pool) {
    if (!process.env.DATABASE_URL) throw new Error('DATABASE_URL_REQUIRED');
    pool = new pg.Pool({ connectionString: process.env.DATABASE_URL, max: Number(process.env.DEUS_DB_POOL_MAX || 8), ssl: process.env.DEUS_DB_SSL === 'disable' ? false : { rejectUnauthorized: process.env.DEUS_DB_SSL_REJECT_UNAUTHORIZED !== 'false' } });
  }
  return pool;
}

export async function one(text, params = []) { const r = await db().query(text, params); return r.rows[0] || null; }
export async function many(text, params = []) { return (await db().query(text, params)).rows; }

export async function storeChallenge(kind, subject, challenge, context = {}, ttlSeconds = 300) {
  const id = randomToken(18);
  await db().query('INSERT INTO hos_challenges(id,kind,subject,challenge,context,expires_at) VALUES($1,$2,$3,$4,$5,now()+($6::text || \' seconds\')::interval)', [id, kind, subject, challenge, context, ttlSeconds]);
  return id;
}
export async function consumeChallenge(id, kind) {
  const r = await db().query(`UPDATE hos_challenges SET consumed_at=now() WHERE id=$1 AND kind=$2 AND consumed_at IS NULL AND expires_at>now() RETURNING *`, [id, kind]);
  return r.rows[0] || null;
}

export async function createSession(userId, aal, req, ttlSeconds = 28800) {
  const token = randomToken(32), csrf = randomToken(24);
  const sessionHash = sha256(token), csrfHash = sha256(csrf);
  const ip = req.headers['x-forwarded-for']?.split(',')[0]?.trim() || req.socket?.remoteAddress || 'unknown';
  const ua = req.headers['user-agent'] || 'unknown';
  await db().query('INSERT INTO hos_sessions(session_hash,user_id,csrf_hash,aal,expires_at,ip_hash,user_agent_hash) VALUES($1,$2,$3,$4,now()+($5::text || \' seconds\')::interval,$6,$7)', [sessionHash,userId,csrfHash,aal,ttlSeconds,sha256(ip),sha256(ua)]);
  return { token, csrf, ttlSeconds };
}
export async function getSession(token) {
  if (!token) return null;
  return one(`SELECT s.*, u.email, u.role, u.status FROM hos_sessions s JOIN hos_users u ON u.id=s.user_id WHERE s.session_hash=$1 AND s.revoked_at IS NULL AND s.expires_at>now() AND u.status='active'`, [sha256(token)]);
}
export async function revokeSession(token) { if (token) await db().query('UPDATE hos_sessions SET revoked_at=now() WHERE session_hash=$1', [sha256(token)]); }

export async function appendAudit(actorId, action, payload = {}) {
  const client = await db().connect();
  try {
    await client.query('BEGIN');
    const prev = (await client.query('SELECT event_hash FROM hos_audit_events ORDER BY seq DESC LIMIT 1 FOR UPDATE')).rows[0]?.event_hash || null;
    const eventId = randomToken(18);
    const createdAt = new Date().toISOString();
    const canonical = JSON.stringify({ eventId, actorId: actorId || null, action, payload, prevHash: prev, createdAt });
    const eventHash = sha256(canonical);
    await client.query('INSERT INTO hos_audit_events(event_id,actor_id,action,payload,prev_hash,event_hash,created_at) VALUES($1,$2,$3,$4,$5,$6,$7)', [eventId, actorId || null, action, payload, prev, eventHash, createdAt]);
    await client.query('COMMIT');
    return { eventId, eventHash, prevHash: prev, createdAt };
  } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
}

export async function takeRate(bucketKey, { capacity = 12, refillPerSecond = 0.2, cost = 1 } = {}) {
  const client = await db().connect();
  try {
    await client.query('BEGIN');
    const row = (await client.query('SELECT * FROM hos_rate_limits WHERE bucket_key=$1 FOR UPDATE', [bucketKey])).rows[0];
    const now = Date.now();
    let tokens = row ? Number(row.tokens) : capacity;
    let updated = row ? new Date(row.updated_at).getTime() : now;
    tokens = Math.min(capacity, tokens + Math.max(0, now - updated) / 1000 * refillPerSecond);
    const ok = tokens >= cost;
    if (ok) tokens -= cost;
    await client.query(`INSERT INTO hos_rate_limits(bucket_key,tokens,updated_at) VALUES($1,$2,now()) ON CONFLICT(bucket_key) DO UPDATE SET tokens=EXCLUDED.tokens, updated_at=EXCLUDED.updated_at`, [bucketKey, tokens]);
    await client.query('COMMIT');
    return { ok, retryAfterSeconds: ok ? 0 : Math.max(1, Math.ceil((cost - tokens) / refillPerSecond)) };
  } catch (e) { await client.query('ROLLBACK'); throw e; } finally { client.release(); }
}
