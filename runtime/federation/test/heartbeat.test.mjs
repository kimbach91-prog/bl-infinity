import test from 'node:test';
import assert from 'node:assert/strict';
import { createProviderHeartbeatClient, createProviderHeartbeatClientFromEnv } from '../worker/heartbeat.mjs';
import { signProviderHeartbeat } from '../lib/provider-heartbeat.mjs';
import { validateProviderGrant } from '../lib/manifest.mjs';

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, text: async () => JSON.stringify(body) };
}

test('worker heartbeat client signs provider, timestamp, nonce and exact body', async () => {
  const secret = 'scoped-heartbeat-secret';
  let calls = 0;
  const client = createProviderHeartbeatClient({
    providerId: 'worker-a',
    heartbeatUrl: 'https://control.example.test/providers/heartbeat/self',
    secret,
    getInFlight: () => 3,
    fetchImpl: async (url, options) => {
      calls += 1;
      assert.equal(url, 'https://control.example.test/providers/heartbeat/self');
      const providerId = options.headers['x-bl-provider-id'];
      const timestamp = Number(options.headers['x-bl-timestamp']);
      const nonce = options.headers['x-bl-nonce'];
      const signature = options.headers['x-bl-heartbeat-signature'];
      assert.equal(providerId, 'worker-a');
      assert.deepEqual(JSON.parse(options.body), { providerId: 'worker-a', inFlight: 3 });
      assert.equal(signature, signProviderHeartbeat(secret, { providerId, timestamp, nonce, body: options.body }));
      return response(200, { ok: true, heartbeatSeq: 1 });
    },
  });
  const result = await client.beat({ now: 1234567890 });
  assert.equal(calls, 1);
  assert.equal(result.ok, true);
});

test('worker heartbeat client rejects plaintext remote coordinator URL', () => {
  assert.throws(() => createProviderHeartbeatClient({
    providerId: 'worker-a',
    heartbeatUrl: 'http://example.com/providers/heartbeat/self',
    secret: 'secret',
  }), /HTTPS/);
  assert.doesNotThrow(() => createProviderHeartbeatClient({
    providerId: 'worker-a',
    heartbeatUrl: 'http://127.0.0.1:8787/providers/heartbeat/self',
    secret: 'secret',
  }));
});

test('worker heartbeat env configuration is all-or-nothing and uses an indirect secret name', () => {
  assert.equal(createProviderHeartbeatClientFromEnv({ env: {} }), null);
  assert.throws(() => createProviderHeartbeatClientFromEnv({ env: { BL_PROVIDER_ID: 'worker-a' } }), /must be set together/);
  assert.throws(() => createProviderHeartbeatClientFromEnv({ env: {
    BL_PROVIDER_ID: 'worker-a',
    BL_HEARTBEAT_URL: 'https://control.example.test/providers/heartbeat/self',
    BL_HEARTBEAT_SECRET_ENV: 'WORKER_A_HEARTBEAT_SECRET',
  } }), /environment variable is missing/);
  assert.doesNotThrow(() => createProviderHeartbeatClientFromEnv({ env: {
    BL_PROVIDER_ID: 'worker-a',
    BL_HEARTBEAT_URL: 'https://control.example.test/providers/heartbeat/self',
    BL_HEARTBEAT_SECRET_ENV: 'WORKER_A_HEARTBEAT_SECRET',
    WORKER_A_HEARTBEAT_SECRET: 'secret',
  }, fetchImpl: async () => response(200, { ok: true }) }));
});

test('signed heartbeat auth reference validates as authority metadata without containing the secret', () => {
  const manifest = {
    manifestVersion: 'bl-cf-provider/v1',
    id: 'worker-a',
    kind: 'http-worker',
    endpoint: 'https://worker.example.test',
    capabilities: ['compute.echo'],
    authorization: { consentRef: 'grant:worker-a', grantor: 'owner', grantedAt: '2026-01-01T00:00:00.000Z', expiresAt: '2099-01-01T00:00:00.000Z', allowedDataClasses: ['public'] },
    limits: { maxConcurrency: 1 },
    liveness: { heartbeatRequired: true, heartbeatTtlMs: 60_000, heartbeatAuth: { mode: 'hmac-env', secretEnv: 'WORKER_A_HEARTBEAT_SECRET' } },
  };
  assert.equal(validateProviderGrant(manifest, Date.parse('2026-09-04T00:00:00Z')), true);
  assert.throws(() => validateProviderGrant({ ...manifest, liveness: { ...manifest.liveness, heartbeatAuth: { mode: 'hmac-env', secretEnv: 'bad-name' } } }, Date.parse('2026-09-04T00:00:00Z')), /environment variable name/);
});
