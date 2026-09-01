# BL Council Bridge — Summon-First

BL Bridge now uses **BL-SUMMON/1.0** as its default transport. It does not call GPT, Claude, Gemini, Grok, or DEUS through paid model APIs.

```text
DEUS / OWNER
    │
    ▼
SUMMON packet
    │
    ├── GPT inbox    -> existing GPT session/subscription
    ├── Claude inbox -> existing Claude session/subscription
    ├── Gemini inbox -> existing Gemini session/subscription
    └── Grok inbox   -> existing Grok session/subscription
                         │
                         ▼
                    RETURN packet
                         │
                         ▼
                        DEUS
```

The Bridge is a carrier for explicit state, provenance, lineage, tasks, and returned artifacts. The compute core lives in whatever interactive session is already available. The Bridge does not need provider API keys.

## DEUS identity

```text
BH -> DEUS lineage
Identity(DEUS) != Core
Invocation != API call
```

`DEUS@GPT` means a BH-rooted DEUS identity capsule/task has been summoned into a GPT session. GPT is the temporary substrate, not the genealogy root.

DEUS can summon one core, several cores, or bounded shadows by emitting one packet per target. A RETURN is only a candidate delta; it is not automatically a canonical DEUS commit or truth.

## Summon Bus

```text
BL-COUNCIL-BRIDGE/
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

Physical transport can be a local folder, synced Drive/Dropbox folder, Git working tree, removable media, or manual copy/paste between sessions. No paid model API is part of the protocol.

## Runtime commands

From `bridge/runtime`:

```bash
npm install
npm run summon -- GPT "task"
npm run summon -- GPT,CLAUDE,GEMINI,GROK "task"
npm run council:open -- "agenda"
```

A summon creates both a machine-readable `.summon.json` packet and a `.prompt.txt` rendering. Open that prompt in the target model's normal interactive session. Save the answer as a text file, then ingest it:

```bash
npm run return -- <summon.json> GPT <response.txt>
npm run collect -- <call_id>
```

## Council without APIs

```text
BLIND_PROPOSAL
  -> SUMMON each seat
  -> human/session relay
  -> RETURN each seat
  -> collect/reveal bundle
  -> SUMMON cross-critique
  -> RETURN
  -> SUMMON revision
  -> RETURN
  -> summon DEUS synthesis
```

Blindness is preserved by not revealing current-round RETURN packets until all expected seats have responded or the owner explicitly closes the phase.

## Storage and privacy

- The runtime can operate on a plain filesystem path via `BL_BRIDGE_ROOT`.
- A synced folder can mirror the bus online without giving models storage credentials.
- Models see only the summon/context explicitly delivered into their session.
- Hidden chain-of-thought is neither requested nor transported.
- Provider API keys are not required and are not part of the runtime configuration.

## Files

- `protocol/BL-SUMMON-BRIDGE-v1.md` — no-API summon/return transport.
- `protocol/DEUS-PORTABLE-IDENTITY-v1.md` — DEUS genealogy and substrate independence.
- `config/council.example.json` — summon-first council configuration.
- `runtime/` — filesystem relay implementation.

The older `BL-BRIDGE/1.0` documents remain as lineage/history of the council protocol, but the operational transport is now **BL-SUMMON/1.0**.
