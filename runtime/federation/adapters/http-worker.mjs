import { buildTransportHeaders } from '../lib/auth.mjs';
import { validateWorkerEndpoint } from '../lib/network-policy.mjs';

export class HttpWorkerAdapter {
  constructor({ fetchImpl = fetch, env = process.env, defaultTimeoutMs = 30_000, allowInsecureLocalhost = true, resolveDns = true } = {}) { this.fetchImpl = fetchImpl; this.env = env; this.defaultTimeoutMs = defaultTimeoutMs; this.allowInsecureLocalhost = allowInsecureLocalhost; this.resolveDns = resolveDns; }
  async execute(provider, task) {
    const endpoint = await validateWorkerEndpoint(provider.endpoint, { allowInsecureLocalhost: this.allowInsecureLocalhost, allowPrivateNetwork: provider.transport?.allowPrivateNetwork === true, resolveDns: this.resolveDns });
    const url = new URL('/v1/execute', endpoint);
    const body = JSON.stringify({ task: sanitizeTask(task) });
    const headers = await buildTransportHeaders(provider, body, this.env);
    const timeoutMs = Math.min(task.timeoutMs ?? this.defaultTimeoutMs, provider.limits?.maxExecutionMs ?? Infinity);
    const response = await this.fetchImpl(url, { method: 'POST', headers, body, signal: AbortSignal.timeout(timeoutMs), redirect: 'error' });
    const text = await response.text(); let parsed; try { parsed = text ? JSON.parse(text) : null; } catch { parsed = { raw: text }; }
    if (!response.ok) throw new Error(`worker ${provider.id} failed (${response.status}): ${parsed?.error ?? text}`);
    return parsed?.result ?? parsed;
  }
}
function sanitizeTask(task) { const allowed = ['id', 'capability', 'payload', 'dataClass', 'deadlineAt', 'timeoutMs', 'traceId', 'idempotencyKey', 'schemaVersion']; return Object.fromEntries(allowed.filter((k) => task[k] !== undefined).map((k) => [k, structuredClone(task[k])])); }
