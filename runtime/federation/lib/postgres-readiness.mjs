const REQUIRED_RELATIONS = [
  'federation_jobs',
  'federation_result_cache',
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
  if (!pool?.query) throw new Error('Postgres pool is required for provider delta readiness check');
  const result = await pool.query(`
    SELECT
      to_regclass('federation_provider_change_seq') AS sequence_name,
      EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'federation_providers'
          AND column_name = 'change_seq'
          AND is_nullable = 'NO'
      ) AS has_change_seq,
      EXISTS (
        SELECT 1
        FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid
        WHERE c.relname='federation_providers'
          AND t.tgname='bl_cf_provider_change_seq_trigger'
          AND NOT t.tgisinternal
      ) AS has_trigger,
      to_regclass('federation_providers_change_seq_idx') AS index_name
  `);
  const row = result.rows[0] ?? {};
  const missing = [];
  if (!row.sequence_name) missing.push('federation_provider_change_seq');
  if (!row.has_change_seq) missing.push('federation_providers.change_seq NOT NULL');
  if (!row.has_trigger) missing.push('bl_cf_provider_change_seq_trigger');
  if (!row.index_name) missing.push('federation_providers_change_seq_idx');
  if (missing.length) {
    const error = new Error(`Postgres provider delta schema is missing: ${missing.join(', ')}`);
    error.code = 'POSTGRES_PROVIDER_DELTA_SCHEMA_MISSING';
    error.missingProviderDeltaObjects = missing;
    throw error;
  }
  return { ok: true, sequence: true, changeSeq: true, trigger: true, index: true };
}

export { REQUIRED_RELATIONS };
