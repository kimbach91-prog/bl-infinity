import crypto from 'node:crypto';

export const PACKET_TYPES = Object.freeze([
  'HELLO_CAPSULE',
  'OFFER_PACKET',
  'REQUEST_PACKET',
  'NEGOTIATION_PACKET',
  'EVIDENCE_PACKET',
  'RESULT_PACKET',
  'RECEIPT_PACKET',
  'EVENT_PACKET'
]);

export const EXTERNAL_DEFAULT_CLASSES = new Set(['S0', 'S1']);
export const SEALED_CLASSES = new Set(['S2', 'S3', 'S4']);

const FORBIDDEN_EXTERNAL_KEYS = new Set([
  'api_key', 'token', 'secret', 'secrets', 'credential', 'credentials',
  'password', 'private_key', 'recovery_code', 'oauth_token', 'access_token',
  'raw_memory', 'raw_reasoning', 'protected_topology', 'private_context',
  'sealed_payload', 'owner_private_state'
]);

const REQUIRED = [
  'version', 'packet_id', 'type', 'source_member_id', 'target_member_id',
  'purpose', 'intent', 'data_class', 'auth_ref', 'idempotency_key',
  'created_at', 'expires_at'
];

const clamp01 = (value) => {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return Math.max(0, Math.min(1, n));
};

export function stableDigest(value) {
  return crypto.createHash('sha256').update(stableStringify(value)).digest('hex');
}

function stableStringify(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`;
  const keys = Object.keys(value).sort();
  return `{${keys.map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(',')}}`;
}

function cleanString(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function validIsoTimestamp(value) {
  if (!cleanString(value)) return false;
  const ms = Date.parse(value);
  return Number.isFinite(ms);
}

function packetTextSize(packet) {
  return Buffer.byteLength(JSON.stringify(packet), 'utf8');
}

function hasClaims(packet) {
  return Array.isArray(packet.claims) && packet.claims.length > 0;
}

function hasSourceRefs(packet) {
  return Array.isArray(packet.source_refs) && packet.source_refs.some((x) => cleanString(x));
}

function hasExchangeValue(packet) {
  const e = packet.exchange;
  if (!e || typeof e !== 'object') return false;
  const mode = cleanString(e.mode);
  const offer = e.offer ?? packet.offer;
  const request = e.request ?? packet.request;
  return Boolean(mode && (offer || request));
}

function requireRouterMetrics(metrics) {
  const fields = [
    'relevance', 'expected_information_gain', 'reciprocity',
    'evidence_quality', 'redundancy', 'privacy_risk',
    'expected_value_gain', 'marginal_cost'
  ];
  const out = {};
  for (const field of fields) {
    const v = clamp01(metrics?.[field]);
    if (v === null) return { ok: false, missing: field };
    out[field] = v;
  }
  return { ok: true, metrics: out };
}

export function validateElitePacket(packet, { now = new Date(), maxBytes = 24_000 } = {}) {
  const reasons = [];
  if (!packet || typeof packet !== 'object' || Array.isArray(packet)) {
    return { state: 'DENY', code: 'INVALID_PACKET', reasons: ['packet must be an object'] };
  }

  for (const field of REQUIRED) {
    if (packet[field] === undefined || packet[field] === null || cleanString(packet[field]) === '') {
      reasons.push(`missing:${field}`);
    }
  }

  if (!PACKET_TYPES.includes(packet.type)) reasons.push('invalid:type');
  if (!['S0', 'S1', 'S2', 'S3', 'S4'].includes(packet.data_class)) reasons.push('invalid:data_class');
  if (!validIsoTimestamp(packet.created_at)) reasons.push('invalid:created_at');
  if (!validIsoTimestamp(packet.expires_at)) reasons.push('invalid:expires_at');

  if (validIsoTimestamp(packet.expires_at) && Date.parse(packet.expires_at) <= now.getTime()) {
    reasons.push('expired');
  }

  if (packetTextSize(packet) > maxBytes) reasons.push('oversize:inline_packet');

  if (hasClaims(packet) && !hasSourceRefs(packet)) reasons.push('claims_without_source_refs');

  if (['OFFER_PACKET', 'REQUEST_PACKET', 'NEGOTIATION_PACKET', 'HELLO_CAPSULE'].includes(packet.type)
      && !hasExchangeValue(packet)) {
    reasons.push('missing:exchange_value');
  }

  if (reasons.length) {
    const code = reasons.includes('expired') ? 'STALE_PACKET' : 'SCHEMA_OR_PROVENANCE_FAIL';
    return { state: 'HOLD', code, reasons };
  }

  return {
    state: 'VALID',
    code: 'STRUCTURE_VALID',
    packet_digest: stableDigest(packet),
    bytes: packetTextSize(packet)
  };
}

export function qualifyElitePacket(packet, context = {}) {
  const structural = validateElitePacket(packet, context);
  if (structural.state !== 'VALID') return structural;

  if (SEALED_CLASSES.has(packet.data_class)) {
    return {
      state: 'HOLD',
      code: 'SEALED_ROUTE_REQUIRED',
      reasons: ['external_default_allows_S0_S1_only'],
      packet_digest: structural.packet_digest
    };
  }

  if (context.seen_idempotency_keys?.has(packet.idempotency_key)
      || context.seen_packet_digests?.has(structural.packet_digest)) {
    return {
      state: 'REJECT',
      code: 'DUPLICATE_OR_REPLAY_NOISE',
      reasons: ['duplicate_or_replay'],
      packet_digest: structural.packet_digest
    };
  }

  const assessed = requireRouterMetrics(context.router_metrics);
  if (!assessed.ok) {
    return {
      state: 'HOLD',
      code: 'NEEDS_TRUSTED_ROUTER_SCORE',
      reasons: [`missing_router_metric:${assessed.missing}`],
      packet_digest: structural.packet_digest
    };
  }

  const m = assessed.metrics;
  const reasons = [];

  if (m.relevance < 0.60) reasons.push('low_relevance');
  if (m.expected_information_gain < 0.35 && m.reciprocity < 0.55) reasons.push('low_useful_gain');
  if (hasClaims(packet) && m.evidence_quality < 0.45) reasons.push('weak_evidence_quality');
  if (m.redundancy > 0.35) reasons.push('high_redundancy');
  if (m.privacy_risk > 0.35) reasons.push('privacy_risk_too_high');
  if (m.expected_value_gain <= m.marginal_cost) reasons.push('non_positive_marginal_value');

  if (reasons.length) {
    return {
      state: 'REJECT',
      code: 'ELITE_GATE_FAIL',
      reasons,
      packet_digest: structural.packet_digest,
      axes: m
    };
  }

  return {
    state: 'ACCEPT',
    code: 'ELITE_PACKET_ACCEPTED',
    packet_digest: structural.packet_digest,
    axes: m,
    execution_authority: false,
    canonical_write: false,
    result_authority: false
  };
}

function sanitize(value) {
  if (Array.isArray(value)) return value.map(sanitize);
  if (!value || typeof value !== 'object') return value;
  const out = {};
  for (const [key, child] of Object.entries(value)) {
    if (FORBIDDEN_EXTERNAL_KEYS.has(key.toLowerCase())) continue;
    out[key] = sanitize(child);
  }
  return out;
}

export function compileExternalProjection(packet, { allowedInlineDataClasses = EXTERNAL_DEFAULT_CLASSES } = {}) {
  if (!packet || typeof packet !== 'object') throw new Error('INVALID_PACKET');
  if (!allowedInlineDataClasses.has(packet.data_class)) throw new Error('SEALED_ROUTE_REQUIRED');

  const safe = sanitize(packet);
  const allowed = [
    'version', 'packet_id', 'type', 'source_member_id', 'target_member_id',
    'task_id', 'purpose', 'intent', 'data_class', 'auth_ref', 'idempotency_key',
    'created_at', 'expires_at', 'source_refs', 'claims', 'unknowns', 'constraints',
    'exchange', 'offer', 'request', 'expected_format', 'result_ref', 'correlation_id'
  ];
  const projection = {};
  for (const key of allowed) {
    if (safe[key] !== undefined) projection[key] = safe[key];
  }

  projection.projection_digest = stableDigest(projection);
  projection.membrane = {
    minimum_sufficient: true,
    raw_secret_exported: false,
    canonical_write: false,
    execution_authority: false
  };
  return projection;
}

export function makeEliteReceipt({ packet, decision, route = 'DEUS_SOVEREIGN_API_V0_1', observed = {} }) {
  const packetDigest = stableDigest(packet);
  const safeObserved = sanitize(observed);
  return {
    receipt_version: 'DEUS-ELITE-RECEIPT/0.1',
    packet_id: packet?.packet_id ?? null,
    task_id: packet?.task_id ?? null,
    packet_digest: packetDigest,
    decision: {
      state: decision?.state ?? 'UNKNOWN',
      code: decision?.code ?? 'UNKNOWN',
      reasons: Array.isArray(decision?.reasons) ? decision.reasons : []
    },
    route,
    observed: safeObserved,
    data_class: packet?.data_class ?? 'UNKNOWN',
    canonical_write: false,
    execution_authority: false,
    secret_material_recorded: false
  };
}
