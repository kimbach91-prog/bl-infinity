-- BL-SCA / BL-CF durable DEUS Compute Treasury (DCT) + DCC schema.
-- PostgreSQL 16+ recommended.
-- This schema is accounting infrastructure, not a claim that DCC is legal tender,
-- e-money, a deposit, a security, or publicly issuable in any jurisdiction.

CREATE TABLE IF NOT EXISTS federation_treasury_settings (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton = true),
  reserved_liabilities_usd numeric(24,8) NOT NULL DEFAULT 0 CHECK (reserved_liabilities_usd >= 0),
  dcc_min_backing_ratio numeric(12,8) NOT NULL DEFAULT 1.20 CHECK (dcc_min_backing_ratio >= 1),
  dcc_unit_value_usd numeric(24,8) NOT NULL DEFAULT 1 CHECK (dcc_unit_value_usd > 0),
  emergency_freeze boolean NOT NULL DEFAULT false,
  freeze_reason text,
  updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO federation_treasury_settings(singleton)
VALUES (true)
ON CONFLICT(singleton) DO NOTHING;

CREATE TABLE IF NOT EXISTS federation_treasury_backing (
  backing_id uuid PRIMARY KEY,
  backing_type text NOT NULL CHECK (backing_type IN ('cash','compute')),
  source_ref text NOT NULL UNIQUE,
  provider_id text,
  consent_ref text,
  face_value_usd numeric(24,8) NOT NULL CHECK (face_value_usd >= 0),
  haircut_rate numeric(12,8) NOT NULL DEFAULT 0 CHECK (haircut_rate >= 0 AND haircut_rate <= 1),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','revoked','expired')),
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz,
  revoked_at timestamptz,
  revoke_reason text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS federation_treasury_backing_effective_idx
  ON federation_treasury_backing(status, expires_at);
CREATE INDEX IF NOT EXISTS federation_treasury_backing_provider_idx
  ON federation_treasury_backing(provider_id, status)
  WHERE provider_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS federation_dcc_accounts (
  account_id text PRIMARY KEY,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','frozen','closed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS federation_dcc_ledger (
  seq bigserial PRIMARY KEY,
  event_id uuid NOT NULL UNIQUE,
  ts timestamptz NOT NULL,
  kind text NOT NULL CHECK (kind IN ('mint','transfer','burn')),
  from_account text REFERENCES federation_dcc_accounts(account_id),
  to_account text REFERENCES federation_dcc_accounts(account_id),
  amount_dcc numeric(30,8) NOT NULL CHECK (amount_dcc > 0),
  authorization_ref text,
  reference text,
  idempotency_key text NOT NULL UNIQUE,
  event_json jsonb NOT NULL,
  prev_hash text,
  hash text NOT NULL UNIQUE,
  CHECK (
    (kind='mint' AND from_account IS NULL AND to_account IS NOT NULL) OR
    (kind='transfer' AND from_account IS NOT NULL AND to_account IS NOT NULL AND from_account <> to_account) OR
    (kind='burn' AND from_account IS NOT NULL AND to_account IS NULL)
  )
);

CREATE INDEX IF NOT EXISTS federation_dcc_ledger_from_idx ON federation_dcc_ledger(from_account, seq) WHERE from_account IS NOT NULL;
CREATE INDEX IF NOT EXISTS federation_dcc_ledger_to_idx ON federation_dcc_ledger(to_account, seq) WHERE to_account IS NOT NULL;
CREATE INDEX IF NOT EXISTS federation_dcc_ledger_kind_idx ON federation_dcc_ledger(kind, seq);

-- Runtime invariants enforced by the PostgresComputeTreasury transaction layer:
-- 1. all mint/transfer/burn mutations serialize on one transaction-scoped advisory lock;
-- 2. mint fails closed if the post-mint backing ratio would fall below the configured minimum;
-- 3. transfers/burns require sufficient account balance;
-- 4. emergency freeze blocks mint/transfer but still permits burn/redemption so liabilities can shrink;
-- 5. backing expiry/revocation removes it from effective solvency immediately;
-- 6. revocation that makes outstanding DCC undercollateralized automatically activates emergency freeze;
-- 7. every DCC event is hash-chained and idempotency-keyed;
-- 8. projected knowledge value is never inserted into federation_treasury_backing unless a separate
--    realized/contracted asset has first converted it into an eligible backing class.
