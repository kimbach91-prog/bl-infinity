import test from 'node:test';
import assert from 'node:assert/strict';
import {
  ApiVersionRegistry,
  IdempotencyStore,
  CursorCodec,
  StreamContract,
  makeRequestEnvelope,
  errorEnvelope,
  SDK_MANIFEST_V1,
  assertDeveloperPlatformContract
} from './index.mjs';

test('API same-major compatibility is explicit', () => {
  const r = new ApiVersionRegistry({ minimum_deprecation_days: 90 });
  r.register({
    version: '1.2.0',
    released_at: '2026-09-01T00:00:00Z',
    schema_ref: 'schema://v1.2.0'
  });
  assert.equal(r.compatibility({ client_version: '1.0.0', server_version: '1.2.0' }).compatible, true);
  assert.equal(r.compatibility({ client_version: '1.9.0', server_version: '2.0.0' }).compatible, false);
});

test('deprecation notice cannot be silently shortened', () => {
  const r = new ApiVersionRegistry({ minimum_deprecation_days: 90 });
  r.register({
    version: '1.0.0',
    released_at: '2026-01-01T00:00:00Z',
    schema_ref: 'schema://v1'
  });
  assert.throws(() => r.deprecate({
    version: '1.0.0',
    deprecated_at: '2026-09-01T00:00:00Z',
    sunset_at: '2026-10-01T00:00:00Z'
  }), /DEPRECATION_NOTICE_TOO_SHORT/);

  const d = r.deprecate({
    version: '1.0.0',
    deprecated_at: '2026-09-01T00:00:00Z',
    sunset_at: '2026-12-15T00:00:00Z'
  });
  assert.equal(d.state, 'DEPRECATED');
});

test('idempotent replay returns prior completion without double action', () => {
  const s = new IdempotencyStore();
  const a = s.begin({
    tenant_id: 't1',
    key: 'k1',
    operation: 'jobs.create',
    request_body: { x: 1 }
  });
  assert.equal(a.replay, false);
  s.complete({
    tenant_id: 't1',
    key: 'k1',
    operation: 'jobs.create',
    response_ref: 'job://1',
    result: { job_id: '1' }
  });
  const b = s.begin({
    tenant_id: 't1',
    key: 'k1',
    operation: 'jobs.create',
    request_body: { x: 1 }
  });
  assert.equal(b.replay, true);
  assert.equal(b.state, 'COMPLETED');
  assert.equal(b.response_ref, 'job://1');
});

test('same idempotency key with different body is rejected', () => {
  const s = new IdempotencyStore();
  s.begin({ tenant_id: 't1', key: 'k1', operation: 'x', request_body: { x: 1 } });
  const b = s.begin({ tenant_id: 't1', key: 'k1', operation: 'x', request_body: { x: 2 } });
  assert.equal(b.accepted, false);
  assert.equal(b.reason, 'IDEMPOTENCY_CONFLICT');
});

test('opaque pagination cursor is signed and tenant-bound', () => {
  const c = new CursorCodec({ secret: 'test-secret-long-enough' });
  const cursor = c.encode({ tenant_id: 't1', resource: 'jobs', offset: 100, snapshot_ref: 'snap-1' });
  const p = c.decode(cursor, 't1');
  assert.equal(p.offset, 100);
  assert.throws(() => c.decode(cursor, 't2'), /CURSOR_TENANT_MISMATCH/);
});

test('stream contract requires monotonic event sequence', () => {
  const s = new StreamContract();
  s.emit({ stream_id: 's1', sequence: 1, type: 'started', data: {}, trace_id: 'tr1' });
  s.emit({ stream_id: 's1', sequence: 2, type: 'delta', data: { text: 'a' }, trace_id: 'tr1' });
  assert.throws(() => s.emit({ stream_id: 's1', sequence: 4, type: 'completed', data: {}, trace_id: 'tr1' }), /STREAM_SEQUENCE_GAP/);
});

test('request and error envelopes preserve tenant, trace and version context', () => {
  const r = makeRequestEnvelope({
    tenant_id: 't1',
    principal_id: 'p1',
    api_version: '1.0.0',
    request_id: 'req1',
    trace_id: 'tr1',
    idempotency_key: 'idem1',
    operation: 'jobs.create'
  });
  assert.equal(r.tenant_id, 't1');
  assert.equal(r.trace_id, 'tr1');
  assert.equal(r.api_version, '1.0.0');

  const e = errorEnvelope({
    request_id: 'req1',
    trace_id: 'tr1',
    code: 'RATE_LIMITED',
    message: 'Retry later',
    retryable: true
  });
  assert.equal(e.error.retryable, true);
  assert.equal(e.trace_id, 'tr1');
});

test('SDK manifest covers TS, Python, Go and platform safety features', () => {
  assert.equal(assertDeveloperPlatformContract(), true);
  assert.deepEqual(Object.keys(SDK_MANIFEST_V1.languages).sort(), ['go', 'python', 'typescript']);
  assert.ok(SDK_MANIFEST_V1.required_features.includes('idempotency_keys'));
  assert.ok(SDK_MANIFEST_V1.required_features.includes('version_negotiation'));
});
