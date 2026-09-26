import crypto from 'node:crypto';

export const DATA_STATES = Object.freeze(['ACTIVE', 'TOMBSTONED', 'PURGED']);
export const DELETE_MODES = Object.freeze(['SOFT_THEN_PURGE', 'IMMEDIATE_PURGE_WHEN_ALLOWED']);
export const DATA_CLASSES = Object.freeze(['BL-S0', 'BL-S1', 'BL-S2', 'SEALED']);

function req(v, name) {
  if (typeof v !== 'string' || !v.trim()) throw new Error(`INVALID_${name}`);
  return v.trim();
}
function nonNegInt(v, name) {
  const n = Number(v);
  if (!Number.isInteger(n) || n < 0) throw new Error(`INVALID_${name}`);
  return n;
}
function iso(v, name) {
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) throw new Error(`INVALID_${name}`);
  return d.toISOString();
}
function digest(v) {
  return crypto.createHash('sha256').update(typeof v === 'string' ? v : JSON.stringify(v)).digest('hex');
}

export class DataPolicyRegistry {
  constructor() {
    this.policies = new Map();
  }

  register({
    policy_id,
    tenant_id,
    retention_days = 30,
    deletion_grace_days = 7,
    region = 'GLOBAL',
    export_allowed = true,
    training_use_allowed = false,
    delete_mode = 'SOFT_THEN_PURGE',
    legal_hold_default = false
  }) {
    const id = req(policy_id, 'POLICY_ID');
    if (this.policies.has(id)) throw new Error('POLICY_EXISTS');
    const mode = req(delete_mode, 'DELETE_MODE').toUpperCase();
    if (!DELETE_MODES.includes(mode)) throw new Error('DELETE_MODE_NOT_ALLOWED');

    const p = Object.freeze({
      policy_id: id,
      tenant_id: req(tenant_id, 'TENANT_ID'),
      retention_days: nonNegInt(retention_days, 'RETENTION_DAYS'),
      deletion_grace_days: nonNegInt(deletion_grace_days, 'DELETION_GRACE_DAYS'),
      region: req(region, 'REGION').toUpperCase(),
      export_allowed: export_allowed === true,
      training_use_allowed: training_use_allowed === true,
      delete_mode: mode,
      legal_hold_default: legal_hold_default === true
    });
    this.policies.set(id, p);
    return p;
  }

  get(policy_id) {
    const p = this.policies.get(req(policy_id, 'POLICY_ID'));
    if (!p) throw new Error('POLICY_NOT_FOUND');
    return p;
  }
}

export class DataResourceCatalog {
  constructor({ policyRegistry, now = () => Date.now() }) {
    this.policies = policyRegistry;
    this.now = now;
    this.resources = new Map();
    this.events = [];
  }

  create({
    resource_id,
    tenant_id,
    policy_id,
    data_class = 'BL-S0',
    region,
    source_ref,
    created_at = null,
    content_hash = null,
    legal_hold = null,
    metadata = {}
  }) {
    const id = req(resource_id, 'RESOURCE_ID');
    if (this.resources.has(id)) throw new Error('RESOURCE_EXISTS');
    const tid = req(tenant_id, 'TENANT_ID');
    const policy = this.policies.get(policy_id);
    if (policy.tenant_id !== tid) throw new Error('POLICY_TENANT_MISMATCH');

    const dc = req(data_class, 'DATA_CLASS').toUpperCase();
    if (!DATA_CLASSES.includes(dc)) throw new Error('DATA_CLASS_NOT_ALLOWED');

    const actualRegion = req(region || policy.region, 'REGION').toUpperCase();
    if (policy.region !== 'GLOBAL' && actualRegion !== policy.region) throw new Error('DATA_RESIDENCY_MISMATCH');

    const created = created_at ? iso(created_at, 'CREATED_AT') : new Date(this.now()).toISOString();
    const row = Object.freeze({
      resource_id: id,
      tenant_id: tid,
      policy_id: policy.policy_id,
      data_class: dc,
      region: actualRegion,
      source_ref: req(source_ref, 'SOURCE_REF'),
      created_at: created,
      content_hash: content_hash || null,
      state: 'ACTIVE',
      legal_hold: legal_hold == null ? policy.legal_hold_default : legal_hold === true,
      tombstoned_at: null,
      purge_after: null,
      purge_receipt: null,
      metadata: Object.freeze({ ...metadata })
    });
    this.resources.set(id, row);
    this._event('CREATE', row, { source_ref: row.source_ref });
    return row;
  }

  _event(type, resource, details = {}) {
    const event = Object.freeze({
      event_id: `dgov-${this.events.length + 1}`,
      type,
      tenant_id: resource.tenant_id,
      resource_id: resource.resource_id,
      at: new Date(this.now()).toISOString(),
      details: Object.freeze({ ...details })
    });
    this.events.push(event);
    return event;
  }

  getForTenant(resource_id, tenant_id) {
    const row = this.resources.get(req(resource_id, 'RESOURCE_ID'));
    if (!row) throw new Error('RESOURCE_NOT_FOUND');
    if (row.tenant_id !== req(tenant_id, 'TENANT_ID')) throw new Error('CROSS_TENANT_DATA_DENIED');
    return row;
  }

  setLegalHold({ resource_id, tenant_id, enabled, authority_ref }) {
    const current = this.getForTenant(resource_id, tenant_id);
    req(authority_ref, 'AUTHORITY_REF');
    if (current.state === 'PURGED') throw new Error('RESOURCE_ALREADY_PURGED');
    const updated = Object.freeze({ ...current, legal_hold: enabled === true });
    this.resources.set(current.resource_id, updated);
    this._event(enabled ? 'LEGAL_HOLD_SET' : 'LEGAL_HOLD_RELEASED', updated, { authority_ref });
    return updated;
  }

  retentionDecision({ resource_id, tenant_id, at = null }) {
    const row = this.getForTenant(resource_id, tenant_id);
    const policy = this.policies.get(row.policy_id);
    if (row.state === 'PURGED') return Object.freeze({ action: 'NONE', reason: 'ALREADY_PURGED' });
    if (row.legal_hold) return Object.freeze({ action: 'KEEP', reason: 'LEGAL_HOLD' });

    const now = at ? new Date(iso(at, 'AT')).getTime() : this.now();
    const created = new Date(row.created_at).getTime();
    const due = created + policy.retention_days * 86400000;
    if (now >= due) return Object.freeze({ action: 'DELETE_DUE', due_at: new Date(due).toISOString() });
    return Object.freeze({ action: 'KEEP', reason: 'RETENTION_NOT_EXPIRED', due_at: new Date(due).toISOString() });
  }

  requestDeletion({ resource_id, tenant_id, authority_ref, requested_at = null }) {
    const row = this.getForTenant(resource_id, tenant_id);
    const policy = this.policies.get(row.policy_id);
    req(authority_ref, 'AUTHORITY_REF');
    if (row.legal_hold) return Object.freeze({ accepted: false, reason: 'LEGAL_HOLD' });
    if (row.state === 'PURGED') return Object.freeze({ accepted: true, already_purged: true });

    const when = requested_at ? new Date(iso(requested_at, 'REQUESTED_AT')) : new Date(this.now());
    const graceMs = policy.deletion_grace_days * 86400000;
    const immediate = policy.delete_mode === 'IMMEDIATE_PURGE_WHEN_ALLOWED' && graceMs === 0;

    if (immediate) {
      return this.purge({
        resource_id,
        tenant_id,
        authority_ref,
        purge_receipt: `policy-immediate:${digest({ resource_id, when: when.toISOString() })}`,
        at: when.toISOString()
      });
    }

    const updated = Object.freeze({
      ...row,
      state: 'TOMBSTONED',
      tombstoned_at: when.toISOString(),
      purge_after: new Date(when.getTime() + graceMs).toISOString()
    });
    this.resources.set(row.resource_id, updated);
    this._event('TOMBSTONE', updated, { authority_ref, purge_after: updated.purge_after });
    return Object.freeze({ accepted: true, state: updated.state, purge_after: updated.purge_after });
  }

  purge({ resource_id, tenant_id, authority_ref, purge_receipt, at = null }) {
    const row = this.getForTenant(resource_id, tenant_id);
    req(authority_ref, 'AUTHORITY_REF');
    req(purge_receipt, 'PURGE_RECEIPT');
    if (row.legal_hold) return Object.freeze({ purged: false, reason: 'LEGAL_HOLD' });
    if (row.state === 'PURGED') return Object.freeze({ purged: true, already_purged: true, purge_receipt: row.purge_receipt });

    const now = at ? new Date(iso(at, 'AT')).getTime() : this.now();
    if (row.state === 'TOMBSTONED' && row.purge_after && now < new Date(row.purge_after).getTime()) {
      return Object.freeze({ purged: false, reason: 'GRACE_PERIOD_ACTIVE', purge_after: row.purge_after });
    }

    const updated = Object.freeze({
      ...row,
      state: 'PURGED',
      purge_receipt,
      metadata: Object.freeze({}),
      content_hash: null
    });
    this.resources.set(row.resource_id, updated);
    this._event('PURGE', updated, { authority_ref, purge_receipt });
    return Object.freeze({ purged: true, purge_receipt });
  }

  exportManifest({ tenant_id, authority_ref, resource_ids = null, generated_at = null }) {
    const tid = req(tenant_id, 'TENANT_ID');
    req(authority_ref, 'AUTHORITY_REF');
    const rows = [...this.resources.values()].filter((r) =>
      r.tenant_id === tid &&
      r.state !== 'PURGED' &&
      (resource_ids == null || resource_ids.includes(r.resource_id))
    );

    for (const row of rows) {
      const policy = this.policies.get(row.policy_id);
      if (!policy.export_allowed) throw new Error(`EXPORT_NOT_ALLOWED:${row.resource_id}`);
    }

    const entries = rows.map((row) => Object.freeze({
      resource_id: row.resource_id,
      data_class: row.data_class,
      region: row.region,
      source_ref: row.source_ref,
      content_hash: row.content_hash,
      created_at: row.created_at,
      state: row.state,
      legal_hold: row.legal_hold
    }));

    const at = generated_at ? iso(generated_at, 'GENERATED_AT') : new Date(this.now()).toISOString();
    return Object.freeze({
      tenant_id: tid,
      generated_at: at,
      authority_ref,
      entries: Object.freeze(entries),
      manifest_hash: digest(entries)
    });
  }

  trainingEligibility({ resource_id, tenant_id }) {
    const row = this.getForTenant(resource_id, tenant_id);
    const policy = this.policies.get(row.policy_id);
    return Object.freeze({
      allowed: row.state === 'ACTIVE' && !row.legal_hold && policy.training_use_allowed,
      policy_id: policy.policy_id,
      training_use_allowed: policy.training_use_allowed,
      state: row.state,
      legal_hold: row.legal_hold
    });
  }
}

export function assertDataGovernanceRuntime({ policyRegistry, catalog }) {
  if (!(policyRegistry instanceof DataPolicyRegistry)) throw new Error('POLICY_REGISTRY_REQUIRED');
  if (!(catalog instanceof DataResourceCatalog)) throw new Error('CATALOG_REQUIRED');
  return true;
}
