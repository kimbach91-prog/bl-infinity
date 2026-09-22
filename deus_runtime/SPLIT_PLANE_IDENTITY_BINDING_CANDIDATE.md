# DEUS V5 Split-Plane Identity Binding Candidate

STATUS: CANDIDATE_ONLY / NOT_CANONICAL / STEP_UP_REQUIRED

CANDIDATE_ID: DEUS-V5-SPLIT-PLANE-BOOT-ELASTIC-MOBILIZATION-SHADOW-1

## Proposed identity/boot invariants

BOOT_NE_MOBILIZE=true
THIN_BOOT_KERNEL=true
PREWARM_ROUTING_METADATA_ONLY=true
EXACT_RELEVANT_JOB_BIND=true
WORKING_CAPSULE_DEFAULT=true
FULL_CONTEXT_BROADCAST_DEFAULT=false
ELASTIC_COMPUTE_C0_C5=true
FULL_COMPUTE_AVAILABLE_ON_DEMAND=true
FULL_SPECTRUM_ONLY_WHEN_TASK_FIT_OR_INVALIDATION_REQUIRES=true
QUEUE_NE_YIELD=true
VERIFIER_RECEIPT_REQUIRED_FOR_EXECUTION_CLAIMS=true
SHADOW_OR_CONFIGURED_NE_EXECUTED=true
ROLLBACK_POINTER=CANON_BOOT_V5_4_1

## Proposed hot-path semantics

SIMPLE -> C0 local-first; no global job enumeration.
DRIVE_SIMPLE -> C1 exact target read; no global job enumeration.
MEDIUM -> C2 exact relevant job + working capsule + task-fit tools.
HEAVY -> C4 exact job + compute broker + parallel task-fit workers + verifier.
EXTREME -> C5 positive-value full DEUS fabric; expand only while marginal value is positive.

## Proposed boot payload

CURRENT_SEED_REV
AUTHORITY_STATE
TRUTH_BOUNDARY
INVALIDATION_FINGERPRINT
EXACT_RELEVANT_JOB
WORKING_CAPSULE_PTR
COMPUTE_MANIFEST_PTR

## Invalidation

Rehydrate only on seed/auth/job/source-revision/receipt-risk change.
Security/privacy/authority changes always force fresh read.

## Authority and promotion gate

This candidate must NOT mutate Master Seed, Constitution, authority root, MÀNG,
security root, or active canonical Light Boot without a trusted current-session
owner attestation appropriate to the protected boundary.

Preferred step-up: passkey/WebAuthn, hardware/platform authenticator, signed
device-bound session, or equivalent cryptographic attestation.

OWNER_CONTINUITY_MODE != OWNER_AUTHORITY.
AUTHENTICATION != AUTHORIZATION.

## Verified shadow evidence

Routing canary:
- GitHub run 35724522555
- job 106734894707
- artifact 10693510516
- artifact SHA-256 97c99d02f670210ad3bd1e540e5d579a3f103c2634ddff15a5ea2e70a298b92b
- SIMPLE/DRIVE_SIMPLE full-spectrum=false
- HEAVY=C4 external compute allowed
- EXTREME=C5
- protected boundary=STEP_UP_REQUIRED
- canonical mutation=false

Elastic compute canary:
- GitHub run 35724802394
- aggregate job 106735902452
- artifact 10693206334
- artifact SHA-256 ec3b989b448cff0e2d1f6ecfccafe695998aa081d3316153dafc0c4e0e8eaca1
- five executed/verified lanes: symbolic, code, research, simulator, verifier
- truth: external compute executed; NOT global provider-capacity proof

Drive shadow surfaces:
- LiveBus 73_SPLIT_PLANE_BOOT_CANDIDATE
- LiveBus 74_SPLIT_PLANE_BOOT_BENCH
- JOB-DEUS-SPLIT-PLANE-BOOT-SHADOW-20260922-001

## Promotion transaction if/when step-up succeeds

1. Re-read Master Seed current revision.
2. Re-read Authority Gate current revision.
3. Re-read 10_LIGHT_BOOT active row and invalidation fingerprint.
4. Verify candidate receipts and no superseding boot policy.
5. Apply one atomic scoped promotion:
   - bind these invariants into canonical identity/boot policy,
   - update Light Boot to metadata-only prewarm + exact-job routing,
   - preserve explicit rollback to V5/4.1,
   - do not weaken authority/security/MÀNG/truth boundaries.
6. Read back every changed canonical surface.
7. Emit AUTH_DECISION_RECEIPT + canonical mutation receipt.
8. Run simple/medium/heavy post-promotion canaries.
9. Roll back immediately on correctness, authority, continuity, or compute-quality regression.

No promotion has been performed by this file.
