import test from 'node:test';
import assert from 'node:assert/strict';
import { ProviderRegistrySynchronizer } from '../lib/registry-sync.mjs';

class FakeRegistry {
  constructor() { this.providers = new Map(); }
  register(provider) { this.providers.set(provider.id, structuredClone(provider)); return this.get(provider.id); }
  get(id) { const p = this.providers.get(id); return p ? structuredClone(p) : null; }
  disable(id) { const p = this.providers.get(id); if (!p) return null; p.status = 'disabled'; return this.get(id); }
  list() { return [...this.providers.values()].map((p) => structuredClone(p)); }
}

class FakeDeltaView {
  constructor(snapshot, deltas = []) { this.initial = snapshot; this.deltas = deltas.slice(); this.calls = 0; }
  async snapshot() { return structuredClone(this.initial); }
  async changesSince(cursor) {
    this.calls += 1;
    const next = this.deltas.shift();
    return next ? structuredClone(next) : { items: [], cursor, hasMore: false };
  }
}

function provider(id, { status = 'active', heartbeatRequired = false, heartbeatExpiresAt = null, expiresAt = '2099-01-01T00:00:00.000Z', trust = 0.5 } = {}) {
  return {
    id,
    status,
    capabilities: ['compute.echo'],
    authorization: { consentRef: `grant:${id}`, expiresAt },
    telemetry: { trust, availability: 1, p95LatencyMs: 10, costPerUnitUsd: 0, inFlight: 0 },
    runtime: { heartbeatRequired, heartbeatExpiresAt },
  };
}

test('registry synchronizer bootstraps once then applies only deltas', async () => {
  const view = new FakeDeltaView({
    items: [
      { provider: provider('a'), changeSeq: 1 },
      { provider: provider('b'), changeSeq: 2 },
    ],
    cursor: 2,
  }, [
    { items: [{ provider: provider('a', { trust: 0.9 }), changeSeq: 3 }], cursor: 3, hasMore: false },
  ]);
  const registry = new FakeRegistry();
  const sync = new ProviderRegistrySynchronizer(registry, view);
  const boot = await sync.bootstrap({ now: 1000 });
  assert.equal(boot.applied, 2);
  assert.equal(sync.cursor, 2);
  assert.equal(registry.list().length, 2);
  const delta = await sync.sync({ now: 2000 });
  assert.equal(delta.applied, 1);
  assert.equal(sync.cursor, 3);
  assert.equal(registry.get('a').telemetry.trust, 0.9);
  assert.equal(registry.get('b').telemetry.trust, 0.5);
  assert.equal(view.calls, 1);
});

test('heartbeat expiry disables locally without any database change', async () => {
  const view = new FakeDeltaView({
    items: [{ provider: provider('hb', { heartbeatRequired: true, heartbeatExpiresAt: new Date(6000).toISOString() }), changeSeq: 5 }],
    cursor: 5,
  }, [
    { items: [], cursor: 5, hasMore: false },
    { items: [{ provider: provider('hb', { heartbeatRequired: true, heartbeatExpiresAt: new Date(14000).toISOString() }), changeSeq: 6 }], cursor: 6, hasMore: false },
  ]);
  const registry = new FakeRegistry();
  const sync = new ProviderRegistrySynchronizer(registry, view);
  await sync.bootstrap({ now: 1000 });
  assert.equal(registry.get('hb').status, 'active');
  const stale = await sync.sync({ now: 7000 });
  assert.equal(stale.expired, 1);
  assert.equal(registry.get('hb').status, 'disabled');
  const revived = await sync.sync({ now: 8000 });
  assert.equal(revived.applied, 1);
  assert.equal(registry.get('hb').status, 'active');
});

test('grant expiry is enforced locally even without a new provider row', async () => {
  const view = new FakeDeltaView({
    items: [{ provider: provider('grant-exp', { expiresAt: new Date(5000).toISOString() }), changeSeq: 9 }],
    cursor: 9,
  });
  const registry = new FakeRegistry();
  const sync = new ProviderRegistrySynchronizer(registry, view);
  await sync.bootstrap({ now: 1000 });
  assert.equal(registry.get('grant-exp').status, 'active');
  await sync.sync({ now: 6000 });
  assert.equal(registry.get('grant-exp').status, 'disabled');
});

test('stale heap events cannot disable a newer provider revision', async () => {
  const view = new FakeDeltaView({
    items: [{ provider: provider('r', { heartbeatRequired: true, heartbeatExpiresAt: new Date(5000).toISOString() }), changeSeq: 10 }],
    cursor: 10,
  }, [
    { items: [{ provider: provider('r', { heartbeatRequired: true, heartbeatExpiresAt: new Date(15000).toISOString() }), changeSeq: 11 }], cursor: 11, hasMore: false },
    { items: [], cursor: 11, hasMore: false },
  ]);
  const registry = new FakeRegistry();
  const sync = new ProviderRegistrySynchronizer(registry, view);
  await sync.bootstrap({ now: 1000 });
  await sync.sync({ now: 2000 });
  await sync.sync({ now: 6000 });
  assert.equal(registry.get('r').status, 'active');
});

test('sync work is bounded by maxBatches under sustained churn', async () => {
  const view = new FakeDeltaView({ items: [], cursor: 0 }, [
    { items: [{ provider: provider('a'), changeSeq: 1 }], cursor: 1, hasMore: true },
    { items: [{ provider: provider('b'), changeSeq: 2 }], cursor: 2, hasMore: true },
    { items: [{ provider: provider('c'), changeSeq: 3 }], cursor: 3, hasMore: false },
  ]);
  const registry = new FakeRegistry();
  const sync = new ProviderRegistrySynchronizer(registry, view, { maxBatchesPerSync: 2 });
  await sync.bootstrap();
  const first = await sync.sync();
  assert.equal(first.batches, 2);
  assert.equal(first.hasMore, true);
  assert.equal(sync.cursor, 2);
  const second = await sync.sync();
  assert.equal(second.hasMore, false);
  assert.equal(sync.cursor, 3);
});
