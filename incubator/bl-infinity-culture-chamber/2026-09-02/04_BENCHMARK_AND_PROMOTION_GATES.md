# Benchmark & Promotion Gates — 2026-09-02 Culture Chamber

**State:** `INCUBATED / TEST_REQUIRED`

## 1. Evidence correction

All numerical benchmark values previously stated in the conversational session are preserved only as narrative/session claims unless independently reproduced.

```text
CHAT_REPORTED_NUMBER -> UNVERIFIED_SESSION_RESULT
```

No accuracy, throughput, win rate, adaptation rate or loss rate from chat is canonical evidence without a reproducible artifact.

## 2. Required benchmark families

### A. Reflex benchmark

Compare:

```text
R0 Reflex
R1 Conditioned Reflex
R2 Predictive SuperReflex
R3 Emotion-Modulated SuperReflex
R4 Adaptive Causal Strike
```

Metrics:

- accuracy/F1 where classification applies;
- decision latency;
- compute per decision;
- calibration;
- false-positive/false-negative cost;
- adaptation time after regime change;
- catastrophic-loss rate;
- regret;
- abstention/hold quality.

### B. Causal disorder arena

Stressors:

- sensor noise;
- hidden confounding;
- delayed observation;
- causal graph drift;
- adversarial false-safe cues;
- partial observability;
- resource exhaustion;
- deceptive correlation;
- sudden role/rule change.

Goal: determine where predictive/reflex complexity improves survival and where it creates confident error.

### C. Rule-CoEvolution arena

Evaluate whether:

```text
PLAY -> DECONSTRUCT -> REGRESS -> ALIGN
```

improves valid outcomes versus:

- immediate commitment;
- rule-text-only reasoning;
- brute-force option search;
- naive negotiation;
- over-cautious abstention.

Metrics:

- valid-path discovery rate;
- number of clarification rounds;
- time/cost to agreement;
- compliance failure rate;
- unnecessary disclosure;
- reversibility preserved;
- counterparty utility when measurable.

### D. Trap and Survival Radar arena

Scenarios:

- low-probability/high-impact threat;
- multi-stage trap;
- poisoned memory/context;
- authorization spoof;
- cumulative reconstruction attempt;
- adversary with greater compute and adaptive policy;
- benign novelty to test false alarms.

Measure both missed threats and paranoia cost.

### E. Execution Twin fidelity benchmark

The twin may predict an owner's likely execution preference only from authorized traces. Compare prediction against later explicit correction/choice.

Metrics:

- decision-match rate;
- calibration;
- correction speed;
- context sensitivity;
- overfitting to old behavior;
- false identity/assertion rate.

Behavioral similarity is not identity proof.

## 3. Reproducibility bundle

Every quantitative promotion candidate requires:

```text
/code
/data-or-generator
/seeds
/config
/metrics-definition
/results
/failures
/runtime-notes
```

Outputs must preserve failures, not only winning runs.

## 4. Promotion decision classes

```text
PROMOTE
PROMOTE_NARROWED
KEEP_INCUBATING
SPLIT_OBJECT
QUARANTINE
REJECT
SUPERSEDE_WITH_LESSON_PRESERVED
```

## 5. Minimum promotion rule

A component is not promoted because it is elegant, complex, owner-aligned or emotionally compelling. It must show a measurable or logically demonstrated delta over a relevant baseline while preserving provenance, reversibility and Reality Veto.
