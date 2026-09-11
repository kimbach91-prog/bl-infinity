BEGIN;

CREATE TABLE IF NOT EXISTS deus_hmi_projection (
  tenant_id text NOT NULL,
  projection_id text NOT NULL,
  schema_version text NOT NULL,
  data_class text NOT NULL CHECK (data_class IN ('public','internal','confidential','restricted','sovereign')),
  policy_version text NOT NULL,
  source_receipt_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
  projection_value jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  PRIMARY KEY (tenant_id, projection_id),
  CHECK (expires_at > created_at)
);

ALTER TABLE deus_hmi_projection ENABLE ROW LEVEL SECURITY;
ALTER TABLE deus_hmi_projection FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS deus_hmi_projection_tenant_policy ON deus_hmi_projection;
CREATE POLICY deus_hmi_projection_tenant_policy
  ON deus_hmi_projection
  FOR ALL
  USING (tenant_id = current_setting('deus.tenant_id', true))
  WITH CHECK (tenant_id = current_setting('deus.tenant_id', true));

REVOKE ALL ON deus_hmi_projection FROM PUBLIC;

CREATE INDEX IF NOT EXISTS deus_hmi_projection_expiry_idx
  ON deus_hmi_projection (expires_at);

COMMIT;

-- Deployment rule:
-- Run migrations as a schema-owner identity, then grant only the required
-- SELECT/INSERT/UPDATE/DELETE rights to a NON-SUPERUSER, NON-BYPASSRLS runtime
-- role. The trusted HMI server must SET LOCAL deus.tenant_id inside each
-- transaction before accessing projection rows. Missing tenant context fails
-- closed because current_setting(..., true) is NULL.
