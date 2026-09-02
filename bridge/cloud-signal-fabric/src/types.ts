import type { Seat } from './config.js';

export type MessageType = 'TASK' | 'ACK' | 'RETURN' | 'CANON_COMMIT' | 'INVALIDATE';
export type Authority = 'CANDIDATE_ONLY' | 'CANONICAL';
export type DeliveryState = 'PENDING' | 'SEEN' | 'WORKING' | 'RETURNED' | 'FAILED' | 'CLOSED';

export interface MailboxManifest {
  protocol: 'DEUS-MAILBOX/1.0';
  message_id: string;
  call_id: string;
  message_type: MessageType;
  from: Seat;
  to: Seat[];
  created_at: string;
  artifact_file_id: string;
  artifact_revision?: string | null;
  artifact_sha256?: string | null;
  parent_message_id?: string | null;
  authority: Authority;
  requires_ack: boolean;
  expires_at?: string | null;
  metadata?: Record<string, unknown>;
}

export interface DeliveryRecord {
  deliveryId: string;
  seat: Seat;
  manifest: MailboxManifest;
  sourceManifestFileId: string;
  sourceManifestVersion?: string | null;
  status: DeliveryState;
  createdAt: string;
  updatedAt: string;
  fencingEpoch: number;
}

export interface PublishRequest {
  from: Seat;
  to: Seat[];
  call_id: string;
  message_type: MessageType;
  artifact_text: string;
  artifact_name?: string;
  artifact_mime_type?: string;
  parent_message_id?: string | null;
  authority?: Authority;
  requires_ack?: boolean;
  metadata?: Record<string, unknown>;
}

export type DocRoundSignalType = 'ROUND_READY' | 'REVIEW_REQUIRED' | 'FINAL_READY' | 'ROUND_CLOSED';
export type DocRoundState = 'CANDIDATE' | 'REVIEW' | 'FINAL' | 'CLOSED';

export interface DocRoundContribution {
  actor: Seat;
  final_text: string;
  metadata?: Record<string, unknown>;
}

export interface DocRoundBatchRequest {
  round_id: string;
  tenant_id: string;
  task_id: string;
  from: Seat;
  to: Seat[];
  signal_type: DocRoundSignalType;
  state: DocRoundState;
  document_id?: string;
  contributions: DocRoundContribution[];
  metadata?: Record<string, unknown>;
}

export interface DocRoundSignalRequest {
  round_id: string;
  tenant_id: string;
  task_id: string;
  from: Seat;
  to: Seat[];
  signal_type: DocRoundSignalType;
  state: DocRoundState;
  document_id?: string;
  marker?: string;
  doc_revision_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface DocRoundSignalRecord {
  protocol: 'DEUS-DOC-ROUND/1.0';
  deliveryId: string;
  seat: Seat;
  roundId: string;
  tenantId: string;
  taskId: string;
  signalType: DocRoundSignalType;
  from: Seat;
  documentId: string;
  marker: string;
  docRevisionId?: string | null;
  state: DocRoundState;
  status: DeliveryState;
  createdAt: string;
  updatedAt: string;
  metadata?: Record<string, unknown>;
}
