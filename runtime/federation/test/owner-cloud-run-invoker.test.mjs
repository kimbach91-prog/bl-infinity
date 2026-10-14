import { test, before } from 'node:test';
import assert from 'node:assert/strict';
import { webcrypto } from 'node:crypto';
import { createOwnerCloudRunInvoker } from '../lib/owner-cloud-run-invoker.mjs';

// Public synthetic fixtures only. No network, account, tokens or private receiver source.
const c = Object.freeze({ teamDomain: 'https://fixture.cloudflareaccess.com', cfAudience: 'a'.repeat(64),
  ownerEmail: 'owner@example.invalid', projectNumber: '123456789012', wifPool: 'fixture-pool',
  wifProvider: 'fixture-provider', invokerServiceAccount: 'fixture-invoker@fixture-project.iam.gserviceaccount.com',
  cloudRunOrigin: 'https://fixture-owner-123456.asia-southeast1.run.app', publicOrigin: 'https://owner.example.invalid' });
const STS = 'https://sts.googleapis.com/v1/token', N = 1900000000;
const ACCESS = 'synthetic-sts-credential', IDEM = 'DEUS-SYNTHETIC-IDEMPOTENCY-0001';
const b64 = value => Buffer.from(value).toString('base64url');
const json = value => new Response(JSON.stringify(value), { headers: { 'content-type': 'application/json' } });
const ID = `${b64('{"alg":"RS256"}')}.${b64('{"aud":"fixture","exp":1900003600}')}.${b64('synthetic-google-signature')}`;
let pair, jwk;
before(async () => {
  pair = await webcrypto.subtle.generateKey({ name: 'RSASSA-PKCS1-v1_5', modulusLength: 2048,
    publicExponent: new Uint8Array([1, 0, 1]), hash: 'SHA-256' }, false, ['sign', 'verify']);
  jwk = { ...await webcrypto.subtle.exportKey('jwk', pair.publicKey), kid: 'fixture-key', alg: 'RS256', use: 'sig' };
});
async function token(overrides = {}, header = {}) {
  const h = b64(JSON.stringify({ alg: 'RS256', kid: 'fixture-key', ...header }));
  const p = b64(JSON.stringify({ iss: c.teamDomain, aud: [c.cfAudience], email: c.ownerEmail,
    exp: N + 900, nbf: N - 5, iat: N - 5, type: 'app', ...overrides }));
  const s = await webcrypto.subtle.sign('RSASSA-PKCS1-v1_5', pair.privateKey, new TextEncoder().encode(`${h}.${p}`));
  return `${h}.${p}.${b64(s)}`;
}
function request(t, path = '/api/jobs', { method = 'POST', body = '{"kind":"task_draft","payload":{"work_id":"DEUS-PUBLIC-WORK-001"}}', headers = {} } = {}) {
  return new Request(c.publicOrigin + path, { method, headers: { 'cf-access-jwt-assertion': t,
    ...(method === 'POST' ? { 'content-type': 'application/json', origin: c.publicOrigin,
      'x-csrf-token': 'synthetic-csrf', 'idempotency-key': IDEM } : {}), ...headers },
    ...(method === 'POST' ? { body } : {}) });
}
function harness(change, options = {}, config = c) {
  const calls = [];
  const fetchImpl = async (url, init) => {
    const headers = new Headers(init.headers);
    const entry = { url: String(url), init, headers,
      body: init.body instanceof Uint8Array ? new TextDecoder().decode(init.body) : init.body };
    calls.push(entry);
    if (change) { const replacement = await change(entry, calls); if (replacement) return replacement; }
    if (url === `${c.teamDomain}/cdn-cgi/access/certs`) return json({ keys: [jwk] });
    if (url === STS) return json({ access_token: ACCESS, token_type: 'Bearer',
      issued_token_type: 'urn:ietf:params:oauth:token-type:access_token', expires_in: 3600 });
    if (String(url).startsWith('https://iamcredentials.googleapis.com/')) return json({ token: ID });
    assert.ok(String(url).startsWith(c.cloudRunOrigin + '/api/'), 'only fixed backend permitted');
    return json({ job_id: 'b'.repeat(32), state: 'queued', proof: 'application response only' });
  };
  return { calls, invoke: createOwnerCloudRunInvoker(config, { fetchImpl, now: () => N * 1000, ...options }) };
}
const backendCalls = h => h.calls.filter(x => x.url.startsWith(c.cloudRunOrigin));
async function noDispatch(h, req, status = 403) {
  const response = await h.invoke(req); const value = await response.json();
  assert.equal(response.status, status); assert.equal(value.effect, 'NO_DISPATCH');
  assert.equal(value.retry, false); assert.equal(backendCalls(h).length, 0);
  return value;
}

test('actual RS256 verification and fixed STS/IAM wire contract preserve WorkID and idempotency', async () => {
  const t = await token(), h = harness();
  const body = '{ "kind": "task_draft", "payload": { "work_id": "DEUS-PUBLIC-WORK-001", "text": "\u03b4" } }';
  const response = await h.invoke(request(t, '/api/jobs', { body, headers: {
    authorization: 'Bearer caller-supplied', 'x-serverless-authorization': 'Bearer caller-supplied',
    'x-backend-origin': 'https://attacker.invalid', 'cf-access-authenticated-user-email': 'attacker@example.invalid' } }));
  assert.equal(response.status, 200); assert.equal((await response.json()).job_id, 'b'.repeat(32));
  assert.equal(h.calls.length, 4);
  const [keys, sts, iam, backend] = h.calls;
  assert.equal(keys.url, `${c.teamDomain}/cdn-cgi/access/certs`);
  assert.equal(keys.headers.has('authorization'), false); assert.equal(sts.headers.has('authorization'), false);
  assert.deepEqual(JSON.parse(sts.body), { grantType: 'urn:ietf:params:oauth:grant-type:token-exchange',
    audience: `//iam.googleapis.com/projects/${c.projectNumber}/locations/global/workloadIdentityPools/${c.wifPool}/providers/${c.wifProvider}`,
    scope: 'https://www.googleapis.com/auth/cloud-platform', requestedTokenType: 'urn:ietf:params:oauth:token-type:access_token',
    subjectToken: t, subjectTokenType: 'urn:ietf:params:oauth:token-type:jwt' });
  assert.equal(iam.url, `https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/${c.invokerServiceAccount}:generateIdToken`);
  assert.equal(iam.headers.get('authorization'), `Bearer ${ACCESS}`);
  assert.deepEqual(JSON.parse(iam.body), { audience: c.cloudRunOrigin, includeEmail: true });
  assert.equal(backend.url, c.cloudRunOrigin + '/api/jobs'); assert.equal(backend.body, body);
  assert.equal(backend.headers.get('idempotency-key'), IDEM); assert.equal(backend.headers.get('x-csrf-token'), 'synthetic-csrf');
  assert.equal(backend.headers.get('cf-access-jwt-assertion'), t);
  assert.equal(backend.headers.get('x-serverless-authorization'), `Bearer ${ID}`);
  assert.equal(backend.headers.get('origin'), c.publicOrigin); assert.equal(backend.headers.has('authorization'), false);
  assert.equal(backend.headers.has('x-backend-origin'), false); assert.equal(backend.headers.has('cookie'), false);
  for (const call of h.calls) assert.equal(call.init.redirect, 'manual');
  assert.equal(response.headers.get('x-deus-transport-state'), 'RESPONSE_FORWARDED_UNVERIFIED');
  assert.equal(response.headers.has('x-serverless-authorization'), false);
});
for (const path of ['/api/session', '/api/jobs', '/api/jobs/' + 'a'.repeat(32)]) {
  test(`readback GET ${path} forwards once without absence/no-effect inference`, async () => {
    const h = harness(); const response = await h.invoke(request(await token(), path, { method: 'GET' }));
    assert.equal(response.status, 200); assert.equal(backendCalls(h).length, 1);
    assert.equal(backendCalls(h)[0].init.method, 'GET'); assert.equal(backendCalls(h)[0].body, undefined);
    assert.equal(response.headers.get('x-deus-transport-state'), 'RESPONSE_FORWARDED_UNVERIFIED');
  });
}
test('wrong owner/audience/issuer/time/type claims reject before STS', async () => {
for (const [name, claims] of [
  ['owner', { email: 'attacker@example.invalid' }], ['owner exact case', { email: 'OWNER@example.invalid' }],
  ['audience', { aud: ['other-app'] }], ['issuer', { iss: 'https://attacker.cloudflareaccess.com' }],
  ['expiry', { exp: N }], ['expiry type', { exp: String(N + 900) }],
  ['future nbf', { nbf: N + 1 }], ['missing nbf', { nbf: null }], ['future iat', { iat: N + 1 }],
  ['global session type', { type: 'org' }],
]) {
  const h = harness(); await noDispatch(h, request(await token(claims)));
  assert.equal(h.calls.some(x => x.url === STS), false);
}
});
test('reject none, HMAC and ES256 algorithm substitutions', async () => {
for (const alg of ['none', 'HS256', 'ES256']) {
  const h = harness(); await noDispatch(h, request(await token({}, { alg })));
  assert.equal(h.calls.length, 0);
}
});
test('tampered signature and unknown signing key cannot reach STS', async () => {
  const valid = await token(), parts = valid.split('.'); parts[2] = (parts[2][0] === 'A' ? 'B' : 'A') + parts[2].slice(1);
  for (const t of [parts.join('.'), await token({}, { kid: 'untrusted-key' })]) {
    const h = harness(); await noDispatch(h, request(t)); assert.equal(h.calls.length, 1);
  }
});
test('attacker JWT jku is never fetched; only pinned certs resolve the verified key', async () => {
  const h = harness(); assert.equal((await h.invoke(request(await token({}, { jku: 'https://attacker.invalid/keys' })))).status, 200);
  assert.equal(h.calls.some(x => x.url.startsWith('https://attacker.invalid')), false);
});
test('duplicate or unsuitable JWKS keys fail closed', async () => {
  for (const keys of [[jwk, jwk], [{ ...jwk, use: 'enc' }], [{ ...jwk, alg: 'HS256' }]]) {
    const h = harness(e => e.url.endsWith('/certs') ? json({ keys }) : null);
    await noDispatch(h, request(await token())); assert.equal(h.calls.length, 1);
  }
});
test('host config rejects SSRF/non-HTTPS/userinfo/port and caller cannot mutate targets', async () => {
  for (const cloudRunOrigin of ['http://fixture.run.app', 'https://127.0.0.1', 'https://fixture.run.app.attacker.invalid',
    'https://user@fixture.run.app', 'https://fixture.run.app:8443', 'https://fixture.run.app/api/jobs']) {
    assert.throws(() => createOwnerCloudRunInvoker({ ...c, cloudRunOrigin }), /HOST_CONFIG_INVALID/);
  }
  assert.throws(() => createOwnerCloudRunInvoker({ ...c, teamDomain: 'https://attacker.invalid' }), /HOST_CONFIG_INVALID/);
  assert.throws(() => createOwnerCloudRunInvoker({ ...c, secretKey: 'not-accepted' }), /HOST_CONFIG_INVALID/);
});
test('closed path allowlist rejects guessed/control/query paths', async () => {
for (const path of ['/api/job-intent?key=some-key', '/api/jobs/' + 'A'.repeat(32), '/api/jobs/' + 'a'.repeat(31),
  '/api/jobs/' + 'a'.repeat(32) + '/cancel', '/api/jobs%2fadmin', '/api/session?target=https://attacker.invalid', '/api/system']) {
  const h = harness(); await noDispatch(h, request(await token(), path, { method: 'GET' }), 404); assert.equal(h.calls.length, 0);
}
});
test('missing/wrong POST origin and cross-origin URL reject before any fetch', async () => {
  for (const origin of [null, 'https://attacker.invalid']) {
    const h = harness(), req = request(await token());
    if (origin === null) req.headers.delete('origin'); else req.headers.set('origin', origin);
    await noDispatch(h, req); assert.equal(h.calls.length, 0);
  }
  const h = harness(); await noDispatch(h, new Request('https://attacker.invalid/api/session', { headers: {
    'cf-access-jwt-assertion': await token() } }), 404); assert.equal(h.calls.length, 0);
});
test('POST needs bounded JSON, CSRF and idempotency before Google exchange', async () => {
  for (const mode of ['csrf', 'idem', 'short', 'long', 'json', 'size']) {
    const h = harness(), req = request(await token(), '/api/jobs', { body: mode === 'json' ? 'broken' :
      mode === 'size' ? JSON.stringify({ text: 'x'.repeat(65536) }) : '{}' });
    if (mode === 'csrf') req.headers.delete('x-csrf-token');
    if (mode === 'idem') req.headers.delete('idempotency-key');
    if (mode === 'short') req.headers.set('idempotency-key', 'short');
    if (mode === 'long') req.headers.set('idempotency-key', 'x'.repeat(129));
    await noDispatch(h, req, 400); assert.equal(h.calls.some(x => x.url === STS), false);
  }
});
test('never-ending input stream is cancelled at deadline with no STS/backend dispatch', async () => {
  let cancelled = false;
  const body = new ReadableStream({ start() {}, cancel() { cancelled = true; } });
  // Node requires duplex for streaming request construction; make the Request directly.
  const streaming = new Request(c.publicOrigin + '/api/jobs', { method: 'POST', duplex: 'half', body,
    headers: { 'cf-access-jwt-assertion': await token(), origin: c.publicOrigin, 'content-type': 'application/json',
      'x-csrf-token': 'synthetic-csrf', 'idempotency-key': IDEM } });
  const h = harness(null, { timeoutMs: 20 }); await noDispatch(h, streaming, 400);
  assert.equal(cancelled, true); assert.equal(h.calls.some(x => x.url === STS), false);
});
for (const stage of ['certs', 'sts', 'iam']) test(`${stage} rejection sanitized, never reaches backend`, async () => {
  const t = await token(), h = harness(e => (stage === 'certs' && e.url.endsWith('/certs')) ||
    (stage === 'sts' && e.url === STS) || (stage === 'iam' && e.url.includes('iamcredentials')) ?
    new Response(`${t} ${ACCESS} ${ID}`, { status: 403 }) : null);
  const response = await h.invoke(request(t)), text = await response.text();
  assert.equal(response.status, 502); assert.equal(JSON.parse(text).effect, 'NO_DISPATCH');
  assert.equal(backendCalls(h).length, 0); for (const secret of [t, ACCESS, ID]) assert.equal(text.includes(secret), false);
});
test('backend timeout/oversize/invalid/reflected credentials are UNKNOWN with no replay', async () => {
  const t = await token();
  for (const mode of ['timeout', 'size', 'json', 'jwt', 'access', 'id-escaped', 'redirect']) {
    let cancelled = false;
    const h = harness(e => {
      if (!e.url.startsWith(c.cloudRunOrigin)) return null;
      if (mode === 'timeout') return new Response(new ReadableStream({ cancel() { cancelled = true; } }),
        { headers: { 'content-type': 'application/json' } });
      if (mode === 'size') return new Response('x'.repeat(131073), { headers: { 'content-type': 'application/json' } });
      if (mode === 'json') return new Response('not-json', { headers: { 'content-type': 'application/json' } });
      if (mode === 'redirect') return new Response(null, { status: 302, headers: { location: 'https://attacker.invalid' } });
      const secret = mode === 'jwt' ? t : mode === 'access' ? ACCESS : ID;
      const text = JSON.stringify({ leaked: secret });
      return new Response(mode === 'id-escaped' ? text.replaceAll('e', '\\u0065') : text,
        { headers: { 'content-type': 'application/json' } });
    }, { timeoutMs: mode === 'timeout' ? 20 : 1000 });
    const response = await h.invoke(request(t)), text = await response.text();
    assert.equal(response.status, 502, mode); assert.equal(JSON.parse(text).effect, 'UNKNOWN', mode);
    assert.equal(JSON.parse(text).retry, false); assert.equal(backendCalls(h).length, 1);
    if (mode === 'timeout') assert.equal(cancelled, true);
    for (const secret of [t, ACCESS, ID]) assert.equal(text.includes(secret), false);
  }
});
test('reliable backend422 is a sanitized response, not NO_DISPATCH or result proof', async () => {
  const h = harness(e => e.url.startsWith(c.cloudRunOrigin) ? new Response('{"detail":"invalid payload"}',
    { status: 422, headers: { 'content-type': 'application/json' } }) : null);
  const response = await h.invoke(request(await token()));
  assert.equal(response.status, 422); assert.equal((await response.json()).effect, 'RESPONSE_RECEIVED');
  assert.equal(backendCalls(h).length, 1);
});

// Host policy fixtures are generic metadata, not a deployed owner's route configuration.
const route = (method, path, fields = {}) => ({ method, path, bodyRequired: method === 'POST',
  idempotencyRequired: false, maxBytes: method === 'POST' ? 131072 : 0, ...fields });
const searchRoute = () => route('GET', '/api/search', { query: {
  q: { type: 'string', maxLength: 200 }, limit: { type: 'integer', min: 1, max: 100 } } });
test('reviewed host-only routes admit bounded synthetic reads/writes without changing default', async () => {
  const config = { ...c, apiRoutes: [route('GET', '/api/status'), route('GET', '/api/items/{id:ascii64}'),
    route('POST', '/api/submit', { idempotencyRequired: true })] };
  for (const path of ['/api/status', '/api/items/' + 'Z_-'.repeat(21)]) {
    const h = harness(null, {}, config), response = await h.invoke(request(await token(), path, { method: 'GET' }));
    assert.equal(response.status, 200); assert.equal(backendCalls(h)[0].url, c.cloudRunOrigin + path);
  }
  const h = harness(null, {}, config), body = JSON.stringify({ work_id: 'DEUS-SYNTHETIC-002', text: 'x'.repeat(70000) });
  assert.equal((await h.invoke(request(await token(), '/api/submit', { body }))).status, 200);
  assert.equal(backendCalls(h)[0].body, body);
  const defaults = harness(); await noDispatch(defaults, request(await token(), '/api/status', { method: 'GET',
    headers: { 'x-api-routes': JSON.stringify(config.apiRoutes) } }), 404); assert.equal(defaults.calls.length, 0);
  const oversize = harness(null, {}, config);
  await noDispatch(oversize, request(await token(), '/api/submit', { body: JSON.stringify({ text: 'x'.repeat(131072) }) }), 400);
});
test('route descriptors reject callbacks/regex/targets/duplicates/ambiguous IDs and remain closed', async () => {
  const get = route('GET', '/api/status');
  for (const apiRoutes of [[], Array(33).fill(get), [get, get], [ { ...get, match: () => true } ],
    [ { ...get, path: /status/ } ], [ { ...get, path: 'https://attacker.invalid/api/status' } ],
    [ { ...get, path: '/api/*' } ], [ { ...get, path: '/api/items/{id:any}' } ],
    [ { ...get, path: '/api/items/{id:ascii64}/{id:hex32}' } ],
    [route('GET', '/api/items/{id:ascii64}'), route('GET', '/api/items/{id:hex32}')],
    [route('POST', '/api/submit', { bodyRequired: false })],
    [route('POST', '/api/jobs')], [route('POST', '/api/chat')],
    [{ ...get, query: { q: { type: 'string', maxLength: 200, regex: '.*' } } }],
    [{ ...get, query: null }]]) {
    assert.throws(() => createOwnerCloudRunInvoker({ ...c, apiRoutes }), /HOST_CONFIG_INVALID/);
  }
  const h = harness(null, {}, { ...c, apiRoutes: [route('GET', '/api/items/{id:ascii64}')] });
  for (const path of ['/api/items/' + 'a'.repeat(65), '/api/items/a%2Fb', '/api/items/item/cancel', '/api/items/item?q=x']) {
    await noDispatch(h, request(await token(), path, { method: 'GET' }), 404);
  }
  assert.equal(h.calls.length, 0);
});
test('prototype/accessor inputs reject and deep-cloned policy cannot be broadened after construction', async () => {
  assert.throws(() => createOwnerCloudRunInvoker(Object.create(c)), /HOST_CONFIG_INVALID/);
  assert.throws(() => createOwnerCloudRunInvoker({ ...c, apiRoutes: [Object.create(route('GET', '/api/status'))] }), /HOST_CONFIG_INVALID/);
  let accessed = false; const accessor = { ...c };
  Object.defineProperty(accessor, 'cfAudience', { get() { accessed = true; return c.cfAudience; } });
  assert.throws(() => createOwnerCloudRunInvoker(accessor), /HOST_CONFIG_INVALID/); assert.equal(accessed, false);
  const entries = []; Object.defineProperty(entries, '0', { get() { accessed = true; return route('GET', '/api/status'); } });
  assert.throws(() => createOwnerCloudRunInvoker({ ...c, apiRoutes: entries }), /HOST_CONFIG_INVALID/); assert.equal(accessed, false);
  const config = { ...c, apiRoutes: [searchRoute(), route('GET', '/api/status')] }, h = harness(null, {}, config);
  config.cloudRunOrigin = 'https://attacker.run.app'; config.ownerEmail = 'attacker@example.invalid';
  config.apiRoutes[0].query.q.maxLength = 1024; config.apiRoutes[0].query.limit.max = 1000000000;
  config.apiRoutes[1].path = '/api/control'; config.apiRoutes.push(route('GET', '/api/control'));
  assert.equal((await h.invoke(request(await token(), '/api/status', { method: 'GET' }))).status, 200);
  assert.equal(backendCalls(h)[0].url, c.cloudRunOrigin + '/api/status');
  for (const path of ['/api/control', '/api/search?q=' + 'x'.repeat(201), '/api/search?limit=101']) {
    const count = h.calls.length, response = await h.invoke(request(await token(), path, { method: 'GET' }));
    assert.equal(response.status, 404); assert.equal((await response.json()).effect, 'NO_DISPATCH');
    assert.equal(h.calls.length, count);
  }
});
test('all policy POSTs require CSRF; explicit idempotency and verified optional bodies are enforced', async () => {
  const optional = [route('POST', '/api/logout', { bodyRequired: false }),
    route('POST', '/api/jobs/{id:ascii64}/cancel', { bodyRequired: false }),
    route('POST', '/api/resources/{id:ascii64}/revoke', { bodyRequired: false })];
  for (const path of ['/api/logout', '/api/jobs/fixture/cancel', '/api/resources/fixture/revoke']) {
    for (const body of ['', '{"reason":"synthetic"}']) {
      const h = harness(null, {}, { ...c, apiRoutes: optional }), req = request(await token(), path, { body });
      req.headers.delete('idempotency-key'); if (!body) req.headers.delete('content-type');
      assert.equal((await h.invoke(req)).status, 200); assert.equal(backendCalls(h)[0].body, body || undefined);
    }
    const h = harness(null, {}, { ...c, apiRoutes: optional }), req = request(await token(), path, { body: '' });
    req.headers.delete('x-csrf-token'); await noDispatch(h, req, 400); assert.equal(h.calls.some(x => x.url === STS), false);
  }
  for (const field of ['x-csrf-token', 'idempotency-key', 'body']) {
    const h = harness(null, {}, { ...c, apiRoutes: [route('POST', '/api/submit', { idempotencyRequired: true })] });
    const req = request(await token(), '/api/submit', { body: field === 'body' ? '' : '{}' });
    if (field !== 'body') req.headers.delete(field);
    await noDispatch(h, req, 400); assert.equal(h.calls.some(x => x.url === STS), false);
  }
});
test('typed host query whitelist validates bounds/duplicates and preserves original search bytes', async () => {
  const config = { ...c, apiRoutes: [searchRoute()] }, path = '/api/search?q=%CE%B4%20road&limit=40';
  const h = harness(null, {}, config);
  assert.equal((await h.invoke(request(await token(), path, { method: 'GET' }))).status, 200);
  assert.equal(backendCalls(h)[0].url, c.cloudRunOrigin + path);
  for (const query of ['?q=one&q=two', '?q=one&%71=two', '?target=https://attacker.invalid', '?q=%00',
    '?q=%ZZ', '?q=' + 'x'.repeat(201), '?q=' + 'x'.repeat(2049), '?limit=0', '?limit=101', '?limit=01', '?limit=1e2']) {
    const blocked = harness(null, {}, config); await noDispatch(blocked, request(await token(), '/api/search' + query, { method: 'GET' }), 404);
    assert.equal(blocked.calls.length, 0);
  }
});
