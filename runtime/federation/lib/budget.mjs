import { randomUUID } from 'node:crypto';

export class BudgetGovernor {
  constructor({ totalUsd = Infinity, perTenantUsd = {}, perProviderUsd = {} } = {}) {
    this.totalUsd = Number(totalUsd);
    this.perTenantUsd = new Map(Object.entries(perTenantUsd).map(([k,v]) => [k, Number(v)]));
    this.perProviderUsd = new Map(Object.entries(perProviderUsd).map(([k,v]) => [k, Number(v)]));
    this.spentTotal = 0; this.spentTenant = new Map(); this.spentProvider = new Map();
    this.reservedTotal = 0; this.reservedTenant = new Map(); this.reservedProvider = new Map(); this.reservations = new Map();
  }
  reserve({ amountUsd = 0, tenantId = 'default', providerId = null, taskId = null } = {}) {
    const amount = Number(amountUsd); if (!Number.isFinite(amount) || amount < 0) throw new Error('budget amount must be >= 0');
    const verdict = this.canSpend({ amountUsd: amount, tenantId, providerId }); if (!verdict.ok) return verdict;
    const id = randomUUID(); const r = { id, amountUsd: amount, tenantId, providerId, taskId, state: 'reserved', createdAt: new Date().toISOString() };
    this.reservations.set(id, r); this.reservedTotal += amount; inc(this.reservedTenant, tenantId, amount); if (providerId) inc(this.reservedProvider, providerId, amount);
    return { ok: true, reservation: structuredClone(r) };
  }
  canSpend({ amountUsd = 0, tenantId = 'default', providerId = null } = {}) {
    const amount = Number(amountUsd);
    if (this.spentTotal + this.reservedTotal + amount > this.totalUsd) return { ok: false, reason: 'global-budget-exceeded' };
    const tenantLimit = this.perTenantUsd.get(tenantId) ?? Infinity;
    if ((this.spentTenant.get(tenantId) ?? 0) + (this.reservedTenant.get(tenantId) ?? 0) + amount > tenantLimit) return { ok: false, reason: 'tenant-budget-exceeded' };
    if (providerId) { const providerLimit = this.perProviderUsd.get(providerId) ?? Infinity; if ((this.spentProvider.get(providerId) ?? 0) + (this.reservedProvider.get(providerId) ?? 0) + amount > providerLimit) return { ok: false, reason: 'provider-budget-exceeded' }; }
    return { ok: true };
  }
  commit(id, actualUsd = null) { const r = this.#active(id); const actual = actualUsd == null ? r.amountUsd : Number(actualUsd); if (!Number.isFinite(actual) || actual < 0) throw new Error('actualUsd must be >= 0'); this.#releaseReserved(r); r.state = 'committed'; r.actualUsd = actual; r.committedAt = new Date().toISOString(); this.spentTotal += actual; inc(this.spentTenant, r.tenantId, actual); if (r.providerId) inc(this.spentProvider, r.providerId, actual); return structuredClone(r); }
  release(id, reason = 'released') { const r = this.#active(id); this.#releaseReserved(r); r.state = 'released'; r.releaseReason = reason; r.releasedAt = new Date().toISOString(); return structuredClone(r); }
  snapshot() { return { limits: { totalUsd: this.totalUsd, perTenantUsd: Object.fromEntries(this.perTenantUsd), perProviderUsd: Object.fromEntries(this.perProviderUsd) }, spent: { totalUsd: this.spentTotal, perTenantUsd: Object.fromEntries(this.spentTenant), perProviderUsd: Object.fromEntries(this.spentProvider) }, reserved: { totalUsd: this.reservedTotal, perTenantUsd: Object.fromEntries(this.reservedTenant), perProviderUsd: Object.fromEntries(this.reservedProvider) } }; }
  #active(id) { const r = this.reservations.get(id); if (!r) throw new Error(`unknown reservation: ${id}`); if (r.state !== 'reserved') throw new Error(`reservation is ${r.state}`); return r; }
  #releaseReserved(r) { this.reservedTotal -= r.amountUsd; inc(this.reservedTenant, r.tenantId, -r.amountUsd); if (r.providerId) inc(this.reservedProvider, r.providerId, -r.amountUsd); }
}
function inc(map, key, value) { const next = (map.get(key) ?? 0) + value; if (Math.abs(next) < 1e-12) map.delete(key); else map.set(key, next); }
