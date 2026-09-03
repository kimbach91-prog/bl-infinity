import { createHeartbeatNonce, signProviderHeartbeat } from '../lib/provider-heartbeat.mjs';

export function createProviderHeartbeatClient({
  providerId,
  heartbeatUrl,
  secret,
  intervalMs = 20_000,
  timeoutMs = 5_000,
  getInFlight = () => 0,
  fetchImpl = globalThis.fetch,
  onError = (error) => console.warn(`provider heartbeat failed: ${error.message}`),
} = {}) {
  if (!providerId) throw new Error('heartbeat providerId is required');
  if (!heartbeatUrl) throw new Error('heartbeat URL is required');
  if (!secret) throw new Error('heartbeat secret is required');
  if (typeof fetchImpl !== 'function') throw new Error('fetch implementation is required');
  validateHeartbeatUrl(heartbeatUrl);
  const interval = boundedMs(intervalMs, 5_000, 60 * 60_000, 'heartbeat interval');
  const timeout = boundedMs(timeoutMs, 500, 60_000, 'heartbeat timeout');
  let timer = null;
  let stopped = true;
  let running = false;

  async function beat({ now = Date.now() } = {}) {
    const inFlight = nonNegativeInteger(getInFlight(), 'inFlight');
    const body = JSON.stringify({ providerId, inFlight });
    const nonce = createHeartbeatNonce();
    const signature = signProviderHeartbeat(secret, { providerId, timestamp: now, nonce, body });
    const response = await fetchImpl(heartbeatUrl, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-bl-provider-id': providerId,
        'x-bl-timestamp': String(now),
        'x-bl-nonce': nonce,
        'x-bl-heartbeat-signature': signature,
      },
      body,
      signal: AbortSignal.timeout(timeout),
    });
    const text = await response.text();
    let parsed = null;
    try { parsed = text ? JSON.parse(text) : null; } catch { parsed = { raw: text }; }
    if (!response.ok) {
      const error = new Error(parsed?.error ?? `heartbeat HTTP ${response.status}`);
      error.status = response.status;
      error.response = parsed;
      throw error;
    }
    return parsed;
  }

  async function loop() {
    if (stopped || running) return;
    running = true;
    try { await beat(); }
    catch (error) { onError?.(error); }
    finally {
      running = false;
      if (!stopped) timer = setTimeout(loop, interval);
    }
  }

  function start() {
    if (!stopped) return;
    stopped = false;
    timer = setTimeout(loop, 0);
  }

  function stop() {
    stopped = true;
    if (timer) clearTimeout(timer);
    timer = null;
  }

  return { beat, start, stop, get running() { return running; } };
}

export function createProviderHeartbeatClientFromEnv({ env = process.env, getInFlight = () => 0, fetchImpl = globalThis.fetch, onError } = {}) {
  const providerId = env.BL_PROVIDER_ID;
  const heartbeatUrl = env.BL_HEARTBEAT_URL;
  const secretEnv = env.BL_HEARTBEAT_SECRET_ENV;
  if (!providerId && !heartbeatUrl && !secretEnv) return null;
  if (!providerId || !heartbeatUrl || !secretEnv) throw new Error('BL_PROVIDER_ID, BL_HEARTBEAT_URL and BL_HEARTBEAT_SECRET_ENV must be set together');
  const secret = env[secretEnv];
  if (!secret) throw new Error(`heartbeat secret environment variable is missing: ${secretEnv}`);
  return createProviderHeartbeatClient({
    providerId,
    heartbeatUrl,
    secret,
    intervalMs: Number(env.BL_HEARTBEAT_INTERVAL_MS || 20_000),
    timeoutMs: Number(env.BL_HEARTBEAT_TIMEOUT_MS || 5_000),
    getInFlight,
    fetchImpl,
    onError,
  });
}

function validateHeartbeatUrl(value) {
  const url = new URL(value);
  if (url.protocol === 'https:') return true;
  if (url.protocol === 'http:' && isLoopback(url.hostname)) return true;
  throw new Error('heartbeat URL must use HTTPS except for localhost development');
}
function isLoopback(hostname) { const h = String(hostname).replace(/^\[|\]$/g, '').toLowerCase(); return h === 'localhost' || h === '127.0.0.1' || h === '::1'; }
function boundedMs(value, min, max, name) { const n = Number(value); if (!Number.isFinite(n) || n < min || n > max) throw new Error(`${name} must be between ${min} and ${max} ms`); return n; }
function nonNegativeInteger(value, name) { const n = Number(value); if (!Number.isSafeInteger(n) || n < 0) throw new Error(`${name} must be a non-negative integer`); return n; }
