# Evidence Base — Efficient Sovereign Compute

Date: 2026-09-07
Status: REFERENCE / update before external use

## Energy constraint

- IEA, *Key Questions on Energy and AI* (2026): global data-centre electricity consumption was about 485 TWh in 2025 and is projected at about 950 TWh in 2030 in its central outlook; AI-focused data-centre electricity demand grows substantially faster than total data-centre demand.
- IEA notes that individual AI tasks are becoming much more energy efficient, while reasoning, video generation and agentic workloads can consume hundreds or thousands of times more energy per query than simple text use. Therefore efficiency gains alone do not guarantee lower aggregate demand.
- IEA also identifies fast-changing rack power density and rapid power swings as grid/supply-chain challenges.

Primary source:
https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary

## Measure real useful work, not vendor TDP

MLCommons MLPerf Inference supports power measurements at the full-system wall and reports power/energy together with benchmark performance and quality constraints. BLI-SCF should use this principle for procurement and runtime benchmarking.

Primary sources:
https://mlcommons.org/benchmarks/inference-datacenter/
https://mlcommons.org/working-groups/benchmarks/power/

## Software/hardware efficiency is moving rapidly

MLCommons reports that MLPerf has tracked more than 100x improvement in inference performance per watt for large language models over its benchmark history. This supports a policy of continually re-benchmarking rather than locking orchestration to one accelerator or one model family.

Primary source:
https://mlcommons.org/2026/07/mlperf-endpoints-v0-7-release/

MLPerf Inference v6.0 explicitly includes an interactive advanced-reasoning scenario supporting speculative decoding, and MLPerf Training v6.0 added sparse/MoE-oriented benchmarks. These are relevant to BLI-SCF's preference for speculative and sparse execution when quality permits.

Primary sources:
https://mlcommons.org/2026/04/mlperf-inference-v6-0-results/
https://mlcommons.org/2026/06/mlperf-training-v6-0-results/

## RAG is an end-to-end system workload

In August 2026 MLCommons introduced an end-to-end RAG inference benchmark spanning vector-database construction, retrieval and iterative multi-hop answering. This supports measuring BLI-SCF pipelines as complete systems instead of optimizing isolated model calls.

Primary source:
https://mlcommons.org/2026/08/endtoend-inference/

## Sovereign-compute trend

EuroHPC's 2026 AI Gigafactories procurement explicitly targets sovereign AI computing infrastructure for public and private users, combining large-scale processors, software/cloud stacks, high-bandwidth connectivity and energy-efficient data centres. The initiative also requires attention to energy efficiency, water efficiency and circularity.

Primary sources:
https://www.eurohpc-ju.europa.eu/eurohpc-joint-undertaking-launches-ai-gigafactories-call-2026-07-30_en
https://www.eurohpc-ju.europa.eu/call-tenders-selection-artificial-intelligence-gigafactory-consortia-and-establishment-ai_en

## Design implication

The evidence supports four immediate decisions:

1. Meter end-to-end energy per quality-qualified task.
2. Place a compute governor in front of every expensive model/HPC path.
3. Prefer reuse, retrieval, small specialists, sparse execution and escalation-on-evidence.
4. Package national/enterprise deployments as sovereign nodes with local data/control and interoperable federation, rather than one global centralized AI service.
