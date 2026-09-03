import test, { after, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import net from 'node:net';
import { fileURLToPath } from 'node:url';
import { Pool } from 'pg';
import { openPostgresFederationState } from '../lib/postgres-state.mjs';

const connectionString = process.env.BL_TEST_POSTGRES_URL || null;
let pool = null;
const runtimeDir = fileURLToPath(new URL('..', import.meta.url));
const tenantToken = 'tenant-a-control-token-0123456789abcdef';
const opsToken = 'global-ops-control-token-0123456789abcdef';
const principalConfig = JSON.stringify([
  { id: 'tenant-a', tenantId: 'tenant-a', tokenEnv: 'TENANT_A_CONTROL_TOKEN', scopes: ['task:submit'] },
  { id: 'ops', tenantId: '*', tokenEnv: 'OPS_CONTROL_TOKEN', scopes: ['provider:read','runtime:read'] },
]);

if (connectionString) {
  before(async () => {
    pool = new Pool({ connectionString, max: 12, application_name: 'bl-cf-control-plane-guard-test' });
    await openPostgresFederationState({ pool, applySchema: true });
  });
  beforeEach(async () => {
    await pool.query(`
      TRUNCATE TABLE
        federation_provider_heartbeat_nonces,
        federation_jobs,
        federation_rate_limit_buckets,
        federation_budget_reservations,
        federation_contribution_ledger,
        federation_audit,
        federation_providers
      RESTART IDENTITY CASCADE
    `);
  });
  after(async () => { await pool?.end(); });
}

const pgtest = (name, fn) => test(name, { skip: connectionString ? false : 'BL_TEST_POSTGRES_URL is not configured' }, fn);

pgtest('two control planes share principal quota and enforce tenant/scope boundaries', async (t) => {
  const portA = await freePort();
  const portB = await freePort();
  const a = await startControlPlane(portA);
  const b = await startControlPlane(portB);
  t.after(() => stopChild(a.child));
  t.after(() => stopChild(b.child));

  const health = await fetch(`${a.base}/health`);
  assert.equal(health.status, 200);
  const healthBody = await health.json();
  assert.equal(healthBody.rateLimitBackend, 'postgres');
  assert.equal(healthBody.controlAuthConfigured, true);
  assert.equal(healthBody.scopedControlPrincipals, 2);

  await pool.query('TRUNCATE TABLE federation_rate_limit_buckets');

  const first = await postJson(a.base, '/tasks/submit', tenantToken, {
    task: { id:'shared-limit-a', capability:'compute.echo', payload:{n:1}, dataClass:'public' },
    options: { idempotencyKey:'shared-limit-a' },
  });
  const second = await postJson(b.base, '/tasks/submit', tenantToken, {
    task: { id:'shared-limit-b', capability:'compute.echo', payload:{n:2}, dataClass:'public' },
    options: { idempotencyKey:'shared-limit-b' },
  });
  const third = await postJson(a.base, '/tasks/submit', tenantToken, {
    task: { id:'shared-limit-c', capability:'compute.echo', payload:{n:3}, dataClass:'public' },
    options: { idempotencyKey:'shared-limit-c' },
  });
  assert.equal(first.response.status, 202);
  assert.equal(second.response.status, 202);
  assert.equal(third.response.status, 429);
  assert.equal(first.body.job.task.tenantId, 'tenant-a');
  assert.equal(second.body.job.task.tenantId, 'tenant-a');

  const rows = await pool.query(`SELECT COUNT(*)::int AS n, MIN(tokens) AS tokens FROM federation_rate_limit_buckets`);
  assert.equal(Number(rows.rows[0].n), 1);
  assert.ok(Number(rows.rows[0].tokens) < 0.01);

  await pool.query('TRUNCATE TABLE federation_rate_limit_buckets');
  const crossTenant = await postJson(a.base, '/tasks/submit', tenantToken, {
    task: { id:'cross-tenant', tenantId:'tenant-b', capability:'compute.echo', payload:null, dataClass:'public' },
  });
  assert.equal(crossTenant.response.status, 403);
  assert.equal(crossTenant.body.code, 'TENANT_SCOPE_VIOLATION');
  assert.equal(await jobExists('cross-tenant'), false);

  const tenantProviders = await getJson(a.base, '/providers', tenantToken);
  assert.equal(tenantProviders.response.status, 403);
  assert.equal(tenantProviders.body.error, 'scope-denied');

  const opsProviders = await getJson(b.base, '/providers', opsToken);
  assert.equal(opsProviders.response.status, 200);
  assert.ok(Array.isArray(opsProviders.body.providers));
});

async function jobExists(id) {
  const result = await pool.query('SELECT 1 FROM federation_jobs WHERE id=$1', [id]);
  return result.rowCount > 0;
}

async function postJson(base, path, token, body) {
  const response = await fetch(`${base}${path}`, {
    method: 'POST',
    headers: { 'content-type':'application/json', authorization:`Bearer ${token}` },
    body: JSON.stringify(body),
  });
  return { response, body: await response.json() };
}

async function getJson(base, path, token) {
  const response = await fetch(`${base}${path}`, { headers: { authorization:`Bearer ${token}` } });
  return { response, body: await response.json() };
}

async function startControlPlane(port) {
  const env = {
    ...process.env,
    HOST: '127.0.0.1',
    PORT: String(port),
    BL_POSTGRES_URL: connectionString,
    BL_POSTGRES_AUTO_MIGRATE: 'false',
    BL_PROVIDER_SYNC_MODE: 'delta',
    BL_POSTGRES_ALLOWED_DATA_CLASSES: 'public',
    BL_CONTROL_TOKEN: '',
    BL_CONTROL_PRINCIPALS_JSON: principalConfig,
    TENANT_A_CONTROL_TOKEN: tenantToken,
    OPS_CONTROL_TOKEN: opsToken,
    BL_RATE_LIMIT_BURST: '4',
    BL_RATE_LIMIT_PER_SECOND: '0.001',
    BL_RATE_LIMIT_CLEANUP_EVERY: '10000',
  };
  const child = spawn(process.execPath, ['dev-server.mjs'], { cwd: runtimeDir, env, stdio: ['ignore','pipe','pipe'] });
  const stderr = [];
  child.stderr.on('data', (chunk) => stderr.push(chunk.toString()));
  await waitForLine(child, new RegExp(`listening on http://127\\.0\\.0\\.1:${port}`), 15_000, stderr);
  return { child, base: `http://127.0.0.1:${port}` };
}

function waitForLine(child, pattern, timeoutMs, stderr) {
  return new Promise((resolve, reject) => {
    let output = '';
    const timer = setTimeout(() => finish(new Error(`control plane startup timeout; stderr=${stderr.join('')}`)), timeoutMs);
    const onData = (chunk) => {
      output += chunk.toString();
      if (pattern.test(output)) finish();
    };
    const onExit = (code) => finish(new Error(`control plane exited before ready: ${code}; stderr=${stderr.join('')}`));
    function finish(error = null) {
      clearTimeout(timer);
      child.stdout.off('data', onData);
      child.off('exit', onExit);
      error ? reject(error) : resolve();
    }
    child.stdout.on('data', onData);
    child.once('exit', onExit);
  });
}

function stopChild(child) {
  if (!child || child.killed) return;
  child.kill('SIGTERM');
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      const port = typeof address === 'object' && address ? address.port : null;
      server.close(() => port ? resolve(port) : reject(new Error('failed to allocate port')));
    });
  });
}
