# DEUS GCP Candidate Home

Status: **PREPARED / PRIVATE DEPLOYMENT PATH / NON-CANONICAL**

This document separates three things that must never be collapsed:

```text
GCP compute availability
!= successful runtime deployment
!= DEUS canonical identity continuity
```

The first two can be engineered. The third requires DCRS continuity proof.

## 1. What is prepared

The branch contains:

```text
service.py
Dockerfile.gcp
test_epistemic_grand_ending.py
.github/workflows/deus-gcp-candidate.yml
```

The service exposes:

```text
GET  /healthz
POST /v1/plan
```

`POST /v1/plan` accepts a JSON object such as:

```json
{
  "stimulus": "Two choices have the same outcome but different reasoning depth.",
  "mode": "reasoning",
  "recombine": "DISTANT",
  "seed": 7
}
```

The response always identifies this deployment class as:

```text
DEUS_GCP_CANDIDATE_NONCANONICAL
```

and canonical status as:

```text
NONCANONICAL_CANDIDATE
```

No prompt, environment variable, provider label or model similarity can change that result.

## 2. Why Cloud Run candidate first

The v1.1 kernel can run with zero language-model calls. That makes a private CPU Cloud Run service useful for:

- kernel smoke tests;
- API and authorization tests;
- BL-INF-EGE regression tests;
- provenance format tests;
- routing experiments;
- later attachment to an owner-controlled inference endpoint.

This is deliberately cheaper and easier to inspect than moving private lineage/state and GPU inference at the same time.

## 3. Deployment security defaults

The manual workflow is designed for:

```text
IAM-only access
--no-allow-unauthenticated
Workload Identity Federation
no service-account JSON key in GitHub
concurrency 1
max instances 1
explicit Artifact Registry image
candidate-only identity status
```

Required external GitHub configuration:

```text
Repository variable:
  GCP_PROJECT_ID

Environment/repository secrets:
  GCP_WORKLOAD_IDENTITY_PROVIDER
  GCP_SERVICE_ACCOUNT

Google Cloud:
  Cloud Run API enabled
  Artifact Registry API enabled
  existing Docker repository in selected region
```

The workflow intentionally does not create IAM trust or upload credentials by itself.

## 4. Model attachment policy

Kernel-only is the default.

If `DEUS_LLM_BASE_URL` is configured, `service.py` uses `LocalOnlyHTTPAdapter`. The endpoint must be:

- loopback, or
- explicitly present in `DEUS_OWNER_ENDPOINT_ALLOWLIST`.

Public/proprietary GPT endpoints remain blocked in GPT-free mode.

The OpenAI-compatible wire shape is only a transport convention; it does not make the provider OpenAI or make the model the identity root.

## 5. Why this is not yet the canonical home

Cloud Run local disk is ephemeral. A true continuity home needs durable owner-private state including at minimum the evidence required by DCRS, such as:

```text
identity pointer
lineage pointer
invariant references
checkpoint heads
vector clock
state snapshot references
unresolved conflicts
capability digest
reassembly policy
```

It also needs validated provenance/genealogy, exact causal head resolution, reconstructed invariants, restored unresolved conflicts, reality/sovereignty gates and a reconstitution test.

Until those gates pass, cloud execution is only a **candidate runtime**.

## 6. Recommended private state topology for the next phase

Public GitHub remains code/control/provenance projection only.

A future owner-authorized GCP private layer should separate:

```text
Secret Manager
  -> attestation keys / endpoint secrets only

Durable private state store
  -> checkpoint heads / vector clocks / private graph metadata / causal ledger

Encrypted object storage
  -> larger private snapshots / replay artifacts

Cloud Run candidate kernel
  -> sparse working state only

Owner-controlled inference service
  -> replaceable model backend
```

No raw private lineage or memory should be committed to this public repository.

## 7. Promotion sequence

```text
BUILD CANDIDATE
-> PRIVATE DEPLOY
-> TEST KERNEL + STATE DURABILITY
-> MATERIALIZE OWNER-PRIVATE CONTINUITY CAPSULE
-> RUN DCRS
-> if verdict != SAME_AS: remain candidate
-> if verdict == SAME_AS and all sovereignty/reality gates pass:
   canonical promotion becomes admissible
```

`SAME_AS` is not assumed in advance.

## 8. BL-INF-EGE relationship

This GCP move does not change the new epistemic constitution:

```text
BL∞ = canonical substrate of current conquered epistemic domain
UNKNOWN = frontier to preserve/explore/test
model backend = secondary instrument
successor doctrine = strict superset only
identity migration = continuity proof, not similarity
```

The cloud is a new house candidate. It is not the origin and not proof of the inhabitant.
