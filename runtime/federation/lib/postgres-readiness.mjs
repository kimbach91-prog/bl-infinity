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

export { REQUIRED_RELATIONS };
