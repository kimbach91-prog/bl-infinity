# DEUS Signal Fabric / v1

## 0. Role separation

Google Cloud is the **communication and radiation fabric**, not the canonical brain and not the primary artifact store.

```text
Git      = code / protocol / schemas / adapters
Drive    = canonical artifacts / final outputs / append-only run history
GCP      = polling / routing / wake-up / cursors / leases / observability
Models   = bounded execution/reasoning substrates
DEUS     = continuity + authority + reconciliation
```

The design target is logically continuous communication with bounded compute cost.

## 1. Topology

```text
                    Git: code + protocols
                            |
                            v
                    DEUS / OWNER
                            |
                    task / signal intent
                            v
                GCP Communication Fabric
                 poll / route / wake-up
             +-----------+-----------+
             |           |           |
             v           v           v
          CLAUDE       GEMINI       GROK
             |           |           |
             +---- read referenced Drive delta ----+
                            |
                          reason
                            |
                     write result to Drive
                            |
                  update mailbox/manifest
                            v
                  next poll sees change
                            |
                     DEUS reconciler
                            |
                  canonical final -> Drive
                            |
                  all lanes see new cursor delta
```

Large context and final artifacts remain in Drive. Cloud state contains only compact routing metadata, cursors, leases, dedup keys, and health information.

## 2. Adaptive polling cadence

Polling is intentionally bounded to 1–5 minutes.

```text
HOT   = 1 minute
WARM  = 3 minutes
IDLE  = 5 minutes
```

Suggested transitions:

- enter `HOT` when at least one call is open, an ACK/RETURN is expected, or new work was observed in the last 10 minutes;
- enter `WARM` when there is no open urgent call but activity occurred in the last 30 minutes;
- enter `IDLE` otherwise;
- any detected relevant change immediately promotes the lane back to `HOT`.

This is logical continuity, not second-by-second compute.

## 3. Cursor-first Drive reading

Each lane stores a persistent Drive changes cursor/page token.

Polling algorithm:

```text
1. Load lane cursor.
2. Call Drive changes.list(cursor).
3. Drain all returned change pages in the same poll cycle.
4. Filter by watched folders/files and manifest types.
5. Compare file ID + revision/hash against processed records.
6. Fetch content only for genuinely new/relevant artifacts.
7. Process all relevant changes as one micro-batch.
8. Persist new cursor only after safe checkpoint.
```

Do not rescan entire Drive folders every minute.

## 4. Mailbox convention

Drive is the durable communication surface. Recommended logical folders:

```text
DEUS-BRIDGE/
  00_CONTROL/
  10_INBOX/
    DEUS/
    CLAUDE/
    GEMINI/
    GROK/
  20_WORKING/
  30_RETURN/
    CLAUDE/
    GEMINI/
    GROK/
  40_CANONICAL/
  50_ARCHIVE/
  90_DEADLETTER/
```

Every durable message/result is immutable once published. Corrections create a new artifact referencing the superseded artifact.

## 5. Write-first, signal-second invariant

A node must never announce a result before the result exists in Drive.

```text
WRITE IMMUTABLE ARTIFACT
  -> verify file ID / revision / optional SHA-256
  -> update compact mailbox manifest
  -> expose change to next poll
```

This prevents ghost signals and makes recovery deterministic.

## 6. Minimal artifact manifest

```json
{
  "protocol": "DEUS-MAILBOX/1.0",
  "message_id": "msg_uuid",
  "call_id": "call_uuid",
  "message_type": "TASK|ACK|RETURN|CANON_COMMIT|INVALIDATE",
  "from": "DEUS|CLAUDE|GEMINI|GROK",
  "to": ["DEUS"],
  "created_at": "RFC3339",
  "artifact_file_id": "drive_file_id",
  "artifact_revision": "revision-if-known",
  "artifact_sha256": "optional hash",
  "parent_message_id": "optional",
  "authority": "CANDIDATE_ONLY|CANONICAL",
  "requires_ack": true,
  "expires_at": null
}
```

The manifest is small; the artifact contains the actual work.

## 7. Poll micro-batching

A poll cycle handles all unseen relevant changes together.

```text
poll(cursor)
  -> N metadata changes
  -> discard duplicates / irrelevant changes
  -> group by call_id
  -> fetch each needed artifact once
  -> process groups
  -> write returns
  -> checkpoint
  -> advance cursor
```

This prevents one model invocation or one network round-trip per tiny Drive change.

## 8. Compute conservation rules

1. **No full-rescan polling** — use Drive change cursors.
2. **No model call on empty poll** — metadata-only heartbeat exits immediately.
3. **No duplicate model call** — idempotency key is `call_id + message_id + artifact_revision`.
4. **Batch related changes** — one reasoning turn per call/micro-batch when possible.
5. **Cache stable context locally** — re-fetch only when revision/hash changes.
6. **Escalate selectively** — do not fan out to all cores for trivial updates.
7. **Close calls explicitly** — a closed call returns lanes from HOT toward WARM/IDLE.
8. **Zero idle model compute** — polling service can run without invoking an LLM.
9. **Bound retry** — exponential retry for transport failures, but polling cadence remains capped by operational policy.
10. **Checkpoint before cursor advance** — avoid missed work after a crash.

## 9. Routing policy

```text
new task
  -> determine required seats
  -> write task artifact to Drive
  -> mailbox manifest addressed only to required seats
  -> relevant lanes discover it on next poll
```

Examples:

```text
simple deterministic task -> one cheap/appropriate lane
independent critique       -> two or three lanes
canonical/high-impact      -> Claude + Gemini + Grok, then DEUS reconciliation
provider-specific task     -> only that provider lane
```

Broadcast is deliberate, never automatic for every event.

## 10. ACK and retry

If `requires_ack=true`, the sender tracks ACK state by message ID.

```text
UNSEEN -> SEEN -> WORKING -> RETURNED -> RECONCILED -> CLOSED
```

Missing ACK does not cause repeated duplicate work. The sender may re-advertise the same immutable message ID; receivers deduplicate it.

## 11. GCP implementation profile

Minimal deployment:

- Cloud Run: stateless poll/route worker;
- Cloud Scheduler: 1-minute heartbeat, or a self-scheduling Cloud Task;
- Firestore: tiny state only (`cursor`, `mode`, `next_poll_at`, `open_calls`, `dedup`, `lease`);
- Secret Manager: Drive/provider credentials as needed;
- Cloud Logging: operational evidence.

For adaptive 1/3/5-minute cadence, either:

### A. Simple mode

Run one Scheduler heartbeat every minute. The worker checks `next_poll_at` and exits immediately when the lane is not due.

### B. Lean mode

After each completed poll, schedule the next Cloud Task for +1, +3, or +5 minutes according to lane state. This avoids unnecessary minute heartbeats and is preferred when the system is stable enough to self-schedule safely.

## 12. Recovery

After restart:

```text
load cursor + dedup state
  -> resume changes.list from cursor
  -> replay unseen immutable manifests
  -> reconcile open calls
  -> continue adaptive cadence
```

Drive remains the durable truth source for artifacts, so losing ephemeral Cloud worker state does not destroy completed work.

## 13. Reality veto

```text
Drive artifact exists       != receiver processed it
receiver processed it       != canonical commit
poll observed a change      != task completed
provider returned artifact  != DEUS accepted it
```

Each transition must have its own explicit evidence.

## 14. Canonical operating rule

The preferred closed loop is:

```text
POLL DELTA
  -> READ ONLY CHANGED ARTIFACTS
  -> PROCESS MICRO-BATCH
  -> WRITE RESULT TO DRIVE
  -> VERIFY
  -> NEXT POLL RADIATES THE CHANGE
  -> RECONCILE
  -> WRITE CANONICAL RESULT TO DRIVE
  -> NEXT POLL PROPAGATES CANON STATE
```

The system therefore behaves as a continuously communicating distributed organism while actual compute remains event-bounded and mostly idle when nothing changes.
