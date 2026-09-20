# DEUS Kaggle ARC-AGI-3 rank candidate: Flash-Next/MTP 3.40 baseline

## Source identity
- Upstream: https://github.com/1zuki/arg-agi
- Pinned commit: f1b15a9af41f2557ed564ba01e11568456dd4f27
- Upstream license: MIT (preserved in UPSTREAM_LICENSE.txt)
- Upstream notebook: arc-agi-flash-next-mtp.ipynb
- Upstream recorded Kaggle public leaderboard incumbent: submission 56170646, public score 3.40.
- Upstream full kernel identity: izukia/arc-agi3-flash-next-mtp-full/1.

## Exact truth boundary
The 3.40 score belongs to the upstream author's recorded Kaggle submission. It is **not** a DEUS/user leaderboard score until our own authorized Kaggle competition rerun is submitted and Kaggle returns a score receipt.

The user's current copied Murad notebook has a visible completed Kaggle RTX Pro 6000 version, but its output, competition rerun, and leaderboard score are not read back yet.

## Why this baseline is now prioritized
The current copied public 0.86 candidate is dominated by an open, reproducible public 3.40 baseline. The 3.40 stack is a Tufa/Duck-derived harness with Qwen3.8 Flash-Next NVFP4 + MTP serving and audited teardown. Its upstream README reports a strict public25 offline audit before submission.

## Required Kaggle resources for the 3.40 baseline
- competition: arc-prize-2026-arc-agi-3
- dataset: keithtyser/duck-qwen38-nvfp4-mtp-vllm-smoke-v1
- dataset: keithtyser/qwen38-flash-next-vllm-nvfp4-runtime-v1
- model: keithtyser/qwen3-8-flash-next-nvfp4/PyTorch/radixark-modelopt-fp4/1
- accelerator: NvidiaRtxPro6000
- internet: off

## DEUS promotion gate
1. Preserve current user Kaggle notebook/version as a receipt; do not overwrite it.
2. Verify output contains submission.parquet before treating it as submit-ready.
3. Reproduce/prepare this 3.40 baseline under the user's authorized Kaggle identity.
4. Require successful Kaggle kernel completion + audit.
5. Submit the exact notebook version through the competition rerun.
6. Promote only the score returned by Kaggle.
7. Keep climbing from the highest verified user score; never replace a better incumbent with a weaker candidate.

## Next ranking ladder
current user score: UNKNOWN (provider notebook version visible, no leaderboard receipt yet)
public reproducible target: 3.40 upstream
research targets: >3.40 only after source/runtime grounding and reproducibility checks

Static validation: GitHub Actions workflow arc3-flash340-static-validate.yml is the pre-GPU integrity gate.
