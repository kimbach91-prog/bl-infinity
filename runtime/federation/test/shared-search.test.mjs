import test, { after, before, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { Pool } from 'pg';
import { openPostgresFederationState } from '../lib/postgres-state.mjs';
import { HybridSearchFabric } from '../lib/search.mjs';
import { PostgresSearchDocumentStore, SearchFabricSynchronizer } from '../lib/search-store.mjs';
import { assertSearchDeltaSchema } from '../lib/postgres-readiness.mjs';

const connectionString = process.env.BL_TEST_POSTGRES_URL || null;
let pool = null;

if (connectionString) {
  before(async () => {
    pool = new Pool({ connectionString, max: 12, application_name: 'bl-cf-shared-search-test' });
    await openPostgresFederationState({ pool, applySchema: true });
  });
  beforeEach(async () => {
    await pool.query('TRUNCATE TABLE federation_search_documents RESTART IDENTITY');
  });
  after(async () => { await pool?.end(); });
}

const pgtest = (name, fn) => test(name, { skip: connectionString ? false : 'BL_TEST_POSTGRES_URL is not configured' }, fn);

function doc(id, overrides = {}) {
  return {
    id,
    title: `Document ${id}`,
    text: 'alpha beta gamma shared federation knowledge',
    source: 'test',
    tenantId: 'default',
    dataClass: 'public',
    trust: 0.7,
    ...overrides,
  };
}

pgtest('shared search converges across independent coordinator materializations', async () => {
  const store = new PostgresSearchDocumentStore(pool, { allowedDataClasses:['public','internal','private'] });
  const a = new HybridSearchFabric();
  const b = new HybridSearchFabric();
  const sa = new SearchFabricSynchronizer(a, store);
  const sb = new SearchFabricSynchronizer(b, store);
  await sa.bootstrap();
  await sb.bootstrap();

  await store.put(doc('shared-doc', { text:'needle federation search' }));
  await sa.sync();
  await sb.sync();
  assert.equal(a.search('needle')[0].id, 'shared-doc');
  assert.equal(b.search('needle')[0].id, 'shared-doc');
  assert.equal(sa.status().cursor, sb.status().cursor);
});

pgtest('delete tombstone propagates and survives later coordinator bootstrap', async () => {
  const store = new PostgresSearchDocumentStore(pool, { allowedDataClasses:['public'] });
  await store.put(doc('deleted-doc', { text:'vanishing needle' }));
  const first = new HybridSearchFabric();
  const sync = new SearchFabricSynchronizer(first, store);
  await sync.bootstrap();
  assert.equal(first.search('vanishing')[0].id, 'deleted-doc');

  const deleted = await store.delete('deleted-doc');
  assert.equal(deleted.changed, true);
  await sync.sync();
  assert.equal(first.search('vanishing').length, 0);

  const second = new HybridSearchFabric();
  const secondSync = new SearchFabricSynchronizer(second, store);
  const boot = await secondSync.bootstrap();
  assert.equal(second.search('vanishing').length, 0);
  assert.ok(boot.cursor >= deleted.entry.changeSeq);
  assert.equal((await store.get('deleted-doc')).status, 'deleted');
});

pgtest('identical re-index is write-free and semantic update emits exactly one delta', async () => {
  const store = new PostgresSearchDocumentStore(pool, { allowedDataClasses:['public'] });
  const original = doc('idem-doc', { relations:[{ target:'x', weight:1 }] });
  const first = await store.put(original);
  assert.equal(first.changed, true);
  const cursor = first.entry.changeSeq;

  const same = await store.put(original);
  assert.equal(same.changed, false);
  assert.equal(same.entry.changeSeq, cursor);
  assert.equal((await store.changesSince(cursor)).items.length, 0);

  const changed = await store.put({ ...original, text:'alpha beta changed content' });
  assert.equal(changed.changed, true);
  assert.ok(changed.entry.changeSeq > cursor);
  const delta = await store.changesSince(cursor);
  assert.equal(delta.items.length, 1);
  assert.equal(delta.items[0].id, 'idem-doc');
});

pgtest('shared search storage fails closed on disallowed data class', async () => {
  const publicOnly = new PostgresSearchDocumentStore(pool, { allowedDataClasses:['public'] });
  await assert.rejects(
    () => publicOnly.put(doc('private-rejected', { dataClass:'private', text:'secret needle' })),
    (error) => error.code === 'SEARCH_DATA_CLASS_REJECTED'
  );
  assert.equal(await publicOnly.get('private-rejected'), null);
});

test('hybrid search public filter cannot leak internal/private result metadata', () => {
  const fabric = new HybridSearchFabric();
  fabric.addDocument(doc('public', { text:'classified keyword', dataClass:'public' }));
  fabric.addDocument(doc('internal', { text:'classified keyword', dataClass:'internal', source:'internal-source' }));
  fabric.addDocument(doc('private', { text:'classified keyword', dataClass:'private', source:'private-source' }));

  const publicResults = fabric.search('classified', { allowedDataClasses:['public'] });
  assert.deepEqual(publicResults.map((result) => result.id), ['public']);
  const all = fabric.search('classified', { allowedDataClasses:['public','internal','private'] });
  assert.deepEqual(new Set(all.map((result) => result.id)), new Set(['public','internal','private']));
});

pgtest('search delta readiness gate detects missing trigger/index contract', async () => {
  assert.equal((await assertSearchDeltaSchema(pool)).ok, true);
  await pool.query('DROP TRIGGER bl_cf_search_change_seq_trigger ON federation_search_documents');
  try {
    await assert.rejects(() => assertSearchDeltaSchema(pool), (error) => error.code === 'POSTGRES_SEARCH_DELTA_SCHEMA_MISSING');
  } finally {
    await pool.query(`
      CREATE TRIGGER bl_cf_search_change_seq_trigger
      BEFORE INSERT OR UPDATE ON federation_search_documents
      FOR EACH ROW
      EXECUTE FUNCTION bl_cf_bump_search_change_seq()
    `);
  }
});
