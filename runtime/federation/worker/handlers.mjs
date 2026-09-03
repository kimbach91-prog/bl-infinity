import { createHash } from 'node:crypto';

export const safeDefaultHandlers = {
  'compute.echo': async (payload) => structuredClone(payload),
  'compute.sha256': async (payload) => {
    const input = typeof payload === 'string' ? payload : JSON.stringify(payload);
    return { sha256: createHash('sha256').update(input).digest('hex') };
  },
  'text.stats': async (payload) => {
    const text = String(payload?.text ?? payload ?? '');
    const words = text.trim() ? text.trim().split(/\s+/u) : [];
    return { chars: [...text].length, words: words.length, lines: text ? text.split(/\r?\n/).length : 0 };
  },
  'json.project': async (payload) => {
    const source = payload?.source;
    const fields = Array.isArray(payload?.fields) ? payload.fields : [];
    if (!source || typeof source !== 'object' || Array.isArray(source)) throw new Error('json.project source must be an object');
    if (fields.length > 100) throw new Error('json.project too many fields');
    const out = {};
    for (const field of fields) if (Object.hasOwn(source, field)) out[field] = source[field];
    return out;
  },
};
