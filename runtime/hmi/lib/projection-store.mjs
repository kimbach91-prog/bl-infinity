import { projectHmiEnvelope } from './access-policy.mjs';

const DATA_CLASSES = new Set(['public', 'internal', 'confidential', 'restricted', 'sovereign']);

function requireText(value, name, max = 200) {
  if (typeof value !== 'string' || value.length < 1 || value.length > max) throw new Error(`${name} is required`);
  return value;
}

function compositeKey(tenantId, projectionId) {
  return `${tenantId}\u0000${projectionId}`;
}

export class TenantProjectionStore {
  constructor() {
    this.records = new Map();
  }

  put(record, now = Date.now()) {
    const tenantId = requireText(record?.tenantId, 'tenantId');
    const projectionId = requireText(record?.projectionId, 'projectionId');
    const schemaVersion = requireText(record?.schemaVersion, 'schemaVersion', 80);
    const dataClass = requireText(record?.dataClass, 'dataClass', 40);
    if (!DATA_CLASSES.has(dataClass)) throw new Error('unsupported dataClass');

    const expiresAt = Number(record?.expiresAt);
    if (!Number.isFinite(expiresAt) || expiresAt <= now) throw new Error('future expiresAt is required');

    const value = projectHmiEnvelope(record?.value ?? {});
    const stored = Object.freeze({
      tenantId,
      projectionId,
      schemaVersion,
      dataClass,
      policyVersion: requireText(record?.policyVersion, 'policyVersion', 100),
      sourceReceiptRefs: Object.freeze([...(Array.isArray(record?.sourceReceiptRefs) ? record.sourceReceiptRefs : [])].map((ref) => requireText(ref, 'sourceReceiptRef', 300))),
      createdAt: Number.isFinite(Number(record?.createdAt)) ? Number(record.createdAt) : now,
      expiresAt,
      value: Object.freeze(structuredClone(value)),
    });

    this.records.set(compositeKey(tenantId, projectionId), stored);
    return stored;
  }

  get({ tenantId, projectionId, now = Date.now() }) {
    requireText(tenantId, 'tenantId');
    requireText(projectionId, 'projectionId');
    const key = compositeKey(tenantId, projectionId);
    const record = this.records.get(key);
    if (!record) return null;
    if (record.expiresAt <= now) {
      this.records.delete(key);
      return null;
    }
    return structuredClone(record);
  }

  delete({ tenantId, projectionId }) {
    requireText(tenantId, 'tenantId');
    requireText(projectionId, 'projectionId');
    return this.records.delete(compositeKey(tenantId, projectionId));
  }

  purgeTenant(tenantId) {
    requireText(tenantId, 'tenantId');
    let removed = 0;
    const prefix = `${tenantId}\u0000`;
    for (const key of this.records.keys()) {
      if (key.startsWith(prefix)) {
        this.records.delete(key);
        removed += 1;
      }
    }
    return removed;
  }

  size() {
    return this.records.size;
  }
}
