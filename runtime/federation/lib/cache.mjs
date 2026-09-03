import { sha256Json } from './canonical.mjs';

export function taskFingerprint(task) {
  const dataClass = task.dataClass ?? 'public';
  const scoped = dataClass === 'public' ? null : { tenantId: task.tenantId ?? 'default', dataLocation: task.dataLocation ?? null };
  return sha256Json({ namespace: task.cacheNamespace ?? 'default', capability: task.capability, payload: task.payload ?? null, dataClass, schemaVersion: task.schemaVersion ?? 1, scoped });
}
export class MemoryResultCache {
  constructor({ maxEntries = 10_000, defaultTtlMs = 10 * 60_000 } = {}) { this.maxEntries = maxEntries; this.defaultTtlMs = defaultTtlMs; this.map = new Map(); }
  get(task, now = Date.now()) { if (!cacheable(task)) return null; const key = task.cacheKey ?? taskFingerprint(task); const entry = this.map.get(key); if (!entry) return null; if (entry.expiresAt <= now) { this.map.delete(key); return null; } entry.hits += 1; return structuredClone(entry); }
  set(task, value, { ttlMs = this.defaultTtlMs, now = Date.now() } = {}) { if (!cacheable(task)) return null; const key = task.cacheKey ?? taskFingerprint(task); if (this.map.size >= this.maxEntries && !this.map.has(key)) this.map.delete(this.map.keys().next().value); const entry = { key, taskId: task.id, dataClass: task.dataClass ?? 'public', tenantId: task.tenantId ?? 'default', value: structuredClone(value), createdAt: now, expiresAt: now + Math.max(1, ttlMs), hits: 0 }; this.map.set(key, entry); return structuredClone(entry); }
  deleteByKey(key) { return this.map.delete(key); }
  stats() { return { entries: this.map.size, hits: [...this.map.values()].reduce((n,e) => n + e.hits, 0) }; }
}
function cacheable(task) { if (task.sideEffect === true) return false; const cls = task.dataClass ?? 'public'; if (cls === 'public') return task.cachePolicy === 'public'; if (cls === 'internal') return task.cachePolicy === 'tenant'; if (cls === 'private') return task.cachePolicy === 'private-ok'; return false; }
