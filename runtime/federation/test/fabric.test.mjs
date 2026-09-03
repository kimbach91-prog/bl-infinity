import test from 'node:test';
import assert from 'node:assert/strict';
import { generateKeyPairSync } from 'node:crypto';
import { once } from 'node:events';
import { ProviderRegistry, planRoute, rankCandidates } from '../lib/fabric.mjs';
import { signProviderManifest, verifyProviderManifest } from '../lib/manifest.mjs';
import { MemoryLeaseQueue } from '../lib/queue.mjs';
import { ReplayGuard, signWorkerEnvelope, verifyWorkerEnvelope } from '../lib/protocol.mjs';
import { FederationExecutor } from '../lib/executor.mjs';
import { LocalAdapter } from '../adapters/local.mjs';
import { MemoryAuditLog, verifyAuditChain } from '../lib/audit.mjs';
import { HybridSearchFabric } from '../lib/search.mjs';
import { createWorkerServer } from '../worker/server.mjs';
import { HttpWorkerAdapter } from '../adapters/http-worker.mjs';

function provider(overrides = {}) {
  const base = {
    manifestVersion: 'bl-cf-provider/v1', id: 'node.local.1', kind: 'local', capabilities: ['compute.echo', 'compute.sha256'],
    authorization: { consentRef: 'consent:test:001', grantor: 'owner', grantedAt: '2026-01-01T00:00:00.000Z', expiresAt: '2099-01-01T00:00:00.000Z', allowedDataClasses: ['public', 'internal', 'private'], maxTaskCostUsd: 1 },
    limits: { maxConcurrency: 2, maxCostPerTaskUsd: 1, maxExecutionMs: 5000 },
    telemetry: { trust: 0.9, availability: 0.99, p95LatencyMs: 20, costPerUnitUsd: 0, inFlight: 0 },
    dataPolicy: { privateDataAllowed: true, internalDataAllowed: true, retention: 'none' }, regions: ['local'], dataLocations: ['local'], tags: ['owner']
  };
  return deepMerge(base, overrides);
}
function deepMerge(a, b) { const out = structuredClone(a); for (const [k, v] of Object.entries(b)) { if (v && typeof v === 'object' && !Array.isArray(v) && out[k] && typeof out[k] === 'object' && !Array.isArray(out[k])) out[k] = deepMerge(out[k], v); else out[k] = structuredClone(v); } return out; }

test('routes to best eligible provider and fails private egress closed', () => {
  const slow = provider({ id: 'slow', telemetry: { p95LatencyMs: 500, trust: 0.8 } });
  const fast = provider({ id: 'fast', telemetry: { p95LatencyMs: 15, trust: 0.95 } });
  const registry = new ProviderRegistry([slow, fast]);
  assert.equal(planRoute(registry, { id: 't1', capability: 'compute.echo', dataClass: 'public', dataLocation: 'local' }).selected[0].providerId, 'fast');
  const remote = new ProviderRegistry([provider({ id: 'remote', dataLocations: ['remote'], dataPolicy: { privateDataAllowed: false } })]);
  assert.equal(rankCandidates(remote, { id: 't2', capability: 'compute.echo', dataClass: 'private', dataLocation: 'local' }).length, 0);
});

test('signed provider manifest detects grant mutation but ignores mutable telemetry', () => {
  const { publicKey, privateKey } = generateKeyPairSync('ed25519');
  const pub = publicKey.export({ type: 'spki', format: 'pem' }), priv = privateKey.export({ type: 'pkcs8', format: 'pem' });
  const signed = signProviderManifest(provider(), priv, 'partner-1');
  assert.equal(verifyProviderManifest(signed, { 'partner-1': pub }).ok, true);
  signed.telemetry.p95LatencyMs = 999; assert.equal(verifyProviderManifest(signed, { 'partner-1': pub }).ok, true);
  signed.limits.maxConcurrency = 999; assert.equal(verifyProviderManifest(signed, { 'partner-1': pub }).ok, false);
});

test('queue deduplicates and recovers expired leases', () => {
  const q = new MemoryLeaseQueue({ defaultLeaseMs: 10, maxAttempts: 2 });
  q.enqueue({ id: 'x', capability: 'compute.echo', payload: { x: 1 } }, { now: 100 });
  assert.equal(q.enqueue({ id: 'duplicate', capability: 'compute.echo', payload: { x: 1 } }, { now: 100 }).deduplicated, true);
  q.claim('w1', ['compute.echo'], { now: 100, leaseMs: 10 }); q.sweepExpired(111); assert.equal(q.get('x').state, 'pending');
  const second = q.claim('w2', ['compute.echo'], { now: 112, leaseMs: 10 }); q.fail('x', second.lease.token, new Error('boom'), { now: 113 }); assert.equal(q.get('x').state, 'deadletter');
});

test('worker HMAC rejects replay', () => {
  const secret = 'test-secret', timestamp = 1_000_000, nonce = 'n-1', body = '{"a":1}';
  const headers = { 'x-bl-timestamp': String(timestamp), 'x-bl-nonce': nonce, 'x-bl-signature': signWorkerEnvelope(secret, { timestamp, nonce, body }) };
  const guard = new ReplayGuard(); assert.equal(verifyWorkerEnvelope(secret, headers, body, { now: timestamp, replayGuard: guard }).ok, true); assert.equal(verifyWorkerEnvelope(secret, headers, body, { now: timestamp, replayGuard: guard }).reason, 'replay');
});

test('executor falls back and preserves audit provenance', async () => {
  const registry = new ProviderRegistry([provider({ id: 'p1', kind: 'bad', telemetry: { trust: 0.99, p95LatencyMs: 1 } }), provider({ id: 'p2', kind: 'local' })]);
  const audit = new MemoryAuditLog();
  const executor = new FederationExecutor({ registry, audit, adapters: { bad: { execute: async () => { throw new Error('planned failure'); } }, local: new LocalAdapter({ 'compute.echo': async (payload) => payload }) } });
  const out = await executor.execute({ id: 't', capability: 'compute.echo', payload: { ok: 1 }, dataClass: 'public' });
  assert.equal(out.providerId, 'p2'); assert.equal(out.attempts.length, 2); assert.equal(verifyAuditChain(audit.list()).ok, true);
});

test('hybrid search combines lexical semantic and graph signals', () => {
  const s = new HybridSearchFabric();
  s.addDocument({ id: 'a', title: 'Taxi Hải Phòng', text: 'taxi tiện chuyến hà nội hải phòng', trust: 0.9, relations: [{ target: 'b', weight: 0.8 }] });
  s.addDocument({ id: 'b', title: 'Driver network', text: 'mạng lưới tài xế đường dài', trust: 0.8 });
  s.addDocument({ id: 'c', title: 'Cooking', text: 'công thức nấu ăn', trust: 0.9 });
  const hits = s.search('taxi tiện chuyến hải phòng', { seedIds: ['a'] }); assert.equal(hits[0].id, 'a'); assert.ok(hits.find((x) => x.id === 'b').explain.graph > 0);
});

test('signed HTTP worker executes only installed capability end-to-end', async (t) => {
  const secret = 'worker-secret', server = createWorkerServer({ sharedSecret: secret, requireAuth: true, maxConcurrency: 1 });
  server.listen(0, '127.0.0.1'); await once(server, 'listening'); t.after(() => server.close());
  const address = server.address();
  const p = provider({ id: 'http1', kind: 'http-worker', endpoint: `http://127.0.0.1:${address.port}`, transport: { auth: 'hmac-env', secretEnv: 'TEST_WORKER_SECRET' }, capabilities: ['compute.sha256'] });
  const result = await new HttpWorkerAdapter({ env: { TEST_WORKER_SECRET: secret } }).execute(p, { id: 't', capability: 'compute.sha256', payload: 'abc', dataClass: 'public' });
  assert.equal(result.sha256, 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
});
