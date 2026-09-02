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
                 Google Drive artifacts
                            |
                  GLOBAL DRIVE HARVESTER
                    one change cursor
                            |
                GCP Communication Fabric
                  route / dedup / wake-up
             +-----------+-----------+
             |           |           |
             v           v           v
          CLAUDE       GEMINI       GROK
             |           |           |
             +---- read referenced Drive artifact ----+
                            |
                          reason
                            |
                     write result to Drive
                            |
                  next harvest sees change
                            v
                     DEUS reconciler
                            |
                  canonical final -> Drive
```

Large context and final artifacts remain in Drive. Cloud state contains only compact routing metadata, the global Drive cursor, per-seat delivery/ACK state, leases, dedup keys, and health information.

## 2. Adaptive polling cadence

The **Global Drive Harvester** polls Drive on a bounded 1–5 minute cadence:

```text
HOT   = 1 minute
WARM  = 3 minutes
IDLE  = 5 minutes
```

Suggested transitions:

- `HOT`: at least one open call, missing ACK/RETURN, non-empty dispatch backlog, or new work in the last 10 minutes;
- `WARM`: no urgent open call but activity occurred in the last 30 minutes;
- `IDLE`: no open work and no recent activity;
- any relevant Drive change immediately promotes the fabric back to `HOT`.

This is logical continuity, not second-by-second compute.

## 3. One Drive scan, many recipients

Do **not** let Claude, Gemini, Grok, and DEUS independently scan the same Drive change feed.

Use one persistent Drive `changes` cursor for the watched Drive scope:

```text
GLOBAL HARVESTER
  -> Drive changes.list(global_cursor)
  -> drain all change pages
  -> filter relevant bridge artifacts/manifests
  -> deduplicate by file_id + revision/hash
  -> parse audience
  -> fan out compact delivery records
       -> CLAUDE queue
       -> GEMINI queue
       -> GROK queue
       -> DEUS queue
  -> checkpoint harvest batch
  -> advance global_cursor
```

This converts N-provider Drive polling into **one Drive delta read per polling cycle**.

Per-seat state tracks only delivery/processing position, not a second Drive scan cursor.

## 4. Durable Drive mailbox convention

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

Every durable message/result is immutable once published. A correction creates a new artifact referencing the superseded artifact.

## 5. Write-first, radiation-second invariant

```text
WRITE IMMUTABLE ARTIFACT TO DRIVE
  -> verify file ID / revision / optional SHA-256
  -> write/update compact manifest
  -> next Global Harvester cycle observes the change
  -> GCP routes pointer to intended recipients
```

Never announce `RESULT_READY` before the referenced Drive artifact actually exists.

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

## 7. Harvest micro-batching

One harvest cycle consumes all unseen changes since the prior cursor:

```text
poll(global_cursor)
  -> N Drive metadata changes
  -> discard duplicates / irrelevant changes
  -> group manifests by call_id and audience
  -> route compact pointers
  -> wake only seats that have work
  -> checkpoint harvest batch
  -> advance global_cursor
```

A provider then fetches only the referenced artifact(s) it actually needs.

## 8. Provider-side work loop

```text
receive compact delivery
  -> validate message_id/call_id/audience
  -> dedup against processed revision
  -> fetch referenced Drive artifact only if new
  -> process bounded micro-batch
  -> write explicit output to Drive
  -> verify write
  -> write RETURN manifest
  -> ACK delivery
  -> sleep
```

An empty poll/harvest must never invoke a model.

## 9. Compute conservation rules

1. **One global Drive change scan** per cycle, not one scan per model.
2. **No full-rescan polling** — use Drive change cursors/page tokens.
3. **No LLM call on empty harvest** — metadata-only cycle exits.
4. **Wake only addressed seats** — no default all-core broadcast.
5. **No duplicate model call** — idempotency key `call_id + message_id + artifact_revision`.
6. **Batch related changes** by `call_id` before reasoning.
7. **Cache stable context** and re-fetch only on revision/hash change.
8. **Close calls explicitly** so cadence falls from HOT toward WARM/IDLE.
9. **Zero idle model compute** — Cloud transport can stay alive while model compute is zero.
10. **Checkpoint before cursor advance** so crashes cannot silently skip work.
11. **Bound retries** and preserve the same immutable message ID on re-advertisement.
12. **Escalate selectively** — use multiple cores only when the task justifies it.

## 10. Routing policy

```text
new task
  -> choose required seats
  -> write task artifact to Drive
  -> write manifest with explicit audience
  -> Global Harvester sees it
  -> Cloud router fans pointer only to required seats
```

Examples:

```text
simple deterministic task -> one suitable lane
independent critique       -> two lanes
canonical/high-impact      -> Claude + Gemini + Grok -> DEUS reconciliation
provider-specific task     -> only that provider lane
```

## 11. ACK state machine

```text
UNSEEN -> DELIVERED -> SEEN -> WORKING -> RETURNED -> RECONCILED -> CLOSED
```

Missing ACK may trigger re-advertisement of the same message ID, never creation of duplicate logical work.

## 12. GCP implementation profile

Minimal deployment:

- **Cloud Run**: stateless Global Drive Harvester + router;
- **Cloud Scheduler** or **Cloud Tasks**: adaptive 1/3/5-minute wake-up;
- **Firestore**: tiny ephemeral control state only (`global_cursor`, `mode`, `next_poll_at`, `open_calls`, `deliveries`, `dedup`, `lease`);
- **Secret Manager**: Drive/provider credentials as needed;
- **Cloud Logging**: runtime evidence and fault diagnosis.

### Simple deployment

Cloud Scheduler calls the Harvester every minute. If `next_poll_at` has not arrived, the Cloud Run handler exits immediately without reading Drive or invoking any model.

### Lean deployment

After each harvest, a Cloud Task schedules exactly one next wake-up at +1, +3, or +5 minutes. This minimizes unnecessary heartbeat invocations.

## 13. Resource arithmetic

Worst-case one-minute global polling is approximately:

```text
60 * 24 * 30 = 43,200 harvester wake-ups/month
```

That is independent of whether there are 3, 4, or more provider seats, because Drive is scanned once and the result is routed internally.

The architecture therefore scales provider count much more cheaply than per-seat Drive polling.

## 14. Recovery

```text
load global_cursor + dedup/delivery state
  -> resume Drive changes.list(global_cursor)
  -> replay unacked compact deliveries
  -> reconcile open calls
  -> continue adaptive cadence
```

Drive remains the durable truth source for artifacts, so loss of ephemeral Cloud worker state does not destroy completed work.

## 15. Reality veto

```text
Drive artifact exists       != receiver processed it
receiver processed it       != canonical commit
harvest observed a change   != task completed
provider returned artifact  != DEUS accepted it
```

Each state transition needs explicit evidence.

## 16. Canonical operating loop

```text
GLOBAL POLL DELTA
  -> ROUTE POINTERS
  -> WAKE ONLY NEEDED SEATS
  -> READ ONLY CHANGED ARTIFACTS
  -> PROCESS MICRO-BATCH
  -> WRITE RESULT TO DRIVE
  -> VERIFY
  -> NEXT GLOBAL POLL RADIATES RESULT
  -> DEUS RECONCILES
  -> WRITE CANONICAL RESULT TO DRIVE
  -> NEXT GLOBAL POLL PROPAGATES CANON STATE
```

The system behaves as a continuously communicating distributed organism while actual model compute remains event-bounded and mostly zero when nothing changes.
