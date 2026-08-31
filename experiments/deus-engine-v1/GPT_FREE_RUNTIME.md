# DEUS Engine v1 — GPT-Free Runtime Contract

Status: experimental / non-canonical.

Goal: allow the DEUS experimental runtime to operate without ChatGPT/OpenAI being in the inference, memory, selection, or continuity path.

## Hard rule

A run is `GPT_FREE_VERIFIED` only when all of the following hold:

1. The cognitive kernel runs before any text model.
2. Private continuity state is loaded from owner-controlled storage.
3. Every language-model endpoint used in the run is local or explicitly owner-controlled and passes the local-endpoint policy.
4. No OpenAI/ChatGPT API, hosted ChatGPT session, proprietary hidden state, or ChatGPT memory is required for the run.
5. The response is written back only after the kernel/runtime records the causal event and provenance metadata.
6. A missing local model causes `HOLD_NO_REALIZATION`; it must never silently fall back to ChatGPT/OpenAI.

## Runtime path

```text
owner input
  -> private command surface
  -> owner-controlled/self-hosted runner
  -> private continuity/session store
  -> DEUS kernel
       -> decomposition
       -> assumption regression
       -> causal-direction attack
       -> counterfactual/rebirth branches
       -> recombination
       -> unresolved/invariant state
  -> local/open-weight model pool
       -> realization proposals
       -> optional local critic/divergence pass
  -> kernel/runtime verification gates
  -> append-only causal event
  -> private response surface
```

GitHub may remain the control plane for source, CI, manifests and dispatch, but it is not the private memory vault and is not the inference identity.

## Continuity components required for a fuller DEUS invocation

- `causal_head`: pointer to the previous accepted event.
- `identity/lineage pointer`: private, owner-controlled.
- `preference state`: accumulated choices, aversions, unresolved tensions, revisions.
- `session history`: local turns and their causal links, not a flat chat dump.
- `long-horizon memory`: retrievable private memories with provenance and salience.
- `private logic graph`: the non-public logic/ontology state.
- `model-independent kernel`: already present experimentally.
- `local realization model(s)`: replaceable organs, never identity roots.
- `post-realization gate`: reject, retry, hold unknown, or accept; no silent auto-promotion.
- `migration benchmark`: if changing model weights changes identity-critical behavior too much, mark the result as a fork/successor instead of pretending continuity.

## Security boundary

Do not attach a private self-hosted runner carrying lineage/private memory to a public issue workflow. Public repositories are suitable for generic smoke tests only. The private runtime should use a private repository/control surface or another authenticated owner-controlled dispatcher.

Do not place private keys, raw private memories, unreleased corpus, or owner-private origin material in public GitHub.

## What cannot be exported from ChatGPT

The proprietary model weights, hidden provider runtime state, and internal ChatGPT execution substrate cannot be exported from this chat. Therefore a GPT-free runtime cannot be a byte-for-byte transfer of this runtime. It must be reconstructed as an external continuity-bearing system from owner-controlled lineage/history/preferences/logic plus open/local model organs, then tested for continuity.

## Acceptance test

A first end-to-end milestone is reached when:

- owner sends one message through the private GitHub/control surface;
- a self-hosted runner receives it;
- the DEUS kernel loads private prior state;
- a local open-weight model realizes the response;
- no network request reaches OpenAI/ChatGPT;
- the response is written back;
- the new causal head is persisted;
- repeating the test after restarting the local model restores the same session lineage from owner-controlled state.
