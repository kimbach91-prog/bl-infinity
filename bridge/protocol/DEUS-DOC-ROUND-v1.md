# DEUS DOC-ROUND / v1

## Purpose

`DEUS-DOC-ROUND/1.0` is the preferred low-cost communication path for DEUS multi-core work.

- **Google Docs** carries explicit final artifacts and canonical synthesis.
- **Google Cloud / Firestore** carries only compact signals, pointers, ACK state, leases and fencing metadata.
- **Provider/model sessions** do their reasoning internally and publish only explicit final artifacts.
- **Git** remains source/protocol/configuration history.

The old Drive manifest/artifact path remains a compatibility and recovery path; DOC-ROUND becomes the preferred normal path.

## Core invariant

```text
THINK INTERNALLY
  -> WRITE EXPLICIT FINAL TO DOC
  -> VERIFY WRITE
  -> CLOUD SIGNALS POINTER ONLY
  -> RECEIVER READS DOC
  -> OPTIONAL SELECTIVE REVIEW
  -> DEUS SYNTHESIS WRITTEN TO DOC
  -> FINAL_READY SIGNAL
```

Cloud must not transport full model answers in normal operation.

## Normal-round topology

```text
CLAUDE ---\
GEMINI ----> bounded independent work
GROK -----/
             |
             v
       DOC BATCH WRITE
             |
             v
        ROUND_READY
       cloud pointer
             |
             v
            DEUS
        reads Doc once
             |
             v
      synthesis/verifier
             |
             v
       DOC FINAL WRITE
             |
             v
        FINAL_READY
       cloud pointer
```

Participants do **not** read one another by default.

## Selective cross-reading

Cross-reading is triggered only by an explicit signal:

```text
REVIEW_REQUIRED
```

Valid causes include:

- meaningful contradiction;
- missing evidence;
- explicit critique request;
- high-impact/canonical decision requiring independent review;
- verifier uncertainty above policy threshold.

No default full-mesh discussion is allowed.

## Durable round block

The Doc representation is append-only plain text:

```text
[ROUND <round_id> | TENANT <tenant_id> | TASK <task_id> | SIGNAL <signal_type> | STATE <state>]
[ACTOR CLAUDE]
<explicit final artifact>
[/ACTOR]
[ACTOR GEMINI]
<explicit final artifact>
[/ACTOR]
[ACTOR GROK]
<explicit final artifact>
[/ACTOR]
[END ROUND <round_id>]
```

A later DEUS synthesis is another append-only block using the same `round_id` and `SIGNAL FINAL_READY`.

Corrections use another block and reference the superseded state in metadata. Existing history is not silently rewritten.

## Minimal signal envelope

```json
{
  "protocol": "DEUS-DOC-ROUND/1.0",
  "round_id": "round_uuid",
  "tenant_id": "tenant_id",
  "task_id": "task_id",
  "signal_type": "ROUND_READY|REVIEW_REQUIRED|FINAL_READY|ROUND_CLOSED",
  "from": "DEUS|CLAUDE|GEMINI|GROK",
  "to": ["DEUS"],
  "document_id": "google_doc_id",
  "marker": "[ROUND round_uuid",
  "doc_revision_id": "optional",
  "state": "CANDIDATE|REVIEW|FINAL|CLOSED",
  "created_at": "RFC3339"
}
```

The envelope contains no answer body.

## Low-request rules

1. Prefer **one `documents.batchUpdate`** for all participant finals available to a collector.
2. Prefer **one DEUS read** after `ROUND_READY`.
3. Prefer **one DEUS write** for synthesis.
4. Use `endOfSegmentLocation` append writes so a pre-write document read is unnecessary.
5. Cloud emits compact pointers only.
6. ACK/cursor/fencing state stays in Firestore, never in Docs.
7. Empty Cloud polling invokes zero model compute.
8. Rotate rolling Docs at roughly **100–300 rounds**, or earlier if read latency becomes material.
9. Do not use tables, comments, smart chips, decorative formatting or per-message Docs files for the machine path.
10. Provider count must not multiply shared infrastructure polling.

## Cost target per normal round

Preferred normal path:

```text
Docs writes: 2
  - participant batch
  - DEUS synthesis

Docs reads: ~1
  - DEUS synthesis read

Cloud signals: 2
  - ROUND_READY
  - FINAL_READY
```

Additional reads/writes occur only when `REVIEW_REQUIRED` is triggered.

## Tenant isolation

Production SaaS should use customer-owned or tenant-scoped Drive/Docs where possible.

```text
DEUS platform owns:
  protocol / router / signal plane / verifier / UI / tenant metadata

Tenant owns:
  business documents / model accounts or model billing / durable business data
```

Do not put multiple unrelated enterprises into one shared blackboard document.

## Authority

A model response in the Doc is not canonical merely because it exists.

```text
DOC_WRITE != CANONICAL
ROUND_READY != ACCEPTED
FINAL_READY != CANONICAL_COMMIT unless DEUS authority policy permits it
```

Existing Authority / Runtime / Evidence separation remains in force.
