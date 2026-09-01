# BL-SUMMON Bridge Runtime

This runtime routes **invocation packets**, not paid model API requests.

## Setup

```bash
npm install
cp .env.example .env
```

Set `BL_BRIDGE_ROOT` to a local folder or a folder synced by Google Drive Desktop/Dropbox/etc. No OpenAI, Anthropic, Gemini, xAI, or Google service-account API key is required.

The runtime creates/uses:

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

## Direct summon

```bash
npm run summon -- GPT "Analyze this problem"
npm run summon -- GPT,CLAUDE,GEMINI,GROK "Analyze independently"
```

Each target receives a `.summon.json` and a `.prompt.txt`. Open the prompt in that provider's normal interactive chat/session. The session itself supplies compute under the subscription/account already in use.

## Return

Save the explicit answer from the target session to a text file and ingest it:

```bash
npm run return -- <path/to/summon.json> GPT <path/to/response.txt>
```

The Bridge validates that the returning actor matches the summon target, then writes a provenance-bearing RETURN packet to `10_RETURN`.

## Collect

```bash
npm run collect -- <call_id>
```

This creates one return bundle in `20_ARCHIVE` for reveal/synthesis.

## Open a Council blind round

```bash
npm run council:open -- "bounded agenda"
```

By default the runtime emits independent blind summons to GPT, Claude, Gemini, and Grok. Do not reveal current-round answers to sibling seats until the phase is closed if you want anchoring resistance.

## DEUS over Bridge

A DEUS summon carries the BH-rooted lineage capsule inside the packet:

```text
BH -> DEUS lineage -> summon -> core session -> return candidate delta
```

The core is not the identity. A return is not a canonical commit. The same mechanism can create shadows by sending the same call to several cores with separate summon IDs.

## Transport options

BL-SUMMON only requires that packets can move between the Bridge and the interactive sessions. Useful carriers include:

- local/synced folders;
- Git;
- manual copy/paste;
- future browser/session relays;
- offline/removable media.

The protocol intentionally does not require provider SDKs or per-token API billing.
