import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { createFederationRuntime } from './lib/runtime.mjs';
import { planRoute } from './lib/fabric.mjs';
import { HybridSearchFabric } from './lib/search.mjs';
import { safeDefaultHandlers } from './worker/handlers.mjs';
import { validateProviderGrant, verifyProviderManifest } from './lib/manifest.mjs';
import { PostgresProviderStore, syncProviderRegistry } from './lib/provider-store.mjs';
import { PostgresProviderDeltaView, ProviderRegistrySynchronizer } from './lib/registry-sync.mjs';
import { verifyProviderHeartbeat } from './lib/provider-heartbeat.mjs';
import { TokenBucketLimiter, PostgresTokenBucketLimiter, classifyRateLimitRoute, rateLimitScopeKey } from './lib/rate-limit.mjs';
import { ControlAuthenticator, bindTaskToPrincipalTenant, parseControlPrincipals, parsePublicReadScopes } from './lib/control-auth.mjs';
import { createSqliteFederationState } from './lib/sqlite-state.mjs';
import { openPostgresFederationState } from './lib/postgres-state.mjs';
import { assertPostgresSchema, assertProviderDeltaSchema } from './lib/postgres-readiness.mjs';

const port = Number(process.env.PORT || 8787);
const host = process.env.HOST || '127.0.0.1';
const maxBodyBytes = Number(process.env.BL_CONTROL_MAX_BODY_BYTES || 1_048_576);
const controlToken = process.env.BL_CONTROL_TOKEN || null;
const controlPrincipals = parseControlPrincipals(process.env.BL_CONTROL_PRINCIPALS_JSON || null);
const controlAuth = new ControlAuthenticator({ legacyToken: controlToken, principals: controlPrincipals });
const publicReadScopes = parsePublicReadScopes(process.env.BL_PUBLIC_READ_SCOPES || '');
const requireSignedManifests = process.env.BL_REQUIRE_SIGNED_MANIFESTS === 'true';
const trustStore = parseJsonEnv('BL_TRUST_STORE_JSON', {});
const bootstrapProviders = await loadProviders();
const manifestVerifier = requireSignedManifests ? (manifest) => verifyProviderManifest(manifest, trustStore, { requireSignature: true }) : null;
const budgetConfig = parseJsonEnv('BL_BUDGET_JSON', {});
const { state: durableState, backend: stateBackend, allowedDataClasses: allowedStateDataClasses } = await loadDurableState(budgetConfig);
const runtime = createFederationRuntime({ providers: bootstrapProviders, localHandlers: safeDefaultHandlers, manifestVerifier, budgetConfig, state: durableState, allowedStateDataClasses });
const providerStore = stateBackend === 'postgres' ? new PostgresProviderStore(durableState.pool, { manifestVerifier }) : null;
const providerSyncMode = providerStore ? parseProviderSyncMode(process.env.BL_PROVIDER_SYNC_MODE || 'delta') : 'memory';
let providerSynchronizer = null;
if (providerStore) {
  for (const provider of runtime.registry.list()) await providerStore.put(provider, { source: 'bootstrap', seedTelemetry: true });
  if (providerSyncMode === 'delta') {
    await assertProviderDeltaSchema(durableState.pool);
    const batchSize = positiveEnvInt('BL_PROVIDER_SYNC_BATCH_SIZE', 500, 5000);
    const maxBatchesPerSync = positiveEnvInt('BL_PROVIDER_SYNC_MAX_BATCHES', 20, 1000);
    providerSynchronizer = new ProviderRegistrySynchronizer(
      runtime.registry,
      new PostgresProviderDeltaView(providerStore, { batchSize }),
      { batchSize, maxBatchesPerSync },
    );
    await providerSynchronizer.bootstrap();
  } else {
    await syncProviderRegistry(runtime.registry, providerStore);
  }
}
const search = new HybridSearchFabric();
const rateCapacity = positiveEnvNumber('BL_RATE_LIMIT_BURST', 120);
const rateRefill = positiveEnvNumber('BL_RATE_LIMIT_PER_SECOND', 2);
const rateLimitMode = parseRateLimitMode(process.env.BL_RATE_LIMIT_MODE || (stateBackend === 'postgres' ? 'shared' : 'memory'));
if (rateLimitMode === 'shared' && stateBackend !== 'postgres') throw new Error('BL_RATE_LIMIT_MODE=shared requires PostgreSQL state');
const limiter = rateLimitMode === 'shared'
  ? new PostgresTokenBucketLimiter(durableState.pool, {
      capacity: rateCapacity,
      refillPerSecond: rateRefill,
      cleanupEvery: positiveEnvInt('BL_RATE_LIMIT_CLEANUP_EVERY', 1000, 1_000_000),
      idleTtlMs: optionalPositiveEnvInt('BL_RATE_LIMIT_IDLE_TTL_MS'),
    })
  : new TokenBucketLimiter({ capacity: rateCapacity, refillPerSecond: rateRefill });
const rateLimitBackend = rateLimitMode === 'shared' ? 'postgres' : 'memory';
const heartbeatPreAuthLimiter = new TokenBucketLimiter({
  capacity: positiveEnvNumber('BL_HEARTBEAT_PREAUTH_BURST', 60),
  refillPerSecond: positiveEnvNumber('BL_HEARTBEAT_PREAUTH_PER_SECOND', 1),
});

const server = http.createServer(async (req, res) => {
  setCommonHeaders(res);
  try {
    const selfHeartbeat = req.method === 'POST' && req.url === '/providers/heartbeat/self';
    const rate = selfHeartbeat
      ? heartbeatPreAuthLimiter.take(req.socket.remoteAddress || 'unknown')
      : await takeRequestRate(req);
    if (!rate.ok) return sendRateLimited(res, rate);

    if (req.method === 'GET' && req.url === '/health') return send(res, 200, {
      ok: true,
      service: 'bl-compute-federation',
      version: '0.9.0',
      stateBackend,
      rateLimitBackend,
      rateLimitMode,
      controlAuthConfigured: controlAuth.configured,
      scopedControlPrincipals: controlPrincipals.length,
      publicReadScopes: [...publicReadScopes].sort(),
      sharedProviderRegistry: Boolean(providerStore),
      providerSyncMode,
      providerSync: providerSynchronizer?.status?.() ?? null,
      directWorkerHeartbeat: Boolean(providerStore),
      stateAllowedDataClasses: allowedStateDataClasses,
      providers: runtime.registry.list().length,
      search: search.stats(),
      signedManifestsRequired: requireSignedManifests,
    });

    if (req.method === 'GET' && req.url === '/providers') {
      const access = authorizeRead(req, res, 'provider:read'); if (!access) return;
      const providerSync = await refreshSharedProviders({ failOnBacklog: false });
      return send(res, 200, { providers: runtime.registry.list().map(sanitizeProvider), providerSync });
    }

    if (req.method === 'POST' && req.url === '/route') {
      const access = authorizeRead(req, res, 'route:read'); if (!access) return;
      await refreshSharedProviders();
      return send(res, 200, planRoute(runtime.registry, await readJson(req, maxBodyBytes)));
    }

    if (req.method === 'POST' && req.url === '/tasks/submit') {
      const access = authorizeRequired(req, res, 'task:submit'); if (!access) return;
      const body = await readJson(req, maxBodyBytes);
      const task = bindTaskToPrincipalTenant(body.task ?? body, access.principal);
      const options = body.options ?? {};
      const submitted = await runtime.orchestrator.submit(task, options);
      await runtime.audit.append('control.task-submitted', { taskId: task.id, tenantId: task.tenantId ?? 'default', actor: access.principal.id });
      return send(res, 202, submitted);
    }

    if (req.method === 'POST' && req.url === '/orchestrate/run-once') {
      const access = authorizeRequired(req, res, 'runtime:operate'); if (!access) return;
      await refreshSharedProviders();
      const body = await readJson(req, maxBodyBytes);
      const result = await runtime.orchestrator.runOnce(body);
      await persistExecutionTelemetry(result?.execution ?? null);
      return send(res, 200, result);
    }

    if (req.method === 'GET' && req.url === '/runtime/status') {
      const access = authorizeRequired(req, res, 'runtime:read'); if (!access) return;
      const providerSync = await refreshSharedProviders({ failOnBacklog: false });
      const rateLimit = typeof limiter.stats === 'function' ? await limiter.stats() : { backend: 'memory' };
      return send(res, 200, { ...(await runtime.orchestrator.status()), providerSyncMode, providerSync, providerSynchronizer: providerSynchronizer?.status?.() ?? null, rateLimitBackend, rateLimitMode, rateLimit });
    }

    if (req.method === 'GET' && req.url === '/ledger') {
      const access = authorizeRequired(req, res, 'ledger:read'); if (!access) return;
      return send(res, 200, { summary: await runtime.orchestrator.ledger.summary() });
    }

    if (req.method === 'POST' && req.url === '/execute') {
      const access = authorizeRequired(req, res, 'runtime:execute'); if (!access) return;
      await refreshSharedProviders();
      const task = await readJson(req, maxBodyBytes);
      const result = await runtime.executor.execute(task);
      await persistExecutionTelemetry(result);
      await runtime.audit.append('control.direct-execute', { taskId: task.id, actor: access.principal.id, providerId: result.providerId });
      return send(res, 200, result);
    }

    if (req.method === 'POST' && req.url === '/providers/register') {
      const access = authorizeRequired(req, res, 'provider:admin'); if (!access) return;
      const manifest = await readJson(req, maxBodyBytes); validateProviderGrant(manifest);
      if (requireSignedManifests) { const verdict = verifyProviderManifest(manifest, trustStore, { requireSignature: true }); if (!verdict.ok) return send(res, 403, { error: 'manifest rejected', reason: verdict.reason }); }
      const candidate = providerStore ? await providerStore.put(manifest, { source: 'operator', seedTelemetry: false }) : { ...structuredClone(manifest), telemetry: neutralTelemetry() };
      const registered = runtime.registry.register(candidate);
      await runtime.audit.append('provider.registered', { providerId: registered.id, consentRef: registered.authorization.consentRef, shared: Boolean(providerStore), actor: access.principal.id });
      return send(res, 201, { provider: sanitizeProvider(registered) });
    }

    if (req.method === 'POST' && req.url === '/providers/replace') {
      const access = authorizeRequired(req, res, 'provider:admin'); if (!access) return;
      if (!providerStore) return send(res, 409, { error: 'shared provider store is unavailable' });
      const manifest = await readJson(req, maxBodyBytes); validateProviderGrant(manifest);
      if (requireSignedManifests) { const verdict = verifyProviderManifest(manifest, trustStore, { requireSignature: true }); if (!verdict.ok) return send(res, 403, { error: 'manifest rejected', reason: verdict.reason }); }
      const stored = await providerStore.put(manifest, { replace: true, source: 'operator-regrant', seedTelemetry: false });
      if (stored.status === 'active') runtime.registry.register(stored); else if (runtime.registry.get(stored.id)) runtime.registry.disable(stored.id);
      await runtime.audit.append('provider.replaced', { providerId: stored.id, consentRef: stored.authorization.consentRef, revision: stored.runtime.revision, actor: access.principal.id });
      return send(res, 200, { provider: sanitizeProvider(stored) });
    }

    if (req.method === 'POST' && req.url === '/providers/revoke') {
      const access = authorizeRequired(req, res, 'provider:admin'); if (!access) return;
      const body = await readJson(req, maxBodyBytes); if (!body.providerId) return send(res, 400, { error: 'providerId is required' });
      let revoked;
      if (providerStore) revoked = await providerStore.revoke(body.providerId, body.reason ?? 'operator-revoked');
      else { if (!runtime.registry.get(body.providerId)) return send(res, 404, { error: 'unknown provider' }); runtime.registry.disable(body.providerId); revoked = runtime.registry.get(body.providerId); }
      if (runtime.registry.get(body.providerId)) runtime.registry.disable(body.providerId);
      await runtime.audit.append('provider.revoked', { providerId: body.providerId, reason: body.reason ?? 'operator-revoked', shared: Boolean(providerStore), actor: access.principal.id });
      return send(res, 200, { provider: sanitizeProvider(revoked) });
    }

    if (req.method === 'POST' && req.url === '/providers/status') {
      const access = authorizeRequired(req, res, 'provider:admin'); if (!access) return;
      if (!providerStore) return send(res, 409, { error: 'shared provider store is unavailable' });
      const body = await readJson(req, maxBodyBytes); if (!body.providerId || !body.status) return send(res, 400, { error: 'providerId and status are required' });
      const stored = await providerStore.setStatus(body.providerId, body.status);
      await refreshSharedProviders({ failOnBacklog: false });
      await runtime.audit.append('provider.status-changed', { providerId: body.providerId, status: body.status, actor: access.principal.id });
      return send(res, 200, { provider: sanitizeProvider(stored) });
    }

    if (req.method === 'POST' && req.url === '/providers/heartbeat/self') {
      if (!providerStore) return send(res, 409, { error: 'shared provider store is required for worker self-heartbeat' });
      const raw = await readBody(req, Math.min(maxBodyBytes, 4096));
      let body; try { body = JSON.parse(raw || '{}'); } catch { return send(res, 400, { error: 'invalid JSON' }); }
      const headerProviderId = header(req.headers, 'x-bl-provider-id');
      if (!body.providerId || body.providerId !== headerProviderId) return send(res, 400, { error: 'providerId must match x-bl-provider-id' });
      const verdict = await verifyProviderHeartbeat(providerStore, req.headers, raw);
      if (!verdict.ok) return send(res, verdict.reason === 'heartbeat-secret-not-configured' ? 503 : 401, { error: 'heartbeat authentication failed', reason: verdict.reason });
      const sharedRate = await takeSharedProviderHeartbeatRate(verdict.providerId);
      if (!sharedRate.ok) return sendRateLimited(res, sharedRate);
      const stored = await providerStore.heartbeat(verdict.providerId, { inFlight: body.inFlight });
      await refreshSharedProviders({ failOnBacklog: false });
      await runtime.audit.append('provider.self-heartbeat', { providerId: verdict.providerId, heartbeatSeq: stored.runtime.heartbeatSeq });
      return send(res, 200, { ok: true, providerId: verdict.providerId, heartbeatSeq: stored.runtime.heartbeatSeq, heartbeatExpiresAt: stored.runtime.heartbeatExpiresAt });
    }

    if (req.method === 'POST' && req.url === '/providers/heartbeat') {
      const access = authorizeRequired(req, res, 'provider:heartbeat'); if (!access) return;
      if (!providerStore) return send(res, 409, { error: 'shared provider store is unavailable' });
      const body = await readJson(req, maxBodyBytes); if (!body.providerId) return send(res, 400, { error: 'providerId is required' });
      const stored = await providerStore.heartbeat(body.providerId, { inFlight: body.inFlight });
      await refreshSharedProviders({ failOnBacklog: false });
      await runtime.audit.append('provider.heartbeat', { providerId: body.providerId, heartbeatSeq: stored.runtime.heartbeatSeq, actor: access.principal.id });
      return send(res, 200, { provider: sanitizeProvider(stored) });
    }

    if (req.method === 'POST' && req.url === '/search/index') {
      const access = authorizeRequired(req, res, 'search:write'); if (!access) return;
      const body = await readJson(req, maxBodyBytes), docs = Array.isArray(body.documents) ? body.documents : [body.document ?? body];
      if (docs.length > 1000) return send(res, 413, { error: 'too many documents in one request' });
      const indexed = docs.map((doc) => search.addDocument(doc));
      await runtime.audit.append('search.indexed', { count: indexed.length, ids: indexed.map((x) => x.id), actor: access.principal.id });
      return send(res, 201, { indexed: indexed.length, stats: search.stats() });
    }

    if (req.method === 'POST' && req.url === '/search/query') {
      const access = authorizeRead(req, res, 'search:read'); if (!access) return;
      const body = await readJson(req, maxBodyBytes); if (!body.query) return send(res, 400, { error: 'query is required' });
      return send(res, 200, { results: search.search(body.query, body.options ?? {}), stats: search.stats() });
    }

    if (req.method === 'GET' && req.url === '/audit/head') {
      const access = authorizeRequired(req, res, 'audit:read'); if (!access) return;
      const records = await runtime.audit.list();
      return send(res, 200, { records: records.length, head: records.at(-1)?.hash ?? null });
    }

    return send(res, 404, { error: 'not found' });
  } catch (error) {
    const status = error.code === 'BODY_TOO_LARGE' ? 413
      : error.code === 'PROVIDER_SYNC_BACKLOG' || error.code === 'RATE_LIMIT_BACKEND_UNAVAILABLE' ? 503
      : error.code === 'TENANT_SCOPE_VIOLATION' ? 403
      : 400;
    return send(res, status, { error: error.message, code: error.code ?? null, providerSync: error.providerSync ?? null });
  }
});

server.listen(port, host, () => {
  console.log(`BL federation control plane listening on http://${host}:${port}`);
  if (!controlAuth.configured && publicReadScopes.size === 0) console.warn('Control auth/public reads are not configured: only health and independently authenticated worker heartbeat remain reachable.');
});
let shuttingDown = false;
for (const signal of ['SIGINT','SIGTERM']) process.once(signal, () => shutdown(signal));

async function takeRequestRate(req) {
  const route = classifyRateLimitRoute(req.method, req.url);
  const principal = controlAuth.authenticate(req);
  const key = rateLimitScopeKey({ principalId: principal?.id ?? null, address: req.socket.remoteAddress || 'unknown', routeGroup: route.group });
  try { return await limiter.take(key, route.cost); }
  catch (error) { const wrapped = new Error(`rate-limit backend unavailable: ${error.message}`); wrapped.code = 'RATE_LIMIT_BACKEND_UNAVAILABLE'; throw wrapped; }
}
async function takeSharedProviderHeartbeatRate(providerId) {
  const key = rateLimitScopeKey({ principalId: `provider:${providerId}`, routeGroup: 'heartbeat-self' });
  try { return await limiter.take(key, 1); }
  catch (error) { const wrapped = new Error(`rate-limit backend unavailable: ${error.message}`); wrapped.code = 'RATE_LIMIT_BACKEND_UNAVAILABLE'; throw wrapped; }
}
function sendRateLimited(res, rate) {
  res.setHeader('retry-after', String(Math.max(1, Math.ceil((rate.retryAfterMs ?? 1000) / 1000))));
  if (rate.remaining != null) res.setHeader('x-ratelimit-remaining', String(rate.remaining));
  return send(res, 429, { error: 'rate limit exceeded', retryAfterMs: rate.retryAfterMs ?? null });
}
function authorizeRequired(req, res, scope) {
  const verdict = controlAuth.authorize(req, scope);
  if (!verdict.ok) { send(res, verdict.status, { error: verdict.reason, requiredScope: scope }); return null; }
  return verdict;
}
function authorizeRead(req, res, scope) {
  if (publicReadScopes.has(scope)) return { ok: true, principal: controlAuth.authenticate(req), public: true };
  return authorizeRequired(req, res, scope);
}
async function refreshSharedProviders({ failOnBacklog = true } = {}) {
  if (!providerStore) return null;
  const result = providerSynchronizer
    ? await providerSynchronizer.sync()
    : await syncProviderRegistry(runtime.registry, providerStore);
  if (failOnBacklog && result?.hasMore === true) {
    const error = new Error('provider registry delta backlog exceeds bounded sync budget');
    error.code = 'PROVIDER_SYNC_BACKLOG';
    error.providerSync = result;
    throw error;
  }
  return result;
}
async function persistExecutionTelemetry(execution) {
  const providerId = execution?.providerId;
  if (!providerStore || !providerId) return;
  const provider = runtime.registry.get(providerId);
  if (!provider) return;
  try { await providerStore.updateMeasuredTelemetry(providerId, provider.telemetry ?? {}); }
  catch (error) { await runtime.audit.append('provider.telemetry-persist-failed', { providerId, error: error.message }); }
}
async function loadDurableState(budget) {
  if (process.env.BL_POSTGRES_URL) {
    const allowedDataClasses = parseAllowedDataClasses(process.env.BL_POSTGRES_ALLOWED_DATA_CLASSES || 'public');
    const autoMigrate = process.env.BL_POSTGRES_AUTO_MIGRATE === 'true';
    const state = await openPostgresFederationState({ connectionString: process.env.BL_POSTGRES_URL, applySchema: autoMigrate, budget, poolOptions: { max: Number(process.env.BL_POSTGRES_POOL_MAX || 10) } });
    if (!autoMigrate) await assertPostgresSchema(state.pool);
    return { state, backend: 'postgres', allowedDataClasses };
  }
  if (process.env.BL_STATE_DB) return { state: createSqliteFederationState(process.env.BL_STATE_DB, { budget }), backend: 'sqlite', allowedDataClasses: null };
  return { state: null, backend: 'memory', allowedDataClasses: null };
}
function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  server.close(async () => {
    try { await durableState?.close?.(); }
    catch (error) { console.error(`state shutdown failed after ${signal}: ${error.message}`); process.exitCode = 1; }
    finally { process.exit(); }
  });
}
async function loadProviders() {
  if (process.env.BL_PROVIDERS_JSON) {
    const parsed = JSON.parse(process.env.BL_PROVIDERS_JSON);
    if (!Array.isArray(parsed)) throw new Error('BL_PROVIDERS_JSON must be an array');
    return parsed;
  }
  const file = process.env.BL_PROVIDER_FILE || new URL('./config/providers.example.json', import.meta.url);
  return JSON.parse(await readFile(file, 'utf8'));
}
function neutralTelemetry() { return { inFlight: 0, trust: 0.5, availability: 0.5, p95LatencyMs: 1000, costPerUnitUsd: 0 }; }
function parseJsonEnv(name, fallback) { return process.env[name] ? JSON.parse(process.env[name]) : fallback; }
function parseAllowedDataClasses(raw) {
  const allowed = new Set(['public','internal','private']);
  const values = [...new Set(String(raw).split(',').map((x) => x.trim()).filter(Boolean))];
  if (!values.length) throw new Error('BL_POSTGRES_ALLOWED_DATA_CLASSES must contain at least one class');
  for (const value of values) if (!allowed.has(value)) throw new Error(`invalid Postgres data class: ${value}`);
  return values;
}
function parseProviderSyncMode(raw) {
  const value = String(raw || '').trim().toLowerCase();
  if (!['delta','full'].includes(value)) throw new Error('BL_PROVIDER_SYNC_MODE must be delta or full');
  return value;
}
function parseRateLimitMode(raw) {
  const value = String(raw || '').trim().toLowerCase();
  if (!['shared','memory'].includes(value)) throw new Error('BL_RATE_LIMIT_MODE must be shared or memory');
  return value;
}
function positiveEnvInt(name, fallback, max) {
  const raw = process.env[name];
  const value = raw == null || raw === '' ? fallback : Number(raw);
  if (!Number.isSafeInteger(value) || value < 1 || value > max) throw new Error(`${name} must be an integer between 1 and ${max}`);
  return value;
}
function optionalPositiveEnvInt(name) {
  const raw = process.env[name];
  if (raw == null || raw === '') return null;
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < 1) throw new Error(`${name} must be a positive integer`);
  return value;
}
function positiveEnvNumber(name, fallback) {
  const raw = process.env[name];
  const value = raw == null || raw === '' ? fallback : Number(raw);
  if (!Number.isFinite(value) || value <= 0) throw new Error(`${name} must be > 0`);
  return value;
}
async function readBody(req, maxBytes) {
  let size = 0; const chunks = [];
  for await (const chunk of req) {
    size += chunk.length;
    if (size > maxBytes) { const e = new Error('request body too large'); e.code = 'BODY_TOO_LARGE'; throw e; }
    chunks.push(chunk);
  }
  return Buffer.concat(chunks).toString('utf8');
}
async function readJson(req, maxBytes) { return JSON.parse((await readBody(req, maxBytes)) || '{}'); }
function header(headers, name) { if (!headers) return null; if (typeof headers.get === 'function') return headers.get(name); return headers[name] ?? headers[name.toLowerCase()] ?? null; }
function sanitizeProvider(provider) {
  const p = structuredClone(provider);
  if (p.transport) { delete p.transport.secret; delete p.transport.token; }
  if (p.signature) p.signature = { algorithm: p.signature.algorithm, keyId: p.signature.keyId, present: true };
  return p;
}
function setCommonHeaders(res) { res.setHeader('content-type', 'application/json; charset=utf-8'); res.setHeader('cache-control', 'no-store'); res.setHeader('x-content-type-options', 'nosniff'); }
function send(res, status, body) { res.statusCode = status; res.end(JSON.stringify(body)); }
