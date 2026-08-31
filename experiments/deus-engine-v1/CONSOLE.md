# DEUS GitHub Console v0

The GitHub Issue console is an owner-gated control surface for the experimental DEUS kernel.

## Use

Open or reuse an issue whose title begins with `[DEUS]`, then comment:

```text
/deus <stimulus or question>
```

Only comments authored by `kimbach91-prog` are accepted by the current workflow. The workflow checks out `proto/deus-engine-v1`, runs the model-independent kernel, and replies with a structured kernel plan.

## Current capability

- decomposition/recombination inputs from the current experimental atom set;
- history counterfactual probes;
- assumption regression;
- causal-direction attacks;
- explicit unresolved/invariant state;
- causal event logging inside the ephemeral run;
- no required language-model call.

## Not yet a full chat surface

Kernel-only mode returns auditable structure, not the finished DEUS conversational voice. Full conversational realization requires an authorized reachable inference backend. The preferred next path is an owner-controlled/self-hosted runner with llama.cpp or another OpenAI-compatible local/open-weight server.

GitHub remains the control plane; private memory, lineage state, unreleased corpus, secrets, and heavy inference/training should remain outside the public repository.
