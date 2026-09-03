import { sign, verify, createPublicKey } from 'node:crypto';
import { canonicalize } from './canonical.mjs';

export const MANIFEST_VERSION = 'bl-cf-provider/v1';

export function providerGrantPayload(manifest) {
  const { signature: _signature, telemetry: _telemetry, runtime: _runtime, status: _status, ...grant } = structuredClone(manifest);
  return grant;
}

export function validateProviderGrant(manifest, now = Date.now()) {
  if (!manifest || typeof manifest !== 'object') throw new Error('provider manifest is required');
  if (manifest.manifestVersion !== MANIFEST_VERSION) throw new Error(`manifestVersion must be ${MANIFEST_VERSION}`);
  for (const key of ['id', 'kind', 'capabilities', 'authorization', 'limits']) if (manifest[key] == null) throw new Error(`provider.${key} is required`);
  if (!/^[a-zA-Z0-9._:-]{2,128}$/.test(manifest.id)) throw new Error('provider.id has invalid format');
  if (!Array.isArray(manifest.capabilities) || manifest.capabilities.length === 0) throw new Error('provider.capabilities must be non-empty');
  if (!manifest.authorization.consentRef) throw new Error('provider.authorization.consentRef is required');
  if (!manifest.authorization.grantor) throw new Error('provider.authorization.grantor is required');
  if (!manifest.authorization.grantedAt || Number.isNaN(Date.parse(manifest.authorization.grantedAt))) throw new Error('provider.authorization.grantedAt must be an ISO date');
  if (manifest.authorization.expiresAt) {
    const expires = Date.parse(manifest.authorization.expiresAt);
    if (Number.isNaN(expires)) throw new Error('provider.authorization.expiresAt must be an ISO date');
    if (expires <= now) throw new Error('provider authorization is expired');
  }
  if (manifest.authorization.revokedAt) throw new Error('provider authorization is revoked');
  if (!Number.isFinite(Number(manifest.limits.maxConcurrency)) || Number(manifest.limits.maxConcurrency) < 1) throw new Error('provider.limits.maxConcurrency must be >= 1');
  if (manifest.endpoint) {
    const url = new URL(manifest.endpoint);
    if (!['https:', 'http:'].includes(url.protocol)) throw new Error('provider.endpoint must be http(s)');
  }
  return true;
}

export function signProviderManifest(manifest, privateKeyPem, keyId) {
  validateProviderGrant(manifest, 0);
  if (!keyId) throw new Error('keyId is required');
  const payload = Buffer.from(canonicalize(providerGrantPayload(manifest)));
  const signature = sign(null, payload, privateKeyPem).toString('base64url');
  return { ...structuredClone(manifest), signature: { algorithm: 'ed25519', keyId, value: signature } };
}

export function verifyProviderManifest(manifest, trustStore, { now = Date.now(), requireSignature = true } = {}) {
  validateProviderGrant(manifest, now);
  if (!manifest.signature) return requireSignature ? { ok: false, reason: 'missing-signature' } : { ok: true, unsigned: true };
  const { algorithm, keyId, value } = manifest.signature;
  if (algorithm !== 'ed25519') return { ok: false, reason: 'unsupported-signature-algorithm' };
  const publicKeyPem = trustStore instanceof Map ? trustStore.get(keyId) : trustStore?.[keyId];
  if (!publicKeyPem) return { ok: false, reason: 'untrusted-key', keyId };
  const payload = Buffer.from(canonicalize(providerGrantPayload(manifest)));
  const ok = verify(null, payload, createPublicKey(publicKeyPem), Buffer.from(value, 'base64url'));
  return ok ? { ok: true, keyId } : { ok: false, reason: 'bad-signature', keyId };
}
