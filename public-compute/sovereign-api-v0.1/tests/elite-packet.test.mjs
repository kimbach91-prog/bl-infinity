import test from 'node:test';
import assert from 'node:assert/strict';
import {
  compileExternalProjection,
  makeEliteReceipt,
  qualifyElitePacket,
  validateElitePacket
} from '../src/elite-packet.mjs';

function basePacket(overrides = {}) {
  return {
    version: 'DEUS-ELITE-PACKET/0.1',
    packet_id: 'pkt-001',
    type: 'REQUEST_PACKET',
    source_member_id: 'partner-a',
    target_member_id: 'deus',
    task_id: 'task-001',
    purpose: 'Exchange bounded research value',
    intent: 'Test one source-backed hypothesis and return an evidence packet',
    data_class: 'S0',
    auth_ref: 'cap:partner-a:research',
    idempotency_key: 'idem-001',
    created_at: '2026-09-20T00:00:00Z',
    expires_at: '2099-09-20T00:00:00Z',
    source_refs: ['src:public:001'],
    claims: [{ id: 'c1', text: 'A bounded public claim' }],
    exchange: { mode: 'RESULT_SWAP', offer: 'verified delta', request: 'counterevidence' },
    constraints: { max_cost: 'bounded', no_raw_private_data: true },
    ...overrides
  };
}

const goodMetrics = {
  relevance: 0.9,
  expected_information_gain: 0.8,
  reciprocity: 0.8,
  evidence_quality: 0.8,
  redundancy: 0.1,
  privacy_risk: 0.1,
  expected_value_gain: 0.8,
  marginal_cost: 0.2
};

test('accepts a high-value S0 packet', () => {
  const d = qualifyElitePacket(basePacket(), { router_metrics: goodMetrics });
  assert.equal(d.state, 'ACCEPT');
  assert.equal(d.code, 'ELITE_PACKET_ACCEPTED');
  assert.equal(d.canonical_write, false);
});

test('holds packet missing auth_ref', () => {
  const packet = basePacket({ auth_ref: '' });
  const d = qualifyElitePacket(packet, { router_metrics: goodMetrics });
  assert.equal(d.state, 'HOLD');
  assert.match(d.reasons.join(','), /missing:auth_ref/);
});

test('holds sealed S2 packet on ordinary external route', () => {
  const d = qualifyElitePacket(basePacket({ data_class: 'S2' }), { router_metrics: goodMetrics });
  assert.equal(d.state, 'HOLD');
  assert.equal(d.code, 'SEALED_ROUTE_REQUIRED');
});

test('holds expired packet', () => {
  const packet = basePacket({ expires_at: '2020-01-01T00:00:00Z' });
  const d = validateElitePacket(packet, { now: new Date('2026-09-20T00:00:00Z') });
  assert.equal(d.state, 'HOLD');
  assert.equal(d.code, 'STALE_PACKET');
});

test('rejects duplicate/replay noise', () => {
  const packet = basePacket();
  const d = qualifyElitePacket(packet, {
    router_metrics: goodMetrics,
    seen_idempotency_keys: new Set(['idem-001'])
  });
  assert.equal(d.state, 'REJECT');
  assert.equal(d.code, 'DUPLICATE_OR_REPLAY_NOISE');
});

test('rejects low-value redundant packet', () => {
  const d = qualifyElitePacket(basePacket(), {
    router_metrics: {
      ...goodMetrics,
      relevance: 0.3,
      expected_information_gain: 0.1,
      reciprocity: 0.2,
      redundancy: 0.9,
      expected_value_gain: 0.2,
      marginal_cost: 0.4
    }
  });
  assert.equal(d.state, 'REJECT');
  assert.equal(d.code, 'ELITE_GATE_FAIL');
  assert.ok(d.reasons.includes('low_relevance'));
  assert.ok(d.reasons.includes('high_redundancy'));
  assert.ok(d.reasons.includes('non_positive_marginal_value'));
});

test('projection strips secret/private fields', () => {
  const packet = basePacket({
    api_key: 'should-never-leave',
    private_context: { raw_memory: 'secret', ok: 'not exported because parent is forbidden' },
    offer: { safe: true, token: 'secret-token', note: 'useful' }
  });
  const projection = compileExternalProjection(packet);
  const serialized = JSON.stringify(projection);
  assert.doesNotMatch(serialized, /should-never-leave|secret-token|raw_memory/);
  assert.equal(projection.offer.safe, true);
  assert.equal(projection.offer.note, 'useful');
  assert.equal(projection.membrane.raw_secret_exported, false);
});

test('claims require source refs', () => {
  const d = validateElitePacket(basePacket({ source_refs: [] }));
  assert.equal(d.state, 'HOLD');
  assert.ok(d.reasons.includes('claims_without_source_refs'));
});

test('trusted router metrics are required before expensive routing', () => {
  const d = qualifyElitePacket(basePacket());
  assert.equal(d.state, 'HOLD');
  assert.equal(d.code, 'NEEDS_TRUSTED_ROUTER_SCORE');
});

test('receipt never records raw secrets', () => {
  const packet = basePacket({ credential: 'raw-secret' });
  const decision = qualifyElitePacket(packet, { router_metrics: goodMetrics });
  const receipt = makeEliteReceipt({
    packet,
    decision,
    observed: { token: 'nope', latency_ms: 10 }
  });
  const serialized = JSON.stringify(receipt);
  assert.doesNotMatch(serialized, /raw-secret|nope/);
  assert.equal(receipt.observed.latency_ms, 10);
  assert.equal(receipt.secret_material_recorded, false);
});
