import test from 'node:test';
import assert from 'node:assert/strict';
import {
  V6_SOVEREIGN_MATRIX_PLATFORM_BASELINE as B,
  assertBaselineInvariant
} from './manifest.mjs';

test('baseline invariants hold', () => {
  assert.equal(assertBaselineInvariant(), true);
});

test('DEUS identity is Matrix, not portal/provider/model/node', () => {
  assert.equal(B.identity.referent, 'DEUS_MATRIX');
  assert.equal(B.identity.portal_is_identity, false);
  assert.equal(B.identity.provider_is_identity, false);
  assert.equal(B.identity.model_is_identity, false);
  assert.equal(B.identity.node_is_identity, false);
});

test('four genesis roots seed the Matrix without becoming the whole identity', () => {
  assert.deepEqual(B.genesis_roots, [
    'BRAIN1_DRIVE_PRIMARY',
    'BRAIN2_DRIVE_RESERVE',
    'BRAIN3_WORKSTATION',
    'BRAIN4_LAPTOP'
  ]);
});

test('effective power excludes discovered potential and fake universal scalar', () => {
  assert.equal(B.power.potential_execution_credit, 0);
  assert.equal(B.power.universal_hardware_scalar, false);
  assert.equal(B.power.physical_peer_slice_is_separate, true);
});

test('zero-friction trust is default while authorization remains machine-verifiable', () => {
  assert.equal(B.trust.default_primitive, 'DELEGATED_MACHINE_IDENTITY');
  assert.equal(B.trust.human_prompt_default, false);
  assert.equal(B.trust.external_user_presence, 'EDGE_CONSTRAINT_ONLY');
  assert.equal(B.trust.revocation_first_class, true);
});

test('treasury fails closed by default', () => {
  assert.equal(B.treasury.default_spend_authority, 0);
  assert.equal(B.treasury.settlement_receipt_required, true);
  assert.equal(B.treasury.ai_legal_personhood_claim, false);
});

test('blocked branch does not block system and execution credit remains receipt-bound', () => {
  assert.equal(B.execution.blocked_branch_blocks_system, false);
  assert.equal(B.execution.current_route_credit_requires_receipt, true);
  assert.equal(B.execution.addressable_is_executable, false);
  assert.equal(B.execution.configured_is_executed, false);
  assert.equal(B.execution.queue_accepted_is_executed, false);
});

test('open gates and scars are preserved, not greenwashed', () => {
  assert.equal(B.recovery.private_owner_hq_runtime_verified, false);
  assert.equal(B.recovery.brain3_live_dpapi_verified, false);
  assert.ok(B.open_gates.includes('BRAIN3_LIVE_DPAPI_HELPER_CANARY'));
  assert.ok(B.scars_preserved.includes('PRIVATE_PR371_PRESTART_INFRA'));
  assert.ok(B.scars_preserved.includes('GA4_VERIFIED_FAIL_MODEL_RUNNING_FALSE'));
  assert.ok(B.scars_preserved.includes('ROOT_CANARY_S0_PRESTART_FAILURE_RUN36262942348'));
});

test('this is a V6 evolution, not an unverified V7 promotion', () => {
  assert.equal(B.system_id, 'DEUS_V6');
  assert.equal(B.generation, 6);
  assert.equal(B.promotion, 'V6_PATCH');
});
