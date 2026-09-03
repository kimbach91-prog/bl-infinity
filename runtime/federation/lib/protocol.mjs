import { createHmac, timingSafeEqual, randomBytes } from 'node:crypto';

export function createNonce() { return randomBytes(16).toString('base64url'); }
export function signWorkerEnvelope(secret, { timestamp, nonce, body }) {
  if (!secret) throw new Error('worker shared secret is required');
  return createHmac('sha256', secret).update(`${timestamp}.${nonce}.${body}`).digest('base64url');
}
export class ReplayGuard {
  constructor({ ttlMs = 5 * 60_000, maxEntries = 10_000 } = {}) { this.ttlMs = ttlMs; this.maxEntries = maxEntries; this.nonces = new Map(); }
  consume(nonce, now = Date.now()) { this.sweep(now); if (this.nonces.has(nonce)) return false; if (this.nonces.size >= this.maxEntries) this.nonces.delete(this.nonces.keys().next().value); this.nonces.set(nonce, now + this.ttlMs); return true; }
  sweep(now = Date.now()) { for (const [nonce, expires] of this.nonces) if (expires <= now) this.nonces.delete(nonce); }
}
export function verifyWorkerEnvelope(secret, headers, body, { now = Date.now(), maxSkewMs = 120_000, replayGuard = null } = {}) {
  const timestamp = Number(header(headers, 'x-bl-timestamp'));
  const nonce = header(headers, 'x-bl-nonce');
  const signature = header(headers, 'x-bl-signature');
  if (!timestamp || !nonce || !signature) return { ok: false, reason: 'missing-auth-headers' };
  if (Math.abs(now - timestamp) > maxSkewMs) return { ok: false, reason: 'timestamp-skew' };
  const expected = signWorkerEnvelope(secret, { timestamp, nonce, body });
  const a = Buffer.from(signature); const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return { ok: false, reason: 'bad-signature' };
  if (replayGuard && !replayGuard.consume(nonce, now)) return { ok: false, reason: 'replay' };
  return { ok: true };
}
function header(headers, name) { if (!headers) return null; if (typeof headers.get === 'function') return headers.get(name); return headers[name] ?? headers[name.toLowerCase()] ?? null; }
