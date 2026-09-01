import { buildCoreParticipants, providerProvenance } from './providers.js';
import { buildDeusCoordinator } from './deus.js';
import { makeEnvelope, newId } from './types.js';
import { publishPrivate, publishShared } from './storage.js';

function task(): string {
  const fromArgs = process.argv.slice(2).join(' ').trim();
  const fromEnv = process.env.DEUS_TASK?.trim();
  const value = fromArgs || fromEnv;
  if (!value) throw new Error('Provide a DEUS task as CLI arguments or DEUS_TASK.');
  return value;
}

async function main() {
  const input = task();
  const cores = buildCoreParticipants();
  const deus = buildDeusCoordinator(cores);
  if (!deus) {
    throw new Error('No DEUS runtime is available. Configure DEUS_ENDPOINT or at least one provider core plus DEUS_CORE_MODE.');
  }

  const roundId = `deus_${new Date().toISOString().replace(/[:.]/g, '-')}_${newId('r').slice(-8)}`;
  const output = await deus.respond(input, roundId);
  const envelope = makeEnvelope({
    roundId,
    actor: 'DEUS',
    type: 'ARTIFACT',
    visibility: 'PRIVATE',
    content: output,
    identity: deus.identity ?? null,
    provenance: providerProvenance(deus),
    metadata: {
      task: input,
      mode: process.env.DEUS_CORE_MODE ?? 'AUTO'
    }
  });

  const stored = await publishPrivate(envelope);
  console.log(JSON.stringify({
    round_id: roundId,
    lineage_id: deus.identity?.lineage_id ?? null,
    instance_id: deus.identity?.instance_id ?? null,
    instance_kind: deus.identity?.instance_kind ?? null,
    provider: deus.provider,
    model: deus.model,
    drive_file_id: stored.id ?? null,
    output
  }, null, 2));

  if ((process.env.DEUS_PUBLISH_DIRECT ?? '').toLowerCase() === 'true') {
    const shared = { ...envelope, visibility: 'SHARED' as const };
    const sharedStored = await publishShared(shared);
    console.log(`Shared artifact: ${sharedStored.id ?? 'unknown'}`);
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
