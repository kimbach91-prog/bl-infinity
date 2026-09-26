const freeze = (v) => Object.freeze(v);
const clone = (v) => JSON.parse(JSON.stringify(v));

export const PLATFORM_FOUNDATION_VERSION = '1.0.0';

export const TENANT_STATES = freeze(['ACTIVE', 'SUSPENDED', 'CLOSED']);
export const PRINCIPAL_KINDS = freeze(['OWNER_USER', 'ORG_USER', 'SERVICE_ACCOUNT', 'WORKLOAD', 'APP']);
export const USAGE_METRICS = freeze([
  'api_requests',
  'input_tokens',
  'output_tokens',
  'compute_ms',
  'storage_bytes',
  'egress_bytes',
  'jobs'
]);

function req(value, name) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`INVALID_${name}`);
  return value.trim();
}

function nonNeg(value, name) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) throw new Error(`INVALID_${name}`);
  return n;
}

function posInt(value, name) {
  const n = Number(value);
  if (!Number.isInteger(n) || n < 1) throw new Error(`INVALID_${name}`);
  return n;
}

function normalizeRegion(value) {
  return req(value || 'GLOBAL', 'REGION').toUpperCase();
}

function normalizePlan(plan = {}) {
  const quotas = {};
  for (const metric of USAGE_METRICS) {
    if (plan.quotas?.[metric] != null) quotas[metric] = nonNeg(plan.quotas[metric], `QUOTA_${metric}`);
  }

  const prices = {};
  for (const metric of USAGE_METRICS) {
    if (plan.prices?.[metric] != null) prices[metric] = nonNeg(plan.prices[metric], `PRICE_${metric}`);
  }

  return freeze({
    plan_id: req(plan.plan_id || 'FREE', 'PLAN_ID'),
    currency: req(plan.currency || 'USD', 'CURRENCY').toUpperCase(),
    quotas: freeze(quotas),
    prices: freeze(prices),
    monthly_credit: nonNeg(plan.monthly_credit || 0, 'MONTHLY_CREDIT')
  });
}

export class TenantRegistry {
  constructor() {
    this.tenants = new Map();
    this.principals = new Map();
  }

  createTenant({
    tenant_id,
    org_id,
    name,
    region = 'GLOBAL',
    plan,
    data_residency = null,
    labels = {}
  }) {
    const id = req(tenant_id, 'TENANT_ID');
    if (this.tenants.has(id)) throw new Error('TENANT_EXISTS');

    const tenant = freeze({
      tenant_id: id,
      org_id: req(org_id || id, 'ORG_ID'),
      name: req(name || id, 'TENANT_NAME'),
      state: 'ACTIVE',
      region: normalizeRegion(region),
      data_residency: data_residency ? normalizeRegion(data_residency) : null,
      plan: normalizePlan(plan),
      labels: freeze({ ...labels }),
      isolation_key: `tenant://${id}`
    });
    this.tenants.set(id, tenant);
    return tenant;
  }

  updateTenantState(tenant_id, state) {
    const id = req(tenant_id, 'TENANT_ID');
    const current = this.tenants.get(id);
    if (!current) throw new Error('TENANT_NOT_FOUND');
    const next = req(state, 'TENANT_STATE').toUpperCase();
    if (!TENANT_STATES.includes(next)) throw new Error('TENANT_STATE_NOT_ALLOWED');
    const updated = freeze({ ...current, state: next });
    this.tenants.set(id, updated);
    return updated;
  }

  registerPrincipal({
    principal_id,
    tenant_id,
    kind,
    roles = [],
    scopes = [],
    credential_ref = null,
    region = null,
    active = true
  }) {
    const pid = req(principal_id, 'PRINCIPAL_ID');
    if (this.principals.has(pid)) throw new Error('PRINCIPAL_EXISTS');
    const tid = req(tenant_id, 'TENANT_ID');
    const tenant = this.tenants.get(tid);
    if (!tenant) throw new Error('TENANT_NOT_FOUND');

    const pk = req(kind, 'PRINCIPAL_KIND').toUpperCase();
    if (!PRINCIPAL_KINDS.includes(pk)) throw new Error('PRINCIPAL_KIND_NOT_ALLOWED');

    const p = freeze({
      principal_id: pid,
      tenant_id: tid,
      kind: pk,
      roles: freeze([...new Set(roles.map((x) => req(x, 'ROLE')))]),
      scopes: freeze([...new Set(scopes.map((x) => req(x, 'SCOPE')))]),
      credential_ref: credential_ref ? req(credential_ref, 'CREDENTIAL_REF') : null,
      region: region ? normalizeRegion(region) : tenant.region,
      active: active === true
    });
    this.principals.set(pid, p);
    return p;
  }

  authorize({
    principal_id,
    tenant_id,
    required_scope = null,
    required_role = null,
    target_region = null
  }) {
    const pid = req(principal_id, 'PRINCIPAL_ID');
    const tid = req(tenant_id, 'TENANT_ID');
    const principal = this.principals.get(pid);
    const tenant = this.tenants.get(tid);

    if (!principal || !principal.active) return freeze({ allowed: false, reason: 'PRINCIPAL_INACTIVE_OR_UNKNOWN' });
    if (!tenant || tenant.state !== 'ACTIVE') return freeze({ allowed: false, reason: 'TENANT_INACTIVE_OR_UNKNOWN' });
    if (principal.tenant_id !== tid) return freeze({ allowed: false, reason: 'CROSS_TENANT_DENIED' });

    if (required_scope && !principal.scopes.includes(required_scope) && !principal.scopes.includes('*')) {
      return freeze({ allowed: false, reason: 'SCOPE_DENIED' });
    }
    if (required_role && !principal.roles.includes(required_role)) {
      return freeze({ allowed: false, reason: 'ROLE_DENIED' });
    }

    if (target_region && tenant.data_residency) {
      const tr = normalizeRegion(target_region);
      if (tr !== tenant.data_residency) return freeze({ allowed: false, reason: 'DATA_RESIDENCY_DENIED' });
    }

    return freeze({
      allowed: true,
      tenant_id: tid,
      principal_id: pid,
      isolation_key: tenant.isolation_key,
      region: target_region ? normalizeRegion(target_region) : principal.region
    });
  }
}

export class UsageLedger {
  constructor() {
    this.events = new Map();
    this.totals = new Map();
  }

  append({
    event_id,
    tenant_id,
    metric,
    quantity,
    source_ref,
    workload_family = 'GENERAL',
    occurred_at = null,
    metadata = {}
  }) {
    const eid = req(event_id, 'EVENT_ID');
    if (this.events.has(eid)) return this.events.get(eid);

    const tid = req(tenant_id, 'TENANT_ID');
    const m = req(metric, 'METRIC');
    if (!USAGE_METRICS.includes(m)) throw new Error('METRIC_NOT_ALLOWED');

    const q = nonNeg(quantity, 'QUANTITY');
    const event = freeze({
      event_id: eid,
      tenant_id: tid,
      metric: m,
      quantity: q,
      source_ref: req(source_ref, 'SOURCE_REF'),
      workload_family: req(workload_family, 'WORKLOAD_FAMILY'),
      occurred_at: occurred_at || new Date().toISOString(),
      metadata: freeze({ ...metadata })
    });
    this.events.set(eid, event);

    const key = `${tid}::${m}`;
    this.totals.set(key, (this.totals.get(key) || 0) + q);
    return event;
  }

  total(tenant_id, metric) {
    return this.totals.get(`${req(tenant_id, 'TENANT_ID')}::${req(metric, 'METRIC')}`) || 0;
  }

  eventsForTenant(tenant_id) {
    const tid = req(tenant_id, 'TENANT_ID');
    return [...this.events.values()].filter((e) => e.tenant_id === tid);
  }
}

export class QuotaEngine {
  constructor({ tenantRegistry, usageLedger }) {
    this.tenants = tenantRegistry;
    this.usage = usageLedger;
  }

  check({ tenant_id, metric, requested_quantity }) {
    const tenant = this.tenants.tenants.get(req(tenant_id, 'TENANT_ID'));
    if (!tenant || tenant.state !== 'ACTIVE') {
      return freeze({ allowed: false, reason: 'TENANT_INACTIVE_OR_UNKNOWN' });
    }

    const m = req(metric, 'METRIC');
    if (!USAGE_METRICS.includes(m)) throw new Error('METRIC_NOT_ALLOWED');
    const qty = nonNeg(requested_quantity, 'REQUESTED_QUANTITY');
    const limit = tenant.plan.quotas[m];

    if (limit == null) return freeze({ allowed: true, unlimited: true, used: this.usage.total(tenant.tenant_id, m) });

    const used = this.usage.total(tenant.tenant_id, m);
    const remaining = Math.max(0, limit - used);
    if (qty > remaining) {
      return freeze({
        allowed: false,
        reason: 'QUOTA_EXCEEDED',
        metric: m,
        limit,
        used,
        requested: qty,
        remaining
      });
    }
    return freeze({ allowed: true, metric: m, limit, used, requested: qty, remaining_after: remaining - qty });
  }
}

export class BillingLedger {
  constructor({ tenantRegistry, usageLedger }) {
    this.tenants = tenantRegistry;
    this.usage = usageLedger;
    this.credits = new Map();
    this.adjustments = [];
  }

  addCredit({ tenant_id, amount, reason, receipt_ref }) {
    const tid = req(tenant_id, 'TENANT_ID');
    const value = nonNeg(amount, 'CREDIT_AMOUNT');
    req(reason, 'CREDIT_REASON');
    req(receipt_ref, 'RECEIPT_REF');

    this.credits.set(tid, (this.credits.get(tid) || 0) + value);
    const row = freeze({ tenant_id: tid, amount: value, reason, receipt_ref });
    this.adjustments.push(row);
    return row;
  }

  previewInvoice(tenant_id) {
    const tid = req(tenant_id, 'TENANT_ID');
    const tenant = this.tenants.tenants.get(tid);
    if (!tenant) throw new Error('TENANT_NOT_FOUND');

    const lines = [];
    let subtotal = 0;
    for (const metric of USAGE_METRICS) {
      const qty = this.usage.total(tid, metric);
      const unit_price = tenant.plan.prices[metric] || 0;
      if (!qty && !unit_price) continue;
      const amount = qty * unit_price;
      subtotal += amount;
      lines.push(freeze({ metric, quantity: qty, unit_price, amount }));
    }

    const credits = tenant.plan.monthly_credit + (this.credits.get(tid) || 0);
    const total = Math.max(0, subtotal - credits);
    return freeze({
      tenant_id: tid,
      currency: tenant.plan.currency,
      lines: freeze(lines),
      subtotal,
      credits,
      total,
      settlement_required: total > 0
    });
  }
}

export class EventOutbox {
  constructor({ max_attempts = 5 } = {}) {
    this.max_attempts = posInt(max_attempts, 'MAX_ATTEMPTS');
    this.subscriptions = new Map();
    this.events = new Map();
    this.sequence = 0;
  }

  subscribe({
    subscription_id,
    tenant_id,
    event_types = ['*'],
    endpoint_ref,
    signing_secret_ref = null,
    active = true
  }) {
    const id = req(subscription_id, 'SUBSCRIPTION_ID');
    if (this.subscriptions.has(id)) throw new Error('SUBSCRIPTION_EXISTS');
    const s = freeze({
      subscription_id: id,
      tenant_id: req(tenant_id, 'TENANT_ID'),
      event_types: freeze([...new Set(event_types.map((x) => req(x, 'EVENT_TYPE')))]),
      endpoint_ref: req(endpoint_ref, 'ENDPOINT_REF'),
      signing_secret_ref: signing_secret_ref ? req(signing_secret_ref, 'SIGNING_SECRET_REF') : null,
      active: active === true
    });
    this.subscriptions.set(id, s);
    return s;
  }

  publish({ event_id, tenant_id, type, payload, source_ref }) {
    const id = req(event_id, 'EVENT_ID');
    if (this.events.has(id)) return this.events.get(id);
    const event = freeze({
      event_id: id,
      tenant_id: req(tenant_id, 'TENANT_ID'),
      type: req(type, 'EVENT_TYPE'),
      payload: freeze(clone(payload || {})),
      source_ref: req(source_ref, 'SOURCE_REF'),
      sequence: ++this.sequence,
      deliveries: freeze([])
    });
    this.events.set(id, event);
    return event;
  }

  eligibleSubscriptions(event_id) {
    const e = this.events.get(req(event_id, 'EVENT_ID'));
    if (!e) throw new Error('EVENT_NOT_FOUND');
    return [...this.subscriptions.values()].filter((s) =>
      s.active &&
      s.tenant_id === e.tenant_id &&
      (s.event_types.includes('*') || s.event_types.includes(e.type))
    );
  }

  planDelivery({ event_id, subscription_id, attempt = 1 }) {
    const e = this.events.get(req(event_id, 'EVENT_ID'));
    const s = this.subscriptions.get(req(subscription_id, 'SUBSCRIPTION_ID'));
    if (!e || !s) throw new Error('EVENT_OR_SUBSCRIPTION_NOT_FOUND');
    if (e.tenant_id !== s.tenant_id) throw new Error('CROSS_TENANT_DELIVERY_DENIED');
    const a = posInt(attempt, 'ATTEMPT');

    if (a > this.max_attempts) {
      return freeze({
        state: 'DEAD_LETTER',
        event_id: e.event_id,
        subscription_id: s.subscription_id,
        attempts: a - 1
      });
    }

    return freeze({
      state: 'READY',
      event_id: e.event_id,
      tenant_id: e.tenant_id,
      type: e.type,
      sequence: e.sequence,
      endpoint_ref: s.endpoint_ref,
      signing_secret_ref: s.signing_secret_ref,
      attempt: a,
      idempotency_key: `${e.event_id}::${s.subscription_id}`
    });
  }
}

export class SLOTracker {
  constructor({ availability_target = 0.999, latency_target_ms = 1000 } = {}) {
    this.availability_target = Number(availability_target);
    this.latency_target_ms = nonNeg(latency_target_ms, 'LATENCY_TARGET_MS');
    if (!(this.availability_target > 0 && this.availability_target <= 1)) throw new Error('INVALID_AVAILABILITY_TARGET');
    this.samples = new Map();
  }

  record({ tenant_id, service, success, latency_ms }) {
    const tid = req(tenant_id, 'TENANT_ID');
    const svc = req(service, 'SERVICE');
    const latency = nonNeg(latency_ms, 'LATENCY_MS');
    const key = `${tid}::${svc}`;
    const list = this.samples.get(key) || [];
    list.push(freeze({ success: success === true, latency_ms: latency }));
    this.samples.set(key, list);
  }

  summarize({ tenant_id, service }) {
    const key = `${req(tenant_id, 'TENANT_ID')}::${req(service, 'SERVICE')}`;
    const list = this.samples.get(key) || [];
    if (!list.length) return freeze({ sample_count: 0, status: 'NO_DATA' });

    const successes = list.filter((s) => s.success).length;
    const availability = successes / list.length;
    const sorted = list.map((s) => s.latency_ms).sort((a, b) => a - b);
    const p95 = sorted[Math.min(sorted.length - 1, Math.ceil(sorted.length * 0.95) - 1)];
    const allowed_failures = list.length * (1 - this.availability_target);
    const failures = list.length - successes;
    const error_budget_remaining = Math.max(0, allowed_failures - failures);

    return freeze({
      sample_count: list.length,
      availability,
      availability_target: this.availability_target,
      p95_latency_ms: p95,
      latency_target_ms: this.latency_target_ms,
      availability_met: availability >= this.availability_target,
      latency_met: p95 <= this.latency_target_ms,
      error_budget_remaining,
      status: availability >= this.availability_target && p95 <= this.latency_target_ms ? 'HEALTHY' : 'SLO_AT_RISK'
    });
  }
}

export class PlatformRuntimeFoundation {
  constructor({ availability_target = 0.999, latency_target_ms = 1000, webhook_max_attempts = 5 } = {}) {
    this.tenants = new TenantRegistry();
    this.usage = new UsageLedger();
    this.quotas = new QuotaEngine({ tenantRegistry: this.tenants, usageLedger: this.usage });
    this.billing = new BillingLedger({ tenantRegistry: this.tenants, usageLedger: this.usage });
    this.events = new EventOutbox({ max_attempts: webhook_max_attempts });
    this.slo = new SLOTracker({ availability_target, latency_target_ms });
  }

  authorizeAndReserve({
    principal_id,
    tenant_id,
    scope,
    role = null,
    target_region = null,
    metric,
    quantity
  }) {
    const auth = this.tenants.authorize({
      principal_id,
      tenant_id,
      required_scope: scope,
      required_role: role,
      target_region
    });
    if (!auth.allowed) return auth;

    const quota = this.quotas.check({
      tenant_id,
      metric,
      requested_quantity: quantity
    });
    if (!quota.allowed) return quota;

    return freeze({
      allowed: true,
      tenant_id,
      principal_id,
      scope,
      metric,
      quantity,
      isolation_key: auth.isolation_key,
      region: auth.region,
      quota
    });
  }

  commitUsage({
    reservation,
    event_id,
    source_ref,
    workload_family = 'GENERAL',
    metadata = {}
  }) {
    if (!reservation?.allowed) throw new Error('RESERVATION_NOT_ALLOWED');
    return this.usage.append({
      event_id,
      tenant_id: reservation.tenant_id,
      metric: reservation.metric,
      quantity: reservation.quantity,
      source_ref,
      workload_family,
      metadata
    });
  }
}
