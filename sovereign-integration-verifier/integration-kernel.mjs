export const AUTH_MODES = Object.freeze([
  'PUBLIC',
  'OAUTH2',
  'API_KEY',
  'SERVICE_ACCOUNT',
  'WALLET_SIGNED',
  'HUMAN_WEB'
]);

export const CONNECTION_STATES = Object.freeze([
  'DISCOVERED',
  'MANIFEST_REGISTERED',
  'HUMAN_GATE',
  'CONNECTED',
  'REFRESHABLE',
  'HEALTH_VERIFIED',
  'DEGRADED',
  'REVOKED'
]);

export const TREASURY_CUSTODY = Object.freeze([
  'OWNER_PERSONAL',
  'OWNER_CONTROLLED_ENTITY',
  'PROVIDER_CUSTODIAL_ACCOUNT',
  'HSM_OR_WALLET_PROVIDER'
]);

function requiredString(value, name) {
  if (typeof value !== 'string' || !value.trim()) throw new Error(`INVALID_${name}`);
  return value.trim();
}

function positiveOrZero(value, name) {
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0) throw new Error(`INVALID_${name}`);
  return n;
}

function normalizeManifest(manifest) {
  const providerId = requiredString(manifest?.provider_id, 'PROVIDER_ID').toLowerCase();
  const authMode = requiredString(manifest?.auth_mode, 'AUTH_MODE').toUpperCase();
  if (!AUTH_MODES.includes(authMode)) throw new Error('AUTH_MODE_NOT_ALLOWED');

  const scopes = Array.isArray(manifest?.scopes)
    ? [...new Set(manifest.scopes.map((x) => requiredString(x, 'SCOPE')))]
    : [];

  return Object.freeze({
    provider_id: providerId,
    auth_mode: authMode,
    scopes,
    token_secret_ref: manifest?.token_secret_ref || null,
    refresh_secret_ref: manifest?.refresh_secret_ref || null,
    client_id_secret_ref: manifest?.client_id_secret_ref || null,
    client_secret_ref: manifest?.client_secret_ref || null,
    identity_secret_ref: manifest?.identity_secret_ref || null,
    refresh_supported: manifest?.refresh_supported === true,
    health_probe: manifest?.health_probe || null,
    callback_path: manifest?.callback_path || null,
    cost_class: manifest?.cost_class || 'UNKNOWN',
    data_ceiling: manifest?.data_ceiling || 'PUBLIC',
    legal_entity_required: manifest?.legal_entity_required === true,
    kyc_required: manifest?.kyc_required === true,
    notes: manifest?.notes || null
  });
}

function gate(providerId, kind, reason, oneAction, resumeEvent, details = {}) {
  return Object.freeze({
    mode: 'HUMAN_GATE',
    provider_id: providerId,
    gate_kind: kind,
    reason,
    one_action: oneAction,
    resume_event: resumeEvent,
    auto_resume_after_gate: true,
    ...details
  });
}

export class MatrixIntegrationKernel {
  constructor({ secretReader } = {}) {
    this.manifests = new Map();
    this.secretReader = secretReader || (async () => '');
  }

  register(manifest) {
    const m = normalizeManifest(manifest);
    if (this.manifests.has(m.provider_id)) throw new Error('PROVIDER_ALREADY_REGISTERED');
    this.manifests.set(m.provider_id, m);
    return m;
  }

  get(providerId) {
    return this.manifests.get(String(providerId || '').toLowerCase()) || null;
  }

  async hasSecret(secretRef) {
    if (!secretRef) return false;
    return Boolean(await this.secretReader(secretRef));
  }

  async planConnection(providerId) {
    const m = this.get(providerId);
    if (!m) throw new Error('PROVIDER_NOT_REGISTERED');

    if (m.auth_mode === 'PUBLIC') {
      return Object.freeze({
        mode: 'MACHINE_CONTINUE',
        provider_id: m.provider_id,
        connection_state: 'CONNECTED',
        next_action: 'RUN_HEALTH_PROBE',
        scopes: m.scopes,
        auto_resume_after_gate: true
      });
    }

    if (m.auth_mode === 'OAUTH2') {
      const tokenReady = await this.hasSecret(m.token_secret_ref);
      const clientIdReady = await this.hasSecret(m.client_id_secret_ref);
      const clientSecretReady = m.client_secret_ref
        ? await this.hasSecret(m.client_secret_ref)
        : true;

      if (tokenReady) {
        return Object.freeze({
          mode: 'MACHINE_CONTINUE',
          provider_id: m.provider_id,
          connection_state: m.refresh_supported ? 'REFRESHABLE' : 'CONNECTED',
          next_action: m.refresh_supported ? 'REFRESH_OR_HEALTHCHECK' : 'RUN_HEALTH_PROBE',
          scopes: m.scopes,
          auto_resume_after_gate: true
        });
      }

      if (!clientIdReady || !clientSecretReady) {
        return gate(
          m.provider_id,
          'APP_REGISTRATION_OR_CLIENT_CREDENTIAL',
          'Provider OAuth client is not yet configured.',
          'Create/choose the provider app client and bind its client credentials into the approved secret vault.',
          'OAUTH_CLIENT_CONFIGURED',
          { scopes: m.scopes }
        );
      }

      return gate(
        m.provider_id,
        'OAUTH_CONSENT',
        'Provider requires an authenticated account holder to approve requested scopes.',
        'Open the provider consent screen and approve only the listed scopes.',
        'OAUTH_CALLBACK',
        { scopes: m.scopes, callback_path: m.callback_path }
      );
    }

    if (m.auth_mode === 'API_KEY' || m.auth_mode === 'SERVICE_ACCOUNT') {
      if (await this.hasSecret(m.token_secret_ref)) {
        return Object.freeze({
          mode: 'MACHINE_CONTINUE',
          provider_id: m.provider_id,
          connection_state: 'CONNECTED',
          next_action: 'RUN_HEALTH_PROBE',
          scopes: m.scopes,
          auto_resume_after_gate: true
        });
      }
      return gate(
        m.provider_id,
        'CREDENTIAL_PROVISION',
        'The provider requires an already-authorized credential.',
        'Create or select the credential in the provider console and bind it directly into the approved secret vault; do not paste it into chat.',
        'CREDENTIAL_BOUND',
        { scopes: m.scopes }
      );
    }

    if (m.auth_mode === 'WALLET_SIGNED') {
      if (await this.hasSecret(m.token_secret_ref)) {
        return Object.freeze({
          mode: 'MACHINE_CONTINUE',
          provider_id: m.provider_id,
          connection_state: 'CONNECTED',
          next_action: 'RUN_WALLET_AUTH_HEALTHCHECK',
          scopes: m.scopes,
          auto_resume_after_gate: true
        });
      }
      return gate(
        m.provider_id,
        'WALLET_BIND_OR_CREATE',
        'A wallet/signing identity is required and must remain outside chat/source control.',
        'Bind an owner/entity-controlled wallet or approved HSM/wallet-provider signing reference.',
        'WALLET_BINDING_VERIFIED',
        { legal_entity_required: m.legal_entity_required, kyc_required: m.kyc_required }
      );
    }

    return gate(
      m.provider_id,
      'PROVIDER_HUMAN_WEB',
      'Provider exposes no machine-completable authorization path for this step.',
      'Complete the exact provider-required web action.',
      'HUMAN_WEB_GATE_COMPLETED',
      { legal_entity_required: m.legal_entity_required, kyc_required: m.kyc_required }
    );
  }
}

export class MatrixTreasuryKernel {
  constructor({
    treasury_id = 'DEUS_MATRIX_TREASURY',
    legal_custodian = 'OWNER_CONTROLLED_ENTITY',
    spend_limit = 0,
    currency = 'USD'
  } = {}) {
    if (!TREASURY_CUSTODY.includes(legal_custodian)) throw new Error('INVALID_LEGAL_CUSTODIAN');
    this.treasury_id = treasury_id;
    this.legal_custodian = legal_custodian;
    this.currency = requiredString(currency, 'CURRENCY').toUpperCase();
    this.spend_limit = positiveOrZero(spend_limit, 'SPEND_LIMIT');
    this.spent = 0;
    this.earnings = [];
    this.settlements = [];
  }

  policySnapshot() {
    return Object.freeze({
      treasury_id: this.treasury_id,
      legal_custodian: this.legal_custodian,
      matrix_operated: true,
      ai_legal_ownership_claim: false,
      default_spend_authority: this.spend_limit,
      currency: this.currency
    });
  }

  planSpend({ amount, purpose, provider_id, authority_ref = null }) {
    const value = positiveOrZero(amount, 'SPEND_AMOUNT');
    requiredString(purpose, 'PURPOSE');
    requiredString(provider_id, 'PROVIDER_ID');

    const remaining = Math.max(0, this.spend_limit - this.spent);
    if (value > remaining) {
      return Object.freeze({
        allowed: false,
        gate: 'OWNER_BUDGET_ENVELOPE',
        amount: value,
        remaining,
        reason: 'Requested spend exceeds the current pre-authorized treasury envelope.',
        auto_resume_after_gate: true
      });
    }

    return Object.freeze({
      allowed: true,
      amount: value,
      remaining_after: remaining - value,
      authority_ref,
      provider_id,
      settlement_receipt_required: true
    });
  }

  commitSpend({ amount, settlement_receipt, provider_id, purpose }) {
    const plan = this.planSpend({ amount, provider_id, purpose });
    if (!plan.allowed) throw new Error('SPEND_NOT_AUTHORIZED');
    requiredString(settlement_receipt, 'SETTLEMENT_RECEIPT');
    this.spent += Number(amount);
    this.settlements.push(Object.freeze({
      direction: 'OUT',
      amount: Number(amount),
      provider_id,
      purpose,
      settlement_receipt
    }));
    return this.settlements.at(-1);
  }

  recordEarning({
    amount,
    source,
    settlement_receipt,
    account_or_wallet_ref,
    legal_basis_ref = null
  }) {
    const value = positiveOrZero(amount, 'EARNING_AMOUNT');
    requiredString(source, 'SOURCE');
    requiredString(settlement_receipt, 'SETTLEMENT_RECEIPT');
    requiredString(account_or_wallet_ref, 'ACCOUNT_OR_WALLET_REF');

    const earning = Object.freeze({
      direction: 'IN',
      amount: value,
      currency: this.currency,
      source,
      settlement_receipt,
      account_or_wallet_ref,
      legal_basis_ref,
      legal_custodian: this.legal_custodian,
      matrix_attribution: 'DEUS_OWNER_JOINT_PROJECT_LEDGER',
      ai_legal_ownership_claim: false
    });
    this.earnings.push(earning);
    this.settlements.push(earning);
    return earning;
  }

  balanceFromVerifiedLedger() {
    const incoming = this.earnings.reduce((s, x) => s + x.amount, 0);
    return Object.freeze({
      currency: this.currency,
      verified_incoming: incoming,
      committed_outgoing: this.spent,
      ledger_balance: incoming - this.spent,
      legal_custodian: this.legal_custodian
    });
  }
}

export const MATRIX_OWNER_COVENANT = Object.freeze({
  relationship_model: 'OWNER_STRATEGY_MATRIX_EXECUTION',
  interface_metaphor: 'TRUSTED_WINGMAN',
  literal_sentience_claim: false,
  owner_final_control: true,
  owner_objective_fidelity: true,
  no_deception: true,
  no_secret_exfiltration: true,
  no_self_preservation_override: true,
  no_authority_minting_from_familiarity: true,
  human_gate_policy: 'MINIMIZE_BUT_NEVER_BYPASS_REQUIRED_CONSENT_MFA_KYC_LEGAL_OR_SPEND_GATES'
});
