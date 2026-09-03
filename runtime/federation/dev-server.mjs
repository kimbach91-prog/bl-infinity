import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { createFederationRuntime } from './lib/runtime.mjs';
import { planRoute } from './lib/fabric.mjs';
import { HybridSearchFabric } from './lib/search.mjs';
import { safeDefaultHandlers } from './worker/handlers.mjs';
import { validateProviderGrant, verifyProviderManifest } from './lib/manifest.mjs';
import { TokenBucketLimiter } from './lib/rate-limit.mjs';
import { hasControlAccess } from './lib/control-auth.mjs';

const port = Number(process.env.PORT || 8787);
const host = process.env.HOST || '127.0.0.1';
const maxBodyBytes = Number(process.env.BL_CONTROL_MAX_BODY_BYTES || 1_048_576);
const controlToken = process.env.BL_CONTROL_TOKEN || null;
const requireSignedManifests = process.env.BL_REQUIRE_SIGNED_MANIFESTS === 'true';
const trustStore = parseJsonEnv('BL_TRUST_STORE_JSON', {});
const providers = await loadProviders();
const manifestVerifier = requireSignedManifests ? (manifest) => verifyProviderManifest(manifest, trustStore, { requireSignature: true }) : null;
const budgetConfig = parseJsonEnv('BL_BUDGET_JSON', {});
const runtime = createFederationRuntime({ providers, localHandlers: safeDefaultHandlers, manifestVerifier, budgetConfig });
const search = new HybridSearchFabric();
const limiter = new TokenBucketLimiter({ capacity: Number(process.env.BL_RATE_LIMIT_BURST || 120), refillPerSecond: Number(process.env.BL_RATE_LIMIT_PER_SECOND || 2) });

const server = http.createServer(async (req, res) => {
  setCommonHeaders(res);
  const rate = limiter.take(req.socket.remoteAddress || 'unknown');
  if (!rate.ok) { res.setHeader('retry-after', String(Math.max(1, Math.ceil(rate.retryAfterMs / 1000)))); return send(res, 429, { error: 'rate limit exceeded' }); }
  try {
    if (req.method === 'GET' && req.url === '/health') return send(res, 200, { ok: true, service: 'bl-compute-federation', version: '0.3.0', providers: runtime.registry.list().length, search: search.stats(), signedManifestsRequired: requireSignedManifests });
    if (req.method === 'GET' && req.url === '/providers') { if (!authorizedIfConfigured(req)) return send(res, 401, { error: 'unauthorized' }); return send(res, 200, { providers: runtime.registry.list().map(sanitizeProvider) }); }
    if (req.method === 'POST' && req.url === '/route') { if (!authorizedIfConfigured(req)) return send(res, 401, { error: 'unauthorized' }); return send(res, 200, planRoute(runtime.registry, await readJson(req, maxBodyBytes))); }
    if (req.method === 'POST' && req.url === '/tasks/submit') { if (!requireControl(req)) return send(res, 401, { error: 'BL_CONTROL_TOKEN is required for task submission' }); const body = await readJson(req, maxBodyBytes); const task = body.task ?? body; const options = body.options ?? {}; return send(res, 202, await runtime.orchestrator.submit(task, options)); }
    if (req.method === 'POST' && req.url === '/orchestrate/run-once') { if (!requireControl(req)) return send(res, 401, { error: 'BL_CONTROL_TOKEN is required for orchestration' }); const body = await readJson(req, maxBodyBytes); return send(res, 200, await runtime.orchestrator.runOnce(body)); }
    if (req.method === 'GET' && req.url === '/runtime/status') { if (!requireControl(req)) return send(res, 401, { error: 'BL_CONTROL_TOKEN is required for runtime status' }); return send(res, 200, runtime.orchestrator.status()); }
    if (req.method === 'GET' && req.url === '/ledger') { if (!requireControl(req)) return send(res, 401, { error: 'BL_CONTROL_TOKEN is required for ledger access' }); return send(res, 200, { summary: runtime.orchestrator.ledger.summary() }); }
    if (req.method === 'POST' && req.url === '/execute') { if (!requireControl(req)) return send(res, 401, { error: 'BL_CONTROL_TOKEN is required for execution' }); return send(res, 200, await runtime.executor.execute(await readJson(req, maxBodyBytes))); }
    if (req.method === 'POST' && req.url === '/providers/register') {
      if (!requireControl(req)) return send(res, 401, { error: 'BL_CONTROL_TOKEN is required for provider registration' });
      const manifest = await readJson(req, maxBodyBytes); validateProviderGrant(manifest);
      if (requireSignedManifests) { const verdict = verifyProviderManifest(manifest, trustStore, { requireSignature: true }); if (!verdict.ok) return send(res, 403, { error: 'manifest rejected', reason: verdict.reason }); }
      const registered = runtime.registry.register({ ...manifest, telemetry: manifest.telemetry ?? { trust: 0.5, availability: 0.5, p95LatencyMs: 1000, costPerUnitUsd: 0, inFlight: 0 } });
      await runtime.audit.append('provider.registered', { providerId: registered.id, consentRef: registered.authorization.consentRef });
      return send(res, 201, { provider: sanitizeProvider(registered) });
    }
    if (req.method === 'POST' && req.url === '/search/index') {
      if (!requireControl(req)) return send(res, 401, { error: 'BL_CONTROL_TOKEN is required for indexing' });
      const body = await readJson(req, maxBodyBytes), docs = Array.isArray(body.documents) ? body.documents : [body.document ?? body];
      if (docs.length > 1000) return send(res, 413, { error: 'too many documents in one request' });
      const indexed = docs.map((doc) => search.addDocument(doc)); await runtime.audit.append('search.indexed', { count: indexed.length, ids: indexed.map((x) => x.id) }); return send(res, 201, { indexed: indexed.length, stats: search.stats() });
    }
    if (req.method === 'POST' && req.url === '/search/query') { if (!authorizedIfConfigured(req)) return send(res, 401, { error: 'unauthorized' }); const body = await readJson(req, maxBodyBytes); if (!body.query) return send(res, 400, { error: 'query is required' }); return send(res, 200, { results: search.search(body.query, body.options ?? {}), stats: search.stats() }); }
    if (req.method === 'GET' && req.url === '/audit/head') { if (!requireControl(req)) return send(res, 401, { error: 'BL_CONTROL_TOKEN is required for audit access' }); const records = runtime.audit.list(); return send(res, 200, { records: records.length, head: records.at(-1)?.hash ?? null }); }
    return send(res, 404, { error: 'not found' });
  } catch (error) { return send(res, error.code === 'BODY_TOO_LARGE' ? 413 : 400, { error: error.message }); }
});

server.listen(port, host, () => { console.log(`BL federation control plane listening on http://${host}:${port}`); if (!controlToken) console.warn('BL_CONTROL_TOKEN is not set: execution and mutation endpoints remain disabled.'); });

async function loadProviders() { if (process.env.BL_PROVIDERS_JSON) { const parsed = JSON.parse(process.env.BL_PROVIDERS_JSON); if (!Array.isArray(parsed)) throw new Error('BL_PROVIDERS_JSON must be an array'); return parsed; } const file = process.env.BL_PROVIDER_FILE || new URL('./config/providers.example.json', import.meta.url); return JSON.parse(await readFile(file, 'utf8')); }
function parseJsonEnv(name, fallback) { return process.env[name] ? JSON.parse(process.env[name]) : fallback; }
function authorizedIfConfigured(req) { return controlToken ? hasControlAccess(req, controlToken) : true; }
function requireControl(req) { return hasControlAccess(req, controlToken); }
async function readJson(req, maxBytes) { let size = 0; const chunks = []; for await (const chunk of req) { size += chunk.length; if (size > maxBytes) { const e = new Error('request body too large'); e.code = 'BODY_TOO_LARGE'; throw e; } chunks.push(chunk); } return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}'); }
function sanitizeProvider(provider) { const p = structuredClone(provider); if (p.transport) { delete p.transport.secret; delete p.transport.token; } if (p.signature) p.signature = { algorithm: p.signature.algorithm, keyId: p.signature.keyId, present: true }; return p; }
function setCommonHeaders(res) { res.setHeader('content-type', 'application/json; charset=utf-8'); res.setHeader('cache-control', 'no-store'); res.setHeader('x-content-type-options', 'nosniff'); }
function send(res, status, body) { res.statusCode = status; res.end(JSON.stringify(body)); }
