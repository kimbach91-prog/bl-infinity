import { validateWorkerEndpoint } from '../lib/network-policy.mjs';

export class RailwayLoopAdapter {
  constructor({ fetchImpl = fetch, defaultTimeoutMs = 30_000 } = {}) {
    this.fetchImpl = fetchImpl;
    this.defaultTimeoutMs = defaultTimeoutMs;
  }

  async execute(provider, task) {
    if (!String(task?.capability || '').startsWith('compute.railway.loop')) {
      throw new Error('railway-loop adapter only supports compute.railway.loop* capabilities');
    }
    const endpoint = await validateWorkerEndpoint(provider.endpoint, {
      allowInsecureLocalhost: false,
      allowPrivateNetwork: false,
      resolveDns: true,
    });
    const requested = Number(task?.payload?.loops ?? 25_000);
    if (!Number.isFinite(requested)) throw new Error('payload.loops must be numeric');
    const loops = Math.max(1_000, Math.min(Math.trunc(requested), 100_000));
    const url = new URL('/compute', endpoint);
    url.searchParams.set('loops', String(loops));
    const timeoutMs = Math.min(task.timeoutMs ?? this.defaultTimeoutMs, provider.limits?.maxExecutionMs ?? Infinity);
    const response = await this.fetchImpl(url, {
      method: 'GET',
      headers: { accept: 'application/json', 'user-agent': 'DEUS-Federation-RailwayLoop/1.0' },
      signal: AbortSignal.timeout(timeoutMs),
      redirect: 'error',
    });
    const text = await response.text();
    let body;
    try { body = text ? JSON.parse(text) : null; } catch { body = { raw: text }; }
    if (!response.ok) throw new Error(`railway loop worker ${provider.id} failed (${response.status})`);
    if (body?.state !== 'EXECUTED') throw new Error(`railway loop worker ${provider.id} returned non-executed state`);
    if (Number(body?.loops) !== loops) throw new Error(`railway loop worker ${provider.id} loop-count mismatch`);
    if (!Number.isFinite(Number(body?.checksum))) throw new Error(`railway loop worker ${provider.id} missing checksum`);
    return {
      providerId: provider.id,
      service: body.service ?? null,
      state: body.state,
      loops,
      checksum: Number(body.checksum),
      durationMs: Number(body.duration_ms ?? 0),
      endpointHost: new URL(endpoint).host,
      truthBoundary: 'BOUNDED_PUBLIC_DETERMINISTIC_CPU_EXECUTION__NOT_ARBITRARY_CODE_OR_GENERAL_WORKER',
    };
  }
}
