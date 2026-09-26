import crypto from 'node:crypto';

export const API_STATES = Object.freeze(['ACTIVE', 'DEPRECATED', 'SUNSET']);
export const SDK_LANGUAGES = Object.freeze(['typescript', 'python', 'go']);
export const STREAM_EVENT_TYPES = Object.freeze(['started', 'delta', 'tool', 'artifact', 'completed', 'error']);

function req(v, name) {
  if (typeof v !== 'string' || !v.trim()) throw new Error(`INVALID_${name}`);
  return v.trim();
}
function posInt(v, name) {
  const n = Number(v);
  if (!Number.isInteger(n) || n < 1) throw new Error(`INVALID_${name}`);
  return n;
}
function isoDate(v, name) {
  const d = new Date(v);
  if (!Number.isFinite(d.getTime())) throw new Error(`INVALID_${name}`);
  return d.toISOString();
}
function sha(value) {
  return crypto.createHash('sha256').update(typeof value === 'string' ? value : JSON.stringify(value)).digest('hex');
}
function parseVersion(v) {
  const s = req(v, 'VERSION');
  const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(s);
  if (!m) throw new Error('INVALID_SEMVER');
  return { raw: s, major: Number(m[1]), minor: Number(m[2]), patch: Number(m[3]) };
}

export class ApiVersionRegistry {
  constructor({ minimum_deprecation_days = 90 } = {}) {
    this.minimum_deprecation_days = posInt(minimum_deprecation_days, 'MIN_DEPRECATION_DAYS');
    this.versions = new Map();
  }

  register({ version, released_at, compatible_with_major, schema_ref, state = 'ACTIVE' }) {
    const p = parseVersion(version);
    if (this.versions.has(p.raw)) throw new Error('VERSION_EXISTS');
    const st = req(state, 'STATE').toUpperCase();
    if (!API_STATES.includes(st)) throw new Error('STATE_NOT_ALLOWED');

    const row = Object.freeze({
      version: p.raw,
      major: p.major,
      minor: p.minor,
      patch: p.patch,
      released_at: isoDate(released_at, 'RELEASED_AT'),
      compatible_with_major: compatible_with_major == null ? p.major : Number(compatible_with_major),
      schema_ref: req(schema_ref, 'SCHEMA_REF'),
      state: st,
      deprecated_at: null,
      sunset_at: null
    });
    this.versions.set(p.raw, row);
    return row;
  }

  deprecate({ version, deprecated_at, sunset_at }) {
    const current = this.versions.get(req(version, 'VERSION'));
    if (!current) throw new Error('VERSION_NOT_FOUND');
    const dep = new Date(isoDate(deprecated_at, 'DEPRECATED_AT'));
    const sun = new Date(isoDate(sunset_at, 'SUNSET_AT'));
    const days = (sun - dep) / 86400000;
    if (days < this.minimum_deprecation_days) throw new Error('DEPRECATION_NOTICE_TOO_SHORT');

    const updated = Object.freeze({
      ...current,
      state: 'DEPRECATED',
      deprecated_at: dep.toISOString(),
      sunset_at: sun.toISOString()
    });
    this.versions.set(current.version, updated);
    return updated;
  }

  resolve(version) {
    const row = this.versions.get(req(version, 'VERSION'));
    if (!row) return Object.freeze({ allowed: false, reason: 'VERSION_NOT_FOUND' });
    if (row.state === 'SUNSET') return Object.freeze({ allowed: false, reason: 'VERSION_SUNSET' });
    return Object.freeze({ allowed: true, version: row });
  }

  compatibility({ client_version, server_version }) {
    const c = parseVersion(client_version);
    const s = parseVersion(server_version);
    return Object.freeze({
      compatible: c.major === s.major,
      client_major: c.major,
      server_major: s.major,
      rule: 'SAME_MAJOR_COMPATIBILITY'
    });
  }
}

export class IdempotencyStore {
  constructor() {
    this.rows = new Map();
  }

  begin({ tenant_id, key, request_body, operation }) {
    const tid = req(tenant_id, 'TENANT_ID');
    const k = req(key, 'IDEMPOTENCY_KEY');
    const op = req(operation, 'OPERATION');
    const request_hash = sha(request_body ?? null);
    const compound = `${tid}::${op}::${k}`;
    const existing = this.rows.get(compound);

    if (existing) {
      if (existing.request_hash !== request_hash) {
        return Object.freeze({ accepted: false, reason: 'IDEMPOTENCY_CONFLICT', existing });
      }
      return Object.freeze({
        accepted: true,
        replay: true,
        state: existing.state,
        response_ref: existing.response_ref,
        result_hash: existing.result_hash
      });
    }

    const row = Object.freeze({
      tenant_id: tid,
      key: k,
      operation: op,
      request_hash,
      state: 'IN_PROGRESS',
      response_ref: null,
      result_hash: null
    });
    this.rows.set(compound, row);
    return Object.freeze({ accepted: true, replay: false, state: 'IN_PROGRESS' });
  }

  complete({ tenant_id, key, operation, response_ref, result }) {
    const compound = `${req(tenant_id, 'TENANT_ID')}::${req(operation, 'OPERATION')}::${req(key, 'IDEMPOTENCY_KEY')}`;
    const existing = this.rows.get(compound);
    if (!existing) throw new Error('IDEMPOTENCY_RECORD_NOT_FOUND');
    const row = Object.freeze({
      ...existing,
      state: 'COMPLETED',
      response_ref: req(response_ref, 'RESPONSE_REF'),
      result_hash: sha(result ?? null)
    });
    this.rows.set(compound, row);
    return row;
  }
}

export class CursorCodec {
  constructor({ secret }) {
    this.secret = req(secret, 'CURSOR_SECRET');
  }

  encode({ tenant_id, resource, offset, snapshot_ref }) {
    const payload = {
      tenant_id: req(tenant_id, 'TENANT_ID'),
      resource: req(resource, 'RESOURCE'),
      offset: Number(offset),
      snapshot_ref: req(snapshot_ref, 'SNAPSHOT_REF')
    };
    if (!Number.isInteger(payload.offset) || payload.offset < 0) throw new Error('INVALID_OFFSET');
    const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
    const sig = crypto.createHmac('sha256', this.secret).update(body).digest('base64url');
    return `${body}.${sig}`;
  }

  decode(cursor, expected_tenant_id) {
    const raw = req(cursor, 'CURSOR');
    const [body, sig] = raw.split('.');
    if (!body || !sig) throw new Error('INVALID_CURSOR');
    const expected = crypto.createHmac('sha256', this.secret).update(body).digest('base64url');
    if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) throw new Error('CURSOR_SIGNATURE_INVALID');
    const payload = JSON.parse(Buffer.from(body, 'base64url').toString('utf8'));
    if (payload.tenant_id !== req(expected_tenant_id, 'TENANT_ID')) throw new Error('CURSOR_TENANT_MISMATCH');
    return Object.freeze(payload);
  }
}

export class StreamContract {
  constructor() {
    this.last = new Map();
  }

  emit({ stream_id, sequence, type, data, trace_id }) {
    const sid = req(stream_id, 'STREAM_ID');
    const seq = posInt(sequence, 'SEQUENCE');
    const et = req(type, 'EVENT_TYPE');
    if (!STREAM_EVENT_TYPES.includes(et)) throw new Error('STREAM_EVENT_TYPE_NOT_ALLOWED');
    const previous = this.last.get(sid) || 0;
    if (seq !== previous + 1) throw new Error('STREAM_SEQUENCE_GAP');
    this.last.set(sid, seq);
    return Object.freeze({
      stream_id: sid,
      sequence: seq,
      type: et,
      trace_id: req(trace_id, 'TRACE_ID'),
      data: Object.freeze(JSON.parse(JSON.stringify(data ?? {})))
    });
  }
}

export function makeRequestEnvelope({
  tenant_id,
  principal_id,
  api_version,
  request_id,
  trace_id,
  idempotency_key = null,
  operation,
  data_class = 'BL-S0'
}) {
  parseVersion(api_version);
  return Object.freeze({
    tenant_id: req(tenant_id, 'TENANT_ID'),
    principal_id: req(principal_id, 'PRINCIPAL_ID'),
    api_version,
    request_id: req(request_id, 'REQUEST_ID'),
    trace_id: req(trace_id, 'TRACE_ID'),
    idempotency_key: idempotency_key ? req(idempotency_key, 'IDEMPOTENCY_KEY') : null,
    operation: req(operation, 'OPERATION'),
    data_class: req(data_class, 'DATA_CLASS')
  });
}

export function errorEnvelope({ request_id, trace_id, code, message, retryable = false, details = null }) {
  return Object.freeze({
    error: Object.freeze({
      code: req(code, 'ERROR_CODE'),
      message: req(message, 'ERROR_MESSAGE'),
      retryable: retryable === true,
      details
    }),
    request_id: req(request_id, 'REQUEST_ID'),
    trace_id: req(trace_id, 'TRACE_ID')
  });
}

export const SDK_MANIFEST_V1 = Object.freeze({
  contract_version: '1.0.0',
  source_of_truth: 'OPENAPI_OR_EQUIVALENT_MACHINE_SCHEMA',
  languages: Object.freeze({
    typescript: Object.freeze({ package: '@deus/sdk', min_runtime: 'node>=22' }),
    python: Object.freeze({ package: 'deus-sdk', min_runtime: 'python>=3.11' }),
    go: Object.freeze({ package: 'github.com/deus-platform/deus-go', min_runtime: 'go>=1.23' })
  }),
  required_features: Object.freeze([
    'typed_request_envelopes',
    'idempotency_keys',
    'cursor_pagination',
    'streaming_contract',
    'structured_errors',
    'retries_for_retryable_errors_only',
    'trace_propagation',
    'version_negotiation'
  ])
});

export function assertDeveloperPlatformContract() {
  const langs = Object.keys(SDK_MANIFEST_V1.languages);
  if (langs.length !== SDK_LANGUAGES.length) throw new Error('SDK_LANGUAGE_SET_INVALID');
  for (const language of SDK_LANGUAGES) {
    if (!SDK_MANIFEST_V1.languages[language]) throw new Error('SDK_LANGUAGE_MISSING');
  }
  if (!SDK_MANIFEST_V1.required_features.includes('idempotency_keys')) throw new Error('IDEMPOTENCY_REQUIRED');
  if (!SDK_MANIFEST_V1.required_features.includes('structured_errors')) throw new Error('STRUCTURED_ERRORS_REQUIRED');
  return true;
}
