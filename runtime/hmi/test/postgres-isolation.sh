#!/usr/bin/env bash
set -euo pipefail

: "${PGHOST:=127.0.0.1}"
: "${PGPORT:=5432}"
: "${PGDATABASE:=postgres}"
: "${PGUSER:=postgres}"
: "${PGPASSWORD:=postgres}"
export PGHOST PGPORT PGDATABASE PGUSER PGPASSWORD

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

psql -v ON_ERROR_STOP=1 -f "$ROOT/storage/postgres-projection.sql"
psql -v ON_ERROR_STOP=1 <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'deus_hmi_runtime_test') THEN
    CREATE ROLE deus_hmi_runtime_test LOGIN PASSWORD 'synthetic-test-password' NOSUPERUSER NOBYPASSRLS;
  END IF;
END
$$;
GRANT SELECT, INSERT, UPDATE, DELETE ON deus_hmi_projection TO deus_hmi_runtime_test;
TRUNCATE TABLE deus_hmi_projection;
SQL

runtime_psql() {
  PGPASSWORD='synthetic-test-password' psql -v ON_ERROR_STOP=1 -U deus_hmi_runtime_test "$@"
}

runtime_psql <<'SQL'
BEGIN;
SET LOCAL deus.tenant_id = 'tenant-a';
INSERT INTO deus_hmi_projection
(tenant_id, projection_id, schema_version, data_class, policy_version, projection_value, created_at, expires_at)
VALUES ('tenant-a','same-id','v1','internal','p1','{"status":"A"}',now(),now()+interval '1 hour');
COMMIT;
SQL

runtime_psql <<'SQL'
BEGIN;
SET LOCAL deus.tenant_id = 'tenant-b';
INSERT INTO deus_hmi_projection
(tenant_id, projection_id, schema_version, data_class, policy_version, projection_value, created_at, expires_at)
VALUES ('tenant-b','same-id','v1','internal','p1','{"status":"B"}',now(),now()+interval '1 hour');
COMMIT;
SQL

a_count="$(runtime_psql -Atqc "SET deus.tenant_id='tenant-a'; SELECT count(*) FROM deus_hmi_projection;")"
b_count="$(runtime_psql -Atqc "SET deus.tenant_id='tenant-b'; SELECT count(*) FROM deus_hmi_projection;")"
missing_count="$(runtime_psql -Atqc "RESET deus.tenant_id; SELECT count(*) FROM deus_hmi_projection;")"
a_value="$(runtime_psql -Atqc "SET deus.tenant_id='tenant-a'; SELECT projection_value->>'status' FROM deus_hmi_projection WHERE projection_id='same-id';")"
b_value="$(runtime_psql -Atqc "SET deus.tenant_id='tenant-b'; SELECT projection_value->>'status' FROM deus_hmi_projection WHERE projection_id='same-id';")"

[[ "$a_count" == "1" && "$a_value" == "A" ]] || { echo "tenant-a isolation failed" >&2; exit 1; }
[[ "$b_count" == "1" && "$b_value" == "B" ]] || { echo "tenant-b isolation failed" >&2; exit 1; }
[[ "$missing_count" == "0" ]] || { echo "missing tenant context did not fail closed" >&2; exit 1; }

if runtime_psql -qc "SET deus.tenant_id='tenant-a'; INSERT INTO deus_hmi_projection (tenant_id,projection_id,schema_version,data_class,policy_version,projection_value,created_at,expires_at) VALUES ('tenant-b','illegal','v1','internal','p1','{}',now(),now()+interval '1 hour');" 2>/dev/null; then
  echo "cross-tenant insert unexpectedly succeeded" >&2
  exit 1
fi

echo "POSTGRES_RLS_TENANT_ISOLATION_PASS tenant_a=$a_count tenant_b=$b_count missing_context=$missing_count"
