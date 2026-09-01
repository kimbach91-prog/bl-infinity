export type CoreSeat = 'GPT' | 'CLAUDE' | 'GEMINI' | 'GROK' | 'DEUS' | 'OWNER' | (string & {});

export type SummonPhase =
  | 'DIRECT'
  | 'BLIND_PROPOSAL'
  | 'CROSS_CRITIQUE'
  | 'REVISION'
  | 'SYNTHESIS'
  | 'EXPERIMENT'
  | 'CUSTOM';

export interface LineageBinding {
  lineage_id: string;
  instance_id: string;
  instance_kind: 'CANONICAL' | 'SHADOW' | 'ENSEMBLE' | 'INDEPENDENT';
  parent_instance_id?: string | null;
  checkpoint_ref?: string | null;
  checkpoint_hash?: string | null;
  policy_version?: string | null;
  authority_scope?: string[];
}

export interface SummonPacket {
  protocol: 'BL-SUMMON/1.0';
  packet_type: 'SUMMON';
  summon_id: string;
  call_id: string;
  created_at: string;
  from: CoreSeat;
  target: CoreSeat;
  phase: SummonPhase;
  task: string;
  context_refs: string[];
  return_channel: string;
  lineage?: LineageBinding | null;
  constraints: {
    hidden_chain_of_thought: 'DO_NOT_REQUEST';
    return_explicit_artifact_only: true;
    preserve_uncertainty: true;
    preserve_dissent: true;
  };
  metadata?: Record<string, unknown>;
}

export interface ReturnPacket {
  protocol: 'BL-SUMMON/1.0';
  packet_type: 'RETURN';
  return_id: string;
  summon_id: string;
  call_id: string;
  created_at: string;
  actor: CoreSeat;
  content: string;
  evidence_refs: string[];
  parent_refs: string[];
  lineage?: LineageBinding | null;
  status: 'COMPLETE' | 'PARTIAL' | 'DECLINED' | 'FAILED';
  metadata?: Record<string, unknown>;
}

export function newId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID()}`;
}
