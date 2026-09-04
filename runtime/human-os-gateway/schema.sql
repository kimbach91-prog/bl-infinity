BEGIN;

CREATE TABLE IF NOT EXISTS hos_users (
  id text PRIMARY KEY,
  email text NOT NULL UNIQUE,
  display_name text,
  role text NOT NULL CHECK (role IN ('founder','admin','member','auditor')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended','revoked')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hos_webauthn_credentials (
  credential_id text PRIMARY KEY,
  user_id text NOT NULL REFERENCES hos_users(id) ON DELETE CASCADE,
  public_key bytea NOT NULL,
  counter bigint NOT NULL DEFAULT 0,
  transports jsonb NOT NULL DEFAULT '[]'::jsonb,
  device_type text,
  backed_up boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz
);
CREATE INDEX IF NOT EXISTS hos_webauthn_user_idx ON hos_webauthn_credentials(user_id);

CREATE TABLE IF NOT EXISTS hos_challenges (
  id text PRIMARY KEY,
  kind text NOT NULL,
  subject text NOT NULL,
  challenge text NOT NULL,
  context jsonb NOT NULL DEFAULT '{}'::jsonb,
  expires_at timestamptz NOT NULL,
  consumed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS hos_challenges_subject_idx ON hos_challenges(subject, kind, expires_at);

CREATE TABLE IF NOT EXISTS hos_totp (
  user_id text PRIMARY KEY REFERENCES hos_users(id) ON DELETE CASCADE,
  secret_ciphertext text NOT NULL,
  kms_key_id text NOT NULL,
  enabled boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  verified_at timestamptz
);

CREATE TABLE IF NOT EXISTS hos_sessions (
  session_hash text PRIMARY KEY,
  user_id text NOT NULL REFERENCES hos_users(id) ON DELETE CASCADE,
  csrf_hash text NOT NULL,
  aal smallint NOT NULL CHECK (aal IN (1,2,3)),
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  ip_hash text,
  user_agent_hash text
);
CREATE INDEX IF NOT EXISTS hos_sessions_user_idx ON hos_sessions(user_id, expires_at);

CREATE TABLE IF NOT EXISTS hos_constitution_receipts (
  receipt_id text PRIMARY KEY,
  user_id text NOT NULL REFERENCES hos_users(id),
  constitution_version text NOT NULL,
  schedule_version text NOT NULL,
  payload jsonb NOT NULL,
  payload_hash text NOT NULL,
  signature text NOT NULL,
  signing_key_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS hos_receipts_user_idx ON hos_constitution_receipts(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS hos_node_enrollments (
  enrollment_id text PRIMARY KEY,
  user_id text NOT NULL REFERENCES hos_users(id),
  receipt_id text NOT NULL REFERENCES hos_constitution_receipts(receipt_id),
  node_name text NOT NULL,
  csr_pem text NOT NULL,
  posture jsonb NOT NULL,
  grant jsonb NOT NULL,
  certificate_chain_pem text,
  certificate_serial text,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','active','suspended','revoked','rejected')),
  created_at timestamptz NOT NULL DEFAULT now(),
  activated_at timestamptz,
  revoked_at timestamptz
);

CREATE TABLE IF NOT EXISTS hos_audit_events (
  seq bigserial PRIMARY KEY,
  event_id text NOT NULL UNIQUE,
  actor_id text,
  action text NOT NULL,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  prev_hash text,
  event_hash text NOT NULL UNIQUE,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS hos_rate_limits (
  bucket_key text PRIMARY KEY,
  tokens double precision NOT NULL,
  updated_at timestamptz NOT NULL
);

CREATE TABLE IF NOT EXISTS hos_security_receipts (
  receipt_id text PRIMARY KEY,
  control_name text NOT NULL,
  environment text NOT NULL,
  state text NOT NULL CHECK (state IN ('configured','verified','failed','revoked')),
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMIT;
