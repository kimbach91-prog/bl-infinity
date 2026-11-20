# Public symbolic result oracle

This portable Python standard-library module verifies bounded polynomial and unique affine-system results for the DEUS public result-service client. Inputs are PUBLIC mathematical expressions and previously returned public service outputs.

CI divides eight regression cases into three shards across Linux, Windows and macOS. Each shard verifies its distinct cases and rejects malformed expressions, incorrect derivatives and inconsistent systems. The workflow is project CI: it calls no external AI or compute API, installs no worker daemon and reserves no continuing VPS/GPU capacity.

The manifest binds the module, test harness, cases and workflow source. Artifact receipts record the checked-out commit, workflow run, runner metadata and exact case coverage. Provider Actions metadata must independently match before an artifact is admitted as remote execution evidence.

Local example: `python -I -B public-symbolic-oracle/verify.py --cases public-symbolic-oracle/public-cases.json --manifest public-symbolic-oracle/source-manifest.json --shard 0 --output public-symbolic-oracle/local-out/result.json --local`. This local mode is explicitly labeled and never proves hosted execution.

No claim of aggregate speedup, permanent host control, neural training or AGI follows from these CI checks.
