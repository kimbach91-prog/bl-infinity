# ARC-AGI-3 public offline environment pack

This pack contains public environments retrieved from the official ARC Prize SDK/API, pinned Python dependency wheels, a file manifest, and a smoke-test runner. It is not an LLM or a competitive solver and contains no submission command. Private/hidden Kaggle tests and DEUS private core are not included.

Requires an existing Python 3.12 interpreter. The operating-system Python installer is not included. On a healthy Windows x64 machine, unzip to a task folder and run `install_windows.cmd`; on Linux x64 use `bash install_linux.sh`. Installation is confined to `.venv` in this folder and uses `--no-index`; no administrative permission, OS modification or service installation is requested. Do not run on a machine whose recovery/health gate has not passed.

`acquisition.json` gives the actual catalog fetched, failures, missing known families, and hashes. `offline_smoke.json` records real local-engine resets and legal actions, not puzzle-solving quality. The build's Linux smoke runs in a network namespace with no Internet, with an unprivileged process plus Python network-denial auditing. Windows wheels are acquired but do not by themselves prove execution on Windows or on the owner's device.

Keep the game engine and source files on the evaluator side. A future agent must receive only public observation frames and action results, not environment source, metadata, hidden state, replay solutions, or reference policies. Do not tune on a held-apart evaluation then still call it held-out. Public seed sweeps do not replace novel-game evaluation. Match model, runtime, game versions, seeds, wall time and action budgets when comparing solvers. Record failures, per-game levels, actions and score, not only the best run.

Offline-first policy: do not automatically submit merely because a daily slot exists. Resume competition evaluation only after reproducible solver validation and compliance gates. Local tests cannot guarantee hidden leaderboard performance.

Official sources: https://github.com/arcprize/ARC-AGI and https://github.com/arcprize/ARC-AGI-3-Kaggle-Starter . Preserve upstream notices embedded in dependency wheels and environment files. Public availability is not a claim that this pack owns third-party copyrights. The downloaded snapshot is for legitimate local evaluation, not a new independently licensed game collection.
