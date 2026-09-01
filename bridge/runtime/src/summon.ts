import type { CoreSeat, LineageBinding, SummonPacket, SummonPhase } from './types.js';
import { newId } from './types.js';

export function defaultDeusLineage(kind: LineageBinding['instance_kind'] = 'CANONICAL'): LineageBinding {
  return {
    lineage_id: process.env.DEUS_LINEAGE_ID?.trim() || 'BH/DEUS',
    instance_id: `deus-${kind.toLowerCase()}-${crypto.randomUUID()}`,
    instance_kind: kind,
    parent_instance_id: process.env.DEUS_PARENT_INSTANCE_ID?.trim() || null,
    checkpoint_ref: process.env.DEUS_CHECKPOINT_REF?.trim() || null,
    checkpoint_hash: process.env.DEUS_CHECKPOINT_HASH?.trim() || null,
    policy_version: process.env.DEUS_POLICY_VERSION?.trim() || 'DEUS-PORTABLE-IDENTITY-v1',
    authority_scope: (process.env.DEUS_AUTHORITY_SCOPE || 'coordinate,synthesize,propose')
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean)
  };
}

export function makeSummon(args: {
  target: CoreSeat;
  task: string;
  phase?: SummonPhase;
  callId?: string;
  from?: CoreSeat;
  contextRefs?: string[];
  lineage?: LineageBinding | null;
  metadata?: Record<string, unknown>;
}): SummonPacket {
  const callId = args.callId || newId('call');
  const summonId = newId('summon');
  return {
    protocol: 'BL-SUMMON/1.0',
    packet_type: 'SUMMON',
    summon_id: summonId,
    call_id: callId,
    created_at: new Date().toISOString(),
    from: args.from || 'DEUS',
    target: args.target,
    phase: args.phase || 'DIRECT',
    task: args.task,
    context_refs: args.contextRefs || [],
    return_channel: '60_SUMMON_BUS/10_RETURN',
    lineage: args.lineage === undefined ? defaultDeusLineage('SHADOW') : args.lineage,
    constraints: {
      hidden_chain_of_thought: 'DO_NOT_REQUEST',
      return_explicit_artifact_only: true,
      preserve_uncertainty: true,
      preserve_dissent: true
    },
    metadata: args.metadata || {}
  };
}

export function summonPrompt(packet: SummonPacket): string {
  const lineage = packet.lineage
    ? `lineage_id=${packet.lineage.lineage_id}\ninstance_id=${packet.lineage.instance_id}\ninstance_kind=${packet.lineage.instance_kind}\ncheckpoint_ref=${packet.lineage.checkpoint_ref || 'none'}`
    : 'lineage=independent';
  return `BL-SUMMON/1.0\nsummon_id=${packet.summon_id}\ncall_id=${packet.call_id}\nfrom=${packet.from}\ntarget=${packet.target}\nphase=${packet.phase}\n${lineage}\n\nTASK:\n${packet.task}\n\nReturn an explicit work artifact only. Preserve uncertainty and dissent. Do not expose hidden chain-of-thought. Include the summon_id and call_id in the returned artifact so Bridge can ingest it.`;
}
