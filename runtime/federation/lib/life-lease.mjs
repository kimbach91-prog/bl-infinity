import fs from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';

export function createLeaseOwnerId(prefix = 'deus-life') {
  return `${prefix}:${process.pid}:${randomUUID()}`;
}

export async function acquireLease({ leasePath, ownerId, ttlMs = 90_000, now = () => Date.now() }) {
  if (!leasePath) throw new Error('leasePath is required');
  if (!ownerId) throw new Error('ownerId is required');
  if (!Number.isFinite(ttlMs) || ttlMs < 10_000) throw new Error('lease ttl must be at least 10000 ms');
  await fs.mkdir(path.dirname(leasePath), { recursive: true });

  for (let attempt = 0; attempt < 3; attempt += 1) {
    const lease = makeLease(ownerId, ttlMs, now());
    try {
      await fs.writeFile(leasePath, `${JSON.stringify(lease)}\n`, { encoding: 'utf8', flag: 'wx' });
      return lease;
    } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      const existing = await readLease(leasePath);
      const current = now();
      if (existing && existing.expiresAt > current && existing.ownerId !== ownerId) {
        const conflict = new Error(`life lease held by ${existing.ownerId}`);
        conflict.code = 'LIFE_LEASE_HELD';
        conflict.lease = existing;
        throw conflict;
      }
      try { await fs.unlink(leasePath); }
      catch (unlinkError) { if (unlinkError.code !== 'ENOENT') throw unlinkError; }
    }
  }
  throw new Error('failed to acquire life lease after retries');
}

export async function refreshLease({ leasePath, ownerId, ttlMs = 90_000, now = () => Date.now() }) {
  const existing = await readLease(leasePath);
  if (!existing || existing.ownerId !== ownerId) {
    const error = new Error('life lease ownership lost');
    error.code = 'LIFE_LEASE_LOST';
    error.lease = existing;
    throw error;
  }
  const lease = makeLease(ownerId, ttlMs, now(), existing.acquiredAt);
  const tmp = `${leasePath}.${process.pid}.tmp`;
  await fs.writeFile(tmp, `${JSON.stringify(lease)}\n`, 'utf8');
  const check = await readLease(leasePath);
  if (!check || check.ownerId !== ownerId) {
    await fs.rm(tmp, { force: true });
    const error = new Error('life lease changed during refresh');
    error.code = 'LIFE_LEASE_LOST';
    throw error;
  }
  await fs.rename(tmp, leasePath);
  return lease;
}

export async function releaseLease({ leasePath, ownerId }) {
  const existing = await readLease(leasePath);
  if (!existing || existing.ownerId !== ownerId) return false;
  try { await fs.unlink(leasePath); return true; }
  catch (error) { if (error.code === 'ENOENT') return false; throw error; }
}

export async function readLease(leasePath) {
  try {
    const raw = await fs.readFile(leasePath, 'utf8');
    const lease = JSON.parse(raw);
    if (!lease || typeof lease.ownerId !== 'string' || !Number.isFinite(lease.expiresAt)) return null;
    return lease;
  } catch (error) {
    if (error.code === 'ENOENT') return null;
    if (error instanceof SyntaxError) return null;
    throw error;
  }
}

function makeLease(ownerId, ttlMs, now, acquiredAt = now) {
  return { ownerId, acquiredAt, refreshedAt: now, expiresAt: now + ttlMs };
}
