import { appendFile } from 'node:fs/promises';
import { canonicalize, sha256 } from './canonical.mjs';

function makeRecord(seq, type, data, prevHash, ts = new Date().toISOString()) {
  const core = { seq, ts, type, data, prevHash };
  return { ...core, hash: sha256(canonicalize(core)) };
}

export class MemoryAuditLog {
  constructor(seed = []) {
    this.records = [];
    for (const record of seed) this.records.push(structuredClone(record));
    if (!verifyAuditChain(this.records).ok) throw new Error('invalid seed audit chain');
  }

  async append(type, data) {
    const prev = this.records.at(-1)?.hash ?? null;
    const record = makeRecord(this.records.length + 1, type, structuredClone(data), prev);
    this.records.push(record);
    return structuredClone(record);
  }

  list() {
    return structuredClone(this.records);
  }
}

export class JsonlAuditLog extends MemoryAuditLog {
  constructor(path, seed = []) {
    super(seed);
    this.path = path;
  }

  async append(type, data) {
    const record = await super.append(type, data);
    await appendFile(this.path, `${JSON.stringify(record)}\n`, { encoding: 'utf8', mode: 0o600 });
    return record;
  }
}

export function verifyAuditChain(records) {
  let prevHash = null;
  for (let i = 0; i < records.length; i += 1) {
    const record = records[i];
    if (record.seq !== i + 1) return { ok: false, index: i, reason: 'sequence' };
    if (record.prevHash !== prevHash) return { ok: false, index: i, reason: 'prevHash' };
    const { hash, ...core } = record;
    if (sha256(canonicalize(core)) !== hash) return { ok: false, index: i, reason: 'hash' };
    prevHash = hash;
  }
  return { ok: true, records: records.length, head: prevHash };
}
