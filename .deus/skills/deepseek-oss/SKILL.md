# DEUS Skill: DeepSeek OSS Compression / Regression

## Purpose
Turn the public `deepseek-ai` GitHub organization into a reusable, provenance-preserving capability pack without repeatedly re-learning unchanged regions.

## Operating policy
1. **Reuse first.** Same repo `HEAD` + same technique-registry hash => trust the cached static analysis and skip the deep scan.
2. **Delta first.** A new SHA, new repo, or new technique signature triggers analysis only for the changed surface.
3. **Static by default.** Clone and inspect source, metadata, history and licenses; never execute upstream code as part of this skill.
4. **Three-pass regression.** R1 reconstructs the current capability surface. R2 walks three recent revisions and measures technique-marker deltas. R3 synthesizes unobserved cross-category recombinations as hypotheses.
5. **Evidence boundary.** Source markers are evidence of implementation concepts, not proof of benchmark quality or causal contribution. Generated variants remain `HYPOTHETICAL_VARIANT_NOT_BENCHMARKED` until independently implemented and tested.
6. **Provenance.** Source manifest pins every synced repository to its observed `HEAD` SHA and records SPDX license metadata when GitHub exposes it.
7. **No core contamination.** Upstream repositories live under `.deus-cache/deepseek-ai/` and are not committed into the DEUS core. The skill code and verified manifests/results may be committed; raw third-party trees remain external cache.
8. **Sustained-load default.** Long jobs use the shared `.deus/runtime/load_governor.py`: bounded concurrency, inter-request pacing, provider `Retry-After`, exponential backoff with jitter, retry/time budgets and a circuit breaker. Never use tight retry loops or mechanisms intended to bypass provider limits.
9. **Checkpoint before breadth.** Large acquisition/analysis batches must persist progress so a cooldown, quota event, network fault or process restart resumes from the last verified checkpoint instead of replaying completed work.
10. **Stability over peak throughput.** A slower stable lane is preferred to a bursty lane that increases throttling, duplicate work or provider pressure.

## Fast path
```bash
python .deus/skills/deepseek-oss/deepseek_skillpack.py all
```

Optional `GITHUB_TOKEN` raises GitHub API rate limits. The pipeline discovers all current public, non-fork repositories in the organization dynamically, so newly released repositories become deltas rather than a manual curriculum.

## Output
- `.deus-state/deepseek-oss/source-manifest.json`
- `.deus-state/deepseek-oss/mastery.json`
- `.deus-state/deepseek-oss/regression.json`
- `.deus-state/deepseek-oss/regression.md`
- `.deus-state/runtime/load-governor.json` when a provider-facing worker uses the shared governor.

## Completion gate
- Unit tests green.
- Source manifest generated with zero or explicitly reviewed failures.
- R1/R2/R3 report generated.
- No upstream executable was run.
- Sustained jobs show bounded retry/concurrency behavior; repeated 429/5xx conditions must cool down instead of amplifying traffic.
- Merge only through the DEUS core-isolation branch review path.
