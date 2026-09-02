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
