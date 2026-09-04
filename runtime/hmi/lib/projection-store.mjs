import { projectHmiEnvelope } from './access-policy.mjs';

const DATA_CLASSES = new Set(['public', 'internal', 'confidential', 'restricted', 'sovereign']);
const DEFAULT_SCHEMA_VERSIONS = Object.freeze(['hmi-projection/v1']);
const IDENTIFIER_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$/;

function requireText(value, name, max = 200) {
  if (typeof value !== 'string' || value.length < 1 || value.length > max) throw new Error(`${name} is required`);
  return value;
}

function requireIdentifier(value, name) {
  const text = requireText(value, name, 200);
  if (!IDENTIFIER_PATTERN.test(text)) throw new Error(`${name} contains unsupported characters`);
  return text;
}

function requireTimestamp(value, name) {
  const timestamp = Number(value);
  if (!Number.isFinite(timestamp)) throw new Error(`${name} is required`);
  return timestamp;
}

function compositeKey(tenantId, projectionId) {
  // tenantId/projectionId are ASCII allowlisted before reaching this function,
  // so the NUL separator cannot be injected by either component.
  return `${tenantId}\u0000${projectionId}`;
}

function sameRecord(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

export class TenantProjectionStore {
  constructor({ supportedSchemaVersions = DEFAULT_SCHEMA_VERSIONS, maxFutureSkewMs = 30_000 } = {}) {
    this.records = new Map();
    this.supportedSchemaVersions = new Set(supportedSchemaVersions);
    this.maxFutureSkewMs = maxFutureSkewMs;
  }

  put(record, now = Date.now()) {
    const tenantId = requireIdentifier(record?.tenantId, 'tenantId');
    const projectionId = requireIdentifier(record?.projectionId, 'projectionId');
    const schemaVersion = requireText(record?.schemaVersion, 'schemaVersion', 80);
    if (!this.supportedSchemaVersions.has(schemaVersion)) throw new Error('unsupported schemaVersion');

    const dataClass = requireText(record?.dataClass, 'dataClass', 40);
    if (!DATA_CLASSES.has(dataClass)) throw new Error('unsupported dataClass');

    const createdAt = requireTimestamp(record?.createdAt, 'createdAt');
    if (createdAt > now + this.maxFutureSkewMs) throw new Error('createdAt exceeds allowed clock skew');

    const expiresAt = requireTimestamp(record?.expiresAt, 'expiresAt');
    if (expiresAt <= now || expiresAt <= createdAt) throw new Error('future expiresAt after createdAt is required');

    const value = projectHmiEnvelope(record?.value ?? {});
    const stored = Object.freeze({
      tenantId,
      projectionId,
      schemaVersion,
      dataClass,
      policyVersion: requireText(record?.policyVersion, 'policyVersion', 100),
      sourceReceiptRefs: Object.freeze([...(Array.isArray(record?.sourceReceiptRefs) ? record.sourceReceiptRefs : [])].map((ref) => requireText(ref, 'sourceReceiptRef', 300))),
      createdAt,
      expiresAt,
      value: Object.freeze(structuredClone(value)),
    });

    const key = compositeKey(tenantId, projectionId);
    const existing = this.records.get(key);
    if (existing) {
      if (stored.createdAt < existing.createdAt) throw new Error('stale projection replay rejected');
      if (stored.createdAt === existing.createdAt) {
        if (sameRecord(existing, stored)) return existing;
        throw new Error('projection version conflict');
      }
    }

    this.records.set(key, stored);
    return stored;
  }

  get({ tenantId, projectionId, now = Date.now() }) {
    requireIdentifier(tenantId, 'tenantId');
    requireIdentifier(projectionId, 'projectionId');
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
    requireIdentifier(tenantId, 'tenantId');
    requireIdentifier(projectionId, 'projectionId');
    return this.records.delete(compositeKey(tenantId, projectionId));
  }

  purgeTenant(tenantId) {
    requireIdentifier(tenantId, 'tenantId');
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
