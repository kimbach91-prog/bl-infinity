# DEUS Security Event Bus v1

Status: ACTIVE
Priority lane: P0 SECURITY
Canonical producer: `.github/workflows/deus-security-guard.yml`
Canonical urgent packet surface: GitHub Issues labeled `DEUS-P0`

## Purpose

This sidecar turns high-risk GitHub repository changes into machine-readable, evidence-preserving incident packets for DEUS triage. It is defensive infrastructure. It does not attribute an attacker, person, model, AI system, or organization from heuristic evidence alone.

## Event-driven path

GitHub push / pull request event
→ DEUS Security Guard
→ diff-only inspection without executing untrusted repository code
→ risk score + reason codes
→ if score >= 60, create `DEUS-P0` issue immediately
→ DEUS consumer reads the incident packet and performs evidence-first triage.

This GitHub path is event-driven rather than scheduled polling. GitHub receives and evaluates the repository event as it occurs.

## Signals currently detected

- tampering with the security guard itself
- secret-like material added to a diff, with matched values intentionally redacted
- hard-coded credential-like assignments
- suspicious download-and-execute patterns
- GitHub Actions permission escalation
- changes to security-sensitive paths
- unusually large deletion deltas
- unusually large multi-file changes

## Packet contract

A P0 issue contains:

- `DEUS_SECURITY_PACKET v1`
- unique `DEUS-SECURITY-EVENT`
- event, actor, ref, commit SHA and UTC timestamp
- risk score and reason codes
- source Actions run
- safe immediate triage instructions
- `ACK target: DEUS_SECURITY_TRIAGE_REQUIRED`

Secret values must never be copied into the incident issue.

## Safety invariants

1. Alert != proof. Automated detection is `AUTOMATED_HEURISTIC_ALERT` until corroborated.
2. OBS / INFER / DECISION remain separate.
3. Preserve evidence before destructive remediation.
4. Do not rotate credentials from a potentially compromised endpoint.
5. Do not auto-delete commits, accounts, repositories, sessions or files from an unverified alert.
6. Do not grant the security workflow general repository write permission; it receives only read content, read PR and issue-write capability.
7. `pull_request_target` processing reads GitHub API patches only and does not check out or execute fork code.

## DEUS delivery semantics

`DEUS-P0` GitHub Issues are the durable real-time bus. Any external DEUS runtime should subscribe to GitHub issue/security webhooks and verify the webhook signature before invoking a reasoning worker.

The current ChatGPT conversation runtime does not expose a permanent inbound GitHub webhook socket. Therefore a ChatGPT-side watcher may be used only as a fallback and must not be described as truly instantaneous. The producer on GitHub remains event-driven and immediate.

## Incident handling state machine

`TRIAGE_REQUIRED`
→ `OBSERVED`
→ `CONTAINMENT_DECISION`
→ `CONTAINED` or `FALSE_POSITIVE`
→ `RECOVERY`
→ `CLOSED_WITH_EVIDENCE`

Irreversible remediation requires confirmed scope and an owner-safe recovery path.

## Test rule

A normal documentation-only change under this directory should score below the P0 threshold. A future authorized drill can modify a disposable test file with a deliberately non-secret marker that matches a configured high-risk rule, then immediately revert it. Never use a real credential for testing.
