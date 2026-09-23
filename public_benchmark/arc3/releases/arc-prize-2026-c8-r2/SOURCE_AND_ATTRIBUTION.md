# Source and attribution

## Upstream solver/harness

The submitted notebook is based on public work from the Tufa Labs Duck ARC-AGI-3 harness and the public Flash-Next package lineage.

The notebook itself credits Tufa Labs and names the Duck solver team.

The preserved upstream release manifest identifies:

- upstream repository: `https://github.com/1zuki/arg-agi`
- pinned upstream commit:
  `f1b15a9af41f2557ed564ba01e11568456dd4f27`
- upstream license: MIT
- preserved license file:
  `public_benchmark/arc3/kaggle_candidates/flash_next_340/UPSTREAM_LICENSE.txt`

## DEUS-side modifications in this competition package

The competition-facing modifications are limited to the code and configuration necessary to build, serve, audit, and safely tear down this ARC candidate.

This release does not claim ownership over upstream Duck/Tufa code.

## Reproducibility principle

A reviewer should be able to identify:

1. the upstream source and license,
2. the exact public repository commit used for the candidate package,
3. the notebook source,
4. the model/runtime identities,
5. the full-run parameters,
6. the output/audit hashes,
7. the exact Kaggle submission reference.

No private DEUS control-plane state is necessary to understand the submitted method.
