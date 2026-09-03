import { randomUUID } from 'node:crypto';
import { sha256Json } from './canonical.mjs';
import { validateTask } from './policy.mjs';

export class MemoryLeaseQueue {
  constructor({ defaultLeaseMs = 30_000, maxAttempts = 3 } = {}) { this.defaultLeaseMs = defaultLeaseMs; this.maxAttempts = maxAttempts; this.jobs = new Map(); this.idempotency = new Map(); }
  enqueue(task, { idempotencyKey = null, priority = 0, maxAttempts = this.maxAttempts, now = Date.now() } = {}) {
    validateTask(task);
    const explicitKey = idempotencyKey ?? task.idempotencyKey ?? null;
    const key = explicitKey ?? (task.sideEffect === true ? `task:${task.id}` : sha256Json({ tenantId: task.tenantId ?? 'default', capability: task.capability, payload: task.payload ?? null, dataClass: task.dataClass ?? 'public', schemaVersion: task.schemaVersion ?? 1 }));
    const existingId = this.idempotency.get(key);
    if (existingId) return { job: this.get(existingId), deduplicated: true };
    const id = task.id; if (this.jobs.has(id)) throw new Error(`job already exists: ${id}`);
    const job = { id, task: structuredClone(task), idempotencyKey: key, state: 'pending', priority: Number(priority) || 0, attempts: 0, maxAttempts, createdAt: new Date(now).toISOString(), availableAt: now, lease: null, result: null, error: null };
    this.jobs.set(id, job); this.idempotency.set(key, id); return { job: this.get(id), deduplicated: false };
  }
  claim(workerId, capabilities = [], { leaseMs = this.defaultLeaseMs, now = Date.now() } = {}) { this.sweepExpired(now); const candidates = [...this.jobs.values()].filter((j) => j.state === 'pending' && j.availableAt <= now && capabilities.includes(j.task.capability)).sort((a, b) => b.priority - a.priority || a.availableAt - b.availableAt || a.createdAt.localeCompare(b.createdAt)); const job = candidates[0]; if (!job) return null; const token = randomUUID(); job.state = 'running'; job.attempts += 1; job.lease = { workerId, token, expiresAt: now + leaseMs, lastHeartbeatAt: now }; return this.get(job.id); }
  heartbeat(jobId, token, { leaseMs = this.defaultLeaseMs, now = Date.now() } = {}) { const job = this.#leased(jobId, token); job.lease.expiresAt = now + leaseMs; job.lease.lastHeartbeatAt = now; return this.get(jobId); }
  complete(jobId, token, result) { const job = this.#leased(jobId, token); job.state = 'succeeded'; job.result = structuredClone(result); job.error = null; job.lease = null; return this.get(jobId); }
  fail(jobId, token, error, { retryDelayMs = 0, now = Date.now() } = {}) { const job = this.#leased(jobId, token); job.error = normalizeError(error); job.lease = null; if (job.attempts >= job.maxAttempts) job.state = 'deadletter'; else { job.state = 'pending'; job.availableAt = now + Math.max(0, retryDelayMs); } return this.get(jobId); }
  sweepExpired(now = Date.now()) { const changed = []; for (const job of this.jobs.values()) { if (job.state !== 'running' || !job.lease || job.lease.expiresAt > now) continue; job.error = { name: 'LeaseExpired', message: 'worker lease expired' }; job.lease = null; if (job.attempts >= job.maxAttempts) job.state = 'deadletter'; else { job.state = 'pending'; job.availableAt = now; } changed.push(job.id); } return changed; }
  get(jobId) { const job = this.jobs.get(jobId); return job ? structuredClone(job) : null; }
  list({ state = null } = {}) { return [...this.jobs.values()].filter((j) => !state || j.state === state).map((j) => structuredClone(j)); }
  #leased(jobId, token) { const job = this.jobs.get(jobId); if (!job) throw new Error(`unknown job: ${jobId}`); if (job.state !== 'running' || !job.lease) throw new Error(`job is not leased: ${jobId}`); if (job.lease.token !== token) throw new Error('invalid lease token'); return job; }
}
function normalizeError(error) { return error && typeof error === 'object' ? { name: error.name ?? 'Error', message: error.message ?? String(error) } : { name: 'Error', message: String(error) }; }
