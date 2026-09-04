import crypto from 'node:crypto';

function normalizeScalar(value) {
  if (typeof value === 'string') return value.normalize('NFC');
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error('HCS_CANONICAL_NON_FINITE_NUMBER');
    return Object.is(value, -0) ? 0 : value;
  }
  if (value === null || typeof value === 'boolean') return value;
  if (value === undefined) throw new Error('HCS_CANONICAL_UNDEFINED_FORBIDDEN');
  return value;
}

export function canonicalizeHcs(value) {
  const walk = (v) => {
    v = normalizeScalar(v);
    if (Array.isArray(v)) return v.map(walk);
    if (v && typeof v === 'object') {
      const normalizedEntries = Object.entries(v).map(([k,val]) => [k.normalize('NFC'), val]);
      const seen = new Set();
      for (const [k] of normalizedEntries) {
        if (seen.has(k)) throw new Error(`HCS_CANONICAL_DUPLICATE_KEY_AFTER_NFC:${k}`);
        seen.add(k);
      }
      normalizedEntries.sort(([a],[b]) => a < b ? -1 : a > b ? 1 : 0);
      const out = {};
      for (const [k,val] of normalizedEntries) out[k] = walk(val);
      return out;
    }
    return v;
  };
  return JSON.stringify(walk(value));
}

export function canonicalBytesHcs(value) {
  return Buffer.from(canonicalizeHcs(value), 'utf8');
}

export function sha256Hcs(value) {
  return crypto.createHash('sha256').update(canonicalBytesHcs(value)).digest('hex');
}
