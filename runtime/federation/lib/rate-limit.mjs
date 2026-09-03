import { createHash } from 'node:crypto';

export class TokenBucketLimiter {
  constructor({ capacity = 120, refillPerSecond = 2, maxKeys = 10_000 } = {}) {
    this.capacity = positiveNumber(capacity, 'capacity');
    this.refillPerSecond = positiveNumber(refillPerSecond, 'refillPerSecond');
    this.maxKeys = positiveInteger(maxKeys, 'maxKeys');
    this.map = new Map();
  }

  take(key, cost = 1, now = Date.now()) {
    const safeKey = normalizeKey(key);
    const safeCost = positiveNumber(cost, 'cost');
    let bucket = this.map.get(safeKey);
    if (!bucket) {
      if (this.map.size >= this.maxKeys) this.map.delete(this.map.keys().next().value);
      bucket = { tokens: this.capacity, updatedAt: now };
      this.map.set(safeKey, bucket);
    }
    const elapsed = Math.max(0, now - bucket.updatedAt) / 1000;
    bucket.tokens = Math.min(this.capacity, bucket.tokens + elapsed * this.refillPerSecond);
    bucket.updatedAt = now;
    if (bucket.tokens < safeCost) {
      return {
        ok: false,
        remaining: Math.max(0, Math.floor(bucket.tokens)),
        retryAfterMs: Math.ceil((safeCost - bucket.tokens) / this.refillPerSecond * 1000),
      };
    }
    bucket.tokens -= safeCost;
    return { ok: true, remaining: Math.max(0, Math.floor(bucket.tokens)) };
  }
}

export class PostgresTokenBucketLimiter {
  constructor(pool, {
    capacity = 120,
    refillPerSecond = 2,
    cleanupEvery = 1000,
    idleTtlMs = null,
  } = {}) {
    if (!pool?.connect || !pool?.query) throw new Error('Postgres pool is required for shared rate limiter');
    this.pool = pool;
    this.capacity = positiveNumber(capacity, 'capacity');
    this.refillPerSecond = positiveNumber(refillPerSecond, 'refillPerSecond');
    this.cleanupEvery = positiveInteger(cleanupEvery, 'cleanupEvery');
    const refillWindowMs = Math.ceil(this.capacity / this.refillPerSecond * 1000);
    this.idleTtlMs = idleTtlMs == null
      ? Math.max(60_000, refillWindowMs * 2)
      : positiveInteger(idleTtlMs, 'idleTtlMs');
    this.operations = 0;
  }

  async take(key, cost = 1, now = Date.now()) {
    const safeKey = normalizeKey(key);
    const safeCost = positiveNumber(cost, 'cost');
    const client = await this.pool.connect();
    let verdict;
    try {
      await client.query('BEGIN');
      await client.query(`
        INSERT INTO federation_rate_limit_buckets(scope_key,tokens,updated_at,expires_at)
        VALUES($1,$2,$3,$4)
        ON CONFLICT(scope_key) DO NOTHING
      `, [safeKey, this.capacity, new Date(now), new Date(now + this.idleTtlMs)]);

      const locked = await client.query(`
        SELECT tokens,updated_at
        FROM federation_rate_limit_buckets
        WHERE scope_key=$1
        FOR UPDATE
      `, [safeKey]);
      if (locked.rowCount !== 1) throw new Error('rate-limit bucket disappeared during transaction');

      const row = locked.rows[0];
      const updatedAt = new Date(row.updated_at).getTime();
      const elapsedSeconds = Math.max(0, now - updatedAt) / 1000;
      const available = Math.min(this.capacity, Number(row.tokens) + elapsedSeconds * this.refillPerSecond);
      const accepted = available >= safeCost;
      const remainingTokens = accepted ? available - safeCost : available;
      const retryAfterMs = accepted ? 0 : Math.ceil((safeCost - available) / this.refillPerSecond * 1000);

      await client.query(`
        UPDATE federation_rate_limit_buckets
        SET tokens=$1,updated_at=$2,expires_at=$3
        WHERE scope_key=$4
      `, [remainingTokens, new Date(now), new Date(now + this.idleTtlMs), safeKey]);
      await client.query('COMMIT');
      verdict = {
        ok: accepted,
        remaining: Math.max(0, Math.floor(remainingTokens)),
        ...(accepted ? {} : { retryAfterMs }),
      };
    } catch (error) {
      try { await client.query('ROLLBACK'); } catch {}
      throw error;
    } finally {
      client.release();
    }

    this.operations += 1;
    if (this.operations % this.cleanupEvery === 0) {
      try { await this.cleanupExpired(now); } catch {}
    }
    return verdict;
  }

  async cleanupExpired(now = Date.now()) {
    const result = await this.pool.query('DELETE FROM federation_rate_limit_buckets WHERE expires_at <= $1', [new Date(now)]);
    return Number(result.rowCount ?? 0);
  }

  async stats(now = Date.now()) {
    const result = await this.pool.query(`
      SELECT
        COUNT(*)::bigint AS buckets,
        COUNT(*) FILTER (WHERE expires_at <= $1)::bigint AS expired
      FROM federation_rate_limit_buckets
    `, [new Date(now)]);
    return { buckets: Number(result.rows[0].buckets), expired: Number(result.rows[0].expired) };
  }
}

export function rateLimitScopeKey({ principalId = null, address = 'unknown', routeGroup = 'default' } = {}) {
  const group = normalizeKey(routeGroup);
  const subject = principalId ? `principal:${normalizeKey(principalId)}` : `address:${normalizeKey(address)}`;
  return createHash('sha256').update(`bl-cf-rate-v1\0${subject}\0${group}`).digest('hex');
}

export function classifyRateLimitRoute(method = 'GET', url = '/') {
  const pathname = String(url || '/').split('?')[0];
  if (pathname.startsWith('/providers/heartbeat/self')) return { group: 'heartbeat-self', cost: 1 };
  if (pathname.startsWith('/orchestrate') || pathname === '/execute') return { group: 'execution', cost: 5 };
  if (pathname.startsWith('/providers/') && method !== 'GET') return { group: 'provider-admin', cost: 4 };
  if (pathname === '/tasks/submit') return { group: 'task-submit', cost: 2 };
  if (pathname === '/search/index') return { group: 'search-write', cost: 3 };
  if (pathname === '/search/query') return { group: 'search-read', cost: 1 };
  return { group: 'read', cost: 1 };
}

function normalizeKey(value) {
  const out = String(value ?? '').trim();
  if (!out || out.length > 512) throw new Error('rate-limit key must contain 1..512 characters');
  return out;
}
function positiveNumber(value, name) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) throw new Error(`${name} must be > 0`);
  return n;
}
function positiveInteger(value, name) {
  const n = Number(value);
  if (!Number.isSafeInteger(n) || n < 1) throw new Error(`${name} must be a positive integer`);
  return n;
}
