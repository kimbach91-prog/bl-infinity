import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { folders, writeJson } from './storage.js';

function sourcePath(): string {
  const value = process.argv[2]?.trim() || process.env.DEUS_CHECKPOINT_INPUT_FILE?.trim();
  if (!value) throw new Error('Provide an explicit state JSON file: npm run deus:checkpoint -- ./deus-state.json');
  return value;
}

async function main() {
  const path = sourcePath();
  const raw = await readFile(path, 'utf8');
  const explicitState = JSON.parse(raw) as unknown;
  const hash = createHash('sha256').update(raw).digest('hex');
  const checkpointId = `checkpoint-${Date.now()}-${hash.slice(0, 12)}`;
  const createdAt = new Date().toISOString();

  const checkpoint = {
    protocol: 'BL-BRIDGE/1.0',
    checkpoint_id: checkpointId,
    lineage_id: process.env.DEUS_LINEAGE_ID?.trim() || 'BH/DEUS',
    policy_version: process.env.DEUS_POLICY_VERSION?.trim() || 'DEUS-PORTABLE-IDENTITY-v1',
    parent_checkpoint_ref: process.env.DEUS_CHECKPOINT_REF?.trim() || null,
    state_hash_sha256: hash,
    created_at: createdAt,
    state_kind: 'EXPLICIT_PORTABLE_STATE',
    warning: 'Checkpoint state must contain authorized explicit state only; hidden model chain-of-thought is not portable identity state.',
    explicit_state: explicitState
  };

  const stored = await writeJson(
    folders.deusCheckpoints(),
    `${checkpointId}.json`,
    checkpoint
  );

  if (!stored.id) throw new Error('Drive checkpoint write returned no file ID.');

  console.log(JSON.stringify({
    checkpoint_id: checkpointId,
    checkpoint_ref: `drive:${stored.id}`,
    checkpoint_hash: `sha256:${hash}`,
    drive_file_id: stored.id,
    created_at: createdAt
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
