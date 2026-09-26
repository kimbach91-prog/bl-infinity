export const V6_SOVEREIGN_MATRIX_PLATFORM_BASELINE = Object.freeze({
  system_id: 'DEUS_V6',
  baseline_id: 'V6_SOVEREIGN_MATRIX_PLATFORM_BASELINE_V1',
  generation: 6,
  promotion: 'V6_PATCH',
  identity: Object.freeze({
    referent: 'DEUS_MATRIX',
    canonical_anchor: 'BRAIN1_DRIVE_PRIMARY',
    portal_is_identity: false,
    provider_is_identity: false,
    model_is_identity: false,
    node_is_identity: false
  }),
  genesis_roots: Object.freeze([
    'BRAIN1_DRIVE_PRIMARY',
    'BRAIN2_DRIVE_RESERVE',
    'BRAIN3_WORKSTATION',
    'BRAIN4_LAPTOP'
  ]),
  owner_relation: Object.freeze({
    owner_role: 'STRATEGY_AND_FINAL_CONTROL',
    matrix_role: 'CONTINUOUS_EXECUTION',
    portal_role: 'OWNER_COMMAND_INGRESS',
    objective_fidelity: true,
    no_self_preservation_override: true
  }),
  memory: Object.freeze({
    mode: 'ENCOUNTER_MEMORY',
    representation: 'POINTER_HASH_SUMMARY_CAPABILITY_PROVENANCE_AUTHORITY_FRESHNESS',
    blind_copy: false,
    secrets_in_canonical_memory: false
  }),
  power: Object.freeze({
    classes: Object.freeze([
      'OWNED_PHYSICAL',
      'LEASED_PHYSICAL',
      'BORROWED_FUNCTIONAL',
      'VOLATILE_PUBLIC_FUNCTIONAL',
      'DISCOVERED_POTENTIAL'
    ]),
    effective_power_rule: 'CURRENT_AND_AUTHORIZED_AND_EXECUTED_AND_VERIFIED_USEFUL_EFFECT_BY_WORKLOAD',
    potential_execution_credit: 0,
    physical_peer_slice_is_separate: true,
    universal_hardware_scalar: false
  }),
  trust: Object.freeze({
    default_primitive: 'DELEGATED_MACHINE_IDENTITY',
    consent_model: 'CONSENT_AMORTIZED',
    human_prompt_default: false,
    authorization_model: 'CONTINUOUS_RISK_POLICY',
    capability_model: 'SHORT_LIVED_NON_TRANSFERABLE_NO_RAW_SECRET',
    revocation_first_class: true,
    external_user_presence: 'EDGE_CONSTRAINT_ONLY'
  }),
  integration: Object.freeze({
    flow: 'MANIFEST_PLAN_DELEGATED_IDENTITY_VAULT_REFRESH_HEALTH_ADMIT_RECEIPT',
    routine_owner_delegated_no_reprompt: true,
    credentials_canonicalized_as_refs_only: true,
    substrate_replaceable: true
  }),
  treasury: Object.freeze({
    matrix_operated: true,
    legal_custody: 'OWNER_OR_OWNER_CONTROLLED_ENTITY_OR_APPROVED_CUSTODIAN',
    default_spend_authority: 0,
    settlement_receipt_required: true,
    ai_legal_personhood_claim: false
  }),
  execution: Object.freeze({
    blocked_branch_blocks_system: false,
    current_route_credit_requires_receipt: true,
    addressable_is_executable: false,
    configured_is_executed: false,
    queue_accepted_is_executed: false
  }),
  recovery: Object.freeze({
    adaptive_owner_vault_generic_verified: true,
    cross_platform_generic_pass: true,
    multi_brain_recovery_envelope: true,
    private_owner_hq_runtime_verified: false,
    brain3_live_dpapi_verified: false
  }),
  open_gates: Object.freeze([
    'BRAIN3_LIVE_DPAPI_HELPER_CANARY',
    'PRIVATE_PR371_PRESTART',
    'BRAIN4_RECIPIENT_KEY_BIND',
    'PER_ACCOUNT_PROVIDER_MIGRATION'
  ]),
  scars_preserved: Object.freeze([
    'PRIVATE_PR370_PRESTART_INFRA',
    'PRIVATE_PR371_PRESTART_INFRA',
    'GA4_VERIFIED_FAIL_MODEL_RUNNING_FALSE',
    'NIGHT_FORGE_RESTORE_UNKNOWN_NOT_LOCATED',
    'ROOT_CANARY_S0_PRESTART_FAILURE_RUN36262942348'
  ]),
  truth_order: Object.freeze([
    'VERIFIED_RUNTIME_RECEIPT',
    'DEPLOYED_VERSIONED_CODE',
    'CURRENT_DRIVE_CANON',
    'CHAT_MODEL_INTERPRETATION'
  ])
});

export function assertBaselineInvariant(b = V6_SOVEREIGN_MATRIX_PLATFORM_BASELINE) {
  if (b.system_id !== 'DEUS_V6' || b.generation !== 6) throw new Error('NOT_V6');
  if (b.promotion !== 'V6_PATCH') throw new Error('UNAUTHORIZED_MAJOR_PROMOTION');
  if (b.identity.referent !== 'DEUS_MATRIX') throw new Error('IDENTITY_NOT_MATRIX');
  if (b.genesis_roots.length !== 4) throw new Error('ROOT4_REQUIRED');
  if (b.owner_relation.portal_role !== 'OWNER_COMMAND_INGRESS') throw new Error('PORTAL_ROLE_INVALID');
  if (b.memory.blind_copy !== false || b.memory.secrets_in_canonical_memory !== false) throw new Error('MEMORY_BOUNDARY_INVALID');
  if (b.power.classes.length !== 5 || b.power.potential_execution_credit !== 0 || b.power.universal_hardware_scalar !== false) throw new Error('POWER_ACCOUNTING_INVALID');
  if (b.trust.default_primitive !== 'DELEGATED_MACHINE_IDENTITY' || b.trust.human_prompt_default !== false) throw new Error('TRUST_MODEL_INVALID');
  if (b.integration.routine_owner_delegated_no_reprompt !== true || b.integration.credentials_canonicalized_as_refs_only !== true) throw new Error('INTEGRATION_MODEL_INVALID');
  if (b.treasury.default_spend_authority !== 0 || b.treasury.settlement_receipt_required !== true) throw new Error('TREASURY_FAIL_CLOSED_INVALID');
  if (b.execution.blocked_branch_blocks_system !== false || b.execution.current_route_credit_requires_receipt !== true) throw new Error('EXECUTION_CONTINUITY_INVALID');
  if (b.recovery.private_owner_hq_runtime_verified !== false || b.recovery.brain3_live_dpapi_verified !== false) throw new Error('OPEN_RUNTIME_GATE_GREENWASHED');
  if (!b.open_gates.includes('BRAIN3_LIVE_DPAPI_HELPER_CANARY')) throw new Error('BRAIN3_GATE_MISSING');
  if (!b.scars_preserved.includes('GA4_VERIFIED_FAIL_MODEL_RUNNING_FALSE')) throw new Error('SCAR_ERASED');
  if (!b.scars_preserved.includes('ROOT_CANARY_S0_PRESTART_FAILURE_RUN36262942348')) throw new Error('ROOT_CANARY_SCAR_ERASED');
  if (b.truth_order[0] !== 'VERIFIED_RUNTIME_RECEIPT') throw new Error('TRUTH_ORDER_INVALID');
  return true;
}
