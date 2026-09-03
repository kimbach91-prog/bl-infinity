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

-- Shared token buckets make request guardrails independent of coordinator count/restart.
-- scope_key is an application-generated SHA-256 fingerprint, not a raw bearer token/IP.
CREATE TABLE IF NOT EXISTS federation_rate_limit_buckets (
  scope_key text PRIMARY KEY,
  tokens double precision NOT NULL CHECK (tokens >= 0),
  updated_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS federation_rate_limit_bucket_expiry_idx ON federation_rate_limit_buckets(expires_at);

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

-- v0.8 uses a monotonic provider change cursor for bounded incremental registry sync.
-- PostgreSQL sequences are allowed to have gaps; only monotonicity is required.
CREATE SEQUENCE IF NOT EXISTS federation_provider_change_seq AS bigint;

-- Signed provider authority is stored separately from mutable runtime state.
-- grant_json is the exact canonical grant payload (signature/telemetry/status excluded).
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

-- Existing rows receive a cursor once. The trigger below covers all later INSERT/UPDATE paths.
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

-- Cross-coordinator replay defense for worker self-heartbeats. The HMAC secret never
-- enters this table; only a provider-scoped nonce and bounded expiry are persisted.
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
-- 2. budget reserve/actual-cost settlement: transaction-scoped advisory lock before
--    checking aggregate spend/reservations and writing;
-- 3. audit/ledger hash heads: transaction-scoped advisory lock so two coordinators
--    cannot append competing records with the same predecessor;
-- 4. PostgreSQL sequences may have gaps after transaction rollback. Chain validity
--    therefore requires strictly increasing seq + valid prev_hash/hash, not gaplessness;
-- 5. provider-success/accounting-failure is non-retryable until reconciled because
--    the external side effect may already have happened;
-- 6. provider heartbeat/status/telemetry never mutate grant_json. Authority changes
--    require an explicit new verified grant revision or an explicit revocation;
-- 7. direct worker heartbeat replay is rejected by the provider-scoped nonce primary key
--    shared by every coordinator using this database;
-- 8. every provider row mutation receives a new change_seq so coordinators can consume
--    bounded deltas; time-based expiry remains locally fail-closed even without a row change;
-- 9. rate-limit buckets are row-locked transactionally so parallel coordinators consume
--    one shared quota instead of multiplying burst capacity by coordinator count.
