import crypto from 'node:crypto';

export const b64u = (buf) => Buffer.from(buf).toString('base64url');
export const randomToken = (bytes = 32) => b64u(crypto.randomBytes(bytes));
export const sha256 = (value) => crypto.createHash('sha256').update(String(value)).digest('hex');
export const timingSafeHexEqual = (a, b) => {
  if (!a || !b || a.length !== b.length) return false;
  try { return crypto.timingSafeEqual(Buffer.from(a, 'hex'), Buffer.from(b, 'hex')); } catch { return false; }
};

export function securityMode() { return process.env.DEUS_SECURITY_MODE || 'production'; }
export function assertProductionSecrets() {
  if (securityMode() !== 'production') return;
  const required = ['DATABASE_URL','DEUS_RP_ID','DEUS_ORIGIN','DEUS_FOUNDER_EMAIL','DEUS_BOOTSTRAP_TOKEN_SHA256','DEUS_KMS_SIGN_URL','DEUS_KMS_ENCRYPT_URL','DEUS_KMS_DECRYPT_URL','DEUS_KMS_KEY_ID','DEUS_CA_SIGN_URL'];
  const missing = required.filter((k) => !process.env[k]);
  if (missing.length) throw new Error(`SECURITY_CONFIG_INCOMPLETE:${missing.join(',')}`);
  if (!process.env.DEUS_ORIGIN.startsWith('https://')) throw new Error('DEUS_ORIGIN_MUST_BE_HTTPS');
}

export function setSecurityHeaders(res) {
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('Referrer-Policy', 'no-referrer');
  res.setHeader('Permissions-Policy', 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()');
  res.setHeader('Strict-Transport-Security', 'max-age=63072000; includeSubDomains; preload');
  res.setHeader('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'");
}

export function parseCookies(req) {
  const raw = req.headers.cookie || '';
  return Object.fromEntries(raw.split(';').map((v) => v.trim()).filter(Boolean).map((v) => { const i = v.indexOf('='); return [decodeURIComponent(v.slice(0, i)), decodeURIComponent(v.slice(i + 1))]; }));
}

export function setSessionCookies(res, sessionToken, csrfToken, maxAgeSeconds = 28800) {
  res.setHeader('Set-Cookie', [
    `__Host-deus_session=${encodeURIComponent(sessionToken)}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${maxAgeSeconds}`,
    `__Host-deus_csrf=${encodeURIComponent(csrfToken)}; Path=/; Secure; SameSite=Strict; Max-Age=${maxAgeSeconds}`
  ]);
}

export function clearSessionCookies(res) {
  res.setHeader('Set-Cookie', [
    '__Host-deus_session=; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=0',
    '__Host-deus_csrf=; Path=/; Secure; SameSite=Strict; Max-Age=0'
  ]);
}

export function assertOrigin(req) {
  const expected = process.env.DEUS_ORIGIN;
  const origin = req.headers.origin;
  if (!expected || origin !== expected) throw new Error('ORIGIN_REJECTED');
}

export function assertCsrf(req, session) {
  const cookies = parseCookies(req);
  const provided = req.headers['x-deus-csrf'];
  if (!provided || !cookies['__Host-deus_csrf'] || provided !== cookies['__Host-deus_csrf']) throw new Error('CSRF_REJECTED');
  if (sha256(provided) !== session.csrf_hash) throw new Error('CSRF_SESSION_MISMATCH');
}

const B32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
export function base32Encode(buf) {
  let bits = '', out = '';
  for (const b of buf) bits += b.toString(2).padStart(8, '0');
  for (let i = 0; i < bits.length; i += 5) out += B32[parseInt(bits.slice(i, i + 5).padEnd(5, '0'), 2)];
  return out;
}
export function base32Decode(input) {
  let bits = '';
  for (const c of String(input).replace(/=+$/,'').toUpperCase()) { const i = B32.indexOf(c); if (i < 0) throw new Error('INVALID_BASE32'); bits += i.toString(2).padStart(5,'0'); }
  const bytes = [];
  for (let i = 0; i + 8 <= bits.length; i += 8) bytes.push(parseInt(bits.slice(i, i + 8), 2));
  return Buffer.from(bytes);
}
export function generateTotpSecret() { return base32Encode(crypto.randomBytes(20)); }
export function totpCode(secret, time = Date.now(), step = 30) {
  const counter = Math.floor(time / 1000 / step);
  const buf = Buffer.alloc(8); buf.writeBigUInt64BE(BigInt(counter));
  const h = crypto.createHmac('sha1', base32Decode(secret)).update(buf).digest();
  const off = h[h.length - 1] & 0x0f;
  const n = (h.readUInt32BE(off) & 0x7fffffff) % 1_000_000;
  return String(n).padStart(6, '0');
}
export function verifyTotp(secret, code) {
  const now = Date.now();
  return [-1,0,1].some((w) => totpCode(secret, now + w * 30_000) === String(code).padStart(6,'0'));
}

async function workloadCall(url, body) {
  if (!url) throw new Error('WORKLOAD_SERVICE_UNAVAILABLE');
  const token = process.env.VERCEL_OIDC_TOKEN || process.env.DEUS_WORKLOAD_IDENTITY_TOKEN;
  if (!token && securityMode() === 'production') throw new Error('WORKLOAD_IDENTITY_UNAVAILABLE');
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...(token ? { authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(5000)
  });
  if (!response.ok) throw new Error(`WORKLOAD_SERVICE_HTTP_${response.status}`);
  return response.json();
}
export async function kmsSignDigest(digestHex) {
  const data = await workloadCall(process.env.DEUS_KMS_SIGN_URL, { keyId: process.env.DEUS_KMS_KEY_ID, algorithm: 'Ed25519-or-KMS-approved', digestHex });
  if (!data.signature || !data.keyId) throw new Error('KMS_INVALID_SIGN_RESPONSE');
  return data;
}
export async function kmsEncrypt(plaintext) {
  const data = await workloadCall(process.env.DEUS_KMS_ENCRYPT_URL, { keyId: process.env.DEUS_KMS_KEY_ID, plaintext: Buffer.from(String(plaintext)).toString('base64') });
  if (!data.ciphertext || !data.keyId) throw new Error('KMS_INVALID_ENCRYPT_RESPONSE');
  return data;
}
export async function kmsDecrypt(ciphertext) {
  const data = await workloadCall(process.env.DEUS_KMS_DECRYPT_URL, { keyId: process.env.DEUS_KMS_KEY_ID, ciphertext });
  if (!data.plaintext) throw new Error('KMS_INVALID_DECRYPT_RESPONSE');
  return Buffer.from(data.plaintext, 'base64').toString('utf8');
}
export async function caSignNodeCsr(request) {
  const data = await workloadCall(process.env.DEUS_CA_SIGN_URL, { ...request, profile: 'deus-node-mtls-v1' });
  if (!data.certificateChainPem || !data.serial) throw new Error('CA_INVALID_SIGN_RESPONSE');
  return data;
}
