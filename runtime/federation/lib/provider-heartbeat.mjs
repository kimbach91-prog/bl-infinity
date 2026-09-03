import { createHmac, timingSafeEqual, randomBytes } from 'node:crypto';

const NONCE_RE = /^[A-Za-z0-9_-]{16,128}$/;
const PROVIDER_ID_RE = /^[a-zA-Z0-9._:-]{2,128}$/;

export function createHeartbeatNonce() {
  return randomBytes(16).toString('base64url');
}

export function signProviderHeartbeat(secret, { providerId, timestamp, nonce, body }) {
  if (!secret) throw new Error('provider heartbeat secret is required');
  if (!PROVIDER_ID_RE.test(providerId ?? '')) throw new Error('invalid providerId');
  return createHmac('sha256', secret)
    .update(`${providerId}.${timestamp}.${nonce}.${body}`)
    .digest('base64url');
}

export async function verifyProviderHeartbeat(store, headers, body, {
  env = process.env,
  now = Date.now(),
  maxSkewMs = 120_000,
  nonceTtlMs = 5 * 60_000,
} = {}) {
  if (!store?.get || !store?.pool?.query) throw new Error('shared provider store is required');
  const providerId = header(headers, 'x-bl-provider-id');
  const timestamp = Number(header(headers, 'x-bl-timestamp'));
  const nonce = header(headers, 'x-bl-nonce');
  const signature = header(headers, 'x-bl-heartbeat-signature');
  if (!providerId || !timestamp || !nonce || !signature) return { ok: false, reason: 'missing-auth-headers' };
  if (!PROVIDER_ID_RE.test(providerId)) return { ok: false, reason: 'invalid-provider-id' };
  if (!NONCE_RE.test(nonce)) return { ok: false, reason: 'invalid-nonce' };
  if (!Number.isFinite(timestamp) || Math.abs(now - timestamp) > maxSkewMs) return { ok: false, reason: 'timestamp-skew' };

  const provider = await store.get(providerId, { now });
  if (!provider) return { ok: false, reason: 'unknown-provider' };
  if (provider.authorization?.revokedAt) return { ok: false, reason: 'provider-revoked' };
  const auth = provider.liveness?.heartbeatAuth;
  if (!auth || auth.mode !== 'hmac-env' || !auth.secretEnv) return { ok: false, reason: 'heartbeat-auth-not-granted' };
  const secret = env[auth.secretEnv];
  if (!secret) return { ok: false, reason: 'heartbeat-secret-not-configured' };

  const expected = signProviderHeartbeat(secret, { providerId, timestamp, nonce, body });
  if (!safeEqual(signature, expected)) return { ok: false, reason: 'bad-signature' };

  const consumed = await consumeHeartbeatNonce(store.pool, providerId, nonce, { now, ttlMs: Math.max(nonceTtlMs, maxSkewMs * 2) });
  if (!consumed) return { ok: false, reason: 'replay' };
  return { ok: true, providerId, provider };
}

export async function consumeHeartbeatNonce(pool, providerId, nonce, { now = Date.now(), ttlMs = 5 * 60_000 } = {}) {
  const expiresAt = new Date(now + Math.max(1, Number(ttlMs) || 1));
  await pool.query('DELETE FROM federation_provider_heartbeat_nonces WHERE expires_at <= $1', [new Date(now)]);
  const result = await pool.query(`
    INSERT INTO federation_provider_heartbeat_nonces(provider_id,nonce,seen_at,expires_at)
    VALUES($1,$2,$3,$4)
    ON CONFLICT(provider_id,nonce) DO NOTHING
    RETURNING nonce
  `, [providerId, nonce, new Date(now), expiresAt]);
  return result.rowCount === 1;
}

function safeEqual(a, b) {
  const left = Buffer.from(String(a));
  const right = Buffer.from(String(b));
  return left.length === right.length && timingSafeEqual(left, right);
}

function header(headers, name) {
  if (!headers) return null;
  if (typeof headers.get === 'function') return headers.get(name);
  return headers[name] ?? headers[name.toLowerCase()] ?? null;
}
