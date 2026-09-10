# DEUS Energy-Compute Governor v0.1

Status: candidate / internal-only / no third-party control.

Purpose: score owner-controlled compute jobs against carbon intensity, energy price, deadline pressure, runtime availability, and risk. The governor only emits recommendations until an authority binding explicitly permits execution.

Safe lanes:
- carbon-aware time shifting of deferrable owner-controlled workloads;
- carbon-aware region selection where a provider already grants access;
- simulation of OpenADR/OpenLEADR demand-response events;
- telemetry/risk scoring and settlement-quality receipts.

Forbidden by default:
- controlling third-party energy assets without explicit authority;
- market enrollment or accepting terms for another party;
- spending money without an explicit budget approval;
- arbitrary shell/code payloads from external inputs;
- treating Drive storage, aliases, labels, or planned nodes as compute.

Decision rule: recommendation is eligible only when authority=true, runtime_verified=true, deadline feasibility is satisfied, and risk_score <= configured threshold. External energy control remains recommendation-only unless an asset-specific authority receipt exists.
