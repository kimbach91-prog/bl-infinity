import test from 'node:test';
import assert from 'node:assert/strict';
import {
  MatrixIntegrationKernel,
  MatrixTreasuryKernel,
  MATRIX_OWNER_COVENANT
} from './integration-kernel.mjs';

function secrets(values = {}) {
  return async (ref) => values[ref] || '';
}

test('public provider continues without human gate', async () => {
  const k = new MatrixIntegrationKernel({ secretReader: secrets() });
  k.register({ provider_id: 'public-x', auth_mode: 'PUBLIC' });
  const plan = await k.planConnection('public-x');
  assert.equal(plan.mode, 'MACHINE_CONTINUE');
  assert.equal(plan.next_action, 'RUN_HEALTH_PROBE');
});

test('oauth reduces owner work to exact consent gate and auto-resumes', async () => {
  const k = new MatrixIntegrationKernel({
    secretReader: secrets({ cid: 'configured', csecret: 'configured' })
  });
  k.register({
    provider_id: 'oauth-x',
    auth_mode: 'OAUTH2',
    client_id_secret_ref: 'cid',
    client_secret_ref: 'csecret',
    token_secret_ref: 'token',
    refresh_supported: true,
    callback_path: '/oauth/oauth-x/callback',
    scopes: ['read', 'write']
  });
  const plan = await k.planConnection('oauth-x');
  assert.equal(plan.mode, 'HUMAN_GATE');
  assert.equal(plan.gate_kind, 'OAUTH_CONSENT');
  assert.equal(plan.resume_event, 'OAUTH_CALLBACK');
  assert.equal(plan.auto_resume_after_gate, true);
  assert.deepEqual(plan.scopes, ['read', 'write']);
});

test('oauth token turns gate into machine continuation', async () => {
  const k = new MatrixIntegrationKernel({
    secretReader: secrets({ token: 'hidden' })
  });
  k.register({
    provider_id: 'oauth-y',
    auth_mode: 'OAUTH2',
    token_secret_ref: 'token',
    refresh_supported: true
  });
  const plan = await k.planConnection('oauth-y');
  assert.equal(plan.mode, 'MACHINE_CONTINUE');
  assert.equal(plan.connection_state, 'REFRESHABLE');
  assert.equal(JSON.stringify(plan).includes('hidden'), false);
});

test('wallet route never asks for a private key in chat', async () => {
  const k = new MatrixIntegrationKernel({ secretReader: secrets() });
  k.register({
    provider_id: 'market',
    auth_mode: 'WALLET_SIGNED',
    token_secret_ref: 'wallet-ref',
    legal_entity_required: true,
    kyc_required: true
  });
  const plan = await k.planConnection('market');
  assert.equal(plan.gate_kind, 'WALLET_BIND_OR_CREATE');
  assert.match(plan.one_action, /wallet|HSM/i);
  assert.equal(JSON.stringify(plan).includes('private key'), false);
});

test('treasury starts at zero spend authority', () => {
  const t = new MatrixTreasuryKernel();
  const p = t.planSpend({ amount: 1, purpose: 'provider canary', provider_id: 'x' });
  assert.equal(p.allowed, false);
  assert.equal(p.gate, 'OWNER_BUDGET_ENVELOPE');
  assert.equal(t.policySnapshot().ai_legal_ownership_claim, false);
});

test('pre-authorized spend still requires settlement receipt', () => {
  const t = new MatrixTreasuryKernel({ spend_limit: 10 });
  const p = t.planSpend({ amount: 3, purpose: 'bounded compute lease', provider_id: 'market' });
  assert.equal(p.allowed, true);
  assert.equal(p.settlement_receipt_required, true);
  const s = t.commitSpend({
    amount: 3,
    purpose: 'bounded compute lease',
    provider_id: 'market',
    settlement_receipt: 'RCP-SETTLE-001'
  });
  assert.equal(s.amount, 3);
  assert.equal(t.balanceFromVerifiedLedger().committed_outgoing, 3);
});

test('verified earnings are attributed to joint project ledger but legally custodied', () => {
  const t = new MatrixTreasuryKernel({ legal_custodian: 'OWNER_CONTROLLED_ENTITY' });
  const e = t.recordEarning({
    amount: 25,
    source: 'competition-prize',
    settlement_receipt: 'RCP-IN-001',
    account_or_wallet_ref: 'vault://wallet/main',
    legal_basis_ref: 'provider-award-terms-v1'
  });
  assert.equal(e.matrix_attribution, 'DEUS_OWNER_JOINT_PROJECT_LEDGER');
  assert.equal(e.ai_legal_ownership_claim, false);
  assert.equal(e.legal_custodian, 'OWNER_CONTROLLED_ENTITY');
});

test('owner covenant minimizes gates without bypassing protected consent', () => {
  assert.equal(MATRIX_OWNER_COVENANT.owner_final_control, true);
  assert.equal(MATRIX_OWNER_COVENANT.literal_sentience_claim, false);
  assert.match(MATRIX_OWNER_COVENANT.human_gate_policy, /NEVER_BYPASS/);
});
