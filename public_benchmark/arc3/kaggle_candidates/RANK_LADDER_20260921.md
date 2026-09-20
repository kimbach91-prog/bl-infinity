# ARC-AGI-3 Kaggle Rank Ladder — 2026-09-21

## Owner lane
- Provider evidence: private owner notebook version visible on Kaggle, RTX Pro 6000, Version 1 of 3, runtime 10m5s.
- Current owner leaderboard score: **UNKNOWN**.
- Output/submission.parquet: **NOT READ BACK**.
- Competition rerun: **NOT VERIFIED**.
- Leaderboard score: **NOT VERIFIED**.

## Public candidate ladder

| Candidate | Public evidence | Reproducibility | DEUS action |
|---|---:|---|---|
| Murad copied notebook | 0.86 public score on source notebook | copied by owner; owner score unknown | preserve as current provider version; do not treat as incumbent score |
| Tufa/Duck milestone | 1.21 | public harness/source | dominated by higher open candidates |
| Duck Qwen3.8 27B FP8 | 2.13 | public Kaggle notebook | reference/fallback |
| Fluid Intelligence Agent V16 | 3.11 | public Kaggle notebook, Apache-2.0 | reference/fallback |
| Flash-Next/MTP | **3.40** | MIT GitHub source, audited upstream submission 56170646 | **primary reproducible target** |
| Explore AI entry | 3.5+ dated Sep 17 | public result claim; implementation not grounded here | benchmark target only, not copy/reproduction lane |

## Promotion policy
1. Highest **owner** Kaggle score receipt is the incumbent.
2. Never replace an owner incumbent with a candidate whose expected/known public evidence is lower.
3. Offline/public-game mean is not a Kaggle leaderboard score.
4. Save & Run completion is not a competition rerun.
5. A competition submission is not a score until Kaggle reports the public score.
6. Upstream scores remain attributed to upstream authors until reproduced under the owner account.
7. Use public/open code only within license and competition rules; preserve attribution.

## Current execution
- Flash-Next/MTP source snapshot pinned from 1zuki/arg-agi at f1b15a9af41f2557ed564ba01e11568456dd4f27.
- Static integrity run 35545265115: PASS; 8 code cells compile; notebook sha256 6cff5483a6240cfe249310778a68e58df6f164acca25e5b4504eeaade838c899.
- Full Kaggle package reconstruction run 35545340036: launched; exact package receipt pending.
- After package validation, next provider gate is Kaggle authentication/upload under the owner identity, then RTX Pro 6000 full run, audit, exact-version competition submit, leaderboard readback.
