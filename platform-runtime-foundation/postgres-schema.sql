-- DEUS V6 Platform Runtime Foundation Postgres adapter.
-- Additive-only schema. Does not alter federation authority/runtime tables.

CREATE TABLE IF NOT EXISTS deus_platform_tenants (
  tenant_id text PRIMARY KEY,
  org_id text NOT NULL,
  name text NOT NULL,
  state text NOT NULL DEFAULT 'ACTIVE' CHECK (state IN ('ACTIVE','SUSPENDED','CLOSED')),
  region text NOT NULL DEFAULT 'GLOBAL',
  data_residency text,
  plan jsonb NOT NULL DEFAULT '{"plan_id":"FREE","currency":"USD","quotas":{},"prices":{},"monthly_credit":0}'::jsonb,
  labels jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS deus_platform_principals (
  principal_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES deus_platform_tenants(tenant_id) ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('OWNER_USER','ORG_USER','SERVICE_ACCOUNT','WORKLOAD','APP')),
  roles text[] NOT NULL DEFAULT ARRAY[]::text[],
  scopes text[] NOT NULL DEFAULT ARRAY[]::text[],
  credential_ref text,
  region text,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS deus_platform_principals_tenant_idx ON deus_platform_principals(tenant_id, active);

CREATE TABLE IF NOT EXISTS deus_platform_usage_events (
  event_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES deus_platform_tenants(tenant_id) ON DELETE CASCADE,
  metric text NOT NULL CHECK (metric IN ('api_requests','input_tokens','output_tokens','compute_ms','storage_bytes','egress_bytes','jobs')),
  quantity numeric(30,8) NOT NULL CHECK (quantity >= 0),
  source_ref text NOT NULL,
  workload_family text NOT NULL DEFAULT 'GENERAL',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS deus_platform_usage_tenant_metric_idx
  ON deus_platform_usage_events(tenant_id, metric, occurred_at);

CREATE TABLE IF NOT EXISTS deus_platform_billing_credits (
  credit_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES deus_platform_tenants(tenant_id) ON DELETE CASCADE,
  amount numeric(20,8) NOT NULL CHECK (amount >= 0),
  reason text NOT NULL,
  receipt_ref text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS deus_platform_billing_credit_tenant_idx
  ON deus_platform_billing_credits(tenant_id, created_at);

CREATE SEQUENCE IF NOT EXISTS deus_platform_event_sequence AS bigint;

CREATE TABLE IF NOT EXISTS deus_platform_webhook_subscriptions (
  subscription_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES deus_platform_tenants(tenant_id) ON DELETE CASCADE,
  event_types text[] NOT NULL DEFAULT ARRAY['*']::text[],
  endpoint_ref text NOT NULL,
  signing_secret_ref text,
  active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS deus_platform_webhook_sub_tenant_idx
  ON deus_platform_webhook_subscriptions(tenant_id, active);

CREATE TABLE IF NOT EXISTS deus_platform_outbox (
  event_id text PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES deus_platform_tenants(tenant_id) ON DELETE CASCADE,
  type text NOT NULL,
  payload jsonb NOT NULL,
  source_ref text NOT NULL,
  sequence bigint NOT NULL DEFAULT nextval('deus_platform_event_sequence'),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS deus_platform_outbox_sequence_idx ON deus_platform_outbox(sequence);
CREATE INDEX IF NOT EXISTS deus_platform_outbox_tenant_type_idx ON deus_platform_outbox(tenant_id, type, sequence);

CREATE TABLE IF NOT EXISTS deus_platform_webhook_deliveries (
  event_id text NOT NULL REFERENCES deus_platform_outbox(event_id) ON DELETE CASCADE,
  subscription_id text NOT NULL REFERENCES deus_platform_webhook_subscriptions(subscription_id) ON DELETE CASCADE,
  state text NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING','DELIVERED','DEAD_LETTER')),
  attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  last_error text,
  delivered_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(event_id, subscription_id)
);
CREATE INDEX IF NOT EXISTS deus_platform_webhook_delivery_state_idx
  ON deus_platform_webhook_deliveries(state, updated_at);

CREATE TABLE IF NOT EXISTS deus_platform_slo_samples (
  id bigserial PRIMARY KEY,
  tenant_id text NOT NULL REFERENCES deus_platform_tenants(tenant_id) ON DELETE CASCADE,
  service text NOT NULL,
  success boolean NOT NULL,
  latency_ms double precision NOT NULL CHECK (latency_ms >= 0),
  trace_ref text,
  observed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS deus_platform_slo_tenant_service_idx
  ON deus_platform_slo_samples(tenant_id, service, observed_at);
