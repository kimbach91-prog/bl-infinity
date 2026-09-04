const REQUIRED_RELATIONS = [
  'federation_jobs',
  'federation_result_cache',
  'federation_rate_limit_buckets',
  'federation_search_documents',
  'federation_budget_reservations',
  'federation_contribution_ledger',
  'federation_audit',
  'federation_providers',
  'federation_provider_heartbeat_nonces',
];

export async function assertPostgresSchema(pool) {
  if (!pool?.query) throw new Error('Postgres pool is required for readiness check');
  const result = await pool.query(`
    SELECT name, to_regclass(name) AS relation
    FROM unnest($1::text[]) AS name
  `, [REQUIRED_RELATIONS]);
  const missing = result.rows.filter((row) => row.relation == null).map((row) => row.name);
  if (missing.length) {
    const error = new Error(`Postgres federation schema is missing: ${missing.join(', ')}`);
    error.code = 'POSTGRES_SCHEMA_MISSING';
    error.missingRelations = missing;
    throw error;
  }
  return { ok: true, relations: REQUIRED_RELATIONS.length };
}

export async function assertProviderDeltaSchema(pool) {
  return assertDeltaSchema(pool, {
    label:'provider',
    sequence:'federation_provider_change_seq',
    table:'federation_providers',
    column:'change_seq',
    trigger:'bl_cf_provider_change_seq_trigger',
    index:'federation_providers_change_seq_idx',
    code:'POSTGRES_PROVIDER_DELTA_SCHEMA_MISSING',
  });
}

export async function assertSearchDeltaSchema(pool) {
  return assertDeltaSchema(pool, {
    label:'search',
    sequence:'federation_search_change_seq',
    table:'federation_search_documents',
    column:'change_seq',
    trigger:'bl_cf_search_change_seq_trigger',
    index:'federation_search_documents_change_seq_idx',
    code:'POSTGRES_SEARCH_DELTA_SCHEMA_MISSING',
  });
}

async function assertDeltaSchema(pool, config) {
  if (!pool?.query) throw new Error(`Postgres pool is required for ${config.label} delta readiness check`);
  const result = await pool.query(`
    SELECT
      to_regclass($1) AS sequence_name,
      EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = $2
          AND column_name = $3
          AND is_nullable = 'NO'
      ) AS has_change_seq,
      EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid
        WHERE c.relname=$2
          AND t.tgname=$4
          AND NOT t.tgisinternal
      ) AS has_trigger,
      to_regclass($5) AS index_name
  `, [config.sequence, config.table, config.column, config.trigger, config.index]);
  const row = result.rows[0] ?? {};
  const missing = [];
  if (!row.sequence_name) missing.push(config.sequence);
  if (!row.has_change_seq) missing.push(`${config.table}.${config.column} NOT NULL`);
  if (!row.has_trigger) missing.push(config.trigger);
  if (!row.index_name) missing.push(config.index);
  if (missing.length) {
    const error = new Error(`Postgres ${config.label} delta schema is missing: ${missing.join(', ')}`);
    error.code = config.code;
    error.missingDeltaObjects = missing;
    throw error;
  }
  return { ok:true, sequence:true, changeSeq:true, trigger:true, index:true };
}

export { REQUIRED_RELATIONS };
