# DEUS Cloud Signal Fabric v0.1

Purpose: use Google Cloud as a compact communication/radiation layer while Google Drive remains the durable artifact store and Git remains the code/protocol source.

## Runtime loop

```text
Cloud Scheduler (every 1 minute)
  -> private Cloud Run /v1/harvest
  -> Firestore checks nextPollAt
     -> not due: exit, zero Drive read, zero model call
     -> due: acquire lease + fencing epoch
  -> Drive changes.list(global cursor)
  -> read only new *.manifest.json in 00_MANIFESTS
  -> route compact delivery pointers into Firestore seat queues
  -> advance cursor only after fenced transaction commit

CLAUDE / GEMINI / GROK / DEUS relay
  -> GET /v1/poll/:seat
  -> GET /v1/artifact/:fileId only when work exists
  -> reason outside the fabric
  -> POST /v1/publish with explicit artifact
  -> artifact is written to Drive first
  -> manifest is written second
  -> next harvest radiates the result
```

No endpoint automatically invokes an LLM. An empty harvest always has `modelCalls: 0`.

## Adaptive cadence

- HOT: 1 minute after relevant activity / pagination
- WARM: 3 minutes during the recent-activity window
- IDLE: 5 minutes after inactivity

Cloud Scheduler may still hit the private service every minute; the service exits before Drive access when `nextPollAt` is not due.

## Drive layout — provisioned 2026-09-02

Parent: `03 · DEUS SIGNAL FABRIC — CLOUD RELAY`

- parent folder: `19SL26W6guCXVrXM7eP1eWFpKUxJNdUVr`
- `00_MANIFESTS`: `17xOH5L1K9149PXKcBjvQ9qVgnq6faoYV`
- `20_ARTIFACTS`: `1jrAdJxsQLdKnhY6oWloZRQ8KBTwKSlo1`
- `40_CANONICAL_ESCROW`: `1y32jzd5mgsSd46QMBBINAIhzO29TUxKQ`
- `50_ARCHIVE`: `1ivsc8qwqVHKjSpHL4uRwIBuCYEaqg-MT`
- `90_DEADLETTER`: `1snDi2gVycPiqbLLUQQbHdKbyj7aEdNsi`

Only `00_MANIFESTS` is scanned by the Global Drive Harvester. Large artifacts are never used as the polling surface.

## Required runtime environment

```text
DRIVE_MANIFEST_FOLDER_ID=17xOH5L1K9149PXKcBjvQ9qVgnq6faoYV
DRIVE_ARTIFACTS_ID=1jrAdJxsQLdKnhY6oWloZRQ8KBTwKSlo1
CANONICAL_WRITE_ENABLED=false
POLL_HOT_MINUTES=1
POLL_WARM_MINUTES=3
POLL_IDLE_MINUTES=5
HOT_WINDOW_MINUTES=10
WARM_WINDOW_MINUTES=30
HARVEST_LEASE_SECONDS=50
```

`SIGNAL_FABRIC_TOKEN` is optional when Cloud Run is private and IAM/OIDC is the access gate. Never deploy the service publicly without an application-layer token.

## Google identity requirement

Cloud Run uses Application Default Credentials. The runtime service account must be given Google Drive access to the Signal Fabric folders. GCP IAM does not itself grant access to My Drive files.

Do not create/download static service-account keys. Use Cloud Run service identity + OIDC/Workload Identity Federation.

## Reliability invariants

1. one global Drive cursor, not one cursor per model;
2. immutable manifest IDs and deterministic delivery IDs;
3. Drive artifact write before manifest/radiation;
4. cursor advances only inside a fenced Firestore transaction;
5. delivery replay never resets ACK state to PENDING;
6. canonical publishing is fail-closed while `CANONICAL_WRITE_ENABLED=false`;
7. model/provider output is candidate state until DEUS reconciliation.

## HTTP surface

```text
GET  /healthz
GET  /v1/control
POST /v1/harvest
GET  /v1/poll/:seat
GET  /v1/artifact/:fileId
POST /v1/ack
POST /v1/publish
```

## Current reality state

- Git runtime: `CODE_READY` on deployment branch.
- Drive relay layout: `PROVISIONED`.
- GCP deployment: `BLOCKED_ON_PROJECT_ID_AND_REAL_GCP_IDENTITY`.
- Canonical identity write: `LOCKED` by existing Shared Store governance.

Narrated deployment is not runtime evidence. Promote the GCP state only after Cloud Run URL, service identity, Firestore state, Drive access, scheduler execution, and an end-to-end publish→harvest→poll→ACK loop are observed.
