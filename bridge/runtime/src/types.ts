export type Seat = 'GPT' | 'CLAUDE' | 'GEMINI' | 'DEUS' | 'OWNER';

export type MessageType =
  | 'AGENDA'
  | 'PROPOSAL'
  | 'EVIDENCE'
  | 'CRITIQUE'
  | 'REVISION'
  | 'SYNTHESIS'
  | 'DISSENT'
  | 'DECISION'
  | 'BENCHMARK'
  | 'ARTIFACT'
  | 'HEARTBEAT';

export type Visibility = 'PRIVATE' | 'SHARED' | 'PUBLIC';

export type ExecutionState =
  | 'NOT_APPLICABLE'
  | 'PROPOSED'
  | 'DECLARED'
  | 'VERIFIED'
  | 'FAILED'
  | 'UNKNOWN';

export interface Provenance {
  provider: string;
  model?: string | null;
  adapter_version?: string | null;
  runtime_id?: string | null;
  source_refs?: string[];
}

export interface Envelope {
  protocol: 'BL-BRIDGE/1.0';
  message_id: string;
  round_id: string;
  actor: Seat;
  type: MessageType;
  visibility: Visibility;
  created_at: string;
  parent_ids?: string[];
  supersedes?: string[];
  claim_ids?: string[];
  content: string;
  concise_rationale?: string | null;
  confidence?: number | null;
  evidence_refs?: string[];
  falsifiers?: string[];
  requested_response?: string | null;
  execution_state?: ExecutionState;
  runtime_evidence?: string[];
  provenance: Provenance;
  metadata?: Record<string, unknown>;
}

export interface Participant {
  seat: Seat;
  provider: string;
  model: string;
  respond(input: string, roundId: string): Promise<string>;
}

export function newId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID()}`;
}

export function makeEnvelope(args: {
  roundId: string;
  actor: Seat;
  type: MessageType;
  visibility: Visibility;
  content: string;
  provenance: Provenance;
  parentIds?: string[];
  supersedes?: string[];
  metadata?: Record<string, unknown>;
}): Envelope {
  return {
    protocol: 'BL-BRIDGE/1.0',
    message_id: newId(args.type.toLowerCase()),
    round_id: args.roundId,
    actor: args.actor,
    type: args.type,
    visibility: args.visibility,
    created_at: new Date().toISOString(),
    parent_ids: args.parentIds ?? [],
    supersedes: args.supersedes ?? [],
    claim_ids: [],
    content: args.content,
    concise_rationale: null,
    confidence: null,
    evidence_refs: [],
    falsifiers: [],
    requested_response: null,
    execution_state: 'NOT_APPLICABLE',
    runtime_evidence: [],
    provenance: args.provenance,
    metadata: args.metadata ?? {}
  };
}
