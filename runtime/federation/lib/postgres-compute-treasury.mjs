import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { canonicalize, sha256 } from './canonical.mjs';

const LOCK_NAMESPACE = 424204;
const LOCK_TREASURY = 1;

export async function openPostgresComputeTreasury({
  connectionString = process.env.BL_POSTGRES_URL,
  pool = null,
  applySchema = false,
  poolOptions = {},
} = {}) {
  let ownsPool = false;
  if (!pool) {
    if (!connectionString) throw new Error('Postgres connectionString or pool is required');
    const { Pool } = await import('pg');
    pool = new Pool({
      connectionString,
      application_name: 'bl-compute-treasury',
      max: Number(poolOptions.max ?? 10),
      idleTimeoutMillis: Number(poolOptions.idleTimeoutMillis ?? 30_000),
      connectionTimeoutMillis: Number(poolOptions.connectionTimeoutMillis ?? 10_000),
      ...poolOptions,
    });
    ownsPool = true;
  }

  if (applySchema) {
    const schema = await readFile(new URL('../storage/postgres/treasury.sql', import.meta.url), 'utf8');
    await pool.query(schema);
  } else {
    await pool.query('SELECT 1');
  }

  return new PostgresComputeTreasury(pool, {
    close: async () => { if (ownsPool) await pool.end(); },
  });
}

export class PostgresComputeTreasury {
  constructor(pool, { close = async () => {} } = {}) {
    if (!pool?.query) throw new Error('Postgres pool is required');
    this.pool = pool;
    this.close = close;
  }

  async addBacking({
    backingId = randomUUID(),
    backingType,
    sourceRef,
    providerId = null,
    consentRef = null,
    faceValueUsd,
    haircutRate = 0,
    expiresAt = null,
    metadata = {},
  } = {}) {
    if (!['cash', 'compute'].includes(backingType)) throw new Error('backingType must be cash or compute');
    if (!String(sourceRef ?? '').trim()) throw new Error('sourceRef is required');
    const face = decimal(faceValueUsd, 'faceValueUsd');
    const haircut = rateDecimal(haircutRate, 'haircutRate');
    const expiry = expiresAt == null ? null : validDate(expiresAt, 'expiresAt');
    const result = await this.pool.query(`
      INSERT INTO federation_treasury_backing
        (backing_id,backing_type,source_ref,provider_id,consent_ref,face_value_usd,haircut_rate,expires_at,metadata)
      VALUES($1,$2,$3,$4,$5,$6::numeric,$7::numeric,$8,$9::jsonb)
      RETURNING *
    `, [backingId, backingType, sourceRef, providerId, consentRef, face, haircut, expiry, JSON.stringify(metadata ?? {})]);
    return mapBacking(result.rows[0]);
  }

  async revokeBacking(backingId, reason = 'revoked', { now = Date.now() } = {}) {
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client);
      const result = await client.query(`
        UPDATE federation_treasury_backing
        SET status='revoked', revoked_at=$1, revoke_reason=$2
        WHERE backing_id=$3 AND status='active'
        RETURNING *
      `, [new Date(now), String(reason), backingId]);
      if (result.rowCount !== 1) throw new Error('backing not active or unknown');
      const status = await reconcileTx(client, now);
      return { backing: mapBacking(result.rows[0]), treasury: status };
    });
  }

  async setReservedLiabilitiesUsd(value, { now = Date.now() } = {}) {
    const amount = decimal(value, 'reservedLiabilitiesUsd');
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client);
      await client.query(`
        UPDATE federation_treasury_settings
        SET reserved_liabilities_usd=$1::numeric, updated_at=$2
        WHERE singleton=true
      `, [amount, new Date(now)]);
      return reconcileTx(client, now);
    });
  }

  async configure({ dccMinBackingRatio = null, dccUnitValueUsd = null } = {}, { now = Date.now() } = {}) {
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client);
      const current = await settingsTx(client);
      const ratio = dccMinBackingRatio == null ? current.dccMinBackingRatio : decimalAtLeast(dccMinBackingRatio, 1, 'dccMinBackingRatio');
      const unit = dccUnitValueUsd == null ? current.dccUnitValueUsd : decimalPositive(dccUnitValueUsd, 'dccUnitValueUsd');
      await client.query(`
        UPDATE federation_treasury_settings
        SET dcc_min_backing_ratio=$1::numeric, dcc_unit_value_usd=$2::numeric, updated_at=$3
        WHERE singleton=true
      `, [fixed8(ratio), fixed8(unit), new Date(now)]);
      return reconcileTx(client, now);
    });
  }

  async setEmergencyFreeze(frozen, reason = null, { now = Date.now() } = {}) {
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client);
      const status = await reconcileTx(client, now);
      if (frozen !== true && status.dccOutstanding > 0 && status.backingRatio < status.dccMinBackingRatio) {
        const error = new Error('cannot unfreeze an undercollateralized DCC treasury');
        error.code = 'DCC_UNDERCOLLATERALIZED';
        throw error;
      }
      await client.query(`
        UPDATE federation_treasury_settings
        SET emergency_freeze=$1, freeze_reason=$2, updated_at=$3
        WHERE singleton=true
      `, [frozen === true, frozen === true ? String(reason ?? 'manual-freeze') : null, new Date(now)]);
      return treasuryStatusTx(client, now);
    });
  }

  async ensureAccount(accountId, metadata = {}) {
    const id = account(accountId);
    const result = await this.pool.query(`
      INSERT INTO federation_dcc_accounts(account_id,metadata)
      VALUES($1,$2::jsonb)
      ON CONFLICT(account_id) DO UPDATE SET updated_at=now()
      RETURNING *
    `, [id, JSON.stringify(metadata ?? {})]);
    return mapAccount(result.rows[0]);
  }

  async mint({
    accountId,
    amountDcc,
    authorizationRef,
    reference = null,
    idempotencyKey,
    now = Date.now(),
  } = {}) {
    const to = account(accountId);
    const amount = decimalPositive(amountDcc, 'amountDcc');
    requireText(authorizationRef, 'authorizationRef');
    requireText(idempotencyKey, 'idempotencyKey');
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client);
      const prior = await existingEventTx(client, idempotencyKey);
      if (prior) return assertIdempotent(prior, { kind: 'mint', fromAccount: null, toAccount: to, amountDcc: fixed8(amount) });
      await ensureAccountTx(client, to);
      const status = await reconcileTx(client, now);
      if (status.emergencyFreeze) throw frozenError(status.freezeReason);
      const nextOutstanding = status.dccOutstanding + amount;
      const nextLiabilityUsd = nextOutstanding * status.dccUnitValueUsd;
      const nextRatio = nextLiabilityUsd <= 0 ? Infinity : status.availableBackingUsd / nextLiabilityUsd;
      if (nextRatio + 1e-12 < status.dccMinBackingRatio) {
        const error = new Error('DCC mint would breach minimum backing ratio');
        error.code = 'DCC_BACKING_INSUFFICIENT';
        error.currentBackingRatio = status.backingRatio;
        error.postMintBackingRatio = nextRatio;
        error.maximumDccOutstanding = status.maximumDccOutstanding;
        throw error;
      }
      const event = await appendEventTx(client, {
        kind: 'mint', fromAccount: null, toAccount: to, amountDcc: amount,
        authorizationRef, reference, idempotencyKey, now,
      });
      return { event, treasury: await treasuryStatusTx(client, now), accountBalanceDcc: await accountBalanceTx(client, to) };
    });
  }

  async transfer({
    fromAccount,
    toAccount,
    amountDcc,
    authorizationRef,
    reference = null,
    idempotencyKey,
    now = Date.now(),
  } = {}) {
    const from = account(fromAccount);
    const to = account(toAccount);
    if (from === to) throw new Error('fromAccount and toAccount must differ');
    const amount = decimalPositive(amountDcc, 'amountDcc');
    requireText(authorizationRef, 'authorizationRef');
    requireText(idempotencyKey, 'idempotencyKey');
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client);
      const prior = await existingEventTx(client, idempotencyKey);
      if (prior) return assertIdempotent(prior, { kind: 'transfer', fromAccount: from, toAccount: to, amountDcc: fixed8(amount) });
      await ensureAccountTx(client, from, { mustExist: true });
      await ensureAccountTx(client, to);
      const status = await reconcileTx(client, now);
      if (status.emergencyFreeze) throw frozenError(status.freezeReason);
      const balance = await accountBalanceTx(client, from);
      if (balance + 1e-12 < amount) throw balanceError(balance, amount);
      const event = await appendEventTx(client, {
        kind: 'transfer', fromAccount: from, toAccount: to, amountDcc: amount,
        authorizationRef, reference, idempotencyKey, now,
      });
      return {
        event,
        treasury: await treasuryStatusTx(client, now),
        fromBalanceDcc: await accountBalanceTx(client, from),
        toBalanceDcc: await accountBalanceTx(client, to),
      };
    });
  }

  async redeem({
    accountId,
    amountDcc,
    authorizationRef,
    reference = null,
    idempotencyKey,
    now = Date.now(),
  } = {}) {
    const from = account(accountId);
    const amount = decimalPositive(amountDcc, 'amountDcc');
    requireText(authorizationRef, 'authorizationRef');
    requireText(idempotencyKey, 'idempotencyKey');
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client);
      const prior = await existingEventTx(client, idempotencyKey);
      if (prior) return assertIdempotent(prior, { kind: 'burn', fromAccount: from, toAccount: null, amountDcc: fixed8(amount) });
      await ensureAccountTx(client, from, { mustExist: true, allowFrozen: true });
      await reconcileTx(client, now);
      const balance = await accountBalanceTx(client, from);
      if (balance + 1e-12 < amount) throw balanceError(balance, amount);
      const event = await appendEventTx(client, {
        kind: 'burn', fromAccount: from, toAccount: null, amountDcc: amount,
        authorizationRef, reference, idempotencyKey, now,
      });
      return { event, treasury: await treasuryStatusTx(client, now), accountBalanceDcc: await accountBalanceTx(client, from) };
    });
  }

  async balance(accountId) {
    return accountBalanceTx(this.pool, account(accountId));
  }

  async status({ now = Date.now() } = {}) {
    return treasuryStatusTx(this.pool, now);
  }

  async reconcile({ now = Date.now() } = {}) {
    return withTransaction(this.pool, async (client) => {
      await advisoryLock(client);
      return reconcileTx(client, now);
    });
  }

  async listBacking({ includeInactive = true } = {}) {
    const result = includeInactive
      ? await this.pool.query('SELECT * FROM federation_treasury_backing ORDER BY created_at,backing_id')
      : await this.pool.query("SELECT * FROM federation_treasury_backing WHERE status='active' ORDER BY created_at,backing_id");
    return result.rows.map(mapBacking);
  }

  async listEvents() {
    const result = await this.pool.query('SELECT * FROM federation_dcc_ledger ORDER BY seq');
    return result.rows.map(mapEventRow);
  }

  async verifyLedger() {
    const events = await this.listEvents();
    let prevHash = null;
    let prevSeq = 0;
    for (let i = 0; i < events.length; i += 1) {
      const event = events[i];
      if (!Number.isSafeInteger(event.seq) || event.seq <= prevSeq) return { ok: false, index: i, reason: 'sequence' };
      if (event.event.prevHash !== prevHash) return { ok: false, index: i, reason: 'prevHash' };
      const expected = sha256(canonicalize(event.event));
      if (expected !== event.hash) return { ok: false, index: i, reason: 'hash' };
      prevSeq = event.seq;
      prevHash = event.hash;
    }
    return { ok: true, records: events.length, head: prevHash, lastSeq: prevSeq };
  }
}

async function reconcileTx(client, now = Date.now()) {
  await client.query(`
    UPDATE federation_treasury_backing
    SET status='expired'
    WHERE status='active' AND expires_at IS NOT NULL AND expires_at <= $1
  `, [new Date(now)]);
  let status = await treasuryStatusTx(client, now);
  if (status.dccOutstanding > 0 && status.backingRatio + 1e-12 < status.dccMinBackingRatio && !status.emergencyFreeze) {
    await client.query(`
      UPDATE federation_treasury_settings
      SET emergency_freeze=true, freeze_reason='automatic-undercollateralization-freeze', updated_at=$1
      WHERE singleton=true
    `, [new Date(now)]);
    status = await treasuryStatusTx(client, now);
  }
  return status;
}

async function treasuryStatusTx(client, now = Date.now()) {
  const result = await client.query(`
    WITH effective_backing AS (
      SELECT COALESCE(SUM(face_value_usd * (1 - haircut_rate)),0)::numeric AS value_usd
      FROM federation_treasury_backing
      WHERE status='active' AND (expires_at IS NULL OR expires_at > $1)
    ), supply AS (
      SELECT COALESCE(SUM(CASE WHEN kind='mint' THEN amount_dcc WHEN kind='burn' THEN -amount_dcc ELSE 0 END),0)::numeric AS outstanding_dcc
      FROM federation_dcc_ledger
    )
    SELECT
      s.reserved_liabilities_usd::text,
      s.dcc_min_backing_ratio::text,
      s.dcc_unit_value_usd::text,
      s.emergency_freeze,
      s.freeze_reason,
      b.value_usd::text AS effective_backing_usd,
      supply.outstanding_dcc::text
    FROM federation_treasury_settings s, effective_backing b, supply
    WHERE s.singleton=true
  `, [new Date(now)]);
  if (result.rowCount !== 1) throw new Error('treasury settings missing');
  const row = result.rows[0];
  const effectiveBackingUsd = Number(row.effective_backing_usd);
  const reservedLiabilitiesUsd = Number(row.reserved_liabilities_usd);
  const availableBackingUsd = Math.max(0, effectiveBackingUsd - reservedLiabilitiesUsd);
  const dccOutstanding = Number(row.outstanding_dcc);
  const dccMinBackingRatio = Number(row.dcc_min_backing_ratio);
  const dccUnitValueUsd = Number(row.dcc_unit_value_usd);
  const dccLiabilityUsd = dccOutstanding * dccUnitValueUsd;
  const backingRatio = dccLiabilityUsd <= 0 ? Infinity : availableBackingUsd / dccLiabilityUsd;
  const maximumDccOutstanding = availableBackingUsd / (dccUnitValueUsd * dccMinBackingRatio);
  return {
    effectiveBackingUsd,
    reservedLiabilitiesUsd,
    availableBackingUsd,
    dccOutstanding,
    dccUnitValueUsd,
    dccLiabilityUsd,
    dccMinBackingRatio,
    backingRatio,
    maximumDccOutstanding,
    emergencyFreeze: row.emergency_freeze === true,
    freezeReason: row.freeze_reason ?? null,
  };
}

async function settingsTx(client) {
  const result = await client.query(`
    SELECT dcc_min_backing_ratio::text, dcc_unit_value_usd::text
    FROM federation_treasury_settings WHERE singleton=true
  `);
  if (result.rowCount !== 1) throw new Error('treasury settings missing');
  return {
    dccMinBackingRatio: Number(result.rows[0].dcc_min_backing_ratio),
    dccUnitValueUsd: Number(result.rows[0].dcc_unit_value_usd),
  };
}

async function ensureAccountTx(client, accountId, { mustExist = false, allowFrozen = false } = {}) {
  if (!mustExist) {
    await client.query(`
      INSERT INTO federation_dcc_accounts(account_id)
      VALUES($1)
      ON CONFLICT(account_id) DO NOTHING
    `, [accountId]);
  }
  const result = await client.query('SELECT * FROM federation_dcc_accounts WHERE account_id=$1 FOR UPDATE', [accountId]);
  if (result.rowCount !== 1) throw new Error(`unknown DCC account: ${accountId}`);
  const status = result.rows[0].status;
  if (status === 'closed') throw new Error(`DCC account is closed: ${accountId}`);
  if (status === 'frozen' && !allowFrozen) throw new Error(`DCC account is frozen: ${accountId}`);
  return mapAccount(result.rows[0]);
}

async function accountBalanceTx(client, accountId) {
  const result = await client.query(`
    SELECT COALESCE(SUM(
      CASE
        WHEN to_account=$1 THEN amount_dcc
        WHEN from_account=$1 THEN -amount_dcc
        ELSE 0
      END
    ),0)::text AS balance
    FROM federation_dcc_ledger
    WHERE from_account=$1 OR to_account=$1
  `, [accountId]);
  return Number(result.rows[0].balance);
}

async function appendEventTx(client, {
  kind, fromAccount, toAccount, amountDcc, authorizationRef, reference, idempotencyKey, now,
}) {
  const last = await client.query('SELECT seq,hash FROM federation_dcc_ledger ORDER BY seq DESC LIMIT 1');
  const seqResult = await client.query(`SELECT nextval(pg_get_serial_sequence('federation_dcc_ledger','seq')) AS seq`);
  const seq = Number(seqResult.rows[0].seq);
  const event = {
    eventId: randomUUID(),
    seq,
    ts: new Date(now).toISOString(),
    kind,
    fromAccount: fromAccount ?? null,
    toAccount: toAccount ?? null,
    amountDcc: fixed8(amountDcc),
    authorizationRef: authorizationRef ?? null,
    reference: reference ?? null,
    idempotencyKey,
    prevHash: last.rows[0]?.hash ?? null,
  };
  const hash = sha256(canonicalize(event));
  await client.query(`
    INSERT INTO federation_dcc_ledger
      (seq,event_id,ts,kind,from_account,to_account,amount_dcc,authorization_ref,reference,idempotency_key,event_json,prev_hash,hash)
    VALUES($1,$2,$3,$4,$5,$6,$7::numeric,$8,$9,$10,$11::jsonb,$12,$13)
  `, [seq, event.eventId, event.ts, kind, fromAccount, toAccount, event.amountDcc, authorizationRef, reference, idempotencyKey, JSON.stringify(event), event.prevHash, hash]);
  return { ...event, amountDcc: Number(event.amountDcc), hash };
}

async function existingEventTx(client, idempotencyKey) {
  const result = await client.query('SELECT * FROM federation_dcc_ledger WHERE idempotency_key=$1', [idempotencyKey]);
  return result.rowCount ? mapEventRow(result.rows[0]) : null;
}

function assertIdempotent(existing, expected) {
  const event = existing.event;
  const same = event.kind === expected.kind &&
    event.fromAccount === expected.fromAccount &&
    event.toAccount === expected.toAccount &&
    event.amountDcc === expected.amountDcc;
  if (!same) {
    const error = new Error('idempotency key reused for a different DCC event');
    error.code = 'IDEMPOTENCY_CONFLICT';
    throw error;
  }
  return { event: { ...event, amountDcc: Number(event.amountDcc), hash: existing.hash }, idempotentReplay: true };
}

function mapBacking(row) {
  return {
    backingId: row.backing_id,
    backingType: row.backing_type,
    sourceRef: row.source_ref,
    providerId: row.provider_id ?? null,
    consentRef: row.consent_ref ?? null,
    faceValueUsd: Number(row.face_value_usd),
    haircutRate: Number(row.haircut_rate),
    effectiveFaceValueUsd: Number(row.face_value_usd) * (1 - Number(row.haircut_rate)),
    status: row.status,
    createdAt: asIso(row.created_at),
    expiresAt: row.expires_at ? asIso(row.expires_at) : null,
    revokedAt: row.revoked_at ? asIso(row.revoked_at) : null,
    revokeReason: row.revoke_reason ?? null,
    metadata: row.metadata ?? {},
  };
}

function mapAccount(row) {
  return {
    accountId: row.account_id,
    status: row.status,
    createdAt: asIso(row.created_at),
    updatedAt: asIso(row.updated_at),
    metadata: row.metadata ?? {},
  };
}

function mapEventRow(row) {
  return {
    seq: Number(row.seq),
    eventId: row.event_id,
    kind: row.kind,
    fromAccount: row.from_account ?? null,
    toAccount: row.to_account ?? null,
    amountDcc: Number(row.amount_dcc),
    authorizationRef: row.authorization_ref ?? null,
    reference: row.reference ?? null,
    idempotencyKey: row.idempotency_key,
    event: row.event_json,
    prevHash: row.prev_hash ?? null,
    hash: row.hash,
  };
}

async function withTransaction(pool, fn) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const value = await fn(client);
    await client.query('COMMIT');
    return value;
  } catch (error) {
    try { await client.query('ROLLBACK'); } catch {}
    throw error;
  } finally {
    client.release();
  }
}

async function advisoryLock(client) {
  await client.query('SELECT pg_advisory_xact_lock($1,$2)', [LOCK_NAMESPACE, LOCK_TREASURY]);
}

function decimal(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < 0) throw new Error(`${name} must be a non-negative number`);
  return number;
}

function decimalPositive(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) throw new Error(`${name} must be > 0`);
  return number;
}

function decimalAtLeast(value, minimum, name) {
  const number = Number(value);
  if (!Number.isFinite(number) || number < minimum) throw new Error(`${name} must be >= ${minimum}`);
  return number;
}

function rateDecimal(value, name) {
  const number = Number(value ?? 0);
  if (!Number.isFinite(number) || number < 0 || number > 1) throw new Error(`${name} must be between 0 and 1`);
  return number;
}

function fixed8(value) {
  return Number(value).toFixed(8);
}

function account(value) {
  const text = String(value ?? '').trim();
  if (!text || text.length > 256) throw new Error('invalid DCC account id');
  return text;
}

function requireText(value, name) {
  if (!String(value ?? '').trim()) throw new Error(`${name} is required`);
}

function validDate(value, name) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) throw new Error(`${name} must be a valid date`);
  return date;
}

function frozenError(reason) {
  const error = new Error(`DCC treasury is frozen${reason ? `: ${reason}` : ''}`);
  error.code = 'DCC_TREASURY_FROZEN';
  return error;
}

function balanceError(balance, amount) {
  const error = new Error('insufficient DCC account balance');
  error.code = 'DCC_BALANCE_INSUFFICIENT';
  error.balanceDcc = balance;
  error.requestedDcc = amount;
  return error;
}

function asIso(value) {
  return value instanceof Date ? value.toISOString() : new Date(value).toISOString();
}
