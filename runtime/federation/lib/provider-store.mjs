import { canonicalize, sha256 } from './canonical.mjs';
import { providerGrantPayload, validateProviderGrant } from './manifest.mjs';

const HEARTBEAT_MIN_MS = 5_000;
const HEARTBEAT_MAX_MS = 24 * 60 * 60_000;

export class PostgresProviderStore {
  constructor(pool, { manifestVerifier = null, defaultHeartbeatTtlMs = 60_000 } = {}) {
    if (!pool?.query) throw new Error('Postgres pool is required');
    this.pool = pool;
    this.manifestVerifier = manifestVerifier;
    this.defaultHeartbeatTtlMs = clampHeartbeatTtl(defaultHeartbeatTtlMs);
  }

  async put(manifest, { replace = false, source = 'operator', now = Date.now() } = {}) {
    validateProviderGrant(manifest, now);
    if (this.manifestVerifier) {
      const verdict = this.manifestVerifier(manifest);
      if (!verdict?.ok) throw taggedError('PROVIDER_MANIFEST_REJECTED', `provider manifest rejected: ${verdict?.reason ?? 'unknown'}`);
    }
    const grant = providerGrantPayload(manifest);
    const grantHash = sha256(canonicalize(grant));
    const signature = manifest.signature ? structuredClone(manifest.signature) : null;
    const seedTelemetry = sanitizeMeasuredTelemetry(manifest.telemetry ?? {});
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const existing = await client.query('SELECT * FROM federation_providers WHERE id=$1 FOR UPDATE', [manifest.id]);
      if (!existing.rowCount) {
        const inserted = await client.query(`
          INSERT INTO federation_providers
            (id,grant_json,signature_json,grant_hash,consent_ref,key_id,status,source,revision,telemetry_json,registered_at,updated_at,grant_expires_at)
          VALUES($1,$2::jsonb,$3::jsonb,$4,$5,$6,'active',$7,1,$8::jsonb,$9,$9,$10)
          RETURNING *
        `, [manifest.id, JSON.stringify(grant), signature ? JSON.stringify(signature) : null, grantHash, grant.authorization.consentRef, signature?.keyId ?? null, source, JSON.stringify(seedTelemetry), new Date(now), grant.authorization.expiresAt ? new Date(grant.authorization.expiresAt) : null]);
        await client.query('COMMIT');
        return rowToProvider(inserted.rows[0], now);
      }

      const row = existing.rows[0];
      if (row.status === 'revoked' && !replace) throw taggedError('PROVIDER_REVOKED', `provider is revoked: ${manifest.id}`);
      if (row.grant_hash !== grantHash && !replace) throw taggedError('PROVIDER_GRANT_CONFLICT', `provider grant differs for id: ${manifest.id}`);
      if (row.grant_hash === grantHash) {
        const updated = await client.query(`
          UPDATE federation_providers
          SET signature_json=COALESCE($1::jsonb,signature_json), key_id=COALESCE($2,key_id), updated_at=$3
          WHERE id=$4 RETURNING *
        `, [signature ? JSON.stringify(signature) : null, signature?.keyId ?? null, new Date(now), manifest.id]);
        await client.query('COMMIT');
        return rowToProvider(updated.rows[0], now);
      }

      const updated = await client.query(`
        UPDATE federation_providers
        SET grant_json=$1::jsonb, signature_json=$2::jsonb, grant_hash=$3, consent_ref=$4, key_id=$5,
            status='active', source=$6, revision=revision+1, telemetry_json=$7::jsonb,
            updated_at=$8, grant_expires_at=$9, revoked_at=NULL, revoke_reason=NULL,
            last_heartbeat_at=NULL, heartbeat_expires_at=NULL, heartbeat_seq=0
        WHERE id=$10 RETURNING *
      `, [JSON.stringify(grant), signature ? JSON.stringify(signature) : null, grantHash, grant.authorization.consentRef, signature?.keyId ?? null, source, JSON.stringify(seedTelemetry), new Date(now), grant.authorization.expiresAt ? new Date(grant.authorization.expiresAt) : null, manifest.id]);
      await client.query('COMMIT');
      return rowToProvider(updated.rows[0], now);
    } catch (error) {
      try { await client.query('ROLLBACK'); } catch {}
      throw error;
    } finally {
      client.release();
    }
  }

  async heartbeat(providerId, { inFlight = null } = {}, { now = Date.now() } = {}) {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const found = await client.query('SELECT * FROM federation_providers WHERE id=$1 FOR UPDATE', [providerId]);
      if (found.rowCount !== 1) throw taggedError('UNKNOWN_PROVIDER', `unknown provider: ${providerId}`);
      const row = found.rows[0];
      if (row.status === 'revoked') throw taggedError('PROVIDER_REVOKED', `provider is revoked: ${providerId}`);
      const grant = row.grant_json;
      const ttlMs = clampHeartbeatTtl(grant.liveness?.heartbeatTtlMs ?? this.defaultHeartbeatTtlMs);
      const telemetry = { ...(row.telemetry_json ?? {}) };
      if (inFlight != null) telemetry.inFlight = nonNegativeNumber(inFlight, 'inFlight');
      telemetry.availability = 1;
      const updated = await client.query(`
        UPDATE federation_providers
        SET telemetry_json=$1::jsonb, last_heartbeat_at=$2, heartbeat_expires_at=$3,
            heartbeat_seq=heartbeat_seq+1, updated_at=$2
        WHERE id=$4 RETURNING *
      `, [JSON.stringify(telemetry), new Date(now), new Date(now + ttlMs), providerId]);
      await client.query('COMMIT');
      return rowToProvider(updated.rows[0], now);
    } catch (error) {
      try { await client.query('ROLLBACK'); } catch {}
      throw error;
    } finally {
      client.release();
    }
  }

  async updateMeasuredTelemetry(providerId, telemetry, { now = Date.now() } = {}) {
    const safe = sanitizeMeasuredTelemetry(telemetry);
    const result = await this.pool.query(`
      UPDATE federation_providers
      SET telemetry_json=COALESCE(telemetry_json,'{}'::jsonb) || $1::jsonb, updated_at=$2
      WHERE id=$3 AND status <> 'revoked'
      RETURNING *
    `, [JSON.stringify(safe), new Date(now), providerId]);
    if (result.rowCount !== 1) throw taggedError('UNKNOWN_OR_REVOKED_PROVIDER', `unknown or revoked provider: ${providerId}`);
    return rowToProvider(result.rows[0], now);
  }

  async setStatus(providerId, status, { now = Date.now() } = {}) {
    if (!['active','disabled'].includes(status)) throw new Error('provider status must be active or disabled');
    const result = await this.pool.query(`
      UPDATE federation_providers
      SET status=$1, updated_at=$2
      WHERE id=$3 AND status <> 'revoked' AND (grant_expires_at IS NULL OR grant_expires_at > $2)
      RETURNING *
    `, [status, new Date(now), providerId]);
    if (result.rowCount !== 1) throw taggedError('PROVIDER_STATUS_REJECTED', `provider cannot transition to ${status}: ${providerId}`);
    return rowToProvider(result.rows[0], now);
  }

  async revoke(providerId, reason = 'revoked', { now = Date.now() } = {}) {
    const result = await this.pool.query(`
      UPDATE federation_providers
      SET status='revoked', revoked_at=COALESCE(revoked_at,$1), revoke_reason=COALESCE(revoke_reason,$2), updated_at=$1
      WHERE id=$3
      RETURNING *
    `, [new Date(now), String(reason || 'revoked'), providerId]);
    if (result.rowCount !== 1) throw taggedError('UNKNOWN_PROVIDER', `unknown provider: ${providerId}`);
    return rowToProvider(result.rows[0], now);
  }

  async get(providerId, { now = Date.now() } = {}) {
    const result = await this.pool.query('SELECT * FROM federation_providers WHERE id=$1', [providerId]);
    return result.rowCount ? rowToProvider(result.rows[0], now) : null;
  }

  async list({ includeInactive = true, now = Date.now() } = {}) {
    const result = await this.pool.query('SELECT * FROM federation_providers ORDER BY id');
    const providers = result.rows.map((row) => rowToProvider(row, now));
    return includeInactive ? providers : providers.filter(isEffectivelyActive);
  }
}

export async function syncProviderRegistry(registry, store, { now = Date.now() } = {}) {
  const providers = await store.list({ includeInactive: true, now });
  let active = 0, disabled = 0, skipped = 0;
  for (const provider of providers) {
    if (isEffectivelyActive(provider)) {
      registry.register(provider);
      active += 1;
      continue;
    }
    const existing = registry.get(provider.id);
    if (existing) {
      registry.disable(provider.id);
      disabled += 1;
    } else {
      skipped += 1;
    }
  }
  return { total: providers.length, active, disabled, skipped };
}

export function isEffectivelyActive(provider) {
  if (!provider || provider.status === 'disabled') return false;
  if (provider.authorization?.revokedAt) return false;
  if (provider.authorization?.expiresAt && Date.parse(provider.authorization.expiresAt) <= Date.now()) return false;
  return true;
}

function rowToProvider(row, now = Date.now()) {
  const grant = structuredClone(row.grant_json);
  const signature = row.signature_json ? structuredClone(row.signature_json) : null;
  const telemetry = { ...(row.telemetry_json ?? {}) };
  const grantExpired = row.grant_expires_at ? new Date(row.grant_expires_at).getTime() <= now : false;
  const heartbeatRequired = grant.liveness?.heartbeatRequired === true;
  const heartbeatFresh = row.heartbeat_expires_at ? new Date(row.heartbeat_expires_at).getTime() > now : false;
  const revoked = row.status === 'revoked';
  const effectiveDisabled = row.status !== 'active' || grantExpired || (heartbeatRequired && !heartbeatFresh);
  const authorization = { ...grant.authorization };
  if (revoked) authorization.revokedAt = new Date(row.revoked_at ?? row.updated_at).toISOString();
  return {
    ...grant,
    ...(signature ? { signature } : {}),
    authorization,
    status: effectiveDisabled ? 'disabled' : 'active',
    telemetry,
    runtime: {
      storedStatus: row.status,
      grantHash: row.grant_hash,
      revision: Number(row.revision),
      source: row.source,
      registeredAt: new Date(row.registered_at).toISOString(),
      updatedAt: new Date(row.updated_at).toISOString(),
      lastHeartbeatAt: row.last_heartbeat_at ? new Date(row.last_heartbeat_at).toISOString() : null,
      heartbeatExpiresAt: row.heartbeat_expires_at ? new Date(row.heartbeat_expires_at).toISOString() : null,
      heartbeatSeq: Number(row.heartbeat_seq),
      heartbeatRequired,
      heartbeatFresh,
      revokeReason: row.revoke_reason ?? null,
    },
  };
}

function sanitizeMeasuredTelemetry(input) {
  const out = {};
  if (input.inFlight != null) out.inFlight = nonNegativeNumber(input.inFlight, 'inFlight');
  if (input.trust != null) out.trust = bounded01(input.trust, 'trust');
  if (input.availability != null) out.availability = bounded01(input.availability, 'availability');
  if (input.p95LatencyMs != null) out.p95LatencyMs = nonNegativeNumber(input.p95LatencyMs, 'p95LatencyMs');
  if (input.costPerUnitUsd != null) out.costPerUnitUsd = nonNegativeNumber(input.costPerUnitUsd, 'costPerUnitUsd');
  if (input.carbonIntensity != null) out.carbonIntensity = nonNegativeNumber(input.carbonIntensity, 'carbonIntensity');
  return out;
}

function clampHeartbeatTtl(value) {
  const ttl = Number(value);
  if (!Number.isFinite(ttl) || ttl < HEARTBEAT_MIN_MS || ttl > HEARTBEAT_MAX_MS) throw new Error(`heartbeatTtlMs must be between ${HEARTBEAT_MIN_MS} and ${HEARTBEAT_MAX_MS}`);
  return ttl;
}
function nonNegativeNumber(value, name) { const n = Number(value); if (!Number.isFinite(n) || n < 0) throw new Error(`${name} must be a non-negative number`); return n; }
function bounded01(value, name) { const n = Number(value); if (!Number.isFinite(n) || n < 0 || n > 1) throw new Error(`${name} must be between 0 and 1`); return n; }
function taggedError(code, message) { const error = new Error(message); error.code = code; return error; }
