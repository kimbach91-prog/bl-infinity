import { randomUUID } from 'node:crypto';
import { canonicalize, sha256 } from './canonical.mjs';

export class ContributionLedger {
  constructor() { this.entries = []; }
  record({ taskId, providerId, consentRef, tenantId = 'default', measuredLatencyMs = 0, billedCostUsd = 0, inputBytes = 0, outputBytes = 0, reportedUsage = null, status = 'succeeded' }) {
    const prevHash = this.entries.at(-1)?.hash ?? null;
    const core = { id: randomUUID(), seq: this.entries.length + 1, ts: new Date().toISOString(), taskId, providerId, consentRef, tenantId, measuredLatencyMs: Math.max(0, Number(measuredLatencyMs) || 0), billedCostUsd: Math.max(0, Number(billedCostUsd) || 0), inputBytes: Math.max(0, Number(inputBytes) || 0), outputBytes: Math.max(0, Number(outputBytes) || 0), reportedUsage: reportedUsage ? structuredClone(reportedUsage) : null, status, prevHash };
    const entry = { ...core, hash: sha256(canonicalize(core)) }; this.entries.push(entry); return structuredClone(entry);
  }
  list({ providerId = null, tenantId = null } = {}) { return this.entries.filter((e) => (!providerId || e.providerId === providerId) && (!tenantId || e.tenantId === tenantId)).map((e) => structuredClone(e)); }
  summary() { const out = {}; for (const e of this.entries) { const x = out[e.providerId] ??= { tasks: 0, success: 0, failure: 0, measuredLatencyMs: 0, billedCostUsd: 0, inputBytes: 0, outputBytes: 0 }; x.tasks += 1; x[e.status === 'succeeded' ? 'success' : 'failure'] += 1; x.measuredLatencyMs += e.measuredLatencyMs; x.billedCostUsd += e.billedCostUsd; x.inputBytes += e.inputBytes; x.outputBytes += e.outputBytes; } return out; }
}

export function verifyContributionLedger(entries) {
  let prevHash = null;
  let prevSeq = 0;
  for (let i = 0; i < entries.length; i += 1) {
    const entry = entries[i];
    if (!Number.isSafeInteger(entry.seq) || entry.seq <= prevSeq) return { ok: false, index: i, reason: 'sequence' };
    if (entry.prevHash !== prevHash) return { ok: false, index: i, reason: 'prevHash' };
    const { hash, ...core } = entry;
    if (sha256(canonicalize(core)) !== hash) return { ok: false, index: i, reason: 'hash' };
    prevSeq = entry.seq;
    prevHash = hash;
  }
  return { ok: true, records: entries.length, head: prevHash, lastSeq: prevSeq };
}
