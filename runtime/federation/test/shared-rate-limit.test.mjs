import test, { after, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { Pool } from 'pg';
import { openPostgresFederationState } from '../lib/postgres-state.mjs';
import { PostgresTokenBucketLimiter, TokenBucketLimiter, classifyRateLimitRoute, rateLimitScopeKey } from '../lib/rate-limit.mjs';

const connectionString = process.env.BL_TEST_POSTGRES_URL || null;
let pool = null;

if (connectionString) {
  before(async () => {
    pool = new Pool({ connectionString, max: 20, application_name: 'bl-cf-shared-rate-test' });
    await openPostgresFederationState({ pool, applySchema: true });
  });
  beforeEach(async () => {
    await pool.query('TRUNCATE TABLE federation_rate_limit_buckets');
  });
  after(async () => { await pool?.end(); });
}

const pgtest = (name, fn) => test(name, { skip: connectionString ? false : 'BL_TEST_POSTGRES_URL is not configured' }, fn);

test('memory limiter still preserves deterministic token-bucket semantics', () => {
  const limiter = new TokenBucketLimiter({ capacity: 2, refillPerSecond: 1 });
  assert.equal(limiter.take('a', 1, 1000).ok, true);
  assert.equal(limiter.take('a', 1, 1000).ok, true);
  const blocked = limiter.take('a', 1, 1000);
  assert.equal(blocked.ok, false);
  assert.equal(blocked.retryAfterMs, 1000);
  assert.equal(limiter.take('a', 1, 2000).ok, true);
});

test('rate-limit scope keys are stable fingerprints and route costs separate expensive paths', () => {
  const key = rateLimitScopeKey({ principalId: 'tenant-operator', routeGroup: 'execution' });
  assert.match(key, /^[a-f0-9]{64}$/);
  assert.equal(key.includes('tenant-operator'), false);
  assert.equal(key, rateLimitScopeKey({ principalId: 'tenant-operator', routeGroup: 'execution' }));
  assert.notEqual(key, rateLimitScopeKey({ principalId: 'tenant-operator', routeGroup: 'read' }));
  assert.deepEqual(classifyRateLimitRoute('POST', '/execute'), { group: 'execution', cost: 5 });
  assert.deepEqual(classifyRateLimitRoute('POST', '/tasks/submit'), { group: 'task-submit', cost: 2 });
  assert.deepEqual(classifyRateLimitRoute('GET', '/health'), { group: 'read', cost: 1 });
});

pgtest('parallel coordinators consume one shared burst instead of multiplying quota', async () => {
  const a = new PostgresTokenBucketLimiter(pool, { capacity: 10, refillPerSecond: 1, cleanupEvery: 10000 });
  const b = new PostgresTokenBucketLimiter(pool, { capacity: 10, refillPerSecond: 1, cleanupEvery: 10000 });
  const key = rateLimitScopeKey({ principalId: 'shared-principal', routeGroup: 'execution' });
  const now = 1_000_000;

  const results = await Promise.all(Array.from({ length: 20 }, (_, i) => (i % 2 ? a : b).take(key, 1, now)));
  assert.equal(results.filter((x) => x.ok).length, 10);
  assert.equal(results.filter((x) => !x.ok).length, 10);

  const row = await pool.query('SELECT tokens FROM federation_rate_limit_buckets WHERE scope_key=$1', [key]);
  assert.equal(row.rowCount, 1);
  assert.equal(Number(row.rows[0].tokens), 0);
});

pgtest('shared bucket survives limiter recreation and refills from persisted timestamp', async () => {
  const key = rateLimitScopeKey({ address: '203.0.113.9', routeGroup: 'search-read' });
  const first = new PostgresTokenBucketLimiter(pool, { capacity: 2, refillPerSecond: 1, cleanupEvery: 10000 });
  assert.equal((await first.take(key, 2, 10_000)).ok, true);
  assert.equal((await first.take(key, 1, 10_000)).ok, false);

  const second = new PostgresTokenBucketLimiter(pool, { capacity: 2, refillPerSecond: 1, cleanupEvery: 10000 });
  const half = await second.take(key, 1, 10_500);
  assert.equal(half.ok, false);
  assert.equal(half.retryAfterMs, 500);
  assert.equal((await second.take(key, 1, 11_000)).ok, true);
});

pgtest('database stores only hashed scope key and expired buckets can be cleaned', async () => {
  const rawAddress = '198.51.100.88';
  const key = rateLimitScopeKey({ address: rawAddress, routeGroup: 'read' });
  const limiter = new PostgresTokenBucketLimiter(pool, { capacity: 1, refillPerSecond: 1, idleTtlMs: 1000, cleanupEvery: 10000 });
  await limiter.take(key, 1, 5000);

  const rows = await pool.query('SELECT scope_key::text, tokens, expires_at FROM federation_rate_limit_buckets');
  assert.equal(rows.rowCount, 1);
  assert.equal(rows.rows[0].scope_key, key);
  assert.equal(rows.rows[0].scope_key.includes(rawAddress), false);
  assert.equal(await limiter.cleanupExpired(5999), 0);
  assert.equal(await limiter.cleanupExpired(6000), 1);
  assert.equal((await limiter.stats(6000)).buckets, 0);
});
