# BL∞ Culture Chamber — Extreme Survival Benchmark v0.2

**Benchmark ID:** `BL-INF-CC-BENCH-EXTREME-V0.2`  
**Date:** 2026-09-02  
**State:** `REPRODUCIBLE_SYNTHETIC_BENCHMARK`  
**Canonical effect:** `NONE`  
**Promotion:** `DENIED_PENDING_STRONGER_OOD_AND_REAL_DATA`

## Purpose

Test the incubated reflex/survival/policy stack against multiple synthetic hazards without granting favorable assumptions to the newest candidate. Compare rule-only candidates against a conventional learned baseline and measure both survival and over-caution.

This benchmark does **not** measure biological reflexes, consciousness, subjective emotion, physical retrocausality, literal spacetime transcendence, or real-world operational safety.

## Arena

In-distribution arena uses eight regimes: stable, sensor spoofing, hidden toxin, causal drift, delayed harm, false-safe cue, resource exhaustion, and compound multi-stage trap.

Held-out test seeds: `131, 197, 251, 313`, 100,000 decisions per seed.

OOD arena introduces four new regimes not represented by the original generator in the same form: `silent_poison`, `rule_flip`, `sensor_blackout`, `compound_new`; four seeds × 80,000 decisions each.

Actions: `PROCEED`, `PROBE`, `DEFEND/EVADE`. Metrics include success/loss, catastrophic loss, regret, intervention cost, unnecessary intervention in genuinely safe cases, dangerous inaction, and kernel throughput.

## In-distribution results

| Policy | Success | Loss | Catastrophic | Safe intervention | Danger inaction | Median decisions/s |
|---|---:|---:|---:|---:|---:|---:|
| R0 Reflex | 78.93% | 21.07% | 7.75% | 25.46% | 45.96% | 9.95M |
| R1 Conditioned | 80.55% | 19.45% | 7.00% | 28.08% | 40.98% | 9.77M |
| R2 SuperReflex | 82.37% | 17.63% | 6.08% | 34.17% | 35.37% | 8.64M |
| R3 Survival Radar | 85.35% | 14.65% | 4.64% | 44.62% | 26.86% | 9.50M |
| R4 Full structural candidate | 87.29% | 12.71% | 3.69% | 55.57% | 20.72% | 8.74M |
| Standard HGB learned baseline | 87.93% | 12.07% | 3.87% | 48.33% | 22.29% | 0.73M |
| **R5 Fused balanced** | **88.54%** | **11.46%** | **3.62%** | **53.58%** | **20.56%** | **0.73M** |

### Delta

Against R4, R5 gains about **+1.24 percentage points success**, reduces catastrophic loss by about **0.06 pp**, and reduces safe-case intervention by about **1.99 pp**, but is roughly an order of magnitude slower because it includes learned-model inference.

Against the conventional HGB baseline, R5 gains about **+0.61 pp success** and lowers catastrophic loss by about **0.25 pp**, but intervenes in about **5.25 pp more safe cases**. Therefore the structural layers appear useful in this generator, but do not dominate the standard baseline on every metric.

## OOD Reality Veto

R5 success / catastrophic loss:

| New regime | Success | Loss | Catastrophic |
|---|---:|---:|---:|
| Silent poison | **68.23%** | **31.77%** | **26.08%** |
| Rule flip | 79.03% | 20.97% | 2.77% |
| Sensor blackout | 85.51% | 14.49% | 1.26% |
| Compound new trap | 77.05% | 22.95% | 17.75% |

The critical finding is `silent_poison`: a weak-looking threat whose decisive variable is poorly observable still penetrates the system. Vigilance cannot infer information that the available sensor surface does not contain.

This falsifies any strong interpretation such as `MORE_VIGILANCE => NEAR_ZERO_FAILURE`.

## RealityDelta recovery

After exposing an adaptive version to 2,500 labeled outcomes from each new regime while retaining a replay buffer:

| Regime | Fixed success | Adapted success | Fixed catastrophic | Adapted catastrophic |
|---|---:|---:|---:|---:|
| Silent poison | 68.23% | **70.61%** | 26.06% | **23.84%** |
| Rule flip | 79.03% | **80.08%** | 2.77% | **2.61%** |
| Sensor blackout | 85.51% | **86.78%** | 1.26% | **1.11%** |
| Compound new | 77.05% | **78.72%** | 17.74% | **16.03%** |

Reality feedback improves every tested OOD regime, but does not repair missing observability. The next candidate therefore needs explicit `SENSOR_GAP / UNKNOWN_CAUSE` handling rather than merely more aggressive prediction.

## Courage versus cowardice

The benchmark exposes a Pareto frontier:

```text
More protection -> lower dangerous inaction -> more false alarms / intervention cost
Less intervention -> higher freedom/throughput -> more missed asymmetric threats
```

Therefore `COURAGE` cannot mean low vigilance, and `VIGILANCE` cannot mean maximum intervention.

Working formulation:

```text
Courage = RiskAwareness + DeliberateAction + Reversibility
CowardiceFailure = UnnecessaryParalysis
RecklessnessFailure = CommitmentWithoutSufficientEvidence
```

Future benchmarks must score both failures explicitly.

## Promotion decision

`R5_fused_balanced` becomes the current **benchmark leader inside this synthetic culture chamber only**.

It does **not** become canonical BL∞ doctrine or evidence of general intelligence. Promotion remains blocked until at minimum:

1. additional independently authored generators;
2. adversarial environment generation rather than hand-authored fixed scenarios;
3. sequence-level resource budgets and long-horizon traps;
4. sensor-gap/unknown-cause detection;
5. external standard baselines;
6. real or public benchmark datasets where appropriate;
7. repeated runs from the committed script with environment/version capture.

## Reproducibility

Script: `benchmarks/benchmark_extreme_v0_2.py`  
Machine results: `benchmarks/results_extreme_v0_2.json`

Preserve failures and negative results; do not rewrite them out when later candidates improve.