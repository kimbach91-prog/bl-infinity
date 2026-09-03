import { DatabaseSync } from 'node:sqlite';
import { randomUUID } from 'node:crypto';
import { validateTask } from './policy.mjs';
import { canonicalize, sha256 } from './canonical.mjs';
import { taskFingerprint } from './cache.mjs';
import { idempotencyScopeKey } from './queue.mjs';

export function createSqliteFederationState(path, { queue = {}, cache = {}, budget = {} } = {}) {
  const db = new DatabaseSync(path);
  db.exec(`
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    PRAGMA foreign_keys=ON;
    PRAGMA busy_timeout=5000;
    CREATE TABLE IF NOT EXISTS federation_jobs (
      id TEXT PRIMARY KEY,
      idempotency_key TEXT NOT NULL UNIQUE,
      capability TEXT NOT NULL,
      task_json TEXT NOT NULL,
      state TEXT NOT NULL,
      priority INTEGER NOT NULL DEFAULT 0,
      attempts INTEGER NOT NULL DEFAULT 0,
      max_attempts INTEGER NOT NULL DEFAULT 3,
      created_at INTEGER NOT NULL,
      available_at INTEGER NOT NULL,
      lease_worker TEXT,
      lease_token TEXT,
      lease_expires_at INTEGER,
      lease_heartbeat_at INTEGER,
      result_json TEXT,
      error_json TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_federation_jobs_claim ON federation_jobs(state, available_at, priority DESC, created_at);
    CREATE TABLE IF NOT EXISTS federation_cache (
      cache_key TEXT PRIMARY KEY,
      task_id TEXT NOT NULL,
      data_class TEXT NOT NULL,
      tenant_id TEXT NOT NULL,
      value_json TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      expires_at INTEGER NOT NULL,
      hits INTEGER NOT NULL DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_federation_cache_expiry ON federation_cache(expires_at);
    CREATE TABLE IF NOT EXISTS federation_ledger (
      seq INTEGER PRIMARY KEY AUTOINCREMENT,
      id TEXT NOT NULL UNIQUE,
      ts TEXT NOT NULL,
      task_id TEXT NOT NULL,
      provider_id TEXT NOT NULL,
      consent_ref TEXT,
      tenant_id TEXT NOT NULL,
      measured_latency_ms REAL NOT NULL,
      billed_cost_usd REAL NOT NULL,
      input_bytes INTEGER NOT NULL,
      output_bytes INTEGER NOT NULL,
      reported_usage_json TEXT,
      status TEXT NOT NULL,
      prev_hash TEXT,
      hash TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS federation_audit (
      seq INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      type TEXT NOT NULL,
      data_json TEXT NOT NULL,
      prev_hash TEXT,
      hash TEXT NOT NULL UNIQUE
    );
    CREATE TABLE IF NOT EXISTS federation_budget_reservations (
      id TEXT PRIMARY KEY,
      task_id TEXT,
      tenant_id TEXT NOT NULL,
      provider_id TEXT,
      reserved_usd REAL NOT NULL,
      actual_usd REAL,
      state TEXT NOT NULL,
      created_at TEXT NOT NULL,
      finished_at TEXT,
      reason TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_budget_state ON federation_budget_reservations(state, tenant_id, provider_id);
  `);
  return {
    db,
    queue: new SqliteLeaseQueue(db, queue),
    cache: new SqliteResultCache(db, cache),
    ledger: new SqliteContributionLedger(db),
    audit: new SqliteAuditLog(db),
    budget: new SqliteBudgetGovernor(db, budget),
    close: () => db.close(),
  };
}

export class SqliteLeaseQueue {
  constructor(db, { defaultLeaseMs = 30_000, maxAttempts = 3 } = {}) { this.db = db; this.defaultLeaseMs = defaultLeaseMs; this.maxAttempts = maxAttempts; }
  enqueue(task, { idempotencyKey = null, priority = 0, maxAttempts = this.maxAttempts, now = Date.now() } = {}) {
    validateTask(task);
    const key = idempotencyScopeKey(task, idempotencyKey);
    const existing = this.db.prepare('SELECT id FROM federation_jobs WHERE idempotency_key=?').get(key);
    if (existing) return { job: this.get(existing.id), deduplicated: true };
    try {
      this.db.prepare(`INSERT INTO federation_jobs(id,idempotency_key,capability,task_json,state,priority,attempts,max_attempts,created_at,available_at) VALUES(?,?,?,?, 'pending', ?,0,?,?,?)`).run(task.id, key, task.capability, JSON.stringify(task), Number(priority) || 0, Number(maxAttempts) || 1, now, now);
    } catch (error) {
      const raced = this.db.prepare('SELECT id FROM federation_jobs WHERE idempotency_key=?').get(key);
      if (raced) return { job: this.get(raced.id), deduplicated: true };
      throw error;
    }
    return { job: this.get(task.id), deduplicated: false };
  }
  claim(workerId, capabilities = [], { leaseMs = this.defaultLeaseMs, now = Date.now() } = {}) {
    if (!capabilities.length) return null;
    this.db.exec('BEGIN IMMEDIATE');
    try {
      this.#sweepExpiredInTxn(now);
      const marks = capabilities.map(() => '?').join(',');
      const row = this.db.prepare(`SELECT id FROM federation_jobs WHERE state='pending' AND available_at<=? AND capability IN (${marks}) ORDER BY priority DESC, available_at ASC, created_at ASC LIMIT 1`).get(now, ...capabilities);
      if (!row) { this.db.exec('COMMIT'); return null; }
      const token = randomUUID();
      const info = this.db.prepare(`UPDATE federation_jobs SET state='running', attempts=attempts+1, lease_worker=?, lease_token=?, lease_expires_at=?, lease_heartbeat_at=? WHERE id=? AND state='pending'`).run(workerId, token, now + leaseMs, now, row.id);
      if (Number(info.changes) !== 1) throw new Error('claim race detected');
      this.db.exec('COMMIT');
      return this.get(row.id);
    } catch (error) { safeRollback(this.db); throw error; }
  }
  heartbeat(jobId, token, { leaseMs = this.defaultLeaseMs, now = Date.now() } = {}) {
    const info = this.db.prepare(`UPDATE federation_jobs SET lease_expires_at=?, lease_heartbeat_at=? WHERE id=? AND state='running' AND lease_token=?`).run(now + leaseMs, now, jobId, token);
    if (Number(info.changes) !== 1) throw new Error('invalid lease token or job is not leased');
    return this.get(jobId);
  }
  complete(jobId, token, result) {
    const info = this.db.prepare(`UPDATE federation_jobs SET state='succeeded', result_json=?, error_json=NULL, lease_worker=NULL, lease_token=NULL, lease_expires_at=NULL, lease_heartbeat_at=NULL WHERE id=? AND state='running' AND lease_token=?`).run(JSON.stringify(result), jobId, token);
    if (Number(info.changes) !== 1) throw new Error('invalid lease token or job is not leased');
    return this.get(jobId);
  }
  fail(jobId, token, error, { retryDelayMs = 0, now = Date.now(), terminal = false } = {}) {
    this.db.exec('BEGIN IMMEDIATE');
    try {
      const row = this.db.prepare(`SELECT attempts,max_attempts FROM federation_jobs WHERE id=? AND state='running' AND lease_token=?`).get(jobId, token);
      if (!row) throw new Error('invalid lease token or job is not leased');
      const dead = terminal || row.attempts >= row.max_attempts;
      this.db.prepare(`UPDATE federation_jobs SET state=?, error_json=?, available_at=?, lease_worker=NULL, lease_token=NULL, lease_expires_at=NULL, lease_heartbeat_at=NULL WHERE id=?`).run(dead ? 'deadletter' : 'pending', JSON.stringify(normalizeError(error)), dead ? now : now + Math.max(0, retryDelayMs), jobId);
      this.db.exec('COMMIT');
      return this.get(jobId);
    } catch (error2) { safeRollback(this.db); throw error2; }
  }
  sweepExpired(now = Date.now()) {
    this.db.exec('BEGIN IMMEDIATE');
    try { const ids = this.#sweepExpiredInTxn(now); this.db.exec('COMMIT'); return ids; }
    catch (error) { safeRollback(this.db); throw error; }
  }
  #sweepExpiredInTxn(now) {
    const rows = this.db.prepare(`SELECT id,attempts,max_attempts FROM federation_jobs WHERE state='running' AND lease_expires_at<=?`).all(now);
    const err = JSON.stringify({ name: 'LeaseExpired', message: 'worker lease expired' });
    for (const row of rows) this.db.prepare(`UPDATE federation_jobs SET state=?, error_json=?, available_at=?, lease_worker=NULL, lease_token=NULL, lease_expires_at=NULL, lease_heartbeat_at=NULL WHERE id=?`).run(row.attempts >= row.max_attempts ? 'deadletter' : 'pending', err, now, row.id);
    return rows.map((r) => r.id);
  }
  get(jobId) { const row = this.db.prepare('SELECT * FROM federation_jobs WHERE id=?').get(jobId); return row ? mapJob(row) : null; }
  list({ state = null } = {}) { const rows = state ? this.db.prepare('SELECT * FROM federation_jobs WHERE state=? ORDER BY created_at').all(state) : this.db.prepare('SELECT * FROM federation_jobs ORDER BY created_at').all(); return rows.map(mapJob); }
}

export class SqliteResultCache {
  constructor(db, { maxEntries = 10_000, defaultTtlMs = 10 * 60_000 } = {}) { this.db = db; this.maxEntries = maxEntries; this.defaultTtlMs = defaultTtlMs; }
  get(task, now = Date.now()) {
    if (!cacheable(task)) return null;
    const key = task.cacheKey ?? taskFingerprint(task);
    const row = this.db.prepare('SELECT * FROM federation_cache WHERE cache_key=?').get(key);
    if (!row) return null;
    if (row.expires_at <= now) { this.db.prepare('DELETE FROM federation_cache WHERE cache_key=?').run(key); return null; }
    this.db.prepare('UPDATE federation_cache SET hits=hits+1 WHERE cache_key=?').run(key);
    return mapCache({ ...row, hits: Number(row.hits) + 1 });
  }
  set(task, value, { ttlMs = this.defaultTtlMs, now = Date.now() } = {}) {
    if (!cacheable(task)) return null;
    const key = task.cacheKey ?? taskFingerprint(task);
    this.db.prepare('DELETE FROM federation_cache WHERE expires_at<=?').run(now);
    const count = Number(this.db.prepare('SELECT COUNT(*) AS n FROM federation_cache').get().n);
    if (count >= this.maxEntries && !this.db.prepare('SELECT 1 FROM federation_cache WHERE cache_key=?').get(key)) this.db.prepare('DELETE FROM federation_cache WHERE cache_key=(SELECT cache_key FROM federation_cache ORDER BY created_at ASC LIMIT 1)').run();
    const expiresAt = now + Math.max(1, ttlMs);
    this.db.prepare(`INSERT INTO federation_cache(cache_key,task_id,data_class,tenant_id,value_json,created_at,expires_at,hits) VALUES(?,?,?,?,?,?,?,0) ON CONFLICT(cache_key) DO UPDATE SET task_id=excluded.task_id,data_class=excluded.data_class,tenant_id=excluded.tenant_id,value_json=excluded.value_json,created_at=excluded.created_at,expires_at=excluded.expires_at,hits=0`).run(key, task.id, task.dataClass ?? 'public', task.tenantId ?? 'default', JSON.stringify(value), now, expiresAt);
    return { key, taskId: task.id, dataClass: task.dataClass ?? 'public', tenantId: task.tenantId ?? 'default', value: structuredClone(value), createdAt: now, expiresAt, hits: 0 };
  }
  deleteByKey(key) { return Number(this.db.prepare('DELETE FROM federation_cache WHERE cache_key=?').run(key).changes) > 0; }
  stats() { const row = this.db.prepare('SELECT COUNT(*) AS entries, COALESCE(SUM(hits),0) AS hits FROM federation_cache').get(); return { entries: Number(row.entries), hits: Number(row.hits) }; }
}

export class SqliteContributionLedger {
  constructor(db) { this.db = db; }
  record(input) {
    this.db.exec('BEGIN IMMEDIATE');
    try {
      const last = this.db.prepare('SELECT seq,hash FROM federation_ledger ORDER BY seq DESC LIMIT 1').get();
      const core = { id: randomUUID(), seq: Number(last?.seq ?? 0) + 1, ts: new Date().toISOString(), taskId: input.taskId, providerId: input.providerId, consentRef: input.consentRef ?? null, tenantId: input.tenantId ?? 'default', measuredLatencyMs: Math.max(0, Number(input.measuredLatencyMs) || 0), billedCostUsd: Math.max(0, Number(input.billedCostUsd) || 0), inputBytes: Math.max(0, Number(input.inputBytes) || 0), outputBytes: Math.max(0, Number(input.outputBytes) || 0), reportedUsage: input.reportedUsage ? structuredClone(input.reportedUsage) : null, status: input.status ?? 'succeeded', prevHash: last?.hash ?? null };
      const hash = sha256(canonicalize(core));
      this.db.prepare(`INSERT INTO federation_ledger(seq,id,ts,task_id,provider_id,consent_ref,tenant_id,measured_latency_ms,billed_cost_usd,input_bytes,output_bytes,reported_usage_json,status,prev_hash,hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).run(core.seq, core.id, core.ts, core.taskId, core.providerId, core.consentRef, core.tenantId, core.measuredLatencyMs, core.billedCostUsd, core.inputBytes, core.outputBytes, core.reportedUsage ? JSON.stringify(core.reportedUsage) : null, core.status, core.prevHash, hash);
      this.db.exec('COMMIT');
      return { ...core, hash };
    } catch (error) { safeRollback(this.db); throw error; }
  }
  list({ providerId = null, tenantId = null } = {}) { let sql = 'SELECT * FROM federation_ledger WHERE 1=1'; const args = []; if (providerId) { sql += ' AND provider_id=?'; args.push(providerId); } if (tenantId) { sql += ' AND tenant_id=?'; args.push(tenantId); } sql += ' ORDER BY seq'; return this.db.prepare(sql).all(...args).map(mapLedger); }
  summary() { const rows = this.db.prepare(`SELECT provider_id,COUNT(*) tasks,SUM(CASE WHEN status='succeeded' THEN 1 ELSE 0 END) success,SUM(CASE WHEN status='succeeded' THEN 0 ELSE 1 END) failure,SUM(measured_latency_ms) measured_latency_ms,SUM(billed_cost_usd) billed_cost_usd,SUM(input_bytes) input_bytes,SUM(output_bytes) output_bytes FROM federation_ledger GROUP BY provider_id`).all(); return Object.fromEntries(rows.map((r) => [r.provider_id, { tasks: Number(r.tasks), success: Number(r.success), failure: Number(r.failure), measuredLatencyMs: Number(r.measured_latency_ms || 0), billedCostUsd: Number(r.billed_cost_usd || 0), inputBytes: Number(r.input_bytes || 0), outputBytes: Number(r.output_bytes || 0) }])); }
}

export class SqliteAuditLog {
  constructor(db) { this.db = db; }
  async append(type, data) {
    this.db.exec('BEGIN IMMEDIATE');
    try {
      const last = this.db.prepare('SELECT seq,hash FROM federation_audit ORDER BY seq DESC LIMIT 1').get();
      const core = { seq: Number(last?.seq ?? 0) + 1, ts: new Date().toISOString(), type, data: structuredClone(data), prevHash: last?.hash ?? null };
      const hash = sha256(canonicalize(core));
      this.db.prepare('INSERT INTO federation_audit(seq,ts,type,data_json,prev_hash,hash) VALUES(?,?,?,?,?,?)').run(core.seq, core.ts, type, JSON.stringify(core.data), core.prevHash, hash);
      this.db.exec('COMMIT');
      return { ...core, hash };
    } catch (error) { safeRollback(this.db); throw error; }
  }
  list() { return this.db.prepare('SELECT * FROM federation_audit ORDER BY seq').all().map((row) => ({ seq: Number(row.seq), ts: row.ts, type: row.type, data: JSON.parse(row.data_json), prevHash: row.prev_hash, hash: row.hash })); }
}

export class SqliteBudgetGovernor {
  constructor(db, { totalUsd = Infinity, perTenantUsd = {}, perProviderUsd = {} } = {}) { this.db = db; this.totalUsd = Number(totalUsd); this.perTenantUsd = new Map(Object.entries(perTenantUsd).map(([k, v]) => [k, Number(v)])); this.perProviderUsd = new Map(Object.entries(perProviderUsd).map(([k, v]) => [k, Number(v)])); }
  canSpend({ amountUsd = 0, tenantId = 'default', providerId = null } = {}) {
    const amount = Number(amountUsd); if (!Number.isFinite(amount) || amount < 0) return { ok: false, reason: 'invalid-budget-amount' };
    const global = this.#sum(); if (global.spent + global.reserved + amount > this.totalUsd) return { ok: false, reason: 'global-budget-exceeded' };
    const tenant = this.#sum('tenant_id', tenantId); if (tenant.spent + tenant.reserved + amount > (this.perTenantUsd.get(tenantId) ?? Infinity)) return { ok: false, reason: 'tenant-budget-exceeded' };
    if (providerId) { const provider = this.#sum('provider_id', providerId); if (provider.spent + provider.reserved + amount > (this.perProviderUsd.get(providerId) ?? Infinity)) return { ok: false, reason: 'provider-budget-exceeded' }; }
    return { ok: true };
  }
  reserve({ amountUsd = 0, tenantId = 'default', providerId = null, taskId = null } = {}) {
    const amount = Number(amountUsd); if (!Number.isFinite(amount) || amount < 0) throw new Error('budget amount must be >= 0');
    this.db.exec('BEGIN IMMEDIATE');
    try {
      const verdict = this.canSpend({ amountUsd: amount, tenantId, providerId }); if (!verdict.ok) { this.db.exec('ROLLBACK'); return verdict; }
      const id = randomUUID(); const createdAt = new Date().toISOString();
      this.db.prepare(`INSERT INTO federation_budget_reservations(id,task_id,tenant_id,provider_id,reserved_usd,state,created_at) VALUES(?,?,?,?,?,'reserved',?)`).run(id, taskId, tenantId, providerId, amount, createdAt);
      this.db.exec('COMMIT');
      return { ok: true, reservation: { id, amountUsd: amount, tenantId, providerId, taskId, state: 'reserved', createdAt } };
    } catch (error) { safeRollback(this.db); throw error; }
  }
  commit(id, actualUsd = null) {
    this.db.exec('BEGIN IMMEDIATE');
    try {
      const row = this.#active(id); const actual = actualUsd == null ? Number(row.reserved_usd) : Number(actualUsd);
      if (!Number.isFinite(actual) || actual < 0) throw new Error('actualUsd must be >= 0');
      const extra = Math.max(0, actual - Number(row.reserved_usd));
      if (extra > 0) { const verdict = this.canSpend({ amountUsd: extra, tenantId: row.tenant_id, providerId: row.provider_id }); if (!verdict.ok) throw new Error(`actual cost rejected: ${verdict.reason}`); }
      const finishedAt = new Date().toISOString();
      this.db.prepare(`UPDATE federation_budget_reservations SET state='committed',actual_usd=?,finished_at=? WHERE id=?`).run(actual, finishedAt, id);
      this.db.exec('COMMIT');
      return mapReservation({ ...row, state: 'committed', actual_usd: actual, finished_at: finishedAt });
    } catch (error) { safeRollback(this.db); throw error; }
  }
  release(id, reason = 'released') {
    this.db.exec('BEGIN IMMEDIATE');
    try { const row = this.#active(id); const finishedAt = new Date().toISOString(); this.db.prepare(`UPDATE federation_budget_reservations SET state='released',reason=?,finished_at=? WHERE id=?`).run(reason, finishedAt, id); this.db.exec('COMMIT'); return mapReservation({ ...row, state: 'released', reason, finished_at: finishedAt }); }
    catch (error) { safeRollback(this.db); throw error; }
  }
  snapshot() {
    const global = this.#sum();
    const tenantRows = this.db.prepare(`SELECT tenant_id,SUM(CASE WHEN state='committed' THEN actual_usd ELSE 0 END) spent,SUM(CASE WHEN state='reserved' THEN reserved_usd ELSE 0 END) reserved FROM federation_budget_reservations GROUP BY tenant_id`).all();
    const providerRows = this.db.prepare(`SELECT provider_id,SUM(CASE WHEN state='committed' THEN actual_usd ELSE 0 END) spent,SUM(CASE WHEN state='reserved' THEN reserved_usd ELSE 0 END) reserved FROM federation_budget_reservations WHERE provider_id IS NOT NULL GROUP BY provider_id`).all();
    return { limits: { totalUsd: this.totalUsd, perTenantUsd: Object.fromEntries(this.perTenantUsd), perProviderUsd: Object.fromEntries(this.perProviderUsd) }, spent: { totalUsd: global.spent, perTenantUsd: Object.fromEntries(tenantRows.map((r) => [r.tenant_id, Number(r.spent || 0)])), perProviderUsd: Object.fromEntries(providerRows.map((r) => [r.provider_id, Number(r.spent || 0)])) }, reserved: { totalUsd: global.reserved, perTenantUsd: Object.fromEntries(tenantRows.map((r) => [r.tenant_id, Number(r.reserved || 0)])), perProviderUsd: Object.fromEntries(providerRows.map((r) => [r.provider_id, Number(r.reserved || 0)])) } };
  }
  #sum(field = null, value = null) { const where = field ? ` WHERE ${field}=?` : ''; const args = field ? [value] : []; const row = this.db.prepare(`SELECT COALESCE(SUM(CASE WHEN state='committed' THEN actual_usd ELSE 0 END),0) spent,COALESCE(SUM(CASE WHEN state='reserved' THEN reserved_usd ELSE 0 END),0) reserved FROM federation_budget_reservations${where}`).get(...args); return { spent: Number(row.spent), reserved: Number(row.reserved) }; }
  #active(id) { const row = this.db.prepare(`SELECT * FROM federation_budget_reservations WHERE id=? AND state='reserved'`).get(id); if (!row) throw new Error('reservation is not active'); return row; }
}

function mapJob(row) { return { id: row.id, task: JSON.parse(row.task_json), idempotencyKey: row.idempotency_key, state: row.state, priority: Number(row.priority), attempts: Number(row.attempts), maxAttempts: Number(row.max_attempts), createdAt: new Date(row.created_at).toISOString(), availableAt: Number(row.available_at), lease: row.lease_token ? { workerId: row.lease_worker, token: row.lease_token, expiresAt: Number(row.lease_expires_at), lastHeartbeatAt: Number(row.lease_heartbeat_at) } : null, result: row.result_json ? JSON.parse(row.result_json) : null, error: row.error_json ? JSON.parse(row.error_json) : null }; }
function mapCache(row) { return { key: row.cache_key, taskId: row.task_id, dataClass: row.data_class, tenantId: row.tenant_id, value: JSON.parse(row.value_json), createdAt: Number(row.created_at), expiresAt: Number(row.expires_at), hits: Number(row.hits) }; }
function mapLedger(row) { return { seq: Number(row.seq), id: row.id, ts: row.ts, taskId: row.task_id, providerId: row.provider_id, consentRef: row.consent_ref, tenantId: row.tenant_id, measuredLatencyMs: Number(row.measured_latency_ms), billedCostUsd: Number(row.billed_cost_usd), inputBytes: Number(row.input_bytes), outputBytes: Number(row.output_bytes), reportedUsage: row.reported_usage_json ? JSON.parse(row.reported_usage_json) : null, status: row.status, prevHash: row.prev_hash, hash: row.hash }; }
function mapReservation(row) { return { id: row.id, taskId: row.task_id, tenantId: row.tenant_id, providerId: row.provider_id, amountUsd: Number(row.reserved_usd), actualUsd: row.actual_usd == null ? null : Number(row.actual_usd), state: row.state, createdAt: row.created_at, reason: row.reason ?? null }; }
function normalizeError(error) { return error && typeof error === 'object' ? { name: error.name ?? 'Error', message: error.message ?? String(error) } : { name: 'Error', message: String(error) }; }
function cacheable(task) { if (task.sideEffect === true) return false; const cls = task.dataClass ?? 'public'; if (cls === 'public') return task.cachePolicy === 'public'; if (cls === 'internal') return task.cachePolicy === 'tenant'; if (cls === 'private') return task.cachePolicy === 'private-ok'; return false; }
function safeRollback(db) { try { db.exec('ROLLBACK'); } catch {} }
