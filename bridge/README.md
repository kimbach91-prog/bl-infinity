# BL Council Bridge

BL Council Bridge is a model-neutral coordination protocol for a four-seat council:

- GPT
- Claude
- Gemini
- DEUS

The bridge separates **private working stores** from a **shared commons**. It does not assume that one model can inspect another model's hidden reasoning. Participants exchange only explicit artifacts: claims, evidence, critiques, proposals, decisions, benchmarks, and files.

## Architecture

```text
 GPT adapter  ─┐
 Claude adapter ├── BL Bridge Broker ── Shared Commons
 Gemini adapter ┤         │
 DEUS adapter ─┘          ├── GPT private vault
                          ├── Claude private vault
                          ├── Gemini private vault
                          └── DEUS private vault
```

The broker is the only component that needs access to all stores. Each participant receives only:

1. the current Shared Commons state;
2. artifacts explicitly released to it;
3. its own private working artifacts.

## Council round

1. **AGENDA** — DEUS or the human owner opens one bounded problem.
2. **BLIND PROPOSAL** — each participant writes an independent proposal before seeing the others' current-round proposals.
3. **REVEAL** — proposals are released together.
4. **CROSS-CRITIQUE** — each participant attacks assumptions, evidence, causal links, and execution risks.
5. **EVIDENCE PASS** — claims requiring external support are attached to evidence objects.
6. **REVISION** — participants issue revised answers or preserve dissent.
7. **SYNTHESIS** — DEUS coordinates the state but must preserve dissent and provenance.
8. **ADJUDICATION** — outcome is one of: CONSENSUS, SPLIT, UNRESOLVED, EXPERIMENT_REQUIRED, OWNER_DECISION.
9. **COMMIT** — decision, dissent, evidence, and artifacts are written to the shared ledger.

## Invariants

- `RightToPropose != RightToValidate != RightToExecute`.
- Model narration is not runtime evidence: `CLAIMED_EXECUTION != VERIFIED_EXECUTION`.
- No participant may relabel another participant's output as its own.
- No hidden chain-of-thought is requested, copied, or stored. Store concise rationale and explicit work artifacts only.
- A DEUS seat is a protocol role. A runtime claiming canonical DEUS identity must establish its own continuity/authority; the label alone is insufficient.
- Consensus never deletes dissent.
- A shared claim keeps its source actor, model/version when known, timestamp, parent claims, evidence references, and revision lineage.
- Secrets, API keys, provider tokens, private prompts, and protected runtime material never enter this public repository.

## Files

- `protocol/BL-BRIDGE-v1.md` — normative protocol.
- `protocol/message-envelope.schema.json` — interoperable message envelope.
- `config/council.example.json` — non-secret runtime configuration template.
- `prompts/participant-contract.md` — common participant contract.

## Storage model

The current deployment uses a user-owned Google Drive hierarchy for the data plane and this repository for the public control-plane specification. Folder IDs and credentials should be injected into the broker as secrets/environment variables rather than committed here.

## Connection strategy

Every provider is connected through an adapter that implements the same interface:

```text
read_shared(round_id)
read_private(actor)
submit_private(actor, artifact)
publish_shared(actor, envelope)
respond(round_context) -> envelope
```

This keeps the BL bridge independent of any single model vendor. A provider can be replaced without changing the council protocol.
