# HCS Continuous Execution Loop v0.1

Status: ACTIVE BUILD PROCEDURE
Goal: move HCS from current state to the v1.0 end-state without opening uncontrolled workstreams.

## Priority order
1. G1 normative core
2. G2 Common Interaction Envelope
3. G3 machine-readable schemas
4. G4 conformance suite
5. G5 security/privacy profile
6. G6 sovereign/offline profile
7. G7 interoperability mappings
8. G8 governance/change process
9. G9 independent implementation evidence
10. G10 independent review/publication

Higher gate work may proceed early only when it reduces risk or unblocks a lower gate.

## One iteration
Each execution iteration MUST:

1. **Observe**
   - inspect branch/PR/CI state;
   - read the current gate registry and blockers;
   - distinguish code present, CI passing, control active, independent evidence and adoption.

2. **Select one highest-value unblocked delta**
   - small enough to review and rollback;
   - directly advances one v1.0 gate;
   - no speculative subsystem creation when a gate can be advanced instead.

3. **Implement**
   - prefer tests/spec/schema/reference code over explanatory prose;
   - preserve provider neutrality and PUBLIC/BLACK_CORE boundary;
   - do not invent cryptographic primitives when reviewed standards suffice.

4. **Verify**
   - run available CI/conformance checks;
   - add negative tests for security/authority/evidence invariants;
   - record observed result, not expected result.

5. **Commit evidence**
   - commit the delta with narrow message;
   - update gate status only if evidence exists;
   - create a blocker entry when external access/review is required.

6. **Continue**
   - immediately choose the next highest-value delta in the next available execution window;
   - stop only for a hard external blocker, exhausted authorized execution window, or completion of G1–G10.

## Scheduling rule
“Continuous” means logically continuous, checkpointed execution. It does not authorize uncontrolled background compute, hidden resource use, bypassing platform limits, or acting outside granted accounts.

## Work-in-progress limit
Maximum active construction lanes: 3
- Lane A: normative/spec semantics
- Lane B: schemas/conformance/reference implementation
- Lane C: security/offline/interoperability

All other ideas go to backlog unless they unblock A–C.

## Fail-closed rules
- No evidence => no completion claim.
- Ambiguous authority => do not execute privileged action.
- Revoked/expired grant => reject.
- Unknown epistemic status => do not label as fact.
- External relay unavailable => sovereign mode must remain possible where local prerequisites exist.
- PUBLIC artifact must not contain DEUS protected prompts, raw private reasoning, secrets, private topology or routing-core internals.

## Progress metric
Primary metric: number of v1.0 gates with evidence-backed PASS.
Secondary metrics:
- normative requirements covered by conformance tests;
- negative test coverage;
- independent implementation count;
- unresolved high-severity blockers;
- offline reproducibility rate.

Velocity alone is not success if it increases semantic ambiguity or security debt.
