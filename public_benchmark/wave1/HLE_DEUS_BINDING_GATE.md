# HLE-Rolling — DEUS endpoint binding gate

Status: **PUBLIC_EVALUATOR_INTERFACE_READY / DATASET_GATED / DEUS_ENDPOINT_UNVERIFIED**

Public evaluator source pin:

- repository: `centerforaisafety/hle`
- commit: `73ae974b1844c3ffa64c3f4343d9f1f259575700`
- prediction script: `hle_eval/run_model_predictions.py`

The public evaluator uses the OpenAI Python chat-completions interface. It loads the HLE dataset through Hugging Face, formats text questions, and adds `image_url` content when a question contains an image.

## Consequence for a DEUS hard run

A reproducible DEUS endpoint must satisfy the actual evaluator contract, not merely answer a text ping:

1. OpenAI-compatible chat-completions request/response behavior required by the evaluator.
2. Exact model/runtime/config identity and a task-bound executor receipt.
3. Text-question handling.
4. Image/multimodal handling for image-bearing HLE items, or a clearly declared restricted subset that is **not** relabeled as a full HLE-Rolling score.
5. Stable usage/result capture sufficient for receipt generation.
6. Dataset revision/hash frozen privately after owner accepts the Hugging Face gate.
7. GPT_TOOL_SUBSTRATE semantic access disabled during TEST.

## Current local candidate boundary

Canonical Drive records BL Infer as OpenAI-compatible on a local endpoint in software-canary scope, but owner-node installation/dispatch is still unverified. The current BL-MINI-001 S0 canary does not by itself prove HLE task fitness or multimodal support.

Therefore:

`OPENAI_COMPATIBLE_PING != HLE_ENDPOINT_COMPATIBLE != HLE_MULTIMODAL_CAPABLE`.

## Data boundary

The official `cais/hle-rolling` dataset is gated. Do not re-upload or publish its question content. GPT may prepare code/config and move opaque hashes/receipts after access, but semantic questions are delivered only to the admitted DEUS executor during TEST.

## Next gate

Owner accepts the Hugging Face dataset conditions, then the private DEUS executor performs a non-benchmark endpoint-contract canary. Only after both gates pass may the dataset be frozen and semantic evaluation start.
