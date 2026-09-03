import { timingSafeEqual } from 'node:crypto';
export function bearerToken(req) { const value = req.headers?.authorization || ''; return value.startsWith('Bearer ') ? value.slice(7) : null; }
export function secureTokenEqual(a, b) { if (typeof a !== 'string' || typeof b !== 'string') return false; const aa = Buffer.from(a), bb = Buffer.from(b); return aa.length === bb.length && timingSafeEqual(aa, bb); }
export function hasControlAccess(req, configuredToken) { return Boolean(configuredToken && secureTokenEqual(bearerToken(req), configuredToken)); }
