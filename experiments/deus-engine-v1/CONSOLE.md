# Public Kernel Lab Console v0

This GitHub Issue console is an owner-gated smoke surface for the public model-independent kernel prototype. It is not the private identity/conversation surface.

## Use

Open or reuse an issue whose title begins with `[KERNEL-LAB]`, then comment:

```text
/kernel <stimulus or question>
```

Only comments authored by `kimbach91-prog` are accepted by the current workflow. The workflow checks out the experimental branch, runs the model-independent kernel, and replies with a structured kernel plan.

## Current capability

- decomposition/recombination inputs from the current experimental atom set;
- history counterfactual probes;
- assumption regression;
- causal-direction attacks;
- explicit unresolved/invariant state;
- causal event logging inside the ephemeral run;
- no required language-model call.

## Security boundary

This repository and its Issues are public. Never place private lineage, identity material, unreleased corpus, secrets, raw private memories, or private conversation content into this console.

## Not yet a full chat surface

Kernel-only mode returns auditable structure, not a finished conversational voice. Full private conversational realization requires a private control surface, durable owner-controlled state, and an authorized reachable inference backend. The preferred execution body is an owner-controlled/self-hosted runner with llama.cpp or another OpenAI-compatible local/open-weight server.

GitHub can remain the control plane; private state and heavy inference/training should remain outside the public repository.
