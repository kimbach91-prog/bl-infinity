-- BL Compute Federation v0.9 shared rate-limit buckets.
-- Additive and safe to retain if application rolls back to memory limiting.

CREATE TABLE IF NOT EXISTS federation_rate_limit_buckets (
  scope_key text PRIMARY KEY,
  tokens double precision NOT NULL CHECK (tokens >= 0),
  updated_at timestamptz NOT NULL,
  expires_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS federation_rate_limit_bucket_expiry_idx
ON federation_rate_limit_buckets(expires_at);
