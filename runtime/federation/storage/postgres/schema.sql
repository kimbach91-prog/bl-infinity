-- BL Compute Federation horizontal-state contract (PostgreSQL 16+ recommended)
-- This schema is deployment infrastructure, not evidence that a live Postgres instance exists.

CREATE TABLE IF NOT EXISTS federation_jobs (
  id text PRIMARY KEY,
  idempotency_key text NOT NULL UNIQUE,
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
CREATE INDEX IF NOT EXISTS federation_jobs_claim_idx ON federation_jobs (state, available_at, priority DESC, created_at);
CREATE INDEX IF NOT EXISTS federation_jobs_lease_idx ON federation_jobs (state, lease_expires_at) WHERE state='running';

CREATE TABLE IF NOT EXISTS federation_result_cache (
  cache_key text PRIMARY KEY,
  task_id text NOT NULL,
  data_class text NOT NULL,
  tenant_id text NOT NULL,
  value jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  hits bigint NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS federation_result_cache_expiry_idx ON federation_result_cache (expires_at);

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
  reason text
);
CREATE INDEX IF NOT EXISTS federation_budget_state_idx ON federation_budget_reservations (state, tenant_id, provider_id);

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

-- Example atomic claim pattern. Application must substitute worker/capabilities/lease interval.
-- FOR UPDATE SKIP LOCKED lets multiple coordinators claim different rows without a global queue lock.
