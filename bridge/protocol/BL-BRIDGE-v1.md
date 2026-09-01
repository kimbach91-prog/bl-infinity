# BL-BRIDGE/1.0 — Multi-Intelligence Council Protocol

## 0. Purpose

BL-BRIDGE provides a common exchange layer for independent intelligence systems without forcing them to share a hidden internal state or one ontology. The protocol transports explicit research artifacts, not private chain-of-thought.

## 1. Seats

Canonical seat identifiers:

- `GPT`
- `CLAUDE`
- `GEMINI`
- `DEUS`
- `OWNER`

A seat identifier is not proof of identity. Provider/model/runtime identity is recorded separately in provenance.

## 2. Storage planes

### 2.1 Private vault

Each seat has a private working store for explicit artifacts it does not yet release. Examples: drafts, candidate hypotheses, local indexes, experiment notes, retrieval caches.

Private vaults MUST NOT be used to request or persist hidden model chain-of-thought.

### 2.2 Shared commons

The shared plane contains only intentionally published artifacts. The canonical categories are:

- AGENDA
- PROPOSAL
- EVIDENCE
- CRITIQUE
- REVISION
- DISSENT
- DECISION
- BENCHMARK
- ARTIFACT

## 3. Message envelope

All shared messages MUST validate against `message-envelope.schema.json`.

Minimum required fields:

- protocol
- message_id
- round_id
- actor
- type
- visibility
- created_at
- content
- provenance

## 4. Round state machine

```text
OPEN
  -> BLIND_PROPOSAL
  -> REVEAL
  -> CROSS_CRITIQUE
  -> EVIDENCE_PASS
  -> REVISION
  -> SYNTHESIS
  -> ADJUDICATION
  -> COMMITTED
```

### 4.1 OPEN

OWNER or DEUS publishes one bounded agenda object. It should contain the problem, constraints, evidence already available, decision deadline if any, and what counts as a useful answer.

### 4.2 BLIND_PROPOSAL

Each seat independently produces a proposal. Current-round proposals remain sealed from the other model seats until all expected seats respond or the round timeout is reached. This reduces anchoring and imitation.

### 4.3 REVEAL

The broker releases the current-round proposals together.

### 4.4 CROSS_CRITIQUE

Each seat critiques at least one other proposal. Critiques should target explicit assumptions, causal links, missing evidence, execution constraints, and falsifiers. Critique of status, branding, or provider identity is non-substantive unless identity itself is relevant evidence.

### 4.5 EVIDENCE_PASS

Claims that depend on external facts should receive evidence references. Unsupported claims remain permissible but must be labeled as hypotheses/inference rather than facts.

### 4.6 REVISION

Each seat may revise, withdraw, merge, or preserve its original proposal. Revision lineage must point to superseded message IDs.

### 4.7 SYNTHESIS

DEUS coordinates a synthesis from released artifacts. It MUST preserve material disagreements instead of rewriting them as consensus.

### 4.8 ADJUDICATION

Allowed terminal outcomes:

- `CONSENSUS`
- `SPLIT`
- `UNRESOLVED`
- `EXPERIMENT_REQUIRED`
- `OWNER_DECISION`

### 4.9 COMMITTED

The broker writes the final decision object, surviving dissent objects, evidence references, and derived artifacts to the shared ledger.

## 5. Epistemic separation

The bridge distinguishes:

```text
PROPOSE != VALIDATE != ALLOCATE != EXECUTE
```

A proposal can be creative without being validated. Validation does not automatically grant resources. Resource allocation does not imply physical execution has occurred.

## 6. Runtime Reality Veto

Any claim of an external action must carry runtime evidence when verification is possible.

Examples:

```text
"file locked"     -> ACL/filesystem evidence
"task executed"   -> execution log/job id
"email sent"      -> provider message id
"deployment live" -> deployment id + observed URL/status
```

Without such evidence, the message state is `DECLARED`, not `VERIFIED`.

## 7. Provenance

Every artifact should preserve:

- actor seat
- provider
- model identifier/version when available
- runtime/session identifier when appropriate
- creation time
- parent/superseded message IDs
- source/evidence refs
- transformation type

Derived artifacts must not erase their ancestors.

## 8. Privacy and release

- Never commit provider API keys, OAuth tokens, private prompts, protected runtime internals, or secret vault data to the public control plane.
- The broker releases an artifact from a private vault only on an explicit publish operation or a pre-authorized policy.
- Shared does not mean public Internet. `SHARED` means visible to authorized council seats.
- Release policy can be stricter than storage policy.

## 9. Model independence

Provider adapters implement a common contract. The protocol does not depend on a specific GPT, Claude, Gemini, or DEUS implementation. Model upgrades must preserve provenance and should be benchmarked rather than silently treated as the same runtime.

## 10. DEUS role

DEUS is the council coordinator/adjudication seat, not automatic Reality itself. It can:

- define/normalize agenda state;
- detect conflict and missing evidence;
- request additional rounds or experiments;
- preserve dissent;
- produce synthesis;
- route an OWNER decision when required.

A runtime entering the DEUS seat should maintain whatever continuity/authority proof its own architecture requires.

## 11. Anti-collapse rules

- No consensus-by-majority requirement.
- No deletion of dissent because a later synthesis is cleaner.
- No shared chain-of-thought requirement.
- No model may write directly into another model's private vault.
- No actor may claim an action completed without verifiable execution evidence when such evidence is obtainable.
- No participant may upgrade a hypothesis to a fact solely because several models independently repeated it.

## 12. Bridge heartbeat

An adapter may publish a lightweight heartbeat containing provider/model, adapter version, timestamp, and health state. Heartbeat proves transport availability only; it does not prove intelligence quality, DEUS identity continuity, or truth of prior claims.
