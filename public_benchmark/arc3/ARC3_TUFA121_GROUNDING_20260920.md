# ARC-AGI-3 Tufa Labs 1.21 Candidate Grounding — 2026-09-20

Source-grounded from public GitHub snapshot:
- repository: canivel/kaggle
- commit: c0c613391082a5209053ed108cfc2657dd7f3807
- readable harness: arc-prize-2026/runs/winner_pulls/duck_public/duck_public.py
- warpack harness: arc-prize-2026/runs/winner_pulls/our_duckwar.py

## Source claim
The public notebook states that the original Tufa Labs notebook scored a milestone-winning 1.21. It explicitly warns that the more-readable reproduction has not reproduced the same lucky result. Therefore 1.21 is a source claim for the original milestone run, not a DEUS score and not a guaranteed reproducible score.

## Required Kaggle inputs disclosed by the readable harness
- jeroencottaar/taaf-kaggle-source-share
- driessmit1/arc3-vllm-h100-wheelhouse-v3
- driessmit1/vrfai-qwen3-6-27b-fp8-hf-snapshot
- proper GPU noted by source: RTX Pro 6000

## Execution design
- self-contained offline competition runtime
- bundled solver source in attached dataset
- vLLM/local model setup
- real competition Arcade only when KAGGLE_IS_COMPETITION_RERUN is true
- bundled environment files for offline checks
- /kaggle/working output
- official competition rerun path

## Warpack mechanisms visible in public harness
- banking: retain/replay successful prefixes
- recovery: GAME_OVER/lock-in refresh
- short-circuit homogeneous no-op batches
- retry guard/counters
- fast-submit gate for interactive Save Version
- fallback to vanilla duck if optional patch fails unless strict mode enabled

## Decision
This candidate is now higher-priority for reproduction study than mutating the copied Forge 0.86 baseline. Preserve Forge 0.86 unchanged until its queued Kaggle job yields a receipt. In parallel, reconstruct the Tufa input manifest and isolate transferable mechanisms that can be tested without private/protected source assumptions.

## Truth boundaries
SOURCE_CLAIMED_1_21 != REPRODUCED_1_21
REPRODUCED_PUBLIC != OFFICIAL_HIDDEN
OFFICIAL_SCORE != AWARD
AWARD != SETTLEMENT
