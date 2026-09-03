function clamp01(x) { return Math.max(0, Math.min(1, Number(x))); }
function ewma(oldValue, sample, alpha) { return oldValue == null || !Number.isFinite(oldValue) ? sample : alpha * sample + (1 - alpha) * oldValue; }

export class TelemetryBook {
  constructor({ alpha = 0.2, latencyWindow = 64 } = {}) { this.alpha = alpha; this.latencyWindow = latencyWindow; this.map = new Map(); }
  ensure(providerId, seed = {}) {
    if (!this.map.has(providerId)) this.map.set(providerId, { availability: seed.availability ?? 1, trust: seed.trust ?? 0.5, p95LatencyMs: seed.p95LatencyMs ?? 1000, costPerUnitUsd: seed.costPerUnitUsd ?? 0, inFlight: seed.inFlight ?? 0, successes: 0, failures: 0, latencies: [], lastSeenAt: null });
    return this.map.get(providerId);
  }
  begin(providerId) { const t = this.ensure(providerId); t.inFlight += 1; t.lastSeenAt = new Date().toISOString(); }
  success(providerId, { latencyMs, costUsd = 0 } = {}) {
    const t = this.ensure(providerId); t.inFlight = Math.max(0, t.inFlight - 1); t.successes += 1; t.availability = clamp01(ewma(t.availability, 1, this.alpha)); t.trust = clamp01(ewma(t.trust, 1, this.alpha / 2));
    if (Number.isFinite(latencyMs)) { t.latencies.push(Math.max(0, latencyMs)); if (t.latencies.length > this.latencyWindow) t.latencies.shift(); t.p95LatencyMs = percentile(t.latencies, 0.95); }
    if (Number.isFinite(costUsd)) t.costPerUnitUsd = ewma(t.costPerUnitUsd, Math.max(0, costUsd), this.alpha);
    t.lastSeenAt = new Date().toISOString();
  }
  failure(providerId, { latencyMs } = {}) {
    const t = this.ensure(providerId); t.inFlight = Math.max(0, t.inFlight - 1); t.failures += 1; t.availability = clamp01(ewma(t.availability, 0, this.alpha)); t.trust = clamp01(ewma(t.trust, 0, this.alpha / 3));
    if (Number.isFinite(latencyMs)) { t.latencies.push(Math.max(0, latencyMs)); if (t.latencies.length > this.latencyWindow) t.latencies.shift(); t.p95LatencyMs = percentile(t.latencies, 0.95); }
    t.lastSeenAt = new Date().toISOString();
  }
  snapshot(providerId) { const t = this.ensure(providerId); const { latencies: _latencies, ...publicFields } = t; return structuredClone(publicFields); }
}

function percentile(values, q) { if (!values.length) return 0; const sorted = [...values].sort((a, b) => a - b); const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil(q * sorted.length) - 1)); return sorted[idx]; }
