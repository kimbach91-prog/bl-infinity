-- BL Compute Federation horizontal-state contract (PostgreSQL 16+ recommended)
-- This schema is deployment infrastructure, not evidence that a live Postgres instance exists.
-- Idempotency is tenant scoped. Applications may store the raw caller key here;
-- the database uniqueness boundary is (tenant_id, idempotency_key).

CREATE TABLE IF NOT EXISTS federation_jobs (
  id text PRIMARY KEY,
  idempotency_key text NOT NULL,
  tenant_id text NOT NULL DEFAULT 'default',
  capability text NOT NULL,
  task jsonb NOT NULL,
  state text NOT NULL CHECK (state IN ('pending','running','succeeded','deadletter')),
  priority integer NOT NULL DEFAULT 0,
  attempts integer NOT NULL DEFAULT 0,
  max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts >= 1),
  created_at timestamptz NOT NULL DEFAULT now(),
  available_at timestamptz NOT NULL DEFAULT now(),
  lease_worker text,
  lease_token uuid,
  lease_expires_at timestamptz,
  lease_heartbeat_at timestamptz,
  result jsonb,
  error jsonb
);
ALTER TABLE federation_jobs DROP CONSTRAINT IF EXISTS federation_jobs_idempotency_key_key;
CREATE UNIQUE INDEX IF NOT EXISTS federation_jobs_tenant_idempotency_idx ON federation_jobs (tenant_id, idempotency_key);
CREATE INDEX IF NOT EXISTS federation_jobs_claim_idx ON federation_jobs(state, available_at, priority DESC, created_at);
CREATE INDEX IF NOT EXISTS federation_jobs_lease_idx ON federation_jobs(state, lease_expires_at) WHERE state='running';

CREATE TABLE IF NOT EXISTS federation_result_cache (
  cache_key text PRIMARY KEY,
  task_id text NOT NULL,
  data_class text NOT NULL,
  tenant_id text NOT NULL,
  value jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  hits bigint NOT NULL DEFAULT 0 CHECK (hits >= 0)
);
CREATE INDEX IF NOT EXISTS federation_result_cache_expiry_idx ON federation_result_cache(expires_at);

CREATE TABLE IF NOT EXISTS federation_rate_limit_buckets (
  scope_key text PRIMARY KEY,
  tokens double precision NOT NULL CHECK (tokens >= 0),
  updated_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS federation_rate_limit_bucket_expiry_idx ON federation_rate_limit_buckets(expires_at);

-- Shared canonical search corpus. Local HybridSearchFabric instances are materialized
-- projections fed by this table's monotonic change cursor and deletion tombstones.
CREATE SEQUENCE IF NOT EXISTS federation_search_change_seq AS bigint;
CREATE TABLE IF NOT EXISTS federation_search_documents (
  id text PRIMARY KEY,
  document jsonb NOT NULL,
  content_hash text NOT NULL,
  tenant_id text NOT NULL DEFAULT 'default',
  data_class text NOT NULL DEFAULT 'public' CHECK (data_class IN ('public','internal','private')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','deleted')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  change_seq bigint
);
ALTER TABLE federation_search_documents ADD COLUMN IF NOT EXISTS change_seq bigint;
UPDATE federation_search_documents
SET change_seq = nextval('federation_search_change_seq')
WHERE change_seq IS NULL;
CREATE OR REPLACE FUNCTION bl_cf_bump_search_change_seq()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.change_seq := nextval('federation_search_change_seq');
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS bl_cf_search_change_seq_trigger ON federation_search_documents;
CREATE TRIGGER bl_cf_search_change_seq_trigger
BEFORE INSERT OR UPDATE ON federation_search_documents
FOR EACH ROW
EXECUTE FUNCTION bl_cf_bump_search_change_seq();
ALTER TABLE federation_search_documents ALTER COLUMN change_seq SET NOT NULL;
CREATE INDEX IF NOT EXISTS federation_search_documents_change_seq_idx ON federation_search_documents(change_seq);
CREATE INDEX IF NOT EXISTS federation_search_documents_status_idx ON federation_search_documents(status, change_seq);
CREATE INDEX IF NOT EXISTS federation_search_documents_tenant_idx ON federation_search_documents(tenant_id, status, change_seq);
CREATE INDEX IF NOT EXISTS federation_search_documents_data_class_idx ON federation_search_documents(data_class, status, change_seq);

CREATE TABLE IF NOT EXISTS federation_budget_reservations (
  id uuid PRIMARY KEY,
  task_id text,
  tenant_id text NOT NULL,
  provider_id text,
  reserved_usd numeric(20,8) NOT NULL CHECK (reserved_usd >= 0),
  actual_usd numeric(20,8),
  state text NOT NULL CHECK (state IN ('reserved','committed','released')),
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  reason text,
  CHECK (actual_usd IS NULL OR actual_usd >= 0)
);
CREATE INDEX IF NOT EXISTS federation_budget_state_idx ON federation_budget_reservations(state, tenant_id, provider_id);
CREATE INDEX IF NOT EXISTS federation_budget_provider_idx ON federation_budget_reservations(provider_id, state) WHERE provider_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS federation_contribution_ledger (
  seq bigserial PRIMARY KEY,
  id uuid NOT NULL UNIQUE,
  ts timestamptz NOT NULL DEFAULT now(),
  task_id text NOT NULL,
  provider_id text NOT NULL,
  consent_ref text,
  tenant_id text NOT NULL,
  measured_latency_ms double precision NOT NULL CHECK (measured_latency_ms >= 0),
  billed_cost_usd numeric(20,8) NOT NULL CHECK (billed_cost_usd >= 0),
  input_bytes bigint NOT NULL CHECK (input_bytes >= 0),
  output_bytes bigint NOT NULL CHECK (output_bytes >= 0),
  reported_usage jsonb,
  status text NOT NULL,
  prev_hash text,
  hash text NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS federation_contribution_provider_idx ON federation_contribution_ledger(provider_id, seq);
CREATE INDEX IF NOT EXISTS federation_contribution_tenant_idx ON federation_contribution_ledger(tenant_id, seq);

CREATE TABLE IF NOT EXISTS federation_audit (
  seq bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  type text NOT NULL,
  data jsonb NOT NULL,
  prev_hash text,
  hash text NOT NULL UNIQUE
);

CREATE SEQUENCE IF NOT EXISTS federation_provider_change_seq AS bigint;
CREATE TABLE IF NOT EXISTS federation_providers (
  id text PRIMARY KEY,
  grant_json jsonb NOT NULL,
  signature_json jsonb,
  grant_hash text NOT NULL,
  consent_ref text NOT NULL,
  key_id text,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled','revoked')),
  source text NOT NULL DEFAULT 'operator',
  revision bigint NOT NULL DEFAULT 1 CHECK (revision >= 1),
  telemetry_json jsonb NOT NULL DEFAULT '{}'::jsonb,
  registered_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  grant_expires_at timestamptz,
  revoked_at timestamptz,
  revoke_reason text,
  last_heartbeat_at timestamptz,
  heartbeat_expires_at timestamptz,
  heartbeat_seq bigint NOT NULL DEFAULT 0 CHECK (heartbeat_seq >= 0),
  change_seq bigint
);
ALTER TABLE federation_providers ADD COLUMN IF NOT EXISTS change_seq bigint;
UPDATE federation_providers
SET change_seq = nextval('federation_provider_change_seq')
WHERE change_seq IS NULL;
CREATE OR REPLACE FUNCTION bl_cf_bump_provider_change_seq()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.change_seq := nextval('federation_provider_change_seq');
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS bl_cf_provider_change_seq_trigger ON federation_providers;
CREATE TRIGGER bl_cf_provider_change_seq_trigger
BEFORE INSERT OR UPDATE ON federation_providers
FOR EACH ROW
EXECUTE FUNCTION bl_cf_bump_provider_change_seq();
ALTER TABLE federation_providers ALTER COLUMN change_seq SET NOT NULL;
CREATE INDEX IF NOT EXISTS federation_providers_change_seq_idx ON federation_providers(change_seq);
CREATE INDEX IF NOT EXISTS federation_providers_status_idx ON federation_providers(status, grant_expires_at);
CREATE INDEX IF NOT EXISTS federation_providers_heartbeat_idx ON federation_providers(heartbeat_expires_at) WHERE status='active';
CREATE INDEX IF NOT EXISTS federation_providers_consent_idx ON federation_providers(consent_ref);

CREATE TABLE IF NOT EXISTS federation_provider_heartbeat_nonces (
  provider_id text NOT NULL REFERENCES federation_providers(id) ON DELETE CASCADE,
  nonce text NOT NULL,
  seen_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  PRIMARY KEY(provider_id, nonce)
);
CREATE INDEX IF NOT EXISTS federation_provider_heartbeat_nonce_expiry_idx ON federation_provider_heartbeat_nonces(expires_at);

-- Horizontal invariants:
-- 1. queue claim: transaction + FOR UPDATE SKIP LOCKED;
-- 2. budget reserve/actual-cost settlement: transaction-scoped advisory lock;
-- 3. audit/ledger hash heads: transaction-scoped advisory lock;
-- 4. PostgreSQL sequences may have gaps after rollback; monotonicity is enough;
-- 5. provider-success/accounting-failure remains non-retryable until reconciled;
-- 6. provider heartbeat/status/telemetry never mutate grant authority;
-- 7. worker heartbeat replay is rejected by shared provider-scoped nonce uniqueness;
-- 8. every provider row mutation publishes a provider change_seq;
-- 9. rate-limit buckets are row-locked so coordinator count cannot multiply quota;
-- 10. search writes/deletes publish a search change_seq and deletion remains a durable tombstone.
