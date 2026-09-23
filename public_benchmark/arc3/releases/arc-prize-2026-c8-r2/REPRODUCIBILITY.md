# Reproducibility

## Exact source pin

Use repository commit:

`654ef1d71095ea847aa30f7275a9fc0baa1e4d3d`

Relevant source files:

- `public_benchmark/arc3/kaggle_candidates/flash_next_340/arc-agi-flash-next-mtp.ipynb`
- `public_benchmark/arc3/kaggle_candidates/flash_next_340/upstream_build_flash_next_package.py`
- `public_benchmark/arc3/kaggle_candidates/flash_next_340/upstream_audit_flash_output.py`
- `public_benchmark/arc3/kaggle_candidates/flash_next_340/upstream_flash_agent_state_patch.py`
- `public_benchmark/arc3/kaggle_candidates/flash_next_340/upstream_flash_teardown_patch.py`
- `public_benchmark/arc3/kaggle_candidates/flash_next_340/UPSTREAM_LICENSE.txt`

## Kaggle resources

The release manifest identifies these competition resources:

- competition: `arc-prize-2026-arc-agi-3`
- dataset: `keithtyser/duck-qwen38-nvfp4-mtp-vllm-smoke-v1`
- dataset: `keithtyser/qwen38-flash-next-vllm-nvfp4-runtime-v1`
- model: `keithtyser/qwen3-8-flash-next-nvfp4/PyTorch/radixark-modelopt-fp4/1`
- accelerator used by the full baseline package: Nvidia RTX Pro 6000 class
- internet: off

## Expected full-run contract

- games: 25
- concurrency: 8
- per-game runtime: 7,200 s
- analyzer timeout: 900 s
- full notebook runtime must remain inside the Kaggle competition runtime limit
- required output includes `submission.parquet`

## Exact audited provider output

For submitted Kaggle kernel version:

`lmkimbch/deus-arc-agi3-flash-next-mtp-c8-full-r2/2`

verified output:

- 143 files
- manifest SHA256:
  `1d334c4007906918764b64d48508ecab9fa5c478298f6692271cefffa2d98def`
- `benchmark.json`: present
- `score.json`: present
- `submission.parquet`: present
- teardown/provenance/runtime diagnostic artifacts: present
- full offline audit: PASS
- audited game count: 25
- total actions: 12,937
- offline mean: `16.63835985988807`

## Audit note

The Kaggle provider emitted the log file as:

`deus-arc-agi3-flash-next-mtp-c8-full-r2.log`

The upstream audit helper originally assumed an `arc-agi3-flash-next-mtp-*` prefix when auto-discovering the log. The successful verification passed the explicit provider log basename to the same audit logic. No output artifact was modified.

## Authoritative score

The authoritative competition result is not the offline mean. It is the Kaggle result for submission ref:

`56474082`

At the time this release was written, Kaggle still reported the submission as pending.
