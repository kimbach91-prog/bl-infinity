import { randomUUID } from 'node:crypto';
import { canonicalize, sha256 } from './canonical.mjs';

export const PLATFORM_API_VERSION = '1.0.0';
export const PLATFORM_API_MAJOR = 1;

const ID_RE = /^[a-zA-Z0-9._:-]{1,160}$/;
const IDEM_RE = /^[a-zA-Z0-9._:/-]{8,160}$/;

export function platformApiContext(req, { requireIdempotency = false } = {}) {
  const version = header(req.headers, 'x-deus-api-version');
  if (!version) return fail(400, 'API_VERSION_REQUIRED', 'x-deus-api-version is required');
  const parsed = parseSemver(version);
  if (!parsed || parsed.major !== PLATFORM_API_MAJOR) {
    return fail(426, 'API_VERSION_UNSUPPORTED', `supported major is ${PLATFORM_API_MAJOR}`, {
      supported_version: PLATFORM_API_VERSION,
      requested_version: version,
    });
  }

  const requestId = normalizeId(header(req.headers, 'x-request-id')) || `req-${randomUUID()}`;
  const traceId = normalizeId(header(req.headers, 'x-trace-id')) || `trace-${randomUUID()}`;
  const idempotencyKey = header(req.headers, 'idempotency-key');

  if (requireIdempotency && (!idempotencyKey || !IDEM_RE.test(idempotencyKey))) {
    return fail(400, 'IDEMPOTENCY_KEY_REQUIRED', 'Idempotency-Key must be 8-160 safe characters');
  }
  if (idempotencyKey && !IDEM_RE.test(idempotencyKey)) {
    return fail(400, 'IDEMPOTENCY_KEY_INVALID', 'Idempotency-Key must be 8-160 safe characters');
  }

  return Object.freeze({
    ok: true,
    api_version: PLATFORM_API_VERSION,
    requested_version: version,
    request_id: requestId,
    trace_id: traceId,
    idempotency_key: idempotencyKey || null,
  });
}

export function applyPlatformResponseHeaders(res, context) {
  res.setHeader('x-deus-api-version', PLATFORM_API_VERSION);
  if (context?.request_id) res.setHeader('x-request-id', context.request_id);
  if (context?.trace_id) res.setHeader('x-trace-id', context.trace_id);
}

export function platformError(context, code, message, {
  status = 400,
  retryable = false,
  details = null,
} = {}) {
  return Object.freeze({
    status,
    body: Object.freeze({
      error: Object.freeze({
        code,
        message,
        retryable: retryable === true,
        details,
      }),
      api_version: PLATFORM_API_VERSION,
      request_id: context?.request_id ?? null,
      trace_id: context?.trace_id ?? null,
    }),
  });
}

export function platformEnvelope(context, data, meta = {}) {
  return Object.freeze({
    api_version: PLATFORM_API_VERSION,
    request_id: context.request_id,
    trace_id: context.trace_id,
    data,
    meta: Object.freeze({ ...meta }),
  });
}

export function developerTaskRequestHash(task) {
  return sha256(canonicalize(task));
}

export function sameDeveloperTask(existingTask, requestedTask) {
  return developerTaskRequestHash(existingTask) === developerTaskRequestHash(requestedTask);
}

export function developerReplayMeta(submitted, task) {
  const replay = submitted?.deduplicated === true;
  if (!replay) {
    return Object.freeze({
      replay: false,
      conflict: false,
      request_hash: developerTaskRequestHash(task),
      existing_hash: null,
    });
  }
  const existing = submitted?.job?.task ?? null;
  const same = existing != null && sameDeveloperTask(existing, task);
  return Object.freeze({
    replay: same,
    conflict: !same,
    request_hash: developerTaskRequestHash(task),
    existing_hash: existing == null ? null : developerTaskRequestHash(existing),
  });
}

function fail(status, code, message, details = null) {
  return Object.freeze({
    ok: false,
    status,
    error: platformError(null, code, message, { status, details }),
  });
}
function normalizeId(value) {
  if (!value) return null;
  const v = String(value);
  return ID_RE.test(v) ? v : null;
}
function parseSemver(value) {
  const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(String(value || ''));
  return m ? { major: Number(m[1]), minor: Number(m[2]), patch: Number(m[3]) } : null;
}
function header(headers, name) {
  if (!headers) return null;
  if (typeof headers.get === 'function') return headers.get(name);
  const target = name.toLowerCase();
  for (const [key, value] of Object.entries(headers)) {
    if (String(key).toLowerCase() === target) return value == null ? null : String(value);
  }
  return null;
}
