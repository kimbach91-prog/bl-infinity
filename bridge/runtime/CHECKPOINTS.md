# DEUS Explicit Checkpoints

Portable DEUS continuity uses explicit, authorized state. Hidden provider chain-of-thought is neither requested nor treated as portable identity state.

## Create a checkpoint

Prepare a JSON file containing the explicit state that may travel with the DEUS lineage, then run:

```bash
npm run deus:checkpoint -- ./deus-state.json
```

The command writes a checkpoint under the BH-rooted DEUS checkpoint vault and returns:

```text
checkpoint_ref=drive:<fileId>
checkpoint_hash=sha256:<hash>
```

Set those values as `DEUS_CHECKPOINT_REF` and `DEUS_CHECKPOINT_HASH` in the runtime secret/config layer.

## Hydration

When a DEUS instance is created on GPT, Claude, Gemini, Grok, or a future core, `drive:<fileId>` checkpoints are read by the broker and supplied as explicit portable state together with lineage/provenance metadata.

The runtime refuses silent checkpoint truncation. `DEUS_CHECKPOINT_MAX_CHARS` is a hard upper bound; oversize state fails and must be deliberately restructured or referenced differently.

## Migration

```bash
npm run deus:migrate -- GPT
npm run deus:migrate -- CLAUDE
npm run deus:migrate -- GEMINI
npm run deus:migrate -- GROK
```

Migration is committed only after the target core answers the hydration probe. The broker then records the migration transaction and the new canonical instance record.

```text
checkpoint -> hydrate target core -> probe -> migration ledger -> canonical instance record
```

This is continuity transfer of explicit state, not a claim that hidden model state or weights moved between providers.
