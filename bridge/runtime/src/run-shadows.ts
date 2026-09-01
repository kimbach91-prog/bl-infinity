import { buildCoreParticipants, providerProvenance } from './providers.js';
import { buildDeusShadows } from './deus.js';
import { makeEnvelope, newId } from './types.js';
import { publishPrivate } from './storage.js';

function task(): string {
  const fromArgs = process.argv.slice(2).join(' ').trim();
  const fromEnv = process.env.DEUS_TASK?.trim();
  const value = fromArgs || fromEnv;
  if (!value) throw new Error('Provide a shadow task as CLI arguments or DEUS_TASK.');
  return value;
}

async function main() {
  const input = task();
  const cores = buildCoreParticipants();
  if (cores.length === 0) throw new Error('No provider cores configured.');

  const parentInstanceId = process.env.DEUS_PARENT_INSTANCE_ID?.trim() || null;
  const shadows = buildDeusShadows(cores, parentInstanceId);
  if (shadows.length === 0) throw new Error('No DEUS shadow cores selected. Check DEUS_SHADOW_CORES and provider credentials.');

  const roundId = `shadow_${new Date().toISOString().replace(/[:.]/g, '-')}_${newId('r').slice(-8)}`;
  const results = await Promise.allSettled(
    shadows.map(async (shadow) => {
      const output = await shadow.respond(
        `DEUS SHADOW TASK. Explore independently. You may attack assumptions, create counterfactuals, or propose novel candidate deltas, but you do not have canonical commit authority.\n\n${input}`,
        roundId
      );
      const envelope = makeEnvelope({
        roundId,
        actor: 'DEUS',
        type: 'PROPOSAL',
        visibility: 'PRIVATE',
        content: output,
        identity: shadow.identity ?? null,
        provenance: providerProvenance(shadow),
        metadata: {
          task: input,
          shadow_core: `${shadow.provider}/${shadow.model}`
        }
      });
      const stored = await publishPrivate(envelope);
      return {
        instance_id: shadow.identity?.instance_id ?? null,
        lineage_id: shadow.identity?.lineage_id ?? null,
        core: `${shadow.provider}/${shadow.model}`,
        drive_file_id: stored.id ?? null,
        output
      };
    })
  );

  const summary = results.map((result, index) => {
    if (result.status === 'fulfilled') return result.value;
    return {
      instance_id: shadows[index].identity?.instance_id ?? null,
      core: `${shadows[index].provider}/${shadows[index].model}`,
      error: String(result.reason)
    };
  });

  console.log(JSON.stringify({ round_id: roundId, shadows: summary }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
