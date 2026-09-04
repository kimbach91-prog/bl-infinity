-- BL Compute Federation v0.10 shared search corpus.
-- Additive: canonical document state + tombstones + monotonic change cursor.

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
