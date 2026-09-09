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
const searchToken = 'global-search-control-token-0123456789abcdef';
const principals = JSON.stringify([
  { id:'search-ops', tenantId:'*', tokenEnv:'SEARCH_CONTROL_TOKEN', scopes:['search:read','search:write','runtime:read'] },
]);

if (connectionString) {
  before(async () => {
    pool = new Pool({ connectionString, max:12, application_name:'bl-cf-control-search-test' });
    await openPostgresFederationState({ pool, applySchema:true });
  });
  beforeEach(async () => {
    await pool.query(`
      TRUNCATE TABLE
        federation_provider_heartbeat_nonces,
        federation_jobs,
        federation_rate_limit_buckets,
        federation_search_documents,
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

pgtest('index on coordinator A converges to B and public search cannot see internal corpus', async (t) => {
  const a = await startControlPlane(await freePort());
  const b = await startControlPlane(await freePort());
  t.after(() => stopChild(a.child));
  t.after(() => stopChild(b.child));

  const indexed = await postJson(a.base, '/search/index', searchToken, {
    documents: [
      { id:'public-doc', title:'Public', text:'needle public knowledge', source:'public-source', dataClass:'public', tenantId:'default' },
      { id:'internal-doc', title:'Internal', text:'needle internal knowledge', source:'internal-source', dataClass:'internal', tenantId:'internal-team' },
    ],
  });
  assert.equal(indexed.response.status, 201);
  assert.equal(indexed.body.indexed, 2);
  assert.equal(indexed.body.changed, 2);

  const publicQuery = await postJson(b.base, '/search/query', null, { query:'needle' });
  assert.equal(publicQuery.response.status, 200);
  assert.deepEqual(publicQuery.body.results.map((r) => r.id), ['public-doc']);
  assert.equal('tenantId' in publicQuery.body.results[0], false);
  assert.equal('dataClass' in publicQuery.body.results[0], false);

  const privileged = await postJson(b.base, '/search/query', searchToken, { query:'needle' });
  assert.equal(privileged.response.status, 200);
  assert.deepEqual(new Set(privileged.body.results.map((r) => r.id)), new Set(['public-doc','internal-doc']));

  const health = await fetch(`${b.base}/health`).then(async (response) => ({ response, body:await response.json() }));
  assert.equal(health.body.searchBackend, 'postgres-materialized');
  assert.equal(health.body.search.documents, 2);
  assert.equal('byDataClass' in health.body.search, false);

  const runtimeStatus = await fetch(`${b.base}/runtime/status`, { headers:{ authorization:`Bearer ${searchToken}` } });
  assert.equal(runtimeStatus.status, 200);
  const statusBody = await runtimeStatus.json();
  assert.equal(statusBody.search.byDataClass.internal, 1);
});

pgtest('tombstone on A removes document on B and from a fresh coordinator bootstrap', async (t) => {
  const a = await startControlPlane(await freePort());
  const b = await startControlPlane(await freePort());
  t.after(() => stopChild(a.child));
  t.after(() => stopChild(b.child));

  assert.equal((await postJson(a.base, '/search/index', searchToken, {
    document:{ id:'vanish', title:'Vanish', text:'vanishing-token', dataClass:'public' },
  })).response.status, 201);
  assert.equal((await postJson(b.base, '/search/query', searchToken, { query:'vanishing-token' })).body.results[0].id, 'vanish');

  const deleted = await postJson(a.base, '/search/delete', searchToken, { id:'vanish' });
  assert.equal(deleted.response.status, 200);
  assert.equal(deleted.body.changed, 1);
  const after = await postJson(b.base, '/search/query', searchToken, { query:'vanishing-token' });
  assert.equal(after.body.results.length, 0);

  const c = await startControlPlane(await freePort());
  t.after(() => stopChild(c.child));
  const fresh = await postJson(c.base, '/search/query', searchToken, { query:'vanishing-token' });
  assert.equal(fresh.body.results.length, 0);
  const row = await pool.query(`SELECT status,deleted_at,change_seq FROM federation_search_documents WHERE id='vanish'`);
  assert.equal(row.rows[0].status, 'deleted');
  assert.ok(row.rows[0].deleted_at);
  assert.ok(Number(row.rows[0].change_seq) > 0);
});

pgtest('shared search can be explicitly rolled back to process-local memory mode', async (t) => {
  const runtime = await startControlPlane(await freePort(), { BL_SEARCH_MODE:'memory' });
  t.after(() => stopChild(runtime.child));
  const health = await fetch(`${runtime.base}/health`);
  assert.equal(health.status, 200);
  const body = await health.json();
  assert.equal(body.stateBackend, 'postgres');
  assert.equal(body.searchMode, 'memory');
  assert.equal(body.searchBackend, 'memory');
});

async function postJson(base, path, token, body) {
  const headers = { 'content-type':'application/json' };
  if (token) headers.authorization = `Bearer ${token}`;
  const response = await fetch(`${base}${path}`, { method:'POST', headers, body:JSON.stringify(body) });
  return { response, body:await response.json() };
}

async function startControlPlane(port, overrides = {}) {
  const env = {
    ...process.env,
    HOST:'127.0.0.1',
    PORT:String(port),
    BL_POSTGRES_URL:connectionString,
    BL_POSTGRES_AUTO_MIGRATE:'false',
    BL_POSTGRES_ALLOWED_DATA_CLASSES:'public,internal',
    BL_SEARCH_ALLOWED_DATA_CLASSES:'public,internal',
    BL_PROVIDER_SYNC_MODE:'delta',
    BL_SEARCH_MODE:'shared',
    BL_CONTROL_TOKEN:'',
    BL_CONTROL_PRINCIPALS_JSON:principals,
    BL_PUBLIC_READ_SCOPES:'search:read',
    SEARCH_CONTROL_TOKEN:searchToken,
    BL_RATE_LIMIT_BURST:'1000',
    BL_RATE_LIMIT_PER_SECOND:'100',
    ...overrides,
  };
  const child = spawn(process.execPath, ['dev-server.mjs'], { cwd:runtimeDir, env, stdio:['ignore','pipe','pipe'] });
  const stderr = [];
  child.stderr.on('data', (chunk) => stderr.push(chunk.toString()));
  await waitForLine(child, new RegExp(`listening on http://127\\.0\\.0\\.1:${port}`), 15_000, stderr);
  return { child, base:`http://127.0.0.1:${port}` };
}

function waitForLine(child, pattern, timeoutMs, stderr) {
  return new Promise((resolve, reject) => {
    let output = '';
    const timer = setTimeout(() => finish(new Error(`control plane startup timeout; stderr=${stderr.join('')}`)), timeoutMs);
    const onData = (chunk) => { output += chunk.toString(); if (pattern.test(output)) finish(); };
    const onExit = (code) => finish(new Error(`control plane exited before ready: ${code}; stderr=${stderr.join('')}`));
    function finish(error = null) { clearTimeout(timer); child.stdout.off('data', onData); child.off('exit', onExit); error ? reject(error) : resolve(); }
    child.stdout.on('data', onData); child.once('exit', onExit);
  });
}
function stopChild(child) { if (child && !child.killed) child.kill('SIGTERM'); }
function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer(); server.unref(); server.once('error', reject);
    server.listen(0, '127.0.0.1', () => { const address = server.address(); const port = typeof address === 'object' && address ? address.port : null; server.close(() => port ? resolve(port) : reject(new Error('failed to allocate port'))); });
  });
}
