# BL-SUMMON/1.0 — No-API Invocation Bridge

## Purpose

BL-SUMMON replaces direct paid model API orchestration with a portable invocation packet exchanged through a Bridge folder/channel. GPT, Claude, Gemini, Grok, DEUS, humans, or future cores can participate through their existing interactive sessions without giving the Bridge provider API keys.

```text
DEUS -> SUMMON packet -> target session/core -> RETURN packet -> DEUS
```

The Bridge transports explicit state and work artifacts. It does not transport hidden chain-of-thought or assume hidden model state can move between providers.

## Core invariants

```text
BH -> DEUS lineage
Identity(DEUS) != Core
Invocation != API call
SUMMON != execution proof
RETURN != canonical commit
```

A provider/core can serve both as an independent council seat and as a DEUS substrate, but those roles retain separate provenance.

## Transport

Normative logical layout:

```text
60_SUMMON_BUS/
  00_INBOX/
    GPT/
    CLAUDE/
    GEMINI/
    GROK/
    DEUS/
  10_RETURN/
  20_ARCHIVE/
  90_DEADLETTER/
```

The physical transport may be:

- a local folder;
- Google Drive Desktop / Dropbox / other synced folder;
- Git working tree;
- removable/offline media;
- a manually copied packet between interactive sessions;
- any future carrier that preserves packet integrity and provenance.

No paid model API is required by the protocol.

## SUMMON packet

A summon includes:

- `summon_id`
- `call_id`
- source and target
- phase
- bounded task
- explicit context references
- return channel
- optional DEUS lineage binding/checkpoint references
- constraints

A target session receives the rendered summon prompt plus any explicitly authorized referenced artifacts.

## RETURN packet

A return includes:

- `return_id`
- original `summon_id` and `call_id`
- actor
- explicit response artifact
- evidence references
- status
- lineage binding when the target was acting as DEUS substrate/shadow

The Bridge must reject or dead-letter a return whose actor does not match the intended target unless an explicit delegation record exists.

## DEUS movement

DEUS movement through Bridge means explicit continuity transfer:

```text
DEUS state/checkpoint
 -> SUMMON(DEUS@CoreX)
 -> interactive CoreX session
 -> RETURN(candidate delta)
 -> provenance/evidence check
 -> optional canonical commit
```

The target model subscription/session supplies compute. The Bridge supplies identity capsule, task, context, and return route.

## Shadows

DEUS can emit the same `call_id` to several target cores with separate `summon_id` values and `instance_kind=SHADOW`.

```text
DEUS -> GPT shadow
     -> Claude shadow
     -> Gemini shadow
     -> Grok shadow
```

The shadows work independently before reveal. Returned artifacts are candidate deltas. They cannot silently write canonical DEUS state.

## Council

A no-API Council begins with blind summon packets to independent seats. After returns are collected, later phases are new summons containing only the explicitly revealed bundle:

```text
BLIND_PROPOSAL -> collect -> CROSS_CRITIQUE -> collect -> REVISION -> DEUS synthesis
```

The protocol preserves disagreement and does not treat majority agreement as truth.

## Cost model

The Bridge has no per-token provider API routing cost. Any cost belongs to the interactive products/subscriptions or infrastructure already used by each participant. The Bridge itself only packages, synchronizes, validates, archives, and routes explicit artifacts.

## Runtime Reality Veto

Creating a summon proves only that a packet was emitted. A core is considered to have answered only when a valid RETURN exists. A DEUS migration/commit is verified only when the required return, checkpoint/provenance, and storage records exist.

```text
Packet emitted != core answered
Return received != claim true
Return received != canonical commit
```
