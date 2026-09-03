import { createHash } from 'node:crypto';

export function canonicalize(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalize).join(',')}]`;
  const keys = Object.keys(value).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${canonicalize(value[k])}`).join(',')}}`;
}

export function sha256(input) {
  return createHash('sha256').update(input).digest('hex');
}

export function sha256Json(value) {
  return sha256(canonicalize(value));
}

export function clone(value) {
  return structuredClone(value);
}
