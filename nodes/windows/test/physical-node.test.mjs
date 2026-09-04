import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { createWorkerServer } from '../../../runtime/federation/worker/server.mjs';
import { createNonce, signWorkerEnvelope } from '../../../runtime/federation/lib/protocol.mjs';

const bootstrap = await readFile(new URL('../bootstrap.ps1', import.meta.url), 'utf8');
const audit = await readFile(new URL('../audit.ps1', import.meta.url), 'utf8');
const rollback = await readFile(new URL('../rollback.ps1', import.meta.url), 'utf8');
const readme = await readFile(new URL('../README.md', import.meta.url), 'utf8');

const SAFE_CAPABILITIES = ['compute.echo', 'compute.sha256', 'json.project', 'text.stats'];

test('bootstrap is loopback-first and never provisions control-plane authority', () => {
  assert.match(bootstrap, /workerHost\s*=\s*'127\.0\.0\.1'/);
  assert.match(bootstrap, /\$env:HOST\s*=\s*'127\.0\.0\.1'/);
  assert.match(bootstrap, /remoteRoutable\s*=\s*\$false/);
  assert.doesNotMatch(bootstrap, /\$env:BL_CONTROL_TOKEN\s*=/);
  assert.doesNotMatch(bootstrap, /0\.0\.0\.0/);
  assert.doesNotMatch(bootstrap, /New-NetFirewallRule[^\r\n]+8790/i);
});

test('bootstrap separates and protects node-scoped credentials', () => {
  assert.match(bootstrap, /execution\.dpapi/);
  assert.match(bootstrap, /heartbeat\.dpapi/);
  assert.match(bootstrap, /DataProtectionScope\]::LocalMachine/);
  assert.match(bootstrap, /secretsEmitted\s*=\s*\$false/);
  assert.match(bootstrap, /controlTokenInstalled\s*=\s*\$false/);
});

test('bootstrap manifest candidate retains the minimal capability set', () => {
  for (const capability of SAFE_CAPABILITIES) assert.match(bootstrap, new RegExp(capability.replace('.', '\\.')));
  assert.match(bootstrap, /REQUIRES_BOUND_SIGNED_PROVIDER_GRANT_BEFORE_REMOTE_ROUTING/);
  assert.match(bootstrap, /restrictedData\s*=\s*'DENY_UNTIL_EXPLICIT_POLICY'/);
});

test('audit checks core physical-node security invariants', () => {
  assert.match(audit, /No-Control-Token-On-Worker/);
  assert.match(audit, /Worker-No-NonLoopback-Listener/);
  assert.match(audit, /Worker-Execution-Requires-Auth/);
  assert.match(audit, /READY_LOCAL_ONLY/);
  assert.match(audit, /remoteAuthorityProven\s*=\s*\$false/);
});

test('rollback is evidence-preserving by default', () => {
  assert.match(rollback, /PurgeNodeData/);
  assert.match(rollback, /rollback-receipt\.json/);
  assert.match(rollback, /security settings restored/);
});

test('documentation explicitly denies implicit remote routability', () => {
  assert.match(readme, /localhost-only/i);
  assert.match(readme, /remote routability/i);
  assert.match(readme, /signed\/revocable provider grant/i);
});

test('BL-CF physical worker denies unauthenticated execution and accepts signed safe capability', async (t) => {
  const secret = 'ci-only-physical-node-secret';
  const server = createWorkerServer({ sharedSecret: secret, maxConcurrency: 1, maxBodyBytes: 262144 });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(0, '127.0.0.1', resolve);
  });
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const address = server.address();
  assert.equal(address.address, '127.0.0.1');
  const base = `http://127.0.0.1:${address.port}`;

  const health = await fetch(`${base}/health`).then((r) => r.json());
  assert.equal(health.ok, true);

  const caps = await fetch(`${base}/v1/capabilities`).then((r) => r.json());
  assert.deepEqual(caps.capabilities, [...SAFE_CAPABILITIES].sort());

  const taskEnvelope = {
    task: {
      id: 'physical-node-ci-task-1',
      idempotencyKey: 'physical-node-ci-idem-1',
      capability: 'compute.sha256',
      payload: 'physical-node-ci',
    },
  };
  const body = JSON.stringify(taskEnvelope);

  const unauth = await fetch(`${base}/v1/execute`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body,
  });
  assert.equal(unauth.status, 401);

  const timestamp = Date.now();
  const nonce = createNonce();
  const signature = signWorkerEnvelope(secret, { timestamp, nonce, body });
  const headers = {
    'content-type': 'application/json',
    'x-bl-timestamp': String(timestamp),
    'x-bl-nonce': nonce,
    'x-bl-signature': signature,
  };

  const authorized = await fetch(`${base}/v1/execute`, { method: 'POST', headers, body });
  assert.equal(authorized.status, 200);
  const result = await authorized.json();
  assert.equal(result.ok, true);
  assert.equal(typeof result.result.sha256, 'string');
  assert.equal(result.result.sha256.length, 64);

  const replay = await fetch(`${base}/v1/execute`, { method: 'POST', headers, body });
  assert.equal(replay.status, 401);
  const replayBody = await replay.json();
  assert.equal(replayBody.error, 'replay');
});
