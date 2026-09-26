import { readFile } from 'node:fs/promises';

const METRICS = new Set([
  'api_requests','input_tokens','output_tokens','compute_ms','storage_bytes','egress_bytes','jobs'
]);
const TENANT_STATES = new Set(['ACTIVE','SUSPENDED','CLOSED']);
const PRINCIPAL_KINDS = new Set(['OWNER_USER','ORG_USER','SERVICE_ACCOUNT','WORKLOAD','APP']);

function req(value, name) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`INVALID_${name}`);
  return value.trim();
}
function nonNeg(value, name) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) throw new Error(`INVALID_${name}`);
  return n;
}
function json(value) { return JSON.stringify(value ?? {}); }

export async function loadPlatformPostgresSchema() {
  return readFile(new URL('./postgres-schema.sql', import.meta.url), 'utf8');
}

export async function openPostgresPlatformRuntime({
  connectionString = process.env.BL_POSTGRES_URL,
  pool = null,
  applySchema = false,
  poolOptions = {},
} = {}) {
  let ownsPool = false;
  if (!pool) {
    if (!connectionString) throw new Error('Postgres connectionString or pool is required');
    const { Pool } = await import('pg');
    pool = new Pool({
      connectionString,
      application_name: 'deus-platform-runtime',
      max: Number(poolOptions.max ?? 10),
      idleTimeoutMillis: Number(poolOptions.idleTimeoutMillis ?? 30_000),
      connectionTimeoutMillis: Number(poolOptions.connectionTimeoutMillis ?? 10_000),
      ...poolOptions,
    });
    ownsPool = true;
  }
  if (applySchema) await pool.query(await loadPlatformPostgresSchema());
  else await pool.query('SELECT 1');
  return {
    runtime: new PostgresPlatformRuntime(pool),
    pool,
    close: async () => { if (ownsPool) await pool.end(); },
  };
}

export class PostgresPlatformRuntime {
  constructor(pool) {
    if (!pool?.query) throw new Error('pool with query() is required');
    this.pool = pool;
  }

  async upsertTenant({
    tenant_id, org_id, name, state = 'ACTIVE', region = 'GLOBAL',
    data_residency = null, plan = {}, labels = {},
  }) {
    const tenantId = req(tenant_id, 'TENANT_ID');
    const st = req(state, 'TENANT_STATE').toUpperCase();
    if (!TENANT_STATES.has(st)) throw new Error('TENANT_STATE_NOT_ALLOWED');
    const result = await this.pool.query(`
      INSERT INTO deus_platform_tenants
        (tenant_id,org_id,name,state,region,data_residency,plan,labels,updated_at)
      VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,now())
      ON CONFLICT(tenant_id) DO UPDATE SET
        org_id=EXCLUDED.org_id,name=EXCLUDED.name,state=EXCLUDED.state,
        region=EXCLUDED.region,data_residency=EXCLUDED.data_residency,
        plan=EXCLUDED.plan,labels=EXCLUDED.labels,updated_at=now()
      RETURNING *
    `, [
      tenantId, req(org_id || tenantId, 'ORG_ID'), req(name || tenantId, 'TENANT_NAME'),
      st, req(region, 'REGION').toUpperCase(),
      data_residency ? req(data_residency, 'DATA_RESIDENCY').toUpperCase() : null,
      json(plan), json(labels),
    ]);
    return mapTenant(result.rows[0]);
  }

  async setTenantState(tenantId, state) {
    const st = req(state, 'TENANT_STATE').toUpperCase();
    if (!TENANT_STATES.has(st)) throw new Error('TENANT_STATE_NOT_ALLOWED');
    const result = await this.pool.query(
      'UPDATE deus_platform_tenants SET state=$1,updated_at=now() WHERE tenant_id=$2 RETURNING *',
      [st, req(tenantId, 'TENANT_ID')],
    );
    if (result.rowCount !== 1) throw new Error('TENANT_NOT_FOUND');
    return mapTenant(result.rows[0]);
  }

  async upsertPrincipal({
    principal_id, tenant_id, kind, roles = [], scopes = [],
    credential_ref = null, region = null, active = true,
  }) {
    const k = req(kind, 'PRINCIPAL_KIND').toUpperCase();
    if (!PRINCIPAL_KINDS.has(k)) throw new Error('PRINCIPAL_KIND_NOT_ALLOWED');
    const result = await this.pool.query(`
      INSERT INTO deus_platform_principals
        (principal_id,tenant_id,kind,roles,scopes,credential_ref,region,active,updated_at)
      VALUES($1,$2,$3,$4::text[],$5::text[],$6,$7,$8,now())
      ON CONFLICT(principal_id) DO UPDATE SET
        tenant_id=EXCLUDED.tenant_id,kind=EXCLUDED.kind,roles=EXCLUDED.roles,
        scopes=EXCLUDED.scopes,credential_ref=EXCLUDED.credential_ref,
        region=EXCLUDED.region,active=EXCLUDED.active,updated_at=now()
      RETURNING *
    `, [
      req(principal_id, 'PRINCIPAL_ID'), req(tenant_id, 'TENANT_ID'), k,
      [...new Set(roles.map((x) => req(x, 'ROLE')))],
      [...new Set(scopes.map((x) => req(x, 'SCOPE')))],
      credential_ref ? req(credential_ref, 'CREDENTIAL_REF') : null,
      region ? req(region, 'REGION').toUpperCase() : null,
      active === true,
    ]);
    return mapPrincipal(result.rows[0]);
  }

  async authorize({
    principal_id, tenant_id, required_scope = null,
    required_role = null, target_region = null,
  }) {
    const result = await this.pool.query(`
      SELECT
        p.principal_id,p.tenant_id,p.roles,p.scopes,p.active,p.region AS principal_region,
        t.state AS tenant_state,t.region AS tenant_region,t.data_residency,t.plan
      FROM deus_platform_principals p
      JOIN deus_platform_tenants t ON t.tenant_id=p.tenant_id
      WHERE p.principal_id=$1 AND p.tenant_id=$2
      LIMIT 1
    `, [req(principal_id, 'PRINCIPAL_ID'), req(tenant_id, 'TENANT_ID')]);
    if (result.rowCount !== 1) return { allowed: false, reason: 'CROSS_TENANT_OR_PRINCIPAL_DENIED' };
    const row = result.rows[0];
    if (!row.active || row.tenant_state !== 'ACTIVE') return { allowed: false, reason: 'PRINCIPAL_OR_TENANT_INACTIVE' };
    if (required_scope && !row.scopes.includes(required_scope) && !row.scopes.includes('*')) return { allowed: false, reason: 'SCOPE_DENIED' };
    if (required_role && !row.roles.includes(required_role)) return { allowed: false, reason: 'ROLE_DENIED' };
    if (target_region && row.data_residency && req(target_region, 'TARGET_REGION').toUpperCase() !== row.data_residency) {
      return { allowed: false, reason: 'DATA_RESIDENCY_DENIED' };
    }
    return {
      allowed: true,
      principal_id: row.principal_id,
      tenant_id: row.tenant_id,
      region: target_region ? req(target_region, 'TARGET_REGION').toUpperCase() : row.principal_region || row.tenant_region,
      isolation_key: `tenant://${row.tenant_id}`,
    };
  }

  async recordUsage({
    event_id, tenant_id, metric, quantity, source_ref,
    workload_family = 'GENERAL', metadata = {}, occurred_at = null,
  }) {
    const m = req(metric, 'METRIC');
    if (!METRICS.has(m)) throw new Error('METRIC_NOT_ALLOWED');
    const result = await this.pool.query(`
      INSERT INTO deus_platform_usage_events
        (event_id,tenant_id,metric,quantity,source_ref,workload_family,metadata,occurred_at)
      VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,COALESCE($8::timestamptz,now()))
      ON CONFLICT(event_id) DO NOTHING
      RETURNING *
    `, [
      req(event_id, 'EVENT_ID'), req(tenant_id, 'TENANT_ID'), m, nonNeg(quantity, 'QUANTITY'),
      req(source_ref, 'SOURCE_REF'), req(workload_family, 'WORKLOAD_FAMILY'), json(metadata), occurred_at,
    ]);
    if (result.rowCount === 1) return { event: mapUsage(result.rows[0]), deduplicated: false };
    const existing = await this.pool.query('SELECT * FROM deus_platform_usage_events WHERE event_id=$1', [event_id]);
    if (existing.rowCount !== 1) throw new Error('USAGE_IDEMPOTENCY_LOOKUP_FAILED');
    return { event: mapUsage(existing.rows[0]), deduplicated: true };
  }

  async usageTotal(tenantId, metric) {
    const m = req(metric, 'METRIC');
    if (!METRICS.has(m)) throw new Error('METRIC_NOT_ALLOWED');
    const result = await this.pool.query(
      'SELECT COALESCE(SUM(quantity),0)::text AS total FROM deus_platform_usage_events WHERE tenant_id=$1 AND metric=$2',
      [req(tenantId, 'TENANT_ID'), m],
    );
    return Number(result.rows[0].total);
  }

  async quotaCheck({ tenant_id, metric, requested_quantity }) {
    const m = req(metric, 'METRIC');
    if (!METRICS.has(m)) throw new Error('METRIC_NOT_ALLOWED');
    const tenant = await this.pool.query('SELECT state,plan FROM deus_platform_tenants WHERE tenant_id=$1', [req(tenant_id, 'TENANT_ID')]);
    if (tenant.rowCount !== 1 || tenant.rows[0].state !== 'ACTIVE') return { allowed: false, reason: 'TENANT_INACTIVE_OR_UNKNOWN' };
    const plan = tenant.rows[0].plan || {};
    const limit = plan.quotas?.[m];
    const requested = nonNeg(requested_quantity, 'REQUESTED_QUANTITY');
    const used = await this.usageTotal(tenant_id, m);
    if (limit == null) return { allowed: true, unlimited: true, used };
    const numericLimit = Number(limit);
    const remaining = Math.max(0, numericLimit - used);
    if (requested > remaining) return { allowed: false, reason: 'QUOTA_EXCEEDED', metric: m, limit: numericLimit, used, requested, remaining };
    return { allowed: true, metric: m, limit: numericLimit, used, requested, remaining_after: remaining - requested };
  }

  async addCredit({ credit_id, tenant_id, amount, reason, receipt_ref }) {
    const result = await this.pool.query(`
      INSERT INTO deus_platform_billing_credits(credit_id,tenant_id,amount,reason,receipt_ref)
      VALUES($1,$2,$3,$4,$5)
      ON CONFLICT(credit_id) DO NOTHING
      RETURNING *
    `, [
      req(credit_id, 'CREDIT_ID'), req(tenant_id, 'TENANT_ID'), nonNeg(amount, 'AMOUNT'),
      req(reason, 'REASON'), req(receipt_ref, 'RECEIPT_REF'),
    ]);
    if (result.rowCount === 1) return { credit: result.rows[0], deduplicated: false };
    const existing = await this.pool.query('SELECT * FROM deus_platform_billing_credits WHERE credit_id=$1', [credit_id]);
    return { credit: existing.rows[0], deduplicated: true };
  }

  async invoicePreview(tenantId) {
    const tid = req(tenantId, 'TENANT_ID');
    const tenant = await this.pool.query('SELECT plan FROM deus_platform_tenants WHERE tenant_id=$1', [tid]);
    if (tenant.rowCount !== 1) throw new Error('TENANT_NOT_FOUND');
    const plan = tenant.rows[0].plan || {};
    const usage = await this.pool.query(`
      SELECT metric,COALESCE(SUM(quantity),0)::text AS quantity
      FROM deus_platform_usage_events WHERE tenant_id=$1 GROUP BY metric
    `, [tid]);
    const credit = await this.pool.query(
      'SELECT COALESCE(SUM(amount),0)::text AS credits FROM deus_platform_billing_credits WHERE tenant_id=$1',
      [tid],
    );
    const lines = usage.rows.map((r) => {
      const quantity = Number(r.quantity);
      const unit_price = Number(plan.prices?.[r.metric] || 0);
      return { metric: r.metric, quantity, unit_price, amount: quantity * unit_price };
    });
    const subtotal = lines.reduce((s, x) => s + x.amount, 0);
    const credits = Number(plan.monthly_credit || 0) + Number(credit.rows[0].credits || 0);
    return {
      tenant_id: tid,
      currency: plan.currency || 'USD',
      lines,
      subtotal,
      credits,
      total: Math.max(0, subtotal - credits),
      settlement_required: subtotal > credits,
    };
  }

  async upsertWebhookSubscription({
    subscription_id, tenant_id, event_types = ['*'], endpoint_ref,
    signing_secret_ref = null, active = true,
  }) {
    const result = await this.pool.query(`
      INSERT INTO deus_platform_webhook_subscriptions
        (subscription_id,tenant_id,event_types,endpoint_ref,signing_secret_ref,active,updated_at)
      VALUES($1,$2,$3::text[],$4,$5,$6,now())
      ON CONFLICT(subscription_id) DO UPDATE SET
        tenant_id=EXCLUDED.tenant_id,event_types=EXCLUDED.event_types,
        endpoint_ref=EXCLUDED.endpoint_ref,signing_secret_ref=EXCLUDED.signing_secret_ref,
        active=EXCLUDED.active,updated_at=now()
      RETURNING *
    `, [
      req(subscription_id, 'SUBSCRIPTION_ID'), req(tenant_id, 'TENANT_ID'),
      [...new Set(event_types.map((x) => req(x, 'EVENT_TYPE')))],
      req(endpoint_ref, 'ENDPOINT_REF'),
      signing_secret_ref ? req(signing_secret_ref, 'SIGNING_SECRET_REF') : null,
      active === true,
    ]);
    return result.rows[0];
  }

  async publishEvent({ event_id, tenant_id, type, payload = {}, source_ref }) {
    const result = await this.pool.query(`
      INSERT INTO deus_platform_outbox(event_id,tenant_id,type,payload,source_ref)
      VALUES($1,$2,$3,$4::jsonb,$5)
      ON CONFLICT(event_id) DO NOTHING
      RETURNING *
    `, [
      req(event_id, 'EVENT_ID'), req(tenant_id, 'TENANT_ID'), req(type, 'EVENT_TYPE'),
      json(payload), req(source_ref, 'SOURCE_REF'),
    ]);
    const event = result.rowCount === 1
      ? result.rows[0]
      : (await this.pool.query('SELECT * FROM deus_platform_outbox WHERE event_id=$1', [event_id])).rows[0];
    await this.pool.query(`
      INSERT INTO deus_platform_webhook_deliveries(event_id,subscription_id)
      SELECT $1,s.subscription_id
      FROM deus_platform_webhook_subscriptions s
      WHERE s.tenant_id=$2 AND s.active=true
        AND ('*'=ANY(s.event_types) OR $3=ANY(s.event_types))
      ON CONFLICT(event_id,subscription_id) DO NOTHING
    `, [event.event_id, event.tenant_id, event.type]);
    return event;
  }

  async pendingWebhookDeliveries({ tenant_id = null, limit = 100 } = {}) {
    const lim = Math.max(1, Math.min(1000, Number(limit) || 100));
    const result = tenant_id
      ? await this.pool.query(`
          SELECT d.*,o.tenant_id,o.type,o.payload,o.source_ref,o.sequence,
                 s.endpoint_ref,s.signing_secret_ref
          FROM deus_platform_webhook_deliveries d
          JOIN deus_platform_outbox o ON o.event_id=d.event_id
          JOIN deus_platform_webhook_subscriptions s ON s.subscription_id=d.subscription_id
          WHERE d.state='PENDING' AND o.tenant_id=$1
          ORDER BY o.sequence LIMIT $2
        `, [req(tenant_id, 'TENANT_ID'), lim])
      : await this.pool.query(`
          SELECT d.*,o.tenant_id,o.type,o.payload,o.source_ref,o.sequence,
                 s.endpoint_ref,s.signing_secret_ref
          FROM deus_platform_webhook_deliveries d
          JOIN deus_platform_outbox o ON o.event_id=d.event_id
          JOIN deus_platform_webhook_subscriptions s ON s.subscription_id=d.subscription_id
          WHERE d.state='PENDING'
          ORDER BY o.sequence LIMIT $1
        `, [lim]);
    return result.rows;
  }

  async recordSloSample({ tenant_id, service, success, latency_ms, trace_ref = null, observed_at = null }) {
    const result = await this.pool.query(`
      INSERT INTO deus_platform_slo_samples(tenant_id,service,success,latency_ms,trace_ref,observed_at)
      VALUES($1,$2,$3,$4,$5,COALESCE($6::timestamptz,now()))
      RETURNING *
    `, [
      req(tenant_id, 'TENANT_ID'), req(service, 'SERVICE'), success === true,
      nonNeg(latency_ms, 'LATENCY_MS'), trace_ref ? req(trace_ref, 'TRACE_REF') : null, observed_at,
    ]);
    return result.rows[0];
  }

  async summarizeSlo({ tenant_id, service, since = null, availability_target = 0.999, latency_target_ms = 1000 }) {
    const target = Number(availability_target);
    if (!(target > 0 && target <= 1)) throw new Error('INVALID_AVAILABILITY_TARGET');
    const latencyTarget = nonNeg(latency_target_ms, 'LATENCY_TARGET_MS');
    const params = [req(tenant_id, 'TENANT_ID'), req(service, 'SERVICE')];
    let where = 'tenant_id=$1 AND service=$2';
    if (since) { params.push(since); where += ` AND observed_at >= $${params.length}::timestamptz`; }
    const result = await this.pool.query(`
      SELECT
        COUNT(*)::bigint AS samples,
        COUNT(*) FILTER (WHERE success)::bigint AS success_count,
        COALESCE(percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms),0)::text AS p95
      FROM deus_platform_slo_samples WHERE ${where}
    `, params);
    const samples = Number(result.rows[0].samples);
    if (!samples) return { sample_count: 0, status: 'NO_DATA' };
    const successCount = Number(result.rows[0].success_count);
    const availability = successCount / samples;
    const p95 = Number(result.rows[0].p95);
    const allowedFailures = samples * (1 - target);
    const failures = samples - successCount;
    return {
      sample_count: samples,
      availability,
      availability_target: target,
      p95_latency_ms: p95,
      latency_target_ms: latencyTarget,
      availability_met: availability >= target,
      latency_met: p95 <= latencyTarget,
      error_budget_remaining: Math.max(0, allowedFailures - failures),
      status: availability >= target && p95 <= latencyTarget ? 'HEALTHY' : 'SLO_AT_RISK',
    };
  }
}

function mapTenant(r) {
  return {
    tenant_id: r.tenant_id, org_id: r.org_id, name: r.name, state: r.state,
    region: r.region, data_residency: r.data_residency, plan: r.plan, labels: r.labels,
  };
}
function mapPrincipal(r) {
  return {
    principal_id: r.principal_id, tenant_id: r.tenant_id, kind: r.kind,
    roles: r.roles, scopes: r.scopes, credential_ref: r.credential_ref,
    region: r.region, active: r.active,
  };
}
function mapUsage(r) {
  return {
    event_id: r.event_id, tenant_id: r.tenant_id, metric: r.metric,
    quantity: Number(r.quantity), source_ref: r.source_ref,
    workload_family: r.workload_family, metadata: r.metadata,
    occurred_at: r.occurred_at instanceof Date ? r.occurred_at.toISOString() : r.occurred_at,
  };
}
