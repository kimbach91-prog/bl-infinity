// Owner-only credential transport. Host configuration is admission, not caller input.
// This module neither provisions IAM nor changes Cloud Run authentication.
const STS = 'https://sts.googleapis.com/v1/token';
const TOKEN = 'urn:ietf:params:oauth:token-type:';
const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', { fatal: true });
const BODY_LIMIT = 65536, RESPONSE_LIMIT = 131072, TOKEN_LIMIT = 12288;
const PUBLIC_CODES = new Set(['PATH_REJECTED', 'REQUEST_REJECTED', 'ACCESS_REJECTED',
  'KEYS_UNAVAILABLE', 'STS_UNAVAILABLE', 'IAM_UNAVAILABLE', 'BACKEND_UNCONFIRMED']);
const fail = (code) => { throw new Error(code); };
const requireValue = (ok, code) => { if (!ok) fail(code); };

function hostConfig(value) {
  const keys = ['teamDomain', 'cfAudience', 'ownerEmail', 'projectNumber',
    'wifPool', 'wifProvider', 'invokerServiceAccount', 'cloudRunOrigin', 'publicOrigin'];
  requireValue(value && keys.every(k => typeof value[k] === 'string') &&
    Object.keys(value).every(k => keys.includes(k)), 'HOST_CONFIG_INVALID');
  const c = Object.fromEntries(keys.map(k => [k, value[k]]));
  requireValue(/^https:\/\/[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.cloudflareaccess\.com$/.test(c.teamDomain), 'HOST_CONFIG_INVALID');
  let u; try { u = new URL(c.cloudRunOrigin); } catch { fail('HOST_CONFIG_INVALID'); }
  requireValue(u.origin === c.cloudRunOrigin && u.protocol === 'https:' &&
    !u.username && !u.password && !u.port && /^[a-z0-9.-]+\.run\.app$/.test(u.hostname) &&
    u.hostname.split('.').every(x => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(x)), 'HOST_CONFIG_INVALID');
  let front; try { front = new URL(c.publicOrigin); } catch { fail('HOST_CONFIG_INVALID'); }
  requireValue(front.origin === c.publicOrigin && front.protocol === 'https:' && !front.username &&
    !front.password && !front.port && /^(?:[a-z0-9-]+\.)+[a-z]{2,63}$/.test(front.hostname), 'HOST_CONFIG_INVALID');
  requireValue(/^[A-Za-z0-9_-]{1,256}$/.test(c.cfAudience) &&
    /^[^\s@<>]{1,64}@[A-Za-z0-9.-]{1,253}$/.test(c.ownerEmail) &&
    /^[1-9][0-9]{5,19}$/.test(c.projectNumber) &&
    /^[a-z][a-z0-9-]{3,31}$/.test(c.wifPool) && /^[a-z][a-z0-9-]{3,31}$/.test(c.wifProvider) &&
    /^[a-z][a-z0-9-]{4,28}[a-z0-9]@[a-z][a-z0-9-]{4,28}[a-z0-9]\.iam\.gserviceaccount\.com$/.test(c.invokerServiceAccount), 'HOST_CONFIG_INVALID');
  return Object.freeze(c);
}

function fromBase64url(s) {
  requireValue(typeof s === 'string' && /^[A-Za-z0-9_-]+$/.test(s) && s.length % 4 !== 1, 'ACCESS_REJECTED');
  let text; try { text = atob(s.replaceAll('-', '+').replaceAll('_', '/') + '='.repeat((4 - s.length % 4) % 4)); }
  catch { fail('ACCESS_REJECTED'); }
  return Uint8Array.from(text, x => x.charCodeAt(0));
}
function objectJson(bytes, code) {
  try {
    const value = JSON.parse(decoder.decode(bytes));
    requireValue(value && typeof value === 'object' && !Array.isArray(value), code);
    return value;
  } catch { fail(code); }
}
async function readBounded(body, limit, code, signal) {
  if (!body) return new Uint8Array();
  const reader = body.getReader(), chunks = []; let size = 0;
  let onAbort, cancelled = false;
  const cancel = () => { if (!cancelled) { cancelled = true; reader.cancel().catch(() => {}); } };
  const abort = new Promise((_, reject) => {
    onAbort = () => { cancel(); reject(new Error(code)); };
    signal.addEventListener('abort', onAbort, { once: true });
    if (signal.aborted) onAbort();
  });
  try {
    for (;;) {
      const { value, done } = await Promise.race([reader.read(), abort]); if (done) break;
      size += value.byteLength; requireValue(size <= limit, code); chunks.push(value);
    }
    const result = new Uint8Array(size); let offset = 0;
    for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.byteLength; }
    return result;
  } finally {
    signal.removeEventListener('abort', onAbort); cancel();
    try { reader.releaseLock(); } catch {}
  }
}
async function timed(operation, timeoutMs, code) {
  const controller = new AbortController(); let timer;
  try {
    return await Promise.race([operation(controller.signal), new Promise((_, reject) => {
      timer = setTimeout(() => { controller.abort(); reject(new Error(code)); }, timeoutMs);
    })]);
  } catch { fail(code); }
  finally { clearTimeout(timer); controller.abort(); }
}
function claimsAllowed(p, c, now) {
  const t = Math.floor(now() / 1000), audiences = Array.isArray(p.aud) ? p.aud : [p.aud];
  requireValue(p.iss === c.teamDomain && p.email === c.ownerEmail && p.type === 'app' &&
    audiences.length > 0 && audiences.length <= 8 && audiences.every(x => typeof x === 'string') && audiences.includes(c.cfAudience) &&
    Number.isSafeInteger(p.exp) && Number.isSafeInteger(p.nbf) && Number.isSafeInteger(p.iat) &&
    p.nbf <= t && p.iat <= t && p.nbf <= p.iat && p.iat < p.exp && p.exp > t, 'ACCESS_REJECTED');
}
function cleanFailure(code) {
  if (!PUBLIC_CODES.has(code)) code = 'REQUEST_REJECTED';
  const status = code === 'PATH_REJECTED' ? 404 : code === 'ACCESS_REJECTED' ? 403 :
    code === 'REQUEST_REJECTED' ? 400 : 502;
  return Response.json({ ok: false, error: code,
    effect: code === 'BACKEND_UNCONFIRMED' ? 'UNKNOWN' : 'NO_DISPATCH', retry: false },
  { status, headers: { 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' } });
}

/** Returns (Request) => Promise<Response>. Call only with reviewed host configuration.
 * fetchImpl/now/timeoutMs are host-only test seams; no request target overrides exist.
 * Every invocation exchanges fresh credentials; redirects/retries/fallbacks are denied.
 */
export function createOwnerCloudRunInvoker(config, {
  fetchImpl = globalThis.fetch, now = Date.now, timeoutMs = 8000,
} = {}) {
  const c = hostConfig(config);
  requireValue(typeof fetchImpl === 'function' && typeof now === 'function' &&
    Number.isInteger(timeoutMs) && timeoutMs >= 1 && timeoutMs <= 30000, 'HOST_CONFIG_INVALID');
  const audience = `//iam.googleapis.com/projects/${c.projectNumber}/locations/global/workloadIdentityPools/${c.wifPool}/providers/${c.wifProvider}`;
  const iam = `https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${c.invokerServiceAccount}:generateIdToken`;
  async function wire(url, init, code, limit = 32768, acceptClientError = false) {
    return timed(async signal => {
      const response = await fetchImpl(url, { ...init, signal, redirect: 'manual', credentials: 'omit', referrerPolicy: 'no-referrer' });
      if (!response.ok && !(acceptClientError && response.status >= 400 && response.status < 500)) {
        response.body?.cancel().catch(() => {}); fail(code);
      }
      const length = response.headers.get('content-length');
      if (length !== null && !(/^[0-9]+$/.test(length) && Number(length) <= limit)) {
        response.body?.cancel().catch(() => {}); fail(code);
      }
      return { response, bytes: await readBounded(response.body, limit, code, signal) };
    }, timeoutMs, code);
  }
  async function verifyAccess(token) {
    requireValue(typeof token === 'string' && token.length <= TOKEN_LIMIT, 'ACCESS_REJECTED');
    const segments = token.split('.'); requireValue(segments.length === 3, 'ACCESS_REJECTED');
    const h = objectJson(fromBase64url(segments[0]), 'ACCESS_REJECTED');
    const p = objectJson(fromBase64url(segments[1]), 'ACCESS_REJECTED');
    requireValue(h.alg === 'RS256' && typeof h.kid === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(h.kid) &&
      h.crit === undefined && h.b64 === undefined, 'ACCESS_REJECTED');
    claimsAllowed(p, c, now);
    const result = await wire(`${c.teamDomain}/cdn-cgi/access/certs`, { method: 'GET' }, 'KEYS_UNAVAILABLE');
    const jwks = objectJson(result.bytes, 'KEYS_UNAVAILABLE');
    requireValue(Array.isArray(jwks.keys) && jwks.keys.length <= 16, 'KEYS_UNAVAILABLE');
    const keys = jwks.keys.filter(k => k && k.kid === h.kid);
    requireValue(keys.length === 1, 'ACCESS_REJECTED');
    const jwk = keys[0]; requireValue(jwk.kty === 'RSA' && jwk.alg === 'RS256' && jwk.use === 'sig' &&
      typeof jwk.n === 'string' && typeof jwk.e === 'string', 'ACCESS_REJECTED');
    let valid = false;
    try {
      const key = await globalThis.crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
      requireValue(key.algorithm.modulusLength >= 2048, 'ACCESS_REJECTED');
      valid = await globalThis.crypto.subtle.verify('RSASSA-PKCS1-v1_5', key,
        fromBase64url(segments[2]), encoder.encode(`${segments[0]}.${segments[1]}`));
    } catch { fail('ACCESS_REJECTED'); }
    requireValue(valid, 'ACCESS_REJECTED'); claimsAllowed(p, c, now);
  }
  return async function invokeOwnerRequest(request) {
    let backendSent = false;
    try {
      const url = new URL(request.url);
      const read = request.method === 'GET' && (['/api/session', '/api/jobs'].includes(url.pathname) || /^\/api\/jobs\/[a-f0-9]{32}$/.test(url.pathname));
      const write = request.method === 'POST' && url.pathname === '/api/jobs';
      requireValue(url.origin === c.publicOrigin && !url.username && !url.password && !url.search && !url.hash &&
        (read || write), 'PATH_REJECTED');
      requireValue((!request.headers.has('origin') || request.headers.get('origin') === c.publicOrigin) &&
        (!write || request.headers.get('origin') === c.publicOrigin), 'ACCESS_REJECTED');
      const token = request.headers.get('cf-access-jwt-assertion');
      await verifyAccess(token);
      let body;
      const headers = new Headers({ 'cf-access-jwt-assertion': token, origin: c.publicOrigin });
      if (write) {
        requireValue(/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(request.headers.get('content-type') || ''), 'REQUEST_REJECTED');
        body = await timed(signal => readBounded(request.body, BODY_LIMIT, 'REQUEST_REJECTED', signal), timeoutMs, 'REQUEST_REJECTED');
        objectJson(body, 'REQUEST_REJECTED'); // Transport only: preserve exact WorkID/body bytes.
        headers.set('content-type', 'application/json');
        requireValue(request.headers.has('x-csrf-token') && request.headers.has('idempotency-key'), 'REQUEST_REJECTED');
      }
      for (const name of ['x-csrf-token', 'idempotency-key']) {
        const value = request.headers.get(name);
        if (value !== null) {
          requireValue(/^[\x21-\x7e]{1,256}$/.test(value) &&
            (name !== 'idempotency-key' || (value.length >= 8 && value.length <= 128)), 'REQUEST_REJECTED');
          headers.set(name, value);
        }
      }
      const sts = objectJson((await wire(STS, { method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ grantType: 'urn:ietf:params:oauth:grant-type:token-exchange', audience,
          scope: 'https://www.googleapis.com/auth/cloud-platform', requestedTokenType: `${TOKEN}access_token`,
          subjectToken: token, subjectTokenType: `${TOKEN}jwt` }) }, 'STS_UNAVAILABLE')).bytes, 'STS_UNAVAILABLE');
      requireValue(typeof sts.access_token === 'string' && /^[A-Za-z0-9._~+\/-]{1,12288}=*$/.test(sts.access_token) &&
        sts.token_type === 'Bearer' && sts.issued_token_type === `${TOKEN}access_token` &&
        Number.isSafeInteger(sts.expires_in) && sts.expires_in > 0, 'STS_UNAVAILABLE');
      const id = objectJson((await wire(iam, { method: 'POST', headers: {
        'content-type': 'application/json', authorization: `Bearer ${sts.access_token}` },
        body: JSON.stringify({ audience: c.cloudRunOrigin, includeEmail: true }) }, 'IAM_UNAVAILABLE')).bytes, 'IAM_UNAVAILABLE');
      requireValue(typeof id.token === 'string' && id.token.length <= TOKEN_LIMIT &&
        /^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(id.token), 'IAM_UNAVAILABLE');
      claimsAllowed(objectJson(fromBase64url(token.split('.')[1]), 'ACCESS_REJECTED'), c, now);
      headers.set('x-serverless-authorization', `Bearer ${id.token}`);
      backendSent = true; // An interrupted POST may have taken effect: never retry here.
      const backend = await wire(`${c.cloudRunOrigin}${url.pathname}`, { method: request.method, headers, body }, 'BACKEND_UNCONFIRMED', RESPONSE_LIMIT, true);
      requireValue(/^application\/json(?:\s*;.*)?$/i.test(backend.response.headers.get('content-type') || ''), 'BACKEND_UNCONFIRMED');
      let text; try { text = JSON.stringify(JSON.parse(decoder.decode(backend.bytes))); } catch { fail('BACKEND_UNCONFIRMED'); }
      requireValue(![token, sts.access_token, id.token].some(secret => text.includes(secret)), 'BACKEND_UNCONFIRMED');
      if (!backend.response.ok) return Response.json({ ok: false, error: 'BACKEND_REJECTED',
        effect: 'RESPONSE_RECEIVED', retry: false }, { status: backend.response.status,
        headers: { 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' } });
      return new Response(backend.bytes, { status: backend.response.status, headers: {
        'content-type': 'application/json', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff',
        'x-deus-transport-state': 'RESPONSE_FORWARDED_UNVERIFIED' } });
    } catch (error) { return cleanFailure(backendSent ? 'BACKEND_UNCONFIRMED' : error?.message); }
  };
}
