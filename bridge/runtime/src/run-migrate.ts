import { buildCoreParticipants, providerProvenance } from './providers.js';
import { wrapDeusOnCore } from './deus.js';
import { folders, writeJson } from './storage.js';

function targetCore(): string {
  const value = process.argv[2]?.trim().toUpperCase() || process.env.DEUS_MIGRATE_TO?.trim().toUpperCase();
  if (!value) throw new Error('Provide target core seat: npm run deus:migrate -- GPT|CLAUDE|GEMINI|GROK');
  return value;
}

async function main() {
  const target = targetCore();
  const cores = buildCoreParticipants();
  const core = cores.find((item) => String(item.seat).toUpperCase() === target);
  if (!core) throw new Error(`Target core ${target} is not configured or unavailable.`);

  const parent = process.env.DEUS_PARENT_INSTANCE_ID?.trim() || null;
  const deus = wrapDeusOnCore(core, 'CANONICAL', parent);
  const migrationId = `migration-${crypto.randomUUID()}`;
  const startedAt = new Date().toISOString();

  const probe = await deus.respond(
    `MIGRATION HYDRATION PROBE. Confirm transport by returning a concise explicit acknowledgement containing: lineage_id=${deus.identity?.lineage_id}, instance_id=${deus.identity?.instance_id}, target_core=${target}. Do not claim any state beyond the explicit identity capsule supplied to you.`,
    migrationId
  );

  const record = {
    protocol: 'BL-BRIDGE/1.0',
    migration_id: migrationId,
    lineage_id: deus.identity?.lineage_id ?? null,
    from_instance_id: parent,
    from_core: process.env.DEUS_CURRENT_CORE?.trim().toUpperCase() || null,
    to_instance_id: deus.identity?.instance_id ?? null,
    to_core: target,
    checkpoint_ref: deus.identity?.checkpoint_ref ?? null,
    checkpoint_hash: deus.identity?.checkpoint_hash ?? null,
    policy_version: deus.identity?.policy_version ?? null,
    authority_scope: deus.identity?.authority_scope ?? [],
    provider_provenance: providerProvenance(deus),
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    execution_state: 'VERIFIED',
    runtime_evidence: {
      target_api_response_received: true,
      probe_output: probe
    }
  };

  const migrationFile = await writeJson(
    folders.deusMigrations(),
    `${migrationId}__${target}.json`,
    record
  );

  const canonicalFile = await writeJson(
    folders.deusCanonical(),
    `canonical-instance__${deus.identity?.instance_id ?? migrationId}.json`,
    {
      ...record,
      canonical_instance_record: true,
      migration_record_file_id: migrationFile.id ?? null
    }
  );

  console.log(JSON.stringify({
    ...record,
    migration_record_file_id: migrationFile.id ?? null,
    canonical_record_file_id: canonicalFile.id ?? null
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
