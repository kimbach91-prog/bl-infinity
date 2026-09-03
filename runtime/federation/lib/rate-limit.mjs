export class TokenBucketLimiter {
  constructor({ capacity = 120, refillPerSecond = 2, maxKeys = 10_000 } = {}) { this.capacity = capacity; this.refillPerSecond = refillPerSecond; this.maxKeys = maxKeys; this.map = new Map(); }
  take(key, cost = 1, now = Date.now()) {
    let b = this.map.get(key);
    if (!b) { if (this.map.size >= this.maxKeys) this.map.delete(this.map.keys().next().value); b = { tokens: this.capacity, updatedAt: now }; this.map.set(key, b); }
    const elapsed = Math.max(0, now - b.updatedAt) / 1000; b.tokens = Math.min(this.capacity, b.tokens + elapsed * this.refillPerSecond); b.updatedAt = now;
    if (b.tokens < cost) return { ok: false, retryAfterMs: Math.ceil((cost - b.tokens) / Math.max(0.0001, this.refillPerSecond) * 1000) };
    b.tokens -= cost; return { ok: true, remaining: Math.floor(b.tokens) };
  }
}
