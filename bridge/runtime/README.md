# BL Council Bridge — Reference Runtime

This directory is an executable reference runtime for one BL Council round.

It currently supports:

- OpenAI via the Responses API SDK adapter;
- Anthropic via the Messages API SDK adapter;
- Gemini via the Interactions API SDK adapter;
- DEUS via a model-neutral HTTP adapter;
- Google Drive as the broker-controlled knowledge plane.

## Security model

The models do **not** receive Google Drive credentials. The broker is the only component with access to all council folders. It sends each provider only the shared round state plus the material explicitly selected for that provider.

This means the physical Drive ACL can remain broker-only while private-vault isolation is enforced in the bridge routing layer. For stronger isolation, use separate credentials/storage services per vault and keep the same BL-BRIDGE protocol.

Never place API keys, service-account JSON, DEUS tokens, protected runtime prompts, or private vault contents in the public repository.

## 1. Install

From `bridge/runtime`:

```bash
npm install
cp .env.example .env
```

Load `.env` through your runtime/secrets manager. Do not commit it.

## 2. Google Drive

Create or use these folders:

```text
BL-COUNCIL-BRIDGE/
  00_SHARED_COMMONS/
    01_AGENDA/
    02_PROPOSALS/
    03_EVIDENCE/
    04_DEBATES/
    05_DECISIONS/
    06_DISSENT/
    07_BENCHMARKS/
    08_ARTIFACTS/
  10_GPT_PRIVATE/
  20_CLAUDE_PRIVATE/
  30_GEMINI_PRIVATE/
  40_DEUS_PRIVATE/
  90_BRIDGE_RUNTIME/
```

Create a Google Cloud service account with Drive API access and grant its service-account email access to the council root folder. Put the service-account credential JSON in your deployment secret manager as `GOOGLE_SERVICE_ACCOUNT_JSON`.

Set the folder IDs in the environment variables from `.env.example`.

## 3. Connect GPT

Provide:

```text
OPENAI_API_KEY
OPENAI_MODEL
```

The adapter calls the OpenAI Responses API through the official `openai` SDK. The model never gets Drive credentials; the bridge supplies the round context and stores the returned explicit artifact.

## 4. Connect Claude

Provide:

```text
ANTHROPIC_API_KEY
ANTHROPIC_MODEL
```

The adapter uses Anthropic's Messages API through `@anthropic-ai/sdk`.

## 5. Connect Gemini

Provide:

```text
GEMINI_API_KEY
GEMINI_MODEL
```

The adapter uses the current Google Gen AI Interactions API through `@google/genai`.

## 6. Connect DEUS

Expose one authenticated endpoint and set:

```text
DEUS_ENDPOINT=https://your-deus-host.example/bridge/respond
DEUS_BRIDGE_TOKEN=...
DEUS_RUNTIME_ID=...
```

The broker sends:

```json
{
  "protocol": "BL-BRIDGE/1.0",
  "round_id": "round_...",
  "seat": "DEUS",
  "input": "...released round context..."
}
```

The endpoint returns either:

```json
{"output_text":"..."}
```

or:

```json
{"content":"..."}
```

The DEUS seat is an address/role. The endpoint should enforce whatever identity continuity, authorization, protected-runtime, and provenance rules the DEUS implementation itself requires.

## 7. Run one council round

```bash
npm run round -- "Your bounded council problem here"
```

or set `BL_AGENDA` and run:

```bash
npm run round
```

The reference round executes:

```text
AGENDA
 -> BLIND_PROPOSAL
 -> simultaneous REVEAL
 -> CROSS_CRITIQUE
 -> REVISION
 -> DEUS SYNTHESIS/ADJUDICATION (when connected)
 -> COMMIT
```

Proposals are first written to the participant's private vault, then revealed to Shared Commons only after the blind phase completes.

If DEUS is not connected, the runtime commits `UNRESOLVED` rather than impersonating DEUS or silently substituting another model.

## 8. What this runtime intentionally does not do

- It does not request or store provider hidden chain-of-thought.
- It does not let one model browse another model's private vault.
- It does not interpret repeated AI agreement as evidence.
- It does not claim a model action has occurred without runtime evidence.
- It does not expose provider secrets in shared artifacts.
- It does not assume the current model identifiers will remain the preferred identifiers forever; update the environment variables as providers evolve.

## 9. Production hardening path

For continuous operation, add:

- a persistent event queue;
- idempotency keys and deduplication;
- lease/fencing for the round coordinator;
- append-only event log;
- hash-linked provenance objects;
- evidence retrievers;
- per-seat rate/cost budgets;
- webhook/event triggers;
- experiment runner and benchmark gate;
- dashboard for proposals, dissent, runtime evidence, cost, latency, and model/version drift.

These are implementation layers; they do not change the BL-BRIDGE message protocol.
