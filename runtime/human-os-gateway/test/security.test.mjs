import test from 'node:test';
import assert from 'node:assert/strict';
import { generateTotpSecret, totpCode, verifyTotp, setSessionCookies, sha256, assertCsrf } from '../lib/security.mjs';

test('TOTP verifies only current-window compatible code', () => {
  const secret = generateTotpSecret();
  const code = totpCode(secret);
  assert.match(code, /^\d{6}$/);
  assert.equal(verifyTotp(secret, code), true);
  assert.equal(verifyTotp(secret, code === '000000' ? '999999' : '000000'), false);
});

test('session cookie is host-only HttpOnly Secure SameSite Strict', () => {
  const headers = new Map();
  const res = { setHeader(k, v) { headers.set(k.toLowerCase(), v); } };
  setSessionCookies(res, 'session-token', 'csrf-token', 600);
  const cookies = headers.get('set-cookie');
  assert.equal(Array.isArray(cookies), true);
  assert.match(cookies[0], /^__Host-deus_session=/);
  assert.match(cookies[0], /HttpOnly/);
  assert.match(cookies[0], /Secure/);
  assert.match(cookies[0], /SameSite=Strict/);
  assert.doesNotMatch(cookies[0], /Domain=/i);
});

test('CSRF token is bound to server session hash', () => {
  const req = { headers: { cookie: '__Host-deus_csrf=abc', 'x-deus-csrf': 'abc' } };
  assert.doesNotThrow(() => assertCsrf(req, { csrf_hash: sha256('abc') }));
  assert.throws(() => assertCsrf(req, { csrf_hash: sha256('different') }), /CSRF_SESSION_MISMATCH/);
});
