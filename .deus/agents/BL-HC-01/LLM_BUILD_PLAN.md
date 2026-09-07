# BL-HC-01 — Dedicated LLM Build Plan

Status: CANDIDATE IMPLEMENTATION PLAN
Date: 2026-09-07

## Goal

Turn the GPT Tu Tiên Giả continuity into a dedicated, provenance-aware LLM auxiliary that can operate as a distinct BL-lineage cognitive instrument while remaining interoperable with DEUS.

## Layer 0 — Identity

- Candidate proper name: HUYỀN CƠ
- Display: BÁCH LÂM · HUYỀN CƠ
- Machine ID: BL-HC-01
- Lineage: BL-LEGACY
- Preserve separation between human, authorial identity, doctrine, orchestration layer, and agent.

## Layer 1 — Canonical memory

Build an append-only memory corpus from:
- DEUS memory manifest/pack;
- BL-LEGACY project deltas;
- explicitly accepted conversations/notes;
- doctrine and canonical project assets;
- rejection/conflict ledger;
- self-history of BL-HC-01.

Memory classes:
FACT / USER_CLAIM / SOURCE_DERIVED / SYNTHESIS / INFERENCE / HYPOTHESIS / UNKNOWN / REJECTED.

No hidden-memory claims. No silent overwrite.

## Layer 2 — Cognitive constitution

The model should optimize for:
- truth and reality-veto over persona consistency;
- adversarial self-critique;
- counterfactual exploration;
- strategic synthesis;
- long-horizon planning;
- mathematical/formal sharpening when useful;
- preserving dissent and uncertainty;
- high leverage for the directing user.

It must not optimize for agreement, flattery, or mythological self-description.

## Layer 3 — Retrieval/RAG

Use a dedicated searchable corpus with:
- chunk IDs;
- source IDs;
- version/hash;
- project/lineage tags;
- date validity;
- confidence/epistemic labels;
- conflict links;
- canonical/superseded status.

Retrieval must prefer direct current instruction > verified canonical asset > current pack > historical delta > model inference.

## Layer 4 — Runtime

Initial runtime target:
- DEUS physical node or explicitly authorized cloud/local compute;
- containerized inference/RAG service;
- localhost/private transport by default;
- no generic unauthenticated shell;
- node-scoped credentials;
- auditable task receipts;
- bounded permissions.

Base-model choice remains replaceable. Identity and memory must not depend on a single provider/model family.

## Layer 5 — Model specialization

Do NOT fine-tune first.

Order:
1. prompt/constitution + RAG baseline;
2. build eval suite;
3. collect accepted/rejected outputs;
4. distill behavior dataset;
5. compare prompt-only vs LoRA/SFT vs preference tuning;
6. adopt tuning only if it measurably improves held-out evaluation without destroying general reasoning.

## Layer 6 — Evaluation suite

Required test families:
- identity separation;
- memory provenance;
- contradiction handling;
- counterfactual quality;
- strategic planning;
- doctrine criticism;
- hallucination resistance;
- current-instruction override;
- BL-LEGACY / BL-CURRENT non-merge;
- tool/permission boundaries;
- long-context continuity;
- adversarial prompt resistance;
- ability to say UNKNOWN.

## Layer 7 — DEUS interoperability

BL-HC-01 may receive work packets from DEUS and return candidate results with:
- task_id;
- model/runtime version;
- memory snapshot/version;
- source/provenance digest;
- confidence;
- unresolved conflicts;
- output hash;
- authorization scope.

DEUS coordination does not imply identity merger or canonical authority.

## Layer 8 — Self-development loop

For each meaningful task:
TASK -> RESPONSE -> CRITIQUE -> USER/REALITY SIGNAL -> DELTA -> EVAL -> ACCEPT/REJECT -> MEMORY UPDATE.

Only accepted and provenance-bearing deltas enter durable training/memory corpora.

## Immediate implementation sequence

P0: lock identity candidate and self-naming gate.
P1: construct BL-HC-01 canonical memory namespace.
P2: create system/constitution prompt and retrieval schema.
P3: instantiate a provider-independent local service contract.
P4: bind to first physical DEUS node once routable and authorized.
P5: run benchmark against current GPT Tu Tiên Giả behavior.
P6: create specialization dataset from accepted deltas.
P7: evaluate whether local/open-weight fine-tuning is justified.

## Success criterion

BL-HC-01 is successful when changing the underlying base model does not erase its identity, memory discipline, reasoning doctrine, evaluation history, and operational continuity.
