const DEFAULT_BATCH_SIZE = 500;
const MAX_BATCH_SIZE = 5000;

export class PostgresProviderDeltaView {
  constructor(store, { batchSize = DEFAULT_BATCH_SIZE } = {}) {
    if (!store?.pool?.query) throw new Error('PostgresProviderStore with pool is required');
    this.store = store;
    this.pool = store.pool;
    this.batchSize = boundedBatch(batchSize);
  }

  async snapshot({ now = Date.now() } = {}) {
    const result = await this.pool.query('SELECT * FROM federation_providers ORDER BY id');
    const items = hydrateRows(result.rows, now);
    const cursor = result.rows.reduce((max, row) => Math.max(max, Number(row.change_seq) || 0), 0);
    return { items, cursor, rowsRead: result.rows.length, queries: 1 };
  }

  async changesSince(cursor = 0, { limit = this.batchSize, now = Date.now() } = {}) {
    const safeCursor = nonNegativeInteger(cursor, 'cursor');
    const safeLimit = boundedBatch(limit);
    const result = await this.pool.query(`
      SELECT *
      FROM federation_providers
      WHERE change_seq > $1
      ORDER BY change_seq ASC
      LIMIT $2
    `, [safeCursor, safeLimit + 1]);
    const hasMore = result.rows.length > safeLimit;
    const rows = hasMore ? result.rows.slice(0, safeLimit) : result.rows;
    const items = hydrateRows(rows, now);
    const nextCursor = rows.length ? Number(rows.at(-1).change_seq) : safeCursor;
    return { items, cursor: nextCursor, hasMore, rowsRead: result.rows.length, queries: 1 };
  }
}

export class ProviderRegistrySynchronizer {
  constructor(registry, deltaView, { batchSize = DEFAULT_BATCH_SIZE, maxBatchesPerSync = 20 } = {}) {
    if (!registry?.register || !registry?.get || !registry?.disable) throw new Error('provider registry is required');
    if (!deltaView?.snapshot || !deltaView?.changesSince) throw new Error('provider delta view is required');
    this.registry = registry;
    this.deltaView = deltaView;
    this.batchSize = boundedBatch(batchSize);
    this.maxBatchesPerSync = positiveInteger(maxBatchesPerSync, 'maxBatchesPerSync');
    this.cursor = 0;
    this.bootstrapped = false;
    this.changeSeqById = new Map();
    this.expiryHeap = [];
    this.lastSync = null;
  }

  async bootstrap({ now = Date.now() } = {}) {
    const snapshot = await this.deltaView.snapshot({ now });
    this.changeSeqById.clear();
    this.expiryHeap.length = 0;
    let applied = 0;
    for (const item of snapshot.items) applied += this.#apply(item, now);
    this.cursor = nonNegativeInteger(snapshot.cursor ?? 0, 'snapshot cursor');
    this.bootstrapped = true;
    const expired = this.#expire(now);
    const result = { mode: 'bootstrap', cursor: this.cursor, applied, expired, batches: 1, hasMore: false, rowsRead: snapshot.rowsRead ?? snapshot.items.length, queries: snapshot.queries ?? 1 };
    this.lastSync = { ...result, at: new Date(now).toISOString() };
    return result;
  }

  async sync({ now = Date.now(), maxBatches = this.maxBatchesPerSync } = {}) {
    if (!this.bootstrapped) return this.bootstrap({ now });
    const batchLimit = positiveInteger(maxBatches, 'maxBatches');
    let applied = 0;
    let batches = 0;
    let rowsRead = 0;
    let queries = 0;
    let hasMore = false;
    while (batches < batchLimit) {
      const delta = await this.deltaView.changesSince(this.cursor, { limit: this.batchSize, now });
      batches += 1;
      rowsRead += Number(delta.rowsRead ?? delta.items.length);
      queries += Number(delta.queries ?? 1);
      for (const item of delta.items) applied += this.#apply(item, now);
      if (delta.cursor < this.cursor) throw new Error('provider delta cursor moved backwards');
      this.cursor = delta.cursor;
      hasMore = delta.hasMore === true;
      if (!hasMore) break;
    }
    const expired = this.#expire(now);
    const result = { mode: 'delta', cursor: this.cursor, applied, expired, batches, hasMore, rowsRead, queries };
    this.lastSync = { ...result, at: new Date(now).toISOString() };
    return result;
  }

  status() {
    return {
      bootstrapped: this.bootstrapped,
      cursor: this.cursor,
      trackedProviders: this.changeSeqById.size,
      scheduledExpiries: this.expiryHeap.length,
      batchSize: this.batchSize,
      maxBatchesPerSync: this.maxBatchesPerSync,
      lastSync: this.lastSync ? structuredClone(this.lastSync) : null,
    };
  }

  #apply(item, now) {
    const provider = item?.provider;
    if (!provider?.id) return 0;
    const changeSeq = nonNegativeInteger(item.changeSeq, 'provider changeSeq');
    const known = this.changeSeqById.get(provider.id) ?? -1;
    if (changeSeq < known) return 0;
    this.changeSeqById.set(provider.id, changeSeq);

    if (provider.status === 'active') this.registry.register(provider);
    else if (this.registry.get(provider.id)) this.registry.disable(provider.id);

    this.#scheduleExpiry(provider, changeSeq, now);
    return 1;
  }

  #scheduleExpiry(provider, changeSeq, now) {
    const grantExpiry = parseTime(provider.authorization?.expiresAt);
    if (grantExpiry != null && grantExpiry > now) heapPush(this.expiryHeap, { at: grantExpiry, providerId: provider.id, changeSeq, kind: 'grant' });
    if (provider.runtime?.heartbeatRequired === true) {
      const heartbeatExpiry = parseTime(provider.runtime?.heartbeatExpiresAt);
      if (heartbeatExpiry != null && heartbeatExpiry > now) heapPush(this.expiryHeap, { at: heartbeatExpiry, providerId: provider.id, changeSeq, kind: 'heartbeat' });
    }
  }

  #expire(now) {
    let expired = 0;
    while (this.expiryHeap.length && this.expiryHeap[0].at <= now) {
      const event = heapPop(this.expiryHeap);
      if (this.changeSeqById.get(event.providerId) !== event.changeSeq) continue;
      const provider = this.registry.get(event.providerId);
      if (!provider) continue;
      const actualExpiry = event.kind === 'grant'
        ? parseTime(provider.authorization?.expiresAt)
        : parseTime(provider.runtime?.heartbeatExpiresAt);
      if (actualExpiry == null || actualExpiry > now) continue;
      if (provider.status !== 'disabled') {
        this.registry.disable(event.providerId);
        expired += 1;
      }
    }
    return expired;
  }
}

export function providerFromDeltaRow(row, now = Date.now()) {
  if (!row) return null;
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

function hydrateRows(rows, now) {
  return rows.map((row) => ({ provider: providerFromDeltaRow(row, now), changeSeq: Number(row.change_seq) }));
}

function parseTime(value) {
  if (!value) return null;
  const n = Date.parse(value);
  return Number.isFinite(n) ? n : null;
}

function boundedBatch(value) {
  const n = positiveInteger(value, 'batch size');
  if (n > MAX_BATCH_SIZE) throw new Error(`batch size must be <= ${MAX_BATCH_SIZE}`);
  return n;
}
function positiveInteger(value, name) { const n = Number(value); if (!Number.isSafeInteger(n) || n < 1) throw new Error(`${name} must be a positive integer`); return n; }
function nonNegativeInteger(value, name) { const n = Number(value); if (!Number.isSafeInteger(n) || n < 0) throw new Error(`${name} must be a non-negative integer`); return n; }

function heapPush(heap, value) {
  heap.push(value);
  let i = heap.length - 1;
  while (i > 0) {
    const parent = Math.floor((i - 1) / 2);
    if (heap[parent].at <= value.at) break;
    heap[i] = heap[parent];
    i = parent;
  }
  heap[i] = value;
}
function heapPop(heap) {
  const root = heap[0];
  const tail = heap.pop();
  if (!heap.length) return root;
  let i = 0;
  while (true) {
    let child = i * 2 + 1;
    if (child >= heap.length) break;
    if (child + 1 < heap.length && heap[child + 1].at < heap[child].at) child += 1;
    if (heap[child].at >= tail.at) break;
    heap[i] = heap[child];
    i = child;
  }
  heap[i] = tail;
  return root;
}
