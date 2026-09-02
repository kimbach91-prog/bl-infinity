# Install DEUS Signal Fabric on Google Cloud

This guide installs the DEUS communication/radiation fabric. It does **not** train or deploy a DEUS-native foundation model. Google Drive remains the durable artifact store; Git remains the source/protocol store; Google Cloud provides routing, polling, state, leases and scheduling.

## Active project binding

```text
project_id     = deus-code-sss
project_number = 618160905661
region         = asia-southeast1
repo           = kimbach91-prog/bl-infinity
branch         = deus/signal-fabric-gcp-v1
```

This binding was switched by owner instruction on 2026-09-02. The previous `buoyant-mason-114302` binding is retained only as historical provenance/fallback and is no longer the DEUS installation target.

## Step 1 — open Google Cloud Shell

Open Cloud Shell while the Google Cloud Console is on project `deus-code-sss`. The installer also runs `gcloud config set project deus-code-sss`, so it does not rely on the browser selector alone.

## Step 2 — run the one-line installer

```bash
curl -fsSL 'https://raw.githubusercontent.com/kimbach91-prog/bl-infinity/deus/signal-fabric-gcp-v1/bridge/cloud-signal-fabric/scripts/bootstrap-gcp-cloudshell.sh' | bash
```

The installer is idempotent and creates no static service-account key. It:

1. verifies project identity and state;
2. enables IAM, STS, Cloud Run, Cloud Build, Artifact Registry, Firestore, Cloud Scheduler and Drive APIs;
3. creates dedicated runtime, scheduler and GitHub deploy service accounts;
4. creates Firestore `(default)` when absent;
5. creates GitHub OIDC Workload Identity Federation restricted to `kimbach91-prog/bl-infinity`;
6. grants the documented Cloud Run Builder role to the Cloud Build/compute service identity when available;
7. deploys the private `deus-signal-fabric` Cloud Run service;
8. creates the one-minute Cloud Scheduler heartbeat;
9. prints the Cloud Run URL and runtime service-account email.

Expected runtime identity:

```text
deus-signal-fabric@deus-code-sss.iam.gserviceaccount.com
```

Expected WIF provider:

```text
projects/618160905661/locations/global/workloadIdentityPools/deus-github/providers/bl-infinity
```

Expected GitHub deploy identity:

```text
deus-github-deploy@deus-code-sss.iam.gserviceaccount.com
```

These WIF identifiers are identifiers, not secrets; future GitHub deploys do not need a service-account JSON key.

## Step 3 — grant the runtime access to the DEUS Drive relay

Open:

```text
https://drive.google.com/drive/folders/19SL26W6guCXVrXM7eP1eWFpKUxJNdUVr
```

Share the parent folder **03 · DEUS SIGNAL FABRIC — CLOUD RELAY** with:

```text
deus-signal-fabric@deus-code-sss.iam.gserviceaccount.com
```

Permission: **Editor**.

Parent-folder permissions normally propagate to child items. If a child folder uses Google Drive limited-access mode, grant the runtime identity directly on that child as well.

## Step 4 — verify the installation end-to-end

In Cloud Shell:

```bash
git clone --depth=1 --branch deus/signal-fabric-gcp-v1 https://github.com/kimbach91-prog/bl-infinity.git
cd bl-infinity
PROJECT_ID=deus-code-sss REGION=asia-southeast1 \
  bash bridge/cloud-signal-fabric/scripts/verify-install.sh
```

The verifier performs an explicit non-canonical smoke test:

```text
health
 -> global cursor bootstrap/advance
 -> write test artifact to Drive
 -> write manifest
 -> forced authenticated harvest
 -> Firestore delivery pointer for GEMINI
 -> seat poll
 -> ACK=SEEN
```

The verifier must end with:

```text
DEUS SIGNAL FABRIC — E2E VERIFIED
```

No LLM is invoked by this smoke test. Canonical write remains locked.

## Step 5 — future deploys from GitHub

After bootstrap, GitHub Actions can authenticate through WIF. Run the workflow:

```text
DEUS Signal Fabric - GCP
```

Project default:

```text
deus-code-sss
```

No GCP JSON key and no WIF secret values are required.

## Runtime cadence

```text
Scheduler heartbeat = 1 minute
HOT                 = 1 minute
WARM                = 3 minutes
IDLE                = 5 minutes
```

The one-minute Scheduler call does not imply a Drive scan or model call every minute. Cloud Run first checks `nextPollAt`; if not due, it exits. When due, one Global Drive Harvester consumes Drive `changes.list` from one persistent cursor and routes compact pointers only to addressed seats.

## Reality-state gate

Do not mark the system `RUNNING_VERIFIED` until all of these exist as observed evidence:

```text
Cloud Run revision healthy
Firestore control document created
Scheduler authenticated invocation succeeds
Drive runtime ACL succeeds
publish -> manifest -> harvest -> seat poll -> ACK succeeds
fencingEpoch is present
modelCalls == 0 for empty/transport-only cycles
```

A successful source build alone is `CODE_VERIFIED`, not runtime verification.
