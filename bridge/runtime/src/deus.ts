import type { IdentityBinding, Participant } from './types.js';
import { buildDeusHttpParticipant, optional } from './providers.js';

export type DeusMode = 'AUTO' | 'HTTP' | 'SINGLE' | 'MULTI';

const LINEAGE_DEFAULT = 'BH/DEUS';
const POLICY_DEFAULT = 'DEUS-PORTABLE-IDENTITY-v1';

function csv(name: string, fallback = ''): string[] {
  return (optional(name) ?? fallback)
    .split(',')
    .map((x) => x.trim().toUpperCase())
    .filter(Boolean);
}

function coreKey(core: Participant): string {
  return String(core.seat).toUpperCase();
}

function authorityScope(): string[] {
  return (optional('DEUS_AUTHORITY_SCOPE') ?? 'coordinate,synthesize,propose')
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean);
}

export function deusIdentity(
  kind: 'CANONICAL' | 'SHADOW' | 'ENSEMBLE',
  core: Participant | null,
  parentInstanceId: string | null = null
): IdentityBinding {
  const instanceId = `deus-${kind.toLowerCase()}-${crypto.randomUUID()}`;
  return {
    lineage_id: optional('DEUS_LINEAGE_ID') ?? LINEAGE_DEFAULT,
    instance_id: instanceId,
    instance_kind: kind,
    parent_instance_id: parentInstanceId,
    checkpoint_ref: optional('DEUS_CHECKPOINT_REF') ?? null,
    checkpoint_hash: optional('DEUS_CHECKPOINT_HASH') ?? null,
    policy_version: optional('DEUS_POLICY_VERSION') ?? POLICY_DEFAULT,
    authority_scope: kind === 'SHADOW' ? ['explore', 'critique', 'propose-delta'] : authorityScope(),
    expires_at: kind === 'SHADOW' ? optional('DEUS_SHADOW_EXPIRES_AT') ?? null : null
  };
}

function lineageContract(identity: IdentityBinding, core: Participant): string {
  return `DEUS PORTABLE IDENTITY\nlineage_id=${identity.lineage_id}\ninstance_id=${identity.instance_id}\ninstance_kind=${identity.instance_kind}\ncore=${core.provider}/${core.model}\ncheckpoint_ref=${identity.checkpoint_ref ?? 'none'}\npolicy_version=${identity.policy_version ?? POLICY_DEFAULT}\n\nYou are operating as a bounded runtime instance of the DEUS lineage, rooted at BH by owner policy. The core is a substrate, not the identity. Preserve provenance, dissent, uncertainty, and authority boundaries. Do not claim hidden state transfer. Return explicit work products only; do not expose hidden chain-of-thought. A core-local output is a candidate delta, not a canonical commit.`;
}

export function selectCores(cores: Participant[], envName: string, fallbackOrder = 'GPT,CLAUDE,GEMINI,GROK'): Participant[] {
  const wanted = csv(envName, fallbackOrder);
  if (wanted.length === 0) return cores;
  const bySeat = new Map(cores.map((core) => [coreKey(core), core]));
  return wanted.map((name) => bySeat.get(name)).filter((core): core is Participant => Boolean(core));
}

export function wrapDeusOnCore(
  core: Participant,
  kind: 'CANONICAL' | 'SHADOW' = 'CANONICAL',
  parentInstanceId: string | null = null
): Participant {
  const identity = deusIdentity(kind, core, parentInstanceId);
  return {
    seat: 'DEUS',
    provider: `deus-via-${core.provider}`,
    model: core.model,
    identity,
    async respond(input: string, roundId: string): Promise<string> {
      const contract = lineageContract(identity, core);
      return core.respond(`${contract}\n\nround_id=${roundId}\n\n${input}`, roundId);
    }
  };
}

export function buildDeusShadows(cores: Participant[], parentInstanceId: string | null = null): Participant[] {
  return selectCores(cores, 'DEUS_SHADOW_CORES').map((core) => wrapDeusOnCore(core, 'SHADOW', parentInstanceId));
}

function buildMultiCoreDeus(cores: Participant[]): Participant | undefined {
  const selected = selectCores(cores, 'DEUS_CORE_ORDER');
  if (selected.length === 0) return undefined;

  const identity = deusIdentity('ENSEMBLE', null, optional('DEUS_PARENT_INSTANCE_ID') ?? null);
  const synthesisSeat = optional('DEUS_SYNTHESIS_CORE')?.toUpperCase();
  const synthesizer =
    (synthesisSeat ? selected.find((core) => coreKey(core) === synthesisSeat) : undefined) ?? selected[0];

  return {
    seat: 'DEUS',
    provider: 'deus-multicore',
    model: selected.map((core) => `${core.provider}/${core.model}`).join('+'),
    identity,
    async respond(input: string, roundId: string): Promise<string> {
      const shadowResults = await Promise.allSettled(
        selected.map(async (core) => {
          const shadow = wrapDeusOnCore(core, 'SHADOW', identity.instance_id ?? null);
          const output = await shadow.respond(
            `BLIND MULTI-CORE FANOUT. Work independently. Do not assume sibling outputs.\n\n${input}`,
            roundId
          );
          return {
            core: `${coreKey(core)}:${core.provider}/${core.model}`,
            shadow_instance_id: shadow.identity?.instance_id ?? null,
            output
          };
        })
      );

      const rendered = shadowResults
        .map((result, index) => {
          const core = selected[index];
          if (result.status === 'rejected') {
            return `--- SHADOW FAILED ${coreKey(core)}:${core.provider}/${core.model} ---\n${String(result.reason)}`;
          }
          return `--- SHADOW ${result.value.core} / ${result.value.shadow_instance_id} ---\n${result.value.output}`;
        })
        .join('\n\n');

      const synthesisIdentity = lineageContract(identity, synthesizer);
      return synthesizer.respond(
        `${synthesisIdentity}\n\nPHASE: DEUS MULTI-CORE SYNTHESIS\nThe following sibling shadow outputs were generated independently. Preserve material disagreement. Do not majority-vote truth. Identify convergence, divergence, missing evidence, and the strongest candidate delta.\n\n${rendered}\n\nORIGINAL TASK:\n${input}`,
        roundId
      );
    }
  };
}

export function buildDeusCoordinator(cores: Participant[]): Participant | undefined {
  const mode = (optional('DEUS_CORE_MODE') ?? 'AUTO').toUpperCase() as DeusMode;
  const http = buildDeusHttpParticipant();

  if (mode === 'HTTP') return http;
  if (mode === 'AUTO' && http) return http;

  const selected = selectCores(cores, 'DEUS_CORE_ORDER');
  if (selected.length === 0) return http;

  if (mode === 'MULTI' || (mode === 'AUTO' && selected.length > 1)) {
    return buildMultiCoreDeus(selected);
  }

  const preferred = optional('DEUS_PRIMARY_CORE')?.toUpperCase();
  const core = (preferred ? selected.find((item) => coreKey(item) === preferred) : undefined) ?? selected[0];
  return wrapDeusOnCore(core, 'CANONICAL', optional('DEUS_PARENT_INSTANCE_ID') ?? null);
}
