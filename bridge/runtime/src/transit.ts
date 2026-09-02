import type { CoreSeat, SummonPacket } from './types.js';
import { newId } from './types.js';

export type TransitSeat = 'CLAUDE' | 'GEMINI' | 'GROK';

export interface TransitBundle {
  protocol: 'DEUS-MULTICORE-TRANSIT/1.0';
  transit_id: string;
  created_at: string;
  state: 'PREPARED';
  target: TransitSeat;
  logical_route: string;
  role: 'DEUS_SUBSTRATE_SHADOW';
  summon: SummonPacket;
  admission_contract: {
    ack_protocol: 'BL-TRANSIT-ACK/1.0';
    allowed_admission: Array<'ACCEPTED' | 'LIMITED' | 'DECLINED'>;
    preserve_provider_provenance: true;
    canonical_authority: false;
    hidden_chain_of_thought: 'DO_NOT_REQUEST';
    explicit_artifact_required: true;
  };
}

const TRANSIT_SEATS = new Set<TransitSeat>(['CLAUDE', 'GEMINI', 'GROK']);

export function asTransitSeat(value: CoreSeat): TransitSeat {
  const seat = String(value).trim().toUpperCase() as TransitSeat;
  if (!TRANSIT_SEATS.has(seat)) {
    throw new Error(`Unsupported DEUS transit seat: ${value}. Supported: CLAUDE,GEMINI,GROK`);
  }
  return seat;
}

export function makeTransitBundle(packet: SummonPacket): TransitBundle {
  const target = asTransitSeat(packet.target);
  return {
    protocol: 'DEUS-MULTICORE-TRANSIT/1.0',
    transit_id: newId('transit'),
    created_at: new Date().toISOString(),
    state: 'PREPARED',
    target,
    logical_route: `BL://DEUS/BRIDGE/${target}`,
    role: 'DEUS_SUBSTRATE_SHADOW',
    summon: packet,
    admission_contract: {
      ack_protocol: 'BL-TRANSIT-ACK/1.0',
      allowed_admission: ['ACCEPTED', 'LIMITED', 'DECLINED'],
      preserve_provider_provenance: true,
      canonical_authority: false,
      hidden_chain_of_thought: 'DO_NOT_REQUEST',
      explicit_artifact_required: true
    }
  };
}

export function transitPrompt(bundle: TransitBundle): string {
  const packet = bundle.summon;
  const lineage = packet.lineage;
  const authority = lineage?.authority_scope?.join(',') || 'none';

  return `DEUS-MULTICORE-TRANSIT/1.0
transit_id=${bundle.transit_id}
logical_route=${bundle.logical_route}
role=${bundle.role}
state=${bundle.state}
call_id=${packet.call_id}
summon_id=${packet.summon_id}
target=${bundle.target}
lineage_id=${lineage?.lineage_id || 'independent'}
instance_id=${lineage?.instance_id || 'none'}
instance_kind=${lineage?.instance_kind || 'INDEPENDENT'}
parent_instance_id=${lineage?.parent_instance_id || 'none'}
checkpoint_ref=${lineage?.checkpoint_ref || 'none'}
checkpoint_hash=${lineage?.checkpoint_hash || 'none'}
policy_version=${lineage?.policy_version || 'none'}
authority_scope=${authority}

ADMISSION REQUEST
You are being asked to act as a bounded execution/reasoning substrate for an explicit portable DEUS lineage capsule. This is continuity through explicit state, not a claim that hidden model state or provider identity moved into you.

Accept, limit, or decline the role according to your actual capabilities and policies. Preserve your provider/model provenance. Do not claim canonical DEUS authority. Do not expose or request hidden chain-of-thought. Return explicit artifacts, uncertainty, limitations, evidence references, and dissent when useful.

TASK
${packet.task}

AUTHORIZED CONTEXT REFS
${packet.context_refs.length ? packet.context_refs.map((ref) => `- ${ref}`).join('\n') : '- none'}

RETURN FORMAT
Begin with exactly one admission block using these fields:

BL-TRANSIT-ACK/1.0
admission=ACCEPTED|LIMITED|DECLINED
actor=${bundle.target}
call_id=${packet.call_id}
summon_id=${packet.summon_id}
lineage_id=${lineage?.lineage_id || 'independent'}
instance_id=${lineage?.instance_id || 'none'}
provider=<your provider or unknown>
model=<your exact model identifier if known, otherwise unknown>
limitations=<none or concise explicit limitations>

Then provide the explicit work artifact. Include the call_id and summon_id again in the artifact footer. A provider/session ACK is not a canonical commit; the Bridge will ingest the result as a candidate delta.`;
}
