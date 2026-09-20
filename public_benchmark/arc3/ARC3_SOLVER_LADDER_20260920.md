# DEUS ARC-AGI-3 Solver Ladder — 2026-09-20

## Truth boundary
This file is a source-grounded candidate ladder, not an official DEUS score claim.
Random plumbing scorecards are excluded from capability scoring.

## Runtime gates already closed
- Kaggle competition access: verified by user-side competition UI.
- ARC_API_KEY: attached in Kaggle Secrets.
- ARC public API authentication: verified.
- Public environment discovery: 25 environments fetched.
- Public action execution: sk48 random canary executed 81 actions.
- Random canary score: 0%; infrastructure evidence only.

## Candidate A — Forge milestone snapshot
Source: canivel/kaggle @ c0c613391082a5209053ed108cfc2657dd7f3807
Path: arc-prize-2026/runs/winner_pulls/forge3rd/forge3rd.py
Source claim: public leaderboard 0.86, third-place candidate at time of submission.

Architecture:
- Gemma 4 31B local vision-language model.
- Offline vLLM 0.23.0, no external inference API during competition rerun.
- Chronological rendered frame context with STEP labels.
- JSON action plans with repair.
- Per-game reflection memory.
- Failed-state action suppression.
- Official competition gateway path emits submission.parquet.

Scored profile preserved by source:
- LLM_ACTION_CANDIDATES=1
- LLM_ACTION_CONTEXT_FRAMES=4
- LLM_CANDIDATE_ARBITER=0
- LLM_CONFIDENCE_PROMPT=0
- LLM_INCLUDE_FRAME_DESCRIPTOR=0
- LLM_REFLECTION_INTERVAL=10
- VLLM_GPU_MEMORY_UTILIZATION=0.94
- VLLM_MAX_MODEL_LEN=32768

Status: copied by owner into Kaggle; GPU Save & Run jobs queued. Do not mutate this baseline before one clean reproducibility receipt.

## Candidate B — Tufa Labs duck harness
Source: canivel/kaggle @ c0c613391082a5209053ed108cfc2657dd7f3807
Path: arc-prize-2026/runs/winner_pulls/our_duckwar.py
Source claim: original milestone-winning notebook scored 1.21. The readable snapshot says it has not reproduced the same lucky result and points to the original notebook.

Mechanisms visible in public harness:
- Real competition rerun detection.
- Offline/self-contained solver bundle.
- Fast-submit gate for interactive Save Version.
- Competition Arcade on real rerun.
- Optional warpack grafts.
- Banking: retain/replay known successful prefixes.
- Recovery: refresh GAME_OVER/lock-in loops.
- Short-circuit: stop homogeneous no-op batches.
- Retry-guard counters.
- Official gateway/submission path.

Status: strongest source-claimed public candidate currently grounded. Must distinguish original milestone notebook from readable reproduction.

## Candidate C — Reki V25 fusion
Source: canivel/kaggle @ c0c613391082a5209053ed108cfc2657dd7f3807
Path: arc-prize-2026/runs/winner_pulls/reki/reki.py

Useful additive mechanisms:
- Saliency-tiered fallback click: prioritize small, rare-colored, button-like untested components.
- Structural dead-click signatures: suppress component classes repeatedly proven inert.
- Protect any structural class that ever changes the frame.
- Pure-numpy click-path logic, avoiding GPU contention with vLLM.

Source explicitly describes the underlying Gemma path as a 0.64 base for these knobs; therefore do not replace Forge 0.86 with this wholesale. Treat the click-path mechanisms as ablation candidates only.

## Execution order
1. Preserve Forge 0.86 copy unchanged until its queued Kaggle run completes.
2. Ground the original Tufa 1.21 milestone notebook and its required attached datasets/models.
3. Build a public-safe DEUS candidate by testing only isolated mechanisms against public ARC scorecards:
   a. Forge exact baseline.
   b. + safe saliency fallback click.
   c. + conservative dead-signature pruning with LLM veto disabled initially.
   d. + successful-prefix banking/replay where framework semantics permit.
4. Promote a change only when public scorecard evidence improves or preserves solved levels without material runtime regression.
5. Use Kaggle hidden submission only for candidates with reproducibility receipts.
6. Never infer prize/award/revenue from public score or source claims.

## Current next action
Ground Tufa original milestone notebook and warpack implementation, then construct a minimal-delta candidate matrix while Forge Kaggle GPU jobs execute.
