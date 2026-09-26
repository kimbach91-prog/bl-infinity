import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DelegatedMachineIdentityFabric,
  ZERO_FRICTION_TRUST_MODEL
} from './zero-friction-trust-fabric.mjs';

test('routine delegated action proceeds without prompt', () => {
  const f = new DelegatedMachineIdentityFabric({ now: () => 1_800_000_000_000 });
  f.registerPrincipal({
    principal_id: 'owner-meta',
    identity_kind: 'CONNECTED_ACCOUNT',
    owner_delegated: true,
    provider: 'meta',
    account_ref: 'acct://owner/meta',
    allowed_actions: ['publish', 'read', 'moderate'],
    max_risk: 0.45,
    credential_strategy: 'OAUTH_REFRESH'
  });
  const d = f.evaluate({
    principal_id: 'owner-meta',
    action: 'publish',
    action_risk: 0.2,
    device_trust: 1,
    session_trust: 1,
    anomaly_score: 0
  });
  assert.equal(d.decision, 'MACHINE_CONTINUE');
});

test('standing mandate can cover higher-risk provider-permitted action', () => {
  const f = new DelegatedMachineIdentityFabric();
  f.registerPrincipal({
    principal_id: 'treasury',
    identity_kind: 'OWNER_USER',
    owner_delegated: true,
    allowed_actions: ['spend'],
    max_risk: 0.4,
    standing_mandates: ['compute-under-budget']
  });
  const d = f.evaluate({
    principal_id: 'treasury',
    action: 'spend',
    action_risk: 0.55,
    standing_mandate: 'compute-under-budget'
  });
  assert.equal(d.decision, 'MACHINE_CONTINUE');
});

test('provider-required user presence remains an edge constraint', () => {
  const f = new DelegatedMachineIdentityFabric();
  f.registerPrincipal({
    principal_id: 'bank',
    identity_kind: 'CONNECTED_ACCOUNT',
    owner_delegated: true,
    allowed_actions: ['change-payout'],
    max_risk: 1
  });
  const d = f.evaluate({
    principal_id: 'bank',
    action: 'change-payout',
    action_risk: 0.1,
    provider_constraint: 'USER_PRESENCE_REQUIRED'
  });
  assert.equal(d.decision, 'STEP_UP_REQUIRED');
  assert.equal(d.auto_resume, true);
});

test('continuous risk can step up without password-centric blocking', () => {
  const f = new DelegatedMachineIdentityFabric();
  f.registerPrincipal({
    principal_id: 'github',
    identity_kind: 'FEDERATED_PRINCIPAL',
    owner_delegated: true,
    allowed_actions: ['deploy'],
    max_risk: 0.35,
    credential_strategy: 'WORKLOAD_FEDERATION'
  });
  const d = f.evaluate({
    principal_id: 'github',
    action: 'deploy',
    action_risk: 0.2,
    device_trust: 0.3,
    session_trust: 0.4,
    anomaly_score: 0.6
  });
  assert.equal(d.decision, 'STEP_UP_REQUIRED');
  assert.equal(d.reason, 'RISK_THRESHOLD_EXCEEDED');
});

test('revocation is immediate', () => {
  const f = new DelegatedMachineIdentityFabric();
  f.registerPrincipal({
    principal_id: 'x',
    identity_kind: 'CONNECTED_ACCOUNT',
    owner_delegated: true,
    allowed_actions: ['*']
  });
  f.revoke('x');
  const d = f.evaluate({ principal_id: 'x', action: 'read' });
  assert.equal(d.decision, 'DENY');
});

test('capabilities are short-lived and contain no raw secret', () => {
  const f = new DelegatedMachineIdentityFabric({ now: () => 1_800_000_000_000 });
  f.registerPrincipal({
    principal_id: 'worker',
    identity_kind: 'WORKLOAD',
    owner_delegated: true,
    allowed_actions: ['inference'],
    credential_strategy: 'OIDC_TOKEN_EXCHANGE'
  });
  const r = f.issueCapability({
    principal_id: 'worker',
    action: 'inference',
    resource: 'provider://model/1',
    ttl_seconds: 120
  });
  assert.equal(r.decision, 'MACHINE_CONTINUE');
  assert.equal(r.capability.expires_at - r.capability.issued_at, 120);
  assert.equal(r.capability.raw_secret_embedded, false);
  assert.equal(r.capability.transferable, false);
});

test('model defaults to delegated machine identity, not repeated human prompts', () => {
  assert.equal(ZERO_FRICTION_TRUST_MODEL.default_security_primitive, 'DELEGATED_MACHINE_IDENTITY');
  assert.equal(ZERO_FRICTION_TRUST_MODEL.human_prompt_default, false);
  assert.equal(ZERO_FRICTION_TRUST_MODEL.password_centric_security, false);
});
