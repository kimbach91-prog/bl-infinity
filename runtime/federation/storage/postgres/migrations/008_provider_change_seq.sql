-- BL-CF v0.8: monotonic provider change cursor for incremental registry sync.
-- Apply under controlled migration authority before enabling delta synchronization.
BEGIN;

CREATE SEQUENCE IF NOT EXISTS federation_provider_change_seq AS bigint;

ALTER TABLE federation_providers
  ADD COLUMN IF NOT EXISTS change_seq bigint;

-- Existing rows receive a stable cursor exactly once. Future changes are handled by
-- the BEFORE trigger below. The sequence is intentionally allowed to have gaps.
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

ALTER TABLE federation_providers
  ALTER COLUMN change_seq SET NOT NULL;

CREATE INDEX IF NOT EXISTS federation_providers_change_seq_idx
  ON federation_providers(change_seq);

COMMIT;
