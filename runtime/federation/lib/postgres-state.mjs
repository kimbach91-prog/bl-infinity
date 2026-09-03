import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { canonicalize, sha256 } from './canonical.mjs';
import { taskFingerprint } from './cache.mjs';
import { idempotencyScopeKey } from './queue.mjs';
import { validateTask } from './policy.mjs';

const LOCK_NAMESPACE = 424201;
const LOCK_LEDGER = 1;
const LOCK_AUDIT = 2;
const LOCK_BUDGET = 3;

export async function openPostgresFederationState({
  connectionString = process.env.BL_POSTGRES_URL,
  pool = null,
  applySchema = false,
  queue = {},
  cache = {},
  budget = {},
  poolOptions = {},
} = {}) {
  let ownsPool = false;
  if (!pool) {
    if (!connectionString) throw new Error('Postgres connectionString or pool is required');
    const { Pool } = await import('pg');
    pool = new Pool({
      connectionString,
      application_name: 'bl-compute-federation',
      max: Number(poolOptions.max ?? 10),
      idleTimeoutMillis: Number(poolOptions.idleTimeoutMillis ?? 30_000),
      connectionTimeoutMillis: Number(poolOptions.connectionTimeoutMillis ?? 10_000),
      ...poolOptions,
    });
    ownsPool = true;
  }

  if (applySchema) {
    const schema = await readFile(new URL('../storage/postgres/schema.sql', import.meta.url), 'utf8');
    await pool.query(schema);
  } else {
    await pool.query('SELECT 1');
  }

  return {
    pool,
    queue: new PostgresLeaseQueue(pool, queue),
    cache: new PostgresResultCache(pool, cache),
    ledger: new PostgresContributionLedger(pool),
    audit: new PostgresAuditLog(pool),
    budget: new PostgresBudgetGovernor(pool, budget),
    close: async () => { if (ownsPool) await pool.end(); },
  };
}

export class PostgresLeaseQueue {
  constructor(pool, { defaultLeaseMs = 30_000, maxAttempts = 3 } = {}) {
    this.pool = pool;
    this.defaultLeaseMs = defaultLeaseMs;
    this.maxAttempts = maxAttempts;
  }

  async enqueue(task, { idempotencyKey = null, priority = 0, maxAttempts = this.maxAttempts, now = Date.now() } = {}) {
    validateTask(task);
    const tenantId = task.tenantId ?? 'default';
    const key = idempotencyScopeKey(task, idempotencyKey);
    const createdAt = new Date(now);
    const result = await this.pool.query(`
      INSERT INTO federation_jobs
        (id,idempotency_key,tenant_id,capability,task,state,priority,attempts,max_attempts,created_at,available_at)
      VALUES ($1,$2,$3,$4,$5::jsonb,'pending',$6,0,$7,$8,$8)
      ON CONFLICT (tenant_id,idempotency_key) DO NOTHING
      RETURNING *
    `, [task.id, key, tenantId, task.capability, JSON.stringify(task), Number(priority) || 0, Number(maxAttempts) || 1, createdAt]);
    if (result.rowCount === 1) return { job: mapJob(result.rows[0]), deduplicated: false };
    const existing = await this.pool.query('SELECT * FROM federation_jobs WHERE tenant_id=$1 AND idempotency_key=$2', [tenantId, key]);
    if (existing.rowCount !== 1) throw new Error('idempotency conflict could not be resolved');
    return { job: mapJob(existing.rows[0]), deduplicated: true };
  }

  async claim(workerId, capabilities = [], { leaseMs = this.defaultLeaseMs, now = Date.now() } = {}) {
    if (!capabilities.length) return null;
    return withTransaction(this.pool, async (client) => {
      await sweepExpiredTx(client, now);
      const selected = await client.query(`
        SELECT id
        FROM federation_jobs
        WHERE state='pending' AND available_at <= $1 AND capability = ANY($2::text[])
        ORDER BY priority DESC, available_at ASC, created_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT 1
      `, [new Date(now), capabilities]);
      if (!selected.rowCount) return null;
      const token = randomUUID();
      const updated = await client.query(`
        UPDATE federation_jobs
        SET state='running', attempts=attempts+1, lease_worker=$1, lease_token=$2,
            lease_expires_at=$3, lease_heartbeat_at=$4
        WHERE id=$5 AND state='pending'
        RETURNING *
      `, [workerId, token, new Date(now + leaseMs), new Date(now), selected.rows[0].id]);
      if (updated.rowCount !== 1) throw new Error('claim race detected');
      return mapJob(updated.rows[0]);
    });
  }

  async heartbeat(jobId, token, { leaseMs = this.defaultLeaseMs, now = Date.now() } = {}) {
    const result = await this.pool.query(`
      UPDATE federation_jobs
      SET lease_expires_at=$1, lease_heartbeat_at=$2
      WHERE id=$3 AND state='running' AND lease_token=$4
      RETURNING *
    `, [new Date(now + leaseMs), new Date(now), jobId, token]);
    if (result.rowCount !== 1) throw new Error('invalid lease token or job is not leased');
    return mapJob(result.rows[0]);
  }

  async complete(jobId, token, resultValue) {
    const result = await this.pool.query(`
      UPDATE federation_jobs
      SET state='succeeded', result=$1::jsonb, error=NULL,
          lease_worker=NULL, lease_token=NULL, lease_expires_at=NULL, lease_heartbeat_at=NULL
      WHERE id=$2 AND state='running' AND lease_token=$3
      RETURNING *
    `, [JSON.stringify(resultValue), jobId, token]);
    if (result.rowCount !== 1) throw new Error('invalid lease token or job is not leased');
    return mapJob(result.rows[0]);
  }

  async fail(jobId, token, error, { retryDelayMs = 0, now = Date.now(), terminal = false } = {}) {
    return withTransaction(this.pool, async (client) => {
      const locked = await client.query(`SELECT attempts,max_attempts FROM federation_jobs WHERE id=$1 AND state='running' AND lease_token=$2 FOR UPDATE`, [jobId, token]);
      if (locked.rowCount !== 1) throw new Error('invalid lease token or job is not leased');
      const row = locked.rows[0];
      const dead = terminal || Number(row.attempts) >= Number(row.max_attempts);
      const updated = await client.query(`
        UPDATE federation_jobs
        SET state=$1, error=$2::jsonb, available_at=$3,
            lease_worker=NULL, lease_token=NULL, lease_expires_at=NULL, lease_heartbeat_at=NULL
        WHERE id=$4
        RETURNING *
      `, [dead ? 'deadletter' : 'pending', JSON.stringify(normalizeError(error)), new Date(dead ? now : now + Math.max(0, retryDelayMs)), jobId]);
      return mapJob(updated.rows[0]);
    });
  }

  async sweepExpired(now = Date.now()) {
    return withTransaction(this.pool, async (client) => sweepExpiredTx(client, now));
  }

  async get(jobId) {
    const result = await this.pool.query('SELECT * FROM federation_jobs WHERE id=$1', [jobId]);
    return result.rowCount ? mapJob(result.rows[0]) : null;
  }

  async list({ state = null } = {}) {
    const result = state
      ? await this.pool.query('SELECT * FROM federation_jobs WHERE state=$1 ORDER BY created_at', [state])
      : await this.pool.query('SELECT * FROM federation_jobs ORDER BY created_at');
    return result.rows.map(mapJob);
  }
}

export class PostgresResultCache {
  constructor(pool, { maxEntries = 100_000, defaultTtlMs = 10 * 60_000 } = {}) {
    this.pool = pool;
    this.maxEntries = maxEntries;
    this.defaultTtlMs = defaultTtlMs;
  }

  async get(task, now = Date.now()) {
    if (!cacheable(task)) return null;
    const key = task.cacheKey ?? taskFingerprint(task);
    const result = await this.pool.query(`
      UPDATE federation_result_cache
      SET hits=hits+1
      WHERE cache_key=$1 AND expires_at > $2
      RETURNING *
    `, [key, new Date(now)]);
    if (result.rowCount) return mapCache(result.rows[0]);
    await this.pool.query('DELETE FROM federation_result_cache WHERE cache_key=$1 AND expires_at <= $2', [key, new Date(now)]);
    return null;
  }

  async set(task, value, { ttlMs = this.defaultTtlMs, now = Date.now() } = {}) {
    if (!cacheable(task)) return null;
    const key = task.cacheKey ?? taskFingerprint(task);
    const createdAt = new Date(now);
    const expiresAt = new Date(now + Math.max(1, ttlMs));
    const result = await this.pool.query(`
      INSERT INTO federation_result_cache(cache_key,task_id,data_class,tenant_id,value,created_at,expires_at,hits)
      VALUES($1,$2,$3,$4,$5::jsonb,$6,$7,0)
      ON CONFLICT(cache_key) DO UPDATE SET
        task_id=EXCLUDED.task_id, data_class=EXCLUDED.data_class, tenant_id=EXCLUDED.tenant_id,
        value=EXCLUDED.value, created_at=EXCLUDED.created_at, expires_at=EXCLUDED.expires_at, hits=0
      RETURNING *
    `, [key, task.id, task.dataClass ?? 'public', task.tenantId ?? 'default', JSON.stringify(value), createdAt, expiresAt]);
    await this.#prune(now);
    return mapCache(result.rows[0]);
  }

  async deleteByKey(key) {
    const result = await this.pool.query('DELETE FROM federation_result_cache WHERE cache_key=$1', [key]);
    return result.rowCount > 0;
  }

  async stats() {
    const result = await this.pool.query('SELECT COUNT(*)::bigint entries, COALESCE(SUM(hits),0)::bigint hits FROM federation_result_cache');
    return { entries: Number(result.rows[0].entries), hits: Number(result.rows[0].hits) };
  }

  async #prune(now) {
    await this.pool.query('DELETE FROM federation_result_cache WHERE expires_at <= $1', [new Date(now)]);
    if (!Number.isFinite(this.maxEntries) || this.maxEntries <= 0) return;
    await this.pool.query(`
      WITH ranked AS (
        SELECT cache_key, row_number() OVER (ORDER BY created_at DESC) AS rn
        FROM federation_result_cache
      )
      DELETE FROM federation_result_cache c
      USING ranked r
      WHERE c.cache_key=r.cache_key AND r.rn > $1
    `, [this.maxEntries]);
  }
}

export class PostgresContributionLedger {
  constructor(pool) { this.pool = pool; }

  async record(input) {
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client, LOCK_LEDGER);
      const last = await client.query('SELECT seq,hash FROM federation_contribution_ledger ORDER BY seq DESC LIMIT 1');
      const seqResult = await client.query(`SELECT nextval(pg_get_serial_sequence('federation_contribution_ledger','seq')) AS seq`);
      const seq = Number(seqResult.rows[0].seq);
      const core = {
        id: randomUUID(), seq, ts: new Date().toISOString(), taskId: input.taskId, providerId: input.providerId,
        consentRef: input.consentRef ?? null, tenantId: input.tenantId ?? 'default',
        measuredLatencyMs: Math.max(0, Number(input.measuredLatencyMs) || 0),
        billedCostUsd: Math.max(0, Number(input.billedCostUsd) || 0),
        inputBytes: Math.max(0, Number(input.inputBytes) || 0), outputBytes: Math.max(0, Number(input.outputBytes) || 0),
        reportedUsage: input.reportedUsage ? structuredClone(input.reportedUsage) : null,
        status: input.status ?? 'succeeded', prevHash: last.rows[0]?.hash ?? null,
      };
      const hash = sha256(canonicalize(core));
      await client.query(`
        INSERT INTO federation_contribution_ledger
          (seq,id,ts,task_id,provider_id,consent_ref,tenant_id,measured_latency_ms,billed_cost_usd,input_bytes,output_bytes,reported_usage,status,prev_hash,hash)
        VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12::jsonb,$13,$14,$15)
      `, [core.seq, core.id, core.ts, core.taskId, core.providerId, core.consentRef, core.tenantId, core.measuredLatencyMs, core.billedCostUsd, core.inputBytes, core.outputBytes, core.reportedUsage ? JSON.stringify(core.reportedUsage) : null, core.status, core.prevHash, hash]);
      return { ...core, hash };
    });
  }

  async list({ providerId = null, tenantId = null } = {}) {
    const clauses = []; const values = [];
    if (providerId) { values.push(providerId); clauses.push(`provider_id=$${values.length}`); }
    if (tenantId) { values.push(tenantId); clauses.push(`tenant_id=$${values.length}`); }
    const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
    const result = await this.pool.query(`SELECT * FROM federation_contribution_ledger ${where} ORDER BY seq`, values);
    return result.rows.map(mapLedger);
  }

  async summary() {
    const result = await this.pool.query(`
      SELECT provider_id, COUNT(*)::bigint tasks,
        SUM(CASE WHEN status='succeeded' THEN 1 ELSE 0 END)::bigint success,
        SUM(CASE WHEN status='succeeded' THEN 0 ELSE 1 END)::bigint failure,
        COALESCE(SUM(measured_latency_ms),0) measured_latency_ms,
        COALESCE(SUM(billed_cost_usd),0) billed_cost_usd,
        COALESCE(SUM(input_bytes),0)::bigint input_bytes,
        COALESCE(SUM(output_bytes),0)::bigint output_bytes
      FROM federation_contribution_ledger GROUP BY provider_id
    `);
    return Object.fromEntries(result.rows.map((r) => [r.provider_id, {
      tasks: Number(r.tasks), success: Number(r.success), failure: Number(r.failure),
      measuredLatencyMs: Number(r.measured_latency_ms), billedCostUsd: Number(r.billed_cost_usd),
      inputBytes: Number(r.input_bytes), outputBytes: Number(r.output_bytes),
    }]));
  }
}

export class PostgresAuditLog {
  constructor(pool) { this.pool = pool; }

  async append(type, data) {
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client, LOCK_AUDIT);
      const last = await client.query('SELECT seq,hash FROM federation_audit ORDER BY seq DESC LIMIT 1');
      const seqResult = await client.query(`SELECT nextval(pg_get_serial_sequence('federation_audit','seq')) AS seq`);
      const core = { seq: Number(seqResult.rows[0].seq), ts: new Date().toISOString(), type, data: structuredClone(data), prevHash: last.rows[0]?.hash ?? null };
      const hash = sha256(canonicalize(core));
      await client.query('INSERT INTO federation_audit(seq,ts,type,data,prev_hash,hash) VALUES($1,$2,$3,$4::jsonb,$5,$6)', [core.seq, core.ts, core.type, JSON.stringify(core.data), core.prevHash, hash]);
      return { ...core, hash };
    });
  }

  async list() {
    const result = await this.pool.query('SELECT * FROM federation_audit ORDER BY seq');
    return result.rows.map((r) => ({ seq: Number(r.seq), ts: asIso(r.ts), type: r.type, data: r.data, prevHash: r.prev_hash, hash: r.hash }));
  }
}

export class PostgresBudgetGovernor {
  constructor(pool, { totalUsd = Infinity, perTenantUsd = {}, perProviderUsd = {} } = {}) {
    this.pool = pool;
    this.totalUsd = Number(totalUsd);
    this.perTenantUsd = new Map(Object.entries(perTenantUsd).map(([k,v]) => [k, Number(v)]));
    this.perProviderUsd = new Map(Object.entries(perProviderUsd).map(([k,v]) => [k, Number(v)]));
  }

  async canSpend({ amountUsd = 0, tenantId = 'default', providerId = null } = {}) {
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client, LOCK_BUDGET);
      return budgetVerdict(client, this, { amountUsd, tenantId, providerId });
    });
  }

  async reserve({ amountUsd = 0, tenantId = 'default', providerId = null, taskId = null } = {}) {
    const amount = Number(amountUsd);
    if (!Number.isFinite(amount) || amount < 0) throw new Error('budget amount must be >= 0');
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client, LOCK_BUDGET);
      const verdict = await budgetVerdict(client, this, { amountUsd: amount, tenantId, providerId });
      if (!verdict.ok) return verdict;
      const id = randomUUID(); const createdAt = new Date().toISOString();
      await client.query(`
        INSERT INTO federation_budget_reservations(id,task_id,tenant_id,provider_id,reserved_usd,state,created_at)
        VALUES($1,$2,$3,$4,$5,'reserved',$6)
      `, [id, taskId, tenantId, providerId, amount, createdAt]);
      return { ok: true, reservation: { id, amountUsd: amount, tenantId, providerId, taskId, state: 'reserved', createdAt } };
    });
  }

  async commit(id, actualUsd = null) {
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client, LOCK_BUDGET);
      const found = await client.query(`SELECT * FROM federation_budget_reservations WHERE id=$1 AND state='reserved' FOR UPDATE`, [id]);
      if (found.rowCount !== 1) throw new Error('reservation is not active');
      const row = found.rows[0];
      const actual = actualUsd == null ? Number(row.reserved_usd) : Number(actualUsd);
      if (!Number.isFinite(actual) || actual < 0) throw new Error('actualUsd must be >= 0');
      const extra = Math.max(0, actual - Number(row.reserved_usd));
      if (extra > 0) {
        const verdict = await budgetVerdict(client, this, { amountUsd: extra, tenantId: row.tenant_id, providerId: row.provider_id });
        if (!verdict.ok) throw new Error(`actual cost rejected: ${verdict.reason}`);
      }
      const finishedAt = new Date().toISOString();
      const updated = await client.query(`
        UPDATE federation_budget_reservations
        SET state='committed', actual_usd=$1, finished_at=$2
        WHERE id=$3 RETURNING *
      `, [actual, finishedAt, id]);
      return mapReservation(updated.rows[0]);
    });
  }

  async release(id, reason = 'released') {
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client, LOCK_BUDGET);
      const updated = await client.query(`
        UPDATE federation_budget_reservations
        SET state='released', reason=$1, finished_at=$2
        WHERE id=$3 AND state='reserved'
        RETURNING *
      `, [reason, new Date().toISOString(), id]);
      if (updated.rowCount !== 1) throw new Error('reservation is not active');
      return mapReservation(updated.rows[0]);
    });
  }

  async snapshot() {
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client, LOCK_BUDGET);
      const global = await budgetSum(client);
      const tenants = await client.query(`
        SELECT tenant_id,
          COALESCE(SUM(CASE WHEN state='committed' THEN actual_usd ELSE 0 END),0) spent,
          COALESCE(SUM(CASE WHEN state='reserved' THEN reserved_usd ELSE 0 END),0) reserved
        FROM federation_budget_reservations GROUP BY tenant_id
      `);
      const providers = await client.query(`
        SELECT provider_id,
          COALESCE(SUM(CASE WHEN state='committed' THEN actual_usd ELSE 0 END),0) spent,
          COALESCE(SUM(CASE WHEN state='reserved' THEN reserved_usd ELSE 0 END),0) reserved
        FROM federation_budget_reservations WHERE provider_id IS NOT NULL GROUP BY provider_id
      `);
      return {
        limits: { totalUsd: this.totalUsd, perTenantUsd: Object.fromEntries(this.perTenantUsd), perProviderUsd: Object.fromEntries(this.perProviderUsd) },
        spent: { totalUsd: global.spent, perTenantUsd: Object.fromEntries(tenants.rows.map((r) => [r.tenant_id, Number(r.spent)])), perProviderUsd: Object.fromEntries(providers.rows.map((r) => [r.provider_id, Number(r.spent)])) },
        reserved: { totalUsd: global.reserved, perTenantUsd: Object.fromEntries(tenants.rows.map((r) => [r.tenant_id, Number(r.reserved)])), perProviderUsd: Object.fromEntries(providers.rows.map((r) => [r.provider_id, Number(r.reserved)])) },
      };
    });
  }
}

async function sweepExpiredTx(client, now) {
  const result = await client.query(`
    UPDATE federation_jobs
    SET state=CASE WHEN attempts >= max_attempts THEN 'deadletter' ELSE 'pending' END,
        error=$2::jsonb, available_at=$1,
        lease_worker=NULL, lease_token=NULL, lease_expires_at=NULL, lease_heartbeat_at=NULL
    WHERE state='running' AND lease_expires_at <= $1
    RETURNING id
  `, [new Date(now), JSON.stringify({ name: 'LeaseExpired', message: 'worker lease expired' })]);
  return result.rows.map((r) => r.id);
}

async function budgetVerdict(client, governor, { amountUsd = 0, tenantId = 'default', providerId = null } = {}) {
  const amount = Number(amountUsd);
  if (!Number.isFinite(amount) || amount < 0) return { ok: false, reason: 'invalid-budget-amount' };
  const global = await budgetSum(client);
  if (global.spent + global.reserved + amount > governor.totalUsd) return { ok: false, reason: 'global-budget-exceeded' };
  const tenant = await budgetSum(client, 'tenant_id', tenantId);
  if (tenant.spent + tenant.reserved + amount > (governor.perTenantUsd.get(tenantId) ?? Infinity)) return { ok: false, reason: 'tenant-budget-exceeded' };
  if (providerId) {
    const provider = await budgetSum(client, 'provider_id', providerId);
    if (provider.spent + provider.reserved + amount > (governor.perProviderUsd.get(providerId) ?? Infinity)) return { ok: false, reason: 'provider-budget-exceeded' };
  }
  return { ok: true };
}

async function budgetSum(client, field = null, value = null) {
  const allowed = new Set(['tenant_id','provider_id']);
  if (field && !allowed.has(field)) throw new Error('invalid budget field');
  const where = field ? ` WHERE ${field}=$1` : '';
  const result = await client.query(`
    SELECT
      COALESCE(SUM(CASE WHEN state='committed' THEN actual_usd ELSE 0 END),0) spent,
      COALESCE(SUM(CASE WHEN state='reserved' THEN reserved_usd ELSE 0 END),0) reserved
    FROM federation_budget_reservations${where}
  `, field ? [value] : []);
  return { spent: Number(result.rows[0].spent), reserved: Number(result.rows[0].reserved) };
}

async function advisoryLock(client, key) {
  await client.query('SELECT pg_advisory_xact_lock($1,$2)', [LOCK_NAMESPACE, key]);
}

async function withTransaction(pool, fn) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const value = await fn(client);
    await client.query('COMMIT');
    return value;
  } catch (error) {
    try { await client.query('ROLLBACK'); } catch {}
    throw error;
  } finally {
    client.release();
  }
}

function mapJob(row) {
  return {
    id: row.id, task: row.task, idempotencyKey: row.idempotency_key, state: row.state,
    priority: Number(row.priority), attempts: Number(row.attempts), maxAttempts: Number(row.max_attempts),
    createdAt: asIso(row.created_at), availableAt: new Date(row.available_at).getTime(),
    lease: row.lease_token ? { workerId: row.lease_worker, token: row.lease_token, expiresAt: new Date(row.lease_expires_at).getTime(), lastHeartbeatAt: new Date(row.lease_heartbeat_at).getTime() } : null,
    result: row.result ?? null, error: row.error ?? null,
  };
}
function mapCache(row) { return { key: row.cache_key, taskId: row.task_id, dataClass: row.data_class, tenantId: row.tenant_id, value: row.value, createdAt: new Date(row.created_at).getTime(), expiresAt: new Date(row.expires_at).getTime(), hits: Number(row.hits) }; }
function mapLedger(row) { return { seq: Number(row.seq), id: row.id, ts: asIso(row.ts), taskId: row.task_id, providerId: row.provider_id, consentRef: row.consent_ref, tenantId: row.tenant_id, measuredLatencyMs: Number(row.measured_latency_ms), billedCostUsd: Number(row.billed_cost_usd), inputBytes: Number(row.input_bytes), outputBytes: Number(row.output_bytes), reportedUsage: row.reported_usage ?? null, status: row.status, prevHash: row.prev_hash, hash: row.hash }; }
function mapReservation(row) { return { id: row.id, taskId: row.task_id, tenantId: row.tenant_id, providerId: row.provider_id, amountUsd: Number(row.reserved_usd), actualUsd: row.actual_usd == null ? null : Number(row.actual_usd), state: row.state, createdAt: asIso(row.created_at), reason: row.reason ?? null }; }
function normalizeError(error) { return error && typeof error === 'object' ? { name: error.name ?? 'Error', message: error.message ?? String(error) } : { name: 'Error', message: String(error) }; }
function cacheable(task) { if (task.sideEffect === true) return false; const cls = task.dataClass ?? 'public'; if (cls === 'public') return task.cachePolicy === 'public'; if (cls === 'internal') return task.cachePolicy === 'tenant'; if (cls === 'private') return task.cachePolicy === 'private-ok'; return false; }
function asIso(value) { return value instanceof Date ? value.toISOString() : new Date(value).toISOString(); }
