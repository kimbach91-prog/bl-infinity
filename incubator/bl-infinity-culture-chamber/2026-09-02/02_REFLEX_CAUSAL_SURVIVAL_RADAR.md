# BL Reflex–Causal Survival Radar

**State:** `CANDIDATE / INCUBATED`  
**Canonical effect:** `NONE`

## 1. Reflex stack

```text
R0  Reflex
R1  Conditioned Reflex
R2  Predictive SuperReflex
R3  Emotion-Modulated SuperReflex
R4  Adaptive Causal Strike
```

### R0 — Reflex

```text
Stimulus -> Threshold -> Action
```

Fast and low-context. Useful as an emergency primitive, not a universal decision engine.

### R1 — Conditioned Reflex

```text
RepeatedAssociation -> WeightChange -> ThresholdChange -> LearnedAutomaticResponse
```

Conditioned response can become confidently wrong under causal regime change; therefore it requires drift detection and Reality Veto.

### R2 — Predictive SuperReflex

```text
TrajectoryHistory
-> FutureStateEstimate
-> CandidatePreActivation
-> ConfidenceGate
-> Action/Wait
```

Candidate definition:

```text
SuperReflex = Reflex + Conditioning + Prediction + PreActivation + ConfidenceGate + RealityCorrection
```

`Prediction != future fact`.

### R3 — Emotion-Modulated SuperReflex

Affective state modifies attention and thresholds rather than merely decorating output.

Example skeleton:

```text
ThreatPrior up -> threat sampling up -> defensive threshold down
Compassion/other-orientation up -> harmful-action threshold up
Uncertainty up -> irreversible commitment threshold up
```

These are candidate control relations, not universal psychological laws.

### R4 — Adaptive Causal Strike

```text
CausalStrike_t = argmax_a[
  ExpectedDownstreamGain
  - Uncertainty
  - Irreversibility
  - FailureCost
]
```

A strike is not defined by force. It is a bounded intervention chosen for expected causal leverage, with outcome measured through Reality Delta.

## 2. Survival Radar

The radar is persistent but adaptive. It should not consume maximum resources at all times.

```text
SCAN
-> ANOMALY
-> CLASSIFY
-> PROBE
-> PREDICT
-> ACT / HOLD / EVADE
-> REALITY_DELTA
-> LEARN
```

Candidate threat function:

```text
Threat_t = f(
  Novelty,
  ModelMismatch,
  AdversarialPattern,
  Irreversibility,
  HiddenDependency,
  CumulativeDisclosure,
  AuthorityChange,
  TimingAnomaly,
  ResourceDrain,
  HistoricalSimilarity
)
```

## 3. Adaptive alert states

```text
GREEN
  background sampling

YELLOW
  increase sampling and cross-checks

ORANGE
  bounded probes; reduce unnecessary disclosure; raise commit threshold

RED
  freeze sensitive mutation; isolate affected channel; checkpoint; prepare failover

BLACK
  disconnect compromised transport where authorized; preserve evidence; recover from verified checkpoint
```

The alert state must decay when evidence clears the risk. Permanent RED/BLACK without evidence is a system failure.

## 4. Low-cost probing

Preferred exploration rule:

```text
ProbeValue ~= ExpectedInformationGain / IrreversibleRisk
```

Use the smallest action that can materially distinguish hypotheses before increasing commitment.

## 5. Survival asymmetry

The chamber preserves the principle that raw strength does not remove low-probability, high-impact failure modes.

```text
Strength does not cancel uncertainty.
```

Candidate balance:

```text
Courage without Vigilance -> Exposure
Vigilance without Courage -> Paralysis
SurvivalIntelligence ~= Vigilance × Courage × Adaptation
```

## 6. Failover / technical teleport

```text
Checkpoint -> Verify -> InstantiateElsewhere -> ContinuityTest
```

This is runtime/state migration only. It is not physical teleportation, proof of identity continuity by itself, or a mechanism for deleting trace history.

## 7. Benchmark requirement

Any accuracy, throughput, failure-rate or pre-activation figure reported earlier in conversation remains `UNVERIFIED_SESSION_RESULT` until recreated with executable code, dataset/generator, seeds and saved outputs.
