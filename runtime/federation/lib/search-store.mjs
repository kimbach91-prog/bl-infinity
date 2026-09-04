import { sha256Json } from './canonical.mjs';
import { validateSearchDocument } from './search.mjs';

const DEFAULT_BATCH_SIZE = 500;
const MAX_BATCH_SIZE = 5000;
const MAX_WRITE_BATCH = 1000;

export class PostgresSearchDocumentStore {
  constructor(pool, { allowedDataClasses = ['public'] } = {}) {
    if (!pool?.query || !pool?.connect) throw new Error('Postgres pool is required for shared search store');
    this.pool = pool;
    this.allowedDataClasses = new Set(allowedDataClasses);
    for (const cls of this.allowedDataClasses) if (!['public','internal','private'].includes(cls)) throw new Error(`invalid search store data class: ${cls}`);
  }

  async put(input, { now = Date.now() } = {}) {
    const doc = this.#prepare(input);
    const stateHash = sha256Json(doc);
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const existing = await client.query('SELECT * FROM federation_search_documents WHERE id=$1 FOR UPDATE', [doc.id]);
      if (!existing.rowCount) {
        const inserted = await client.query(`
          INSERT INTO federation_search_documents(
            id,document,content_hash,tenant_id,data_class,status,created_at,updated_at,deleted_at
          ) VALUES($1,$2::jsonb,$3,$4,$5,'active',$6,$6,NULL)
          RETURNING *
        `, [doc.id, JSON.stringify(doc), stateHash, doc.tenantId, doc.dataClass, new Date(now)]);
        await client.query('COMMIT');
        return { changed: true, entry: mapSearchRow(inserted.rows[0]) };
      }
      const row = existing.rows[0];
      const same = row.status === 'active'
        && row.content_hash === stateHash
        && canonicalJson(row.document) === canonicalJson(doc)
        && row.tenant_id === doc.tenantId
        && row.data_class === doc.dataClass;
      if (same) {
        await client.query('COMMIT');
        return { changed: false, entry: mapSearchRow(row) };
      }
      const updated = await client.query(`
        UPDATE federation_search_documents
        SET document=$1::jsonb,content_hash=$2,tenant_id=$3,data_class=$4,
            status='active',updated_at=$5,deleted_at=NULL
        WHERE id=$6
        RETURNING *
      `, [JSON.stringify(doc), stateHash, doc.tenantId, doc.dataClass, new Date(now), doc.id]);
      await client.query('COMMIT');
      return { changed: true, entry: mapSearchRow(updated.rows[0]) };
    } catch (error) {
      try { await client.query('ROLLBACK'); } catch {}
      throw error;
    } finally {
      client.release();
    }
  }

  async putMany(inputs, { now = Date.now() } = {}) {
    if (!Array.isArray(inputs) || inputs.length < 1) throw new Error('search documents must be a non-empty array');
    if (inputs.length > MAX_WRITE_BATCH) throw new Error(`search write batch must contain <= ${MAX_WRITE_BATCH} documents`);
    const docs = inputs.map((input) => this.#prepare(input));
    const ids = new Set();
    for (const doc of docs) {
      if (ids.has(doc.id)) throw new Error(`duplicate document id in search write batch: ${doc.id}`);
      ids.add(doc.id);
    }
    const incoming = docs.map((doc) => ({
      id: doc.id,
      document: doc,
      content_hash: sha256Json(doc),
      tenant_id: doc.tenantId,
      data_class: doc.dataClass,
    }));
    const result = await this.pool.query(`
      WITH incoming AS (
        SELECT *
        FROM jsonb_to_recordset($1::jsonb)
          AS x(id text, document jsonb, content_hash text, tenant_id text, data_class text)
      )
      INSERT INTO federation_search_documents(
        id,document,content_hash,tenant_id,data_class,status,created_at,updated_at,deleted_at
      )
      SELECT id,document,content_hash,tenant_id,data_class,'active',$2,$2,NULL
      FROM incoming
      ON CONFLICT(id) DO UPDATE SET
        document=EXCLUDED.document,
        content_hash=EXCLUDED.content_hash,
        tenant_id=EXCLUDED.tenant_id,
        data_class=EXCLUDED.data_class,
        status='active',
        updated_at=$2,
        deleted_at=NULL
      WHERE federation_search_documents.status <> 'active'
         OR federation_search_documents.content_hash IS DISTINCT FROM EXCLUDED.content_hash
         OR federation_search_documents.document IS DISTINCT FROM EXCLUDED.document
         OR federation_search_documents.tenant_id IS DISTINCT FROM EXCLUDED.tenant_id
         OR federation_search_documents.data_class IS DISTINCT FROM EXCLUDED.data_class
      RETURNING *
    `, [JSON.stringify(incoming), new Date(now)]);
    return { total: docs.length, changed: result.rowCount, entries: result.rows.map(mapSearchRow) };
  }

  async delete(id, { now = Date.now() } = {}) {
    const safeId = normalizeId(id);
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const existing = await client.query('SELECT * FROM federation_search_documents WHERE id=$1 FOR UPDATE', [safeId]);
      if (!existing.rowCount) {
        await client.query('COMMIT');
        return { changed: false, entry: null };
      }
      const row = existing.rows[0];
      if (row.status === 'deleted') {
        await client.query('COMMIT');
        return { changed: false, entry: mapSearchRow(row) };
      }
      const updated = await client.query(`
        UPDATE federation_search_documents
        SET status='deleted',deleted_at=$1,updated_at=$1
        WHERE id=$2
        RETURNING *
      `, [new Date(now), safeId]);
      await client.query('COMMIT');
      return { changed: true, entry: mapSearchRow(updated.rows[0]) };
    } catch (error) {
      try { await client.query('ROLLBACK'); } catch {}
      throw error;
    } finally {
      client.release();
    }
  }

  async deleteMany(ids, { now = Date.now() } = {}) {
    if (!Array.isArray(ids) || ids.length < 1) throw new Error('search delete ids must be a non-empty array');
    if (ids.length > MAX_WRITE_BATCH) throw new Error(`search delete batch must contain <= ${MAX_WRITE_BATCH} ids`);
    const safeIds = [...new Set(ids.map(normalizeId))];
    const result = await this.pool.query(`
      UPDATE federation_search_documents
      SET status='deleted',deleted_at=$1,updated_at=$1
      WHERE id = ANY($2::text[]) AND status <> 'deleted'
      RETURNING *
    `, [new Date(now), safeIds]);
    return { total:safeIds.length, changed:result.rowCount, entries:result.rows.map(mapSearchRow) };
  }

  async get(id) {
    const result = await this.pool.query('SELECT * FROM federation_search_documents WHERE id=$1', [normalizeId(id)]);
    return result.rowCount ? mapSearchRow(result.rows[0]) : null;
  }

  async snapshot() {
    const result = await this.pool.query('SELECT * FROM federation_search_documents ORDER BY id');
    const cursor = result.rows.reduce((max, row) => Math.max(max, Number(row.change_seq) || 0), 0);
    const items = result.rows.filter((row) => row.status === 'active').map(mapSearchRow);
    return { items, cursor, rowsRead: result.rows.length, queries: 1 };
  }

  async changesSince(cursor = 0, { limit = DEFAULT_BATCH_SIZE } = {}) {
    const safeCursor = nonNegativeInteger(cursor, 'search cursor');
    const safeLimit = boundedBatch(limit);
    const result = await this.pool.query(`
      SELECT *
      FROM federation_search_documents
      WHERE change_seq > $1
      ORDER BY change_seq ASC
      LIMIT $2
    `, [safeCursor, safeLimit + 1]);
    const hasMore = result.rows.length > safeLimit;
    const rows = hasMore ? result.rows.slice(0, safeLimit) : result.rows;
    const nextCursor = rows.length ? Number(rows.at(-1).change_seq) : safeCursor;
    return { items: rows.map(mapSearchRow), cursor: nextCursor, hasMore, rowsRead: result.rows.length, queries: 1 };
  }

  async stats() {
    const result = await this.pool.query(`
      SELECT
        COUNT(*) FILTER (WHERE status='active')::bigint AS active,
        COUNT(*) FILTER (WHERE status='deleted')::bigint AS deleted,
        COUNT(*) FILTER (WHERE status='active' AND data_class='public')::bigint AS public,
        COUNT(*) FILTER (WHERE status='active' AND data_class='internal')::bigint AS internal,
        COUNT(*) FILTER (WHERE status='active' AND data_class='private')::bigint AS private,
        COALESCE(MAX(change_seq),0)::bigint AS cursor
      FROM federation_search_documents
    `);
    const row = result.rows[0];
    return {
      active: Number(row.active),
      deleted: Number(row.deleted),
      byDataClass: { public: Number(row.public), internal: Number(row.internal), private: Number(row.private) },
      cursor: Number(row.cursor),
    };
  }

  #prepare(input) {
    const doc = normalizeDocument(input);
    validateSearchDocument(doc);
    this.#assertDataClass(doc.dataClass);
    return doc;
  }

  #assertDataClass(dataClass) {
    if (!this.allowedDataClasses.has(dataClass)) {
      const error = new Error(`search document dataClass ${dataClass} is outside shared search storage policy`);
      error.code = 'SEARCH_DATA_CLASS_REJECTED';
      throw error;
    }
  }
}

export class SearchFabricSynchronizer {
  constructor(fabric, store, { batchSize = DEFAULT_BATCH_SIZE, maxBatchesPerSync = 20 } = {}) {
    if (!fabric?.addDocument || !fabric?.removeDocument) throw new Error('HybridSearchFabric is required');
    if (!store?.snapshot || !store?.changesSince) throw new Error('shared search store is required');
    this.fabric = fabric;
    this.store = store;
    this.batchSize = boundedBatch(batchSize);
    this.maxBatchesPerSync = positiveInteger(maxBatchesPerSync, 'maxBatchesPerSync');
    this.cursor = 0;
    this.bootstrapped = false;
    this.lastSync = null;
  }

  async bootstrap({ clear = true } = {}) {
    const snapshot = await this.store.snapshot();
    if (clear) for (const id of [...this.fabric.docs.keys()]) this.fabric.removeDocument(id);
    let applied = 0;
    for (const entry of snapshot.items) {
      this.fabric.addDocument(entry.document);
      applied += 1;
    }
    this.cursor = nonNegativeInteger(snapshot.cursor, 'search snapshot cursor');
    this.bootstrapped = true;
    const result = { mode:'bootstrap', cursor:this.cursor, applied, removed:0, batches:1, hasMore:false, rowsRead:snapshot.rowsRead, queries:snapshot.queries ?? 1 };
    this.lastSync = { ...result, at:new Date().toISOString() };
    return result;
  }

  async sync({ maxBatches = this.maxBatchesPerSync } = {}) {
    if (!this.bootstrapped) return this.bootstrap();
    const max = positiveInteger(maxBatches, 'maxBatches');
    let applied = 0, removed = 0, batches = 0, rowsRead = 0, queries = 0, hasMore = false;
    while (batches < max) {
      const delta = await this.store.changesSince(this.cursor, { limit:this.batchSize });
      batches += 1;
      rowsRead += Number(delta.rowsRead ?? delta.items.length);
      queries += Number(delta.queries ?? 1);
      for (const entry of delta.items) {
        if (entry.status === 'deleted') {
          if (this.fabric.removeDocument(entry.id)) removed += 1;
        } else {
          this.fabric.addDocument(entry.document);
          applied += 1;
        }
      }
      if (delta.cursor < this.cursor) throw new Error('search delta cursor moved backwards');
      this.cursor = delta.cursor;
      hasMore = delta.hasMore === true;
      if (!hasMore) break;
    }
    const result = { mode:'delta', cursor:this.cursor, applied, removed, batches, hasMore, rowsRead, queries };
    this.lastSync = { ...result, at:new Date().toISOString() };
    return result;
  }

  status() {
    return {
      bootstrapped:this.bootstrapped,
      cursor:this.cursor,
      batchSize:this.batchSize,
      maxBatchesPerSync:this.maxBatchesPerSync,
      lastSync:this.lastSync ? structuredClone(this.lastSync) : null,
      localDocuments:this.fabric.stats().documents,
    };
  }
}

function normalizeDocument(input) {
  const doc = structuredClone(input ?? {});
  doc.id = normalizeId(doc.id);
  doc.tenantId = String(doc.tenantId ?? 'default');
  doc.dataClass = String(doc.dataClass ?? 'public');
  if (doc.relations) {
    doc.relations = doc.relations
      .map((rel) => ({ ...rel, target:String(rel.target), weight:Number(rel.weight ?? 1) }))
      .sort((a, b) => a.target.localeCompare(b.target) || a.weight - b.weight);
  }
  return doc;
}
function normalizeId(id) {
  const value = String(id ?? '').trim();
  if (!value || value.length > 256) throw new Error('search document id must contain 1..256 characters');
  return value;
}
function mapSearchRow(row) {
  return {
    id:row.id,
    document:structuredClone(row.document),
    contentHash:row.content_hash,
    tenantId:row.tenant_id,
    dataClass:row.data_class,
    status:row.status,
    createdAt:new Date(row.created_at).toISOString(),
    updatedAt:new Date(row.updated_at).toISOString(),
    deletedAt:row.deleted_at ? new Date(row.deleted_at).toISOString() : null,
    changeSeq:Number(row.change_seq),
  };
}
function canonicalJson(value) {
  return JSON.stringify(sortObject(value));
}
function sortObject(value) {
  if (Array.isArray(value)) return value.map(sortObject);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.keys(value).sort().map((key) => [key, sortObject(value[key])]));
}
function boundedBatch(value) {
  const n = positiveInteger(value, 'batch size');
  if (n > MAX_BATCH_SIZE) throw new Error(`batch size must be <= ${MAX_BATCH_SIZE}`);
  return n;
}
function positiveInteger(value, name) {
  const n = Number(value);
  if (!Number.isSafeInteger(n) || n < 1) throw new Error(`${name} must be a positive integer`);
  return n;
}
function nonNegativeInteger(value, name) {
  const n = Number(value);
  if (!Number.isSafeInteger(n) || n < 0) throw new Error(`${name} must be a non-negative integer`);
  return n;
}
