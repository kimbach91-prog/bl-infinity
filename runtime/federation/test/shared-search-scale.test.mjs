import test, { after, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { performance } from 'node:perf_hooks';
import { Pool } from 'pg';
import { openPostgresFederationState } from '../lib/postgres-state.mjs';
import { PostgresSearchDocumentStore } from '../lib/search-store.mjs';

const connectionString = process.env.BL_TEST_POSTGRES_URL || null;
let pool = null;

if (connectionString) {
  before(async () => {
    pool = new Pool({ connectionString, max: 8, application_name: 'bl-cf-shared-search-scale-test' });
    await openPostgresFederationState({ pool, applySchema: true });
  });
  beforeEach(async () => {
    await pool.query('TRUNCATE TABLE federation_search_documents RESTART IDENTITY');
  });
  after(async () => { await pool?.end(); });
}

const pgtest = (name, fn) => test(name, { skip: connectionString ? false : 'BL_TEST_POSTGRES_URL is not configured' }, fn);

pgtest('1000-document batch upsert is idempotent and only changed docs publish deltas', async () => {
  const store = new PostgresSearchDocumentStore(pool, { allowedDataClasses:['public'] });
  const docs = Array.from({ length: 1000 }, (_, i) => ({
    id:`batch-${String(i).padStart(4,'0')}`,
    title:`Batch ${i}`,
    text:`shared batch document ${i}`,
    dataClass:'public',
    tenantId:'default',
    trust:0.5,
  }));

  const first = await store.putMany(docs);
  assert.equal(first.total, 1000);
  assert.equal(first.changed, 1000);
  const cursor = (await store.stats()).cursor;

  const retry = await store.putMany(docs);
  assert.equal(retry.total, 1000);
  assert.equal(retry.changed, 0);
  assert.equal((await store.stats()).cursor, cursor);

  const changedDocs = docs.map((doc, i) => i < 10 ? { ...doc, text:`shared batch UPDATED ${i}` } : doc);
  const update = await store.putMany(changedDocs);
  assert.equal(update.changed, 10);
  const delta = await store.changesSince(cursor, { limit:100 });
  assert.equal(delta.items.length, 10);
  assert.equal(delta.hasMore, false);
});

pgtest('10k shared-search corpus reads one snapshot then only changed rows', async () => {
  const documentCount = 10_000;
  const changedCount = 10;
  await pool.query(`
    WITH source AS (
      SELECT gs, 'search-bench-' || lpad(gs::text, 5, '0') AS id
      FROM generate_series(1, $1::int) AS gs
    )
    INSERT INTO federation_search_documents(
      id,document,content_hash,tenant_id,data_class,status,created_at,updated_at,deleted_at
    )
    SELECT
      id,
      jsonb_build_object(
        'id',id,
        'title','Search Benchmark ' || gs,
        'text','shared search benchmark corpus term ' || gs,
        'source','benchmark',
        'tenantId','default',
        'dataClass','public',
        'trust',0.5
      ),
      md5(id),
      'default',
      'public',
      'active',
      now(),now(),NULL
    FROM source
  `, [documentCount]);

  const store = new PostgresSearchDocumentStore(pool, { allowedDataClasses:['public'] });
  let queryCount = 0;
  const countedStore = new PostgresSearchDocumentStore({
    query: async (...args) => { queryCount += 1; return pool.query(...args); },
    connect: (...args) => pool.connect(...args),
  }, { allowedDataClasses:['public'] });

  const snapshotStarted = performance.now();
  const snapshot = await countedStore.snapshot();
  const snapshotMs = performance.now() - snapshotStarted;
  assert.equal(snapshot.items.length, documentCount);
  assert.equal(snapshot.rowsRead, documentCount);
  assert.equal(snapshot.queries, 1);
  assert.equal(queryCount, 1);

  await pool.query(`
    UPDATE federation_search_documents
    SET document = jsonb_set(document, '{text}', to_jsonb('updated shared search benchmark'::text), true),
        content_hash = md5(id || '-updated'),
        updated_at = clock_timestamp()
    WHERE id IN (
      SELECT 'search-bench-' || lpad(gs::text, 5, '0')
      FROM generate_series(1, $1::int) AS gs
    )
  `, [changedCount]);

  queryCount = 0;
  const deltaStarted = performance.now();
  const delta = await countedStore.changesSince(snapshot.cursor, { limit:500 });
  const deltaMs = performance.now() - deltaStarted;
  assert.equal(delta.items.length, changedCount);
  assert.equal(delta.rowsRead, changedCount);
  assert.equal(delta.queries, 1);
  assert.equal(queryCount, 1);
  assert.equal(delta.hasMore, false);
  const rowReduction = snapshot.rowsRead / delta.rowsRead;
  assert.ok(rowReduction >= 1000, `expected >=1000x row reduction, got ${rowReduction}`);

  console.log(`# shared-search-scale-benchmark ${JSON.stringify({ documentCount, changedCount, snapshotRows:snapshot.rowsRead, deltaRows:delta.rowsRead, rowReduction, snapshotMs:Number(snapshotMs.toFixed(2)), deltaMs:Number(deltaMs.toFixed(2)) })}`);

  // Keep a live store reference used so lint/syntax-level refactors do not accidentally remove constructor coverage.
  assert.equal((await store.stats()).active, documentCount);
});
